"""Neo4j client with async connection management."""

import asyncio
import logging
import time
from typing import Dict, Any, List, Optional, Union
from contextlib import asynccontextmanager
from pathlib import Path

import neo4j
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession, AsyncTransaction
from neo4j.exceptions import Neo4jError, ServiceUnavailable, AuthError, ConfigurationError

from .config import Neo4jConfig, load_neo4j_config
from .models import QueryResult, HealthCheckResult, ConnectionStatus
from .exceptions import (
    Neo4jConnectionError,
    Neo4jQueryError,
    Neo4jConfigurationError,
    TransactionError
)


logger = logging.getLogger(__name__)


class Neo4jClient:
    """Async Neo4j client with connection pooling and health checks."""

    def __init__(self, config: Optional[Neo4jConfig] = None, config_path: Optional[Path] = None):
        """Initialize Neo4j client.

        Args:
            config: Neo4j configuration object
            config_path: Path to configuration file
        """
        self.config = config or load_neo4j_config(config_path)
        self._driver: Optional[AsyncDriver] = None
        self._is_connected = False
        self._connection_lock = asyncio.Lock()

        # Setup logging
        if self.config.performance.enable_query_logging:
            logging.getLogger("neo4j").setLevel(logging.DEBUG)

    async def connect(self) -> None:
        """Establish connection to Neo4j database."""
        async with self._connection_lock:
            if self._is_connected and self._driver:
                return

            try:
                # Get password from environment
                password = self.config.connection.password

                # Create driver with configuration
                self._driver = AsyncGraphDatabase.driver(
                    self.config.connection.uri,
                    auth=(self.config.connection.username, password),
                    max_connection_pool_size=self.config.pool.max_connections,
                    connection_timeout=self.config.pool.connection_timeout
                )

                # Verify connectivity
                await self._driver.verify_connectivity()
                self._is_connected = True

                logger.info(f"Connected to Neo4j at {self.config.connection.uri}")

            except AuthError as e:
                raise Neo4jConnectionError(
                    f"Authentication failed: {e}",
                    uri=self.config.connection.uri,
                    details={'error_type': 'auth_error'}
                )
            except ServiceUnavailable as e:
                raise Neo4jConnectionError(
                    f"Neo4j service unavailable: {e}",
                    uri=self.config.connection.uri,
                    details={'error_type': 'service_unavailable'}
                )
            except ConfigurationError as e:
                raise Neo4jConfigurationError(f"Configuration error: {e}")
            except Exception as e:
                raise Neo4jConnectionError(
                    f"Failed to connect to Neo4j: {e}",
                    uri=self.config.connection.uri,
                    details={'error_type': 'connection_error'}
                )

    async def disconnect(self) -> None:
        """Close connection to Neo4j database."""
        async with self._connection_lock:
            if self._driver:
                await self._driver.close()
                self._driver = None
                self._is_connected = False
                logger.info("Disconnected from Neo4j")

    async def health_check(self) -> HealthCheckResult:
        """Perform health check on Neo4j connection."""
        start_time = time.time()

        try:
            if not self._is_connected or not self._driver:
                await self.connect()

            # Simple query to test connectivity
            result = await self.execute_query("RETURN 1 as health_check")
            response_time = time.time() - start_time

            # Get database info
            db_info = await self._get_database_info()

            return HealthCheckResult(
                status=ConnectionStatus.CONNECTED,
                response_time=response_time,
                database_info=db_info
            )

        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                status=ConnectionStatus.ERROR,
                response_time=response_time,
                error_message=str(e)
            )

    async def _get_database_info(self) -> Dict[str, Any]:
        """Get database information."""
        try:
            result = await self.execute_query(
                "CALL dbms.components() YIELD name, versions, edition"
            )
            return {
                'components': result.records,
                'database': self.config.connection.database
            }
        except Exception:
            return {'database': self.config.connection.database}

    @asynccontextmanager
    async def session(self, **kwargs) -> AsyncSession:
        """Create async session context manager."""
        if not self._is_connected or not self._driver:
            await self.connect()

        session = self._driver.session(
            database=self.config.connection.database,
            **kwargs
        )

        try:
            yield session
        finally:
            await session.close()

    @asynccontextmanager
    async def transaction(self, **kwargs) -> AsyncTransaction:
        """Create async transaction context manager."""
        async with self.session(**kwargs) as session:
            tx = await session.begin_transaction()
            try:
                yield tx
                await tx.commit()
            except Exception:
                await tx.rollback()
                raise

    async def execute_query(
        self,
        query: str,
        parameters: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None
    ) -> QueryResult:
        """Execute a Cypher query.

        Args:
            query: Cypher query string
            parameters: Query parameters
            timeout: Query timeout in seconds

        Returns:
            QueryResult with records and metadata
        """
        if not query.strip():
            raise Neo4jQueryError("Query cannot be empty")

        parameters = parameters or {}
        timeout = timeout or self.config.performance.query_timeout
        start_time = time.time()

        try:
            async with self.session() as session:
                result = await session.run(query, parameters, timeout=timeout)
                records = [record.data() async for record in result]
                summary = await result.consume()

                execution_time = time.time() - start_time

                if self.config.performance.enable_query_logging:
                    logger.debug(f"Query executed in {execution_time:.3f}s: {query[:100]}...")

                return QueryResult(
                    records=records,
                    summary={
                        'query_type': summary.query_type,
                        'counters': dict(summary.counters),
                        'plan': summary.plan.arguments if summary.plan else None,
                        'profile': summary.profile.arguments if summary.profile else None,
                        'notifications': [n.description for n in summary.notifications],
                        'database': summary.database,
                        'server': summary.server.address if summary.server else None
                    },
                    execution_time=execution_time
                )

        except Neo4jError as e:
            execution_time = time.time() - start_time
            raise Neo4jQueryError(
                f"Query execution failed: {e}",
                query=query,
                parameters=parameters,
                details={
                    'execution_time': execution_time,
                    'error_code': getattr(e, 'code', None),
                    'error_classification': getattr(e, 'classification', None)
                }
            )
        except Exception as e:
            execution_time = time.time() - start_time
            raise Neo4jQueryError(
                f"Unexpected error during query execution: {e}",
                query=query,
                parameters=parameters,
                details={'execution_time': execution_time}
            )

    async def execute_batch(
        self,
        queries: List[Dict[str, Any]],
        batch_size: Optional[int] = None
    ) -> List[QueryResult]:
        """Execute multiple queries in batches.

        Args:
            queries: List of query dictionaries with 'query' and optional 'parameters'
            batch_size: Batch size for processing

        Returns:
            List of QueryResult objects
        """
        if not queries:
            return []

        batch_size = batch_size or self.config.performance.batch_size
        results = []

        for i in range(0, len(queries), batch_size):
            batch = queries[i:i + batch_size]
            batch_results = []

            async with self.transaction() as tx:
                for query_dict in batch:
                    query = query_dict.get('query', '')
                    parameters = query_dict.get('parameters', {})

                    try:
                        result = await tx.run(query, parameters)
                        records = [record.data() async for record in result]
                        summary = await result.consume()

                        batch_results.append(QueryResult(
                            records=records,
                            summary={'query_type': summary.query_type},
                            execution_time=0.0  # Individual timing not available in batch
                        ))

                    except Exception as e:
                        raise Neo4jQueryError(
                            f"Batch query failed: {e}",
                            query=query,
                            parameters=parameters
                        )

            results.extend(batch_results)

        return results

    async def execute_transaction(
        self,
        transaction_func,
        *args,
        **kwargs
    ) -> Any:
        """Execute a function within a transaction.

        Args:
            transaction_func: Function to execute within transaction
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function

        Returns:
            Result of the transaction function
        """
        try:
            async with self.transaction() as tx:
                return await transaction_func(tx, *args, **kwargs)
        except Exception as e:
            raise TransactionError(f"Transaction failed: {e}")

    async def create_indexes(self) -> None:
        """Create indexes defined in configuration."""
        if not self.config.indexes.auto_create:
            return

        # Create node indexes
        for index_def in self.config.indexes.node_indexes:
            try:
                await self.execute_query(index_def)
                logger.info(f"Created node index: {index_def}")
            except Exception as e:
                logger.warning(f"Failed to create node index: {e}")

        # Create relationship indexes
        for index_def in self.config.indexes.relationship_indexes:
            try:
                await self.execute_query(index_def)
                logger.info(f"Created relationship index: {index_def}")
            except Exception as e:
                logger.warning(f"Failed to create relationship index: {e}")

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        return self._is_connected

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

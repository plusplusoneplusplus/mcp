"""Utility for segmenting markdown tables and storing them in a vector database."""

import re
import uuid
import os
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
from sentence_transformers import SentenceTransformer
from utils.vector_store.vector_store import ChromaVectorStore

class MarkdownTableSegmenter:
    """
    Utility for segmenting markdown tables and storing them in a vector database.
    """
    def __init__(
        self,
        vector_store: ChromaVectorStore,
        model_name: str = "all-MiniLM-L6-v2"
    ):
        """
        Initialize the table segmenter with an embedding model and vector store.
        
        Args:
            vector_store: An instance of ChromaVectorStore to use for storing segments.
            model_name: Name of the sentence transformer model to use for embeddings
        """
        self.model = SentenceTransformer(model_name)
        self.vector_store = vector_store
    
    def extract_tables(self, markdown_content: str) -> List[Dict[str, Any]]:
        """
        Extract tables from markdown content.
        
        Args:
            markdown_content: Markdown content containing tables
            
        Returns:
            List of dictionaries containing table information
        """
        # Regular expression to match markdown tables
        # This pattern matches tables with headers and at least one row
        table_pattern = r'(\|[^\n]+\|\n\|[-:| ]+\|\n(?:\|[^\n]+\|\n)+)'
        
        tables = []
        for i, match in enumerate(re.finditer(table_pattern, markdown_content)):
            table_content = match.group(1).strip()
            
            # Extract context (text before the table)
            start_pos = max(0, match.start() - 500)  # Get up to 500 chars before table
            context = markdown_content[start_pos:match.start()].strip()
            
            # Try to extract a heading that might be above the table
            heading = self._extract_heading_before_table(markdown_content, match.start())
            
            # Create a table entry
            table_info = {
                "id": f"table_{i}_{uuid.uuid4().hex[:8]}",
                "content": table_content,
                "context": context[-500:] if len(context) > 500 else context,  # Limit context size
                "heading": heading,
                "position": match.start()
            }
            tables.append(table_info)
        
        return tables
    
    def _extract_heading_before_table(self, markdown_content: str, table_start_pos: int) -> str:
        """
        Extract the nearest heading before a table.
        
        Args:
            markdown_content: Full markdown content
            table_start_pos: Starting position of the table
            
        Returns:
            Extracted heading or empty string if none found
        """
        # Look for headings (## Heading) before the table
        content_before = markdown_content[:table_start_pos]
        heading_matches = list(re.finditer(r'^(#{1,6})\s+(.+?)$', content_before, re.MULTILINE))
        
        if heading_matches:
            # Get the last heading before the table
            last_heading = heading_matches[-1]
            return last_heading.group(2).strip()
        
        return ""
    
    def _create_table_embedding(self, table_info: Dict[str, Any]) -> List[float]:
        """
        Create an embedding for a table based on its content and context.
        
        Args:
            table_info: Dictionary containing table information
            
        Returns:
            Embedding vector
        """
        # Combine table content, heading and context for embedding
        text_to_embed = f"{table_info['heading']} {table_info['context']} {table_info['content']}"
        
        # Generate embedding
        embedding = self.model.encode(text_to_embed)
        return embedding.tolist()
    
    def segment_and_store(self, markdown_content: str) -> Tuple[int, List[str]]:
        """
        Segment tables from markdown content and store them in the vector database.
        
        Args:
            markdown_content: Markdown content containing tables
            
        Returns:
            Tuple of (number of tables stored, list of table IDs)
        """
        # Extract tables
        tables = self.extract_tables(markdown_content)
        
        if not tables:
            return 0, []
        
        # Prepare data for vector store
        ids = [table["id"] for table in tables]
        embeddings = [self._create_table_embedding(table) for table in tables]
        metadatas = [{
            "heading": table["heading"],
            "context": table["context"][:100] + "..." if len(table["context"]) > 100 else table["context"],
            "position": table["position"]
        } for table in tables]
        documents = [table["content"] for table in tables]
        
        # Store in vector database
        self.vector_store.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )
        
        return len(tables), ids
    
    def search_tables(self, query: str, n_results: int = 5) -> Dict[str, Any]:
        """
        Search for tables based on semantic similarity to the query.
        
        Args:
            query: Search query
            n_results: Number of results to return
            
        Returns:
            Search results with matching tables
        """
        # Generate embedding for the query
        query_embedding = self.model.encode(query).tolist()
        
        # Query the vector store
        results = self.vector_store.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )
        
        return results 
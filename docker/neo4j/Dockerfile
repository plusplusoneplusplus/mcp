FROM neo4j:5.15-community

# Install additional tools for development
USER root

# Install curl and other utilities
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    jq \
    && rm -rf /var/lib/apt/lists/*

# Create directories for custom scripts
RUN mkdir -p /var/lib/neo4j/scripts

# Copy custom initialization scripts
COPY init-scripts/ /docker-entrypoint-initdb.d/

# Set proper permissions
RUN chown -R neo4j:neo4j /var/lib/neo4j/scripts
RUN chown -R neo4j:neo4j /docker-entrypoint-initdb.d

# Switch back to neo4j user
USER neo4j

# Expose ports
EXPOSE 7474 7687

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD cypher-shell -u neo4j -p ${NEO4J_PASSWORD:-devpassword} "RETURN 1" || exit 1

FROM python:3.11-slim

# Set work directory
WORKDIR /app

# Install git for some tools that rely on it
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY . /app

# Install project dependencies
RUN pip install --no-cache-dir pip && \
    pip install --no-cache-dir .

# Expose default server port
EXPOSE 8000

# Start the MCP server
CMD ["python", "server/main.py"]

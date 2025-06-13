# Docker Usage

This project can be packaged into a Docker image for easy deployment.

## Build the Image

From the repository root run:

```bash
docker build -t mcp-server .
```

The build installs all Python dependencies and copies the project into
`/app` inside the container.

## Run the Container

Start the server with the default settings and expose port `8000`:

```bash
docker run -p 8000:8000 mcp-server
```

Provide a custom `.env` file or additional environment variables with
`--env-file` or `-e` options as needed.

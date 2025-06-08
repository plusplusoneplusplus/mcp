#!/bin/bash

# Demo script that outputs various types of secrets for testing security filtering

echo "Starting security demo script..."
echo "DB_PASSWORD=mySecretPassword123!"
echo "API_KEY=sk-1234567890abcdef1234567890abcdef"
echo "AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
echo "Connection string: server=db.example.com;uid=admin;pwd=SuperSecret123!"
echo "JWT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
echo "Script completed successfully"

# Also output to stderr
echo "Debug: Using password=debugSecret123 for connection" >&2
echo "Warning: API key abc123def456ghi789 detected in config" >&2 
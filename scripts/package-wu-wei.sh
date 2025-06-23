#!/bin/bash

# Wu Wei Extension Packaging Script
# This script packages the Wu Wei VS Code extension into a .vsix file

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WU_WEI_DIR="$PROJECT_ROOT/wu-wei"

echo -e "${BLUE}Wu Wei Extension Packaging Script${NC}"
echo "=================================="

# Check if wu-wei directory exists
if [ ! -d "$WU_WEI_DIR" ]; then
    echo -e "${RED}Error: wu-wei directory not found at $WU_WEI_DIR${NC}"
    exit 1
fi

# Change to wu-wei directory
cd "$WU_WEI_DIR"

echo -e "${YELLOW}Working directory: $(pwd)${NC}"

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo -e "${RED}Error: package.json not found in wu-wei directory${NC}"
    exit 1
fi

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo -e "${RED}Error: npm is not installed${NC}"
    exit 1
fi

echo -e "${BLUE}Step 1: Installing dependencies...${NC}"
npm ci

echo -e "${BLUE}Step 2: Running linter...${NC}"
npm run lint

echo -e "${BLUE}Step 3: Compiling TypeScript...${NC}"
npm run compile

# Check if vsce is installed globally
if ! command -v vsce &> /dev/null; then
    echo -e "${YELLOW}vsce not found globally, installing...${NC}"
    npm install -g @vscode/vsce
fi

echo -e "${BLUE}Step 4: Packaging extension...${NC}"
vsce package

# Find the generated .vsix file
VSIX_FILE=$(find . -name "*.vsix" -type f | head -n 1)

if [ -n "$VSIX_FILE" ]; then
    echo -e "${GREEN}✅ Extension packaged successfully!${NC}"
    echo -e "${GREEN}Package location: $WU_WEI_DIR/$VSIX_FILE${NC}"
    
    # Get file size
    FILE_SIZE=$(ls -lh "$VSIX_FILE" | awk '{print $5}')
    echo -e "${GREEN}Package size: $FILE_SIZE${NC}"
    
    # Optional: Copy to a common artifacts directory
    ARTIFACTS_DIR="$PROJECT_ROOT/artifacts"
    if [ "$1" = "--copy-to-artifacts" ]; then
        mkdir -p "$ARTIFACTS_DIR"
        cp "$VSIX_FILE" "$ARTIFACTS_DIR/"
        echo -e "${GREEN}Package copied to: $ARTIFACTS_DIR/$(basename "$VSIX_FILE")${NC}"
    fi
else
    echo -e "${RED}❌ Error: No .vsix file found after packaging${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Wu Wei extension packaging completed successfully!${NC}"

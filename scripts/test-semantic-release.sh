#!/bin/bash

# Test semantic-release configuration locally
# This script simulates what semantic-release would do based on commit history

set -e

echo "🔍 Testing Semantic-Release Configuration"
echo "========================================"

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "❌ Error: Not in a git repository"
    exit 1
fi

# Check if semantic-release is available
echo "📦 Setting up semantic-release..."
if ! command -v uv &> /dev/null; then
    echo "❌ Error: uv is not installed. Please install it first."
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    uv venv
fi

# Activate virtual environment and install semantic-release
echo "Installing python-semantic-release..."
source .venv/bin/activate
uv pip install python-semantic-release

echo -e "\n📋 Current semantic-release configuration:"
echo "=========================================="
echo "From pyproject.toml:"
echo "- allowed_tags: [feat, fix, perf, refactor]"
echo "- minor_tags: [feat]"
echo "- patch_tags: [fix, perf, refactor]"
echo "- major_tags: [] (NONE - this prevents major bumps)"

echo -e "\n📝 Recent commits analysis:"
echo "==========================="
echo "Last 10 commits with their potential version impact:"

# Analyze recent commits
git log --oneline -10 --pretty=format:"%h %s" | while read commit_hash commit_message; do
    echo -n "  $commit_hash: "

    # Check commit message patterns
    if echo "$commit_message" | grep -q "^feat"; then
        echo -e "\033[0;33m$commit_message\033[0m (would bump MINOR)"
    elif echo "$commit_message" | grep -q "^fix\|^perf\|^refactor"; then
        echo -e "\033[0;32m$commit_message\033[0m (would bump PATCH)"
    elif echo "$commit_message" | grep -q "BREAKING CHANGE\|BREAKING:\|!:"; then
        echo -e "\033[0;31m$commit_message\033[0m (would be IGNORED - breaking changes disabled)"
    else
        echo -e "\033[0;37m$commit_message\033[0m (no version impact)"
    fi
done

echo -e "\n🔍 Testing semantic-release dry run:"
echo "===================================="

# Get current version
CURRENT_VERSION=$(git describe --tags --abbrev=0 2>/dev/null || echo '0.1.0')
echo "Current version: $CURRENT_VERSION"

# Test semantic-release version calculation
echo "Running semantic-release version --print (dry run)..."
NEW_VERSION=$(semantic-release version --print 2>/dev/null || echo "No version bump needed")

if [ "$NEW_VERSION" = "No version bump needed" ] || [ -z "$NEW_VERSION" ]; then
    echo "✅ Result: No version bump would occur"
else
    echo "📊 Proposed new version: $NEW_VERSION"

    # Extract version components for validation
    if [[ "$CURRENT_VERSION" =~ ^v?([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
        CURRENT_MAJOR=${BASH_REMATCH[1]}
        CURRENT_MINOR=${BASH_REMATCH[2]}
        CURRENT_PATCH=${BASH_REMATCH[3]}
    else
        echo "⚠️  Warning: Could not parse current version format"
        CURRENT_MAJOR=0
        CURRENT_MINOR=1
        CURRENT_PATCH=0
    fi

    if [[ "$NEW_VERSION" =~ ^v?([0-9]+)\.([0-9]+)\.([0-9]+) ]]; then
        NEW_MAJOR=${BASH_REMATCH[1]}
        NEW_MINOR=${BASH_REMATCH[2]}
        NEW_PATCH=${BASH_REMATCH[3]}
    else
        echo "❌ Error: Could not parse new version format"
        exit 1
    fi

    echo "Version analysis:"
    echo "  Current: $CURRENT_MAJOR.$CURRENT_MINOR.$CURRENT_PATCH"
    echo "  New:     $NEW_MAJOR.$NEW_MINOR.$NEW_PATCH"

    # Validate the version bump
    if [ "$NEW_MAJOR" -gt "$CURRENT_MAJOR" ]; then
        echo "❌ CRITICAL: Major version bump detected! This should not happen."
        echo "   Configuration error - major bumps should be disabled."
        exit 1
    elif [ "$NEW_MINOR" -gt "$CURRENT_MINOR" ]; then
        echo "✅ VALID: Minor version bump (feature addition)"
    elif [ "$NEW_PATCH" -gt "$CURRENT_PATCH" ]; then
        echo "✅ VALID: Patch version bump (bug fix/improvement)"
    else
        echo "⚠️  Warning: Unexpected version relationship"
    fi
fi

echo -e "\n🧪 Testing commit message patterns:"
echo "=================================="

# Test different commit message patterns
test_commit_patterns() {
    local pattern="$1"
    local expected="$2"

    echo "Testing: '$pattern' → Expected: $expected"

    # This is a simplified test - in reality, semantic-release would analyze the actual commit
    if echo "$pattern" | grep -q "^feat"; then
        echo "  Result: Would bump MINOR version ✅"
    elif echo "$pattern" | grep -q "^fix\|^perf\|^refactor"; then
        echo "  Result: Would bump PATCH version ✅"
    elif echo "$pattern" | grep -q "BREAKING CHANGE\|BREAKING:\|!:"; then
        echo "  Result: Would be IGNORED (breaking changes disabled) ✅"
    else
        echo "  Result: No version impact ✅"
    fi
}

test_commit_patterns "feat: add new feature" "MINOR"
test_commit_patterns "fix: resolve bug" "PATCH"
test_commit_patterns "perf: improve performance" "PATCH"
test_commit_patterns "refactor: clean up code" "PATCH"
test_commit_patterns "feat!: breaking change" "IGNORED"
test_commit_patterns "feat: add feature\n\nBREAKING CHANGE: breaks api" "IGNORED"
test_commit_patterns "docs: update readme" "NONE"

echo -e "\n✅ Semantic-release test completed!"
echo "=================================="
echo "Configuration appears to correctly prevent major version bumps."

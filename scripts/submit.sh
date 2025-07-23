#!/bin/bash

# Submit Code Changes Workflow Script
# Assumes commits are already created and no AI is needed for commit messages

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 1. Pre-Submission Analysis
print_status "Checking current git status..."
git status

print_status "Fetching latest changes from origin..."
git fetch origin

print_status "Comparing with main branch..."
echo "Commits ahead of origin/main:"
git log --oneline origin/main..HEAD

echo ""
echo "Commits in main that current branch doesn't have:"
git log --oneline HEAD..origin/main

# 2. Branch and Remote Verification
print_status "Verifying repository information..."
git remote -v
git branch -vv

# Get current branch name
CURRENT_BRANCH=$(git branch --show-current)
print_status "Current branch: $CURRENT_BRANCH"

# Check if we're on main branch and handle accordingly
if [ "$CURRENT_BRANCH" = "main" ]; then
    print_warning "Currently on main branch. Creating a feature branch for changes..."

    # Check if there are any uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        print_error "You have uncommitted changes on main branch. Please commit or stash them first."
        exit 1
    fi

    # Check if there are commits ahead of origin/main
    COMMITS_AHEAD=$(git rev-list --count origin/main..HEAD)
    if [ "$COMMITS_AHEAD" -eq 0 ]; then
        print_error "No commits to submit. You're up to date with origin/main."
        exit 1
    fi

    # Generate branch name based on latest commit
    LATEST_COMMIT_MSG=$(git log -1 --pretty=format:"%s")
    BRANCH_TYPE="feature"

    # Determine if this is a fix or feature based on commit message
    if echo "$LATEST_COMMIT_MSG" | grep -i -E "(fix|bug|patch|hotfix)" > /dev/null; then
        BRANCH_TYPE="fix"
    fi

    # Create sanitized branch name from commit message
    BRANCH_SUFFIX=$(echo "$LATEST_COMMIT_MSG" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g' | cut -c1-50)
    NEW_BRANCH="${BRANCH_TYPE}/${BRANCH_SUFFIX}"

    print_status "Creating branch: $NEW_BRANCH"

    # Create new branch pointing to current HEAD
    git checkout -b "$NEW_BRANCH"

    # Reset main to origin/main
    git checkout main
    git reset --hard origin/main

    # Switch back to new branch
    git checkout "$NEW_BRANCH"

    # Update CURRENT_BRANCH variable
    CURRENT_BRANCH="$NEW_BRANCH"
    print_success "Created and switched to branch: $CURRENT_BRANCH"
fi

# Get repository information
REPO_URL=$(git remote get-url origin)
REPO_OWNER=$(echo $REPO_URL | sed -n 's/.*github\.com[:/]\([^/]*\)\/.*/\1/p')
REPO_NAME=$(echo $REPO_URL | sed -n 's/.*github\.com[:/][^/]*\/\([^.]*\).*/\1/p')

print_status "Repository: $REPO_OWNER/$REPO_NAME"

# 3. Push current branch to remote
print_status "Pushing current branch to remote..."
if git push origin $CURRENT_BRANCH 2>/dev/null; then
    print_success "Branch pushed successfully"
else
    print_status "Setting upstream and pushing..."
    git push -u origin $CURRENT_BRANCH
fi

# 4. Create Pull Request
print_status "Creating pull request..."

# Generate PR title from latest commit message
PR_TITLE=$(git log -1 --pretty=format:"%s")
print_status "Using PR title: $PR_TITLE"

# Generate PR body with commit summary
PR_BODY="## Summary

This PR includes the following commits:

$(git log --oneline origin/main..HEAD)

## Changes
$(git diff --name-only origin/main..HEAD | sed 's/^/- /')

🤖 Generated with automated submission script"

# Create PR using GitHub CLI
if command -v gh &> /dev/null; then
    PR_URL=$(gh pr create --title "$PR_TITLE" --body "$PR_BODY" --base main --head $CURRENT_BRANCH 2>/dev/null | grep -o 'https://github.com/[^[:space:]]*')

    if [ $? -eq 0 ]; then
        print_success "Pull request created: $PR_URL"

        # 5. Enable Auto-Merge
        print_status "Enabling auto-merge with squash strategy..."
        if gh pr merge --auto --squash $PR_URL 2>/dev/null; then
            print_success "Auto-merge enabled successfully"
        else
            print_warning "Failed to enable auto-merge. You may need to enable it manually."
        fi

        # 6. Final Status Check
        print_status "Checking PR status..."
        gh pr view $PR_URL

        echo ""
        print_success "Submission complete!"
        echo ""
        echo "📋 Summary:"
        echo "- Branch: $CURRENT_BRANCH"
        echo "- Repository: $REPO_OWNER/$REPO_NAME"
        echo "- Pull Request: $PR_URL"
        echo "- Auto-merge: Enabled (squash strategy)"
        echo ""
        echo "🔄 Next steps:"
        echo "- Monitor CI pipeline completion"
        echo "- Address any reviewer feedback"
        echo "- Auto-merge will complete after approval and CI passes"

    else
        print_error "Failed to create pull request"
        exit 1
    fi
else
    print_error "GitHub CLI (gh) is not installed. Please install it to create pull requests."
    print_status "Alternative: Create PR manually at https://github.com/$REPO_OWNER/$REPO_NAME/compare/main...$CURRENT_BRANCH"
    exit 1
fi

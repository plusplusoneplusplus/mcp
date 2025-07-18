---
title: GitHub Issue Resolution Workflow
description: Complete end-to-end workflow for resolving GitHub issues including analysis, implementation, testing, code review, and PR creation
category: Development Workflow
tags: [github, issues, workflow, implementation, testing, pull-requests, git, code-review]
---

# AI Prompt: GitHub Issue Resolution Workflow

## Task Overview

Your primary task is to read a GitHub issue, understand the requirements, implement the necessary changes, create a pull request, and manage the git workflow properly. This is a complete end-to-end workflow for issue resolution.

**Code Editor Context:** Always identify and mention the current code editor being used (e.g., Cursor, Windsurf, VSCode, etc.) in your workflow updates, commit messages, and PR descriptions. This helps provide context for the development environment and any editor-specific features or limitations that may affect the implementation.

## Workflow Steps

### 0. Pre-Work Setup

**⚠️ IMPORTANT: Always start by checking out the main branch**
```bash
git checkout main && git pull origin main && source .venv/bin/activate
```
This ensures you're working from the latest stable code and prevents conflicts.

**Environment Setup:**
- Use existing virtual environment if available, otherwise create one with `uv venv`
- Always use uv instead of python/pip for all package management and Python execution:
  - Use `uv run` instead of `python`
  - Use `uv add` instead of `pip install`
  - Use `uv sync` to install dependencies from lock file

**Repository Identification:** Run `git remote -v` to identify the correct repository owner and name before any GitHub operations.

### 1. Issue Analysis Phase

**Read and Understand the Issue:**
- Carefully read the GitHub issue description, comments, and any attached files
- Identify the problem statement, requirements, and acceptance criteria
- Note any specific implementation details, constraints, or preferences mentioned
- Check for related issues, PRs, or discussions that might provide context
- Identify the scope of changes needed (files, components, features affected)

**Ask Clarifying Questions (if needed):**
- If the issue is unclear or missing critical information, ask specific questions
- Confirm your understanding of the requirements before proceeding
- Verify any assumptions about the implementation approach

### 2. Planning Phase

**Create Implementation Plan:**
- Break down the work into logical steps
- Identify which files need to be modified or created
- Consider the impact on existing functionality
- Plan for testing requirements (unit tests, integration tests, etc.)
- Identify any dependencies or prerequisites

**Branch Management:**
- **First, ensure you're on the main branch with latest changes** (see Pre-Work Setup above)
- Create a new feature branch with a descriptive name (e.g., `fix/issue-123-description` or `feature/issue-456-new-feature`)
- Verify you're working from the latest main branch

### 3. Implementation Phase

**⚠️ FIRST STEP: Mark Issue as Work-in-Progress**
- **Immediately after creating your branch and before making any code changes**, add a work-in-progress tag to the GitHub issue
- This prevents duplicate work and improves team coordination

**Code Changes:**
- Implement the required changes following the project's coding standards
- Write clean, well-documented code with appropriate comments
- Follow existing patterns and conventions in the codebase
- Ensure backward compatibility unless breaking changes are explicitly required

**Testing:**
- Add or update unit tests for new functionality
- Run existing tests to ensure no regressions
- Add integration tests if applicable
- Test edge cases and error scenarios

**Documentation:**
- Update relevant documentation (README, API docs, etc.)
- Add inline code comments for complex logic
- Update changelog if the project maintains one

### 4. Quality Assurance Phase

**Code Review Preparation:**
- Review your own changes thoroughly
- Check for code quality, performance implications, and security considerations
- Ensure all tests pass
- Verify that the implementation fully addresses the issue requirements

**Commit Management:**
- Make atomic, logical commits with clear commit messages that include the editor name at the end (e.g., "Fix issue #123: Update validation logic (Cursor)")
- Follow the project's commit message conventions
- Include the code editor name at the end of commit messages for development context
- Squash or organize commits if needed for a clean history

### 5. Local Test Execution and Validation Phase

**⚠️ MANDATORY: Complete Local Testing Before PR Submission**

Before creating a pull request, you MUST execute and validate all relevant test cases locally to ensure your implementation works correctly and doesn't introduce regressions.

**Local Testing Requirements:**
1. **Run All Existing Tests:** Execute the complete test suite to ensure no regressions
   ```bash
   # Use project-specific test commands, examples:
   uv run pytest                    # For Python projects with pytest
   uv run python -m pytest         # Alternative pytest execution
   uv run python -m unittest       # For unittest-based projects
   npm test                         # For Node.js projects
   make test                        # If project uses Makefile
   ```

2. **Run New/Modified Tests:** Execute any tests you've added or modified
   ```bash
   # Run specific test files or test cases
   uv run pytest tests/test_new_feature.py
   uv run pytest -k "test_specific_function"
   ```

3. **Integration Testing:** Test the feature end-to-end in a local environment
   - Start the application locally if applicable
   - Test the specific functionality addressed by the issue
   - Verify edge cases and error scenarios
   - Test with different input combinations

4. **Cross-Platform Testing (if applicable):** Test on different environments if the project supports multiple platforms

5. **Performance Testing (if applicable):** Run performance tests if your changes could impact performance

**Test Validation Checklist:**
- [ ] All existing tests pass without failures
- [ ] New tests pass and provide adequate coverage
- [ ] Integration tests demonstrate the feature works end-to-end
- [ ] No test warnings or deprecation messages introduced
- [ ] Test execution time hasn't significantly increased
- [ ] All test dependencies are properly installed and configured

**Test Results Documentation:**
Document your local testing results:

```markdown
## Local Test Execution Results
- **Code Editor:** [Editor used for development]
- **Test Framework:** [pytest/unittest/jest/etc.]
- **Total Tests Run:** [Number of tests executed]
- **Test Results:** [All passed/X failed/X skipped]
- **New Tests Added:** [Number and description]
- **Test Coverage:** [Coverage percentage if available]
- **Integration Testing:** [Completed/Not applicable]
- **Performance Impact:** [None/Improved/Degraded - with details]
- **Test Execution Time:** [Total time taken]
```

**If Tests Fail:**
- **DO NOT CREATE THE PULL REQUEST**
- **Fix all failing tests before proceeding**
- **Investigate and resolve any test failures**
- **Re-run the complete test suite after fixes**
- **Document any test changes or fixes made**

### 6. Pre-Submission Code Review Phase

**⚠️ MANDATORY: Automated Code Review Before PR Submission**

After successful local test validation, you MUST perform an automated code review using available tools (GitHub Copilot, AI code review tools, etc.) to assess the quality of your implementation.

**Code Review Process:**
1. **Request Automated Review:** Use available code review tools to analyze your changes
2. **Evaluate Review Results:** Carefully assess the feedback for:
   - Code quality issues (bugs, performance problems, security vulnerabilities)
   - Best practice violations
   - Maintainability concerns
   - Test coverage gaps
   - Documentation issues
3. **Quality Gate Decision:** Based on the review results:
   - **PROCEED:** If review results are positive with only minor suggestions
   - **STOP:** If review results indicate significant issues, bugs, or poor code quality

**If Review Results Are Poor:**
- **DO NOT CREATE THE PULL REQUEST**
- **CLEARLY NOTIFY THE USER** with a detailed explanation including:
  - Specific issues identified by the code review
  - Severity of the problems found
  - Recommended actions to address the issues
  - Estimated effort required for fixes

**Review Results Documentation:**
Document the review process and results in your workflow output:

```markdown
## Pre-Submission Code Review
- **Code Editor:** [Editor used for development]
- **Review Tool Used:** [GitHub Copilot/AI Review Tool/etc.]
- **Review Status:** [PASSED/FAILED]
- **Issues Found:** [List of significant issues, if any]
- **Decision:** [PROCEED_TO_PR/STOP_AND_FIX]
- **Next Steps:** [Actions required before PR submission]
```

**Only proceed to the next phase if the code review results are satisfactory.**

### 7. Pull Request Phase

**Create Pull Request:**
- Write a clear, descriptive PR title that references the issue (e.g., "Fix issue #123: Update validation logic")
- Include a comprehensive PR description that:
  - References the original issue (e.g., "Fixes #123" or "Closes #456")
  - Mentions the code editor used for development (e.g., "Developed using Cursor")
  - Summarizes the changes made
  - Explains the approach taken
  - Lists any breaking changes or migration steps
  - Includes testing instructions for reviewers

**PR Best Practices:**
- Add appropriate labels and assignees
- Request reviews from relevant team members
- Include screenshots or demos for UI changes
- Link to any related issues or PRs

### 8. Post-Submission Phase

**Monitor and Respond:**
- Respond promptly to review comments and feedback
- Make requested changes in additional commits or amend existing ones
- Re-request reviews after addressing feedback
- Ensure CI/CD checks pass

**Merge and Cleanup:**
- Once approved, merge the PR using the project's preferred merge strategy
- Delete the feature branch after successful merge
- Verify the issue is properly closed and linked to the PR

## Git Commands Reference

```bash
# Start workflow - ensure you're on main and up to date
git checkout main && git pull origin main

# Verify repository information
git remote -v

# Create and switch to feature branch
git checkout -b fix/issue-123-description

# IMPORTANT: Mark issue as work-in-progress BEFORE making code changes
# (Add WIP label, comment on issue, or assign yourself via GitHub UI/API)

# Make commits with editor context
git commit -m "Fix issue #123: Update validation logic (Cursor)"
git commit -m "Add tests for issue #123: Validation improvements (VSCode)"

# After making changes and commits
git push origin fix/issue-123-description

# After PR is merged, cleanup
git branch -d fix/issue-123-description
git push origin --delete fix/issue-123-description  # if needed
```

## Commit Message Format

Always include the code editor name at the end of your commit messages using this format:
- `Action: Brief description (EditorName)`
- Examples:
  - `Fix issue #123: Update validation logic (Cursor)`
  - `Add feature #456: New user authentication (VSCode)`
  - `Refactor: Improve error handling in API calls (Windsurf)`

## Output Format

When working through this workflow, provide updates at each major step:

### Issue Analysis Summary
```markdown
## Issue Analysis
- **Code Editor:** [Current editor: Cursor/Windsurf/VSCode/etc.]
- **Issue Number:** #123
- **Problem:** [Brief description]
- **Requirements:** [Key requirements identified]
- **Scope:** [Files/components affected]
- **Approach:** [Planned implementation approach]
```

### Implementation Progress
```markdown
## Implementation Progress
- **Code Editor:** [Current editor being used]
- **Branch Created:** `fix/issue-123-description`
- **WIP Status:** [Issue marked as work-in-progress: Yes/No]
- **Files Modified:** [List of files changed]
- **Key Changes:** [Summary of main changes]
- **Tests Added/Updated:** [Testing changes]
- **Editor Features Used:** [Any specific editor features utilized, e.g., AI assistance, extensions, etc.]
```

### Local Test Execution Results
```markdown
## Local Test Execution Results
- **Code Editor:** [Editor used for development]
- **Test Framework:** [pytest/unittest/jest/etc.]
- **Total Tests Run:** [Number of tests executed]
- **Test Results:** [All passed/X failed/X skipped]
- **New Tests Added:** [Number and description]
- **Test Coverage:** [Coverage percentage if available]
- **Integration Testing:** [Completed/Not applicable]
- **Performance Impact:** [None/Improved/Degraded - with details]
- **Test Execution Time:** [Total time taken]
```

### Pre-Submission Code Review
```markdown
## Pre-Submission Code Review
- **Code Editor:** [Editor used for development]
- **Review Tool Used:** [GitHub Copilot/AI Review Tool/etc.]
- **Review Status:** [PASSED/FAILED]
- **Issues Found:** [List of significant issues, if any]
- **Decision:** [PROCEED_TO_PR/STOP_AND_FIX]
- **Next Steps:** [Actions required before PR submission]
```

### Pull Request Summary
```markdown
## Pull Request Created
- **Code Editor:** [Editor used for development]
- **PR Title:** [Title]
- **PR Number:** #456
- **Description:** [Brief summary of PR description]
- **Status:** [Draft/Ready for Review/Approved/Merged]
```

### Completion Confirmation
```markdown
## Workflow Complete
- **Code Editor:** [Editor used throughout workflow]
- **PR Status:** Merged
- **Issue Status:** Closed
- **Branch Cleanup:** Complete
```

## Best Practices

1. **Repository Verification:** Always verify repository information before starting work
2. **Communication:** Keep stakeholders informed of progress and any blockers
3. **Documentation:** Document decisions and trade-offs made during implementation
4. **Testing:** Prioritize thorough testing to prevent regressions
5. **Local Test Validation:** Always execute and validate all tests locally before PR submission
6. **Code Quality:** Maintain high code quality standards throughout
7. **Pre-Submission Review:** Always perform automated code review before creating PRs
8. **Quality Gates:** Never submit PRs with significant code quality issues or failing tests
9. **Git Hygiene:** Keep commit history clean and meaningful
10. **Issue Tracking:** Ensure proper linking between issues, commits, and PRs

## Error Handling

If you encounter issues during any phase:
- Document the problem clearly
- Seek help or clarification when needed
- Consider alternative approaches if the original plan isn't working
- Update stakeholders on any delays or changes in scope
- Don't hesitate to ask for code review or pair programming assistance

Remember: The goal is not just to close the issue, but to deliver a high-quality solution that improves the codebase and provides value to users.

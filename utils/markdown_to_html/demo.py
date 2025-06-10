#!/usr/bin/env python3
"""
Demonstration script for markdown to HTML conversion functionality.

This script shows how the work item tool will automatically convert
markdown descriptions to HTML when creating work items.
"""

from utils.markdown_to_html import markdown_to_html, detect_and_convert_markdown
from utils.markdown_to_html.converter import is_markdown_content


def demo_markdown_conversion():
    """Demonstrate markdown to HTML conversion with various examples."""

    print("=== Markdown to HTML Conversion Demo ===\n")

    # Example 1: Bug report with markdown
    bug_report = """# Login Bug Report

## Description
The login functionality is **not working** properly after the latest deployment.

## Steps to Reproduce
1. Navigate to the login page
2. Enter valid credentials
3. Click the "Login" button

## Expected Result
User should be logged in successfully and redirected to the dashboard.

## Actual Result
Error message appears: `Invalid credentials`

## Additional Information
- This affects all browsers (Chrome, Firefox, Safari)
- Issue started after deployment on 2024-01-15
- Error appears in console: `TypeError: Cannot read property 'token' of undefined`

## Workaround
Users can refresh the page and try again - sometimes works on second attempt.

> **Priority**: High - affects all users
"""

    print("Example 1: Bug Report")
    print("=" * 50)
    print("Original Markdown:")
    print(bug_report)
    print("\nIs Markdown?", is_markdown_content(bug_report))
    print("\nConverted HTML:")
    html_result = detect_and_convert_markdown(bug_report)
    print(html_result)
    print("\n" + "=" * 80 + "\n")

    # Example 2: Feature request with code
    feature_request = """## New Authentication System

### Overview
Implement a new authentication system with the following features:

- **Multi-factor authentication (MFA)**
- Single sign-on (SSO) integration
- Password reset functionality
- Session management

### Technical Requirements

#### API Endpoints
```python
# Login endpoint
@app.route('/api/auth/login', methods=['POST'])
def login():
    return authenticate_user(request.json)

# MFA verification
@app.route('/api/auth/mfa/verify', methods=['POST'])
def verify_mfa():
    return verify_mfa_token(request.json)
```

#### Database Schema
| Field | Type | Description |
|-------|------|-------------|
| user_id | UUID | Primary key |
| email | VARCHAR(255) | User email |
| password_hash | VARCHAR(255) | Hashed password |
| mfa_enabled | BOOLEAN | MFA status |

### Acceptance Criteria
1. Users can log in with email and password
2. MFA is required for admin accounts
3. Session timeout after 30 minutes of inactivity
4. Password reset via email link

### Links
- [Design Document](https://docs.company.com/auth-design)
- [Security Requirements](https://docs.company.com/security)
"""

    print("Example 2: Feature Request")
    print("=" * 50)
    print("Original Markdown:")
    print(feature_request)
    print("\nIs Markdown?", is_markdown_content(feature_request))
    print("\nConverted HTML:")
    html_result = detect_and_convert_markdown(feature_request)
    print(html_result)
    print("\n" + "=" * 80 + "\n")

    # Example 3: Plain text (should not be converted)
    plain_text = "This is just a simple task description without any special formatting. It should remain as plain text."

    print("Example 3: Plain Text")
    print("=" * 50)
    print("Original Text:")
    print(plain_text)
    print("\nIs Markdown?", is_markdown_content(plain_text))
    print("\nAfter detect_and_convert_markdown:")
    result = detect_and_convert_markdown(plain_text)
    print(result)
    print("Same as original?", result == plain_text)
    print("\n" + "=" * 80 + "\n")

    # Example 4: Mixed content
    mixed_content = """Task: Update documentation

The documentation needs to be updated with the following changes:
- Add new API endpoints
- Update examples with **current syntax**
- Fix broken links

See the `docs/api.md` file for details.
"""

    print("Example 4: Mixed Content")
    print("=" * 50)
    print("Original Text:")
    print(mixed_content)
    print("\nIs Markdown?", is_markdown_content(mixed_content))
    print("\nConverted HTML:")
    html_result = detect_and_convert_markdown(mixed_content)
    print(html_result)


if __name__ == "__main__":
    demo_markdown_conversion()

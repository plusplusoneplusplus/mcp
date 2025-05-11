---
trigger: model_decision
description: Rules for writing documentation
---

# Documentation Writing Rules

These rules define how to write and structure documentation. All contributors and automation should follow these guidelines when generating or updating documentation files.

---

## 1. High-Level and Concise
- Documentation should provide a high-level summary of each component, tool, or utility.
- Avoid excessive detail or code dumps; focus on what the module does and how it is used.
- Each section should fit comfortably on a single screen for quick reference.

## 2. Section Structure
- Each tool or utility should be documented as a separate section ("talk") in Markdown.
- Each section must include:
  - **Name** (with code formatting if it's a class or module)
  - **Functionality:** (bullet points summarizing what the tool does)
  - **Usage:** (bullet points or short sentences on how to use the tool, including main entry points, key functions/classes, and typical inputs/outputs)
- Optionally include a short example if it adds clarity, but keep it brief.

## 3. Formatting
- Use Markdown for all documentation.
- Use bold and code formatting for clarity (e.g., `ToolName`, **Functionality:**, etc.).
- Use bullet points for lists and keep sentences short and direct.
- Separate each tool/utility section with a horizontal rule (`---`).

## 4. Scope
- Only document public or intended-for-use tools/utilities. Do not document internal helpers unless they are part of the public API.
- If a tool is deprecated or experimental, indicate this clearly at the start of the section.

## 5. File Organization
- Place high-level documentation in the `docs/` directory.
- If documenting rules or standards, place them in `.windsurf/rules/` as Markdown files, with a clear filename (e.g., `doc_documentation.md`).

## 6. Language and Tone
- Use clear, professional, and neutral language.
- Avoid jargon unless it is explained or commonly understood in the field.
- Prefer active voice and direct instructions.

---

For questions or suggestions about these rules, update this file or contact the project maintainers.

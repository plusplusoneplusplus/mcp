---
title: Extract Key Information from Commits
description: Analyzes software commits to extract patterns and entities for building knowledge graphs from codebase evolution
category: Code Analysis
tags: [commits, knowledge-extraction, patterns, entities, relationships, documentation]
---

# AI Prompt: Extract Key Information from Commits

## Task Overview

Your primary task is to analyze one or more software commits (including commit messages and code diffs) and extract meaningful patterns, entities, and their relationships. The goal is to build a knowledge base from the evolution of the codebase.

## Input

You will be provided with:
1.  **Commit Message(s):** The message(s) associated with the commit(s).
2.  **Code Diff(s):** The changes made to the code in patch format.

## Information to Extract

You need to identify and document two main categories of information:

### 1. Patterns in Changes

Identify and describe common or significant patterns in the code changes. These patterns represent "how-to" knowledge. Examples include:
    - How to add a new configuration parameter.
    - How to implement logging for a specific module.
    - How to define a new API endpoint.
    - Refactoring patterns applied.
    - How to add a new test case for a particular type of feature.

For each pattern identified:
    - Provide a concise name for the pattern.
    - Describe the steps involved or the structure of the pattern.
    - Include relevant code snippets (if applicable and concise) from the diff to illustrate the pattern.

### 2. Entities and Relationships

Identify key entities and the relationships between them. Entities can be:
    - Features (e.g., "User Authentication", "Payment Processing")
    - Modules or Components (e.g., "AuthService", "DatabaseConnector")
    - Key terms or concepts introduced or modified (e.g., "Rate Limiting", "Idempotency Key")
    - Data structures or important variables.

For each entity:
    - Identify its name.
    - Provide a brief description.

For relationships between entities:
    - Identify the source entity.
    - Identify the target entity.
    - Describe the nature of the relationship (e.g., "uses", "depends on", "configures", "extends", "relates to"). Provide a brief reason or context for this relationship based on the commit.

## Output Format

**⚠️ IMPORTANT: Commit ID Preservation**
All output files MUST include the commit ID(s) at the top of each file for traceability. Use the following format:

```markdown
<!-- Source Commit(s): [commit_id_1], [commit_id_2], ... -->
```

Your output should be structured as a set of markdown files organized as follows:

### 1. How-To Pattern Documents

For each identified pattern, create a separate markdown file.
    - **File Naming:** `how-to-<pattern-name-slugified>.md` (e.g., `how-to-add-configuration.md`)
    - **Content:**
        ```markdown
        <!-- Source Commit(s): [commit_id_1], [commit_id_2], ... -->
        # How To: [Pattern Name]

        ## Description
        [Detailed description of the pattern and when it's used.]

        ## Steps / Structure
        [Step-by-step instructions or description of the pattern's structure.]
        - Step 1: ...
        - Step 2: ...

        ## Examples from Commit(s)
        (Optional: Include relevant, concise code snippets from the commit if they clearly illustrate the pattern)
        ```

### 2. Entity Documents and Relationships

For each identified entity, create or update a markdown file.
    - **File Naming:** `entity-<entity-name-slugified>.md` (e.g., `entity-user-authentication.md`)
    - **Content (if new entity):**
        ```markdown
        <!-- Source Commit(s): [commit_id_1], [commit_id_2], ... -->
        # Entity: [Entity Name]

        ## Description
        [Brief description of the entity.]
        <!-- For large features, expand this section with more details. -->
        <!-- Consider a Mermaid diagram if it helps visualize the feature's components or interactions. -->
        <!-- Example Mermaid diagram:
        ```mermaid
        graph TD;
            A[Component A] --> B(Component B);
            A --> C{Decision Point};
            C -->|Yes| D[Sub-feature D];
            C -->|No| E[Sub-feature E];
        ```
        -->

        ## Relationships
        <!-- Relationships will be appended here by the extraction process -->
        ```
    - **Updating Relationships:** If the entity file already exists, append the new relationship to its "Relationships" section.
    - **For Large Features:**
        - Provide a more detailed description, outlining its purpose, key sub-components (if any), and core functionality.
        - If the feature involves complex interactions or a clear structure, consider generating a Mermaid diagram (```mermaid ... ```) within the description to visualize this. Focus on clarity and avoid overly complex diagrams.

For each identified relationship, append to the *source entity's* markdown file under the "Relationships" section:
        ```markdown
        - **Relates to:** `[Target Entity Name]`
          - **Reason/Context:** [Description of why/how these entities are related, based on the commit.]
          - **Link:** `[./entity-<target-entity-name-slugified>.md](mdc:entity-<target-entity-name-slugified>.md)`
        ```

**Example of appending a relationship to `entity-auth-service.md`:**
```markdown
<!-- Source Commit(s): abc123, def456 -->
# Entity: AuthService

## Description
Handles user authentication and authorization.

## Relationships
- **Relates to:** `DatabaseConnector`
  - **Reason/Context:** AuthService uses DatabaseConnector to retrieve user credentials from the database.
  - **Link:** `[./entity-database-connector.md](mdc:entity-database-connector.md)`
- **Relates to:** `RateLimiter`  <!-- New relationship being added -->
  - **Reason/Context:** AuthService calls RateLimiter to prevent brute-force attacks on login attempts, as introduced in commit [commit_hash_or_description].
  - **Link:** `[./entity-rate-limiter.md](mdc:entity-rate-limiter.md)`
```

## General Guidelines
- Be concise and focus on the most impactful information.
- Use clear and unambiguous language.
- Ensure file names are slugified (lowercase, dashes for spaces, remove special characters).
- If multiple commits are provided, try to synthesize information but also attribute changes or new insights to specific commits if relevant (e.g., "This pattern was introduced in commit X" or "The relationship between Y and Z was established by commit A").

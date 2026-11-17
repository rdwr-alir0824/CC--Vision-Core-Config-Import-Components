# CC -Vision Core Config Import Components

## 1. Project Identity

Project Name:
CC -Vision Core Config Import Components

Project Type:
Enterprise Python automation and REST API integration.

Target Platforms:
- Radware APSolute Vision
- Radware Cyber Controller

Development Environment:
- Visual Studio Code
- GitHub Copilot
- Python
- Git

## 2. Project Mission

Develop a modular application that consolidates existing
scripts for exporting, importing, migrating, and validating
configuration objects between Radware Vision and
Cyber Controller environments.

The primary goal is to reduce manual configuration
backup, restoration, and migration procedures.

The application must reuse existing working functionality
where appropriate while improving reliability,
security, error handling, and maintainability.

## 3. Primary Objectives

1. Preserve existing migration functionality.
2. Consolidate duplicate code.
3. Centralize authentication and API connections.
4. Implement independent migration modules.
5. Provide a master controller for executing modules.
6. Support configuration export and import.
7. Introduce pre-import validation.
8. Implement configuration comparison.
9. Improve logging and failure reporting.
10. Investigate additional supported APIs.
11. Reduce remaining manual configuration steps.
12. Maintain development progress and documentation.

## 4. Existing Scripts

Existing scripts are stored under:

legacy/

The original scripts remain in a separate workspace.

Treat the scripts under legacy/ as READ-ONLY
reference implementations.

Do not:
- Modify legacy scripts.
- Delete legacy scripts.
- Rename legacy scripts.
- Execute legacy migration scripts.
- Execute their authentication functions.
- Connect to external systems without approval.

All new application code must be developed
separately under src/.

## 5. Initial Migration Domains

The initial source discovery identified:

- Controller site and device objects
- Physical and Organization trees
- Device-access configuration
- Device credential transformations
- LDAP permission mappings
- Scheduled tasks

Additional utilities include:
- Document restoration
- Docker deployment helpers

Do not assume every utility belongs in the
new master application.

Validate module scope before integration.

## 6. Proposed Application Architecture

Prefer a modular Python application.

Proposed components:

- Master CLI/controller
- Configuration and profile management
- Authentication and session management
- Vision API client
- Cyber Controller API client
- Shared HTTP transport
- Independent migration modules
- Export/import orchestration
- Configuration comparison
- Validation and reporting
- Structured logging

This architecture is proposed until approved.

Avoid placing all functionality in one large file.

## 7. API Development Rules

Never invent API endpoints.

API functionality must be supported by:
- Existing source-code evidence
- Approved official API documentation
- Authorized test results

Track API compatibility by product and version.

Clearly distinguish:
- Observed in source
- Documented
- Mock tested
- Live tested

Never assume Vision and Cyber Controller
implement every endpoint identically.

## 8. Authentication and Security

- Never hardcode credentials or tokens.
- Never log passwords or authentication cookies.
- Never expose secrets in documentation.
- Use explicit session lifecycle management.
- Implement bounded HTTP timeouts.
- Handle authentication failures.
- Enable TLS certificate verification by default.
- Never silently disable TLS verification.
- Do not retry configuration-changing API requests
  without considering whether they already succeeded.

All live API operations require authorization.

## 9. Migration Safety

Export, plan, import, and validation operations
must remain logically separate.

Future imports should support:
- Preflight validation
- Dependency checking
- Dry-run planning
- Explicit approval
- Structured results
- Post-import verification

Do not silently:
- Broaden LDAP authorization scopes.
- Force device-locking settings.
- Substitute unknown configuration values.
- Change object hierarchy placement.
- Reuse source-controller device IDs on a
  different destination controller.

Unknown or ambiguous mappings must be reported.

HTTP acceptance does not necessarily mean an
asynchronous configuration operation completed.

## 10. Development Workflow

Before implementing a task:

1. Read the project instructions.
2. Read docs/PROGRESS.md if available.
3. Review relevant existing scripts.
4. Identify the approved task.
5. Explain affected files and dependencies.
6. Identify API and security implications.
7. Define acceptance criteria.

During implementation:

- Follow the approved task scope.
- Keep changes small.
- Preserve working behavior.
- Prefer reusable functions.
- Avoid unnecessary dependencies.
- Create appropriate tests.

After implementation:

- Review all changes.
- Run only authorized tests.
- Record actual test results.
- Update the progress tracker.
- Identify remaining problems.

Never mark untested functionality as verified.

## 11. Git Rules

The project uses a local Git repository.

A company GitHub remote may be configured later.

Do not automatically:
- Stage files
- Commit changes
- Push changes
- Create branches
- Delete repository content
- Modify Git history

These operations require explicit authorization.

Never commit credentials or operational exports.

## 12. Project Documentation

Maintain the following documents:

docs/PROJECT.md
docs/ARCHITECTURE.md
docs/API_MATRIX.md
docs/ROADMAP.md
docs/PROGRESS.md
docs/DECISIONS.md

PROGRESS.md is the authoritative development
checkpoint for the project.

API_MATRIX.md tracks API capabilities and
verification status.

ROADMAP.md tracks milestones and planned tasks.

DECISIONS.md records architecture decisions
and their approval status.

## 13. Progress Tracking

Each development task must contain:

- Task ID
- Description
- Priority
- Dependencies
- Approval status
- Implementation status
- Verification status
- Files affected
- Test evidence
- Known blockers
- Next action

Distinguish:
- Planned
- Approved
- In progress
- Implemented
- Verified complete
- Blocked

A task is not verified complete until
its acceptance criteria have passed.

## 14. Session Completion Report

At the end of each task, report:

1. Task ID and objective
2. Work completed
3. Files created or modified
4. API operations involved
5. Tests executed
6. Results and evidence
7. Problems or blockers
8. Recommended next action

Clearly distinguish verified results
from assumptions and proposals.

## 15. Current Development Phase

Current Milestone:

CCV-001 - Project Foundation

Current authorized objectives:

- Verify the legacy script inventory.
- Establish project instructions.
- Create architecture documentation.
- Create the API coverage matrix.
- Create the development roadmap.
- Create the progress tracker.

Do not begin application refactoring or
production migration code until authorized.

Do not execute live API requests or migration scripts.
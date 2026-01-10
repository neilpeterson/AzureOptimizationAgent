---
description: Clean up project by removing unnecessary code and updating documentation
allowed-tools: Glob, Grep, Read, Edit, Write, Bash(git:*), Bash(python:*), Bash(pip:*), Bash(pytest:*), Bash(ruff:*), Bash(az:*), Bash(ls:*), Task
---

# Project Scrub Command

Performs comprehensive Azure Optimization Agent project cleanup: removes unnecessary code, simplifies where possible, and ensures all documentation is current.

## Workflow:

### 1. **Pre-Scrub Assessment**
   - Read `STATUS.md` to understand current project state
   - Read `PLAN.md` to understand implementation roadmap
   - Create a checklist of areas to review
   - Ask user if there are specific areas of concern

### 2. **Code Cleanup**

   **A. Find Unused Code:**
   - Run Ruff linter: `ruff check src/`
   - Look for:
     - Commented-out code blocks
     - Unused imports
     - Unused private functions (functions starting with `_`)
     - Dead code paths (unreachable code after return/raise)
     - TODO/FIXME comments that need action or removal
     - Empty function bodies (just `pass`)
     - Unused Pydantic model fields

   **B. Python-Specific Cleanup:**
   - Remove unused imports at top of files
   - Check for unused variables in functions
   - Look for unnecessary `# type: ignore` comments
   - Find functions without docstrings
   - Check for hardcoded strings that should be constants
   - Look for inline values that should use configuration
   - Verify type hints are consistent

   **C. Pydantic/Data Model Cleanup:**
   - Check `shared/models.py` for unused model classes
   - Verify all model fields are used in the codebase
   - Look for model duplication or overlap
   - Check that Field aliases are consistent (snake_case ↔ camelCase)
   - Verify default values are appropriate
   - Look for models that could be simplified

   **D. Azure Functions Cleanup:**
   - Check for unused function endpoints
   - Verify function bindings match implementation
   - Look for unused environment variable references
   - Check for hardcoded Azure resource names
   - Verify managed identity usage is consistent

   **E. Simplification Opportunities:**
   - Look for overly complex functions (should be broken into smaller functions)
   - Check for repeated code that could be extracted to shared utilities
   - Find magic numbers/strings that should be constants
   - Identify modules with too many responsibilities
   - Look for deeply nested conditionals that could be flattened
   - Check for try/except blocks that are too broad

   **F. File Organization:**
   - Check for empty directories
   - Look for duplicate or redundant files
   - Verify file placement matches folder structure
   - Check for temporary or backup files (.bak, .tmp, .DS_Store, __pycache__, etc.)
   - Ensure shared code is in `shared/`, detection modules in `detection_layer/`, etc.
   - Look for files not following naming conventions

### 3. **Infrastructure & Configuration**

   **Review Bicep Files:**
   - `infra/main.bicep` - Check for unused resources or parameters
   - `infra/main.bicepparam` - Verify parameter values are current
   - Look for hardcoded values that should be parameters
   - Check RBAC assignments are minimal and necessary
   - Verify resource naming conventions are consistent

   **Review Python Configuration:**
   - `requirements.txt` - Check for unused dependencies
   - `host.json` / `local.settings.json` - Verify settings are current
   - `.gitignore` - Ensure Python artifacts are ignored properly
   - Check for `.env` files that shouldn't be committed

   **Actions:**
   - Remove unused Bicep parameters
   - Update outdated resource API versions
   - Verify deployment configurations are correct
   - Check that environment variable names are consistent

### 4. **Shared Library Review**

   **Check Modularity Principle:**
   - Verify `shared/` contains only generic, reusable code
   - Check that module-specific logic is in `detection_layer/`
   - Look for domain-specific code that leaked into shared library
   - Verify `__init__.py` exports are up to date

   **Specific Files:**
   - `shared/models.py` - No module-specific models
   - `shared/cosmos_client.py` - Generic CRUD only
   - `shared/resource_graph.py` - Generic query client only
   - `shared/confidence.py` - Generic utilities only
   - `shared/cost_calculator.py` - Generic utilities only

   **Detection Module Review:**
   - `detection_layer/abandoned_resources/` - All abandoned-specific logic here
   - Check `config.py`, `queries.py`, `confidence.py`, `cost_calculator.py`
   - Verify module `__init__.py` exports are complete

### 5. **Documentation Review**

   **A. CLAUDE.md:**
   - Verify architecture description matches implementation
   - Check tech stack is current
   - Update module system documentation if changed
   - Verify data contracts match models.py
   - Check severity/confidence thresholds are accurate

   **B. STATUS.md:**
   - Update phase completion status
   - Move completed items from "In Progress" to done
   - Add any new tasks discovered
   - Update "Notes" with recent changes
   - Remove stale entries
   - Verify blockers are current

   **C. PLAN.md:**
   - Verify implementation phases match current state
   - Check file lists are accurate
   - Update resource descriptions if changed
   - Verify dependencies between phases

   **D. docs/shared-library.md:**
   - Verify architecture diagrams are current
   - Check code examples work
   - Update function signatures if changed
   - Verify "Adding a New Module" guide is accurate

   **E. README.md (if exists):**
   - Verify setup instructions work
   - Check feature list matches implementation
   - Ensure deployment instructions are current
   - Verify links are not broken

### 6. **KQL Query Review**

   **In `detection_layer/abandoned_resources/queries.py`:**
   - Verify all queries are syntactically correct
   - Check for hardcoded subscription IDs
   - Look for deprecated Resource Graph properties
   - Ensure projected fields match what code expects
   - Check for redundant or duplicate queries
   - Verify query comments are accurate

### 7. **Dependencies**

   **Review requirements.txt:**
   - Check for unused packages
   - Look for outdated dependencies
   - Verify version constraints are appropriate
   - Check for security vulnerabilities

   **Actions:**
   - Remove unused packages
   - Update outdated dependencies: `pip list --outdated`
   - Verify all dependencies are necessary
   - Check Azure SDK versions are compatible

### 8. **Build & Test Verification**

   **Linting:**
   - Run Ruff: `ruff check src/`
   - Run type checking: `mypy src/` (if configured)
   - Check for formatting issues: `ruff format --check src/`

   **Tests (if present):**
   - Run test suite: `pytest`
   - Look for obsolete tests
   - Ensure test names are descriptive
   - Check for tests without assertions
   - Verify mocks are up to date

   **Import Verification:**
   - Try importing main modules to catch import errors:
     ```python
     python -c "from shared import *"
     python -c "from detection_layer.abandoned_resources import *"
     ```

### 9. **Repository Hygiene**

   **Check for:**
   - Uncommitted changes: `git status`
   - Untracked files that should be committed or gitignored
   - Large files that shouldn't be in repo
   - Sensitive data (API keys, credentials, connection strings)
   - Python cache files in repo

   **Common files that should be gitignored:**
   - `__pycache__/`
   - `*.pyc`
   - `.env`
   - `local.settings.json`
   - `.venv/`
   - `*.egg-info/`
   - `.mypy_cache/`
   - `.ruff_cache/`
   - `.DS_Store`

### 10. **Create Summary Report**

   **Document all changes made:**
   - What was removed and why
   - What was simplified
   - Documentation updates made
   - Any issues found but not fixed (and why)
   - Recommendations for future cleanup
   - Warnings that should be addressed
   - Modularity violations found and fixed

### 11. **Update Status**

   - Update `STATUS.md` with scrub completion
   - Add entry to "Notes" section with date
   - Note any technical debt identified
   - Update phase status if applicable

### 12. **Commit Changes**

   - Stage all changes
   - Create detailed commit message explaining cleanup
   - Suggest whether changes should be in one commit or split
   - Ask user if they want to commit

## Important Notes:

- **Be Conservative**: Only remove code you're certain is unused
- **Preserve History**: Don't remove comments that explain "why" decisions were made
- **Check Imports**: Verify imports work after any code modifications
- **Ask Before Big Changes**: If unsure about removing something, ask the user
- **Document Everything**: Keep track of what was removed for the summary
- **Maintain Modularity**: Ensure shared library stays generic

## Tools to Use:

- `git status` - Check for untracked files
- `ruff check` - Check for code style and lint issues
- `ruff format` - Check formatting
- `pytest` - Run tests
- Task tool with Explore agent - For comprehensive code exploration
- Grep tool - Search for patterns (TODO, FIXME, unused imports, etc.)
- Glob tool - Find files by pattern
- Read tool - Review documentation and code files

## Common Grep Patterns:

```bash
# Find TODOs and FIXMEs
Grep: pattern="TODO|FIXME" glob="*.py"

# Find print statements (debug code)
Grep: pattern="print\\(" glob="*.py"

# Find unused imports (look for import without usage)
Grep: pattern="^from|^import" glob="*.py"

# Find hardcoded subscription IDs
Grep: pattern="[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}" glob="*.py"

# Find empty except blocks
Grep: pattern="except.*:" glob="*.py"

# Find pass statements (potential incomplete code)
Grep: pattern="^\\s+pass$" glob="*.py"

# Find type: ignore comments
Grep: pattern="# type: ignore" glob="*.py"

# Find hardcoded Azure resource names
Grep: pattern="microsoft\\.[a-z]+/" glob="*.py"
```

## Success Criteria:

- ✅ All Python imports work without errors
- ✅ Ruff linting passes (or violations documented)
- ✅ All documentation is current and accurate
- ✅ No unnecessary files remain
- ✅ Dependencies are minimal and up to date
- ✅ Code follows modularity principle (shared vs module-specific)
- ✅ STATUS.md accurately reflects project state
- ✅ No sensitive data in repository
- ✅ All models and contracts are documented
- ✅ Architecture diagrams match implementation

## Example Usage:

```bash
/scrub
```

The command will systematically go through all areas and report findings.

---
description: Display current project status, phase progress, and recent changes
allowed-tools: Read, Glob, Grep
---

# Project Status Overview

Provide a comprehensive status report for the Azure Optimization Agent project.

## Steps:

### 1. **Read Project Files**
   - Read `STATUS.md` for current implementation status
   - Read `PLAN.md` for the implementation roadmap
   - Optionally scan `src/functions/` to verify file counts

### 2. **Display Phase Progress**

   Show each phase with completion status:

   ```
   ## Implementation Progress

   | Phase | Status | Progress |
   |-------|--------|----------|
   | Phase 1: Infrastructure | ✅ Complete | 4/4 |
   | Phase 2: Shared Library | ✅ Complete | 7/8 |
   | Phase 3: Data Layer | ⏳ Not Started | 0/9 |
   | Phase 4: Detection Layer | 🔨 In Progress | 6/9 |
   | Phase 5: AI Agent | ⏳ Not Started | 0/5 |
   | Phase 6: Notification | ⏳ Not Started | 0/4 |
   ```

### 3. **Highlight Current Focus**
   - What phase is currently in progress
   - What specific files/tasks are next
   - Any blockers or issues noted

### 4. **Show Recent Activity**
   - List items from the "Notes" section in STATUS.md
   - Highlight significant refactoring or architecture decisions
   - Note any documentation updates

### 5. **File Verification**
   - Count actual Python files in `src/functions/`
   - Verify shared library files exist
   - Verify detection module files exist
   - Report any discrepancies between STATUS.md and actual files

### 6. **Architecture Summary**
   Show the current project structure:

   ```
   src/functions/
   ├── requirements.txt
   ├── shared/           # Generic utilities (Phase 2)
   │   ├── models.py
   │   ├── cosmos_client.py
   │   ├── resource_graph.py
   │   ├── confidence.py
   │   └── cost_calculator.py
   ├── data_layer/       # Data Layer Functions (Phase 3)
   └── detection_layer/  # Detection Modules (Phase 4)
       └── abandoned_resources/
   ```

### 7. **Suggest Next Steps**
   Based on current progress, suggest:
   - The next logical phase to work on
   - Specific files that need to be created
   - Any pending items (like unit tests)

   Ask the user what they'd like to work on next.

## Output Format:

Present information in a clear, scannable format:

```markdown
# Azure Optimization Agent - Project Status

## Overall Progress: X% Complete

### Phase Summary
[Table showing all phases]

### Current Focus
- Phase X: [Name]
- Next task: [Specific file or feature]

### Recent Changes
- [Date]: [Change description]

### Files Implemented
- Shared Library: X files
- Detection Layer: X files
- Data Layer: X files

### Pending Items
- [ ] Unit tests for shared library
- [ ] [Other pending items]

### Blockers
- [Any blockers, or "None"]

---

**What would you like to work on next?**
- Continue Phase X (next: [specific task])
- Start Phase Y
- Run `/scrub` to clean up
- Run `/deploy` to deploy infrastructure
```

## Key Files to Check:

| File | Purpose |
|------|---------|
| `STATUS.md` | Implementation progress tracking |
| `PLAN.md` | Detailed implementation plan |
| `CLAUDE.md` | Project architecture and guidelines |
| `docs/shared-library.md` | Shared library documentation |

## Important Notes:

- Always read STATUS.md first - it's the source of truth
- Verify file counts by scanning the actual directories
- Highlight any discrepancies between STATUS.md and actual state
- If STATUS.md is outdated, offer to update it
- Reference related commands: `/scrub`, `/deploy`

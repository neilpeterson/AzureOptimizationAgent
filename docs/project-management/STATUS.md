# Implementation Status

> Last Updated: 2026-01-11 (Phase 8 planning)

## Phase 1: Infrastructure ✅
- [x] `infra/main.bicep` - All resources: Storage, Cosmos DB, Function App, Logic App, Log Analytics, NSP
- [x] `infra/main.bicepparam` - Deployment parameters
- [x] Deploy to dev environment
- [x] Validate RBAC assignments

## Phase 2: Shared Library ✅
- [x] `src/functions/requirements.txt` - Python dependencies
- [x] `src/functions/shared/__init__.py` - Public API exports
- [x] `src/functions/shared/models.py` - Pydantic data contracts (Finding, ModuleInput/Output, etc.)
- [x] `src/functions/shared/cosmos_client.py` - Cosmos DB wrapper with managed identity
- [x] `src/functions/shared/resource_graph.py` - Generic Resource Graph client (refactored)
- [x] `src/functions/shared/confidence.py` - Generic confidence utilities (refactored)
- [x] `src/functions/shared/cost_calculator.py` - Generic severity classification & cost utilities (refactored)
- [ ] Unit tests for shared library

## Phase 3: Data Layer Functions ✅
- [x] `src/functions/function_app.py` - Main entry point with all HTTP triggers
- [x] `src/functions/data_layer/__init__.py`
- [x] `src/functions/data_layer/get_module_registry.py`
- [x] `src/functions/data_layer/save_findings.py`
- [x] `src/functions/data_layer/get_findings_history.py`
- [x] `src/functions/data_layer/get_findings_trends.py` - Month-over-month trend analysis (module-agnostic)
- [x] `src/functions/data_layer/get_subscription_owners.py`
- [x] `data/seed/module-registry.json` - Seed data for abandoned-resources module
- [x] `data/seed/subscription-owners.sample.json` - Sample owner mappings
- [ ] Integration tests

## Phase 4: Detection Layer ✅
- [x] `src/functions/detection_layer/__init__.py`
- [x] `src/functions/detection_layer/abandoned_resources/__init__.py`
- [x] `src/functions/detection_layer/abandoned_resources/confidence.py` - Module-specific confidence scoring
- [x] `src/functions/detection_layer/abandoned_resources/cost_calculator.py` - Module-specific cost estimation
- [x] `src/functions/detection_layer/abandoned_resources/queries.py` - KQL queries for 8 resource types
- [x] `src/functions/detection_layer/abandoned_resources/config.py` - Module-specific configuration schema
- [x] `src/functions/detection_layer/abandoned_resources/detector.py` - Main detection logic
- [x] Test with dry run
- [x] Test against real subscriptions

## Phase 5: AI Agent Configuration ✅
- [x] `src/agent/__init__.py` - Module init
- [x] `src/agent/system_prompt.txt` - Agent instructions with workflow steps and recommendations
- [x] `src/agent/tool_definitions.json` - OpenAPI-style tool schemas for all endpoints
- [x] `src/agent/run_agent.py` - Orchestration script for local testing and production
- [ ] Configure AI Foundry project (manual Azure portal step)
- [ ] Test agent tool calls (requires deployed infrastructure)

## Phase 6: Notification Layer ✅
- [x] `src/logic-apps/send-optimization-email/workflow.json` - Workflow definition with HTTP trigger
- [x] `src/logic-apps/send-optimization-email/connections.json` - Office 365 connector configuration
- [x] `src/logic-apps/templates/email-template.html` - Professional HTML email template
- [x] `src/functions/function_app.py` - Added `/api/send-optimization-email` endpoint
- [ ] Configure Office 365 connector (manual Azure portal step)
- [ ] Test email delivery (requires deployed infrastructure)

## Phase 7: Detection Targets ✅
- [x] `infra/main.bicep` - Added `detection-targets` Cosmos container (partition key: `/targetId`)
- [x] `src/functions/shared/models.py` - `DetectionTarget` model, `TargetType` enum, `targetType` field in `SubscriptionOwner`
- [x] `src/functions/shared/models.py` - `ModuleInput` updated with `managementGroupIds` field
- [x] `src/functions/shared/cosmos_client.py` - Target methods (`get_enabled_targets`, `get_targets_by_type`, `upsert_target`)
- [x] `src/functions/shared/resource_graph.py` - `get_subscriptions_in_management_group()`, `resolve_targets_to_subscriptions()`
- [x] `src/functions/data_layer/get_detection_targets.py` - Function to retrieve enabled targets
- [x] `src/functions/function_app.py` - `/api/get-detection-targets` HTTP endpoint
- [x] `data/seed/detection-targets.sample.json` - Sample seed data
- [x] `src/agent/tool_definitions.json` - Added `get_detection_targets` tool, updated `abandoned_resources` with `managementGroupIds`
- [x] `src/agent/system_prompt.txt` - Updated to 7-step workflow starting with detection targets
- [x] `src/agent/run_agent.py` - Detection targets workflow, `--management-groups` CLI flag
- [x] `docs/detection-targets.md` - Configuration guide for targets and subscription owners
- [x] `docs/deployment-guide.md` - Added target seeding steps
- [x] `README.md` - Updated diagrams and execution flow
- [x] `CLAUDE.md` - Added detection targets schema

## Phase 8: Consolidate Detection Targets & Subscription Owners 🔄

**Goal:** Merge `detection-targets` and `subscription-owners` containers into a single `detection-targets` container. Support multiple notification email addresses per target.

### Schema Changes
- [ ] `src/functions/shared/models.py` - Update `DetectionTarget` model:
  - Add `ownerEmails: list[str]` (replaces single `ownerEmail`)
  - Add `ownerNames: list[str]` (optional, for email personalization)
  - Add `notificationPreferences: dict` (timezone, language)
  - Remove `SubscriptionOwner` model (no longer needed)
- [ ] `data/seed/detection-targets.sample.json` - Update sample with new fields

### Data Layer Changes
- [ ] `src/functions/shared/cosmos_client.py` - Remove subscription-owners methods
- [ ] `src/functions/data_layer/get_subscription_owners.py` - Delete file
- [ ] `src/functions/data_layer/__init__.py` - Remove get_subscription_owners export
- [ ] `src/functions/function_app.py` - Remove `/api/get-subscription-owners` endpoint
- [ ] `src/functions/function_app.py` - Update `/api/get-detection-targets` to return owner info

### Infrastructure Changes
- [ ] `infra/main.bicep` - Remove `subscription-owners` container from Cosmos DB

### Agent Changes
- [ ] `src/agent/tool_definitions.json` - Remove `get_subscription_owners` tool
- [ ] `src/agent/tool_definitions.json` - Update `get_detection_targets` response schema
- [ ] `src/agent/system_prompt.txt` - Update workflow (remove step to get owners separately)
- [ ] `src/agent/run_agent.py` - Update to use detection targets for owner info

### Notification Layer Changes
- [ ] `src/functions/function_app.py` - Update `send-optimization-email` to handle multiple recipients
- [ ] `src/logic-apps/send-optimization-email/workflow.json` - Support multiple To addresses

### Documentation Changes
- [ ] `docs/detection-targets.md` - Update schema documentation
- [ ] `docs/deployment-guide.md` - Remove subscription-owners seeding steps
- [ ] `docs/api-reference.md` - Remove get-subscription-owners, update get-detection-targets
- [ ] `CLAUDE.md` - Update container list and schema

### Cleanup
- [ ] Remove `data/seed/subscription-owners.sample.json`
- [ ] Run `/scrub` to verify no dead code

## Testing & Validation
- [x] `scripts/test_detector_live.py` - Live detector test against Azure subscriptions
- [x] `scripts/test_data_layer_live.py` - Live data layer test against Cosmos DB
- [ ] Unit test suite
- [ ] Integration test suite
- [ ] E2E test with test subscriptions
- [ ] Dry run across all subscriptions
- [ ] Pilot with subset of subscriptions

## Documentation
- [x] `docs/solution-docs/deployment-guide.md` - Step-by-step deployment instructions
- [x] `docs/solution-docs/detection-targets.md` - Detection targets and subscription owners configuration guide
- [x] `docs/solution-docs/shared-library.md` - Shared library architecture and module integration guide
- [x] `docs/solution-docs/module-contracts.md` - ModuleInput/ModuleOutput schemas and examples
- [x] `docs/solution-docs/module-registration.md` - How to register modules in Cosmos DB
- [x] `docs/solution-docs/api-reference.md` - API endpoint documentation
- [x] `README.md` - Architecture diagrams, execution flow, and project overview
- [x] `CLAUDE.md` - Project instructions for Claude Code
- [x] `docs/project-management/PLAN.md` - Implementation roadmap
- [x] `docs/project-management/SPECIFICATION.md` - Full project specification
- [x] `docs/project-management/STATUS.md` - Implementation status (this file)

## Claude Commands
- [x] `.claude/commands/scrub.md` - Project cleanup and code review command
- [x] `.claude/commands/deploy.md` - Azure infrastructure deployment command

## Blockers & Issues
- None yet

## Technical Debt / Revisit

### `get-subscription-owners` uses POST instead of GET
- **Location:** `function_app.py` line ~150, `tool_definitions.json`
- **Issue:** Endpoint is semantically a read operation but uses POST to accept `subscriptionIds` array in request body
- **Rationale:** POST avoids URL length limits (~2000-8000 chars) when looking up many subscriptions
- **Options:** (1) Keep POST for pragmatism, (2) Change to GET with comma-separated query param, (3) Support both
- **Recommendation:** Revisit if API consistency becomes a priority; current approach works fine

# Implementation Status

> Last Updated: 2026-01-11

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

## Testing & Validation
- [x] `scripts/test_detector_live.py` - Live detector test against Azure subscriptions
- [x] `scripts/test_data_layer_live.py` - Live data layer test against Cosmos DB
- [ ] Unit test suite
- [ ] Integration test suite
- [ ] E2E test with test subscriptions
- [ ] Dry run across all subscriptions
- [ ] Pilot with subset of subscriptions

## Documentation
- [x] `docs/deployment-guide.md` - Step-by-step deployment instructions
- [x] `docs/detection-targets.md` - Detection targets and subscription owners configuration guide
- [x] `docs/shared-library.md` - Shared library architecture and module integration guide
- [x] `docs/module-contracts.md` - ModuleInput/ModuleOutput schemas and examples
- [x] `docs/module-registration.md` - How to register modules in Cosmos DB
- [x] `README.md` - Architecture diagrams, execution flow, and project overview
- [x] `CLAUDE.md` - Project instructions for Claude Code
- [x] `PLAN.md` - Implementation roadmap
- [x] `OptimizationAgent.md` - Original design document

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

## Notes
- **2026-01-11:** Completed Phase 7 Detection Targets. Implemented: `SubscriptionOwner` schema updated with `targetType` field, `ModuleInput` supports `managementGroupIds`, `ResourceGraphClient` has `resolve_targets_to_subscriptions()` and `get_subscriptions_in_management_group()` methods, `get_detection_targets` tool definition added, system prompt updated to 7-step workflow with detection targets, `run_agent.py` updated with `--management-groups` CLI flag and automatic target retrieval from Cosmos DB, CLAUDE.md updated with detection targets schema.
- **2026-01-11:** Completed Phase 7 Data Layer implementation. Added `detection-targets` Cosmos container to Bicep, `DetectionTarget` model and `TargetType` enum to models.py, Cosmos client methods for target operations, `get_detection_targets.py` function, `/api/get-detection-targets` endpoint, and seed data. Created `docs/detection-targets.md` with comprehensive configuration guide for targets and subscription owners. Updated deployment guide with target seeding steps. Updated README with detection targets in architecture diagram, execution flow (now 7 steps), and tool call flow. Scrubbed all docs to remove "200 subscriptions" references - now uses generic "target subscriptions and management groups" language.
- **2026-01-11:** Added Phase 7 Detection Targets feature plan. Supports multiple subscriptions and/or management groups with mixed targeting. Different targets can belong to different teams via subscription-owners. Email reports will include per-subscription breakdowns with costs and findings details.
- **2026-01-10:** Added deployment guide (`docs/deployment-guide.md`) with step-by-step instructions for Bicep, Function App, Logic App, and AI Agent deployment.
- **2026-01-10:** Completed Phase 6 Notification Layer. Created `src/logic-apps/send-optimization-email/` with: `workflow.json` (Logic App workflow with HTTP trigger and Office 365 email action), `connections.json` (Office 365 connector config). Created `email-template.html` with professional styling, trend messaging, and findings display. Added `/api/send-optimization-email` endpoint to function_app.py that forwards requests to Logic App and adds resource-specific recommendations. Remaining manual steps: configure Office 365 connector in Azure portal and test email delivery.
- **2026-01-10:** Ran `/scrub` - removed 4 unused imports from `run_agent.py` (AgentThread, FunctionTool, MessageRole, ToolSet). Updated PLAN.md directory structure to match actual implementation (detection_layer now has abandoned_resources subdirectory with separate files for queries, config, confidence, cost_calculator). Added get_findings_trends.py to PLAN.md. Removed specific "200 subscriptions" reference from PLAN.md. All imports verified working. No sensitive data in repo.
- **2026-01-10:** Completed Phase 5 AI Agent Configuration. Created `src/agent/` directory with: `system_prompt.txt` (agent instructions with 6-step workflow), `tool_definitions.json` (OpenAPI-style schemas for all 8 endpoints), and `run_agent.py` (orchestration script using Azure AI Foundry SDK with CLI args for --dry-run and --subscriptions). Remaining manual steps: configure AI Foundry project in Azure portal and test agent tool calls.
- **2026-01-10:** Added `get-findings-trends` endpoint for month-over-month analysis. Module-agnostic design works for any detection module. Enables AI agent to add historical context to notifications (e.g., "Findings decreased from 50 to 22, great progress!"). Added `get_findings_for_trends()` to CosmosClient. Updated README execution flow and module-contracts.md with trends schema.
- **2026-01-10:** Added comprehensive documentation - `module-contracts.md` (ModuleInput/ModuleOutput schemas), `module-registration.md` (Cosmos DB registration guide). Updated README with architecture diagrams, expanded execution flow showing AI agent reasoning, and project overview.
- **2026-01-10:** Completed Phase 3 Data Layer - added `function_app.py` with HTTP triggers for all endpoints (`/api/get-module-registry`, `/api/save-findings`, `/api/get-findings-history`, `/api/get-subscription-owners`, `/api/abandoned-resources`, `/api/health`). Created data_layer module with 4 functions. Added `get_all_modules()` and `get_findings_by_subscription_and_status()` to CosmosClient. Created seed data files for module registry and sample subscription owners.
- **2026-01-10:** Ran `/scrub` - removed 2 unused imports (PartitionKey, get_confidence_level), fixed load balancer KQL query (`== null` → `isnull()`), added `from __future__ import annotations` for Python 3.9 compatibility. All ruff checks pass. Verified live detection against Azure subscription - found 1 unused public IP. Phase 4 complete.
- **2026-01-10:** Completed `detector.py` - main detection orchestration that wires together queries, confidence scoring, and cost estimation. Implements module interface contract (ModuleInput → ModuleOutput). Added `detect()` and `detect_from_dict()` entry points. Also exported `ModuleSummary` from shared library.
- **2026-01-09:** Refactored confidence scoring to maintain modularity. Generic utilities in `shared/confidence.py`, module-specific logic (name patterns, tag checks, orphan duration) moved to `detection_layer/abandoned_resources/confidence.py`. Future modules (e.g., Overprovisioned VMs) can implement their own confidence logic.
- **2026-01-09:** Refactored cost calculator similarly. Generic severity classification and aggregation utilities remain in `shared/cost_calculator.py`. Resource-type-specific pricing (ABANDONED_RESOURCE_COSTS lookup table, estimate_abandoned_resource_cost) moved to `detection_layer/abandoned_resources/cost_calculator.py`.
- **2026-01-09:** Refactored resource_graph.py. Generic ResourceGraphClient (query, query_batched, query_single) remains in shared. All 8 KQL queries moved to `detection_layer/abandoned_resources/queries.py`. Future modules can define their own queries (e.g., VM metrics queries for overprovisioned detection).
- **2026-01-09:** Refactored ModuleConfiguration out of shared/models.py. `ModuleRegistry.configuration` is now `dict[str, Any]` (opaque to shared library). Each module defines its own config schema - see `detection_layer/abandoned_resources/config.py` for AbandonedResourcesConfig with resource_types, minimum_orphan_age_days, etc.

# Implementation Status

> Last Updated: 2026-01-10

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

## Phase 5: AI Agent Configuration
- [ ] `src/agent/system_prompt.txt` - Agent instructions
- [ ] `src/agent/tool_definitions.json` - Tool schemas
- [ ] `src/agent/run_agent.py` - Orchestration script
- [ ] Configure AI Foundry project
- [ ] Test agent tool calls

## Phase 6: Notification Layer
- [ ] `src/logic-apps/send-optimization-email/workflow.json` - Workflow definition
- [ ] `src/logic-apps/templates/email-template.html` - Email template
- [ ] Configure Office 365 connector
- [ ] Test email delivery

## Testing & Validation
- [x] `scripts/test_detector_live.py` - Live detector test against Azure subscriptions
- [x] `scripts/test_data_layer_live.py` - Live data layer test against Cosmos DB
- [ ] Unit test suite
- [ ] Integration test suite
- [ ] E2E test with test subscriptions
- [ ] Dry run across all subscriptions
- [ ] Pilot with subset of subscriptions

## Documentation
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

## Notes
- **2026-01-10:** Added comprehensive documentation - `module-contracts.md` (ModuleInput/ModuleOutput schemas), `module-registration.md` (Cosmos DB registration guide). Updated README with architecture diagrams, expanded execution flow showing AI agent reasoning, and project overview.
- **2026-01-10:** Completed Phase 3 Data Layer - added `function_app.py` with HTTP triggers for all endpoints (`/api/get-module-registry`, `/api/save-findings`, `/api/get-findings-history`, `/api/get-subscription-owners`, `/api/abandoned-resources`, `/api/health`). Created data_layer module with 4 functions. Added `get_all_modules()` and `get_findings_by_subscription_and_status()` to CosmosClient. Created seed data files for module registry and sample subscription owners.
- **2026-01-10:** Ran `/scrub` - removed 2 unused imports (PartitionKey, get_confidence_level), fixed load balancer KQL query (`== null` → `isnull()`), added `from __future__ import annotations` for Python 3.9 compatibility. All ruff checks pass. Verified live detection against Azure subscription - found 1 unused public IP. Phase 4 complete.
- **2026-01-10:** Completed `detector.py` - main detection orchestration that wires together queries, confidence scoring, and cost estimation. Implements module interface contract (ModuleInput → ModuleOutput). Added `detect()` and `detect_from_dict()` entry points. Also exported `ModuleSummary` from shared library.
- **2026-01-09:** Refactored confidence scoring to maintain modularity. Generic utilities in `shared/confidence.py`, module-specific logic (name patterns, tag checks, orphan duration) moved to `detection_layer/abandoned_resources/confidence.py`. Future modules (e.g., Overprovisioned VMs) can implement their own confidence logic.
- **2026-01-09:** Refactored cost calculator similarly. Generic severity classification and aggregation utilities remain in `shared/cost_calculator.py`. Resource-type-specific pricing (ABANDONED_RESOURCE_COSTS lookup table, estimate_abandoned_resource_cost) moved to `detection_layer/abandoned_resources/cost_calculator.py`.
- **2026-01-09:** Refactored resource_graph.py. Generic ResourceGraphClient (query, query_batched, query_single) remains in shared. All 8 KQL queries moved to `detection_layer/abandoned_resources/queries.py`. Future modules can define their own queries (e.g., VM metrics queries for overprovisioned detection).
- **2026-01-09:** Refactored ModuleConfiguration out of shared/models.py. `ModuleRegistry.configuration` is now `dict[str, Any]` (opaque to shared library). Each module defines its own config schema - see `detection_layer/abandoned_resources/config.py` for AbandonedResourcesConfig with resource_types, minimum_orphan_age_days, etc.

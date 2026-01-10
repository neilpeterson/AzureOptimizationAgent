"""Azure Functions entry point for the Optimization Agent.

This module registers all HTTP triggers for the Data Layer and Detection Layer.
"""

from __future__ import annotations

import json
import logging

import azure.functions as func

from data_layer.get_module_registry import get_module_registry
from data_layer.save_findings import save_findings
from data_layer.get_findings_history import get_findings_history
from data_layer.get_subscription_owners import get_subscription_owners
from detection_layer.abandoned_resources import detect_from_dict

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)
logger = logging.getLogger(__name__)


# =============================================================================
# Data Layer Endpoints
# =============================================================================


@app.route(route="get-module-registry", methods=["GET"])
def get_module_registry_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get all enabled modules from the registry.

    GET /api/get-module-registry
    Query params:
        - include_disabled: bool (optional) - Include disabled modules

    Returns:
        200: List of module registry entries
        500: Error response
    """
    try:
        include_disabled = req.params.get("include_disabled", "false").lower() == "true"
        result = get_module_registry(include_disabled=include_disabled)
        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error getting module registry")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="save-findings", methods=["POST"])
def save_findings_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Save findings to the findings-history container.

    POST /api/save-findings
    Body:
        {
            "executionId": "exec-001",
            "moduleId": "abandoned-resources",
            "findings": [...]
        }

    Returns:
        200: Success with count of saved findings
        400: Invalid request body
        500: Error response
    """
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            mimetype="application/json",
            status_code=400,
        )

    try:
        execution_id = body.get("executionId")
        module_id = body.get("moduleId")
        findings = body.get("findings", [])

        if not execution_id or not module_id:
            return func.HttpResponse(
                json.dumps({"error": "executionId and moduleId are required"}),
                mimetype="application/json",
                status_code=400,
            )

        result = save_findings(
            execution_id=execution_id,
            module_id=module_id,
            findings=findings,
        )
        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error saving findings")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="get-findings-history", methods=["GET"])
def get_findings_history_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get findings history for trend analysis.

    GET /api/get-findings-history
    Query params:
        - subscription_id: str (required) - Subscription to query
        - limit: int (optional) - Max results (default 100)
        - status: str (optional) - Filter by status (open, resolved)

    Returns:
        200: List of historical findings
        400: Missing required parameters
        500: Error response
    """
    subscription_id = req.params.get("subscription_id")
    if not subscription_id:
        return func.HttpResponse(
            json.dumps({"error": "subscription_id is required"}),
            mimetype="application/json",
            status_code=400,
        )

    try:
        limit = int(req.params.get("limit", "100"))
        status = req.params.get("status")

        result = get_findings_history(
            subscription_id=subscription_id,
            limit=limit,
            status=status,
        )
        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error getting findings history")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )


@app.route(route="get-subscription-owners", methods=["POST"])
def get_subscription_owners_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get subscription owner information for notifications.

    POST /api/get-subscription-owners
    Body:
        {
            "subscriptionIds": ["sub-1", "sub-2"]
        }

    Returns:
        200: List of subscription owner mappings
        400: Invalid request body
        500: Error response
    """
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            mimetype="application/json",
            status_code=400,
        )

    try:
        subscription_ids = body.get("subscriptionIds", [])
        if not subscription_ids:
            return func.HttpResponse(
                json.dumps({"error": "subscriptionIds is required"}),
                mimetype="application/json",
                status_code=400,
            )

        result = get_subscription_owners(subscription_ids=subscription_ids)
        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error getting subscription owners")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )


# =============================================================================
# Detection Layer Endpoints
# =============================================================================


@app.route(route="abandoned-resources", methods=["POST"])
def abandoned_resources_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Run the abandoned resources detection module.

    POST /api/abandoned-resources
    Body:
        {
            "executionId": "exec-001",
            "subscriptionIds": ["sub-1", "sub-2"],
            "configuration": {},
            "dryRun": false
        }

    Returns:
        200: Module output with findings and summary
        400: Invalid request body
        500: Error response
    """
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            mimetype="application/json",
            status_code=400,
        )

    try:
        if not body.get("executionId") or not body.get("subscriptionIds"):
            return func.HttpResponse(
                json.dumps({"error": "executionId and subscriptionIds are required"}),
                mimetype="application/json",
                status_code=400,
            )

        result = detect_from_dict(body)
        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error running abandoned resources detection")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )


# =============================================================================
# Health Check
# =============================================================================


@app.route(route="health", methods=["GET"])
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint.

    GET /api/health

    Returns:
        200: Service is healthy
    """
    return func.HttpResponse(
        json.dumps({"status": "healthy", "service": "optimization-agent"}),
        mimetype="application/json",
        status_code=200,
    )

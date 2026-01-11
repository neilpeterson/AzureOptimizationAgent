"""Azure Functions entry point for the Optimization Agent.

This module registers all HTTP triggers for the Data Layer and Detection Layer.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import urllib.error

import azure.functions as func

from data_layer.get_module_registry import get_module_registry
from data_layer.save_findings import save_findings
from data_layer.get_findings_history import get_findings_history
from data_layer.get_findings_trends import get_findings_trends
from data_layer.get_subscription_owners import get_subscription_owners
from data_layer.get_detection_targets import get_detection_targets
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


@app.route(route="get-findings-trends", methods=["GET"])
def get_findings_trends_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get month-over-month findings trends for any detection module.

    GET /api/get-findings-trends
    Query params:
        - module_id: str (required) - Module ID (e.g., 'abandoned-resources')
        - months: int (optional) - Number of months to analyze (default: 3)
        - subscription_id: str (optional) - Filter to specific subscription

    Returns:
        200: Trend data with monthly aggregates and change summary
        400: Missing required parameters
        500: Error response

    Example response:
        {
            "moduleId": "abandoned-resources",
            "trends": [
                {"month": "2026-01", "totalFindings": 22, "totalCost": 850.00, ...},
                {"month": "2025-12", "totalFindings": 50, "totalCost": 1920.00, ...}
            ],
            "summary": {
                "hasComparison": true,
                "findingsChange": -28,
                "findingsChangePercent": -56.0,
                "trend": "improving",
                "message": "Great progress! Findings decreased from 50 to 22..."
            }
        }
    """
    module_id = req.params.get("module_id")
    if not module_id:
        return func.HttpResponse(
            json.dumps({"error": "module_id is required"}),
            mimetype="application/json",
            status_code=400,
        )

    try:
        months = int(req.params.get("months", "3"))
        subscription_id = req.params.get("subscription_id")

        result = get_findings_trends(
            module_id=module_id,
            months=months,
            subscription_id=subscription_id,
        )
        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error getting findings trends")
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


@app.route(route="get-detection-targets", methods=["GET"])
def get_detection_targets_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Get detection targets (subscriptions and management groups to scan).

    GET /api/get-detection-targets
    Query params:
        - include_disabled: bool (optional) - Include disabled targets
        - target_type: str (optional) - Filter by type ('subscription' or 'managementGroup')

    Returns:
        200: List of detection targets with counts
        500: Error response

    Example response:
        {
            "targets": [
                {"targetId": "sub-123", "targetType": "subscription", "displayName": "Production", ...},
                {"targetId": "mg-corp", "targetType": "managementGroup", "displayName": "Corporate", ...}
            ],
            "count": 2,
            "subscriptionCount": 1,
            "managementGroupCount": 1
        }
    """
    try:
        include_disabled = req.params.get("include_disabled", "false").lower() == "true"
        target_type = req.params.get("target_type")

        result = get_detection_targets(
            include_disabled=include_disabled,
            target_type=target_type,
        )
        return func.HttpResponse(
            json.dumps(result, default=str),
            mimetype="application/json",
            status_code=200,
        )
    except Exception as e:
        logger.exception("Error getting detection targets")
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
# Notification Layer Endpoints
# =============================================================================


@app.route(route="send-optimization-email", methods=["POST"])
def send_optimization_email_handler(req: func.HttpRequest) -> func.HttpResponse:
    """Send optimization report email via Logic App.

    POST /api/send-optimization-email
    Body:
        {
            "ownerEmail": "owner@example.com",
            "ownerName": "John Doe",
            "subscriptionId": "sub-123",
            "subscriptionName": "Production",
            "findings": [...],
            "trends": {...},
            "totalEstimatedMonthlyCost": 500.00
        }

    Returns:
        200: Email sent successfully
        400: Invalid request body
        500: Error sending email
        503: Logic App URL not configured
    """
    logic_app_url = os.environ.get("LOGIC_APP_URL")
    if not logic_app_url:
        return func.HttpResponse(
            json.dumps({"error": "LOGIC_APP_URL environment variable not configured"}),
            mimetype="application/json",
            status_code=503,
        )

    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            mimetype="application/json",
            status_code=400,
        )

    # Validate required fields
    if not body.get("ownerEmail") or not body.get("subscriptionId") or not body.get("findings"):
        return func.HttpResponse(
            json.dumps({"error": "ownerEmail, subscriptionId, and findings are required"}),
            mimetype="application/json",
            status_code=400,
        )

    # Add recommendations to findings if not present
    findings_with_recommendations = []
    for finding in body.get("findings", []):
        if "recommendation" not in finding:
            finding["recommendation"] = _get_recommendation(finding.get("resourceType", ""))
        findings_with_recommendations.append(finding)
    body["findings"] = findings_with_recommendations

    try:
        # Forward request to Logic App
        request_data = json.dumps(body).encode("utf-8")
        request_obj = urllib.request.Request(
            logic_app_url,
            data=request_data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        with urllib.request.urlopen(request_obj, timeout=30) as response:
            response_data = response.read().decode("utf-8")
            return func.HttpResponse(
                response_data,
                mimetype="application/json",
                status_code=response.status,
            )
    except urllib.error.HTTPError as e:
        logger.exception("Logic App returned error")
        return func.HttpResponse(
            json.dumps({"error": f"Logic App error: {e.code}"}),
            mimetype="application/json",
            status_code=500,
        )
    except urllib.error.URLError as e:
        logger.exception("Failed to connect to Logic App")
        return func.HttpResponse(
            json.dumps({"error": f"Connection error: {e.reason}"}),
            mimetype="application/json",
            status_code=500,
        )
    except Exception as e:
        logger.exception("Error sending optimization email")
        return func.HttpResponse(
            json.dumps({"error": str(e)}),
            mimetype="application/json",
            status_code=500,
        )


def _get_recommendation(resource_type: str) -> str:
    """Get recommendation text based on resource type."""
    recommendations = {
        "microsoft.compute/disks": (
            "Consider deleting this disk or attaching it to a VM. "
            "If needed for backup, consider using snapshots instead."
        ),
        "microsoft.network/publicipaddresses": (
            "Delete this IP if no longer needed, or associate it with "
            "a resource to avoid charges."
        ),
        "microsoft.network/loadbalancers": (
            "Remove this load balancer or configure backend pools."
        ),
        "microsoft.network/natgateways": (
            "Delete or associate with a subnet."
        ),
        "microsoft.sql/servers/elasticpools": (
            "Remove or add databases to the pool."
        ),
        "microsoft.network/virtualnetworkgateways": (
            "Delete if VPN/ExpressRoute connectivity is no longer needed."
        ),
        "microsoft.network/ddosprotectionplans": (
            "Delete or associate with virtual networks."
        ),
        "microsoft.network/privateendpoints": (
            "Reconnect to target resource or delete."
        ),
    }
    return recommendations.get(
        resource_type.lower(),
        "Review this resource and delete if no longer needed."
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

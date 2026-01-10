#!/usr/bin/env python3
"""Run the Azure Optimization Agent.

This script demonstrates how to invoke the AI agent using Azure AI Foundry.
It can be used for local testing or as a template for production deployment.

Prerequisites:
    1. Azure CLI logged in: `az login`
    2. Azure AI Foundry project configured
    3. Environment variables set (see below)

Environment Variables:
    AZURE_AI_PROJECT_CONNECTION_STRING: AI Foundry project connection string
    FUNCTION_APP_URL: Base URL of the deployed Function App
    FUNCTION_APP_KEY: Function App host key for authentication

Usage:
    # Run with default subscriptions from environment
    python src/agent/run_agent.py

    # Run with specific subscriptions
    python src/agent/run_agent.py --subscriptions sub-1,sub-2,sub-3

    # Dry run (no notifications sent)
    python src/agent/run_agent.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Azure AI Foundry imports
try:
    from azure.ai.projects import AIProjectClient
    from azure.ai.projects.models import (
        AgentThread,
        FunctionTool,
        MessageRole,
        ToolSet,
    )
    from azure.identity import DefaultAzureCredential
except ImportError:
    print("Error: Azure AI Foundry SDK not installed.")
    print("Install with: pip install azure-ai-projects azure-identity")
    sys.exit(1)

import requests


def load_system_prompt() -> str:
    """Load the system prompt from file."""
    prompt_path = Path(__file__).parent / "system_prompt.txt"
    with open(prompt_path) as f:
        return f.read()


def load_tool_definitions() -> list[dict[str, Any]]:
    """Load tool definitions from JSON file."""
    tools_path = Path(__file__).parent / "tool_definitions.json"
    with open(tools_path) as f:
        data = json.load(f)
    return data["tools"]


class OptimizationAgentRunner:
    """Runner for the Azure Optimization Agent."""

    def __init__(
        self,
        function_app_url: str | None = None,
        function_app_key: str | None = None,
        project_connection_string: str | None = None,
    ):
        """Initialize the agent runner.

        Args:
            function_app_url: Base URL of the Function App (e.g., https://func-xxx.azurewebsites.net)
            function_app_key: Function App host key for authentication
            project_connection_string: Azure AI Foundry project connection string
        """
        self.function_app_url = function_app_url or os.environ.get("FUNCTION_APP_URL")
        self.function_app_key = function_app_key or os.environ.get("FUNCTION_APP_KEY")
        self.project_connection_string = project_connection_string or os.environ.get(
            "AZURE_AI_PROJECT_CONNECTION_STRING"
        )

        if not self.function_app_url:
            raise ValueError("FUNCTION_APP_URL environment variable or parameter required")

        # Initialize Azure AI Project client
        if self.project_connection_string:
            self.credential = DefaultAzureCredential()
            self.project_client = AIProjectClient.from_connection_string(
                conn_str=self.project_connection_string,
                credential=self.credential,
            )
        else:
            self.project_client = None
            print("Warning: No AI project connection string. Running in local/test mode.")

    def _call_function(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Execute a function tool call against the Function App.

        Args:
            name: Function name (maps to API endpoint)
            arguments: Function arguments

        Returns:
            Function response as dict
        """
        # Map function names to HTTP methods and endpoints
        endpoint_map = {
            "get_module_registry": ("GET", "/api/get-module-registry"),
            "save_findings": ("POST", "/api/save-findings"),
            "get_findings_history": ("GET", "/api/get-findings-history"),
            "get_findings_trends": ("GET", "/api/get-findings-trends"),
            "get_subscription_owners": ("POST", "/api/get-subscription-owners"),
            "abandoned_resources": ("POST", "/api/abandoned-resources"),
            "send_optimization_email": ("POST", "/api/send-optimization-email"),
            "health_check": ("GET", "/api/health"),
        }

        if name not in endpoint_map:
            return {"error": f"Unknown function: {name}"}

        method, path = endpoint_map[name]
        url = f"{self.function_app_url}{path}"

        headers = {"Content-Type": "application/json"}
        if self.function_app_key:
            headers["x-functions-key"] = self.function_app_key

        try:
            if method == "GET":
                # Convert arguments to query parameters
                response = requests.get(url, params=arguments, headers=headers, timeout=120)
            else:
                response = requests.post(url, json=arguments, headers=headers, timeout=120)

            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            return {"error": str(e)}

    def run(
        self,
        subscription_ids: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run the optimization agent workflow.

        Args:
            subscription_ids: List of subscription IDs to scan (optional)
            dry_run: If True, skip notifications

        Returns:
            Execution summary
        """
        execution_id = f"exec-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-001"
        print(f"Starting optimization run: {execution_id}")

        results = {
            "executionId": execution_id,
            "modulesExecuted": [],
            "totalFindings": 0,
            "totalEstimatedMonthlySavings": 0.0,
            "subscriptionsNotified": 0,
            "errors": [],
        }

        # Step 1: Get enabled modules
        print("\n[Step 1] Getting enabled modules...")
        modules_response = self._call_function("get_module_registry", {})
        if "error" in modules_response:
            results["errors"].append(f"Failed to get modules: {modules_response['error']}")
            return results

        modules = modules_response.get("modules", [])
        print(f"  Found {len(modules)} enabled modules")

        # Step 2: Run each detection module
        all_findings = []
        for module in modules:
            module_id = module.get("moduleId")
            print(f"\n[Step 2] Running detection: {module_id}")

            detection_args = {
                "executionId": execution_id,
                "subscriptionIds": subscription_ids or [],
                "configuration": module.get("configuration", {}),
                "dryRun": dry_run,
            }

            detection_response = self._call_function(module_id.replace("-", "_"), detection_args)
            if "error" in detection_response:
                results["errors"].append(f"Detection failed for {module_id}: {detection_response['error']}")
                continue

            findings = detection_response.get("findings", [])
            summary = detection_response.get("summary", {})
            print(f"  Found {len(findings)} findings, ${summary.get('totalEstimatedMonthlySavings', 0):.2f}/month")

            all_findings.extend(findings)
            results["modulesExecuted"].append(module_id)
            results["totalFindings"] += len(findings)
            results["totalEstimatedMonthlySavings"] += summary.get("totalEstimatedMonthlySavings", 0)

        # Step 3: Save findings
        if all_findings and not dry_run:
            print(f"\n[Step 3] Saving {len(all_findings)} findings...")
            save_response = self._call_function("save_findings", {
                "executionId": execution_id,
                "moduleId": "combined",
                "findings": all_findings,
            })
            if "error" in save_response:
                results["errors"].append(f"Failed to save findings: {save_response['error']}")

        # Step 4: Get trends
        print("\n[Step 4] Getting historical trends...")
        trends_by_module = {}
        for module_id in results["modulesExecuted"]:
            trends_response = self._call_function("get_findings_trends", {"module_id": module_id})
            if "error" not in trends_response:
                trends_by_module[module_id] = trends_response.get("summary", {})
                trend = trends_by_module[module_id].get("trend", "unknown")
                print(f"  {module_id}: {trend}")

        # Step 5: Get subscription owners
        if all_findings:
            subscription_ids_with_findings = list(set(f.get("subscriptionId") for f in all_findings))
            print(f"\n[Step 5] Getting owners for {len(subscription_ids_with_findings)} subscriptions...")

            owners_response = self._call_function("get_subscription_owners", {
                "subscriptionIds": subscription_ids_with_findings
            })
            owners = owners_response.get("owners", [])
            print(f"  Found {len(owners)} owners")

            # Step 6: Send notifications (skip if dry run)
            if not dry_run:
                print("\n[Step 6] Sending notifications...")
                for owner in owners:
                    owner_findings = [
                        f for f in all_findings
                        if f.get("subscriptionId") == owner.get("subscriptionId")
                    ]
                    if owner_findings:
                        email_response = self._call_function("send_optimization_email", {
                            "ownerEmail": owner.get("ownerEmail"),
                            "ownerName": owner.get("ownerName"),
                            "subscriptionId": owner.get("subscriptionId"),
                            "subscriptionName": owner.get("subscriptionName"),
                            "findings": owner_findings,
                            "trends": trends_by_module.get("abandoned-resources", {}),
                            "totalEstimatedMonthlyCost": sum(
                                f.get("estimatedMonthlyCost", 0) for f in owner_findings
                            ),
                        })
                        if "error" not in email_response:
                            results["subscriptionsNotified"] += 1
                        else:
                            results["errors"].append(
                                f"Failed to notify {owner.get('ownerEmail')}: {email_response['error']}"
                            )
                print(f"  Notified {results['subscriptionsNotified']} subscription owners")
            else:
                print("\n[Step 6] Skipping notifications (dry run)")

        # Summary
        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"  Execution ID: {results['executionId']}")
        print(f"  Modules executed: {len(results['modulesExecuted'])}")
        print(f"  Total findings: {results['totalFindings']}")
        print(f"  Estimated monthly savings: ${results['totalEstimatedMonthlySavings']:.2f}")
        print(f"  Subscriptions notified: {results['subscriptionsNotified']}")
        if results["errors"]:
            print(f"  Errors: {len(results['errors'])}")
            for error in results["errors"]:
                print(f"    - {error}")

        return results


def main():
    parser = argparse.ArgumentParser(description="Run the Azure Optimization Agent")
    parser.add_argument(
        "--subscriptions",
        help="Comma-separated list of subscription IDs to scan",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run detection but skip saving and notifications",
    )
    parser.add_argument(
        "--function-url",
        help="Function App URL (default: FUNCTION_APP_URL env var)",
    )
    args = parser.parse_args()

    subscription_ids = None
    if args.subscriptions:
        subscription_ids = [s.strip() for s in args.subscriptions.split(",")]

    try:
        runner = OptimizationAgentRunner(function_app_url=args.function_url)
        results = runner.run(
            subscription_ids=subscription_ids,
            dry_run=args.dry_run,
        )
        sys.exit(0 if not results["errors"] else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

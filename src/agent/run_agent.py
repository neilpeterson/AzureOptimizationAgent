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
            "get_detection_targets": ("GET", "/api/get-detection-targets"),
            "get_module_registry": ("GET", "/api/get-module-registry"),
            "save_findings": ("POST", "/api/save-findings"),
            "get_findings_history": ("GET", "/api/get-findings-history"),
            "get_findings_trends": ("GET", "/api/get-findings-trends"),
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
        management_group_ids: list[str] | None = None,
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Run the optimization agent workflow.

        Args:
            subscription_ids: List of subscription IDs to scan (optional)
            management_group_ids: List of management group IDs to scan (optional)
            dry_run: If True, skip notifications

        Returns:
            Execution summary
        """
        execution_id = f"exec-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-001"
        print(f"Starting optimization run: {execution_id}")

        results = {
            "executionId": execution_id,
            "targetsScanned": {"subscriptions": 0, "managementGroups": 0},
            "modulesExecuted": [],
            "totalFindings": 0,
            "totalEstimatedMonthlySavings": 0.0,
            "subscriptionsNotified": 0,
            "errors": [],
        }

        # Step 1: Get detection targets (if not provided via CLI)
        # Targets include owner info (ownerEmails, ownerNames, notificationPreferences)
        targets = []
        if not subscription_ids and not management_group_ids:
            print("\n[Step 1] Getting detection targets...")
            targets_response = self._call_function("get_detection_targets", {})
            if "error" in targets_response:
                results["errors"].append(f"Failed to get targets: {targets_response['error']}")
                return results

            targets = targets_response.get("targets", [])
            subscription_ids = [
                t["targetId"] for t in targets if t.get("targetType") == "subscription"
            ]
            management_group_ids = [
                t["targetId"] for t in targets if t.get("targetType") == "managementGroup"
            ]
            print(f"  Found {len(subscription_ids)} subscriptions and {len(management_group_ids)} management groups")
        else:
            print("\n[Step 1] Using provided targets...")
            print(f"  {len(subscription_ids or [])} subscriptions, {len(management_group_ids or [])} management groups")

        results["targetsScanned"]["subscriptions"] = len(subscription_ids or [])
        results["targetsScanned"]["managementGroups"] = len(management_group_ids or [])

        # Step 2: Get enabled modules
        print("\n[Step 2] Getting enabled modules...")
        modules_response = self._call_function("get_module_registry", {})
        if "error" in modules_response:
            results["errors"].append(f"Failed to get modules: {modules_response['error']}")
            return results

        modules = modules_response.get("modules", [])
        print(f"  Found {len(modules)} enabled modules")

        # Step 3: Run each detection module
        all_findings = []
        for module in modules:
            module_id = module.get("moduleId")
            print(f"\n[Step 3] Running detection: {module_id}")

            detection_args = {
                "executionId": execution_id,
                "subscriptionIds": subscription_ids or [],
                "managementGroupIds": management_group_ids or [],
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

        # Step 4: Save findings
        if all_findings and not dry_run:
            print(f"\n[Step 4] Saving {len(all_findings)} findings...")
            save_response = self._call_function("save_findings", {
                "executionId": execution_id,
                "moduleId": "combined",
                "findings": all_findings,
            })
            if "error" in save_response:
                results["errors"].append(f"Failed to save findings: {save_response['error']}")

        # Step 5: Get trends
        print("\n[Step 5] Getting historical trends...")
        trends_by_module = {}
        for module_id in results["modulesExecuted"]:
            trends_response = self._call_function("get_findings_trends", {"module_id": module_id})
            if "error" not in trends_response:
                trends_by_module[module_id] = trends_response.get("summary", {})
                trend = trends_by_module[module_id].get("trend", "unknown")
                print(f"  {module_id}: {trend}")

        # Step 6: Send notifications (using owner info from detection targets)
        if all_findings and targets:
            subscription_ids_with_findings = list(set(f.get("subscriptionId") for f in all_findings))
            # Build a map of target ID to target (with owner info)
            target_map = {t["targetId"]: t for t in targets}

            if not dry_run:
                print(f"\n[Step 6] Sending notifications to {len(subscription_ids_with_findings)} targets...")
                for sub_id in subscription_ids_with_findings:
                    target = target_map.get(sub_id, {})
                    owner_emails = target.get("ownerEmails", [])
                    owner_names = target.get("ownerNames", [])

                    if not owner_emails:
                        results["errors"].append(f"No owner emails for target {sub_id}")
                        continue

                    target_findings = [
                        f for f in all_findings
                        if f.get("subscriptionId") == sub_id
                    ]
                    if target_findings:
                        email_response = self._call_function("send_optimization_email", {
                            "ownerEmails": owner_emails,
                            "ownerNames": owner_names,
                            "subscriptionId": sub_id,
                            "subscriptionName": target.get("displayName", sub_id),
                            "findings": target_findings,
                            "trends": trends_by_module.get("abandoned-resources", {}),
                            "totalEstimatedMonthlyCost": sum(
                                f.get("estimatedMonthlyCost", 0) for f in target_findings
                            ),
                        })
                        if "error" not in email_response:
                            results["subscriptionsNotified"] += 1
                        else:
                            results["errors"].append(
                                f"Failed to notify {owner_emails}: {email_response['error']}"
                            )
                print(f"  Notified {results['subscriptionsNotified']} subscription owners")
            else:
                print("\n[Step 6] Skipping notifications (dry run)")

        # Summary
        print("\n" + "=" * 60)
        print("EXECUTION SUMMARY")
        print("=" * 60)
        print(f"  Execution ID: {results['executionId']}")
        print(f"  Targets scanned: {results['targetsScanned']['subscriptions']} subscriptions, "
              f"{results['targetsScanned']['managementGroups']} management groups")
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
        "--management-groups",
        help="Comma-separated list of management group IDs to scan",
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

    management_group_ids = None
    if args.management_groups:
        management_group_ids = [m.strip() for m in args.management_groups.split(",")]

    try:
        runner = OptimizationAgentRunner(function_app_url=args.function_url)
        results = runner.run(
            subscription_ids=subscription_ids,
            management_group_ids=management_group_ids,
            dry_run=args.dry_run,
        )
        sys.exit(0 if not results["errors"] else 1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

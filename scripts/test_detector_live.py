#!/usr/bin/env python3
"""Live test script for the abandoned resources detector.

Prerequisites:
    1. Azure CLI logged in: `az login`
    2. Python dependencies installed: `pip install -r src/functions/requirements.txt`

Usage:
    python scripts/test_detector_live.py <subscription-id>
    python scripts/test_detector_live.py <subscription-id> --all-types
    python scripts/test_detector_live.py  # Uses current subscription from az cli
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Add src/functions to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "functions"))

from detection_layer.abandoned_resources import detect
from shared import ModuleInput


def get_current_subscription() -> str:
    """Get current subscription from Azure CLI."""
    try:
        result = subprocess.run(
            ["az", "account", "show", "--query", "id", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("Error: Could not get current subscription. Run 'az login' first.")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Test abandoned resources detector")
    parser.add_argument(
        "subscription_id",
        nargs="?",
        help="Azure subscription ID (defaults to current az cli subscription)",
    )
    parser.add_argument(
        "--all-types",
        action="store_true",
        help="Scan all 8 resource types (default: disks only)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON instead of formatted text",
    )
    args = parser.parse_args()

    # Get subscription ID
    subscription_id = args.subscription_id or get_current_subscription()
    print(f"Testing against subscription: {subscription_id}\n")

    # Configure resource types
    if args.all_types:
        resource_types = [
            "microsoft.compute/disks",
            "microsoft.network/publicipaddresses",
            "microsoft.network/loadbalancers",
            "microsoft.network/natgateways",
            "microsoft.sql/servers/elasticpools",
            "microsoft.network/virtualnetworkgateways",
            "microsoft.network/ddosprotectionplans",
            "microsoft.network/privateendpoints",
        ]
    else:
        resource_types = ["microsoft.compute/disks"]
        print("Scanning disks only. Use --all-types to scan all resource types.\n")

    # Run detection
    print("Running detection...")
    print("-" * 60)

    result = detect(
        ModuleInput(
            executionId="test-live-001",
            subscriptionIds=[subscription_id],
            configuration={"resourceTypes": resource_types},
            dryRun=False,
        )
    )

    # Output results
    if args.json:
        print(json.dumps(result.model_dump(by_alias=True), indent=2, default=str))
        return

    print(f"\nStatus: {result.status}")
    print(f"Execution ID: {result.execution_id}")
    print(f"Subscriptions Scanned: {result.subscriptions_scanned}")
    print(f"Total Findings: {len(result.findings)}")
    print(
        f"Estimated Monthly Savings: ${result.summary.total_estimated_monthly_savings:.2f}"
    )

    if result.errors:
        print(f"\nErrors ({len(result.errors)}):")
        for error in result.errors:
            print(f"  - {error}")

    if result.summary.findings_by_severity:
        print(f"\nFindings by Severity:")
        for severity, count in sorted(result.summary.findings_by_severity.items()):
            print(f"  {severity}: {count}")

    if result.summary.findings_by_resource_type:
        print(f"\nFindings by Resource Type:")
        for rtype, count in sorted(result.summary.findings_by_resource_type.items()):
            print(f"  {rtype.split('/')[-1]}: {count}")

    if result.findings:
        print(f"\n{'=' * 60}")
        print("FINDINGS")
        print("=" * 60)

        for i, f in enumerate(result.findings, 1):
            print(f"\n[{i}] {f.resource_name}")
            print(f"    Resource ID: {f.resource_id}")
            print(f"    Type: {f.resource_type}")
            print(f"    Location: {f.location}")
            print(f"    Resource Group: {f.resource_group}")
            print(f"    Monthly Cost: ${f.estimated_monthly_cost:.2f}")
            print(f"    Severity: {f.severity}")
            print(f"    Confidence: {f.confidence_score}% ({f.confidence_level})")
            print(f"    Rule: {f.detection_rule}")
            if f.metadata:
                print(f"    Metadata: {json.dumps(f.metadata, default=str)}")
    else:
        print("\nNo abandoned resources found!")


if __name__ == "__main__":
    main()

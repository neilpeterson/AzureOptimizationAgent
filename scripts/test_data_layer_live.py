#!/usr/bin/env python3
"""Live test script for the data layer functions.

Prerequisites:
    1. Azure CLI logged in: `az login`
    2. Cosmos DB deployed with containers created
    3. Python dependencies installed: `pip install -r src/functions/requirements.txt`

Usage:
    python scripts/test_data_layer_live.py
    python scripts/test_data_layer_live.py --endpoint <cosmos-endpoint>
    python scripts/test_data_layer_live.py --seed  # Seed test data first
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Add src/functions to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src" / "functions"))


def get_cosmos_endpoint() -> str:
    """Get Cosmos DB endpoint from Azure CLI."""
    try:
        result = subprocess.run(
            [
                "az", "cosmosdb", "list",
                "--query", "[0].documentEndpoint",
                "-o", "tsv"
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        endpoint = result.stdout.strip()
        if not endpoint:
            print("Error: No Cosmos DB account found.")
            sys.exit(1)
        return endpoint
    except subprocess.CalledProcessError as e:
        print(f"Error getting Cosmos endpoint: {e}")
        sys.exit(1)


def get_cosmos_database() -> str:
    """Get Cosmos DB database name from Azure CLI."""
    try:
        # Get account name first
        account_result = subprocess.run(
            ["az", "cosmosdb", "list", "--query", "[0].name", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=True,
        )
        account_name = account_result.stdout.strip()

        # Get resource group
        rg_result = subprocess.run(
            ["az", "cosmosdb", "list", "--query", "[0].resourceGroup", "-o", "tsv"],
            capture_output=True,
            text=True,
            check=True,
        )
        rg_name = rg_result.stdout.strip()

        # Get database name
        db_result = subprocess.run(
            [
                "az", "cosmosdb", "sql", "database", "list",
                "--account-name", account_name,
                "--resource-group", rg_name,
                "--query", "[0].name",
                "-o", "tsv"
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        db_name = db_result.stdout.strip()
        return db_name if db_name else "optimization-agent"
    except subprocess.CalledProcessError:
        return "optimization-agent"


def seed_test_data(cosmos_client):
    """Seed test data into Cosmos DB."""
    print("\n" + "=" * 60)
    print("SEEDING TEST DATA")
    print("=" * 60)

    # Load seed data
    seed_dir = Path(__file__).parent.parent / "data" / "seed"

    # Seed module registry
    module_file = seed_dir / "module-registry.json"
    if module_file.exists():
        with open(module_file) as f:
            modules = json.load(f)
        for module in modules:
            cosmos_client._get_container("module-registry").upsert_item(module)
            print(f"  Seeded module: {module['moduleId']}")

    # Seed subscription owners (sample)
    owners_file = seed_dir / "subscription-owners.sample.json"
    if owners_file.exists():
        with open(owners_file) as f:
            owners = json.load(f)
        for owner in owners:
            cosmos_client._get_container("subscription-owners").upsert_item(owner)
            print(f"  Seeded owner: {owner['subscriptionId'][:8]}...")

    print("Seed data loaded successfully!")


def test_get_module_registry():
    """Test the get_module_registry function."""
    print("\n" + "-" * 60)
    print("TEST: get_module_registry")
    print("-" * 60)

    from data_layer import get_module_registry

    # Test getting enabled modules
    result = get_module_registry(include_disabled=False)
    print(f"Enabled modules: {result['count']}")
    for module in result['modules']:
        print(f"  - {module['moduleId']}: {module['moduleName']}")

    # Test getting all modules
    result_all = get_module_registry(include_disabled=True)
    print(f"All modules: {result_all['count']}")

    return result['count'] >= 0  # Pass if no error


def test_save_findings():
    """Test the save_findings function."""
    print("\n" + "-" * 60)
    print("TEST: save_findings")
    print("-" * 60)

    from data_layer import save_findings

    # Create test findings
    test_findings = [
        {
            "findingId": "test-finding-001",
            "subscriptionId": "00000000-0000-0000-0000-000000000001",
            "resourceId": "/subscriptions/00000000-0000-0000-0000-000000000001/resourceGroups/test-rg/providers/Microsoft.Compute/disks/test-disk",
            "resourceType": "microsoft.compute/disks",
            "resourceName": "test-disk",
            "category": "abandoned",
            "severity": "medium",
            "confidenceScore": 75,
            "confidenceLevel": "high",
            "estimatedMonthlyCost": 25.50,
            "description": "Test finding for data layer validation",
        }
    ]

    result = save_findings(
        execution_id="test-exec-001",
        module_id="abandoned-resources",
        findings=test_findings,
    )

    print(f"Saved: {result['saved']} findings")
    print(f"Execution ID: {result['executionId']}")
    print(f"Module ID: {result['moduleId']}")

    return result['saved'] == 1


def test_get_findings_history():
    """Test the get_findings_history function."""
    print("\n" + "-" * 60)
    print("TEST: get_findings_history")
    print("-" * 60)

    from data_layer import get_findings_history

    # Query for the test subscription
    result = get_findings_history(
        subscription_id="00000000-0000-0000-0000-000000000001",
        limit=10,
    )

    print(f"Found: {result['count']} findings")
    for finding in result['findings'][:3]:
        print(f"  - {finding.get('findingId')}: {finding.get('severity')} - ${finding.get('estimatedMonthlyCost', 0):.2f}")

    # Test with status filter
    result_open = get_findings_history(
        subscription_id="00000000-0000-0000-0000-000000000001",
        limit=10,
        status="open",
    )
    print(f"Open findings: {result_open['count']}")

    return True


def test_get_subscription_owners():
    """Test the get_subscription_owners function."""
    print("\n" + "-" * 60)
    print("TEST: get_subscription_owners")
    print("-" * 60)

    from data_layer import get_subscription_owners

    # Query for sample subscription IDs
    result = get_subscription_owners(
        subscription_ids=[
            "00000000-0000-0000-0000-000000000001",
            "00000000-0000-0000-0000-000000000002",
            "nonexistent-subscription",
        ]
    )

    print(f"Found: {result['found']} owners")
    print(f"Not found: {len(result['notFound'])} subscriptions")

    for owner in result['owners']:
        print(f"  - {owner['subscriptionId'][:8]}...: {owner.get('ownerEmail')}")

    if result['notFound']:
        print(f"  Missing: {result['notFound']}")

    return True


def main():
    parser = argparse.ArgumentParser(description="Test data layer functions")
    parser.add_argument(
        "--endpoint",
        help="Cosmos DB endpoint (defaults to first account from az cli)",
    )
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed test data before running tests",
    )
    args = parser.parse_args()

    # Get Cosmos endpoint and database
    endpoint = args.endpoint or get_cosmos_endpoint()
    database = os.environ.get("COSMOS_DATABASE") or get_cosmos_database()
    print(f"Using Cosmos DB: {endpoint}")
    print(f"Using Database: {database}")

    # Set environment variables
    os.environ["COSMOS_ENDPOINT"] = endpoint
    os.environ["COSMOS_DATABASE"] = database

    # Import after setting env var
    from shared import CosmosClient

    # Seed data if requested
    if args.seed:
        client = CosmosClient()
        seed_test_data(client)

    # Run tests
    print("\n" + "=" * 60)
    print("RUNNING DATA LAYER TESTS")
    print("=" * 60)

    results = {}

    try:
        results['get_module_registry'] = test_get_module_registry()
    except Exception as e:
        print(f"FAILED: {e}")
        results['get_module_registry'] = False

    try:
        results['save_findings'] = test_save_findings()
    except Exception as e:
        print(f"FAILED: {e}")
        results['save_findings'] = False

    try:
        results['get_findings_history'] = test_get_findings_history()
    except Exception as e:
        print(f"FAILED: {e}")
        results['get_findings_history'] = False

    try:
        results['get_subscription_owners'] = test_get_subscription_owners()
    except Exception as e:
        print(f"FAILED: {e}")
        results['get_subscription_owners'] = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status}: {test}")

    print(f"\nTotal: {passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

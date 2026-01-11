#!/usr/bin/env python3
"""Seed Cosmos DB with module registry and detection targets."""

import json
import os
import subprocess
import sys
from pathlib import Path

from azure.cosmos import CosmosClient

# Configuration
COSMOS_ACCOUNT = os.environ.get("COSMOS_ACCOUNT", "cosmos-optimization-agent-cenus")
COSMOS_ENDPOINT = f"https://{COSMOS_ACCOUNT}.documents.azure.com:443/"
DATABASE_NAME = os.environ.get("COSMOS_DATABASE", "db-optimization-agent-cenus")
RESOURCE_GROUP = os.environ.get("RESOURCE_GROUP", "rg-optimization-agent-cenus")

# Seed data paths (relative to repo root)
REPO_ROOT = Path(__file__).parent.parent
MODULE_REGISTRY_FILE = REPO_ROOT / "data" / "seed" / "module-registry.json"
DETECTION_TARGETS_FILE = REPO_ROOT / "data" / "seed" / "detection-targets.sample.json"


def get_cosmos_client() -> CosmosClient:
    """Create Cosmos client using account key from Azure CLI."""
    # Get account key via Azure CLI
    result = subprocess.run(
        [
            "az", "cosmosdb", "keys", "list",
            "--name", COSMOS_ACCOUNT,
            "--resource-group", RESOURCE_GROUP,
            "--type", "keys",
            "--query", "primaryMasterKey",
            "--output", "tsv"
        ],
        capture_output=True,
        text=True,
        check=True
    )
    account_key = result.stdout.strip()
    return CosmosClient(COSMOS_ENDPOINT, credential=account_key)


def seed_container(client: CosmosClient, container_name: str, items: list) -> int:
    """Upsert items into a container. Returns count of items seeded."""
    database = client.get_database_client(DATABASE_NAME)
    container = database.get_container_client(container_name)

    count = 0
    for item in items:
        container.upsert_item(item)
        print(f"  Upserted: {item.get('id', 'unknown')}")
        count += 1
    return count


def main():
    print(f"Cosmos DB Seeder")
    print(f"  Endpoint: {COSMOS_ENDPOINT}")
    print(f"  Database: {DATABASE_NAME}")
    print()

    client = get_cosmos_client()

    # Seed module registry
    if MODULE_REGISTRY_FILE.exists():
        print(f"Seeding module-registry from {MODULE_REGISTRY_FILE}...")
        with open(MODULE_REGISTRY_FILE) as f:
            data = json.load(f)
        # Handle both single object and array
        items = [data] if isinstance(data, dict) else data
        count = seed_container(client, "module-registry", items)
        print(f"  Done: {count} item(s)")
    else:
        print(f"Warning: {MODULE_REGISTRY_FILE} not found, skipping module-registry")

    print()

    # Seed detection targets
    if DETECTION_TARGETS_FILE.exists():
        print(f"Seeding detection-targets from {DETECTION_TARGETS_FILE}...")
        with open(DETECTION_TARGETS_FILE) as f:
            data = json.load(f)
        items = [data] if isinstance(data, dict) else data
        count = seed_container(client, "detection-targets", items)
        print(f"  Done: {count} item(s)")
    else:
        print(f"Warning: {DETECTION_TARGETS_FILE} not found, skipping detection-targets")

    print()
    print("Seeding complete.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

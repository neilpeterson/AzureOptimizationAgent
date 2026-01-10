# Azure Optimization Agent

An AI-powered solution that automatically detects cost optimization opportunities across Azure subscriptions and delivers personalized monthly recommendations to subscription owners.

## Overview

Managing Azure costs across many subscriptions is challenging. Teams often leave behind orphaned resources—unattached disks, unused public IPs, empty load balancers—that accumulate cost without providing value.

The Azure Optimization Agent solves this by:

- **Detecting** orphaned and underutilized resources across all your subscriptions
- **Analyzing** findings to prioritize by cost impact and confidence
- **Delivering** personalized monthly reports to subscription owners with actionable recommendations

## Architecture

The solution uses a three-layer architecture orchestrated by an Azure AI Foundry Agent:

| Layer | Purpose |
|-------|---------|
| **Detection Layer** | Scans Azure subscriptions via Resource Graph for optimization opportunities |
| **Data Layer** | Manages module registry, findings history, and subscription-owner mapping |
| **Notification Layer** | Sends personalized email reports to subscription owners |

## Key Features

- **Modular Design** - Add new detection capabilities without changing the core system
- **AI-Powered Analysis** - GPT-4o synthesizes findings and generates recommendations
- **Trend Detection** - Track optimization opportunities over time
- **Scalable** - Designed for hundreds of subscriptions

## Getting Started

1. Deploy the infrastructure using the Bicep templates in `/infra`
2. Configure the Azure AI Foundry agent
3. Seed the module registry and subscription owner data
4. Run your first optimization scan

## Documentation

| Document | Description |
|----------|-------------|
| [Design Document](OptimizationAgent.md) | Detailed architecture, data contracts, and module specifications |
| [Implementation Plan](PLAN.md) | Phased implementation roadmap |
| [Shared Library Guide](docs/shared-library.md) | Technical guide for the shared library and adding new modules |
| [Project Status](STATUS.md) | Current implementation progress |

## Project Structure

```
OptimizationAgent/
├── infra/                    # Bicep infrastructure templates
├── src/
│   └── functions/
│       ├── shared/           # Generic utilities (Cosmos client, Resource Graph, etc.)
│       └── detection_layer/  # Detection modules
│           └── abandoned_resources/
├── docs/                     # Additional documentation
└── data/                     # Seed data for Cosmos DB
```

## License

MIT

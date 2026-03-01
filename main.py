#!/usr/bin/env python3
"""CLI entry point for Datadog-to-Grafana dashboard conversion."""

import argparse
import json
import sys
from collections import Counter

from dd2grafana import convert_dashboard


def main():
    parser = argparse.ArgumentParser(
        description="Convert a Datadog dashboard JSON to Grafana dashboard JSON"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to Datadog dashboard JSON file",
    )
    parser.add_argument(
        "--output", "-o",
        default="output_grafana.json",
        help="Path for output Grafana dashboard JSON (default: output_grafana.json)",
    )
    args = parser.parse_args()

    # Load input
    try:
        with open(args.input) as f:
            dd_dashboard = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {args.input}: {e}", file=sys.stderr)
        sys.exit(1)

    # Convert
    grafana_dashboard = convert_dashboard(dd_dashboard)

    # Write output
    with open(args.output, "w") as f:
        json.dump(grafana_dashboard, f, indent=2)

    # Print summary
    panels = grafana_dashboard.get("panels", [])
    type_counts = Counter()
    _count_panel_types(panels, type_counts)

    print(f"Converted: {dd_dashboard.get('title', 'Untitled')}")
    print(f"  Panels created: {sum(type_counts.values())}")
    print(f"  Panel types: {dict(type_counts)}")
    print(f"  Template variables: {len(grafana_dashboard.get('templating', {}).get('list', []))}")
    print(f"  Output: {args.output}")


def _count_panel_types(panels: list[dict], counts: Counter):
    for panel in panels:
        counts[panel.get("type", "unknown")] += 1
        # Count nested panels in rows
        for child in panel.get("panels", []):
            counts[child.get("type", "unknown")] += 1


if __name__ == "__main__":
    main()

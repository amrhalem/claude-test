"""Translate Datadog metric queries to PromQL."""

import re


def translate_query(dd_query: str) -> str:
    """Convert a Datadog metric query string to a PromQL expression.

    Examples:
        avg:system.cpu.user{host:myhost} -> avg(system_cpu_user{host="myhost"})
        sum:http.requests{env:prod} by {service} -> sum by(service) (http_requests{env="prod"})
        top(avg:system.mem.used{*} by {host}, 10, 'mean', 'desc') -> topk(10, avg by(host) (system_mem_used))
    """
    dd_query = dd_query.strip()

    # Handle top() wrapper
    top_match = re.match(
        r"top\(\s*(.+?)\s*,\s*(\d+)\s*,\s*['\"].*?['\"]\s*,\s*['\"].*?['\"]\s*\)",
        dd_query,
    )
    if top_match:
        inner_query = top_match.group(1)
        top_n = top_match.group(2)
        inner_prom = translate_query(inner_query)
        return f"topk({top_n}, {inner_prom})"

    # Handle derivative() wrapper
    deriv_match = re.match(r"derivative\(\s*(.+)\s*\)", dd_query)
    if deriv_match:
        inner_prom = translate_query(deriv_match.group(1))
        return f"rate({inner_prom}[5m])"

    # Handle cumsum() wrapper
    cumsum_match = re.match(r"cumsum\(\s*(.+)\s*\)", dd_query)
    if cumsum_match:
        inner_prom = translate_query(cumsum_match.group(1))
        return f"increase({inner_prom}[1h])"

    # Main pattern: agg:metric{filters} [by {groups}]
    main_match = re.match(
        r"(\w+):([a-zA-Z0-9_.]+)\{([^}]*)\}(?:\s+by\s+\{([^}]*)\})?\s*$",
        dd_query,
    )
    if not main_match:
        # Fallback: return as-is with dots replaced
        return dd_query.replace(".", "_")

    agg = main_match.group(1)
    metric = main_match.group(2)
    filters_raw = main_match.group(3)
    groups_raw = main_match.group(4)

    # Convert metric name: dots -> underscores
    prom_metric = metric.replace(".", "_")

    # Convert filters
    prom_filters = _translate_filters(filters_raw)

    # Build label selector
    label_selector = ""
    if prom_filters:
        label_selector = "{" + ", ".join(prom_filters) + "}"

    # Build PromQL
    if groups_raw:
        groups = ", ".join(g.strip() for g in groups_raw.split(","))
        return f"{agg} by({groups}) ({prom_metric}{label_selector})"
    else:
        return f"{agg}({prom_metric}{label_selector})"


def _translate_filters(filters_raw: str) -> list[str]:
    """Convert Datadog filter string to list of PromQL label matchers."""
    filters_raw = filters_raw.strip()
    if not filters_raw or filters_raw == "*":
        return []

    result = []
    for part in filters_raw.split(","):
        part = part.strip()
        if not part:
            continue

        # Template variable reference: $varname
        if part.startswith("$"):
            result.append(f'{part}=~".*"')
            continue

        # Negation filter: !tag:value
        if part.startswith("!"):
            part = part[1:]
            key, _, value = part.partition(":")
            result.append(f'{key.strip()}!="{value.strip()}"')
        else:
            key, _, value = part.partition(":")
            if value:
                result.append(f'{key.strip()}="{value.strip()}"')
            # Skip bare tags without values

    return result


def extract_legend_format(dd_query: str) -> str:
    """Generate a Grafana legendFormat from the by-clause of a Datadog query."""
    by_match = re.search(r"by\s+\{([^}]+)\}", dd_query)
    if by_match:
        groups = [g.strip() for g in by_match.group(1).split(",")]
        return " - ".join(f"{{{{{g}}}}}" for g in groups)
    return ""

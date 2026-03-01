"""Main converter orchestrator: Datadog dashboard JSON -> Grafana dashboard JSON."""

from .widget_mappers import WIDGET_MAPPERS, scale_grid_pos, map_group


def convert_dashboard(dd_dashboard: dict) -> dict:
    """Convert a Datadog dashboard dict to a Grafana dashboard dict."""
    panels, _ = _convert_widgets(dd_dashboard.get("widgets", []), panel_id=1)

    return {
        "uid": "",
        "title": dd_dashboard.get("title", "Converted Dashboard"),
        "description": dd_dashboard.get("description", ""),
        "tags": ["converted", "datadog"],
        "schemaVersion": 38,
        "editable": True,
        "panels": panels,
        "templating": {
            "list": _convert_template_variables(
                dd_dashboard.get("template_variables", [])
            ),
        },
        "time": {"from": "now-6h", "to": "now"},
        "refresh": "30s",
        "fiscalYearStartMonth": 0,
        "liveNow": False,
    }


def _convert_widgets(
    widgets: list[dict], panel_id: int = 1, y_offset: int = 0
) -> tuple[list[dict], int]:
    """Convert a list of Datadog widgets to Grafana panels.

    Returns (panels_list, next_panel_id).
    """
    panels = []

    for widget in widgets:
        definition = widget.get("definition", {})
        widget_type = definition.get("type", "")
        layout = widget.get("layout", {})

        if widget_type == "group":
            group_panels, panel_id = map_group(
                definition, layout, panel_id, _convert_widgets
            )
            panels.extend(group_panels)
            continue

        mapper = WIDGET_MAPPERS.get(widget_type)
        if mapper is None:
            # Unsupported widget type — create a text panel placeholder
            grid_pos = scale_grid_pos(layout) if layout else _default_grid_pos()
            grid_pos.y += y_offset
            panel = {
                "id": panel_id,
                "type": "text",
                "title": definition.get("title", f"Unsupported: {widget_type}"),
                "gridPos": grid_pos.to_dict(),
                "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
                "targets": [],
                "fieldConfig": {"defaults": {}, "overrides": []},
                "options": {
                    "mode": "markdown",
                    "content": f"*Unsupported Datadog widget type: `{widget_type}`*",
                },
            }
            panels.append(panel)
            panel_id += 1
            continue

        grid_pos = scale_grid_pos(layout) if layout else _default_grid_pos()
        grid_pos.y += y_offset
        panel = mapper(definition, grid_pos, panel_id)
        panels.append(panel)
        panel_id += 1

    return panels, panel_id


def _default_grid_pos():
    from .models import GridPos
    return GridPos(x=0, y=0, w=12, h=8)


def _convert_template_variables(dd_vars: list[dict]) -> list[dict]:
    """Convert Datadog template_variables to Grafana templating list."""
    grafana_vars = []
    for var in dd_vars:
        name = var.get("name", "")
        defaults = var.get("defaults", [])
        available = var.get("available_values", [])

        if available:
            # Custom variable with known values
            grafana_var = {
                "name": name,
                "label": name.capitalize(),
                "type": "custom",
                "query": ", ".join(available) if available else "",
                "current": {
                    "text": defaults[0] if defaults else (available[0] if available else ""),
                    "value": defaults[0] if defaults else (available[0] if available else ""),
                },
                "options": [
                    {"text": v, "value": v, "selected": v in defaults}
                    for v in available
                ],
                "multi": False,
                "includeAll": True,
                "allValue": ".*",
            }
        else:
            # Query-based variable (use label_values)
            prefix = var.get("prefix", name)
            grafana_var = {
                "name": name,
                "label": name.capitalize(),
                "type": "query",
                "datasource": {"type": "prometheus", "uid": "${DS_PROMETHEUS}"},
                "query": f'label_values({prefix})',
                "current": {
                    "text": defaults[0] if defaults else "",
                    "value": defaults[0] if defaults else "",
                },
                "refresh": 1,
                "multi": False,
                "includeAll": True,
                "allValue": ".*",
            }

        grafana_vars.append(grafana_var)

    return grafana_vars

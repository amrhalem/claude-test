"""Widget-type-specific conversion logic from Datadog to Grafana."""

from .query_translator import translate_query, extract_legend_format
from .models import GridPos, Target, GrafanaPanel


# Datadog palette -> Grafana color
_DD_PALETTE_TO_COLOR = {
    "white_on_red": "red",
    "white_on_yellow": "yellow",
    "white_on_green": "green",
    "red_on_white": "red",
    "yellow_on_white": "yellow",
    "green_on_white": "green",
}

# Datadog display_type -> Grafana drawStyle
_DD_DISPLAY_TO_DRAW = {
    "line": "line",
    "area": "line",  # with fillOpacity
    "bars": "bars",
}


def scale_grid_pos(layout: dict) -> GridPos:
    """Scale Datadog 12-col grid to Grafana 24-col grid."""
    return GridPos(
        x=layout.get("x", 0) * 2,
        y=layout.get("y", 0) * 2,
        w=layout.get("width", 6) * 2,
        h=max(layout.get("height", 4) * 2, 4),
    )


def _build_targets(requests: list[dict]) -> list[Target]:
    """Convert Datadog requests array to Grafana targets."""
    targets = []
    for i, req in enumerate(requests):
        query = req.get("q", "")
        ref_id = chr(ord("A") + i)
        targets.append(Target(
            expr=translate_query(query),
            legend_format=extract_legend_format(query),
            ref_id=ref_id,
        ))
    return targets


def _convert_conditional_formats(cond_formats: list[dict]) -> dict:
    """Convert Datadog conditional_formats to Grafana threshold steps."""
    steps = [{"value": None, "color": "green"}]

    # Sort by value to build threshold steps
    sorted_fmts = sorted(
        [cf for cf in cond_formats if cf.get("value") is not None],
        key=lambda cf: cf["value"],
    )

    for cf in sorted_fmts:
        color = _DD_PALETTE_TO_COLOR.get(cf.get("palette", ""), "red")
        steps.append({"value": cf["value"], "color": color})

    return {"mode": "absolute", "steps": steps}


def map_timeseries(definition: dict, grid_pos: GridPos, panel_id: int) -> dict:
    """Convert Datadog timeseries widget to Grafana timeseries panel."""
    requests = definition.get("requests", [])
    targets = _build_targets(requests)

    # Determine draw style from first request
    display_type = "line"
    if requests:
        display_type = requests[0].get("display_type", "line")

    draw_style = _DD_DISPLAY_TO_DRAW.get(display_type, "line")
    fill_opacity = 25 if display_type == "area" else 10

    show_legend = definition.get("show_legend", True)

    panel = GrafanaPanel(
        id=panel_id,
        type="timeseries",
        title=definition.get("title", ""),
        grid_pos=grid_pos,
        targets=targets,
        field_config={
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "drawStyle": draw_style,
                    "lineWidth": 1,
                    "fillOpacity": fill_opacity,
                    "pointSize": 5,
                    "showPoints": "auto",
                },
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"value": None, "color": "green"}],
                },
            },
            "overrides": [],
        },
        options={
            "legend": {
                "displayMode": "list" if show_legend else "hidden",
                "placement": "bottom",
            },
            "tooltip": {"mode": "multi"},
        },
    )
    return panel.to_dict()


def map_query_value(definition: dict, grid_pos: GridPos, panel_id: int) -> dict:
    """Convert Datadog query_value widget to Grafana stat panel."""
    requests = definition.get("requests", [])
    targets = _build_targets(requests)

    # Convert conditional formats to thresholds
    thresholds = {"mode": "absolute", "steps": [{"value": None, "color": "green"}]}
    if requests:
        cond_fmts = requests[0].get("conditional_formats", [])
        if cond_fmts:
            thresholds = _convert_conditional_formats(cond_fmts)

    panel = GrafanaPanel(
        id=panel_id,
        type="stat",
        title=definition.get("title", ""),
        grid_pos=grid_pos,
        targets=targets,
        field_config={
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": thresholds,
            },
            "overrides": [],
        },
        options={
            "colorMode": "background",
            "graphMode": "none",
            "textMode": "auto",
            "reduceOptions": {
                "calcs": ["lastNotNull"],
                "fields": "",
                "values": False,
            },
        },
    )
    return panel.to_dict()


def map_toplist(definition: dict, grid_pos: GridPos, panel_id: int) -> dict:
    """Convert Datadog toplist widget to Grafana bargauge panel."""
    requests = definition.get("requests", [])
    targets = _build_targets(requests)

    panel = GrafanaPanel(
        id=panel_id,
        type="bargauge",
        title=definition.get("title", ""),
        grid_pos=grid_pos,
        targets=targets,
        field_config={
            "defaults": {
                "color": {"mode": "palette-classic"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"value": None, "color": "green"}],
                },
            },
            "overrides": [],
        },
        options={
            "orientation": "horizontal",
            "displayMode": "gradient",
            "reduceOptions": {
                "calcs": ["lastNotNull"],
                "fields": "",
                "values": False,
            },
        },
    )
    return panel.to_dict()


def map_query_table(definition: dict, grid_pos: GridPos, panel_id: int) -> dict:
    """Convert Datadog query_table widget to Grafana table panel."""
    requests = definition.get("requests", [])
    targets = _build_targets(requests)

    panel = GrafanaPanel(
        id=panel_id,
        type="table",
        title=definition.get("title", ""),
        grid_pos=grid_pos,
        targets=targets,
        field_config={
            "defaults": {
                "color": {"mode": "thresholds"},
                "thresholds": {
                    "mode": "absolute",
                    "steps": [{"value": None, "color": "green"}],
                },
            },
            "overrides": [],
        },
        options={
            "showHeader": True,
            "sortBy": [],
        },
    )
    return panel.to_dict()


def map_heatmap(definition: dict, grid_pos: GridPos, panel_id: int) -> dict:
    """Convert Datadog heatmap widget to Grafana heatmap panel."""
    requests = definition.get("requests", [])
    targets = _build_targets(requests)

    panel = GrafanaPanel(
        id=panel_id,
        type="heatmap",
        title=definition.get("title", ""),
        grid_pos=grid_pos,
        targets=targets,
        field_config={
            "defaults": {},
            "overrides": [],
        },
        options={
            "calculate": True,
            "color": {"scheme": "Oranges", "mode": "scheme"},
            "yAxis": {"unit": "ms"},
        },
    )
    return panel.to_dict()


def map_note(definition: dict, grid_pos: GridPos, panel_id: int) -> dict:
    """Convert Datadog note widget to Grafana text panel."""
    content = definition.get("content", "")

    panel = GrafanaPanel(
        id=panel_id,
        type="text",
        title=definition.get("title", ""),
        grid_pos=grid_pos,
        field_config={"defaults": {}, "overrides": []},
        options={
            "mode": "markdown",
            "content": content,
        },
    )
    return panel.to_dict()


def map_free_text(definition: dict, grid_pos: GridPos, panel_id: int) -> dict:
    """Convert Datadog free_text widget to Grafana text panel."""
    text = definition.get("text", "")

    panel = GrafanaPanel(
        id=panel_id,
        type="text",
        title="",
        grid_pos=grid_pos,
        field_config={"defaults": {}, "overrides": []},
        options={
            "mode": "markdown",
            "content": text,
        },
    )
    return panel.to_dict()


def map_group(definition: dict, layout: dict, panel_id: int, convert_widgets_fn) -> tuple[list[dict], int]:
    """Convert Datadog group widget to Grafana row + nested panels.

    Returns a list of panels (row + children) and the next available panel_id.
    """
    grid_pos = scale_grid_pos(layout)
    row_panel = {
        "id": panel_id,
        "type": "row",
        "title": definition.get("title", "Group"),
        "gridPos": {"x": 0, "y": grid_pos.y, "w": 24, "h": 1},
        "collapsed": True,
        "panels": [],
    }
    panel_id += 1

    nested_widgets = definition.get("widgets", [])
    child_panels, panel_id = convert_widgets_fn(nested_widgets, panel_id, y_offset=grid_pos.y + 1)
    row_panel["panels"] = child_panels

    return [row_panel], panel_id


# Registry of mappers
WIDGET_MAPPERS = {
    "timeseries": map_timeseries,
    "query_value": map_query_value,
    "toplist": map_toplist,
    "query_table": map_query_table,
    "heatmap": map_heatmap,
    "distribution": map_heatmap,  # reuse heatmap as histogram-like
    "note": map_note,
    "free_text": map_free_text,
}

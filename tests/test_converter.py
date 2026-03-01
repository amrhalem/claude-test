"""Tests for the Datadog-to-Grafana dashboard converter."""

import json
import os

import pytest

from dd2grafana.query_translator import translate_query, extract_legend_format
from dd2grafana.widget_mappers import scale_grid_pos, WIDGET_MAPPERS
from dd2grafana.converter import convert_dashboard
from dd2grafana.models import GridPos


# --- Query Translation Tests ---

class TestQueryTranslation:
    def test_simple_avg(self):
        result = translate_query("avg:system.cpu.user{host:myhost}")
        assert result == 'avg(system_cpu_user{host="myhost"})'

    def test_sum_with_by_clause(self):
        result = translate_query("sum:http.requests{env:prod} by {service}")
        assert result == 'sum by(service) (http_requests{env="prod"})'

    def test_wildcard_filter(self):
        result = translate_query("avg:system.cpu.user{*}")
        assert result == "avg(system_cpu_user)"

    def test_template_variable(self):
        result = translate_query("avg:system.cpu.user{$env}")
        # $env should be preserved as-is (works in both systems)
        assert "$env" in result

    def test_multiple_filters(self):
        result = translate_query("sum:http.errors{env:prod,service:web}")
        assert 'env="prod"' in result
        assert 'service="web"' in result

    def test_negation_filter(self):
        result = translate_query("avg:system.cpu.user{!host:excluded}")
        assert 'host!="excluded"' in result

    def test_top_function(self):
        result = translate_query(
            "top(avg:system.mem.used{*} by {host}, 10, 'mean', 'desc')"
        )
        assert result.startswith("topk(10,")
        assert "system_mem_used" in result

    def test_derivative_function(self):
        result = translate_query("derivative(avg:system.cpu.user{*})")
        assert "rate(" in result
        assert "system_cpu_user" in result

    def test_dots_to_underscores(self):
        result = translate_query("avg:my.custom.metric.name{*}")
        assert "my_custom_metric_name" in result

    def test_by_clause_multiple_groups(self):
        result = translate_query("avg:metric{*} by {host,region}")
        assert "by(host, region)" in result


class TestLegendFormat:
    def test_single_group(self):
        result = extract_legend_format("avg:metric{*} by {host}")
        assert result == "{{host}}"

    def test_multiple_groups(self):
        result = extract_legend_format("avg:metric{*} by {host,region}")
        assert result == "{{host}} - {{region}}"

    def test_no_group(self):
        result = extract_legend_format("avg:metric{*}")
        assert result == ""


# --- Grid Position Tests ---

class TestGridPosition:
    def test_scale_12_to_24_col(self):
        layout = {"x": 0, "y": 0, "width": 12, "height": 4}
        pos = scale_grid_pos(layout)
        assert pos.x == 0
        assert pos.y == 0
        assert pos.w == 24
        assert pos.h == 8

    def test_half_width(self):
        layout = {"x": 6, "y": 2, "width": 6, "height": 3}
        pos = scale_grid_pos(layout)
        assert pos.x == 12
        assert pos.y == 4
        assert pos.w == 12
        assert pos.h == 6

    def test_minimum_height(self):
        layout = {"x": 0, "y": 0, "width": 4, "height": 1}
        pos = scale_grid_pos(layout)
        assert pos.h >= 4  # minimum height


# --- Widget Mapper Tests ---

class TestWidgetMappers:
    def test_timeseries_mapper(self):
        definition = {
            "type": "timeseries",
            "title": "CPU Usage",
            "show_legend": True,
            "requests": [{"q": "avg:system.cpu.user{*} by {host}", "display_type": "line"}],
        }
        grid_pos = GridPos(0, 0, 24, 8)
        panel = WIDGET_MAPPERS["timeseries"](definition, grid_pos, 1)

        assert panel["type"] == "timeseries"
        assert panel["title"] == "CPU Usage"
        assert len(panel["targets"]) == 1
        assert "system_cpu_user" in panel["targets"][0]["expr"]
        assert panel["fieldConfig"]["defaults"]["custom"]["drawStyle"] == "line"

    def test_timeseries_area(self):
        definition = {
            "type": "timeseries",
            "title": "Net In",
            "requests": [{"q": "avg:system.net.bytes_rcvd{*}", "display_type": "area"}],
        }
        panel = WIDGET_MAPPERS["timeseries"](definition, GridPos(0, 0, 24, 8), 1)
        assert panel["fieldConfig"]["defaults"]["custom"]["fillOpacity"] == 25

    def test_timeseries_bars(self):
        definition = {
            "type": "timeseries",
            "title": "Requests",
            "requests": [{"q": "sum:http.requests{*}", "display_type": "bars"}],
        }
        panel = WIDGET_MAPPERS["timeseries"](definition, GridPos(0, 0, 24, 8), 1)
        assert panel["fieldConfig"]["defaults"]["custom"]["drawStyle"] == "bars"

    def test_query_value_mapper(self):
        definition = {
            "type": "query_value",
            "title": "Error Rate",
            "requests": [{
                "q": "sum:http.errors{*}",
                "conditional_formats": [
                    {"comparator": ">", "value": 100, "palette": "white_on_red"},
                    {"comparator": "<", "value": 10, "palette": "white_on_green"},
                ],
            }],
        }
        panel = WIDGET_MAPPERS["query_value"](definition, GridPos(0, 0, 8, 4), 1)

        assert panel["type"] == "stat"
        thresholds = panel["fieldConfig"]["defaults"]["thresholds"]["steps"]
        # Should have base + 2 threshold steps
        assert len(thresholds) == 3
        values = [s.get("value") for s in thresholds]
        assert None in values  # base step
        assert 10 in values
        assert 100 in values

    def test_toplist_mapper(self):
        definition = {
            "type": "toplist",
            "title": "Top Hosts",
            "requests": [{"q": "top(avg:system.mem.used{*} by {host}, 10, 'mean', 'desc')"}],
        }
        panel = WIDGET_MAPPERS["toplist"](definition, GridPos(0, 0, 12, 8), 1)

        assert panel["type"] == "bargauge"
        assert panel["options"]["orientation"] == "horizontal"

    def test_query_table_mapper(self):
        definition = {
            "type": "query_table",
            "title": "Service Table",
            "requests": [
                {"q": "avg:http.request.duration{*} by {service}"},
                {"q": "sum:http.requests{*} by {service}"},
            ],
        }
        panel = WIDGET_MAPPERS["query_table"](definition, GridPos(0, 0, 24, 8), 1)

        assert panel["type"] == "table"
        assert len(panel["targets"]) == 2
        assert panel["targets"][0]["refId"] == "A"
        assert panel["targets"][1]["refId"] == "B"

    def test_heatmap_mapper(self):
        definition = {
            "type": "heatmap",
            "title": "Latency",
            "requests": [{"q": "avg:http.request.duration{*}"}],
        }
        panel = WIDGET_MAPPERS["heatmap"](definition, GridPos(0, 0, 12, 8), 1)
        assert panel["type"] == "heatmap"

    def test_note_mapper(self):
        definition = {
            "type": "note",
            "title": "",
            "content": "## Hello World",
        }
        panel = WIDGET_MAPPERS["note"](definition, GridPos(0, 0, 24, 4), 1)

        assert panel["type"] == "text"
        assert panel["options"]["content"] == "## Hello World"
        assert panel["options"]["mode"] == "markdown"

    def test_free_text_mapper(self):
        definition = {"type": "free_text", "text": "Dashboard Title"}
        panel = WIDGET_MAPPERS["free_text"](definition, GridPos(0, 0, 24, 4), 1)
        assert panel["type"] == "text"
        assert panel["options"]["content"] == "Dashboard Title"


# --- Full Dashboard Conversion Tests ---

class TestDashboardConversion:
    @pytest.fixture
    def sample_dashboard(self):
        path = os.path.join(
            os.path.dirname(__file__), "..", "mock_data", "sample_datadog_dashboard.json"
        )
        with open(path) as f:
            return json.load(f)

    def test_top_level_fields(self, sample_dashboard):
        result = convert_dashboard(sample_dashboard)

        assert result["title"] == "Production Infrastructure Overview"
        assert result["schemaVersion"] == 38
        assert "panels" in result
        assert "templating" in result

    def test_template_variables_converted(self, sample_dashboard):
        result = convert_dashboard(sample_dashboard)
        tmpl_list = result["templating"]["list"]

        names = [v["name"] for v in tmpl_list]
        assert "env" in names
        assert "host" in names
        assert "service" in names

        # env should be custom type with available values
        env_var = next(v for v in tmpl_list if v["name"] == "env")
        assert env_var["type"] == "custom"

        # host should be query type (no available_values)
        host_var = next(v for v in tmpl_list if v["name"] == "host")
        assert host_var["type"] == "query"

    def test_panel_count(self, sample_dashboard):
        result = convert_dashboard(sample_dashboard)
        panels = result["panels"]

        # Count all panels including nested
        total = 0
        for p in panels:
            total += 1
            total += len(p.get("panels", []))

        # 9 widgets in input, group expands to row + 2 children
        assert total >= 10

    def test_group_becomes_row(self, sample_dashboard):
        result = convert_dashboard(sample_dashboard)
        row_panels = [p for p in result["panels"] if p["type"] == "row"]

        assert len(row_panels) == 1
        assert row_panels[0]["title"] == "Network Metrics"
        assert row_panels[0]["collapsed"] is True
        assert len(row_panels[0]["panels"]) == 2

    def test_all_panels_have_required_fields(self, sample_dashboard):
        result = convert_dashboard(sample_dashboard)

        for panel in result["panels"]:
            assert "id" in panel
            assert "type" in panel
            assert "gridPos" in panel
            gp = panel["gridPos"]
            assert "x" in gp and "y" in gp and "w" in gp and "h" in gp

    def test_unsupported_widget_type(self):
        dd = {
            "title": "Test",
            "widgets": [{
                "id": 1,
                "layout": {"x": 0, "y": 0, "width": 6, "height": 4},
                "definition": {"type": "geomap", "title": "World Map"},
            }],
        }
        result = convert_dashboard(dd)
        assert len(result["panels"]) == 1
        assert result["panels"][0]["type"] == "text"
        assert "Unsupported" in result["panels"][0]["options"]["content"]

    def test_output_is_valid_json(self, sample_dashboard):
        result = convert_dashboard(sample_dashboard)
        # Should be serializable
        output = json.dumps(result, indent=2)
        # Should be parseable back
        parsed = json.loads(output)
        assert parsed["title"] == result["title"]

    def test_datasource_set(self, sample_dashboard):
        result = convert_dashboard(sample_dashboard)
        for panel in result["panels"]:
            if panel["type"] != "row":
                assert panel["datasource"]["uid"] == "${DS_PROMETHEUS}"

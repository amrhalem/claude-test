# dd2grafana

A CLI tool that converts Datadog dashboard JSON exports into Grafana-compatible dashboard JSON.

## What This Is

This project was built as a test of Claude's coding capabilities. The entire tool — including the converter logic, query translation, widget mapping, data models, CLI entry point, mock data, and tests — was produced in approximately 15 minutes.

## Features

- Converts Datadog widget types (timeseries, query_value, toplist, heatmap, etc.) to their Grafana panel equivalents
- Translates Datadog metric queries to PromQL
- Maps Datadog grid layouts to Grafana grid positions
- Converts template variables
- Supports grouped/nested widgets
- Provides placeholder panels for unsupported widget types

## Usage

```bash
python main.py -i mock_data/sample_datadog_dashboard.json -o output_grafana.json
```

## Project Structure

```
├── main.py                 # CLI entry point
├── dd2grafana/
│   ├── converter.py        # Main conversion orchestrator
│   ├── query_translator.py # Datadog query -> PromQL translation
│   ├── widget_mappers.py   # Widget type mapping functions
│   └── models.py           # Data models (GridPos, etc.)
├── mock_data/
│   └── sample_datadog_dashboard.json
├── tests/
│   └── test_converter.py
└── requirements.txt
```

## Running Tests

```bash
pip install -r requirements.txt
pytest
```

"""Lightweight dataclasses for intermediate representation."""

from dataclasses import dataclass, field


@dataclass
class GridPos:
    x: int
    y: int
    w: int
    h: int

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y, "w": self.w, "h": self.h}


@dataclass
class Target:
    expr: str
    legend_format: str = ""
    ref_id: str = "A"

    def to_dict(self) -> dict:
        return {
            "refId": self.ref_id,
            "expr": self.expr,
            "legendFormat": self.legend_format,
        }


@dataclass
class GrafanaPanel:
    id: int
    type: str
    title: str
    grid_pos: GridPos
    targets: list[Target] = field(default_factory=list)
    field_config: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    datasource: dict = field(default_factory=lambda: {
        "type": "prometheus",
        "uid": "${DS_PROMETHEUS}",
    })
    panels: list = field(default_factory=list)  # for row type

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "type": self.type,
            "title": self.title,
            "gridPos": self.grid_pos.to_dict(),
            "datasource": self.datasource,
            "targets": [t.to_dict() for t in self.targets],
            "fieldConfig": self.field_config,
            "options": self.options,
        }
        if self.type == "row":
            d["collapsed"] = True
            d["panels"] = self.panels
        return d

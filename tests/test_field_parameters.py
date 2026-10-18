"""Field parameters (Forecast Level, TDP Level) are in model.bim and point at columns that exist and are related."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODEL = json.loads((ROOT / "PowerBI" / "model.bim").read_text(encoding="utf-8"))["model"]
TABLES = {t["name"]: t for t in MODEL["tables"]}


def _refs(table):
    expr = " ".join(TABLES[table]["partitions"][0]["source"]["expression"])
    import re
    return re.findall(r"NAMEOF\('([^']+)'\[([^\]]+)\]\)", expr)


def test_both_parameters_have_field_parameter_metadata():
    for name in ("Forecast Level", "TDP Level"):
        cols = {c["name"]: c for c in TABLES[name]["columns"]}
        meta = cols[name + " Fields"]["extendedProperties"][0]
        assert meta["name"] == "ParameterMetadata"
        assert json.loads(meta["value"]) == {"version": 3, "kind": 2}
        assert cols[name]["sortByColumn"] == name + " Order"


def test_every_referenced_column_exists():
    for name in ("Forecast Level", "TDP Level"):
        refs = _refs(name)
        assert refs
        for t, c in refs:
            assert c in {x["name"] for x in TABLES[t]["columns"]}, (t, c)


def test_each_level_is_related_to_the_fact_it_drives():
    rel = {(r["fromTable"], r["toTable"]) for r in MODEL["relationships"]}
    for t, _ in _refs("Forecast Level"):
        assert ("Fact Offtake Sales", t) in rel, t
    for t, _ in _refs("TDP Level"):
        assert ("Fact TDP", t) in rel or t == "Article Master", t
        assert ("Fact TDP", "Article Master") in rel

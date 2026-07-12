"""DuckDB layer: local analytical SQL over the repo's committed CSVs.

``duckdb`` is an optional dependency (pip install duckdb). Everything else in
the agent works without it; the ``sql``/``db-build`` commands raise a clear
message if it's missing.

Views built by build_db():
  v_primary_article  — PowerBI/RawDataFolders/Primary_Article_Monthly/*.csv
  v_offtake          — PowerBI/RawDataFolders/Offtake_Monthly/offtake_*.csv
  v_primary_shipto   — PowerBI/RawDataFolders/Primary_ShipTo_Monthly/*.csv
  m_*                — one table per SeedData/Masters CSV (m_chainmaster, ...)

THE ONE FY RULE lives in SQL macros (fy_from_ym / fy_from_label) so every
template derives FY from month+year — never from a fixed column position.
"""
from __future__ import annotations

import re
from pathlib import Path

from .config import Config


class DuckDBMissing(RuntimeError):
    pass


def _duckdb():
    try:
        import duckdb
        return duckdb
    except ImportError as e:
        raise DuckDBMissing(
            "duckdb is not installed — run: pip install duckdb "
            "(see agent/requirements.txt)") from e


# Mirrors mtagent.fyrules — the eval tests assert both stay in agreement.
FY_MACROS = """
CREATE OR REPLACE MACRO mon3_num(lab) AS
    CASE lower(substr(trim(lab), 1, 3))
        WHEN 'jan' THEN 1 WHEN 'feb' THEN 2 WHEN 'mar' THEN 3
        WHEN 'apr' THEN 4 WHEN 'may' THEN 5 WHEN 'jun' THEN 6
        WHEN 'jul' THEN 7 WHEN 'aug' THEN 8 WHEN 'sep' THEN 9
        WHEN 'oct' THEN 10 WHEN 'nov' THEN 11 WHEN 'dec' THEN 12
    END;

CREATE OR REPLACE MACRO fy_from_ym(y, m) AS
    CASE WHEN y IS NULL OR m IS NULL THEN NULL
         ELSE 'FY' || lpad(CAST(((CASE WHEN m >= 4 THEN y + 1 ELSE y END) % 100) AS VARCHAR), 2, '0')
    END;

-- Some offtake extracts carry a raw Excel date serial in the Month column
-- ('46113.0' = 2026-04-01) instead of "Apr'26"; the dashboard build accepts
-- both, so these macros do too. NULL = genuinely unparsable.
CREATE OR REPLACE MACRO excel_serial_date(lab) AS
    CASE WHEN trim(CAST(lab AS VARCHAR)) SIMILAR TO '[0-9]{5}(\\.[0-9]*)?'
         THEN DATE '1899-12-30'
              + CAST(floor(TRY_CAST(trim(CAST(lab AS VARCHAR)) AS DOUBLE)) AS INTEGER)
         ELSE NULL END;

CREATE OR REPLACE MACRO month_num_any(lab) AS
    CASE WHEN excel_serial_date(lab) IS NOT NULL THEN month(excel_serial_date(lab))
         ELSE mon3_num(CAST(lab AS VARCHAR)) END;

CREATE OR REPLACE MACRO year_any(lab) AS
    CASE WHEN excel_serial_date(lab) IS NOT NULL THEN year(excel_serial_date(lab))
         ELSE 2000 + TRY_CAST(regexp_extract(trim(CAST(lab AS VARCHAR)),
                                             '([0-9]{2})$', 1) AS INTEGER) END;

-- "Apr'25" / "Apr-25" / "Apr 2025" / Excel serial -> 'FY26' (or NULL)
CREATE OR REPLACE MACRO fy_from_label(lab) AS
    fy_from_ym(year_any(lab), month_num_any(lab));

-- any style -> canonical 'Apr-26' label (or NULL)
CREATE OR REPLACE MACRO norm_month_label(lab) AS
    CASE WHEN year_any(lab) IS NULL OR month_num_any(lab) IS NULL THEN NULL
         ELSE strftime(make_date(year_any(lab), month_num_any(lab), 1), '%b-%y') END;

CREATE OR REPLACE MACRO fy_quarter(m) AS ((m - 4 + 12) % 12) // 3 + 1;
"""


def connect(cfg: Config, read_only: bool = False):
    duckdb = _duckdb()
    path = cfg.path(cfg.db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(path), read_only=read_only)
    if not read_only:
        con.execute(FY_MACROS)
    return con


def build_db(cfg: Config) -> list[str]:
    """(Re)create views over the committed CSVs. Returns build log lines."""
    root = cfg.root()
    pbi = root / "PowerBI"
    con = connect(cfg)
    log: list[str] = []

    def csvglob(rel: str, exclude_prefix: str = "_") -> list[str]:
        files = sorted((pbi / rel).parent.glob(Path(rel).name))
        return [str(f) for f in files if not f.name.startswith(exclude_prefix)]

    def make_view(name: str, files: list[str],
                  normalize_cols: list[str] | None = None) -> None:
        if not files:
            log.append(f"{name}: no source files found — skipped")
            return
        lst = ", ".join("'" + f.replace("'", "''") + "'" for f in files)
        base = (f"SELECT * FROM read_csv_auto([{lst}], header=true, "
                "union_by_name=true, all_varchar=false, sample_size=-1)")
        # DATA CONTRACT: TRIM+UPPER the lookup dimensions at load so casing/
        # trailing spaces can't create phantom duplicate chains/stores/DCs.
        if normalize_cols:
            rep = ", ".join(f'upper(trim("{c}")) AS "{c}"' for c in normalize_cols)
            try:
                con.execute(f"CREATE OR REPLACE VIEW {name} AS "
                            f"SELECT * REPLACE ({rep}) FROM ({base})")
                n = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
                log.append(f"{name}: {len(files)} file(s), {n} rows "
                           f"(normalized: {', '.join(normalize_cols)})")
                return
            except Exception as e:   # a column missing from this union — fall back
                log.append(f"{name}: normalization skipped ({e})")
        con.execute(f"CREATE OR REPLACE VIEW {name} AS {base}")
        n = con.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
        log.append(f"{name}: {len(files)} file(s), {n} rows")

    make_view("v_primary_article",
              csvglob("RawDataFolders/Primary_Article_Monthly/primary_article_*.csv"),
              normalize_cols=["Chain name", "Ship To Name"])
    make_view("v_offtake",
              csvglob("RawDataFolders/Offtake_Monthly/offtake_store_article_*.csv"),
              normalize_cols=["Chain Name", "Site Name", "DC Code"])
    make_view("v_primary_shipto",
              csvglob("RawDataFolders/Primary_ShipTo_Monthly/Primary_ShipTo_*.csv"),
              normalize_cols=["Chain", "Ship To Name"])

    masters = sorted((pbi / "SeedData" / "Masters").glob("*.csv"))
    for m in masters:
        tname = "m_" + re.sub(r"[^a-z0-9]+", "_", m.stem.lower()).strip("_")
        con.execute(f"""
            CREATE OR REPLACE VIEW {tname} AS
            SELECT * FROM read_csv_auto('{str(m).replace("'", "''")}',
                header=true, all_varchar=false, sample_size=-1)
        """)
        log.append(f"{tname}: {m.name}")

    log += _build_unmapped_staging(con)
    con.close()
    return log


def _build_unmapped_staging(con) -> list[str]:
    """DATA CONTRACT missing-mapping guard: rows whose Chain/Store/Article
    key is absent from the active masters are never dropped — each unmapped
    value is quarantined into `unmapped_staging` (one row per distinct
    unmapped entity, with row_count + NSV impact) and a structural warning
    is emitted. Store/Article guards only engage when the corresponding
    master looks real (>= 100 rows) — the committed seeds are small samples
    and would otherwise flag everything."""
    log: list[str] = []
    parts = [
        ("offtake", "chain", "v_offtake", "Chain Name", "NSV",
         "m_chainmaster", "Chain", 0),
        ("primary", "chain", "v_primary_article", "Chain name", "sale in lac",
         "m_chainmaster", "Chain", 0),
        ("offtake", "store", "v_offtake", "Site Code", "NSV",
         "m_storemaster", "Store Code", 100),
        ("offtake", "article", "v_offtake", "Article", "NSV",
         "m_articlemaster", "Article Code", 100),
    ]
    selects = []
    for feed, kind, view, key, val, master, mkey, min_rows in parts:
        try:
            if con.execute(f"SELECT count(*) FROM {master}").fetchone()[0] < min_rows:
                continue
            con.execute(f'SELECT "{key}" FROM {view} LIMIT 0')
            selects.append(f"""
                SELECT '{feed}' AS source_feed, '{kind}' AS unmapped_kind,
                       upper(trim(CAST("{key}" AS VARCHAR))) AS unmapped_value,
                       count(*) AS row_count, round(sum("{val}"), 2) AS nsv_lakh
                FROM {view}
                WHERE upper(trim(CAST("{key}" AS VARCHAR))) NOT IN
                      (SELECT upper(trim(CAST("{mkey}" AS VARCHAR)))
                       FROM {master} WHERE "{mkey}" IS NOT NULL)
                GROUP BY 1, 2, 3""")
        except Exception:
            continue
    if not selects:
        con.execute("CREATE OR REPLACE TABLE unmapped_staging AS "
                    "SELECT '' AS source_feed, '' AS unmapped_kind, "
                    "'' AS unmapped_value, 0 AS row_count, 0.0 AS nsv_lakh "
                    "WHERE false")
        log.append("unmapped_staging: no mapping checks ran (masters missing)")
        return log
    con.execute("CREATE OR REPLACE TABLE unmapped_staging AS "
                + " UNION ALL ".join(selects))
    rows = con.execute("""
        SELECT source_feed, unmapped_kind, count(*) AS entities,
               sum(row_count) AS rows_hit, round(sum(nsv_lakh), 1) AS nsv
        FROM unmapped_staging GROUP BY 1, 2 ORDER BY 1, 2""").fetchall()
    if rows:
        for feed, kind, ents, hit, nsv in rows:
            log.append(f"STRUCTURAL WARNING: {ents} unmapped {kind}(s) in "
                       f"{feed} ({hit} rows, {nsv} Lakh) — rows kept, see "
                       "unmapped_staging")
    else:
        log.append("unmapped_staging: clean — every key maps to the masters")
    return log


def run_sql(cfg: Config, sql: str) -> tuple[list[str], list[tuple]]:
    con = connect(cfg)
    try:
        cur = con.execute(sql)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
    finally:
        con.close()
    return cols, rows


def format_table(cols: list[str], rows: list[tuple], max_rows: int = 50) -> str:
    shown = rows[:max_rows]
    cells = [[("" if v is None else str(v)) for v in r] for r in shown]
    widths = [max([len(c)] + [len(row[i]) for row in cells])
              for i, c in enumerate(cols)]
    def fmt(row):
        return " | ".join(v.ljust(w) for v, w in zip(row, widths))
    out = [fmt(cols), "-+-".join("-" * w for w in widths)]
    out += [fmt(r) for r in cells]
    if len(rows) > max_rows:
        out.append(f"... {len(rows) - max_rows} more row(s)")
    return "\n".join(out)

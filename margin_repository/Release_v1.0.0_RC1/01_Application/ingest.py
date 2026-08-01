# -*- coding: utf-8 -*-
"""Normalize a raw commercial source file into repository columns.

Handles messy headers (via schema.HEADER_ALIASES), auto-detects the header
row, keeps every original row, and fills the standard column set. Supports
.xlsx/.xlsm/.xls/.xlsb/.csv. Unmapped source columns are preserved in a
`_Unmapped` note so nothing is lost.
"""
import os
import pandas as pd
from schema import REPO_COLS, canon_header, ARTICLE_COLS, COMMERCIAL_COLS, CONDITION_COLS, DATE_COLS

READERS = {
    ".xlsx": dict(engine="openpyxl"), ".xlsm": dict(engine="openpyxl"),
    ".xlsb": dict(engine="pyxlsb"), ".xls": dict(engine=None), ".csv": None,
}
SOURCE_COLS = ARTICLE_COLS + COMMERCIAL_COLS + CONDITION_COLS + DATE_COLS


def _read_raw(path, sheet=0):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return pd.read_csv(path, header=None, dtype=str, keep_default_na=False)
    kw = READERS.get(ext, dict(engine="openpyxl"))
    return pd.read_excel(path, sheet_name=sheet, header=None,
                         **({} if kw is None else kw))


def _detect_header_row(raw, max_scan=15):
    """Best header row = the row whose cells map to the most known columns."""
    best, best_score = 0, -1
    for i in range(min(max_scan, len(raw))):
        vals = [canon_header(v) for v in raw.iloc[i].tolist()]
        score = sum(1 for v in vals if v in SOURCE_COLS)
        if score > best_score:
            best, best_score = i, score
    return best, best_score


def normalize_file(path, sheet=0):
    raw = _read_raw(path, sheet)
    if raw.empty:
        return pd.DataFrame(columns=REPO_COLS), {"rows": 0, "header_row": None, "mapped": 0}
    hrow, score = _detect_header_row(raw)
    headers = [canon_header(v) for v in raw.iloc[hrow].tolist()]
    body = raw.iloc[hrow + 1:].copy()
    body.columns = headers
    # drop fully blank rows
    body = body.dropna(how="all")
    body = body[~body.apply(lambda r: all(str(x).strip() == "" for x in r), axis=1)]

    mapped = [h for h in headers if h in SOURCE_COLS]
    unmapped = [h for h in headers if h not in SOURCE_COLS and h is not None]

    out = pd.DataFrame(index=body.index)
    for c in REPO_COLS:
        if c in body.columns:
            # if duplicate mapped headers, take first
            col = body[c]
            out[c] = col.iloc[:, 0] if isinstance(col, pd.DataFrame) else col
        else:
            out[c] = ""
    # preserve unmapped content for audit
    if unmapped:
        def note(r):
            return "; ".join("%s=%s" % (u, r[u]) for u in unmapped
                             if str(r[u]).strip() != "")
        out["_Unmapped"] = body.apply(note, axis=1)
    out = out.reset_index(drop=True)
    meta = {"rows": len(out), "header_row": hrow, "mapped": len(mapped),
            "mapped_cols": mapped, "unmapped_cols": unmapped, "header_score": score}
    return out, meta

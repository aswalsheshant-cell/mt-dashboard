# -*- coding: utf-8 -*-
"""Core append-only Chain x Article Margin Repository.

Guarantees (non-negotiables from the charter):
  * Never overwrites a historical record - every change appends a new version.
  * EAN is the primary identifier (article key prefers EAN, falls back only
    when EAN is blank, and flags it).
  * Full audit trail: Source_File, Import_Batch_Id, timestamp, Version_Number,
    Change_Type per row.
  * Rollback to any prior version via immutable per-import snapshots.

Durable store = an append-only CSV (`repository_history.csv`) holding EVERY
version ever seen. The "current" view is derived (latest published version per
article key). Excel outputs are always regenerated, never the source of truth.
"""
import os, hashlib, uuid, datetime as dt, json
import pandas as pd
from schema import (REPO_COLS, ARTICLE_KEY_EAN, ARTICLE_KEY_FALLBACK,
                    COMMERCIAL_COMPONENTS, COMMERCIAL_PCT_COLS, NUMERIC_COLS)
from validation import validate_frame

HIST_FILE = "repository_history.csv"
SNAP_DIR = "snapshots"
CHANGELOG_DIR = "change_logs"
MANIFEST_DIR = "manifests"
SCHEMA_VERSION = "1.1.0"

# fields whose change triggers a new version + change-log entries
TRACKED_FIELDS = COMMERCIAL_PCT_COLS + ["Final Effective Margin %", "MRP", "GST %",
                                        "EAN", "Effective To", "Approval Status", "Status"]


def _s(v):
    return "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()


def article_key(row):
    """EAN-priority article identity. Returns (key_string, used_fallback)."""
    ean = _s(row.get("EAN"))
    if ean:
        parts = [_s(row.get("Chain")).upper(), ean, _s(row.get("Pack Size")).upper(),
                 _s(row.get("MRP"))]
        return "EAN|" + "||".join(parts), False
    parts = [_s(row.get(c)).upper() for c in ARTICLE_KEY_FALLBACK]
    return "ALT|" + "||".join(parts), True


def record_key(row):
    h = "||".join(_s(row.get(c)) for c in
                  ["Chain", "Brand", "Category", "Sub Category", "Article",
                   "EAN", "Pack Size", "MRP", "Effective From", "Version Number"])
    return hashlib.sha1(h.encode("utf-8")).hexdigest()[:16]


def coerce_numeric(df):
    df = df.copy()
    for c in NUMERIC_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(
                df[c].map(lambda x: str(x).replace("%", "").replace(",", "").strip()
                          if x is not None and str(x).strip() != "" else None),
                errors="coerce").astype("float64")
    return df


def derive_final_margin(df):
    """Fill Final Effective Margin % only where the source left it blank,
    using the documented component sign map. Provided values are respected."""
    df = df.copy()
    computed = pd.Series(0.0, index=df.index)
    for col, sign in COMMERCIAL_COMPONENTS:
        if col in df.columns:
            computed = computed + sign * pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "Final Effective Margin %" in df.columns:
        provided = pd.to_numeric(df["Final Effective Margin %"], errors="coerce")
    else:
        provided = pd.Series([None] * len(df), index=df.index)
    df["Final Effective Margin %"] = provided.where(provided.notna(), computed.round(2))
    return df


def file_checksum(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


class MarginRepository:
    def __init__(self, root):
        self.root = root
        os.makedirs(root, exist_ok=True)
        os.makedirs(os.path.join(root, SNAP_DIR), exist_ok=True)
        os.makedirs(os.path.join(root, CHANGELOG_DIR), exist_ok=True)
        os.makedirs(os.path.join(root, MANIFEST_DIR), exist_ok=True)
        self.hist_path = os.path.join(root, HIST_FILE)
        self.history = self._load()
        self._imported_checksums = self._load_checksums()

    def _load_checksums(self):
        path = os.path.join(self.root, "imported_checksums.json")
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    def _save_checksums(self):
        path = os.path.join(self.root, "imported_checksums.json")
        with open(path, "w") as f:
            json.dump(self._imported_checksums, f, indent=2)

    def check_duplicate_import(self, source_path):
        cs = file_checksum(source_path)
        prev = self._imported_checksums.get(cs)
        return prev, cs

    def _load(self):
        if os.path.exists(self.hist_path):
            return pd.read_csv(self.hist_path, dtype=str, keep_default_na=False)
        return pd.DataFrame(columns=REPO_COLS)

    def _persist(self):
        for c in REPO_COLS:
            if c not in self.history.columns:
                self.history[c] = ""
        self.history[REPO_COLS].to_csv(self.hist_path, index=False)

    # ---- current view: latest published version per article key ----
    def current(self, include_held=False):
        h = self.history.copy()
        if h.empty:
            return h
        h["_v"] = pd.to_numeric(h["Version Number"], errors="coerce").fillna(0)
        if not include_held:
            h = h[h["Record_Status"] == "PUBLISHED"]
        if h.empty:
            return h
        h = h.sort_values("_v").groupby("Article_Key", as_index=False).tail(1)
        return h.drop(columns="_v")

    def _latest_version_map(self):
        if self.history.empty:
            return {}, {}
        h = self.history.copy()
        h["_v"] = pd.to_numeric(h["Version Number"], errors="coerce").fillna(0)
        latest = h.sort_values("_v").groupby("Article_Key").tail(1)
        vmap = dict(zip(latest["Article_Key"], latest["_v"].astype(int)))
        rowmap = {r["Article_Key"]: r for _, r in latest.iterrows()}
        return vmap, rowmap

    # -------------------------------------------------------------------
    # Import a normalized frame -> validate, version, append, change-log.
    # -------------------------------------------------------------------
    def import_frame(self, df, source_file, today=None, source_path=None,
                     submitted_by="", business_owner=""):
        batch = dt.datetime.now().strftime("B%Y%m%d%H%M%S-") + uuid.uuid4().hex[:6]
        ts = dt.datetime.now().isoformat(timespec="seconds")

        # backup before import
        if not self.history.empty:
            self._snapshot("PRE-IMPORT-" + batch)

        df = coerce_numeric(df)
        df = derive_final_margin(df)
        df = validate_frame(df, today=today)

        akeys, fallbacks = [], []
        for _, r in df.iterrows():
            k, fb = article_key(r)
            akeys.append(k); fallbacks.append(fb)
        df["Article_Key"] = akeys

        vmap, rowmap = self._latest_version_map()
        changelog = []
        out_rows = []
        for i, r in df.reset_index(drop=True).iterrows():
            ak = r["Article_Key"]
            prev_v = vmap.get(ak, 0)
            prev = rowmap.get(ak)
            # determine change type + version
            if prev is None:
                change_type, new_v, changed = "NEW", 1, []
            else:
                changed = []
                for fld in TRACKED_FIELDS:
                    ov, nv = _s(prev.get(fld)), _s(r.get(fld))
                    # numeric-aware compare
                    try:
                        if ov != "" or nv != "":
                            if float(ov or 0) != float(nv or 0):
                                changed.append((fld, ov, nv))
                            continue
                    except ValueError:
                        pass
                    if ov != nv:
                        changed.append((fld, ov, nv))
                if changed:
                    change_type, new_v = "CHANGED", prev_v + 1
                else:
                    change_type, new_v = "UNCHANGED", prev_v  # no new version stored
            rr = {c: r.get(c, "") for c in REPO_COLS if c in r.index}
            rr.update({
                "Article_Key": ak, "Source_File": source_file, "Import_Batch_Id": batch,
                "Import_Timestamp": ts, "Change_Type": change_type,
                "Version Number": new_v, "Is_Current": "Y",
                "Submitted_By": submitted_by, "Submitted_Date": ts,
                "Business_Owner": business_owner,
            })
            rr["Record_Key"] = record_key(rr)
            if change_type == "UNCHANGED":
                continue  # never duplicate an identical version
            out_rows.append(rr)
            for fld, ov, nv in changed:
                try:
                    diff = float(nv or 0) - float(ov or 0)
                    diff = round(diff, 2)
                except ValueError:
                    diff = ""
                changelog.append({
                    "Article_Key": ak, "Chain": r.get("Chain"), "Brand": r.get("Brand"),
                    "Article": r.get("Article"), "EAN": r.get("EAN"), "Field": fld,
                    "Old Value": ov, "New Value": nv, "Difference": diff,
                    "Change Type": change_type, "Version": new_v,
                    "Effective From": r.get("Effective From"),
                    "Reason": r.get("Approval Status") or "Imported commercial update",
                    "Source_File": source_file, "Import_Batch_Id": batch,
                    "Logged_At": ts,
                })

        added = pd.DataFrame(out_rows)
        # mark superseded rows Is_Current=N for keys we versioned up
        if not added.empty and not self.history.empty:
            bumped = set(added.loc[added["Change_Type"] == "CHANGED", "Article_Key"])
            self.history.loc[self.history["Article_Key"].isin(bumped), "Is_Current"] = "N"

        self.history = pd.concat([self.history, added], ignore_index=True) if not added.empty \
            else self.history
        # detect removed articles (in repo current, absent from this file) - reported, NOT deleted
        removed = self._detect_removed(df, source_file)
        self._persist()
        self._snapshot(batch)

        cl = pd.DataFrame(changelog)
        if not cl.empty:
            cl.to_csv(os.path.join(self.root, CHANGELOG_DIR, batch + "_changelog.csv"), index=False)

        n_new = int((added["Change_Type"] == "NEW").sum()) if not added.empty else 0
        n_changed = int((added["Change_Type"] == "CHANGED").sum()) if not added.empty else 0
        n_unchanged = int(len(df) - len(added))
        n_warning = int((df["QC_Severity"] == "WARNING").sum())
        n_fail = int((df["QC_Severity"] == "FAIL").sum())
        n_blocked = int((df["QC_Severity"] == "BLOCKED").sum())
        n_pass = int((df["QC_Severity"] == "PASS").sum())
        n_fallback = int(sum(fallbacks))
        n_published = int((df["Record_Status"] == "PUBLISHED").sum())
        n_held = int((df["Record_Status"] == "HELD").sum())

        # reconciliation: source rows must equal the sum of outcomes
        recon_sum = n_new + n_changed + n_unchanged
        recon_diff = len(df) - recon_sum

        summary = {
            "batch": batch, "source_file": source_file, "schema_version": SCHEMA_VERSION,
            "rows_in_file": len(df),
            "new": n_new, "changed": n_changed, "unchanged": n_unchanged,
            "pass": n_pass, "warning": n_warning, "fail": n_fail, "blocked": n_blocked,
            "published_forecast_ready": n_published, "held": n_held,
            "fallback_article_keys": n_fallback,
            "removed_from_file": len(removed),
            "changelog_entries": len(cl),
            "reconciliation_diff": recon_diff,
        }

        # write import manifest
        manifest = {**summary, "timestamp": ts, "submitted_by": submitted_by}
        mpath = os.path.join(self.root, MANIFEST_DIR, batch + "_manifest.json")
        with open(mpath, "w") as f:
            json.dump(manifest, f, indent=2)

        # register checksum
        if source_path and os.path.exists(source_path):
            cs = file_checksum(source_path)
            self._imported_checksums[cs] = {"batch": batch, "file": source_file, "ts": ts}
            self._save_checksums()

        return summary, cl, removed

    def _detect_removed(self, incoming, source_file):
        cur = self.current()
        if cur.empty:
            return pd.DataFrame(columns=["Article_Key", "Chain", "Article", "EAN"])
        incoming_keys = set(incoming["Article_Key"])
        # only compare within chains present in this file
        chains = set(incoming["Chain"].map(_s).str.upper())
        cur = cur[cur["Chain"].map(lambda x: _s(x).upper()).isin(chains)]
        gone = cur[~cur["Article_Key"].isin(incoming_keys)]
        return gone[["Article_Key", "Chain", "Article", "EAN", "Version Number"]].copy()

    def _snapshot(self, batch):
        path = os.path.join(self.root, SNAP_DIR, batch + ".csv")
        self.history[REPO_COLS].to_csv(path, index=False)

    # ---- rollback: restore repository state to a prior snapshot ----
    def list_versions(self):
        snaps = sorted(f for f in os.listdir(os.path.join(self.root, SNAP_DIR))
                       if f.endswith(".csv"))
        return [s[:-4] for s in snaps]

    def rollback(self, batch):
        path = os.path.join(self.root, SNAP_DIR, batch + ".csv")
        if not os.path.exists(path):
            raise FileNotFoundError("No snapshot for batch %s" % batch)
        # rollback itself is non-destructive: archive current first
        self._snapshot("PRE-ROLLBACK-" + dt.datetime.now().strftime("%Y%m%d%H%M%S"))
        self.history = pd.read_csv(path, dtype=str, keep_default_na=False)
        self._persist()
        return len(self.history)

"""B5 on Power BI Service: run the governed CM2 / rolling-average DAX cases through the ExecuteQueries REST API
and hand the raw results to scripts/b5_evidence.py (which applies the run sheet's PASS rules).

*** UNTESTED against a real workspace. *** It was written without a Power BI tenant. The unit tests use a fake
HTTP layer. Your first run is its first test: read the console output, and if anything looks off, stop and send it.

Owner decision 2026-10-11: B5 may be measured on a published, refreshed copy of the model instead of Desktop.
The evidence file says it was measured on the Service. Everything else about B5 is unchanged.

What you need
  1. The model published to a workspace, built from the frozen main SHA (Desktop or Tabular Editor deploy), and refreshed
     there. The last refresh must be Completed; the script checks it and refuses otherwise.
     Our queries read a local folder (pRootFolder): the Service needs a gateway or a SharePoint/OneDrive copy to refresh.
  2. Build permission on the dataset. Workspace id and dataset id are in the dataset URL.
  3. An access token for https://analysis.windows.net/powerbi/api in the environment variable PBI_ACCESS_TOKEN, for example
       az account get-access-token --resource https://analysis.windows.net/powerbi/api --query accessToken -o tsv
     The token is read from the environment only. It is never printed, never written to a file.

What it does not do
  * It cannot run the FY parser (Power Query M, not DAX). Run tests/powerbi/pq39_fy_parser_cases.pq in Power Query Online
    or Desktop and pass --fy-parser-failures N --attested-by "<name>". Without them that row stays NOT_RUN.
  * It cannot take screenshots. Attach one per step, as the run sheet requires.
  * It does not decide PASS or FAIL: scripts/b5_evidence.py does.

Usage
  git checkout <frozen SHA>   # clean tree
  set PBI_ACCESS_TOKEN=...    (PowerShell: $env:PBI_ACCESS_TOKEN = "...")
  python scripts/b5_execute_queries.py --workspace-id <guid> --dataset-id <guid> --published-from-sha <short SHA> --refreshed \\
      --run-by "MT Channel Analyst Lead" --fy-parser-failures 0 --attested-by "<name>" --expect-sha <frozen SHA>
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import b5_evidence as b5  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
API = "https://api.powerbi.com/v1.0/myorg"
PAUSE = 0.6          # the API allows about 120 requests a minute per user
RETRIES = 3


def http(method, url, token, body=None):
    """One HTTP call -> (status, parsed json or None, headers). Replaced by a fake in tests."""
    data = None if body is None else json.dumps(body).encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers={
        "Authorization": "Bearer " + token, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            raw = r.read()
            return r.status, (json.loads(raw.decode("utf-8-sig")) if raw else None), dict(r.headers)
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            parsed = json.loads(raw.decode("utf-8-sig")) if raw else None
        except ValueError:
            parsed = {"raw": raw[:300].decode("utf-8", "replace")}
        return e.code, parsed, dict(e.headers or {})


def to_table(resp):
    """ExecuteQueries response -> {columns, rows} (rows stay dicts keyed like '[Col]' or 'Table[Col]')."""
    tables = ((resp or {}).get("results") or [{}])[0].get("tables") or []
    rows = (tables[0].get("rows") if tables else None) or []
    cols = list(rows[0].keys()) if rows else []
    return {"columns": cols, "rows": rows}


def run_query(token, ws, ds, text, send=http, sleep=time.sleep):
    url = f"{API}/groups/{ws}/datasets/{ds}/executeQueries"
    body = {"queries": [{"query": text}], "serializerSettings": {"includeNulls": True}}
    for attempt in range(RETRIES + 1):
        status, resp, hdr = send("POST", url, token, body)
        if status == 200:
            err = ((resp or {}).get("results") or [{}])[0].get("error")
            if err:
                raise RuntimeError("DAX error: " + json.dumps(err)[:300])
            return to_table(resp)
        if status == 429 and attempt < RETRIES:
            sleep(float(hdr.get("Retry-After", 5)))
            continue
        raise RuntimeError(f"HTTP {status}: {json.dumps(resp)[:300]}")


def dataset_facts(token, ws, ds, send=http):
    s, d, _ = send("GET", f"{API}/groups/{ws}/datasets/{ds}", token)
    if s != 200:
        raise SystemExit(f"cannot read the dataset (HTTP {s}). Check ids and Build permission.")
    s, r, _ = send("GET", f"{API}/groups/{ws}/datasets/{ds}/refreshes?$top=1", token)
    last = ((r or {}).get("value") or [{}])[0] if s == 200 else {}
    return d.get("name", ""), last.get("status", ""), last.get("endTime", "")


def git_state(root=ROOT):
    sha = subprocess.run(["git", "-C", str(root), "rev-parse", "--short", "HEAD"], capture_output=True, text=True).stdout.strip()
    dirty = bool(subprocess.run(["git", "-C", str(root), "status", "--porcelain", "--untracked-files=no"],
                                capture_output=True, text=True).stdout.strip())
    return sha, dirty


def build_doc(token, a, send=http, sleep=time.sleep, git=git_state):
    name, status, end = dataset_facts(token, a.workspace_id, a.dataset_id, send)
    sha, dirty = git()
    queries = b5.collect_queries()
    cases, errors = {}, {}
    for key, text in queries.items():
        try:
            cases[key] = run_query(token, a.workspace_id, a.dataset_id, text, send, sleep)
            print(f"  {key:<14} {len(cases[key]['rows'])} row(s)")
        except Exception as e:  # one failing block must not hide the others; its row reads NOT_RUN
            errors[key] = str(e)
            print(f"  {key:<14} ERROR: {e}")
        sleep(PAUSE)
    meta = {"source": b5.SERVICE_SOURCE, "database": name, "workspace_id": a.workspace_id, "dataset_id": a.dataset_id,
            "git_sha": sha, "git_dirty": dirty, "published_from_sha": a.published_from_sha,
            "model_file": a.model_file or name, "utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "last_refresh_utc": end, "last_refresh_status": status}
    return {"meta": meta, "queries": queries, "cases": cases, "errors": errors}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--workspace-id", required=True)
    ap.add_argument("--dataset-id", required=True)
    ap.add_argument("--published-from-sha", required=True, help="the SHA the published model was built from")
    ap.add_argument("--model-file", default="", help="name of the published model (default: the dataset name)")
    ap.add_argument("--results-path", default="", help="where to keep results.json (default: a temp folder, outside the repo)")
    ap.add_argument("--run-by")
    ap.add_argument("--fy-parser-failures", type=int, metavar="N")
    ap.add_argument("--attested-by")
    ap.add_argument("--expect-sha", required=True, help="the frozen SHA (required: the run is only evidence for that commit)")
    ap.add_argument("--refreshed", action="store_true", required=True,
                    help="attest that you refreshed the published model after publishing it from the frozen SHA")
    ap.add_argument("--allow-dirty", action="store_true")
    ap.add_argument("--skip-evidence", action="store_true")
    a = ap.parse_args(argv)
    token = os.environ.get("PBI_ACCESS_TOKEN", "").strip()
    if not token:
        print("PBI_ACCESS_TOKEN is not set (see the usage note at the top of this file).", file=sys.stderr)
        return 2
    print("=== B5 on Power BI Service (UNTESTED against a real workspace: your first run is its first test) ===")
    doc = build_doc(token, a)
    path = Path(a.results_path) if a.results_path else Path(tempfile.mkdtemp(prefix="b5_service_")) / "results.json"
    raw = json.dumps(doc, indent=2, default=str).encode("utf-8")
    path.write_bytes(raw)
    print(f"Raw results written to {path} (keep it with the screenshots; it holds business numbers)")
    if doc["errors"]:
        print(f"WARNING: {len(doc['errors'])} query(ies) failed; their rows will read NOT_RUN.")
    if a.skip_evidence:
        return 0
    if doc["errors"]:
        print("Evidence NOT written: some queries failed (token expired? throttled?). Fix that and re-run; "
              "a partial evidence file would block a same-day re-run.")
        return 1
    try:
        out = b5.write_evidence(doc, raw_sha256=hashlib.sha256(raw).hexdigest(), run_by=a.run_by, refreshed=a.refreshed,
                                fy_parser_failures=a.fy_parser_failures, attested_by=a.attested_by,
                                allow_dirty=a.allow_dirty, expect_sha=a.expect_sha)
    except b5.EvidenceRefused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 3
    rows = b5.evaluate_all(doc, manual_fy_failures=a.fy_parser_failures, attested_by=a.attested_by)
    print(f"wrote {out}")
    for rid in b5.ROW_IDS:
        print(f"  row {rid:>3}: {rows[rid].status:<14} {rows[rid].actual}")
    ok = all(rows[r].status == "PASS" for r in b5.REQUIRED_PASS) and rows["3"].status in ("PASS", "NOT_EXERCISED")
    print("ALL REQUIRED ROWS PASS - attach screenshots, then a human sets the verdict to CLEARED." if ok
          else "NOT ALL ROWS PASS - B5 stays OPEN.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())

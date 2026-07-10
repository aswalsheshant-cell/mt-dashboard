"""
Phase 6 — the template fill engine.

Binds a TemplateSpec to the source files the user supplies and produces a filled,
leadership-ready Report plus an audit sheet, source provenance, and a QC report.

Hard rules enforced here:
  * Every number comes from a real query on a provided source file. If a required
    dataset/period is missing, the figure is the SOURCE_REQUIRED sentinel — never
    a guessed value (rule 10).
  * 'Others' is hidden from the visible breakdown but kept in the totals (rule 5).
  * Growth is carried as a signed % so renderers colour it green/red (rule 6).
  * Audit + provenance record which files/sheets/columns/filters were used or
    excluded and why (rules 2-4).
  * QC runs before the report is considered final (rule 9).
Structure, framing and action-owner logic come from the template (memory); values
never do.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from ai_analyst.data_layer import DataLayer, sanitize_identifier
from ai_analyst.report import Report
from ai_analyst.templates import TemplateSpec, get_template
from ai_analyst.provenance import Provenance, Metric, ProvenanceLog, SOURCE_REQUIRED
from ai_analyst.qc import QCContext, run_qc, qc_status, QCCheck


def _cr(value: Optional[float], unit: str) -> Optional[float]:
    if value is None:
        return None
    return value / 1e7 if unit == "Cr" else value


@dataclass
class FilledReport:
    report: Report
    qc_checks: List[QCCheck]
    qc_headline: str
    provenance: ProvenanceLog
    considered: List[list]
    not_considered: List[list]
    available: bool

    def save(self, path) -> str:
        return self.report.save(path)


class TemplateFiller:
    def __init__(self, engine: str = "auto"):
        self.engine = engine

    # -- helpers -----------------------------------------------------------
    def _sum(self, dl: DataLayer, table: str, col: str, where: str = "") -> Optional[float]:
        if col not in (dl.table(table).columns if dl.table(table) else []):
            return None
        _, rows = dl.run_sql(
            f'SELECT SUM(CAST(NULLIF("{col}",\'\') AS REAL)) FROM "{table}" {where}')
        return rows[0][0] if rows and rows[0][0] is not None else 0.0

    def _breakdown(self, dl: DataLayer, table: str, dim: str, col: str,
                   where: str = "") -> List[tuple]:
        cols = dl.table(table).columns if dl.table(table) else []
        if dim not in cols or col not in cols:
            return []
        _, rows = dl.run_sql(
            f'SELECT "{dim}", SUM(CAST(NULLIF("{col}",\'\') AS REAL)) AS v '
            f'FROM "{table}" {where} GROUP BY "{dim}" ORDER BY v DESC')
        return [(r[0], r[1] or 0.0) for r in rows]

    # -- main --------------------------------------------------------------
    def fill(self, template_key: str, sources: Dict[str, Dict[str, str]],
             period: str, compare: Optional[str] = None) -> FilledReport:
        spec: TemplateSpec = get_template(template_key)
        dl = DataLayer(engine=self.engine)
        prov = ProvenanceLog()
        considered: List[list] = []
        not_considered: List[list] = []

        # --- load required datasets ---
        loaded: Dict[str, Dict[str, str]] = {}   # dataset -> {period: table}
        for ds in spec.required_datasets:
            files = sources.get(ds) or {}
            if not files:
                not_considered.append(["Not Considered", ds, "(none)", "-", "-", "-", "-",
                                       "Required source file not provided"])
                continue
            loaded[ds] = {}
            for per, path in files.items():
                tbl = f"{ds}_{sanitize_identifier(per)}"
                t = dl.load_csv(path, table=tbl)
                loaded[ds][per] = tbl
                filt = "MT offtake (whole file); period tagged from filename " \
                       "(source 'month' column unreliable)"
                if spec.channel_column:
                    filt = f"WHERE {spec.channel_column}=MT (GT excluded)"
                considered.append(["Considered", ds, Path(path).name, "(CSV)", t.nrows,
                                   ", ".join(m.key for m in spec.measures), filt,
                                   f"Period {per}"])

        primary_ds = spec.required_datasets[0]
        have_primary = primary_ds in loaded and period in loaded[primary_ds]
        rep = Report(spec.name, subtitle=f"Period: {period}"
                     + (f"  |  Compare: {compare}" if compare else ""),
                     classification=spec.classification)

        metrics: List[Metric] = []
        qc = QCContext(period=period, compare_period=compare)

        if not have_primary:
            # rule 10 — build the structure, mark values required, still audit + QC
            rep.add_kpis([(m.label, SOURCE_REQUIRED) for m in spec.measures],
                         title="Headline (source required)")
            rep.add_text(
                f"Required dataset '{primary_ds}' for {period} was not provided, so no "
                f"figures were computed. Supply the source file to populate this report.",
                title="Status")
            self._add_action_tracker(rep, [])
            self._add_audit(rep, considered, not_considered)
            self._add_provenance(rep, prov)
            checks = run_qc(qc)
            self._add_qc(rep, checks)
            return FilledReport(rep, checks, qc_status(checks), prov, considered,
                                not_considered, available=False)

        table = loaded[primary_ds][period]
        where = ""
        if spec.channel_column and spec.channel_column in dl.table(table).columns:
            where = f'WHERE UPPER("{spec.channel_column}")=\'MT\''

        measure = spec.measures[0]
        src_name = Path(sources[primary_ds][period]).name

        # --- headline measures (period + compare + MoM) ---
        total = self._sum(dl, table, measure.key, where)
        kpis: List[tuple] = []
        compare_total = None
        if compare and primary_ds in loaded and compare in loaded[primary_ds]:
            ctbl = loaded[primary_ds][compare]
            compare_total = self._sum(dl, ctbl, measure.key, where)

        for m in spec.measures:
            v = self._sum(dl, table, m.key, where)
            met = Metric(m.label, _cr(v, m.unit) if v is not None else SOURCE_REQUIRED,
                         Provenance(src_name, column=m.key,
                                    filter=(where or "MT offtake (whole file)"),
                                    calc=f"SUM({m.key})" + (" / 1e7 -> Cr" if m.unit == "Cr" else "")),
                         unit=m.unit)
            metrics.append(met)
            prov.record(met)
            kpis.append((m.label, met.display()))

        mom = None
        if compare_total not in (None, 0):
            mom = (total - compare_total) / compare_total * 100.0
            mom_met = Metric(f"MoM ({period} vs {compare})", mom,
                             Provenance(src_name, column=measure.key,
                                        filter=where or "MT offtake",
                                        calc=f"(cur-prev)/prev*100 on SUM({measure.key})"),
                             unit="%")
            metrics.append(mom_met); prov.record(mom_met)
            kpis.append((f"MoM {measure.label}", mom_met.display()))
        rep.add_kpis(kpis, title=f"Headline — {period}")

        # --- category breakdown (hide Others, keep in total) ---
        dim = spec.breakdowns[0]
        full = self._breakdown(dl, table, dim.key, measure.key, where)
        grand = sum(v for _, v in full)
        cmp_map = {}
        if compare and compare in loaded.get(primary_ds, {}):
            cmp_map = {k: v for k, v in self._breakdown(
                dl, loaded[primary_ds][compare], dim.key, measure.key, where)}

        rows = []
        visible_total = 0.0
        for name, v in full:
            is_others = str(name).strip().lower() == "others"
            contrib = (v / grand * 100.0) if grand else 0.0
            cat_mom = ""
            if name in cmp_map and cmp_map[name]:
                cat_mom = f"{(v - cmp_map[name]) / cmp_map[name] * 100.0:+.1f}%"
            if not is_others:
                visible_total += v
                rows.append([name, f"{_cr(v, measure.unit):,.2f}", f"{contrib:.1f}%", cat_mom])
        rep.add_table(
            [dim.label, f"{measure.label} (Cr)", "Contribution %", f"MoM %"],
            rows,
            title=f"{measure.label} by {dim.label}",
            note=(f"'Others' hidden from view but included in totals. "
                  f"Grand total (incl Others): ₹{_cr(grand, measure.unit):,.2f} Cr."),
            growth_col=3,
        )

        # --- insights (derived from the real numbers) ---
        rep.add_text(self._insights(spec, period, compare, total, compare_total, mom,
                                    full, grand, measure), title="Leadership insights")

        # --- action tracker (structure from template, findings from data) ---
        self._add_action_tracker(rep, self._actions(full, cmp_map, grand, measure))

        # --- QC context from real figures ---
        dup_count = self._duplicates(dl, table)
        blank_cat = self._count_blank(dl, table, dim.key)
        blank_chain = self._count_blank(dl, table, "chain_name")
        blank_article = self._count_blank(dl, table, "article")
        qc.grand_total = grand
        qc.breakdown_total = sum(v for _, v in full)
        qc.period_totals = {period: total}
        if compare_total is not None:
            qc.period_totals[compare] = compare_total
        qc.reported_mom = mom
        qc.contribution_sum = sum((v / grand * 100.0) for _, v in full) if grand else None
        qc.duplicate_count = dup_count
        qc.missing_mapping = blank_cat
        qc.unmapped_chain = blank_chain
        qc.unmapped_article = blank_article
        if spec.channel_column and spec.channel_column in dl.table(table).columns:
            gt = self._count_where(dl, table, f'UPPER("{spec.channel_column}")<>\'MT\'')
            qc.channel_ok = (gt == 0)
            qc.channel_note = f"{gt} non-MT row(s) after filter"
        else:
            qc.channel_note = "offtake source is MT-only by construction (no channel column)"

        self._add_audit(rep, considered, not_considered)
        self._add_provenance(rep, prov)
        checks = run_qc(qc)
        self._add_qc(rep, checks)

        fr = FilledReport(rep, checks, qc_status(checks), prov, considered,
                          not_considered, available=True)
        dl.close()
        return fr

    # -- section builders --------------------------------------------------
    def _insights(self, spec, period, compare, total, compare_total, mom, full, grand, measure) -> str:
        lines = []
        cr = _cr(total, measure.unit)
        head = f"Total MT {measure.label} for {period} was ₹{cr:,.2f} Cr"
        if mom is not None:
            direction = "up" if mom > 0 else "down"
            head += f", {direction} {abs(mom):.1f}% vs {compare} (₹{_cr(compare_total, measure.unit):,.2f} Cr)"
        lines.append(head + ".")
        visible = [(n, v) for n, v in full if str(n).strip().lower() != "others"]
        if visible:
            top_n, top_v = visible[0]
            lines.append(f"{top_n} led with ₹{_cr(top_v, measure.unit):,.2f} Cr "
                         f"({top_v / grand * 100:.1f}% of MT {measure.label}).")
        return " ".join(lines)

    def _actions(self, full, cmp_map, grand, measure) -> List[list]:
        actions = []
        # data-driven: flag the largest MoM decliner among visible categories
        worst = None
        for name, v in full:
            if str(name).strip().lower() == "others":
                continue
            if name in cmp_map and cmp_map[name]:
                d = (v - cmp_map[name]) / cmp_map[name] * 100.0
                if worst is None or d < worst[1]:
                    worst = (name, d)
        if worst and worst[1] < 0:
            actions.append([f"Investigate {worst[0]} decline ({worst[1]:+.1f}% MoM)",
                            "Category Head", "High", "2 weeks"])
        if full:
            top = next((n for n, _ in full if str(n).strip().lower() != "others"), None)
            if top:
                actions.append([f"Protect momentum in {top}", "Sales Lead", "Medium", "1 month"])
        actions.append(["Validate source mapping flagged in QC", "Analytics", "Medium", "1 week"])
        return actions

    def _add_action_tracker(self, rep: Report, actions: List[list]) -> None:
        if not actions:
            actions = [["Populate once source data is provided", "Analytics", "-", "-"]]
        rep.add_table(["Action", "Owner", "Priority", "Timeline"], actions,
                      title="Action tracker")

    def _add_audit(self, rep: Report, considered, not_considered) -> None:
        cols = ["Status", "Dataset", "File", "Sheet", "Rows", "Columns used", "Filter", "Reason/Period"]
        rep.add_table(cols, considered + not_considered,
                      title="Audit — Considered / Not Considered",
                      note="Every source touched (or deliberately excluded) for this report.")

    def _add_provenance(self, rep: Report, prov: ProvenanceLog) -> None:
        cols, rows = prov.table()
        if not rows:
            rows = [["(no figures computed)", "", "", "", "", ""]]
        rep.add_table(cols, rows, title="Source provenance",
                      note="Traceability for every key number.")

    def _add_qc(self, rep: Report, checks: List[QCCheck]) -> None:
        rep.add_table(["Check", "Status", "Detail"], [c.as_row() for c in checks],
                      title=f"QC report — {qc_status(checks)}",
                      note="Run before export. NA = source data required.")

    # -- small SQL helpers -------------------------------------------------
    def _count_blank(self, dl: DataLayer, table: str, col: str) -> Optional[int]:
        if not dl.table(table) or col not in dl.table(table).columns:
            return None
        return self._count_where(dl, table, f'"{col}" IS NULL OR "{col}"=\'\'')

    def _count_where(self, dl: DataLayer, table: str, cond: str) -> int:
        _, rows = dl.run_sql(f'SELECT COUNT(*) FROM "{table}" WHERE {cond}')
        return rows[0][0]

    def _duplicates(self, dl: DataLayer, table: str) -> int:
        total = dl.table(table).nrows
        _, rows = dl.run_sql(f'SELECT COUNT(*) FROM (SELECT DISTINCT * FROM "{table}")')
        return max(0, total - rows[0][0])

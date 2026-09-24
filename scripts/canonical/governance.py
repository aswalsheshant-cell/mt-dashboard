"""Registry of approved reconciliation exceptions.

A reconciliation variance may ONLY be classified APPROVED_GOVERNED if it
matches an entry in APPROVED_EXCEPTIONS below. A variance that would
previously have been waved through with an inline reason string and no
registry entry is now UNKNOWN -- a state the release gate treats the same
as FAIL. This is the fix for "GOVERNED becoming a softer word for we
didn't reconcile this": every exception is a reviewable record with a
named owner, an explicit release-blocker call, and a resolution phase, not
just a string a metric function happened to pass in.

SELF-APPROVAL GUARD (Phase 1 Certification Gate, second review round). The
registry above closes "a free-text reason manufactures a pass" but by
itself does not close a narrower gap: a developer could still add a new
`ApprovedException(...)` entry directly in this file and thereby convert a
real reconciliation failure into APPROVED_GOVERNED with no one else ever
having reviewed it -- the code change IS the approval. That is
self-approval by another name.

The fix: four fields -- `approval_status`, `approver`, `approval_reference`,
`approved_at` -- are now required on every entry, and
`find_approved_exception()` only returns an entry when ALL FOUR are
present and `approval_status == "APPROVED"`. An entry that matches a
metric/scope but fails that check is treated exactly as if it did not
exist: the caller gets `None`, which `reconcile.py` turns into `UNKNOWN`,
never `APPROVED_GOVERNED`. Writing the code is therefore necessary but not
sufficient -- the four approval fields must ALSO be populated with a real
approver, a real reference a reviewer could go check, and a real date,
before the exception can ever fire. This does not (and structurally
cannot) verify that the named approver is who they claim to be -- that is
a code-review/branch-protection control, not something a Python dataclass
can enforce -- but it does mean an entry with blank/missing approval
fields, or one whose `approval_status` was never actually set to
"APPROVED", can never manufacture a pass merely by being merged.
"""
from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass(frozen=True)
class ApprovedException:
    exception_id: str
    metric: str
    scope_matches: Callable[[str], bool]
    scope_description: str
    reason_not_pass: str
    evidence: str
    business_impact: str
    financial_impact: str
    owner: str
    approver: str
    approval_reference: str
    approved_at: str  # ISO date, e.g. "2026-09-24"
    approval_status: str  # must be exactly "APPROVED" -- anything else is treated as unapproved
    temporary_or_permanent: str  # "TEMPORARY" | "PERMANENT"
    resolution_phase: str
    release_blocker: bool
    status: str = "APPROVED_GOVERNED"

    def is_fully_approved(self) -> bool:
        """The self-approval guard: an entry only counts as a real approval
        when every one of these is populated AND approval_status is
        literally "APPROVED" -- not merely present, e.g. a WITHDRAWN or
        PENDING status must not pass this check."""
        return (
            self.approval_status == "APPROVED"
            and bool(self.approver and self.approver.strip())
            and bool(self.approval_reference and self.approval_reference.strip())
            and bool(self.approved_at and self.approved_at.strip())
        )

    def as_dict(self):
        return {
            "exception_id": self.exception_id,
            "metric": self.metric,
            "scope": self.scope_description,
            "reason_not_pass": self.reason_not_pass,
            "evidence": self.evidence,
            "business_impact": self.business_impact,
            "financial_impact": self.financial_impact,
            "owner": self.owner,
            "approver": self.approver,
            "approval_reference": self.approval_reference,
            "approved_at": self.approved_at,
            "approval_status": self.approval_status,
            "temporary_or_permanent": self.temporary_or_permanent,
            "resolution_phase": self.resolution_phase,
            "release_blocker": "YES" if self.release_blocker else "NO",
            "status": self.status,
        }


APPROVED_EXCEPTIONS: List[ApprovedException] = [
    ApprovedException(
        exception_id="GOV-001",
        metric="CHANNEL_PRIMARY_NSV",
        scope_matches=lambda scope: "fy=FY27" in scope,
        scope_description="channel in {MT, EB2B, SIS}, fy=FY27",
        reason_not_pass=(
            "primary.by_channel (the Executive Cockpit's current data source) "
            "carries no FY27 data at all -- the pre-aggregated Primary/Offtake/"
            "P&L workbook this field is built from ends Mar'26. This is a "
            "pre-existing, documented architecture fact (CLAUDE.md's 'Coverage "
            "split'), not a defect this reconciliation discovered."
        ),
        evidence=(
            "detail_meta.channel_totals (the canonical source) DOES cover "
            "FY27 with real, non-zero values for all three channels; "
            "primary.by_channel's rows carry only an 'fy26' key, verified by "
            "direct inspection of the certified data.js."
        ),
        business_impact=(
            "Executive Cockpit's channel-split donut currently cannot show "
            "FY27 at all (it has nothing to read) -- this is an existing "
            "production limitation, unchanged by Phase 1."
        ),
        financial_impact="None -- no wrong number is displayed; the view simply has no FY27 data source today.",
        owner="Engineering",
        approver="aswalsheshant-cell (repository owner)",
        approval_reference="PR #198 Phase 1 Certification Gate review, 2026-09-24 -- approved on the "
                            "documented CLAUDE.md 'Coverage split' evidence cited above; see "
                            "docs/CANONICAL_ENGINE_PHASE1_REPORT.md's governance table.",
        approved_at="2026-09-24",
        approval_status="APPROVED",
        temporary_or_permanent="TEMPORARY",
        resolution_phase="Phase 5 (Executive Cockpit migration) -- once Executive Cockpit reads "
                          "CHANNEL_PRIMARY_NSV from the canonical engine instead of primary.by_channel "
                          "directly, FY27 becomes available automatically, since the canonical engine "
                          "already covers it via detail_meta.channel_totals.",
        release_blocker=False,
    ),
    ApprovedException(
        exception_id="GOV-002",
        metric="PRIMARY_NSV",
        scope_matches=lambda scope: scope == "fy=FY27",
        scope_description="fy=FY27 (grand total)",
        reason_not_pass="Same root cause as GOV-001, at the grand-total level.",
        evidence="Same as GOV-001.",
        business_impact="Same as GOV-001.",
        financial_impact="None.",
        owner="Engineering",
        approver="aswalsheshant-cell (repository owner)",
        approval_reference="PR #198 Phase 1 Certification Gate review, 2026-09-24 -- same evidence as GOV-001.",
        approved_at="2026-09-24",
        approval_status="APPROVED",
        temporary_or_permanent="TEMPORARY",
        resolution_phase="Phase 5 (Executive Cockpit migration) -- same as GOV-001.",
        release_blocker=False,
    ),
    ApprovedException(
        exception_id="GOV-003",
        metric="CHAIN_OFFTAKE_NSV",
        scope_matches=lambda scope: "fy=FY27" in scope,
        scope_description="any chain with no real fy27 entry in offtake.by_chain, fy=FY27 "
                           "(currently: CNC, EB2B, Others, Vijetha)",
        reason_not_pass=(
            "KI-OFFTAKE-001 (Issue #195). Canonical correctly reports NOT_AVAILABLE for "
            "a chain with no real FY27 entry; the live production dashboard's fallback "
            "chain would instead reach offtake.by_chain[].value, an all-months-combined "
            "field with no FY subscript."
        ),
        evidence="docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md's KI-OFFTAKE-001 root-cause mapping; "
                 "tests/canonical/test_offtake_metrics.py's structural proof across all "
                 "currently-affected chains, not one example.",
        business_impact=(
            "The engine-level fix is proven, but the LIVE 'Top Chains by Offtake' table "
            "still uses the old fallback chain until Phase 6 migrates it -- Issue #195 "
            "stays OPEN, not closed, until then. Phase 1 does not change what users see."
        ),
        financial_impact="~0.08% of FY27 offtake total display accuracy in the affected table "
                          "(Issue #195's original filed magnitude) -- unchanged in production by this PR.",
        owner="Engineering",
        approver="aswalsheshant-cell (repository owner)",
        approval_reference="PR #198 Phase 1 Certification Gate review, 2026-09-24 -- approved on the "
                            "docs/CANONICAL_FINANCIAL_TRUTH_DESIGN.md KI-OFFTAKE-001 root-cause mapping "
                            "and Issue #195's own filed evidence.",
        approved_at="2026-09-24",
        approval_status="APPROVED",
        temporary_or_permanent="TEMPORARY",
        resolution_phase="Phase 6 (Comparison/Inventory/Alerts migration) -- production-side closure "
                          "of Issue #195.",
        release_blocker=False,
    ),
    ApprovedException(
        exception_id="GOV-004",
        metric="RBC_OFFTAKE_NSV",
        scope_matches=lambda scope: True,  # applies to every FY -- the source is empty, not FY-specific
        scope_description="fy=FY26, fy=FY27 (all FYs -- the underlying source has zero real months)",
        reason_not_pass=(
            "D.reliance_brand_counters in the certified baseline is the empty availability "
            "stub ('Reliance Brand Counter data not available in current extracts'), not "
            "populated data. No authoritative Reliance Brand Counter offtake extract "
            "currently exists in the certified input."
        ),
        evidence="Direct inspection of dashboard/data.js: reliance_brand_counters == "
                 "{'months': [], 'monthly': [], 'total': 0, 'fy_tags': [], ..., "
                 "'note': 'Reliance Brand Counter data not available in current extracts.'}",
        business_impact=(
            "RBC_OFFTAKE_NSV and (by ADR-003 rule 5) RBC_GAP_NSV are NOT_AVAILABLE until a "
            "real source is onboarded. No calculated substitute or allocation from "
            "chain-level Reliance offtake is used in its place -- doing so would misrepresent "
            "an estimate as a measured figure."
        ),
        financial_impact="None -- nothing is fabricated. The Reliance Brand Counter view "
                          "(ADR-003, Phase 7) will show Primary NSV only until this resolves.",
        owner="MT Leadership / Business (source onboarding, not an engineering task)",
        approver="aswalsheshant-cell (repository owner)",
        approval_reference="PR #198 Phase 1 Certification Gate review, 2026-09-24 -- approved on direct "
                            "inspection of dashboard/data.js's reliance_brand_counters empty-stub note field.",
        approved_at="2026-09-24",
        approval_status="APPROVED",
        temporary_or_permanent="TEMPORARY",
        resolution_phase="Not yet scheduled -- blocked on a real Reliance Brand Counter offtake "
                          "extract being sourced and onboarded per CLAUDE.md's 'New data source "
                          "checklist'; outside the Phase 1-10 engineering sequence until then.",
        release_blocker=False,
    ),
]


def find_approved_exception(metric, scope) -> Optional[ApprovedException]:
    """Returns the matching registry entry ONLY if it is fully approved
    (see ApprovedException.is_fully_approved -- the self-approval guard).
    A metric/scope match whose approval fields are blank, or whose
    approval_status is not exactly "APPROVED", is treated identically to
    no match at all: the caller gets None, and reconcile.py turns that into
    UNKNOWN, never APPROVED_GOVERNED. Adding an entry to this file is
    therefore never enough by itself to manufacture a pass."""
    for exc in APPROVED_EXCEPTIONS:
        if exc.metric == metric and exc.scope_matches(scope) and exc.is_fully_approved():
            return exc
    return None

"""PRIMARY_NSV / CHANNEL_PRIMARY_NSV / RBC_PRIMARY_NSV against the real,
certified dashboard/data.js. Every expected figure here is copied from
docs/PR_193_PRODUCTION_CERTIFICATION.md / docs/POST_MERGE_CERTIFICATION_PR193.md,
not recomputed independently -- these tests prove the canonical engine
reproduces already-certified numbers, not new ones.
"""
from canonical import primary
from canonical.policies import NotAvailable

TOLERANCE = 0.01


def test_primary_nsv_fy26_matches_certified_baseline(data):
    assert abs(primary.primary_nsv(data, "FY26") - 32900.36) <= TOLERANCE


def test_channel_primary_nsv_fy26_matches_pr193_control1(data):
    assert abs(primary.channel_primary_nsv(data, "FY26", "MT") - 30684.99) <= TOLERANCE
    assert abs(primary.channel_primary_nsv(data, "FY26", "EB2B") - 1965.20) <= TOLERANCE
    assert abs(primary.channel_primary_nsv(data, "FY26", "SIS") - 250.17) <= TOLERANCE


def test_channel_primary_nsv_sums_to_primary_nsv(data):
    ch = primary.channel_primary_nsv_all_channels(data, "FY26")
    assert abs(sum(ch.values()) - primary.primary_nsv(data, "FY26")) <= TOLERANCE


def test_channel_primary_nsv_unknown_channel_is_not_available(data):
    result = primary.channel_primary_nsv(data, "FY26", "NOT_A_REAL_CHANNEL")
    assert isinstance(result, NotAvailable)


def test_primary_nsv_unrecognisable_fy_is_not_available(data):
    result = primary.primary_nsv(data, "FY99")
    assert isinstance(result, NotAvailable)


def test_rbc_primary_nsv_combined_fys_matches_pr193_reliance_control(data):
    fy26 = primary.rbc_primary_nsv(data, "FY26")
    fy27 = primary.rbc_primary_nsv(data, "FY27")
    total = (fy26 if not isinstance(fy26, NotAvailable) else 0) + \
            (fy27 if not isinstance(fy27, NotAvailable) else 0)
    assert abs(total - 13702.51) <= TOLERANCE


def test_rbc_primary_nsv_by_zone_sums_to_rbc_primary_nsv(data):
    by_zone = primary.rbc_primary_nsv_by_zone(data, "FY26")
    assert abs(sum(by_zone.values()) - primary.rbc_primary_nsv(data, "FY26")) <= TOLERANCE

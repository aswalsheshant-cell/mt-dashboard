"""No canonical metric may return NaN, Infinity, or an unlabelled sentinel
standing in for a real value."""
import math

from canonical import offtake, primary
from canonical.policies import NotAvailable


def _assert_clean(value):
    if isinstance(value, NotAvailable):
        return
    assert isinstance(value, (int, float))
    assert not math.isnan(value)
    assert not math.isinf(value)


def test_primary_metrics_never_return_nan_or_infinity(data):
    _assert_clean(primary.primary_nsv(data, "FY26"))
    _assert_clean(primary.primary_nsv(data, "FY27"))
    for v in primary.channel_primary_nsv_all_channels(data, "FY26").values():
        _assert_clean(v)


def test_offtake_metrics_never_return_nan_or_infinity(data):
    _assert_clean(offtake.offtake_nsv(data, "FY26"))
    _assert_clean(offtake.offtake_nsv(data, "FY27"))
    for v in offtake.chain_offtake_nsv_all_chains(data, "FY27").values():
        _assert_clean(v)


def test_reliance_metrics_never_return_nan_or_infinity(data):
    _assert_clean(primary.rbc_primary_nsv(data, "FY26"))
    _assert_clean(offtake.rbc_offtake_nsv(data, "FY27"))

from canonical.fiscal import normalize_fy, data_key


def test_normalize_fy_accepts_uppercase():
    assert normalize_fy("FY27") == "FY27"


def test_normalize_fy_accepts_lowercase():
    assert normalize_fy("fy26") == "FY26"


def test_normalize_fy_accepts_month_label():
    # Apr-26 -> FY27 (THE ONE FY RULE: Apr..Dec of year Y -> FY(Y+1))
    assert normalize_fy("Apr-26") == "FY27"


def test_normalize_fy_rejects_garbage():
    assert normalize_fy("not-a-fy") is None
    assert normalize_fy(None) is None
    assert normalize_fy("") is None


def test_data_key_lowercases():
    assert data_key("FY27") == "fy27"


def test_data_key_raises_on_unrecognisable_fy():
    import pytest
    with pytest.raises(ValueError):
        data_key("garbage")

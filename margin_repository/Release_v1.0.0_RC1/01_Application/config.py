# -*- coding: utf-8 -*-
"""Configurable validation thresholds and GST controls.

All business-sensitive thresholds are externalized here so they can be
reviewed, approved, and changed without modifying engine code. Defaults
are conservative starting points — final values require business sign-off.
"""
import os
import json

DEFAULT_CONFIG = {
    "schema_version": "1.1.0",

    # --- Margin risk thresholds (percentage points) ---
    "risk_thresholds": {
        "normal_max_pp": 1.0,
        "warning_max_pp": 3.0,
        "high_risk_max_pp": 5.0,
        "labels": {
            "normal": "Normal — standard review",
            "warning": "Warning — checker approval required",
            "high_risk": "High Risk — commercial approval required",
            "blocked": "Blocked — finance/commercial dual approval required",
        },
    },

    # --- GST validation controls ---
    "gst_controls": {
        "valid_rates": [0, 5, 12, 18, 28],
        "severity": {
            "blank_gst": "WARNING",
            "invalid_gst_value": "FAIL",
            "gst_mismatch_article_master": "BLOCKED",
            "gst_change_from_prior": "WARNING",
            "unsupported_gst_rate": "BLOCKED",
        },
    },

    # --- Validation rule severities (overridable) ---
    "rule_severity": {
        "BLANK_EAN": "WARNING",
        "BLANK_MRP": "BLOCKED",
        "MISSING_CHAIN": "BLOCKED",
        "MISSING_BRAND": "FAIL",
        "MISSING_CATEGORY": "FAIL",
        "MARGIN_OVER_100": "BLOCKED",
        "NEGATIVE_MARGIN": "BLOCKED",
        "INCORRECT_GST": "FAIL",
        "INCORRECT_PACK_SIZE": "WARNING",
        "DUPLICATE_EAN": "WARNING",
        "DUPLICATE_CHAIN_ARTICLE": "WARNING",
        "DUPLICATE_EFFECTIVE_DATE": "FAIL",
        "EXPIRED_COMMERCIAL": "WARNING",
        "INACTIVE_ARTICLE": "WARNING",
        "MISSING_COMMERCIALS": "WARNING",
        "BLANK_TRADE_MARGIN": "WARNING",
        "BLANK_GST": "WARNING",
        "GST_CHANGED": "WARNING",
    },

    # --- Approval workflow ---
    "approval": {
        "valid_statuses": ["DRAFT", "PENDING_REVIEW", "APPROVED", "REJECTED", "SUPERSEDED"],
        "forecast_eligible_statuses": ["APPROVED"],
        "forecast_eligible_record_statuses": ["PUBLISHED"],
        "forecast_eligible_listing_statuses": ["ACTIVE"],
    },

    # --- Margin ceiling (absolute bounds) ---
    "margin_bounds": {
        "max_margin_pct": 100.0,
        "min_margin_pct": 0.0,
        "allow_negative_with_approval": False,
    },
}


def load_config(config_path=None):
    if config_path and os.path.exists(config_path):
        with open(config_path) as f:
            user = json.load(f)
        cfg = _deep_merge(DEFAULT_CONFIG, user)
        return cfg
    return DEFAULT_CONFIG.copy()


def save_config(cfg, config_path):
    os.makedirs(os.path.dirname(config_path) or ".", exist_ok=True)
    with open(config_path, "w") as f:
        json.dump(cfg, f, indent=2)


def classify_margin_risk(delta_pp, cfg=None):
    """Classify a margin change (in percentage points) into a risk tier."""
    cfg = cfg or DEFAULT_CONFIG
    t = cfg["risk_thresholds"]
    d = abs(delta_pp) if delta_pp is not None else 0
    if d <= t["normal_max_pp"]:
        return "NORMAL"
    elif d <= t["warning_max_pp"]:
        return "WARNING"
    elif d <= t["high_risk_max_pp"]:
        return "HIGH_RISK"
    else:
        return "BLOCKED"


def get_gst_severity(rule_key, cfg=None):
    """Get the configured severity for a GST validation rule."""
    cfg = cfg or DEFAULT_CONFIG
    return cfg["gst_controls"]["severity"].get(rule_key, "FAIL")


def get_rule_severity(rule_name, cfg=None):
    """Get configured severity for any validation rule."""
    cfg = cfg or DEFAULT_CONFIG
    return cfg["rule_severity"].get(rule_name, "WARNING")


def _deep_merge(base, override):
    result = base.copy()
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result

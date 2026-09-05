"""
Modern Trade (MT) Analytics Engine
Calculates dynamic business metrics for Leadership Deck generation:
- Multi-step diagnostic waterfall auto-balancing
- Scenario ROI, sensitivity, and net margin impact
- 2x2 Risk-Opportunity spatial quadrant mapping
"""

from typing import Dict, Any, List, Tuple


def calculate_waterfall_bridge(
    primary: float,
    realized_offtake: float,
    shelf_share_loss_pct: float = 0.39,
    price_resistance_pct: float = 0.26
) -> Dict[str, Any]:
    """
    Computes an auto-balanced multi-step primary-to-offtake diagnostic bridge.

    Total Gap = Primary - Realized Offtake
    - Shelf space loss: primary * conversion loss factor
    - Price resistance: primary * price elasticity penalty
    - Trapped/Stuck Inventory: residual balance to ensure total equals realized offtake

    Args:
        primary: Total primary dispatch in ₹ Cr
        realized_offtake: Actual sell-out in ₹ Cr
        shelf_share_loss_pct: Proportion of leakage due to shelf space loss (default 39%)
        price_resistance_pct: Proportion of leakage due to price resistance (default 26%)

    Returns:
        Dict with primary, shelf_loss, price_loss, stuck_inventory, realized_offtake,
        conversion_rate (%), and trapped_capital
    """
    primary = max(0.0, float(primary))
    realized_offtake = max(0.0, float(realized_offtake))
    total_leakage = max(0.0, primary - realized_offtake)

    if total_leakage <= 0:
        return {
            "primary": primary,
            "shelf_loss": 0.0,
            "price_loss": 0.0,
            "stuck_inventory": 0.0,
            "realized_offtake": realized_offtake,
            "conversion_rate": round((realized_offtake / primary * 100), 1) if primary > 0 else 100.0,
            "trapped_capital": 0.0
        }

    # Calculate proportional leakage
    shelf_loss = round(total_leakage * shelf_share_loss_pct, 2)
    price_loss = round(total_leakage * price_resistance_pct, 2)
    stuck_inventory = round(total_leakage - (shelf_loss + price_loss), 2)

    # Prevent roundoff negative values on residual
    if stuck_inventory < 0:
        stuck_inventory = 0.0
        shelf_loss = round(total_leakage - price_loss, 2)

    conv_rate = round((realized_offtake / primary * 100), 1) if primary > 0 else 0.0

    return {
        "primary": primary,
        "shelf_loss": shelf_loss,
        "price_loss": price_loss,
        "stuck_inventory": stuck_inventory,
        "realized_offtake": realized_offtake,
        "conversion_rate": conv_rate,
        "trapped_capital": round(total_leakage, 2)
    }


def calculate_scenario_roi(
    current_offtake_weekly: float,
    current_conv: float,
    target_conv: float,
    promo_spend: float,
    promo_days: int = 21,
    gross_margin_pct: float = 0.45,
    discount_pct: float = 0.10
) -> Dict[str, Any]:
    """
    Dynamic scenario ROI and elasticity calculator.

    Uplift is modeled by normalising offtake against conversion efficiency.

    Args:
        current_offtake_weekly: Weekly offtake in ₹ Cr
        current_conv: Current conversion rate in % (e.g. 45.0)
        target_conv: Target conversion rate in % (e.g. 70.0)
        promo_spend: Promotional spend in ₹ Lakhs or ₹ Crores (same scale as offtake)
        promo_days: Duration of promotional window (default 21 days)
        gross_margin_pct: Gross margin % (default 45%)
        discount_pct: Discount depth in % (default 10%)

    Returns:
        Dict with conversion uplift, weekly offtake projections, ROI multiples,
        and net revenue impact
    """
    current_conv = max(1.0, float(current_conv))
    target_conv = max(current_conv, float(target_conv))

    # Implied baseline full potential weekly velocity
    base_weekly_velocity = current_offtake_weekly / (current_conv / 100.0)

    # Interim conversion with promo (70% of the way to target)
    mid_conv = round(current_conv + (target_conv - current_conv) * 0.70, 1)
    promo_weekly_offtake = round(base_weekly_velocity * (mid_conv / 100.0), 2)
    target_weekly_offtake = round(base_weekly_velocity * (target_conv / 100.0), 2)

    weeks = promo_days / 7.0
    incremental_weekly = promo_weekly_offtake - current_offtake_weekly
    gross_uplift = round(incremental_weekly * weeks, 2)
    net_uplift = round(gross_uplift * (1.0 - (discount_pct / 100.0)), 2)

    gross_margin_gain = round(net_uplift * gross_margin_pct, 2)

    if promo_spend > 0:
        roi_multiple = round(net_uplift / promo_spend, 1)
        net_roi_multiple = round(gross_margin_gain / promo_spend, 1)
    else:
        roi_multiple = 0.0
        net_roi_multiple = 0.0

    return {
        "current_conv": current_conv,
        "mid_conv": mid_conv,
        "target_conv": target_conv,
        "conv_lift_pp": round(target_conv - current_conv, 1),
        "current_weekly": current_offtake_weekly,
        "promo_weekly": promo_weekly_offtake,
        "target_weekly": target_weekly_offtake,
        "uplift_pct": round(((promo_weekly_offtake - current_offtake_weekly) / current_offtake_weekly) * 100, 1) if current_offtake_weekly > 0 else 0.0,
        "promo_spend": promo_spend,
        "gross_uplift": gross_uplift,
        "net_uplift": net_uplift,
        "roi_multiple": roi_multiple,
        "net_roi_multiple": net_roi_multiple
    }


def calculate_matrix_coordinates(
    zones: List[Dict[str, Any]],
    box_left: float,
    box_top: float,
    box_width: float,
    box_height: float,
    target_conv: float = 75.0
) -> List[Dict[str, Any]]:
    """
    Maps zone metrics to Cartesian PPTX shape coordinates on a 2x2 Risk-Opportunity grid.

    X-axis: Conversion Gap (Target - Current). Larger gap = further to the right (more urgent).
    Y-axis: Offtake / Scale (₹ Cr). Larger scale = higher up (inverted for PPT top-down coordinates).

    Args:
        zones: List of zone dicts with 'name', 'conversion' (%), 'nsv' (₹ Cr)
        box_left: Left edge of matrix box in inches
        box_top: Top edge of matrix box in inches
        box_width: Width of matrix box in inches
        box_height: Height of matrix box in inches
        target_conv: Target conversion benchmark (default 75%)

    Returns:
        List of zones augmented with x_coord, y_coord, gap_pp, quadrant, color_theme
    """
    if not zones:
        return []

    conversions = [z.get("conversion", 50.0) for z in zones]
    nsvs = [z.get("nsv", 1.0) for z in zones]

    min_nsv = min(nsvs) if nsvs else 0.5
    max_nsv = max(nsvs) if nsvs else 5.0
    nsv_range = (max_nsv - min_nsv) if max_nsv != min_nsv else 1.0

    mapped_zones = []
    padding = 0.08  # 8% inner gutter to keep bubbles within quadrants

    for z in zones:
        conv = z.get("conversion", 50.0)
        nsv = z.get("nsv", 1.0)
        gap = target_conv - conv  # Positive = underperforming target

        # X normalization: -10pp gap (left/good) to +35pp gap (right/critical)
        norm_x = (gap - (-10.0)) / (35.0 - (-10.0))
        norm_x = min(max(norm_x, 0.0), 1.0)

        # Y normalization: larger NSV = higher up (smaller top offset in PPT)
        norm_y = (nsv - min_nsv) / nsv_range
        norm_y = min(max(norm_y, 0.0), 1.0)

        # Apply bounding box with padding
        plot_left = box_left + (box_width * padding) + (norm_x * box_width * (1.0 - 2 * padding))
        plot_top = (box_top + box_height) - (box_height * padding) - (norm_y * box_height * (1.0 - 2 * padding))

        # Classify Quadrant
        is_large_scale = nsv >= (min_nsv + 0.45 * nsv_range)
        is_high_gap = conv < 65.0

        if is_large_scale and is_high_gap:
            quadrant = "URGENT"
            color_theme = "RED"
        elif not is_large_scale and is_high_gap:
            quadrant = "MONITOR"
            color_theme = "ORANGE"
        elif is_large_scale and not is_high_gap:
            quadrant = "WATCH"
            color_theme = "YELLOW"
        else:
            quadrant = "HEALTHY"
            color_theme = "GREEN"

        mapped_zones.append({
            **z,
            "gap_pp": round(gap, 1),
            "x_coord": round(plot_left, 2),
            "y_coord": round(plot_top, 2),
            "quadrant": quadrant,
            "color_theme": color_theme
        })

    return mapped_zones

#!/usr/bin/env python3
"""
Integration module for monthly insights pre-calculation into build_dashboard_data.py.

Provides clean interface between revenue_presentation_engine and the main build pipeline.
"""

import json
from typing import Dict, Any, Optional
from revenue_presentation_engine import RevenuePresentationEngine


def build_monthly_insights_block(dash_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Pre-calculate monthly insights from dashboard data blocks.

    Args:
        dash_data: Partial or complete DASH object with primary, offtake, forecast blocks

    Returns:
        Dictionary with structure:
        {
            'month': str,
            'generated_at': str (ISO timestamp),
            'headline': str,
            'metrics': {...},
            'alignment': {...},
            'distribution': {...},
            'distributor_health': [...],
            'forecast_accuracy': {...},
            'action_items': [...]
        }
        or None if insufficient data to calculate
    """
    try:
        # Validate we have minimum required blocks
        if not dash_data.get("primary") or not dash_data.get("offtake"):
            print("⚠ Insufficient data blocks for monthly_insights (need primary + offtake)")
            return None

        # Initialize engine
        engine = RevenuePresentationEngine(dash_data)

        # Generate brief for latest month
        brief = engine.generate_monthly_insight_brief()

        if brief.get("error"):
            print(f"⚠ Monthly insights generation error: {brief['error']}")
            return None

        print(f"✓ Monthly insights: {brief['month']}, "
              f"Alignment={brief['alignment']['health_status']}, "
              f"ND={brief['distribution']['nd_pct']:.1f}%, "
              f"WD={brief['distribution']['wd_pct']:.1f}%, "
              f"Actions={len(brief['action_items'])}")

        return brief

    except Exception as e:
        print(f"⚠ Monthly insights calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return None


def inject_monthly_insights_into_data(data_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate and inject monthly_insights block into data dictionary.

    Non-destructive: if calculation fails, original dict is returned unchanged.
    Safe for all build modes (full, primary-only, offtake-patch, etc.)

    Args:
        data_dict: The DASH object before JSON serialization

    Returns:
        Updated data_dict with monthly_insights block added
    """
    brief = build_monthly_insights_block(data_dict)

    if brief:
        data_dict["monthly_insights"] = brief

    return data_dict


def validate_monthly_insights_serializable(brief: Dict[str, Any]) -> bool:
    """
    Verify monthly_insights block is JSON-serializable without NaN/Infinity.

    Args:
        brief: The monthly_insights block from build_monthly_insights_block

    Returns:
        True if serializable, False otherwise (logs issues)
    """
    try:
        # Try to serialize
        json_str = json.dumps(brief, allow_nan=False, ensure_ascii=False)

        # Validate no NaN/Infinity slipped through
        if "NaN" in json_str or "Infinity" in json_str:
            print(f"⚠ NaN/Infinity detected in serialized monthly_insights")
            return False

        # Size check (warn if too large)
        size_kb = len(json_str.encode('utf-8')) / 1024
        if size_kb > 100:
            print(f"⚠ Monthly insights block is {size_kb:.1f}KB (expected <50KB)")

        return True

    except (ValueError, TypeError) as e:
        print(f"⚠ Monthly insights serialization error: {e}")
        return False


if __name__ == "__main__":
    # Smoke test: load sample data.js and generate brief
    import sys
    from pathlib import Path

    if len(sys.argv) < 2:
        print("Usage: python monthly_insights_integration.py <data.js path> [output.json]")
        sys.exit(1)

    data_js_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else None

    try:
        # Load data.js
        with open(data_js_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse JSON
        if content.startswith('window.DASH = '):
            content = content[14:]
        if content.endswith(';'):
            content = content[:-1]

        dash_data = json.loads(content)

        # Generate and inject
        dash_data = inject_monthly_insights_into_data(dash_data)

        # Validate
        if "monthly_insights" in dash_data:
            if validate_monthly_insights_serializable(dash_data["monthly_insights"]):
                print("✓ Monthly insights validated and serializable")

                if output_path:
                    # Write just the brief
                    with open(output_path, 'w', encoding='utf-8') as f:
                        json.dump(dash_data["monthly_insights"], f, indent=2)
                    print(f"✓ Written to {output_path}")
            else:
                print("✗ Validation failed")
                sys.exit(1)
        else:
            print("⚠ No monthly_insights block generated")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

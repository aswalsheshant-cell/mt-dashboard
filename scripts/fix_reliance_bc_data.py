#!/usr/bin/env python3
"""
Generate Reliance Brand Counter (RBC) data aggregates from detail_records
and patch into dashboard/data.js
"""

import json
import re
from pathlib import Path
from collections import defaultdict

def load_data_js(path):
    """Load data.js as JSON."""
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        start = content.find('{')
        end = content.rfind('}') + 1
        return json.loads(content[start:end])

def generate_reliance_bc(detail_records):
    """Generate RBC aggregates from detail_records filtered to Reliance chains."""

    # Reliance chains to include
    reliance_chains = {'Reliance Retail-DC', 'Reliance Retail Limited',
                       'Reliance Retail-(Azorte)', 'Reliance Retail-Store'}

    # Filter to Reliance records
    reliance_recs = [r for r in detail_records
                     if r.get('Chain') in reliance_chains]

    if not reliance_recs:
        return None

    print(f"✓ Found {len(reliance_recs)} Reliance records")

    # Aggregate by zone, brand, category, state, FY+Month
    by_zone = defaultdict(float)
    by_brand = defaultdict(float)
    by_category = defaultdict(float)
    by_state = defaultdict(lambda: {'nsv': 0, 'state_name': '', 'zone_name': ''})

    monthly_data = defaultdict(lambda: defaultdict(float))  # (fy, month) -> total
    fy_totals = defaultdict(float)
    fy_tags = set()
    months_by_fy = defaultdict(set)

    for r in reliance_recs:
        nsv = float(r.get('NSV', 0))
        zone = r.get('Zone', 'Unknown')
        brand = r.get('Brand', 'Unknown')
        cat = r.get('Category', 'Unknown')
        state = r.get('State', 'Unknown')
        fy = r.get('FY', 'FY26')
        month = r.get('Month', 'Unknown')

        # Aggregate by dimension
        by_zone[zone] += nsv
        by_brand[brand] += nsv
        by_category[cat] += nsv

        # State tracking (include zone)
        state_key = (state, zone)
        by_state[state_key]['nsv'] += nsv
        by_state[state_key]['state_name'] = state
        by_state[state_key]['zone_name'] = zone

        # Monthly totals
        monthly_data[fy][month] += nsv
        fy_totals[fy] += nsv

        fy_tags.add(fy)
        months_by_fy[fy].add(month)

    # Build RBC data structure
    rbc = {
        'fy_tags': sorted(fy_tags),
        'by_zone': [{'name': z, 'total': float(v), 'fy25': 0, 'fy26': 0, 'fy27': 0}
                    for z, v in sorted(by_zone.items())],
        'by_brand': [{'name': b, 'total': float(v), 'fy25': 0, 'fy26': 0, 'fy27': 0}
                     for b, v in sorted(by_brand.items(), key=lambda x: -x[1])],
        'by_category': [{'name': c, 'total': float(v), 'fy25': 0, 'fy26': 0, 'fy27': 0}
                        for c, v in sorted(by_category.items(), key=lambda x: -x[1])],
        'by_state': [{'state': v['state_name'], 'zone': v['zone_name'],
                      'total': float(v['nsv']), 'fy25': 0, 'fy26': 0, 'fy27': 0}
                     for v in sorted(by_state.values(),
                                   key=lambda x: -x['nsv'])],
        'note': 'Reliance Brand Counter aggregated from Modern Trade detail records',
        'data_complete_through': 'Current month'
    }

    # Add FY-specific totals and monthly data
    for fy in sorted(fy_tags):
        fy_short = 'fy' + fy.lower().replace('fy', '')
        rbc[f'total_{fy_short}'] = float(fy_totals.get(fy, 0))

        # Add FY totals to zone/brand/category
        for zone_rec in rbc['by_zone']:
            zone_rec[fy_short] = zone_rec['total']
        for brand_rec in rbc['by_brand']:
            brand_rec[fy_short] = brand_rec['total']
        for cat_rec in rbc['by_category']:
            cat_rec[fy_short] = cat_rec['total']

        # Monthly breakdown
        months_list = sorted(months_by_fy.get(fy, []))
        rbc[f'months_{fy_short}'] = months_list

        monthly_totals = [float(monthly_data[fy].get(m, 0)) for m in months_list]
        rbc[f'monthly_{fy_short}'] = monthly_totals

    # Fallback totals/months for backward compat
    if fy_tags:
        primary_fy = sorted(fy_tags)[-1]
        fy_short = 'fy' + primary_fy.lower().replace('fy', '')
        rbc['total'] = float(fy_totals.get(primary_fy, 0))
        rbc['months'] = rbc.get(f'months_{fy_short}', [])
        rbc['monthly'] = rbc.get(f'monthly_{fy_short}', [])

    return rbc

def patch_data_js(data_js_path, rbc_data):
    """Patch RBC data into data.js."""

    with open(data_js_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Find the data.js structure start (window.DASH = {...})
    match = re.search(r'window\.DASH\s*=\s*\{', content)
    if not match:
        raise ValueError("Could not find 'window.DASH = {' in data.js")

    # Find end of DASH object
    start_pos = match.end() - 1  # Include the opening brace
    open_braces = 1
    pos = start_pos + 1
    in_string = False
    escape = False

    while pos < len(content) and open_braces > 0:
        char = content[pos]

        if escape:
            escape = False
        elif char == '\\':
            escape = True
        elif char == '"':
            in_string = not in_string
        elif not in_string:
            if char == '{':
                open_braces += 1
            elif char == '}':
                open_braces -= 1
        pos += 1

    end_pos = pos

    # Extract and parse JSON
    json_str = content[start_pos:end_pos]
    data = json.loads(json_str)

    # Add RBC data
    data['reliance_bc'] = rbc_data

    # Rebuild file
    new_json = json.dumps(data, ensure_ascii=False, separators=(',', ':'))
    new_content = content[:match.start()] + f'window.DASH={new_json};' + content[end_pos:]

    # Write back
    with open(data_js_path, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"✓ Patched RBC data into {data_js_path}")

def main():
    data_js_path = Path(__file__).parent.parent / "dashboard" / "data.js"

    print("=" * 80)
    print("FIXING RELIANCE BRAND COUNTER DATA")
    print("=" * 80)
    print()

    # Load data
    try:
        data = load_data_js(str(data_js_path))
    except Exception as e:
        print(f"❌ Failed to load data.js: {e}")
        return 1

    # Generate RBC aggregates
    detail_records = data.get('detail_records', [])
    rbc_data = generate_reliance_bc(detail_records)

    if not rbc_data:
        print("❌ No Reliance records found in detail_records")
        return 1

    print(f"\nGenerated RBC aggregates:")
    print(f"  Zones: {len(rbc_data['by_zone'])}")
    print(f"  Brands: {len(rbc_data['by_brand'])}")
    print(f"  Categories: {len(rbc_data['by_category'])}")
    print(f"  States: {len(rbc_data['by_state'])}")
    print(f"  FY coverage: {rbc_data['fy_tags']}")
    print()

    # Patch into data.js
    try:
        patch_data_js(str(data_js_path), rbc_data)
        print("\n✓ SUCCESS: RBC data has been generated and patched")
        print("  The Reliance Brand Counter tab should now display zone/brand data")
        return 0
    except Exception as e:
        print(f"❌ Failed to patch data.js: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())

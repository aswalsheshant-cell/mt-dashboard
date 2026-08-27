"""
Centralized chain name alias dictionary.
Maps every known variant → canonical display name.
Import this in any pipeline script that reads chain names from
data.js, Excel, or CSV sources.

Canonical names (source of truth):
  DMart | Apollo | Reliance Retail | Nykaa (FSN) | Health & Glow |
  Wellness Forever | Sancus (RMT) | VMM | More Retail | Metro C&C |
  Walmart | Spencer | Frankross | V-Mart | Trent | Lulu | Azorte |
  Eremedium | Ratnadeep | Guardian | Arambagh | B&N | Shoppers Stop |
  Sasta Sundar | Ascent Wellness | Broadway | Lifestyle | Deal Share |
  Apna Mart | National Mart | Sumo Save | Trilife | WH-Smith |
  Medanta | Dabur New U | Max Hyper | Pothys | Vijetha | Sarvana
"""

CHAIN_ALIASES: dict[str, str] = {
    # ── DMart ────────────────────────────────────────────────────────────
    'Dmart':                        'DMart',
    'D-Mart':                       'DMart',
    'd-mart':                       'DMart',
    'dmart':                        'DMart',

    # ── Apollo ───────────────────────────────────────────────────────────
    'Apollo Pharmacy':              'Apollo',
    'Apollo Healthco':              'Apollo',

    # ── VMM (Vishal Mega Mart) ───────────────────────────────────────────
    'Vishal Mega Mart':             'VMM',
    'Vmm':                          'VMM',

    # ── Sancus / RMT ─────────────────────────────────────────────────────
    'RMT-Sancus':                   'Sancus (RMT)',

    # ── Health & Glow ────────────────────────────────────────────────────
    'H&G':                          'Health & Glow',

    # ── Nykaa ────────────────────────────────────────────────────────────
    'Nykaa SS(fsn)':                'Nykaa (FSN)',

    # ── Metro Cash & Carry ───────────────────────────────────────────────
    'Metro-CNC-RRL':                'Metro C&C',
    'Metro C&C':                    'Metro C&C',

    # ── Walmart ──────────────────────────────────────────────────────────
    'Walmart CNC':                  'Walmart',

    # ── Reliance Retail sub-brands ───────────────────────────────────────
    'Reliance Retail-(Azorte)':     'Azorte',

    # ── Casing / formatting variants ─────────────────────────────────────
    'FRANKROSS':                    'Frankross',
    'ARAMBAGH':                     'Arambagh',
    'Sasta Sunder':                 'Sasta Sundar',
    'Dabur New':                    'Dabur New U',
    'Shoppers Stop ':               'Shoppers Stop',
    'Lifestyle ':                   'Lifestyle',
}


def normalize(name: str) -> str:
    """Return the canonical chain name, or the original if no alias exists."""
    if not name:
        return name
    return CHAIN_ALIASES.get(name.strip(), name.strip())

# Issue — eB2B and SIS are inside MT Zone Sales

**Raised:** 16 Aug 2026 · **Severity:** Critical · **Status:** PARTIALLY APPLIED — zone level still BLOCKED
**Affected:** July 2026 MT Command Centre deck, all zone-derived metrics
**Check:** `python scripts/mt_channel_reconciliation.py` (exit 2 = BLOCKED)

---

## Verdict

**PASS** for national MT, eB2B and SIS reporting — those figures are exact and are
now in the deck. **BLOCKED** for zone-level MT primary, conversion and gap, and for
everything derived from them (rankings, benchmark prize, opportunity sizing).

### Applied 16 Aug 2026 (business decision)

- Nykaa (FSN) excluded from Modern Trade in full and reported under **eB2B**.
- The **"Pan India" zone is renamed eB2B** and reported as a channel, not a geography
  (deck page 11).
- **SIS** given its own channel page on the same basis (deck page 12).
- Classification held in `scripts/data/channel_master.json` with a named owner.
- Methodology note added to every page footer.
- Thirteen pages whose figures still derive from zone-level primary are stamped
  **PROVISIONAL** with an amber rule and an explicit footer reason.

**July 2026, Modern Trade only — EXACT:** primary **₹47.02 Cr**, offtake
**₹34.04 Cr**, conversion **72.4%**, gap **₹12.98 Cr**. National MT offtake now ties
exactly to the sum of the six MT zones. Previously published all-channel figures were
₹49.21 Cr / ₹36.10 Cr / 73.4%.

## What the reconciliation found

**1. The zone rollup carries all three channels.** `detail_meta.fyx_primary.FY27`
is the exact uncapped FY27 primary. Its `by_zone` figures sum to 18,581.28 L — the
**all-channel** total (18,581.29 L), not the MT-only total (17,675.36 L). eB2B and
SIS are being allocated into geographic MT zones.

| Channel | FY27 primary (INR Lakh) | Share |
|---|---:|---:|
| MT | 17,675.36 | 95.12% |
| eB2B | 879.41 | 4.73% |
| SIS | 26.52 | 0.14% |
| **Total** | **18,581.29** | |

**Rs 9.06 Cr of non-MT primary sits inside FY27 zone sales.**

**2. One deck-facing account is misclassified.** Nykaa (FSN) is presented across the
deck as an MT account — its own zone page (slide 11), its own deep-dive (slide 14),
and a line in the national rollup. Its primary is classified **EB2B**.

| Account | FY27 MT | FY27 eB2B | FY27 SIS | Presented as MT in deck |
|---|---:|---:|---:|---|
| Nykaa (FSN) | 0.00 | 645.53 | 0.00 | **Yes** |
| Eremedium | 0.00 | 25.96 | 0.00 | No |
| Azorte | 0.00 | 0.00 | 15.03 | No |
| Shoppers Stop | 0.00 | 0.00 | 4.51 | No |

SIS accounts (`detail_meta.sis_reconciliation`): Azorte, Broadway, Lifestyle,
Shoppers Stop, Today's Basket. None are named in the deck, but their value is inside
the zone rollup.

**3. "Pan India" is not a geography.** FY27 offtake for the Pan India zone (860.01 L)
equals Nykaa (FSN) chain offtake (860.01 L) exactly, 1:1. It is a single eB2B account
carried as a seventh zone.

This also explains the grain defect raised in the previous deck revision: the
Rs 13.11 Cr vs Rs 15.17 Cr discrepancy existed because Pan India offtake had no
mapped primary. The cause is now known — **it is not MT at all.**

## Reconciliation identity

Exact, no estimation, using the deck's own July figures (INR Cr):

```
MT zone offtake (six geographic zones summed)   34.04
Pan India / Nykaa (eB2B)                         2.07
                                                ------
Published national offtake                      36.10   (36.10 - 2.07 - 34.04 = -0.01, rounding)
```

**National MT offtake = Rs 34.04 Cr**, not Rs 36.10 Cr.

## What cannot be corrected yet

`fyx_primary` gives an exact channel split, but only at FY level. `detail_records`
gives the full month x zone x channel cut but is capped at 40k groups covering
94.65% of FY27 value, and is measurably MT-biased (+0.95 pp), so it **understates**
the exclusion.

**A month x zone x channel primary cut is not derivable exactly from `data.js`.**

### Required to close

`July'26 primary and distributor secondary.xlsb` (article-wise primary, uncapped) —
the source `scripts/build_dashboard_data.py` reads for `fyx_primary`. It is
gitignored and absent from the working tree. With it, zone primary can be recut with
`Channel == 'MT'` applied before aggregation.

### Indicative impact (ESTIMATE — sampled, MT-biased, do not publish)

| Zone | Published primary | Est. non-MT | Est. MT primary | MT offtake | Published conv. | Est. MT conv. |
|---|---:|---:|---:|---:|---:|---:|
| West | 10.05 | 0.27 | 9.78 | 8.28 | 82.3% | 84.7% |
| South-1 | 9.80 | 0.21 | 9.59 | 8.19 | 83.6% | 85.4% |
| North | 11.95 | 0.45 | 11.50 | 6.99 | 58.5% | 60.8% |
| South-2 | 6.89 | 0.11 | 6.78 | 4.91 | 71.3% | 72.4% |
| East | 7.83 | 0.60 | 7.23 | 3.55 | 45.3% | 49.1% |
| Central | 2.69 | 0.04 | 2.65 | 2.12 | 78.8% | 80.0% |

National MT primary lands between **Rs 46.81 and 47.53 Cr** (published all-channel:
Rs 49.21 Cr). National MT conversion **71.6%–72.7%** against 73.4% published.

**Note the direction.** Every zone's conversion goes *up* once eB2B leaves its
denominator, while the national rate goes *down* once Nykaa's 99.4% flow leaves the
numerator. This is Simpson's paradox: the national figure and every one of its parts
move in opposite directions. Any commentary written on the blended number is
therefore unsafe in both directions.

## Open business decision

Nykaa (FSN) combines **FSN (B2C marketplace)** with **Nykaa SS (eB2B)** at article
level — the deck already flags that the two cannot be separated in the current feed.
A whole-account exclusion therefore also removes B2C e-commerce, which is neither MT
nor eB2B. Business owner to confirm one of:

- exclude the whole account from MT and report it under eB2B, or
- request separated FSN / Nykaa SS feeds and split it, or
- carry FSN B2C as its own third channel heading.

## Correction plan once the source lands

1. Apply `Channel == 'MT'` before any zone aggregation in
   `scripts/build_dashboard_data.py`.
2. Re-run `scripts/mt_channel_reconciliation.py` — CHECK 2 must show the zone rollup
   equal to the MT-only total; CHECK 3 must return no deck-facing offenders.
3. Regenerate the deck; recompute conversion, gap, benchmark prize, rankings,
   contribution %, Pareto and all opportunity sizing from MT-only figures.
4. Restructure reporting as: **Modern Trade** → MT accounts → zone-wise MT
   performance; **eB2B** separate; **SIS** separate.
5. Add the methodology note only after steps 1–3 pass:
   > *Zone performance represents Modern Trade accounts only. eB2B and SIS channels
   > are excluded from MT zone sales and reported separately.*

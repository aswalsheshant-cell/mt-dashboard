# TDP — Definition and Data Requirement Decision

**Status:** Decision pending — three options below  
**Current implementation:** Presence-based proxy (Option A)

---

## What TDP Means

**Total Distribution Points (TDP)** measures how broadly a product is distributed.
It is used in the Distribution tab to identify range gaps and prioritise focus SKUs.

---

## The Three Options

### Option A — Sales Presence Proxy (Current, live now)

**Definition:** An article is "distributed" in a store-month if it has any
recorded offtake (qty > 0) in that store that month.

**Formula (DAX):**
```
TDP (Presence) =
CALCULATE (
    COUNTROWS ( 'Fact Offtake Sales' ),
    'Fact Offtake Sales'[Offtake Qty] > 0
)
```

**Pros:** No additional data required; available immediately  
**Cons:** Understates distribution (a product can be listed but have zero sales in a
month); overstates coverage in gaps  
**Risk:** Can mislead range-expansion decisions  

### Option B — Store Listing Master

**Definition:** An article is "distributed" if it appears in a confirmed store
listing / planogram record for that store-month.

**Data required:** A store-listing file with columns:
`Store Code, Article Code, EAN Code, Listed From Date, Listed To Date`

This file does **not** currently exist in the repository.

**Pros:** Most accurate; industry-standard definition  
**Cons:** Requires a separate listing extract (usually from the retailer or SAP)  

### Option C — ACV-Weighted TDP (Nielsen RMS)

**Definition:** Nielsen's standard TDP = (stores carrying SKU / total stores) × ACV weight

**Data required:** Nielsen RMS store-level coverage data (not available; see
`Nielsen_Source_Requirement.md`)

**Pros:** Comparable to industry benchmarks  
**Cons:** External data dependency; significant lag  

---

## Recommendation

Use **Option A** for MVP. It is live, honest, and clearly labelled as a proxy.

Upgrade to **Option B** when a store-listing extract becomes available.
Option C is a stretch goal for the Nielsen integration phase.

**Action required from business:** confirm which option to standardise on.
Until confirmed, all Distribution tab labels include "(Presence-based)" to
distinguish from an ACV or listing definition.

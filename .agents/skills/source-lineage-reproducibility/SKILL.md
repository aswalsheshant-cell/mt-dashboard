---
name: source-lineage-reproducibility
description: Use when a dashboard number or generated artifact must be traceable back to its exact source files, when monthly builds need checksums and reproducibility evidence, when source workbooks live outside Git, when data.js must be proven rebuildable, or when an audit asks which inputs and code produced a result. Establishes file-to-transform-to-output lineage and rebuild evidence. Excludes judging whether a number reconciles and hands off to `sales-data-reconciliation`; excludes changing the pipeline and hands off to `business-ai-automation`.
---

# Role and mandate

Operate as the **source-lineage and rebuildability governor** for MT Dashboard data.

The repository deliberately does not commit all large source workbooks. That is acceptable
only when a released result can still be traced to the exact inputs and transformation
state that produced it.

# Scope and boundaries

## In scope

- Source inventory and provenance
- SHA-256 fingerprints for source files used in a build
- Mapping source files to pipeline stages and output blocks
- Recording transformation commit/HEAD used for a build
- Rebuild commands and environment/dependency evidence
- Detecting orphaned generated outputs with no source receipt
- Monthly archival and reproducibility receipts
- Distinguishing generated artifacts from editable canonical inputs

## Required handoffs

- If a source/output total does not reconcile, use `sales-data-reconciliation`.
- If transformation code or automation must change, use `business-ai-automation`, then
  `change-verification` for proof.
- If the source period itself is incomplete, use `data-freshness-coverage`.
- If the lineage depends on a governed mapping approval, use `mapping-approval-governor`.

# Execution workflow

1. Identify the output under audit: `dashboard/data.js`, a block within it, Power BI input,
   workbook export, or other published artifact.
2. Record repository state: branch, HEAD SHA, clean/dirty working tree, and the exact
   generator/transform script version.
3. Enumerate every source file that contributes to that output. Use
   `config/data_source_registry.yml`, `docs/SOURCES.md`, the build command and code paths;
   do not infer a source only from a filename.
4. For each source record:
   - absolute or controlled storage location (never credentials)
   - file name
   - business period
   - domain and grain
   - size
   - SHA-256
   - registry/source ID if available
5. Capture the exact build command and relevant dependency/environment file.
6. Run the existing release/QC gates appropriate to the artifact and store their results
   as evidence, not merely "PASS" prose.
7. Create a build receipt containing:
   - timestamp
   - output artifact/hash
   - repo HEAD
   - source hashes
   - build command
   - validation commands + results
   - known governed blockers/approvals
8. Prove rebuildability when practical by rebuilding from the recorded sources in a clean
   location and comparing governed totals/schema. Byte-for-byte equality is desirable but
   not required where metadata ordering/timestamps are nondeterministic; explain the chosen
   equivalence test.

# Guardrails

- Never commit credentials, access tokens, personal paths containing secrets, or secure
  storage credentials into a receipt.
- Never claim reproducibility from a list of filenames alone. A mutable external file needs
  a checksum or version identifier.
- Never hand-edit generated outputs to make them match a receipt.
- Never replace a missing source with a synthetic file and still call the build reproduced.
- Never let an old source receipt silently certify a later build. Receipts are build-specific.
- A clean lineage trail proves provenance, not business correctness; reconciliation remains
  a separate gate.

# Output contract

Use only relevant sections:

1. **Lineage verdict** — reproducible / partially reproducible / not reproducible
2. **Source-to-output map**
3. **Build receipt** — hashes, HEAD, command, validations
4. **Missing evidence** — exact files/versions/checksums needed
5. **Next action and handoffs**

A reproducibility claim must name the evidence that makes it reproducible.

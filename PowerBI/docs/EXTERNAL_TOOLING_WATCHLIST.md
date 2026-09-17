# External Tooling Watchlist

Tools spotted externally that are relevant to this project's Power BI work
but are **not adopted, not installed, and not configured** here. Entries
exist so a future session doesn't re-research the same tool from zero —
not as a roadmap commitment.

---

## Power BI MCP Servers (e.g. Microsoft's `@microsoft/powerbi-modeling-mcp`)

**Status:** WATCH / NOT ADOPTED

**What it is:** An MCP (Model Context Protocol) server that lets an AI
agent (GitHub Copilot, Claude, or any MCP client) create and modify Power
BI semantic model objects — tables, columns, measures, relationships,
hierarchies, RLS roles — via natural-language requests, against a model
open in Power BI Desktop, a Fabric workspace, or a PBIP/TMDL project.
Shipped by Microsoft, public preview since 18 Nov 2025.

**Potential future use, if ever adopted:**
- Semantic-model inspection (read-only exploration of an existing model)
- Metadata querying (list measures, relationships, hierarchies)
- Controlled, reviewed model maintenance (bulk renames, added descriptions,
  format-string consistency — the kind of chore this repo's own
  `PowerBI/CI/bpa_rules.json` already asks for)
- AI-assisted DAX/model development against this repo's `PowerBI/DAX/` and
  `PowerBI/PowerQuery/` files, once a real `.pbip`/TMDL model exists
- Model diagnostics (DAX query execution, performance benchmarking)

**Why it is not usable today:** it requires Power BI Desktop or a Fabric
workspace, VS Code with the GitHub Copilot Chat extension, and (per its own
setup guidance) Node.js — none of which exist in this repo's cloud Linux
CI/dev environment. This repo also does not commit a `.pbip`/`.bim`/`.pbix`
file (by design, per `CLAUDE.md`), so there is no live model for such a
server to connect to even where the environment did support it.

**Governance statement:**
- MCP is not currently part of this project's production architecture.
- No MCP agent has standing authority to modify any production model,
  DAX file, Power Query file, or dashboard artifact in this repo.
- No write access to any model is approved by default, for any MCP client.
- Future adoption — if ever proposed — requires its own architecture,
  security, auditability, and validation review, and sign-off through this
  repo's normal release-governance process before any write-capable use.
  This entry does not constitute that review or that sign-off.

**Related:** the same read-only-first discipline this entry describes is
already this project's default posture for any new tool — see
`PowerBI/docs/CI_VALIDATION_BOUNDARIES.md` for why "a tool exists" and "a
tool has been validated for use here" are kept as separate, explicit claims.

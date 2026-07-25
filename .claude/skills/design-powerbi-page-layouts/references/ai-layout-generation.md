# AI Layout Generation — Safe Workflow

AI assistance may be used to propose initial layout JSON from a natural-language
requirement. The output is always a proposal subject to human review and explicit
acceptance before it is applied. AI-generated layouts must pass the same
validation as manually designed layouts.

---

## Generation workflow

```
1. User provides requirement
        ↓
2. Structured requirement extraction
        ↓
3. Candidate layout JSON generated
        ↓
4. Schema validation (schemaVersion, types, field presence)
        ↓
5. Visual and binding validation (types supported, bindings plausible)
        ↓
6. Boundary and overlap validation
        ↓
7. User preview (show the proposed layout; do not apply it yet)
        ↓
8. Explicit user acceptance or rejection
        ↓
9. Accepted layout saved and recorded in history
```

If validation fails at steps 4–6, do not show the proposal. Report the
specific validation errors and offer to retry.

---

## Required inputs from the user

Before generating a layout, collect:

- **Audience** — who reads the page (e.g. "Regional Sales Manager")
- **Business decision** — what decision the page supports
- **Page type** — which template category (see SKILL.md template list)
- **KPIs** — the primary measures to display
- **Dimensions** — the fields to break down by (Brand, Chain, State, FY, etc.)
- **Available fields** — confirmed list of DAX measures and dimension fields available in the semantic model
- **Required filters** — slicers that must be present
- **Preferred theme** — e.g. `honasa-teal`
- **Canvas requirement** — Desktop, Mobile, or Wide
- **Visual constraints** — any visual types that must or must not appear
- **Mobile requirement** — whether a mobile override is needed

If any required input is missing, ask for it before generating. Do not infer
business definitions, measure names, or data availability.

---

## AI output constraints

The model output must:

- Conform to the versioned layout schema (`references/layout-contract.md`)
- Contain only supported visual types (see SKILL.md visual types list)
- Use only field names explicitly provided by the user
- Set `accessibilityLabel` on every visual
- Place all visuals within the specified canvas boundaries
- Include no fabricated measure values, no sample data unless explicitly requested
- Include no executable code (JavaScript, SQL, DAX, HTML)
- Include no secret or credential-like strings

If sample data is explicitly requested:
- Mark every sample value prominently as **SYNTHETIC — NOT REAL DATA**
- Keep it in a separate clearly-labelled section, not inside the layout visuals
- Do not use it as a substitute for real source data in the handoff

---

## Security requirements

### Provider keys
- Never request an AI provider API key from the user in the browser UI.
- Never accept a pasted API key via any form field or chat input.
- Never store a provider key in `localStorage`, `sessionStorage`, cookies, URLs, log files, or layout JSON.
- Never commit a provider key to the repository in any file (source code, config, `.env`, comments, or test fixtures).
- AI generation calls must be routed through an authenticated server-side gateway. The browser receives only the layout proposal, never a raw API response containing credentials.

### Trust model
- Treat all AI model output as untrusted external data.
- Validate every field in the generated layout against the schema before display.
- Reject any generated content that:
  - Contains unknown visual types
  - Contains coordinates outside canvas bounds
  - Contains dimensions or sizes below minimum (10 px)
  - Exceeds the maximum visual count per page
  - Exceeds the maximum page count
  - Contains executable markup or code
  - Contains secret patterns (`sk-`, `ghp_`, `Bearer`)

### Limits
- Maximum visuals per page: 50 (reject proposals exceeding this)
- Maximum pages per layout: 50
- Maximum field name length: 200 characters
- Generated JSON must not exceed a reasonable size limit (e.g. 500 KB)

---

## User review gate

The proposal must be presented to the user as a **preview** before any
persistent action. The UI must make clear:

- This is an AI-generated proposal, not a validated design.
- The user must review all visual placements, bindings, and labels.
- Accepting the proposal applies it to the canvas and adds one history entry.
- Rejecting or dismissing the proposal leaves the canvas unchanged.

Do not apply a generated layout without explicit user acceptance.

---

## Model and API versioning

Do not hardcode a specific model version as permanent knowledge. Current
model capabilities and API contracts change. Refer to the provider's
current documentation at generation time. The skill documents the
workflow and constraints, not a fixed API call signature.

---

## Multilingual input

Multilingual requirement interpretation should only be applied when the
user explicitly requests it. Do not automatically map non-English field
names or business terms to assumed equivalents. Ask the user to confirm
the mapping before generating.

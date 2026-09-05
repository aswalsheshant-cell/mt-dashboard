# End-to-End Workflow: MT Deck Generator → Google Slides

Complete guide for generating, validating, and deploying Modern Trade leadership decks to both PowerPoint and Google Slides.

---

## Quick Start (5 minutes)

### 1. Generate both PPTX and Google Slides JSON

```bash
python build_mt_monthly_ppt.py --month september --year 2026 --format both
```

**Output:**
- `MT_september2026.pptx` — PowerPoint deck (18 slides, 58 KB)
- `MT_september2026_gslides_batch.json` — Google Slides API payload (251 requests)

---

## Full Workflow Steps

### Step 1: Generate Deck (Format Selection)

Choose one of three export modes:

#### Option A: PowerPoint only
```bash
python build_mt_monthly_ppt.py --month september --year 2026 --format pptx
# Output: MT_september2026.pptx
```

#### Option B: Google Slides JSON only
```bash
python build_mt_monthly_ppt.py --month september --year 2026 --format json
# Output: MT_september2026_gslides_batch.json
```

#### Option C: Both formats (Recommended)
```bash
python build_mt_monthly_ppt.py --month september --year 2026 --format both
# Output: Both files
```

### Step 2: Customize (Optional)

Edit `DEFAULT_CONFIG` in `build_mt_monthly_ppt.py`:
- Zones: offtake, conversion %, gap, status, YoY growth
- KPIs: Q1/4M/monthly offtake, growth rates
- Chain diagnostics: Primary vs. offtake (for Slide 5c waterfall)
- Scenario parameters: Promo spend, target conversion, days (for Slide 12)
- Brands/chains data

Or pass data via config dict in code.

### Step 3: Validate JSON (Optional)

Before deploying to Google Slides, validate the payload:

```bash
python deploy_to_google_slides.py \
  --json-file MT_september2026_gslides_batch.json \
  --dry-run
```

Output: `[DRY RUN] Would deploy 251 requests`

### Step 4: Deploy to Google Slides (Live)

#### Setup (First time only)

1. **Create Google Cloud Project**
   - Go to https://console.cloud.google.com/
   - Create new project: "MT Dashboard"

2. **Enable APIs**
   - Enable: Google Slides API
   - Enable: Google Drive API

3. **Create OAuth 2.0 Credentials**
   - APIs & Services → Credentials
   - Create → OAuth 2.0 Desktop application
   - Download JSON → Save as `scripts/credentials.json`

4. **Install dependencies**
   ```bash
   pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client
   ```

#### Deploy

**Create new presentation:**
```bash
python deploy_to_google_slides.py \
  --json-file MT_september2026_gslides_batch.json \
  --title "MT September 2026 Review"
```

Output:
```
✓ Loaded 251 API requests
🔐 Authenticating...
✓ Created presentation: 1ABC...XYZ...
📤 Deploying to Google Slides...
✅ Deployed 251 operations
✨ Presentation ready: https://docs.google.com/presentation/d/1ABC...XYZ.../edit
```

**Update existing presentation:**
```bash
python deploy_to_google_slides.py \
  --json-file MT_september2026_gslides_batch.json \
  --presentation-id 1ABC...XYZ...
```

---

## Architecture Overview

```
build_mt_monthly_ppt.py (Main CLI)
├── Phase 1: Python-PPTX generation (18 slides)
├── Phase 2: Analytics engine
│   ├── Waterfall bridge (primary → offtake losses)
│   ├── Scenario ROI (promo uplift modeling)
│   └── Risk matrix (zone prioritization)
├── Phase 3: Dual-export
│   ├── mt_deck_ir.py (Intermediate Representation)
│   ├── gslides_exporter.py (Google Slides serializer)
│   └── PPTX file output
│
└── deploy_to_google_slides.py
    ├── Load batchUpdate JSON
    ├── OAuth 2.0 auth
    ├── Create/update Slides presentation
    └── Return shareable URL
```

---

## Command Reference

### Generate Deck

| Command | Output | Use Case |
|---------|--------|----------|
| `--format pptx` | `.pptx` only | Download & share via email |
| `--format json` | `.json` only | Validate payload; technical review |
| `--format both` | Both files | Full workflow; keep both backups |

### Deploy Deck

| Command | Action |
|---------|--------|
| `--dry-run` | Validate without deploying |
| `--presentation-id <ID>` | Update existing (instead of creating new) |
| `--title "Custom Title"` | Set presentation title (new only) |

---

## Validation Checklist

Before committing or sharing deck:

- [ ] **Syntax:** `python -m py_compile build_mt_monthly_ppt.py`
- [ ] **Analytics:** All 9 engine tests passing (`python test_analytics_engine.py`)
- [ ] **Google Slides:** All 11 export tests passing (`python test_gslides_export.py`)
- [ ] **PPTX:** All 18 slides render (open locally or preview)
- [ ] **JSON:** Payload valid (run with `--dry-run` before deploying)
- [ ] **Google Slides:** Presentation renders correctly (wait 10-30s after deploy)

---

## Troubleshooting

### Issue: "credentials.json not found"

**Fix:** Download OAuth 2.0 Desktop app JSON from Google Cloud Console and save to `scripts/credentials.json`

### Issue: "No requests found in JSON"

**Fix:** Ensure batchUpdate payload generated with `--format json` or `--format both`

### Issue: Presentation deploys but slides are blank

**Fix:**
1. Wait 10-30 seconds (Google Slides API processing time)
2. Refresh browser (Cmd+R)
3. Check JSON payload: `python deploy_to_google_slides.py --json-file <file> --dry-run`

### Issue: "PERMISSION_DENIED" when deploying

**Fix:** Ensure `credentials.json` has Slides API + Drive API permissions; re-download if needed

---

## File Manifest

| File | Purpose | Status |
|------|---------|--------|
| `build_mt_monthly_ppt.py` | Main deck generator (18 slides, dual-export) | ✓ Production |
| `mt_deck_ir.py` | Platform-agnostic IR builder | ✓ Production |
| `gslides_exporter.py` | Google Slides API serializer | ✓ Production |
| `mt_analytics_engine.py` | Calculation engine (waterfall, ROI, matrix) | ✓ Production |
| `deploy_to_google_slides.py` | Live Slides deployment (OAuth 2.0) | ✓ Production |
| `test_gslides_export.py` | Google Slides validation (11 tests) | ✓ All passing |
| `test_analytics_engine.py` | Analytics validation (9 tests) | ✓ All passing |

---

## Example Workflows

### Workflow A: Weekly Update (PPTX only)

```bash
# Monday morning: Generate this week's deck
python build_mt_monthly_ppt.py --month september --year 2026 --format pptx

# Download MT_september2026.pptx
# Send via email to zone managers
```

### Workflow B: Live Leadership Review (Google Slides)

```bash
# Friday before review: Generate and deploy
python build_mt_monthly_ppt.py --month september --year 2026 --format both

# Deploy JSON to Slides
python deploy_to_google_slides.py \
  --json-file MT_september2026_gslides_batch.json \
  --title "MT Q1 Review - Live"

# Share link: https://docs.google.com/presentation/d/.../edit
# Presenters can click through live during meeting
```

### Workflow C: Archive & Audit (Both formats)

```bash
# End of month: Generate both formats for record
python build_mt_monthly_ppt.py --month september --year 2026 --format both

# Archive both to OneDrive/Drive
# - MT_september2026.pptx (backup for offline access)
# - MT_september2026_gslides_batch.json (payload for re-deployment if needed)
```

---

## Performance Notes

- **PPTX generation:** ~2-3 seconds (18 slides, all shapes/text pre-computed)
- **Google Slides JSON:** ~1 second (serialization only; no API calls)
- **Google Slides deployment:** ~5-10 seconds (API batch operations)
- **Google Slides rendering:** 10-30 seconds (full slide rendering in browser)

---

## Next Steps

1. **Run end-to-end once:** Test all three steps (generate → validate → deploy)
2. **Integrate with calendar:** Set up weekly task to regenerate monthly deck
3. **Extend exporters:** Add PDF (via Google Slides), Excel data tables, Slack preview
4. **Add CI/CD:** Auto-generate decks on schedule; commit to git; push to Drive

---

**Questions?** Review comments in individual scripts or check validation test suites.

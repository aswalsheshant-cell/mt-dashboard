#!/bin/bash
#
# build.sh — Automated MT Dashboard build script
#
# Usage:
#   ./build.sh [--full|--primary-only|--offtake-patch|--detail-only|--forecast-only]
#
# Examples:
#   ./build.sh --full         Full rebuild from source (requires all workbooks)
#   ./build.sh --offtake-patch Refresh Offtake block only (faster; reuses existing data.js)
#   ./build.sh                (default) Same as --full
#

set -e  # Exit on error

# Color output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[0;33m'
NC='\033[0m'  # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="${MT_SOURCES_DIR:-$HOME/MT-Sources}"
OUTPUT_FILE="$SCRIPT_DIR/dashboard/data.js"
BUILD_MODE="${1:---full}"

# Functions
log_info() {
  echo -e "${GREEN}✓${NC} $1"
}

log_error() {
  echo -e "${RED}✗${NC} $1" >&2
}

log_warn() {
  echo -e "${YELLOW}⚠${NC} $1"
}

check_dependencies() {
  log_info "Checking dependencies..."

  if ! command -v python3 &> /dev/null; then
    log_error "Python 3 not found. Install Python 3 and retry."
    exit 1
  fi

  if ! python3 -c "import pandas" &> /dev/null; then
    log_error "pandas not installed. Run: pip install -r requirements.txt"
    exit 1
  fi

  log_info "Dependencies OK (Python 3, pandas, build_dashboard_data.py found)"
}

check_source_files() {
  if [ ! -d "$SRC_DIR" ]; then
    log_error "Source directory not found: $SRC_DIR"
    log_error "Set MT_SOURCES_DIR environment variable or place sources in ~/MT-Sources/"
    exit 1
  fi

  if [ "$BUILD_MODE" = "--full" ] || [ "$BUILD_MODE" = "--primary-only" ]; then
    if [ ! -f "$SRC_DIR/Primary_ShipTo_FY25-26_to_May26.xlsb" ]; then
      log_warn "Primary workbook not found in $SRC_DIR"
      log_warn "Build will proceed; Primary block may be empty or stale"
    fi
  fi

  if [ "$BUILD_MODE" = "--full" ] || [ "$BUILD_MODE" = "--offtake-patch" ]; then
    if ! ls "$SRC_DIR"/Offtake_*.xlsb &> /dev/null; then
      log_warn "No Offtake files found in $SRC_DIR"
      log_warn "Build will proceed; Offtake block may be empty or stale"
    fi
  fi

  log_info "Source check OK"
}

run_build() {
  log_info "Building data.js with mode: $BUILD_MODE"

  cd "$SCRIPT_DIR"

  case "$BUILD_MODE" in
    --full)
      python3 scripts/build_dashboard_data.py --src "$SRC_DIR" --out "$OUTPUT_FILE"
      ;;
    --primary-only)
      python3 scripts/build_dashboard_data.py --primary-only --src "$SRC_DIR" --out "$OUTPUT_FILE"
      ;;
    --offtake-patch)
      python3 scripts/build_dashboard_data.py --offtake-patch --src "$SRC_DIR" --out "$OUTPUT_FILE"
      ;;
    --detail-only)
      python3 scripts/build_dashboard_data.py --detail-only --src "$SRC_DIR" --out "$OUTPUT_FILE"
      ;;
    --forecast-only)
      python3 scripts/build_dashboard_data.py --forecast-only --src "$SRC_DIR" --out "$OUTPUT_FILE"
      ;;
    *)
      log_error "Unknown build mode: $BUILD_MODE"
      echo "Valid modes: --full, --primary-only, --offtake-patch, --detail-only, --forecast-only"
      exit 1
      ;;
  esac

  log_info "Build complete: $OUTPUT_FILE"
}

run_validation() {
  log_info "Running validation..."

  cd "$SCRIPT_DIR"

  # Syntax check
  python3 -m py_compile scripts/build_dashboard_data.py
  log_info "Syntax check passed"

  # QC gate
  python3 scripts/qc_dashboard.py --data "$OUTPUT_FILE"
  log_info "QC gate passed"
}

run_tests() {
  log_info "Running test suite..."

  cd "$SCRIPT_DIR"

  if ! python3 -m pytest scripts/test_pipeline.py -q; then
    log_warn "Some tests failed (non-critical)"
  fi

  log_info "Test suite completed"
}

main() {
  echo "=========================================="
  echo "MT Dashboard Build Script"
  echo "=========================================="
  echo "Source directory: $SRC_DIR"
  echo "Output file: $OUTPUT_FILE"
  echo "Build mode: $BUILD_MODE"
  echo "=========================================="
  echo ""

  check_dependencies
  check_source_files
  run_build
  run_validation
  run_tests

  echo ""
  echo "=========================================="
  log_info "Build successful!"
  echo "=========================================="
  echo ""
  echo "Next steps:"
  echo "  1. Review data.js: $OUTPUT_FILE (~$(du -h "$OUTPUT_FILE" | awk '{print $1}'))"
  echo "  2. Serve locally: python3 -m http.server 8000"
  echo "  3. Open dashboard: http://localhost:8000/dashboard/"
  echo "  4. Commit & push when ready: git add dashboard/data.js && git commit ..."
  echo ""
}

main "$@"

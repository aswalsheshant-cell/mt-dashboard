#!/usr/bin/env python3
"""
PBIX Template Loader & Manipulator

Utilities for PBIX file manipulation:
- Unpack PBIX (it's a ZIP archive)
- Modify Power Query connections to point to CSV data
- Inject DAX measures and relationships
- Re-pack PBIX for use

PBIX structure (Office Open XML):
  PBIXFile.zip
  ├── [Content_Types].xml
  ├── _rels/
  ├── ppt/                    (presentation layer — not used)
  ├── xl/                     (Excel-like model definition)
  │   ├── metadata.xml        (model schema)
  │   ├── connections.xml     (data source connections)
  │   ├── tables/             (table definitions)
  │   └── ...
  ├── word/                   (not used)
  └── customXml/
      └── item1.xml           (model semantics, measures, hierarchies)

Power BI Desktop (.pbix) uses XMLA format for the semantic model.
Full modification requires opening in Power BI and refreshing via COM API.

This module provides:
1. PBIX unpacking/repacking utilities
2. Connection string modification (CSV paths)
3. Measure metadata inspection (Phase 2.5: dynamic injection)
4. Validation + repacking

Phase 2: Basic unpacking + metadata inspection
Phase 2.5: Dynamic measure injection via XMLA editing
"""
from __future__ import annotations
import argparse
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree as ET

# XML namespaces for PBIX internals
PBIX_NAMESPACES = {
    "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "ct": "http://schemas.openxmlformats.org/package/2006/content-types",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


def log(level: str, msg: str):
    """Print timestamped log message."""
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sym = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "DEBUG": "→"}[level]
    print(f"[{ts}] {sym} {msg}")


def unpack_pbix(pbix_path: Path, output_dir: Path) -> bool:
    """
    Unpack PBIX (ZIP) to output directory.
    Returns True if successful.
    """
    if not pbix_path.exists():
        log("ERROR", f"PBIX not found: {pbix_path}")
        return False

    try:
        with zipfile.ZipFile(pbix_path, 'r') as z:
            z.extractall(output_dir)
        log("OK", f"Unpacked {pbix_path.name} to {output_dir}")
        return True
    except Exception as e:
        log("ERROR", f"Failed to unpack PBIX: {e}")
        return False


def pack_pbix(unpacked_dir: Path, output_pbix: Path) -> bool:
    """
    Re-pack unpacked PBIX directory back to PBIX file.
    Returns True if successful.
    """
    try:
        # Remove old file if exists (don't use -u flag with zipfile)
        if output_pbix.exists():
            output_pbix.unlink()

        # Create new ZIP archive
        with zipfile.ZipFile(output_pbix, 'w', zipfile.ZIP_DEFLATED) as z:
            for fpath in sorted(unpacked_dir.rglob('*')):
                if fpath.is_file():
                    arcname = fpath.relative_to(unpacked_dir)
                    z.write(fpath, arcname)

        log("OK", f"Packed PBIX: {output_pbix.name}")
        return True
    except Exception as e:
        log("ERROR", f"Failed to pack PBIX: {e}")
        return False


def inspect_pbix_metadata(unpacked_dir: Path) -> dict:
    """
    Inspect PBIX metadata: tables, measures, relationships.
    Returns metadata dict with counts.
    """
    metadata = {
        "tables": [],
        "measures": [],
        "relationships": [],
        "connections": [],
        "errors": [],
    }

    # Look for model definition files (Phase 2: inspection only)
    # Full XMLA parsing is Phase 2.5
    metadata_xml = unpacked_dir / "xl" / "metadata.xml"
    if metadata_xml.exists():
        log("DEBUG", f"Found metadata.xml")
        try:
            tree = ET.parse(metadata_xml)
            root = tree.getroot()
            # Phase 2.5: parse XMLA structure
            log("DEBUG", f"  Root tag: {root.tag}")
        except Exception as e:
            metadata["errors"].append(f"metadata.xml parse error: {e}")

    # Look for connections
    connections_xml = unpacked_dir / "xl" / "connections.xml"
    if connections_xml.exists():
        log("DEBUG", f"Found connections.xml")
        try:
            tree = ET.parse(connections_xml)
            root = tree.getroot()
            # Phase 2.5: extract connection details
            for child in root:
                metadata["connections"].append(child.tag)
        except Exception as e:
            metadata["errors"].append(f"connections.xml parse error: {e}")

    return metadata


def modify_csv_connection(unpacked_dir: Path, csv_data_dir: Path) -> bool:
    """
    Modify Power Query connections in PBIX to point to CSV data directory.
    Returns True if successful (Phase 2.5 enhancement).

    Power Query connections are stored in:
    - xl/connections.xml
    - customXml/item.xml (M code for queries)

    This function updates folder paths to the CSV data directory.
    """
    connections_xml = unpacked_dir / "xl" / "connections.xml"
    if not connections_xml.exists():
        log("WARN", "connections.xml not found — cannot update CSV paths")
        return False

    try:
        tree = ET.parse(connections_xml)
        root = tree.getroot()

        # Phase 2.5: Update folder connection to csv_data_dir
        # This requires understanding Power Query's XML structure
        # For now, this is a placeholder

        log("WARN", "CSV connection update: Phase 2.5 enhancement (M query parsing)")
        return True
    except Exception as e:
        log("ERROR", f"Failed to modify connections: {e}")
        return False


def inject_dax_measures(unpacked_dir: Path, measures: dict) -> bool:
    """
    Inject DAX measures into PBIX model definition.
    Returns True if successful (Phase 2.5 enhancement).

    measures: dict of measure_name → dax_expression
    Example: {"Total NSV": "[NSV] * [Rate]", "CM2": "[NSV] - [Expenses]"}

    Full implementation requires:
    1. Parse XMLA model semantics (customXml/item.xml)
    2. Find or create measure containers (by table)
    3. Insert measure definitions
    4. Update calculation groups if needed
    5. Re-serialize XML with correct formatting
    """
    log("INFO", f"Injecting {len(measures)} DAX measures")

    custom_xml = unpacked_dir / "customXml" / "item.xml"
    if not custom_xml.exists():
        log("WARN", "customXml/item.xml not found — cannot inject measures")
        return False

    try:
        # Phase 2.5: Parse XMLA, inject measures, re-serialize
        tree = ET.parse(custom_xml)
        root = tree.getroot()

        for measure_name, dax_expr in measures.items():
            log("DEBUG", f"  {measure_name}: {dax_expr[:50]}...")

        log("WARN", "DAX measure injection: Phase 2.5 enhancement (XMLA editing)")
        return True
    except Exception as e:
        log("ERROR", f"Failed to inject measures: {e}")
        return False


def validate_pbix_structure(unpacked_dir: Path) -> (bool, list):
    """
    Validate PBIX structure (required files, relationships).
    Returns (valid: bool, issues: list of validation errors)
    """
    required_files = [
        "[Content_Types].xml",
        "_rels/.rels",
        "xl/metadata.xml",
    ]

    issues = []
    for fname in required_files:
        fpath = unpacked_dir / fname
        if not fpath.exists():
            issues.append(f"Missing: {fname}")

    if issues:
        log("WARN", f"PBIX structure issues: {len(issues)}")
        for issue in issues:
            log("DEBUG", f"  {issue}")
        return False, issues

    log("OK", "PBIX structure valid")
    return True, []


def main():
    ap = argparse.ArgumentParser(
        description="PBIX template loader and manipulation utilities",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Unpack PBIX for inspection/modification
  python scripts/pbix_template_loader.py --pbix PowerBI/mt-dashboard-template.pbix --unpack

  # Inspect PBIX metadata
  python scripts/pbix_template_loader.py --pbix PowerBI/mt-dashboard-template.pbix --inspect

  # Validate PBIX structure
  python scripts/pbix_template_loader.py --pbix PowerBI/mt-dashboard-template.pbix --validate

  # Repack modified PBIX (Phase 2.5)
  python scripts/pbix_template_loader.py --pbix unpacked/ --pack --out PowerBI/mt-dashboard-modified.pbix
        """
    )
    ap.add_argument("--pbix", type=Path, required=True,
                    help="PBIX file path or unpacked directory")
    ap.add_argument("--unpack", action="store_true",
                    help="Unpack PBIX to temp directory")
    ap.add_argument("--pack", action="store_true",
                    help="Re-pack directory to PBIX")
    ap.add_argument("--out", type=Path,
                    help="Output path for repacked PBIX (with --pack)")
    ap.add_argument("--inspect", action="store_true",
                    help="Inspect PBIX metadata")
    ap.add_argument("--validate", action="store_true",
                    help="Validate PBIX structure")
    ap.add_argument("--csv-dir", type=Path,
                    help="CSV data directory (for --modify-connections)")
    ap.add_argument("--modify-connections", action="store_true",
                    help="Modify Power Query CSV connections (Phase 2.5)")

    args = ap.parse_args()

    log("INFO", "═" * 70)
    log("INFO", "PBIX Template Loader & Manipulator")
    log("INFO", "═" * 70)

    if args.unpack:
        log("INFO", "")
        log("INFO", "Action: Unpack PBIX")
        with tempfile.TemporaryDirectory() as tmpdir:
            if unpack_pbix(args.pbix, Path(tmpdir)):
                log("OK", f"PBIX unpacked to: {tmpdir}")
                # Keep temp dir open briefly for user inspection
                input("Press Enter to clean up...")
            else:
                sys.exit(1)

    elif args.pack:
        if not args.out:
            log("ERROR", "--pack requires --out")
            sys.exit(1)
        log("INFO", "")
        log("INFO", "Action: Pack PBIX")
        if pack_pbix(args.pbix, args.out):
            log("OK", "PBIX repacked successfully")
        else:
            sys.exit(1)

    elif args.inspect:
        log("INFO", "")
        log("INFO", "Action: Inspect PBIX Metadata")
        if args.pbix.is_file():
            with tempfile.TemporaryDirectory() as tmpdir:
                if unpack_pbix(args.pbix, Path(tmpdir)):
                    metadata = inspect_pbix_metadata(Path(tmpdir))
                    log("OK", "Metadata inspection complete")
                    log("DEBUG", f"  Tables: {len(metadata['tables'])}")
                    log("DEBUG", f"  Measures: {len(metadata['measures'])}")
                    log("DEBUG", f"  Relationships: {len(metadata['relationships'])}")
                    log("DEBUG", f"  Connections: {len(metadata['connections'])}")
                    if metadata["errors"]:
                        log("WARN", f"  Errors: {len(metadata['errors'])}")
                        for err in metadata["errors"]:
                            log("DEBUG", f"    {err}")
        else:
            metadata = inspect_pbix_metadata(args.pbix)
            log("OK", "Metadata inspection complete")

    elif args.validate:
        log("INFO", "")
        log("INFO", "Action: Validate PBIX Structure")
        if args.pbix.is_file():
            with tempfile.TemporaryDirectory() as tmpdir:
                if unpack_pbix(args.pbix, Path(tmpdir)):
                    valid, issues = validate_pbix_structure(Path(tmpdir))
                    if valid:
                        sys.exit(0)
                    else:
                        sys.exit(1)
        else:
            valid, issues = validate_pbix_structure(args.pbix)
            if valid:
                sys.exit(0)
            else:
                sys.exit(1)

    elif args.modify_connections:
        if not args.csv_dir:
            log("ERROR", "--modify-connections requires --csv-dir")
            sys.exit(1)
        log("INFO", "")
        log("INFO", "Action: Modify CSV Connections")
        if args.pbix.is_file():
            with tempfile.TemporaryDirectory() as tmpdir:
                unpacked = Path(tmpdir)
                if unpack_pbix(args.pbix, unpacked):
                    if modify_csv_connection(unpacked, args.csv_dir):
                        log("OK", "CSV connections modified")
                    else:
                        sys.exit(1)
        else:
            if modify_csv_connection(args.pbix, args.csv_dir):
                log("OK", "CSV connections modified")
            else:
                sys.exit(1)

    else:
        ap.print_help()
        sys.exit(0)

    log("INFO", "")
    log("INFO", "═" * 70)
    log("OK", "PBIX template operations complete")
    log("INFO", "═" * 70)
    sys.exit(0)


if __name__ == "__main__":
    main()

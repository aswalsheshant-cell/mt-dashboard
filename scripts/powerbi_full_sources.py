"""Read-only physical source coverage; this does not execute Power Query."""
import argparse
import csv
import json
import re
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path


def _period(value, row):
    return _parse_period((value or '').strip(), (row.get('Year') or '').strip(), (row.get('FY') or row.get('FY Year') or '').strip())


@lru_cache(maxsize=8192)
def _parse_period(value, year, fy):
    if re.fullmatch(r'\d{4}-\d{2}(?:-\d{2})?', value):
        try:
            datetime.strptime(value[:7], '%Y-%m')
            return value[:7]
        except ValueError:
            return None
    for fmt in ("%b'%y", '%b-%y', '%b_%y', '%b %Y', '%B %Y', '%d/%m/%Y', '%m/%d/%Y', '%Y/%m/%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m')
        except ValueError:
            pass
    months = {datetime(2000, m, 1).strftime('%b').lower(): m for m in range(1, 13)}
    month = months.get(value[:3].lower())
    year = year.removesuffix('.0')
    if not year:
        match = re.search(r'(20\d{2})\D*(\d{2,4})', fy)
        short = re.fullmatch(r'FY(\d{2})-(\d{2})', fy, re.IGNORECASE)
        if short and int(short[2]) == (int(short[1]) + 1) % 100 and month:
            year = str(2000 + int(short[1]) + (month < 4))
        elif match and month:
            year = str(int(match[1]) + (month < 4))
    if month and re.fullmatch(r'20\d{2}', year):
        return f'{year}-{month:02d}'
    return None


def inspect_sources(repo_root: Path, manifest_path: Path) -> dict:
    """Return physical rows, coverage and key issues, never changing inputs.

    available means readable files cover any required periods and dependencies;
    current_period_status is unassessed until a period is selected. Neither is Finance
    approval or model readiness. A missing/unreadable source has null row_count.
    Derived queries expose dependencies and null counts until model execution.
    """
    repo_root = Path(repo_root).resolve()
    manifest = json.loads(Path(manifest_path).read_text(encoding='utf-8-sig'))
    definitions = manifest['sources']
    ids = [source['id'] for source in definitions]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate source IDs in manifest')
    results = {}
    for source in definitions:
        matches = {pattern: [p for p in repo_root.glob(pattern)
                             if p.is_file() and not p.name.startswith('_')]
                   for pattern in source.get('paths', [])}
        files = sorted({p for paths in matches.values() for p in paths})
        missing_paths = sorted(pattern for pattern, paths in matches.items() if not paths)
        issues = [{'type': 'missing_file', 'path': pattern} for pattern in missing_paths]
        periods, keys = set(), Counter()
        count = 0
        readable = False
        for path in files:
            if path.suffix.lower() != '.csv':
                issues.append({'type': 'unsupported_format', 'file': path.relative_to(repo_root).as_posix()})
                continue
            try:
                with path.open(encoding='utf-8-sig', newline='') as stream:
                    reader = csv.DictReader(stream)
                    headers = reader.fieldnames or []
                    if not headers:
                        raise ValueError('Missing CSV header')
                    missing = set(source.get('key_columns', [])) - set(headers)
                    if missing:
                        issues.append({'type': 'missing_key_columns', 'file': path.relative_to(repo_root).as_posix(), 'columns': sorted(missing)})
                    for row in reader:
                        if not any(v for v in row.values()):
                            continue
                        count += 1
                        if None in row or any(value is None for value in row.values()):
                            issues.append({'type': 'malformed_row', 'file': path.relative_to(repo_root).as_posix(), 'row': reader.line_num})
                            continue
                        for column in source.get('period_columns', []):
                            value = row.get(column, '') or ''
                            period = _period(value, row)
                            if period:
                                periods.add(period)
                                break
                            quarter = re.fullmatch(r'([A-Za-z]{3})-([A-Za-z]{3}) (20\d{2})', value.strip())
                            if quarter:
                                first = datetime.strptime(quarter[1], '%b').month
                                last = datetime.strptime(quarter[2], '%b').month
                                periods.update(f'{quarter[3]}-{m:02d}' for m in range(first, last + 1))
                                break
                        if source.get('key_columns') and not missing:
                            key = tuple((row.get(c) or '').strip() for c in source['key_columns'])
                            if any(not part for part in key):
                                issues.append({'type': 'blank_key', 'file': path.relative_to(repo_root).as_posix(), 'row': reader.line_num})
                            else:
                                keys[key] += 1
                    readable = True
            except (OSError, UnicodeError, csv.Error, ValueError) as exc:
                issues.append({'type': 'read_error', 'file': path.relative_to(repo_root).as_posix(), 'message': str(exc)})
        for key, occurrences in keys.items():
            if occurrences > 1:
                issues.append({'type': 'duplicate_key', 'key': list(key), 'occurrences': occurrences})
        required = source.get('required_periods', manifest.get('required_periods', [])) if source.get('period_columns') else []
        missing_periods = sorted(set(required) - periods)
        available = readable and not missing_periods and not any(i['type'] in ('read_error', 'unsupported_format', 'missing_file', 'malformed_row') for i in issues)
        current_status = ('unassessed' if not required else 'available' if available else 'unavailable') if source.get('period_columns') else 'not_applicable'
        results[source['id']] = {
            'files': [p.relative_to(repo_root).as_posix() for p in files],
            'periods': sorted(periods), 'row_count': count if readable else None,
            'key_issues': issues, 'available': available,
            'missing_paths': missing_paths, 'current_period_status': current_status,
            'current_period_available': current_status == 'available',
            'missing_periods': missing_periods, 'grain': source.get('grain'),
            'dimensions': source.get('dimensions', []), 'dependencies': source.get('dependencies', []),
            'inspection_basis': 'physical_source_rows' if files else 'no_physical_source',
        }
    # Resolve the dependency graph independently of manifest order. Physical
    # inputs keep their own files/counts; their readiness also needs dependencies.
    by_id = {source['id']: source for source in definitions}
    resolved, visiting = set(), set()

    def resolve(source_id):
        if source_id in resolved:
            return
        if source_id in visiting:
            raise ValueError(f'Cyclic source dependency: {source_id}')
        if source_id not in by_id:
            raise ValueError(f'Unknown source dependency: {source_id}')
        visiting.add(source_id)
        source, entry = by_id[source_id], results[source_id]
        dependency_ids = source.get('dependencies', [])
        for dependency_id in dependency_ids:
            resolve(dependency_id)
        if dependency_ids:
            dependencies = [results[d] for d in dependency_ids]
            unavailable = [d for d in dependency_ids if not results[d]['available']]
            entry['key_issues'].extend({'type': 'unavailable_dependency', 'source': d} for d in unavailable)
            if not source.get('paths'):
                entry.update(available=not unavailable,
                             files=sorted({f for d in dependencies for f in d['files']}),
                             periods=sorted(set.intersection(*(set(d['periods']) for d in dependencies))),
                             inspection_basis='dependency_coverage_only')
            else:
                entry['available'] = entry['available'] and not unavailable
            period_dependencies = [d for d in dependencies if d['current_period_status'] != 'not_applicable']
            required = source.get('required_periods', manifest.get('required_periods', []))
            if source.get('period_columns') or period_dependencies:
                entry['missing_periods'] = sorted(set(entry['missing_periods']) | {p for d in period_dependencies for p in d['missing_periods']})
                if not required:
                    entry['current_period_status'] = 'unassessed'
                elif entry['available'] and all(d['current_period_available'] for d in period_dependencies):
                    entry['current_period_status'] = 'available'
                else:
                    entry['current_period_status'] = 'unavailable'
                entry['current_period_available'] = entry['current_period_status'] == 'available'
        visiting.remove(source_id)
        resolved.add(source_id)

    for source_id in ids:
        resolve(source_id)
    return {'schema_version': 1, 'required_periods': manifest.get('required_periods', []), 'sources': results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo-root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    print(json.dumps(inspect_sources(args.repo_root, args.manifest or args.repo_root / 'PowerBI/full_report_sources.json'), indent=2))


if __name__ == '__main__':
    main()

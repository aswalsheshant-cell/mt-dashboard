# GitHub Actions checklist

For every workflow file the PR adds or changes, and for every workflow whose result the
PR's claim depends on.

## Result integrity

- [ ] No `continue-on-error: true` on a required validation step
- [ ] **pwsh**: a step fails only on the last native command's exit code. After each
      `python`, `node` or `.exe` call that matters:
      `if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }`
- [ ] **bash**: with no `shell:` GitHub runs `bash -e {0}` (no pipefail, so a pipe keeps
      only the last command's status); `shell: bash` adds `-o pipefail`. `cmd || true`
      and `|| echo` hide failures either way
- [ ] Optional diagnostics are visible (`::warning::`), not silent
- [ ] `if: failure()` / `if: always()` steps cannot turn a failed job green
- [ ] Reading the result: open the job log; a success conclusion over a
      `CI RUN FAILED` or `exit code 1` line is a masked failure

## Supply chain and permissions

- [ ] Every `uses:` pinned to a full 40-character commit SHA (CLAUDE.md invariant 4),
      with the tag in a trailing comment; verify the SHA exists upstream before changing it
- [ ] `permissions:` set to the least needed (`contents: read` unless the job writes)
- [ ] No secret echoed; no untrusted PR text interpolated into `run:` (`${{ github.event... }}`)

## Coverage

- [ ] Triggers (`on:` / `paths:` / `paths-ignore:`) actually fire for the files the PR changes
- [ ] The new test is collected by a workflow that runs (e.g. Production Acceptance Gate
      runs `pytest tests/`; browser `.js` tests are mostly not run by CI — guard the
      behaviour with a string check in "Validate HTML Structure & Fixes" instead)
- [ ] A test that skips when a tool is missing is shown to run on the runner (pass/skip
      counts in the log match a local run with the tool present)

## Known environment signatures (label, do not "fix")

- `CAPIError: 400 The requested model is not supported` in the code-scanning job →
  `BLOCKED_ENVIRONMENT` (CB-09) only after reading that run's own log.
- Node 20 deprecation warnings → informational until the action pins are updated.

# API Retry Lab — v0.1.0 (experimental pre-release candidate)

[日本語](README_ja.md) · Python 3.11+ · standard library only · localhost only

Reproduce HTTP response loss, retry and duplicate synthetic business effects.
Independent of SQLite Fault Lab and Data Transfer Guard. No external API target,
telemetry, production data, credentials or proxy feature.

**Release status:** GitHub Actions CI for Ubuntu and Windows × Python 3.11,
3.12 and 3.13 **passed all six jobs** on 2026-11-14 (JST), as observed in
the repository owner's GitHub Actions run #1 screenshot (commit `6b5891d`).
The source repository was **Private** at this documentation update; public
visibility and the `v0.1.0` release are separate, not-yet-confirmed steps.
`evidence/ci_status.json` is the **historical pre-CI snapshot**, not the
current result. See `evidence/ci_verified_20261114.json` for the post-run record.
CI verifies the specified tests, not production API safety or commercial value.

## Quick start

From the extracted directory, using a fresh output name each time:

```bash
python3 arl.py demo --out my-run-001
python3 arl.py run --scenario safe_replay --out my-run-002
python3 arl.py list
python3 -m unittest discover -s tests -v
```

On Windows PowerShell replace `python3` with `py -3`. Python must already be
installed; no pip packages or additional services are needed. Parent output
directory must exist. The tool refuses existing output directories.

Exit 0 means all expected observations match; 1 means a mismatch; 2 means
INVALID_TEST / input, environment, startup or report-write failure. Output
creation/write errors are reported as a JSON object on stdout with exit 2;
existing files are not overwritten. Partial files after write failures are not
successful evidence. Internal `_server` startup exceptions also emit JSON/2.

The existing 23 scenarios are preserved. For example `safe_replay` loses the
response after commit, observes UNKNOWN, reads back in another HTTP request,
then replays the same key: effect count stays 1. `unsafe_retry` intentionally
uses another key, creates two effects and detects the defect. Its `passed=true`
means successful negative-control detection, not safe business behaviour.

## FIX-01 Retry-After contract

```bash
python3 arl.py run --scenario 429_valid --retry-after 1 --out my-run-wait
python3 arl.py run --scenario 429_valid --retry-after=-1 --out my-run-hold
```

ASCII unsigned integer seconds **0 or 1** are supported. Cap is 1 second.
Positive 1-second and zero waits are measured with a monotonic clock; actual
wait duration and retry count are in the case trace. At most one retry (two
POST attempts) occurs. Values greater than 1, negative values, empty strings,
non-numeric text and HTTP dates cause HOLD_UNKNOWN and no retry. HTTP date
support is deliberately excluded. The seven forms are exercised through real
HTTP 429 responses. A safely held unsupported value matches its expected test
outcome and therefore exits 0, while its safety finding remains HOLD_UNKNOWN.

## Evidence and reproducibility

`summary.json` and case `result.json`, client `trace.jsonl`, server
`server.jsonl`, stderr logs and SQLite state separate HTTP observations from
persisted effects. A test-harness DB read does not automatically resolve client
UNKNOWN. Raw synthetic keys and payloads are not personal data.

```bash
ARL_EVIDENCE=evidence-new python3 -m unittest discover -s tests -v
python3 compare.py --out comparison-new --repeats 10
python3 benchmark/measure_addition.py --out addition-new
```

PowerShell: set `$env:ARL_EVIDENCE='evidence-new'` before the test command.
The comparison baseline has its own HTTP server, client, database and checks;
it does not import ARL or its oracle. Four cases are compared: normal replay,
post-commit response loss, duplicate effect, payload conflict. Addition
experiment executes a third identical request using fresh modified copies.

Local pre-CI results: Linux Python 3.12.14 and 3.13.5, **46/46 tests each**;
original 23-scenario demo passed on both. Separately, the GitHub Actions
**six-job matrix passed** on Ubuntu/Windows × Python 3.11/3.12/3.13 at
commit `6b5891d` (run #1, screenshot supplied by repository owner).
macOS remains untested. The documentation changes made after that run must
pass CI again before public release.

## Scope

Keys are ASCII letters/digits/underscore/hyphen, 1–64 characters. Same key and
same canonical JSON payload reuses a result; conflicting payload returns 409.
This is a project-specific contract, not a declaration that an Idempotency-Key
draft is a final standard. The sample accepts operation_id `op-001` and integer
amount, with atomic key check and effect insert in SQLite.

Timeout scenario uses a controlled post-commit delay; extreme scheduler load
can still affect timing. Retry waits are lower-bounded by the requested value,
not exact real-time scheduling. Parallel scenario sends four requests together.
No TLS, arbitrary API adapter, distributed transaction, key expiry, load test
or disk-failure guarantee. All-state exactly-once, human savings and commercial
demand are not established. Comparison timings do not prove product superiority.

See TECHNICAL_SPEC.md, OSS_COMPARISON.md, REPORT_ja.md and RELEASE_DECISIONS.md.
MIT License with the owner's chosen copyright attribution `KenKan964`;
third-party rights and license compliance remain the publisher's responsibility.
GitHub Private Vulnerability Reporting is a **proposed** security contact and
has not been confirmed enabled. A Private GitHub repository exists; neither
public visibility nor the public `v0.1.0` release has been confirmed.

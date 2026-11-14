# API Retry Lab

**Reproduce HTTP retry failures and inspect whether a repeated request creates duplicate business effects.**

**v0.1.0 — Experimental · Python 3.11+ · Standard library only · Localhost only · MIT License**

**English** | [日本語](README_ja.md) · [v0.1.0 pre-release](https://github.com/KenKan964/api-retry-lab/releases/tag/v0.1.0)

## Why use it?

An HTTP client can time out **after** a server has committed an operation. The client may not know whether the operation succeeded. Blindly retrying with a different idempotency key can apply the same business effect twice.

API Retry Lab is a **free, reproducible local laboratory** for studying that situation. It starts a synthetic HTTP server on `127.0.0.1`, simulates failures at known points, replays requests, and compares the client's observations with the effects recorded in a local SQLite database.

This is a test harness for understanding retry and idempotency behavior, **not** a tool that connects to, repairs, or guarantees the safety of your production APIs.

## What can you test?

| Scenario | What it demonstrates |
| --- | --- |
| Response lost after commit | The server may have applied an operation even though the client did not receive a response |
| `safe_replay` | Read back over HTTP, then retry with the same key; one effect is retained |
| `unsafe_retry` | Retry with a different key; a deliberate duplicate effect is detected |
| Payload conflict | Reusing a key for a different payload is rejected |
| Timeouts / connection errors | Distinguish a failed observation from a confirmed operation |
| 429 / 503 responses | Exercise bounded retry and hold decisions |
| Concurrent requests | Exercise duplicate-effect protection under four parallel requests |
| Restart and mutants | Replay after restart and detect intentionally broken implementations |

The suite contains **23 defined scenarios**. Use `python arl.py list` to see their exact names.

## Quick start

**Requirements:** Python 3.11 or newer; no pip packages, external service, credentials, or network access beyond loopback.

From the repository root:

```sh
python arl.py list
python arl.py demo --out demo-001
python arl.py run --scenario safe_replay --out replay-001
python arl.py run --scenario unsafe_retry --out duplicate-001
```

On Windows, use `py -3` instead of `python` if needed. Supply a **new output directory** for each command; existing destinations are refused, and the parent directory must already exist.

The local HTTP service is started and stopped by the tool. No external URL is accepted.

## Interpreting the results

Two important examples:

- **`safe_replay`:** The synthetic operation is committed, its response is lost, the client observes an unknown outcome, a separate HTTP readback is performed, and replay with the **same key** retains **one** business effect.
- **`unsafe_retry`:** An intentionally unsafe retry uses a **different key** and creates **two** effects. The lab correctly identifies the defect.

A test scenario's `passed: true` means **the observed outcome matched the test expectation**. In particular, it does **not** mean the unsafe scenario is safe.

Look inside the output directory for the JSON case results, client `trace.jsonl`, server `server.jsonl`, stderr logs, and SQLite evidence. HTTP observations and the database's actual effects are kept separate: **a database check by the test harness must not be presented as knowledge the HTTP client already had.**

**CLI exit codes:**

| Code | Meaning |
| --- | --- |
| `0` | Expected test observations matched (including successful detection of an intentionally unsafe case) |
| `1` | A test expectation did not match the observation |
| `2` | `INVALID_TEST`: invalid inputs, startup, environment, or evidence-output failure |

A client-side `UNKNOWN` or `HOLD_UNKNOWN` may still be a **correctly observed test outcome** with exit code 0. Always read the findings and trace, not just the process exit code.

## Retry-After: deliberately narrow support

The laboratory supports HTTP 429 `Retry-After` values of **ASCII integer seconds `0` or `1`** only. It waits using a monotonic clock and makes **at most one retry** (two POST attempts in total).

```sh
python arl.py run --scenario 429_valid --retry-after 1 --out retry-wait-001
python arl.py run --scenario 429_valid --retry-after=-1 --out retry-hold-001
```

Values outside this supported contract — including integers above 1, negative values, empty values, text, and HTTP-date formats — produce a **`HOLD_UNKNOWN` decision without a retry**. An expected hold is not evidence that the original business operation succeeded.

## Verification

The repository includes **46 automated tests** (as recorded for the FIX-01 release candidate), the 23-scenario demo, and an independent HTTP/SQLite comparison. The comparison covers four cases and 80 executions in its recorded local experiment; it is not proof of superior detection, speed, reduced human effort, or commercial value.

**GitHub Actions:** Ubuntu and Windows × Python 3.11, 3.12, 3.13 — **all six jobs passed** on the published main-branch validation [run #14](https://github.com/KenKan964/api-retry-lab/actions/runs/43466471108). Check [Actions](https://github.com/KenKan964/api-retry-lab/actions) for the latest status, including changes after this README.

```sh
python -m unittest discover -s tests -v
python compare.py --out comparison-001 --repeats 10
python benchmark/measure_addition.py --out addition-001
```

The comparison and addition experiment create new output directories; use fresh names. `evidence/ci_status.json` is a **historical pre-CI snapshot** rather than the present status.

## Boundaries and safety

- **Synthetic loopback workloads only:** no public listening address, remote API adapter, TLS, proxy, telemetry, or production credentials.
- The sample contract accepts a fixed synthetic `operation_id`, integer `amount`, and locally scoped idempotency keys. This does **not** establish a general Idempotency-Key standard.
- The experiment separates HTTP uncertainty from database state. It **does not guarantee exactly-once execution across distributed systems**.
- Retry timing and process-fault injection are controlled test conditions, not guarantees under arbitrary scheduler delays, host crashes, or disk failures.
- This is not a penetration-testing tool, production load tester, or universal HTTP resilience library.
- Keep output artifacts free of real or confidential payloads. Test-only fault hooks do not accept arbitrary hosts, commands, or PIDs.

## Documentation

- [日本語 README](README_ja.md)
- [Technical specification](TECHNICAL_SPEC.md)
- [Security considerations](SECURITY.md)
- [Comparison scope and limitations](OSS_COMPARISON.md)
- [Release notes and decisions (historical pre-publication record)](RELEASE_DECISIONS.md)
- [Developer verification report](REPORT_ja.md)
- [Change history](CHANGELOG.md)
- [MIT License](LICENSE)

**License:** MIT · Copyright © 2026 KenKan964.

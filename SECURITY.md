# Security / セキュリティ

API Retry Lab is a synthetic localhost laboratory, not a production HTTP server.
Only 127.0.0.1 is used; there are no external URL, proxy, arbitrary command or
arbitrary PID parameters. Only owned child process handles are terminated.
The owner token prevents accidental reuse, not hostile same-user access.

Fault hooks are test-only: startup bind failure, missing executable, abnormal
child exit, readiness timeout and report-write failure. They operate only in
new laboratory directories. Never deploy this server to an exposed interface.
Parent SIGKILL, host/power failure and malicious concurrent filesystem changes
are outside cleanup guarantees. No cross-system exactly-once claim is made.

**Proposed private reporting channel:** GitHub Private Vulnerability Reporting
(Security → Report a vulnerability), after the repository owner enables it.
It is not configured yet. No email address or working reporting endpoint is
claimed. Do not disclose sensitive reports or real payloads in public issues.
The release owner must confirm the contact before publication; see
RELEASE_DECISIONS.md. No independent security audit is claimed.

セキュリティ連絡方法はGitHubの非公開脆弱性報告を候補として提出しています。
現時点では未有効化です。公開者が窓口とLICENSEを最終確認し、研究部審査・CI確認を経て公開可否を決定します。

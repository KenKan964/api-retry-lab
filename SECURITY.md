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

**Security reporting:** This repository is public and v0.1.0 is an
experimental pre-release. GitHub Private Vulnerability Reporting is the
proposed channel, but its activation has **not been independently verified**.
If the repository's Security tab offers “Report a vulnerability”, use that
private channel. Do not include security-sensitive details, private data,
or real credentials in public issues. No alternative private contact is
claimed here. No independent security audit has been performed.

GitHub Actions passed six jobs for the published main-branch
[run #14](https://github.com/KenKan964/api-retry-lab/actions/runs/43466471108).
Check newer workflow runs for later changes. CI does not prove production
resilience, security isolation, or cross-system exactly-once guarantees.

**日本語：** リポジトリとv0.1.0実験版は公開済みです。非公開の脆弱性報告機能は
候補ですが、有効化は独立確認できていません。Securityタブに非公開報告がある
場合はそれを利用し、機密情報を公開Issueに書かないでください。6環境CIの成功は
独立セキュリティ監査や本番での安全性の証明ではありません。

# API Retry Lab

**HTTP通信の失敗・再試行によって業務処理が二重適用される問題を、ローカル環境で再現・検証するツールです。**

**v0.1.0 — 実験版 · Python 3.11以降 · 標準ライブラリのみ · localhost限定 · MITライセンス**

[English](README.md) | **日本語** · [v0.1.0 Pre-release](https://github.com/KenKan964/api-retry-lab/releases/tag/v0.1.0)

## 何を解決するツールか

HTTP要求がサーバーで確定された**後**に応答が失われると、クライアントは処理が成功したか分からなくなります。その状態で異なる冪等性キーを使って再送すると、同じ業務効果が二重に発生することがあります。

API Retry Labは、そのような状況を**合成のローカルHTTPサーバー**で再現する無料の検証ツールです。`127.0.0.1`上で意図的に障害を起こし、再送時のHTTP観測とSQLiteに記録された業務効果を分けて確認します。

> **対象範囲：** ローカルの合成データによる実験環境です。本番APIを診断・修復するツールではなく、分散システムでのexactly-once処理を保証しません。

## 検証できること

| シナリオ | 検証する問題 |
| --- | --- |
| 確定後の応答喪失 | 応答がなくてもサーバーで処理済みの場合がある |
| `safe_replay` | 別HTTP要求で読戻した後、同じキーで再送して効果が1件に保たれる |
| `unsafe_retry` | 別キーで再送すると意図的に業務効果が2件となり、欠陥を検出できる |
| ペイロードの不一致 | 同一キーと異なる内容の組合せを拒否する |
| タイムアウト・接続異常 | 未確認の応答と確定済みの処理を区別する |
| HTTP 429・503 | 再試行・保留の判断を確認する |
| 並行要求 | 4件の同時要求に対する二重適用防止を検証する |
| 再起動・意図的欠陥 | 再起動後の再送と、不正な実装の検出を試験する |

既定で**23種類のシナリオ**を備えています。すべての名称は`python arl.py list`で確認できます。

## 最初に試す

**必要環境：** Python 3.11以降。pipでの追加インストールや外部サービス、認証情報は不要です。

リポジトリのルートディレクトリで実行します。

```sh
python arl.py list
python arl.py demo --out demo-001
python arl.py run --scenario safe_replay --out replay-001
python arl.py run --scenario unsafe_retry --out duplicate-001
```

Windowsでは必要に応じて`python`を`py -3`に置き換えてください。毎回**未使用の出力ディレクトリ**を指定してください。既存先は拒否され、親ディレクトリは事前に存在する必要があります。

HTTPサーバーはツールが起動・終了します。外部URLは指定できません。

## 結果をどう読むか

代表的な2例：

- **`safe_replay`：** 合成業務処理の確定後に応答が失われ、クライアントは結果不明となります。別のHTTP要求による読戻しと**同一キー**での再送を行っても、業務効果は**1件**です。
- **`unsafe_retry`：** 意図的に**異なるキー**で再送すると業務効果が**2件**発生し、その危険な再送を検出します。

シナリオ結果の`passed: true`は、**観測結果が試験の期待値に一致した**という意味です。危険な再送の安全性を示すものではありません。

出力ディレクトリには、JSONによるケース結果、クライアントの`trace.jsonl`、サーバーの`server.jsonl`、stderrログ、SQLiteの証拠などが残ります。**テスト側がDBの確定結果を知っていることと、HTTPクライアントが処理結果を確認できたことは異なります。**

**CLI終了コード：**

| コード | 意味 |
| --- | --- |
| `0` | 観測結果が期待値と一致（意図的な欠陥を正しく検出した場合も含む） |
| `1` | 期待する観測結果との不一致 |
| `2` | `INVALID_TEST`：入力、起動、環境、証拠出力などの失敗 |

クライアント側の`UNKNOWN`や`HOLD_UNKNOWN`が**期待どおりの試験結果**であれば、終了コードは0になり得ます。コードだけで業務成功と判断せず、診断と通信履歴を確認してください。

## Retry-Afterの対応範囲

HTTP 429の`Retry-After`には、ASCII数字による整数秒の**`0`と`1`のみ**対応します。単調時計で待機を計測し、再試行は**最大1回**（POSTは最大2回）です。

```sh
python arl.py run --scenario 429_valid --retry-after 1 --out retry-wait-001
python arl.py run --scenario 429_valid --retry-after=-1 --out retry-hold-001
```

1秒超、負数、空文字、数値以外の文字列、HTTP日付形式などは、**再試行せず`HOLD_UNKNOWN`**として保留します。正しく保留できた試験が合格しても、元の業務処理の成功を意味しません。

## 試験・検証状況

FIX-01時点で**46件の自動試験**、23種類のシナリオ、独立したHTTP/SQLite実装との比較があります。比較実験では4条件・80実行の期待判定が一致しましたが、検出性能・実行速度・人間の工数・商用価値が優れていることを示す結果ではありません。

**GitHub Actions：Ubuntu・Windows × Python 3.11／3.12／3.13の6環境すべて成功**。公開済み`main`に対する[実行#14](https://github.com/KenKan964/api-retry-lab/actions/runs/43466471108)で確認しました。このREADME以後の修正については[最新のActions](https://github.com/KenKan964/api-retry-lab/actions)を参照してください。

```sh
python -m unittest discover -s tests -v
python compare.py --out comparison-001 --repeats 10
python benchmark/measure_addition.py --out addition-001
```

比較実験と追加実験には新しい出力先を指定してください。`evidence/ci_status.json`の`NOT_RUN`は**CI導入前の履歴**であり、現在の実行状況ではありません。

## 安全上の注意と制限

- **localhost上の合成データ専用。** 公開ネットワークでの待受、本番API接続、TLS、プロキシ、テレメトリ、実アカウントの認証情報は扱いません。
- サンプルは固定の合成`operation_id`と整数の`amount`、ローカルの冪等性キーを使います。普遍的な`Idempotency-Key`仕様への準拠宣言ではありません。
- HTTP上の結果不明とDB上の確定を区別します。**分散環境でのexactly-onceを保証しません。**
- タイムアウトや障害注入は制御された実験であり、任意のOS負荷、電源断、実ディスク障害での安全性は未検証です。
- 侵入試験、性能負荷試験、汎用HTTPライブラリを目的とする製品ではありません。
- 機密データを証拠に含めないでください。試験用故障フックは任意のホスト・コマンド・PIDを受け付けません。

## 関連資料

- [English README](README.md)
- [技術仕様](TECHNICAL_SPEC.md)
- [セキュリティ上の注意](SECURITY.md)
- [独立比較と限界](OSS_COMPARISON.md)
- [公開前判断の履歴](RELEASE_DECISIONS.md)
- [検証報告書](REPORT_ja.md)
- [変更履歴](CHANGELOG.md)
- [MITライセンス](LICENSE)

**ライセンス：** MIT · Copyright © 2026 KenKan964.

# API Retry Lab — v0.1.0／実験版公開候補

[English](README.md)。Python 3.11以上・標準ライブラリのみ・localhost限定。
HTTP障害、再試行、合成業務効果の二重適用を検証します。既存23シナリオを維持しました。

**公開準備状況：** 2026年11月14日、GitHub ActionsでUbuntu／Windows × Python
3.11／3.12／3.13の**6ジョブすべてが成功**しました。リポジトリ所有者が提示した
実行#1の画面（コミット`6b5891d`）で確認しました。現時点のリポジトリはPrivateであり、
Publicへの変更とv0.1.0公開は別途実施・確認する工程です。
`evidence/ci_status.json`はCI実行前の**履歴資料**です。現在のCI確認結果は
`evidence/ci_verified_20261114.json`を参照してください。CI成功は本番安全性の保証ではありません。

## クイックスタート

```bash
python3 arl.py demo --out my-run-001
python3 arl.py run --scenario safe_replay --out my-run-002
python3 arl.py list
python3 -m unittest discover -s tests -v
```

Windows PowerShellでは `python3` を `py -3` に置き換えます。Python以外のインストールは不要。
出力先は未作成ディレクトリを指定し、親ディレクトリは事前に作成してください。
既存先は拒否します。終了0＝期待判定一致、1＝不一致、2＝INVALID_TEST／入力・起動・実行・出力異常。
出力先を作成／保存できないときはstdoutのJSONと終了2で報告します。
既存ファイルへエラーJSONを上書きしません。保存途中の不完全ファイルは合格証拠ではありません。

safe_replayは確定後応答喪失→UNKNOWN→別HTTP要求の読戻し→同じキー再送で効果1を確認します。
unsafe_retryは意図的に別キーで再送し、効果2と危険再送を検出します。
欠陥例のpassed=trueは「欠陥検出成功」であり、その処理が安全という意味ではありません。

## Retry-After

```bash
python3 arl.py run --scenario 429_valid --retry-after 1 --out my-run-wait
python3 arl.py run --scenario 429_valid --retry-after=-1 --out my-run-hold
```

ASCII非負整数秒の0と1に対応。上限1秒、最大2回のPOST（再試行1回）。
正の1秒・0秒を実際に待ち、単調時計で経過時間と再試行回数を記録します。
上限超過、負数、空文字、不正文字列、HTTP日付はHOLD_UNKNOWN・待機なし・再試行なし。
HTTP日付は未対応と明示したうえで安全に保留します。7形式すべて実HTTPで検証しました。
保留が期待どおりなら試験の終了は0ですが、業務安全判定はHOLD_UNKNOWNのままです。

## 再現・追加試験

```bash
ARL_EVIDENCE=evidence-new python3 -m unittest discover -s tests -v
python3 compare.py --out comparison-new --repeats 10
python3 benchmark/measure_addition.py --out addition-new
```

PowerShellでは先に `$env:ARL_EVIDENCE='evidence-new'` を指定します。
46試験をLinux Python 3.12.14／3.13.5で各46/46合格。既存23シナリオのデモも両環境で23/23一致。
別途、GitHub ActionsのUbuntu／Windows × Python 3.11／3.12／3.13の6ジョブが成功しています
（コミット`6b5891d`、実行#1）。macOSは未検証です。この文書修正後のコミットについては
公開前にCIを再確認します。

F02はポート初期化失敗、存在しない試験用実行ファイル、子の異常終了、準備待ちタイムアウト、
レポート書込み失敗を注入。JSONと終了2、起動した子のwait回収、既存ファイル不変を確認します。
このフックはローカル負例試験専用で、任意ホスト・コマンド・PIDを受け付けません。

F03のOSS基準はHTTPサーバー・クライアント・DB・判定を独立実装し、ARLもoracle.pyもimportしません。
4シナリオ×2方式×10回の80実行が一致。追加シナリオを実際に作成し、コード・設定差分も保存しました。
機械時間や行数を人間工数へ換算していません。工数削減、ROI、商用需要は未実証です。

## 範囲と公開候補

JSON/JSONLでHTTP観測・確定・再試行・独立DB照合を分けます。DBオラクルの知識をクライアントの確定知識にしません。
キーは英数字等1～64文字、operation_idはop-001固定、amountは整数。キー契約は本製品独自のものです。
タイムアウトは確定後の制御遅延で再現しますが、極端なスケジューリング遅延まで保証しません。
分散システムのexactly-once、本番API、TLS、負荷試験、鍵の期限切れ、ディスク障害は対象外です。

[技術仕様](TECHNICAL_SPEC.md)、[OSS比較](OSS_COMPARISON.md)、[是正報告](REPORT_ja.md)、
[公開候補の名義・窓口](RELEASE_DECISIONS.md)。MITライセンスの著作権表示は、
公開者が指定した`KenKan964`に変更しています。第三者の権利や利用条件の確認は引き続き必要です。
GitHub Private Vulnerability Reportingは窓口候補であり、現時点では未有効化です。
API Retry LabのPrivateリポジトリは作成済みですが、Public化・正式リリースは未確認です。
既存SQLite Fault Labのリポジトリは変更していません。

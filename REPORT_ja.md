# ARL-DEV-001 / FIX-01 是正報告書

提出日：2026-11-14（日本時間）。v0.1.0公開候補の限定是正。
**F01〜F03・F05は実装・ローカル検証済み。F04は環境制約による保留。GitHub公開はHOLD。**
研究部の独立審査と残るCI確認後に公開可否を決める。GitHub公開・リポジトリ作成は行っていない。
SQLite Fault LabとData Transfer Guardは変更対象外。旧ARL原本も保持した別ディレクトリで是正した。

## 実測結果

|項目|結果|証拠|
|---|---|---|
|Linux Python3.12.14 自動試験|46/46 OK、5.376秒|evidence/tests312.log|
|Linux Python3.13.5 自動試験|46/46 OK、4.937秒|evidence/tests313.log|
|既存HTTPシナリオ|両環境23/23期待一致|evidence/demo, demo313|
|F01|7種類の実HTTP Retry-After検証|evidence/fix01, fix01_python313|
|F02|起動・終了・タイムアウト・書込異常、既存先保護|同上、テストログ|
|F03|独立2方式4ケース10反復、80/80一致|evidence/f03|
|シナリオ追加実験|両方式期待一致、差分実測|evidence/f03_addition|
|F04|6ジョブすべてNOT_RUN|evidence/ci_status.json|

46試験は既存26件＋F01/F02追加15件＋独立基準5件。件数をシナリオ数と混同しない。
意図的欠陥のPASSは欠陥検出成功であり、安全な業務処理という意味ではない。

## F01 実測内訳（Python3.12）

|ヘッダ|判断|再試行数|待機実測秒|証拠JSON|
|---|---|---:|---:|---|
|-1|HOLD_UNKNOWN|0|0.000000440|F01_1bad6b8cf971.json|
|0|RETRY|1|0.000076332|F01_5feceb66ffc8.json|
|1|RETRY|1|1.001623391|F01_6b86b273ff34.json|
|Wed, 21 Oct 2037 07:28:00 GMT|HOLD_UNKNOWN|0|0.000000451|F01_7ba72400990d.json|
|oops|HOLD_UNKNOWN|0|0.000000581|F01_d13f2eadd4ed.json|
|2|HOLD_UNKNOWN|0|0.000000561|F01_d4735e3a265e.json|
|(空文字)|HOLD_UNKNOWN|0|0.000000591|F01_e3b0c44298fc.json|

0/1秒のみ対応、上限1秒・最大再試行1回。HTTP日付は未対応として保留する仕様。
異常値を待機0へ変換して再送しない。時刻はmonotonic実測でスケジューラ誤差を含む。

## F02 是正根拠

内部bind競合、存在しない試験用実行ファイル、子exit17、readiness timeout、
結果書込OSErrorを負例としてJSONのexit_code=2とプロセス終了2の一致を確認。
所有Popenの生成PIDと回収PIDを照合しwait完了を証拠化。spawn失敗には子PIDがない。
既存ディレクトリ拒否で合成markerのSHA-256不変を確認した。
不正な内部直接起動と親ディレクトリ欠落もJSON/2を確認。
書込障害は決定的な注入であり、実ディスク容量不足を発生させた試験ではない。
親自体の強制終了やOS障害時の子回収・ログ耐久性は保証しない。

## F03 比較評価

独立OSS-onlyはARL内部診断を利用せず、別HTTP/SQLite/判定を実装する。
機械時間中央値ARL 61.3496005ms、OSS 81.6910245ms。ただし証拠保存の負担差があり速度優位は主張しない。
追加実験はARLコード6行、OSS設定23行、各1ファイル・検証1コマンド。
初期構築は両方式Python1、追加pip0、外部サービス0。
人間の工数は未測定（null）。行数から工数削減率・商用需要を推定しない。
詳細はOSS_COMPARISON.md。原理の独占性はなく、配布・診断・再現手順の統合が追加価値。

## F04と公開判定

Ubuntu/Windows × Python3.11/3.12/3.13の6環境をCI設定に記載。
すべてNOT_RUN、run ID/job IDはnull。ローカルLinux結果をGitHub Actions合格と扱わない。
環境制約による保留は研究部継続指示に基づく。既存別製品リポジトリで代用実行しない。
**研究継続GO／公開HOLD（公開GOではない）。**
公開可能な段階で6ジョブのURL・run ID・commit SHA・ログ・証拠を追加し、研究部が独立再審査する。
LICENSEのMIT候補、著作権表示、非公開脆弱性報告先案はRELEASE_DECISIONS.mdとSECURITY.mdに整理。
公開者確認と連絡先有効化は未完了。商用化・本番組込みのGO判断は対象外。

## 再現と提出

Python標準ライブラリのみ。新規出力先を使う。

```bash
python -m unittest discover -s tests -v
python arl.py demo --out reproduced-demo
python compare.py --out reproduced-comparison --repeats 10
python benchmark/measure_addition.py --out reproduced-addition
```

審査用ZIPには全実測DB・JSON/JSONL・テストログを収録。
公開候補ZIPはソース、テスト、日英README、CI、仕様、集計・限定証拠を収録。
各ZIP内のMANIFEST.sha256は自己ファイルを除く全同梱ファイルのSHA-256。
自己署名・第三者監査ではない。大容量DBや所有token、pycacheを公開候補に含めない。

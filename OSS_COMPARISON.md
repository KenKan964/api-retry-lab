# OSS-only比較・FIX-01

旧版の共通fixture比較を置換し、標準Python HTTP＋SQLite＋unittestだけの独立実装を作成した。
ARLのサーバー・クライアント・診断・oracleを共有しない。比較ドライバと期待契約だけを共通化。
ベースラインも完全自動化し、同じlocalhost・合成payload・SQLite・新規試験先で実行する。

|共通契約|効果件数|HTTP結果|診断|
|---|---:|---|---|
|正常同一キー再送|1|200,200|なし|
|確定後応答喪失|1|応答なし|HOLD_UNKNOWN|
|意図的二重確定|2|200,200|DUPLICATE_EFFECT_DETECTED|
|同一キーpayload競合|1|200,409|PAYLOAD_CONFLICT_DETECTED|

Linux Python3.12.14、4ケース×2方式×10反復＝80/80期待一致。
seed=1001で各反復の方式順を入替。全試行はevidence/f03/summary.jsonと各DB・ログに保存。
実行時間中央値はARL 61.3496005ms、OSS-only 81.6910245ms。
起動・HTTP・SQL・診断・回収を含む。共通最終保存は除くがOSS側の内部結果保存が含まれる。
実装と証拠保存負担の差があるため速度優位の証明には使用しない。

## 追加シナリオの実測

同一キー3要求、効果1、再使用応答2を両方式に追加して実行した。
一時コピーを使用し、本体23シナリオは維持。patchと結果はevidence/f03_addition。

|測定項目|ARL|OSS-only|
|---|---:|---:|
|コード追加物理行数|6|0|
|設定追加物理行数|0|23|
|削除行数|0|0|
|変更ファイル数|1|1|
|検証コマンド呼出数|1|1|
|必要Python環境|1|1|
|pipパッケージ・外部サービス|0|0|
|Python導入後のインストールコマンド|0|0|
|人間作業時間・手動操作数|null（未測定）|null（未測定）|

コード変更と設定変更の分類はファイル種別。行数は書式に依存する。
上記はスクリプトが実行した変更・コマンド数で、人間の操作の観測ではない。
初期設定、原因調査、結果判定などの人間工数も未測定。削減率・ROI・需要は主張しない。

## 追加価値と限界

ARLの追加価値は23種の業務効果・応答喪失・再試行の契約、負例、独立読戻し、証拠を配布単位にまとめた点。
同じ原理は既存OSSで実装可能であり、4ケースではOSS-onlyも同じ安全性異常を検出した。
一般的な誤検知率や見逃し率、全23ケースに対するOSS比較は未測定。
WireMockの障害応答模擬、ToxiproxyのTCP障害注入との直接ベンチマークは行っていない。
参考機能の出典（旧審査資料の参照先）：https://wiremock.org/docs/simulating-faults/ 、https://github.com/Shopify/toxiproxy 。
これらに対する新規性や優位性の実証とは位置づけない。

再現：python compare.py --out NEW_COMPARISON --repeats 10
追加試験：python benchmark/measure_addition.py --out NEW_ADDITION
いずれも出力先は未存在のパスとする。

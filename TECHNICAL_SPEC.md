# ARL 技術仕様

## コンポーネント

arl.server: ThreadingHTTPServer子プロセス。所有tokenを照合し127.0.0.1:0へbind。
arl.exercise: 起動、HTTPクライアント、シナリオ手順、後処理。外部URLを受け付けない。
arl.main: list/demo/run、ディレクトリ排他新規作成、JSON保存。
oracle.audit: 読取専用SQLite接続で件数、commitログとreportの一致、連番、stderr空を確認。

POST /operationsはJSON operation_id、amountとIdempotency-Keyを要求する。
GET /operations/op-001は別HTTP要求による効果件数参照。GET /healthは準備状態。
DBのkeys(k PRIMARY KEY,p)とeffects(op,amount)をBEGIN IMMEDIATE内で操作する。
canonical payloadはsort_keys=TrueのJSON。金額は整数、操作IDは合成値固定。
意図的欠陥は重複チェック無視、payload競合無視、効果なし200応答。

## 障害と観測

before_sendはクライアント内の送信前失敗で、受信なしをtraceに記録。
before_applyは受付後、SQL更新前の接続shutdown。
after_apply_before_responseはcommitログの後、応答前に接続shutdown。
delayはcommit後の制御遅延。503_before/503_afterを別条件として扱う。
並行4要求はBarrierで送信開始を合わせ、SQLの原子性で二重適用を防ぐ。
server.jsonlはサーバー主体、trace.jsonlはクライアント／ハーネス主体。
monotonic_nsと連番を記録。再起動時はserver連番を既存行数から継続。

UNKNOWNはHTTP応答を得られない観測。明示的送信前失敗もbefore_send_failureとして別記する。
最終HTTPが不明または429/503なら保留。直接DBオラクルが件数を知っていてもクライアントUNKNOWNを解消しない。
SAFE_REPLAYは指定再送ケースのreplayed応答が根拠。重複・409・虚偽200・危険な別キー再送は別分類。
危険再送の診断は意図的欠陥を示すtraceイベントに依存し、未知クライアントの挙動を一般推論しない。

## 証拠と失敗

ケースresult: schema_version/scenario/mode/passed/checks/findings/effects/effect_count/expected値/http/retries/oracle/trace。
summary: 環境、全ケース結果、合計、合格数、終了コード。
子のstderrはファイル保存し、独立オラクルで非空なら不一致にする。
入力拒否はstdoutにINVALID_TESTとexit_code=2。出力先を作れない場合、既存先へは書かない。
例外の発生した試験はINVALID_TEST。通常終了・例外後は所有Popenをterminate/waitする。
親プロセス自体のSIGKILLやOS障害での回収・ログ耐久性は保証しない。
内部_serverは所有tokenが必要だが、悪意ある同一権限ユーザーへの隔離機構ではない。

## FIX-01契約

Retry-AfterはASCII数字のみの秒数、上限1秒。0と1は実際に待機し1回だけ再送する。
正規表現外、10桁超、上限超、負数、空文字、文字列、HTTP日付はHOLD_UNKNOWNで停止する。
HTTP日付の解釈や無制限待機は提供しない。429_validの--retry-afterで試験値を指定する。
traceのretry_after_decisionにはheader/requested_seconds/cap_seconds/decision/elapsed_secondsを記録する。
monotonicによる実測待機は指定秒以上であり、厳密なリアルタイム保証ではない。
正常な保留という期待結果の一致は終了0になり、業務成功を意味しない。

内部試験用--test-faultは固定列挙値だけを受け付ける。
spawn: 存在しない試験用Pythonを起動しOSエラーを発生。
port_init: 子内でloopbackポートを先に占有しbind失敗を発生。
child_crash: readiness出力後に子が17で終了。
check_timeout: 子の起動を30秒遅延し準備待ちを0.2秒で打切り回収。
output_write: 結果書込箇所でOSErrorを注入（実ディスク枯渇試験ではない）。
通常readiness期限5秒、回収terminate/wait5秒後に必要時kill/wait。
child_spawned、startup_response、child_reapedが所有PIDと回収根拠を残す。
起動・実行失敗はINVALID_TEST/exit_code=2。出力失敗はstdout JSON/終了2。
_serverの不正所有tokenと起動例外もJSON/2。既存出力先は排他的に拒否する。
既存先の不変は合成markerのSHA-256前後比較で確認。全ファイルシステムの不変保証ではない。

## 独立比較

benchmark/oss_baseline.pyは独自のHTTP server/client、SQLite receipts/applied、
unittest判定、子回収を実装する。arl/oracleをimportしないことをASTでも検査する。
compare.pyだけが両方式を呼出し、cases.jsonの共通期待契約と照合する。
measure_addition.pyは一時コピーに同一キー3要求の新ケースを実装し、差分と実行結果を保存する。
本体の23シナリオは変更しない。判定の独立性は実装分離であり、第三者執筆を意味しない。

## 制約

固定シナリオラボであり汎用Adapterではない。業務効果は追記、key保持は無期限。
同じoperation_idでも別keyなら別効果。分散環境のexactly-once保証ではない。
本番・外部API、TLS、キー期限、実ディスク障害、親SIGKILLの回収は対象外。
F04の6環境GitHub Actionsは設定のみ・全件未実施。公開判定HOLD。

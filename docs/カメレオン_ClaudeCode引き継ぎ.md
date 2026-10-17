# エボシカメレオン透明標本 Claude Code への引き継ぎ

- DATE: 2026-10-17
- 前の担当: Claude（Cowork。クラウドの Linux 環境で CT と膜を処理し、Mac の Blender は MCP から裏の `blender -b` を起動して書き出していた）
- この文書の役割: Claude Code が最初に読む文書。いまの状態、決まったこと、最初に片付けること、次の作業を書く
- 経緯の正: `docs/カメレオン透明標本_計画書_v1.0.md`（以下「計画書」）。決定の言葉と測った数は、計画書の記録が正。この文書の数は計画書から写した
- 最後のカメレオンのコミット: `1ea74f2`（2026-10-17、骨端を載っている骨へ移す）。この文書のコミットはその後

ゴールは、白いスタジオの瓶の液の中に、エボシカメレオン（*Chamaeleo calyptratus*）の透明骨格標本（骨はアリザリンの赤、軟骨はアルシアンの青）が頭を下にして浮かび、高いかぶと・上で渦を巻く尾・2 本ずつの束の足が見え、体の中まで透けて観察できる状態にすること（計画書 第 1・2 節）。イカ・シュモクザメと同じギャラリーに並べる。

---

## 1. 決まったこと

プロデューサーの言葉は計画書に書かれたまま写した。言葉が記録されていないものは「（言葉の記録なし）」と書いた。

| 日付 | 決めたこと | プロデューサーの言葉 | 計画書 |
|---|---|---|---|
| 10-12 | 頭骨は Digimorph の CT（TNHC 62768）の形をそのまま使う | （言葉の記録なし。「プロデューサー決定」とだけある） | 第 6 節 6.1 の後の「頭骨は CT の形をそのまま使う」 |
| 10-13 | 順番は A 透明標本（静止、瓶なし）→ B 動かす（瓶なし）→ C 瓶に入れる（後回し） | （言葉の記録なし。「プロデューサー決定」） | 6.0 の初め |
| 10-13 | 胸郭の肋骨の寝る角は 50° まで起こす（写真 06 で測った値） | （言葉の記録なし） | 6.1 の後の「修正 2」 |
| 10-13 | 皮膚・筋肉の膜（A2）を前倒しで作る | （言葉の記録なし） | 6.1 の後の「修正 2」 |
| 10-13 | 呼吸と心拍は、カメレオンの値が見つからないので近いトカゲの値を仮に使う | 「プロデューサー了承」 | 6.0 の「B の記録 1」 |
| 10-13 | 後肢の向きも、前肢と同じく写真 01 の関節の点で解き直す | 「後肢も同じ方法で」 | 6.0 の「C の記録 3」 |
| 10-13 | 写真 01 の色の型を足す。写真 06 の型は残す（`?stain=01`） | 「写真 01 の色のバージョンも作る。今のものは残す」 | 6.0 の「C の記録 4」 |
| 10-14 | トサカ・顎の下・肋骨・目・とげの直し方の方針 | 「修正方針を承認します。変更前に一度コミットして下さい」 | 6.0 の「C の記録 9」 |
| 10-15 | 舌骨の作り直し（胸の 5 本を外す、HYOID_EXTRA をやめる、舌内突起・基舌骨・角舌骨を軟骨で足す、膜を作り直す） | 「承認します」 | 6.0 の「C の記録 12」「記録 13」 |
| 10-15 | 舌骨の軟骨の濃さを写真 06 の喉の水色に合わせる | 「写真06の濃さに合わせる」 | 6.0 の「C の記録 15」 |
| 10-15 | 肘・膝のこぶの小さな骨は、直す前に正体を調べる | 「先に骨の正体を調べる」 | 6.0 の「C の記録 18」 |
| 10-15 | 膜と骨の距離が一定なのも検討する | 「膜と骨の距離が一定なのも実態と違うのではないでしょうか？それも検討に含めて」 | 6.0 の「C の記録 18」 |
| 10-17 | 骨端を、成長板で載っている骨へ移す（案 A）。膜の厚みを位置で変える案（B）は保留 | 「Aを進めて下さい」 | 6.0 の「C の記録 19」 |
| 10-17 | カメレオンの開発を Cowork から Claude Code へ移す | 「カメレオンの開発を、この会話（Cowork）から Claude Code に移します」 | （この文書） |

食い違いが 1 つある。計画書 6.0 の「A3 の記録」（10-13）は「のどの軟骨は置かない。軟骨の青は、肋骨の途切れの 22 本だけ」と書く。10-15 にプロデューサーが記録 12 の方針（舌内突起・基舌骨・角舌骨を軟骨で足す）を「承認します」とし、今の glb には舌骨の軟骨がある。CLAUDE.md の「言葉を正にし、決まりの文書を直してから進める」に従えば後の言葉が正だが、A3 の行はまだ直していない。直してよいかをプロデューサーに確かめる（第 4 節）。

---

## 2. いまの状態

段の名前は計画書 6.0。

| 段 | 状態 | 成果物 |
|---|---|---|
| A1 骨 | 済み。全身 CT（MorphoSource 000050726）の骨 72 本と、Digimorph の頭骨。胸郭は肋骨ごとに測って並べ直した（記録 8）。舌骨は第 1 角鰓骨の対だけ（記録 12・13）。骨端の持ち主を直した（記録 19） | `blender/private/chameleon_body_ct.npz`、`docs/chameleon_ct_body/` の図 |
| A2 膜 | 済み（`skinbody.py` の 7 版）。骨から作り、CT の軟部は尾の肉の厚みだけに使う。頭と胴は別に作って後頭部でつなぐ。穴 0、骨のはみ出し最大 0.27 mm（尾椎 v36）。手足は区間ごとに一定の厚み（上腕 1.30・前腕 0.97・手 0.73・大腿 1.59・下腿 1.31・足 1.12 mm）で、位置で変える案 B は保留 | `blender/private/chameleon_body_soft.npz`（`soft__`） |
| A3 軟骨 | 途中。肋骨の途切れと、肋骨の腹の端の軟骨（`cart__`）、舌骨の軟骨（臓器 `hyoid_cartilage`）は済み。胸骨は CT で位置が分からず未 | `cart__`、`org_hyoid_cartilage__` |
| A4 眼と内臓 | 済み（眼球とレンズの球、体腔の臓器 12 個）。眼の色素・腹膜の色素は未 | `org_*`（`organs.py`、`eyes_mesh.py`） |
| A5 染まり | 済み。色の型 "06"（写真 06）と "01"（写真 01）。10-15 に今の膜で当て直した（記録 14・16） | `水槽/scenes/specimen/src/chameleon-stain.js`、テスト `tests/chameleon-stain.mjs` |
| A6 生々しさ | 未着手 | |
| A の出口 | 未。プロデューサーが「透明標本に見える」と判断した記録はない | |
| B1 展示の姿勢 | 済み（`rig_chameleon_ct.py` の `POSE_JAR`、写真 01 で測った） | `blender/rig_chameleon_ct.py` |
| B2 遅いループ `CH_Hover` | 途中。尾・手足・頭は済み。呼吸（肋骨を回す）と心拍は仮の値で付けた（B の記録 1） | `rig_chameleon_ct.py` |
| B3 内臓の時計 | 途中。心臓の拍は臓器 heart で（`chameleon-material.js`）。B の出口（Blender の動画）は未 | |
| C 瓶 | 途中。`index.html?specimen=chameleon` で瓶に載る（記録 1）。瓶の書き出し・液の濃さ・映り込み・ラベル（外してある）は未 | `水槽/scenes/specimen/src/specimen-chameleon.js` |

いまの glb（`水槽/scenes/specimen/assets/private/specimen_chameleon.glb`、21.2 MB、10-17 に書き出し）の中身: 骨 113 本、膜、軟骨（肋骨）、臓器 17 個（体腔の 12 個、眼球とレンズ 4 個、舌骨の軟骨）、`CH_Hover`。

---

## 3. 最初に片付けること

どれも描写を変えない作業。

### 3.1 環境

1. `.venv` を作る（CLAUDE.md のコマンド）。カメレオンの処理には、CLAUDE.md の一覧のほかに `pyfqmr`（膜・臓器の面を減らす）と `networkx`（`hyoid2.py` など古い段）が要る。標本ページを撮る道具は `playwright`
2. Blender の裏の書き出しが動くか確かめる: `cd ~/transparent-aquarium/transparent-aquarium && /Applications/Blender.app/Contents/MacOS/Blender -b -P blender/export_chameleon_gltf.py -- 水槽/scenes/specimen/assets/private/specimen_chameleon.glb`。前の担当は、開いている Blender の Python から `subprocess` でこれを起動していた。出力の最後に `[Chameleon glb] … 21.2 MB` と出る
3. git のコミットも、前の担当は Blender の Python から `subprocess` で行っていた（Cowork の Linux 側からは .git のロックを消せないため）。Claude Code では普通に `git` を使えばよい

### 3.2 作業フォルダ

CT 処理のスクリプトは、すべてカレントフォルダの相対パスで読み書きする（例: `np.load('pose_jar.npz')`）。前の担当はクラウドの作業フォルダ（第 8 節）で、全部の中間ファイルを 1 つのフォルダに置いて回していた。

1. `blender/private/` の下に作業フォルダを作る（例: `blender/private/work/`。`blender/private/` は `.gitignore` 済み。新しく `.gitignore` を変えるときは共通のファイルなので先に聞く）
2. `blender/private/cowork_work_2026-10-17/` の中身と、`blender/private/` の `chameleon_body_ct.npz`・`ct_ms50726_vol4.npz`・`ct_ms50726_vol4max.npz`・`ribtracks2.npz`・`chameleon_body_ct_v1_ribs.npz` を写す
3. 圧縮して運んだものを、スクリプトが読む名前に戻す: `soft2_mask.npz`（キー `m`）→ `soft2_mask.npy`、`intruder.npz`（`m`）→ `intruder.npy`、`B_final_labels.npz`（`B`）→ `B.npy`、`W2.0.npz`・`Mc.npz`・`M.npz`・`vertLf.npz`・`cavity_half.npz`・`organs_lung.npz`・`soft_solid_half.npz`（どれもキー `a`）→ 同じ名前の `.npy`
4. スクリプト（`blender/ct_body_pipeline/*.py`）を作業フォルダから実行する（`cd blender/private/work && python ../../ct_body_pipeline/skinbody.py`）

### 3.3 膜から glb までを、今の骨から作り直して比べる

第 7 節のとおり、骨のメッシュより後ろ（膜・臓器・書き出し）は今のファイルからもう一度回せる。最初に 1 回回して、今の glb と比べる。

1. 作業フォルダで `bash ../../ct_body_pipeline/run_skin_organs.sh`（skinbody.py → organs_cav.py → organs.py → organs_mesh.py → eyes_mesh.py → hyoidcart_mesh.py → pack_soft.py。skinbody はクラウドで約 5 分）。`run_skin_organs.sh` は自分のフォルダへ `cd` する作りなので、作業フォルダへ写してから実行するか、`cd` の行を外す
2. 検査: `diag_inside.py`（穴）→ `diag_bones.py`（骨のはみ出し）→ `chk_cart.py`（軟骨）→ `chk_soft.py`（臓器）→ `diag_excess.py skin_posed.npz 1.5 out.png`（骨から 1.5 mm より外の膜の面積）。10-17 の値: 穴 0、はみ出し最大 0.27 mm（v36）、軟骨・臓器 0%（`soft` の行の約 52% は膜そのものなので見ない）、骨から 1.5 mm より外の膜 右から 105 mm²・上から 44 mm²・前から 8.5 mm²
3. `pack_soft.py` が出した `chameleon_body_soft.npz` を `blender/private/` に置き、`blender/private/chameleon_body_ct_dec.npz`（骨を間引いた控え。骨が変わったら消すか別名にする）を確かめてから書き出す
4. 標本ページを第 9 節の引数で撮り、`docs/chameleon_ct_body/epiphysis_fix.png` などの今の図と並べる

### 3.4 標本ページを撮る道具を Mac で動くようにする

前の担当の道具は `blender/ct_body_pipeline/page_check/`（第 9 節）。クラウドの Chromium（`/opt/pw-browsers/chromium`、SwiftShader）と、`page_check/w/` に置いた `水槽` の写し（ポート 8099）を前提にしている。Mac では `npm start`（ポート 8080）と、`tools/record-specimen/` と同じ Chrome（`CHROME_CHANNEL`）に直す。

---

## 4. まだ決まっていないこと、プロデューサーに確かめること

決める前に、どれも案ごとの絵を並べて見せる（CLAUDE.md）。

| 項目 | 背景 | いつ |
|---|---|---|
| 手足の膜の厚みを、骨に沿った位置で変える案 B | 記録 18。CT の軟部では肘・膝の端が 0.3〜0.5 mm、大腿の中ほどが 2〜2.5 mm だが、左右の差が大きく（CT の個体は丸まり手足が体に触れる）、数は 1 体の CT か写真 06 の前腕 1 本から取ることになる | 次の形の作業の前 |
| 計画書 A3 の「のどの軟骨は置かない」（10-13）を、10-15 の承認に合わせて直してよいか | 第 1 節の最後 | 最初に |
| A の出口（「透明標本に見える」か） | 判断の記録がない | A を締める前 |
| 第 2 角鰓骨を足すか | 文献が食い違う（Herrel et al. 2009 は無い、Meyers & Nishikawa 2000 と chameleons.info の図には CBII）。CT に 2 対目の棒は無いので足していない（記録 12） | 舌骨を触るとき |
| 写真 06 の喉の水色の場所 | 写真 06 では下あごの後ろ・首の下の斑で、画面の舌の芯は下あごに沿う。濃さだけ合わせた（記録 15）。斑が角鰓骨の先の軟骨か喉頭の軟骨かは出典が無い | 喉を触るとき |
| 色はどちらの型を正にするか（06 か 01） | 記録 1・4。ギャラリーの瓶は `?stain=01` を付けないと "06" | C の前 |
| 呼吸・心拍の仮の値 | 近いトカゲの値（呼吸 10 回/分、心拍 40 回/分）を仮に使っている（B の記録 1） | B を締める前 |
| 計画書 6.0 の最後の「決めること: 染まりを描く場所（案 1・案 2）」 | 実際は案 1（標本ページに glb を載せる）で進んでいる。この項を消してよいか | 最初に |
| 瓶（C）の残り: 瓶の書き出し、液の濃さ（瓶の倍率 J ≈ 3.8 の分）、映り込み、ラベル（外した） | 記録 1・7 | C の前 |
| 眼の色素、腹膜の色素 | 計画書 6.0 の「まだ」 | A4 の残り |
| 膜の残りの塊: 尾の付け根の下（約 31 mm²、総排泄腔のあたり）、喉の横・首の下（約 23 mm²） | 記録 11・13。生体の喉袋や総排泄腔の組織と読んで残している | 膜を触るとき |
| 手首・足首の小さな骨（骨端か手根骨・足根骨か） | 記録 19 で動かさなかった。足根の近位 3 要素は 1 つに癒合する（Diaz & Trainor 2015） | 手足を触るとき |

---

## 5. 次の作業

1. 第 3 節を終える（環境、作業フォルダ、膜から glb までの作り直しと比べ、ページを撮る道具）
2. CLAUDE.md（コミット `cf49744`）の「Claude Code での最初の作業」: `docs/標本づくりの元データと手法_振り返り_v1.0.md` 第 9 節の点検（いまの部品を「何を元に作ったか」で見直し、外形を参考と重ねた図を見せる。直すかはプロデューサーが決める）。この文書の第 2 節（いまの状態）と、計画書の記録 8・18（外形と膜の厚みの根拠）を使う
3. 第 4 節の「最初に」の 2 項をプロデューサーに聞き、計画書を直す
4. 案 B（手足の膜の厚み）をプロデューサーに聞く。進めるなら、記録 18 の数（`limb_soft_profile_ct.png`、`photo06_forearm_tissue.png`）を表にし、使う数の出どころを計画書に書いてから `skinbody.py` の `LIMB_T` を位置の関数にする
5. A6 生々しさ、A の出口
6. B の出口（Blender の動画）、C の残り

---

## 6. 元データと中間ファイル

### 6.1 元データ（リポジトリの外、Mac にある）

| ファイル | 場所 | 使い方 |
|---|---|---|
| 全身 CT の JPEG 断面 4287 枚（`Chamaeleo-calyptratus-000050726.zip`） | `~/transparent-aquarium/画像サンプル収集/エボシカメレオン/morphosource_media-id-000050726_download-c86f5ae0/` | 頭以外の骨。商用不可・再配布しない（`docs/references/chameleon/SOURCES.md`） |
| 頭骨の STL（Digimorph TNHC 62768） | `~/transparent-aquarium/画像サンプル収集/エボシカメレオン/Chamaeleo.stl` | 頭骨（`blender/build_chameleon_skull_from_ct.py`） |
| 参考写真 01〜10 | `docs/references/chameleon/`（`SOURCES.md`） | 01 は透かし入りで git に入れない。05・06 は CC BY-SA 4.0（Brianwray26、Wikimedia Commons） |

### 6.2 `blender/private/` の各ファイル

「作ったもの」は、計画書・README とスクリプトの入出力から読んだ。

| ファイル | 作ったもの | 中身 |
|---|---|---|
| `ct_ms50726_vol4.npz` | その場のコマンド（残っていない）。断面を 4 枚に 1 枚、面内 4×4 の平均 | 体積（0.104 mm） |
| `ct_ms50726_vol4max.npz` | `ct_body_pipeline/ds2_vol4max.py`（README では `ds2.py`。出力名は `vol4max.npz` で、名前を変えて置いた） | 細い肋骨用の体積 |
| `chameleon_body_labels.npz` | 10-12 の版（`final_labels.py` 以後のどこか）。新しい版は `cowork_work_2026-10-17/chameleon_body_labels_cloud.npz`（10-13） | 骨のラベルの体積 |
| `ribtracks2.npz` | `ribtrack2.py` | 肋骨の中心線（`ribrestore.py` が読む） |
| `chameleon_body_ct_v1_ribs.npz` | `finish.sh`（10-13 の骨。肋骨は CT の形） | `ribdepth.py` → `ribmodel2.py` の入力 |
| `chameleon_body_ct.npz` | `finish.sh` → `ribdepth.py`（`ribmodel2.py`、`hyoid_relabel.py`、`ribbottom.py`）→ `strip_strays.py` → `hyoid_rebuild.py` → `epiphysis_relabel.py`（README 32・45〜57） | いまの骨・軟骨・骨組みのデータ。Blender の `generate_chameleon_ct_body.py` が読む |
| `chameleon_body_ct_dec.npz` | `generate_chameleon_ct_body.py`（骨を間引いた控え。無ければ作る） | 骨が変わったら消すか別名にする。古い控えが残ると古い骨で書き出す |
| `chameleon_body_soft.npz` | `pack_soft.py`（膜 `soft__`、臓器 `org_*`） | Blender が読む |
| `chameleon_skull_ct.npz`、`_dec.npz` | `build_chameleon_skull_from_ct.py`（10-12、頭骨だけの時期） | いまの書き出しでは使っていない |
| `joints.json`、`joints_v1.json` | `joints.py`、手直し（README 10・20） | 四肢の関節 |
| `lat_head.png`、`lat_spine.png`、`lat_thick_bone.*`、`lat_thick_grid.npy` | 10-12 の初めの横からの測り。作ったスクリプトはリポジトリに無い | いまは使っていない |
| `pose_mac_h12b.npz` | `dump_pose.py`（10-15、Mac の Blender） | 展示の姿勢の骨の行列。クラウドの `pose_jar.npz` との差 4.8e-6 を確かめた |
| `tmp/before_fix9/` | 記録 9 の直す前の控え | |
| `tmp/` のほか | 10-14 の作業の控え（`pose_jar_v4_*.npz` など） | |
| `old_v11/` | 10-15〜17 に置き換えた前の版（`_h12`・`_h12a`・`_h12b` は舌骨と骨端の直しの前） | |
| `cowork_work_2026-10-17/` | 10-17 にクラウドの作業フォルダから写した（第 6.3 節） | |
| `cowork_scripts_2026-10-17.tar.gz` | クラウドの作業フォルダの `.py`・`.sh` 全部（231 本。一回きりの診断や図のスクリプトを含む） | リポジトリに無いスクリプトを探すとき |

### 6.3 `blender/private/cowork_work_2026-10-17/`（10-17 にコピー、md5 は送る前と同じことを確かめた）

| ファイル | 作ったもの | 使うスクリプト |
|---|---|---|
| `B_final_labels.npz`（キー `B`） | `finish.sh` に最後に渡した骨のラベル（`B.npy`） | `bonemesh.py` |
| `chameleon_body_labels_cloud.npz` | 10-13 のラベル（`B.npy` と 0.1% 違う。どちらが B_h11 かは確かめていない） | |
| `M.npz`、`Mc.npz`、`W2.0.npz`、`vertLf.npz` | README 1・2・4・9 | `thick.py`、`seg.py`、`joints.py`、`final_labels.py` |
| `intruder.npz`（キー `m`） | `final_labels.py`（別の個体の骨） | `hyoidfix.py`、`softmesh.py` |
| `axis5.npy`、`axis5_s.npy`、`axis5_t.npy`、`frame_D.npy`、`J.npy` | `axis5.py`、`prof.py`、`straight.py`、その場のコマンド（J） | `ribrestore.py`、`rig_data.py`、`organs*.py` |
| `bones_raw.npz`、`rig.npz` | `bonemesh.py`、`rig_data.py` | `finish.sh` の統合 |
| `bone_names.json`、`sides.json`、`joints.json` | | `bonemesh.py` ほか（同じものが `ct_body_pipeline/` にもある） |
| `cart_gaps.json`、`rib_pts.pkl`、`cart_pts.pkl`、`ribmodel2.json`、`dv_override.json`、`dv_override_v1.json`、`girdle_ventral.json`、`ribbottom.json`、`strays.json` | `cartgaps.py`、`ribmodel2.py`、`ribdepth.py`、`girdle_ventral.py`、`ribbottom.py`、`strip_strays.py` | 胸郭の作り直し（README 45・46・49・50） |
| `hyoid_pose.json` | `hyoid_pose.py`（もう使っていない HYOID_EXTRA の元） | |
| `ento_line.npy`、`skull_frame_ct.npy`、`hyoid_rebuild.json` | `entotrace.py`、`skull_frame.py`、`hyoid_rebuild.py` | `hyoid_rebuild.py` |
| `epiphysis_relabel.json` | `epiphysis_relabel.py` | |
| `pose_jar.npz` | `dump_pose.py` の出力を、舌骨の行列を頭と同じにして直したもの（10-15。Mac の `dump_pose.py` の出力と一致） | `skinbody.py`、`organs*.py`、`eyes*.py`、`ribmodel2.py` |
| `eyes.json` | `eyes.py` | `skinbody.py`、`eyes_mesh.py` |
| `soft2_vol.npz`、`soft2_mask.npz`（キー `m`）、`soft_solid_half.npz` | `softvol2.py`、`softmesh.py` | `skinbody.py`（尾の肉）、`limb_thick.py` |
| `skin_posed.npz`、`soft_rigged.npz`、`skinbody_tables.npz` | `skinbody.py` | `organs_cav.py`、`pack_soft.py`、診断 |
| `organs_cav.npz`、`organs_lab.npz`、`organs_rigged.npz`、`organs_lung.npz`、`cavity_half.npz` | `organs_cav.py`、`organs.py`、`organs_mesh.py`＋`eyes_mesh.py`＋`hyoidcart_mesh.py`、`visceramesh.py` | `pack_soft.py`、`ribmodel2.py`（`organs_cav.npz`） |
| `viscera_rigged.npz` | `visceramesh.py`（内臓の一塊。書き出していない） | `pack_soft.py`（`PACK_VISCERA` を付けたときだけ） |
| `diag_inside.npz` | `diag_inside.py` | `ribbottom.py`、`girdle_ventral.py` |

### 6.4 リポジトリに足したもの（10-17）

- `blender/ct_body_pipeline/run_skin_organs.sh`: 膜から臓器まで（3.3）
- `blender/ct_body_pipeline/page_check/`: 標本ページを撮る・測る道具（第 9 節）

---

## 7. 最初から通しで作り直せるか

できない。切れ目は次のとおり。

| 切れ目 | 中身 |
|---|---|
| 残っていないコマンド | `vol4.npz`、`M.npy`（README 1）、`J.npy`（README 8）を作ったコマンドが残っていない。`M`・`J` の結果は 6.3 にある |
| 手で選んだ番号 | `final_labels.py` は、頭・四肢の塊の番号を画像を見て手で選んだ（`W2.0` の実行に固有）。`W2.0` を作り直すと番号が変わる |
| 輪になった依存 | `ribmodel2.py` が `organs_cav.npz`（膜から作る）と `pose_jar.npz`（Blender の骨組みから作る）を読む。膜は骨から作る。前の担当は、前の回の膜と姿勢を使って骨を作り、その骨で膜を作り直した。1 回で通る順番は無い |
| 回数を重ねた段 | `ribdepth.py` は `ribmodel2.py` → `hyoid_relabel.py` → `ribbottom.py` を 6 回回して肋骨の深さを X 線に合わせた（README 46）。`ribdepth.py` の中の値（`RIB_SLOPES=0.57,-1.3,0.54`、`RIB_CART_TIP=1.2`）は残っている |
| 古い段のスクリプトが入れ替わった | `hyoid5.py`・`hyoid_relabel.py` で舌骨に入れた棒は、`hyoid_rebuild.py` で外した（記録 12・13）。通しで回すなら、後の段で前の段の結果を消す作りのまま回すことになる |
| パス | どのスクリプトもカレントフォルダの相対パスで読み書きする |

通しで回せるのは、`chameleon_body_ct.npz` から後ろ（膜・臓器・書き出し）だけ（3.3）。骨を作り直すときは、今の `chameleon_body_ct.npz` を出発点にして、変える段だけを回す（記録 12〜19 はこのやり方）。

---

## 8. 前の担当の環境にだけあって、Mac に無いもの

前の担当のクラウドの作業フォルダ（`/tmp/claude-0/-home-claude/1d1858a9-9367-5399-8183-e4b2d1185ae5/scratchpad/`、作業の中心は `r/ms/` と `web/`）は、会話が終わると消える。Cowork の Linux 仮想環境（`~/mnt/transparent-aquarium/...`）は Mac のこのフォルダそのものを開いていたので、そこで書いたファイルは Mac にある。仮想環境の `/tmp` には一時の文字のファイルだけを置いた。Mac の `/tmp` には、Blender から書いた控え（`dump_pose_h12.py`、`pose_mac_h12.npz`、`pose_mac_h12b.npz`、`x.glb`）がある。要るのは `pose_mac_h12b.npz` だけで、`blender/private/` に写した。

- コピーしたもの: 第 6.3 節の 46 ファイル（49 MB）、スクリプトの tar（`cowork_scripts_2026-10-17.tar.gz`）、`page_check/` の 9 本と `run_skin_organs.sh`
- 移さなかったもの:
  - 途中の段のラベルの体積（`B_r4`〜`B_h11` の各段）。もう残っていない（上書きされた）
  - 作り直せる体積: `D2.npy`、`m2.npy`、`W1.5.npy`、`lab.npy`（766 MB）、`seg15/20.npz`、`vertL.npy`・`vertL2.npy` など
  - 古い版の中間ファイル（`chameleon_body_ct_ribs2〜7.npz`、`skin_posed_v2〜v12.npz`、`organs_*_loft3.npz` など）
  - 確認のために描いた画像（数百枚）。計画書に載せた図は `docs/chameleon_ct_body/` にコミット済み
  - 標本ページを撮った画像と、色の当てはめに使った画面の書き出し（`p01_v12.npy`、`cal01_v12.npz`、`cal06_hc.npz`、`p06_v12.npy` など）。第 9 節の道具で取り直せる
  - クラウドに写した `水槽` の一式（`web/w/`）。カメレオンのページのファイルはリポジトリと同じ（10-15 に md5 で確かめた）

---

## 9. 標本ページの確かめ方

1. `cd 水槽 && npm start` のあと、http://127.0.0.1:8080/scenes/specimen/chameleon.html（瓶なし、ライトボックス）
2. glb は `水槽/scenes/specimen/assets/private/specimen_chameleon.glb`（git に入らない）。書き出し直したら、ブラウザのキャッシュを消して読み直す

`chameleon.html` の引数（`src/chameleon-main.js`）:

| 引数 | 意味 |
|---|---|
| `?stain=01` | 色の型 "01"（写真 01）。付けなければ "06"（写真 06） |
| `?view=photo06` | 写真 06 と同じ向き（頭が右、背が上） |
| `?still=1` | 止める |
| `?t=<秒>` | `CH_Hover` のその時刻で始める |
| `?ss=<n>` | 通り道を描く細かさ（既定 2）。ちらつきの較正用 |

瓶のページ: `index.html?specimen=chameleon`（`&stain=01` も使える）。

ページの中の道具（`window.chameleonPage`）:

- `look`: 効果の強さ（`skin`、`film`、`organs`、`viscera` など）。0 にした画面と比べる
- `paths()`、`film()`、`organ()`: 組織ごとの通り道の画像（浮動小数）。色の当てはめはこれを読む
- `organs`: 臓器ごとの吸光度の uniform。`calibrateOrgans.on = true` で、色の型が臓器を描かないときも臓器の通り道を描く

`blender/ct_body_pipeline/page_check/` の道具（クラウドの Chromium 向け。3.4 で Mac 用に直す）:

| ファイル | すること |
|---|---|
| `serve_run.sh` | `page_check/w/` を 8099 で配信し、引数のコマンドを走らせる |
| `shot.py <URL> <出力.png> <待つ秒>` | 1 枚撮る |
| `shot0.py` | 舌骨の軟骨の吸光度を 0 にして撮る（下地を測るため） |
| `lbrot.py <URL> <接頭辞>` | 正面・90°・180° を撮る |
| `bones.py <URL> <接頭辞>` | 膜・膜の層・臓器を 0 にして骨だけで撮る |
| `paths3.py <URL> <出力.npy>` | `paths()` と `film()` を保存 |
| `organcal.py <URL> <出力.npz>` | 臓器ごとの通り道を保存（色の当てはめ用） |
| `lm.py`、`lm2.py <URL>` | 骨の点の画面の位置（`lm2.py` は首の椎骨） |

色の当てはめのスクリプト（`fit_stain01.py`、`fit_organs01.py`、`fit_eyes01.py`、`fit_skin06.py`、`fit_hyoidcart06.py`）は、これらの出力と写真を読む。使い方は各スクリプトの先頭の注。

テスト: `cd 水槽 && npm test`（`tests/chameleon-stain.mjs` が色の型の数を確かめる。色の数を変えたらテストの行も変える）。

---

## 10. 作っている中で分かった落とし穴

手順書（`docs/動く透明標本_最短開発手順_v1.0.md`）の表で見つからなかったものを書く。計画書の記録には書いてある。

- **CT のラベルの誤りは、展示の姿勢にして初めて見える**: 関節の向こうの骨のラベルに入った骨端（記録 19）や、舌骨と思った胸の棒（実は腹側の肋骨、記録 12・13）は、静止の CT では正しい位置にあるので、膜を作って骨組みで動かしたときに「こぶ」「骨が飛び出す」として出る。名前の付いた骨でも、主の骨以外の連結成分を 1 つずつ見て、触れている面の広さで持ち主を確かめる
- **頭の膜の切り取りに入れる部品**: 頭の膜は頭骨・眼球の横・上・前の像の外へ出さない作り（`skinbody.py`）。頭について動く部品（舌骨の骨と軟骨）をこの像に入れないと、膜の外へ出る（舌の芯の 47% が出た、記録 13）
- **`rig_chameleon_ct.py` の FOLLOW_HEAD の順番**: 骨の位置を親から順につなぐとき、親が頸の骨の舌骨は頭骨より先に来て、頭骨から約 4 mm ずれていた（10-15 に直した）。骨組みを変えたら `dump_pose.py` の行列で、頭について動く骨が頭骨と同じ行列か確かめる
- **`pose_jar.npz` と Blender の骨組みは別々に持たれている**: 膜・臓器は `pose_jar.npz`（`dump_pose.py` の出力）で作り、glb は Blender の骨組みで動く。片方だけ変えると膜と骨がずれる。変えたら両方の行列を比べる（10-15 の差 4.8e-6）
- **骨を変えたら `chameleon_body_ct_dec.npz` を消す**: Blender の生成スクリプトは、この控えがあると読み直さない
- **画面の書き出しの大きさが変わる**: `paths()` は 800×956 のときと 1600×1912 のときがあった（10-15）。画面の点（`lm.py` は 800×956）と合わせるときは 2×2 の平均で縮める（`fit_organs01.py` の注）
- **色の当てはめは場所でなく割合でそろえている**: 写真 01 と画面は胴の曲がりが違うので、色の組の画素の割合で対応させている（`fit_stain01.py`）。膜や臓器を変えたら当て直す。前の値が同じ手順で再現できることを先に確かめる（10-15 は 4 桁まで再現）
- **臓器の吸光度の uniform は、色の型に無い臓器では前の値のまま残る**: `chameleon-material.js` は色の型に書いた臓器だけ値を入れる。同じページで型を切り替える作りにするなら、全部の臓器を毎回入れ直す
- **舌骨の軟骨は臓器として描く**: 肋骨の軟骨と別の強さにするため（記録 15）。`generate_chameleon_ct_body.py` は骨 `hyoid` の軟骨を `CH_Cartilage` に入れない。膜の作り（`skinbody.py`）は `cart__` のまま使う
- **別の個体が CT に写っている**: 同じ断面に、もう 1 体の後肢と指がある（`intruder.npy`）。舌骨のラベルに爪が入っていた（A3 の記録）
- **CT の軟部は手足の厚みに使えない**: この個体は丸まり、手足の骨の多くは体のほかの部分から 3 mm 以内にある。軟部の厚みを測ると体の組織が混ざり、左右で大きく違う（記録 18）
- **膜の検査は 2 方向**: 「骨が膜の外へ出ていないか」（`diag_bones.py`）だけでなく、「骨の無い所に膜を張っていないか」（`diag_excess.py`）も見る（記録 11。前の担当はこれを見落として指摘を受けた）

---

## 11. 参照

| 何 | 場所 |
|---|---|
| 計画書（決定と記録） | `docs/カメレオン透明標本_計画書_v1.0.md`（記録 9〜19 は 6.0 の「C の記録」） |
| CT 処理の実行順 | `blender/ct_body_pipeline/README.md`（番号の順でなく、行の並びと各行の注に従う。32 の `finish.sh` は 29〜36 の後） |
| 出典 | `docs/references/chameleon/SOURCES.md` |
| 確認の図 | `docs/chameleon_ct_body/` |
| Blender | `blender/generate_chameleon_ct_body.py`（骨・膜・軟骨・臓器を作る）、`blender/rig_chameleon_ct.py`（骨組み・展示の姿勢・CH_Hover）、`blender/export_chameleon_gltf.py`（glb） |
| ページ | `水槽/scenes/specimen/chameleon.html`、`src/chameleon-main.js`、`chameleon-material.js`、`chameleon-stain.js`、瓶は `specimen-chameleon.js` |
| 前の引き継ぎ（10-12、Claude デスクトップへ） | `docs/カメレオン透明標本_引き継ぎ_2026-10-12.md`（古い。頭骨だけの時期） |

---

## 12. CLAUDE.md への直し

CLAUDE.md は編集していない。「エボシカメレオン」の節（`cf49744` の版）について、直すとよい所を書く。

1. 「ページ」の行に、URL の引数が無い（シュモクザメの節にはある）。`?stain=01`（写真 01 の色）、`?view=photo06`（写真 06 の向き）、`?still=1`、`?t=<秒>`、`?ss=<n>`、瓶は `index.html?specimen=chameleon` を足す
2. 「ページ」の `src/chameleon-*.js` に、瓶の `src/specimen-chameleon.js` が入らない
3. 「CT 処理」の行に、作業のやり方が無い。スクリプトはカレントフォルダの相対パスで読み書きするので、`blender/private/` の下の作業フォルダで回すこと、中間ファイルは `blender/private/cowork_work_2026-10-17/`、膜から臓器までは `run_skin_organs.sh`、書き出しは `blender -b -P blender/export_chameleon_gltf.py -- 水槽/scenes/specimen/assets/private/specimen_chameleon.glb`、骨を変えたら `chameleon_body_ct_dec.npz` を消すこと、を足す
4. 「元データ」の行が無い。全身 CT の zip と頭骨の STL は `~/transparent-aquarium/画像サンプル収集/エボシカメレオン/`（リポジトリの外）
5. 「権利」の行で、写真 05・06 は CC BY-SA 4.0（Brianwray26）なので、使った図には出典の表示が要る。透かし入りで git に入れないのは写真 01 など（`SOURCES.md`）
6. 共通の「コマンド」の CT の Python の一覧に、カメレオンで使う `pyfqmr`、`networkx`、`playwright` が無い
7. README の「最初から通しで作り直す確認はまだ」は正しいが、切れ目（第 7 節）は輪になった依存を含むので、「通しで作り直す」でなく「今の `chameleon_body_ct.npz` から変える段だけ回す」が今のやり方であることを書くとよい

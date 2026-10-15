# シロシュモクザメ CT → 骨格（ZMA.PISC.108725）

データ: Kamminga et al. 2017（figshare, CC0）。元の zip は `~/transparent-aquarium/シュモクザメ/全身CT/`。
中間ファイル（数百 MB〜1 GB）はリポジトリに入れず、`work/` に置く（git に入れない）。面（PLY）は `mesh/`。
置き場はすべて `hh_paths.py` で決める。どのスクリプトも先頭でそこから読み、カレントフォルダには頼らない。

## 通して作る

```bash
blender/ct_hammerhead/run_all.sh <出力のフォルダ>   # zip から glb まで。いまの work/・mesh/・glb には書かない
blender/ct_hammerhead/run_all.sh --default          # いつもの置き場に上書き
```

`FIGS=1` で確認の図も作る。`FROM=<スクリプト名>` でその段から始める。

## 段ごとの検算

```bash
blender/ct_hammerhead/check_stage.sh <スクリプト> [引数]
```

`work/`・`mesh/` の元のファイルを入力に 1 つの段を走らせ（`rebuild/check/` の APFS の複製の中で。元には書かない）、書いたファイルを `compare_work.py` で元と比べる。glb は `compare_glb.py <元> <新>`。

## 実行順


| 順 | スクリプト | 内容 |
|---|---|---|
| 1 | a1_load_clean.py | DICOM を読む。撮影台とシートを外した体の体積（zyg_clean.npy） |
| 2 | a2_skeleton.py | 骨格の塊分け、背骨の中心線、椎骨の境目 |
| 3 | a2b_split_head_spine.py | 頭と背骨を分ける |
| 3b | a2d_comps_info.py | 塊ごとの断面の範囲の表 → comps_info.json（2026-10-15 書き起こし） |
| 4 | a2c_roll.py | 体の横倒し（背の向き）を神経弓で測る |
| 5 | a3_unroll_preview.py | 神経弓の倒れで体を起こした試し（旧。6 で置き換え） |
| 6 | a3b_sym_tilt.py | 倒れを断面の左右対称で測り直し、体を起こした体積を作る |
| 6b | a3c0_pect_split.py | 肩帯と胸びれの塊 833 を起こした座標に移し、左右に分ける → c833_uvz.npy・c833_split.npy・pect_info.json（2026-10-15 に計画書の文章から書き起こし。前の work/ と一致） |
| 7 | a3c_pectoral_options.py | 左右対称の向きの案を図にする → pect_options.png |
| 8 | a3d_pectoral_pose.py（2026-10-14 に 20 の後でやり直し） | 決定した向き（後ろへ35°・下へ15°）で左右の胸びれを置き、肩帯の右半分を鏡映して左右をそろえる → pect_posed.npz・pect_posed.json・pect_posed.png |
| 9 | a3e0_pelvic_look.py | 腹びれの所の塊を起こした座標に移す（pelvic_uvz.npz）。確認図 pelvic_look.png |
| 10 | a3e_pelvic_options.py | 腹びれの向きの案（右を使う／左を使う × 3 通り）→ pelvic_options.png・pelvic_info.json |
| 11 | a3f_pelvic_pose.py | 決定した腹びれの姿勢（右を使う・後ろへ60°・下へ20°、左は鏡映）→ pelvic_posed.npz・pelvic_posed.json・pelvic_posed.png |
| 12 | a3g0_tail_look.py | 尾を、背骨を一直線にせずに起こして見る → tail_look.png |
| 13 | a3g_tail_upturn.py ／ a3g_tail_upturn_fig.py | 700 mm より後ろは背骨の背腹のずれを残して起こす → derolled3.npy・tail_upturn.json・tail_upturn.png |
| 14 | a3h_tail_options.py | 尾の反りの角度の案（CT のまま／15°／20°）→ tail_options.png |
| 15 | a3i_tail_bend.py | 決定した尾の反り（約20°）を入れる → derolled4.npy・tail_bend.json |
| 16 | a3j_body_fig.py | A3 の決定をすべて入れた全身の確認図 → body_a3.png |
| 17 | a3k0_head_midline.py | 頭の正中線を、上から見た外形の鏡映で探す |
| 18 | a3k_head_yaw.py | 頭の横向き（約11°）を胴にそろえる → derolled5.npy |
| 19 | a3l0_neck_roll_measure.py | 頭〜胸（150〜330 mm）の倒れの残りを断面の左右対称で測る → neck_roll2.json |
| 20 | a3l_neck_roll_fix.py | 倒れの残り（最大16°）を戻す → derolled6.npy・c833_uvz_r.npy。このあと a3d と a3j をやり直す |
| 21 | a3m_head_options.py | 頭の翼の左右差の案 → head_options.png |
| 22 | a3n_head_mirror.py | 決定した頭の翼（画面の右の半分を左右に使う）→ derolled7.npy。このあと a3j をやり直す |
| 23 | a3o_comps_look.py ／ a3o_comps_xsec.py | 名前のない塊を描き、断面で確かめる → comps_head.png・comps_trunk.png・comps_xsec.png。扱いの表は docs/hammerhead_ct/comps_names.json |
| 24 | a4a_photo_top_cmp.py | 背中からの外形を NOAA の写真（パブリックドメイン）と重ねる → photo_top_cmp.png・photo_top_cmp.json |
| 25 | a4b_trunk_options.py | 体の膜の胴の幅の案 → trunk_options.png |
| 26 | a4c_final_volume.py | A3 の直しをすべて逆にたどり、最終の座標の骨の体積（0.735 mm）を作る → a4_skel_field.npy |
| 27 | a4d_fins_volume.py ／ a4d2_median_fins.py | 決定後の胸びれ・肩帯・腹びれ、立て直した背びれ・臀びれの体積 |
| 28 | a4e_mesh.py | マーチングキューブで面を作る → mesh/HH_*.ply（git に入れない） |
| 29 | a4f_render_outline.py | Blender（別シーン HH_A4）で白い光の静止画 → docs/hammerhead_ct/a4_*.png |
| 30 | a4g_overlay_top.py | 背中の静止画に写真の外形を重ねる → a4_top_photo.png |
| 31 | a4h_headwidth_options.py ／ a4i_bodywidth_options.py | 頭の幅・胴の幅の案の絵 |
| 32 | a5a_shell.py（段 1〜4）／ a5a_mesh.py ／ a5a_check.py | 体の膜の体積（半径の表、胴の幅、正中のひれの膜）→ a5_S.npy、面 mesh/HH_body.ply、確かめの図 |
| 33 | a5b_render_body.py | 膜と骨を重ねた静止画 → docs/hammerhead_ct/a5_*.png（a4f の後に同じシーンで） |
| 34 | a5c_photo_pect.py ／ a5d_pect_membrane.py ／ a5e_pelv_membrane.py | 胸びれの膜（写真の外形）、腹びれの膜（仮、骨を広げた形）→ mesh/HH_pectmem_*.ply・HH_pelvmem_*.ply |
| 35 | a6b_split_head.py ／ a6a_export_gltf.py | 骨格を頭の軟骨とそれ以外に分け、組織ごとに減らして glb に書き出す（Blender の別シーン HH_EXPORT）→ 水槽/scenes/specimen/assets/specimen_hammerhead.glb。A7 の後は 40 のあとにやり直す |
| 36 | a4c_final_volume.py（直し）| 頭の幅の縮めを翼だけにする（正中から 45 mm まで縮めない）。`python3 a4c_final_volume.py 0 226 keep` で頭の断面だけ作り直し、a5a_shell.py 1〜4 をやり直す。いまの a4c はこの直しを含むので、通して作るときは 26 の 1 回でよい |
| 37 | a7_probe.py ／ a7a_jaw_fine.py | 逆写像の共通部分。顎のまわりを 0.35 mm の格子で作る → a7_jaw_fine.npz |
| 38 | a7b_jaw_seg.py | 頭骨・上あご・下あご・舌の弓・歯（上・下）に分ける（断面で置いた種から殻に沿って流し込む）→ a7_jawlab.npy |
| 39 | a7c_open_mesh.py <角度> mesh | 顎の関節の軸のまわりに下あごと下の歯を回して口を開き、体の膜（a5_S_open.npy）も開く。顎・歯・舌の弓の面 → mesh/HH_jaw_*・HH_teeth_*・HH_hyoid.ply、docs/hammerhead_ct/a7_open.json。このあと `a5a_mesh.py a5_S_open.npy` |
| 40 | a7d_skel_mesh.py | 骨格の面を、顎・歯・舌の弓を除いて作り直す（HH_skeleton.ply）。このあと a6b_split_head.py |
| 41 | a7f_gill_field.py ／ a7g_gill_frag.py | エラのまわりを 0.5 mm の格子で（小さな塊も入れて）作り、エラの空気とかけらを見る |
| 41b | a7g2_gill_air.py | エラの空気（a7_slit.npy）と、左のエラの空気の内と外の端（a7_uin.npy）（2026-10-15 書き起こし。前の work/ と一致） |
| 42 | a7h_gill_arches.py | （旧）エラの骨 5 対と底鰓の 1 回目（細い棒、置き場所は左のエラの空気の帯）。2026-10-15 に 42b で置き換え |
| 42b | a7h2_gill_options.py B2 139 215 2 53.4 | エラの骨（案 B2、2026-10-15 決定。前の B は 150〜215 mm）。形は BIODIDAC の Squalus の図を読んだ板、吻端から 139〜215 mm（顎のすぐ後ろから）、腹の端は体の膜の 6 mm 内側。7・8 番目の引数で鰓条（使っていない）→ mesh/HH_gill.ply、a7_gill_arches_B2.json（docs/hammerhead_ct/a7_gill_arches.json に写す） |
| 43 | a7e_render_head.py ／ a7i_mouth_options.py | 頭の部品を色分けした不透明の静止画（Blender の別シーン HH_HEAD）、口の開き方の案 → docs/hammerhead_ct/a7_head_*.png・a7_mouth_*.png |
| 44 | a8a_viscera.py（HH_VISC_SIGMA=10,3,3 HH_VISC_GAPDIL=0 HH_VISC_OPEN=0） | 体腔の形（CT のすき間を包む形）→ a8_viscera_ct.npy。mesh を付けると CT から取り出した内臓の面（案 1、使っていない） |
| 45 | a8b_viscera_organs.py（HH_ORGANS=B HH_SPIRAL=bowl） | 内臓（案 2c、2026-10-15 決定）。並び方は BIODIDAC の Squalus の消化器の図、置き場所は CT。肝臓・消化管・らせん弁の仕切り → mesh/HH_liver.ply・HH_gut.ply・HH_spiral.ply、a8_organs.json。このあと a6a_export_gltf.py |

確かめた図は `docs/hammerhead_ct/`（comps_named.png、spine_cpr2.png、roll_check.png、pect_posed.png）と `~/transparent-aquarium/シュモクザメ/_確認/`。

注意: 前の担当の Mac 上の Linux（メモリ約 4 GB）では、全体の体積（2093×512×512）に 3D の塊分けをかけるとメモリが足りないため、体の範囲に切った zyg_clean.npy（2093×108×430）で行っていた。24 GB の Mac でも同じ手順で動き、結果を変えないため切ったままにしている。
| 46 | a8c_vertebrae.py（HH_VERT_JITTER=2 HH_VERT_SOFT=1 HH_VERT_ARCHH=0.8） | 背骨（案 E、2026-10-15 決定）。形は BIODIDAC の Squalus の椎骨の写真、位置と太さは CT。中の詰まった椎体 → mesh/HH_vert_centra.ply（glb の部品 Centrum、a6a に HH_VERT_CENTRA_PART=Centrum）、背と腹の弓 → mesh/HH_vert_arches.ply（Cartilage に足す）。CT の殻 HH_bone は Bone のまま |

#!/bin/zsh
# シロシュモクザメ: 全身 CT の zip から、標本ページの glb まで通して作る（README の実行順）。
#
#   blender/ct_hammerhead/run_all.sh <出力のフォルダ>    そのフォルダに work/ mesh/ docs/ specimen_hammerhead.glb を作る
#   blender/ct_hammerhead/run_all.sh --default           いつもの置き場（work/、mesh/、docs/hammerhead_ct/、標本ページの glb）に上書きする
#   FIGS=1 を付けると、確認の図（docs/hammerhead_ct/ の *.png の元）も作る。FROM=<スクリプト名> でその段から始める
#
# 必要なもの: リポジトリ直下の .venv（CLAUDE.md）、Blender 5.2（/Applications/Blender.app）、元の zip（hh_paths.py の ZIP）
# 時間とディスク: 2026-10-15 の Mac（M4、24 GB）で約 5 分（279 秒）、出力に約 4.6 GB
set -e
H=${0:A:h}
PY=$H/../../.venv/bin/python
BL=/Applications/Blender.app/Contents/MacOS/Blender
if [[ $1 == --default ]]; then
  unset HH_WORK HH_MESH HH_DOCS HH_GLB
elif [[ -n $1 ]]; then
  O=${1:A}
  export HH_WORK=$O/work HH_MESH=$O/mesh HH_DOCS=$O/docs HH_GLB=$O/specimen_hammerhead.glb
  mkdir -p $HH_WORK $HH_MESH $HH_DOCS
else
  echo "使い方: run_all.sh <出力のフォルダ> | --default"; exit 2
fi
export HH_SCRIPTS=$H
started=${FROM:+no}
t0=$(date +%s)
step() {   # step <py|blender|fig|figblender> <スクリプト> [引数 ...]
  local kind=$1 s=$2; shift 2
  if [[ $started == no ]]; then [[ $s == $FROM ]] && started=yes || return 0; fi
  [[ $kind == fig* && -z $FIGS ]] && return 0
  local t=$(date +%s)
  if [[ $kind == *blender ]]; then
    $BL -b --factory-startup -P $H/$s -- "$@" 2>&1 | grep -v DeprecationWarning | grep -E "Error|Traceback|wrote|parts|faces|open" || true
  else
    $PY $H/$s "$@" | tail -3
  fi
  echo "--- $s $* : $(( $(date +%s) - t )) s（通算 $(( $(date +%s) - t0 )) s）"
}
# A1・A2 CT を読み、骨の塊と背骨の線
step py a1_load_clean.py
step py a2_skeleton.py
step py a2b_split_head_spine.py
step py a2d_comps_info.py
step py a2c_roll.py
# A3 変形を戻す（決定はスクリプトの注と計画書 第 9 節 A3）
step py a3_unroll_preview.py
step py a3b_sym_tilt.py
step py a3c0_pect_split.py
step fig a3c_pectoral_options.py
step fig a3o_comps_look.py
step fig a3o_comps_xsec.py
step py a3e0_pelvic_look.py
step py a3e_pelvic_options.py
step py a3f_pelvic_pose.py
step fig a3g0_tail_look.py
step py a3g_tail_upturn.py
step fig a3g_tail_upturn_fig.py
step fig a3h_tail_options.py
step py a3i_tail_bend.py
step fig a3k0_head_midline.py
step py a3k_head_yaw.py
step py a3l0_neck_roll_measure.py
step py a3l_neck_roll_fix.py
step py a3d_pectoral_pose.py
step fig a3m_head_options.py
step py a3n_head_mirror.py
step fig a3j_body_fig.py
step fig a4a_photo_top_cmp.py
step fig a4b_trunk_options.py
# A4 最終の座標の骨の体積と面
step py a4c_final_volume.py
step py a4d_fins_volume.py
step py a4d2_median_fins.py
step py a4e_mesh.py skel
step py a4e_mesh.py spine
step py a4e_mesh.py fins
step fig a4h_headwidth_options.py
step fig a4i_bodywidth_options.py
# A5 体の膜とひれの膜
step py a5a_shell.py 1
step py a5a_shell.py 2
step py a5a_shell.py 3
step py a5a_shell.py 4
step fig a5a_check.py
step py a5c_photo_pect.py
step py a5d_pect_membrane.py
step py a5e_pelv_membrane.py
# A7 顎・歯・舌の弓（口は 25° 開く。2026-10-15 プロデューサー決定）、エラの骨
step py a7a_jaw_fine.py
step py a7b_jaw_seg.py
step py a7c_open_mesh.py 25 mesh
step py a5a_mesh.py a5_S_open.npy
step py a7d_skel_mesh.py
step py a6b_split_head.py
step py a7f_gill_field.py
step fig a7g_gill_frag.py
step py a7g2_gill_air.py
# エラの骨は案 B2（139〜215 mm。2026-10-15 プロデューサー決定。前の B は 150〜215 mm）。前の形（a7h_gill_arches.py）は使わない
step py a7h2_gill_options.py B2 139 215 2 53.4
# A8 内臓（案 2c、2026-10-15 プロデューサー決定）: a8a は体腔の形（a8b が読む）、a8b が肝臓・消化管・らせん弁を作る
HH_VISC_SIGMA=10,3,3 HH_VISC_GAPDIL=0 HH_VISC_OPEN=0 step py a8a_viscera.py
HH_ORGANS=B HH_SPIRAL=bowl step py a8b_viscera_organs.py
# A8 背骨（案 E、2026-10-15 プロデューサー決定）: 椎体と弓を部品から作り、椎体は別の部品 Centrum（CT の殻は Bone のまま）
HH_VERT_JITTER=2 HH_VERT_SOFT=1 HH_VERT_ARCHH=0.8 step py a8c_vertebrae.py
export HH_VERT_CENTRA_PART=Centrum HH_VERT_ARCH_PART=Arch   # 弓も別の部品（2026-10-15 H1）
# A6 glb に書き出す（Blender）
step py b5a_jaw_region.py   # B5 口: 下あごといっしょに動く膜の範囲（b1_rig.py が使う）
export HH_RIG=1   # B1 骨組み（b1_rig.py）を付けて書き出す。標本ページは B3（2026-10-15）から骨組みでうねる
step blender a6a_export_gltf.py
# Blender の確認の図（a4f → a5b は同じシーン、a7e → a7i も同じシーンなので、1 つの Blender で続けて走らせる）
if [[ -n $FIGS && $started != no ]]; then
  $BL -b --factory-startup -P $H/a4f_render_outline.py -P $H/a5b_render_body.py 2>&1 | grep -E "Error|Traceback|wrote" || true
  $PY $H/a4g_overlay_top.py | tail -1
  $BL -b --factory-startup -P $H/a7e_render_head.py -P $H/a7i_mouth_options.py 2>&1 | grep -E "Error|Traceback|wrote" || true
fi
echo "=== 終わり: $(( $(date +%s) - t0 )) s。glb: ${HH_GLB:-既定の置き場}"

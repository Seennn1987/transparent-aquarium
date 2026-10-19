#!/bin/zsh
# シロシュモクザメ: 全身 CT の zip から、標本ページの glb まで通して作る（README の実行順）。
#
#   blender/ct_hammerhead/run_all.sh <出力のフォルダ>    そのフォルダに work/ mesh/ docs/ specimen_hammerhead.glb を作る
#   blender/ct_hammerhead/run_all.sh --default           いつもの置き場（work/、mesh/、docs/hammerhead_ct/、標本ページの glb）に上書きする
#   FIGS=1 を付けると、確認の図（docs/hammerhead_ct/ の *.png の元）も作る。FROM=<スクリプト名> でその段から始める
#
# 案を作るとき（2026-10-17 プロデューサー「案ごとに残すのは「作り直す方法」と「小さい結果」だけにして、work/ は残しません」）:
#   BASE=<作り直したフォルダ> を付けると、出力のフォルダに work/ mesh/ docs/ が無いとき、BASE の中身を APFS の複製（cp -c）で置いてから始める。
#     複製はファイルの中身を共有するので、FROM= より前の段の中間ファイル（zyg.npy など）はディスクを使わない。書き直した段の分だけ増える
#   blender/ct_hammerhead/ に未コミットの変更があると止まる（どの版で作ったかを残すため）。試しだけなら ALLOW_DIRTY=1
#   出力のフォルダに run_info.txt を書く（日時、引数、FROM・BASE、git のコミット、未コミットの変更、HH_ の環境変数、終わったときの glb）
#   うまく終わったら work/ をゴミ箱（~/.Trash）へ移す。残すときは KEEP_WORK=1。--default のときは移さない。ゴミ箱は空にするまでディスクを使う
#   TAG=<名前>（例 hh-body-f1）で、うまく終わったときに git のタグを付ける
#
# 必要なもの: リポジトリ直下の .venv（CLAUDE.md）、Blender 5.2（/Applications/Blender.app）、元の zip（hh_paths.py の ZIP）
# 時間とディスク: 2026-10-15 の Mac（M4、24 GB）で約 5 分（279 秒）、出力に約 4.6 GB
set -e
setopt pipefail   # 段の Python が失敗したら止める（tail に渡しても失敗が消えないように。work/ を片付ける前に、うまく終わったかを確かめるため）
H=${0:A:h}
R=${H:h:h}
# どの版で作ったかを残すため、blender/ct_hammerhead/ に未コミットの変更があれば、何かを作る前に止める
dirty=$(git -C $R status --porcelain -- blender/ct_hammerhead)
if [[ -n $dirty && -z $ALLOW_DIRTY ]]; then
  echo "blender/ct_hammerhead/ に未コミットの変更があります。コミットしてから実行してください（試しだけなら ALLOW_DIRTY=1）:"; echo "$dirty"; exit 3
fi
PY=$H/../../.venv/bin/python
BL=/Applications/Blender.app/Contents/MacOS/Blender
if [[ $1 == --default ]]; then
  unset HH_WORK HH_MESH HH_DOCS HH_GLB
elif [[ -n $1 ]]; then
  O=${1:A}
  export HH_WORK=$O/work HH_MESH=$O/mesh HH_DOCS=$O/docs HH_GLB=$O/specimen_hammerhead.glb
  if [[ -n $BASE && ! -e $HH_WORK ]]; then
    B=${BASE:A}; [[ -d $B/work ]] || { echo "BASE に work/ がありません: $B"; exit 2; }
    mkdir -p $O && cp -c -R $B/work $B/mesh $B/docs $O/
  fi
  mkdir -p $HH_WORK $HH_MESH $HH_DOCS
else
  echo "使い方: run_all.sh <出力のフォルダ> | --default"; exit 2
fi
export HH_SCRIPTS=$H
started=${FROM:+no}
t0=$(date +%s)
# どの版・どの設定で作ったかを残す
INFO=${O:-$H/mesh}/run_info.txt   # --default のときは mesh/ に置く（work/ には書き足さない）
{
  echo "日時: $(date '+%Y-%m-%d %H:%M:%S')"
  echo "コマンド: run_all.sh $*"
  echo "FROM: ${FROM:-（最初から）}"
  echo "BASE: ${BASE:-（なし）}"
  echo "git: $(git -C $R rev-parse HEAD)（$(git -C $R log -1 --format=%s | cut -c1-60)）"
  echo "未コミットの変更（blender/ct_hammerhead/）: ${dirty:-なし}"
  echo "FIGS: ${FIGS:-} KEEP_WORK: ${KEEP_WORK:-} TAG: ${TAG:-}"
  echo "始めるときに指定した環境変数:"; { env | grep '^HH_' | grep -v -E '^HH_(WORK|MESH|DOCS|GLB|SCRIPTS)=' | sort | sed 's/^/  /' } || echo "  （なし）"
} > $INFO
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
# 2026-10-19 決定（プロデューサー「この臀びれでよいので、同じ作り方を第 2 背びれと腹びれに広げて…」→「今の変更を既定にした後…」）: 第 2 背びれ・臀びれ・腹びれの軟骨を、
#  元の CT の細かさ（閾値 175、σ 0.5 画素）で面にしてから動かす（a4d3_fin_ct_mesh.py）。膜は軟骨に合わせて大きさを決める（HH_FINCT_FIT=membrane）。
#  前の形は HH_FINCT_ANAL= HH_FINCT_DFIN2= HH_FINCT_FIT= HH_PELV_CT175=
export HH_FINCT_ANAL=${HH_FINCT_ANAL-1} HH_FINCT_DFIN2=${HH_FINCT_DFIN2-1} HH_FINCT_FIT=${HH_FINCT_FIT-membrane} HH_PELV_CT175=${HH_PELV_CT175-1}
[[ $HH_FINCT_ANAL == 1 ]] && step py a4d3_fin_ct_mesh.py anal
[[ $HH_FINCT_DFIN2 == 1 ]] && step py a4d3_fin_ct_mesh.py dfin2
[[ $HH_PELV_CT175 == 1 ]] && step py a4d3_fin_ct_mesh.py pelv
step fig a4h_headwidth_options.py
step fig a4i_bodywidth_options.py
# A5 体の膜とひれの膜
# 胴の形は案 2（2026-10-16 プロデューサー「胴の形は案 2 に決めて、既定にしてください」）: 幅は FMIB 51331・高さは Duane Raver の図に合わせ（ref）、
#  断面をなめらかな曲線で当て（smooth）、横から見た背と腹の線を 40・90 mm でならし、背びれ・臀びれの膜を ±3 mm の板に、面を作ったあとにならす。
#  前の形は HH_TRUNK_PROFILE=ct HH_SHELL_FIT=median HH_SIDE_SMOOTH= HH_FIN_HALF= HH_MESH_TAUBIN=0 HH_MESH_SIGMA=1
export HH_TRUNK_PROFILE=${HH_TRUNK_PROFILE-ref} HH_SHELL_FIT=${HH_SHELL_FIT-smooth} HH_SIDE_SMOOTH=${HH_SIDE_SMOOTH-40,90} HH_FIN_HALF=${HH_FIN_HALF-3}
export HH_MESH_TAUBIN=${HH_MESH_TAUBIN-50} HH_MESH_SIGMA=${HH_MESH_SIGMA-1.5}
# ひれ（2026-10-17 プロデューサー「背びれ 2 つと臀びれを参考の外形にし、胸びれ・腹びれを下へ 15° 回す案で既定にしてください」）: 外形は hh_fins.py。
#  前の形は HH_FIN_REF= HH_FIN_PLATE= HH_PECT_DOWN=0 HH_PELV_DOWN=0
# 胸びれは 2026-10-17 の見直しで下へ 5°（水平から約 22° 下。プロデューサー「胸びれはおすすめの約 22° 下で既定にしてください」。泳ぐサメの計測 6〜23°、Wilga & Lauder）
export HH_FIN_REF=${HH_FIN_REF-1} HH_FIN_PLATE=${HH_FIN_PLATE-1} HH_PECT_DOWN=${HH_PECT_DOWN-5} HH_PELV_DOWN=${HH_PELV_DOWN-15}
# 2026-10-17 決定（プロデューサー「全てのヒレの色のつき方が変です…」→ 直しの範囲の図に「進めて」）: 第 2 背びれ・臀びれの軟骨を参考の膜の付け根へ（先が膜の高さの 0.53）、
#  尾びれの下の葉の軟骨を膜と同じだけ腹側へ、腹びれの膜を付け根を中心に 1.4 倍。前の形は HH_FIN_CART_REACH= HH_LOBE_CART= HH_PELV_SCALE=1
export HH_FIN_CART_REACH=${HH_FIN_CART_REACH-0.53} HH_LOBE_CART=${HH_LOBE_CART-1} HH_PELV_SCALE=${HH_PELV_SCALE-1.4}
# 2026-10-17 プロデューサー「今、ヒレごとの色の濃さを調整できません。特に背鰭がずっと透明です。」: ひれごとに軟骨と膜を別の部品に（ページで濃さ・にごり度を変える）。
#  背びれ 2 つと臀びれの膜は、体の膜の体積に足さず板の面にする（HH_FIN_PLATE=all）。前の形は HH_FIN_PARTS= HH_FIN_PLATE=1
export HH_FIN_PARTS=${HH_FIN_PARTS-1}
[[ $HH_FIN_PARTS == 1 && $HH_FIN_PLATE == 1 ]] && export HH_FIN_PLATE=all
# 2026-10-18（プロデューサー「内臓（直し A）とひれ（直し B・C）の両方を、その案で直してください」）: 内臓は部品ごとに 1 つの塊にしてから面を作る（HH_ORGAN_UNION）、
#  背びれ・臀びれの軟骨のひねりを取って膜の板の厚さに収め（HH_FIN_CART_FLAT）、膜の外形の内側へ寄せる（HH_FIN_CART_FIT）。前の形は 3 つとも空に
export HH_ORGAN_UNION=${HH_ORGAN_UNION-1} HH_FIN_CART_FLAT=${HH_FIN_CART_FLAT-1} HH_FIN_CART_FIT=${HH_FIN_CART_FIT-1}
# 2026-10-18（プロデューサー「CTを原本にしない方が良いのでは？もっと良い事例を探してみて」→「その案で進めてください」）の案: 第 2 背びれ・臀びれ（HH_FIN_RODS）と
#  腹びれ（HH_PELV_RODS）の軟骨を、CT の代わりに図と写真から棒と板で作る（hh_finrods.py）。プロデューサー「そんな直線的で太さも感覚も均一な棒みたいなのを置くのでいいわけないじゃん。」で使わない
step py a5a_shell.py 1
step py a5a_shell.py 2
step py a5a_shell.py 3
step py a5a_shell.py 4
step fig a5a_check.py
step py a5c_photo_pect.py
step py a5d_pect_membrane.py
step py a5e_pelv_membrane.py
# 2026-10-20 決定（プロデューサー「腹びれの軟骨と膜を、腰帯・基鰭軟骨・放射軟骨のつくりに合わせて直す案を…」→「ヒレそのものの形はこれまでのものの方が実態に近いのでは？…」→
#  「腹びれはこの案を既定にしてください」）: 腹びれの膜は前の版の外形の縁を直線にならし、軟骨はウチワシュモクザメの透明標本の写真の形（腰帯・基鰭軟骨・放射軟骨）を
#  その中に割り振る（a5f_pelv_photo.py。写真は git に入れていないので、手元に無ければ止まる）。前の形は HH_PELV_PHOTO=
export HH_PELV_PHOTO=${HH_PELV_PHOTO-1}
[[ $HH_PELV_PHOTO == 1 ]] && step py a5f_pelv_photo.py
# A7 顎・歯・舌の弓（口は 25° 開く。2026-10-15 プロデューサー決定）、エラの骨
step py a7a_jaw_fine.py
step py a7b_jaw_seg.py
step py a7c_open_mesh.py ${HH_MOUTH_DEG:-15} mesh   # 口の開き（2026-10-15 決定 15°、前は 25°。HH_MOUTH_DEG で案を作る）
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
# 尾の骨（2026-10-17 プロデューサー「尾の骨を足す案にして、弓の色はひれの軟骨の半分の青で既定にしてください」）: 血道弓を高く、肋骨と尾びれの鰭条を足す
export HH_VERT_HAEMAL=${HH_VERT_HAEMAL-1} HH_VERT_RIBS=${HH_VERT_RIBS-1} HH_VERT_RADIALS=${HH_VERT_RADIALS-1}
HH_VERT_JITTER=2 HH_VERT_SOFT=1 HH_VERT_ARCHH=0.8 step py a8c_vertebrae.py
export HH_VERT_CENTRA_PART=Centrum HH_VERT_ARCH_PART=Arch   # 弓も別の部品（2026-10-15 H1）
# A6 glb に書き出す（Blender）
step py b5b_heart.py   # B5 心臓（案「実物に近い大きさ」、2026-10-15 決定）
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
G=${HH_GLB:-$R/水槽/scenes/specimen/assets/specimen_hammerhead.glb}
{
  echo "終わり: $(date '+%Y-%m-%d %H:%M:%S')（$(( $(date +%s) - t0 )) 秒）"
  [[ -f $G ]] && echo "glb: $G $(stat -f %z $G) バイト md5 $(md5 -q $G)"
  echo "終わったときの環境変数（このスクリプトの既定を含む）:"; { env | grep '^HH_' | grep -v -E '^HH_(WORK|MESH|DOCS|GLB|SCRIPTS)=' | sort | sed 's/^/  /' } || true
} >> $INFO
if [[ -n $O && -z $KEEP_WORK && -d $HH_WORK ]]; then
  T=~/.Trash/${O:t}-work-$(date +%Y%m%d%H%M%S)
  mv $HH_WORK $T && echo "work/ をゴミ箱へ移した: $T" | tee -a $INFO
fi
if [[ -n $TAG ]]; then git -C $R tag $TAG && echo "タグ: $TAG" | tee -a $INFO; fi

#!/bin/bash
# 記録 144: 記録 102 の骨（p102）で、左膝を開いた姿勢（open_knee.py）から、手・足・体の膜、つなぎ目、爪の鞘を作り直す。臓器は今のもの。
#   cd blender/private/work/p144 && bash ../../../ct_body_pipeline/build_skin_144.sh
# 手順は p76/build_T.sh と同じ。違いは 骨（p102）、姿勢（pose_jar_open.npz）、手の膜も作り直すこと
set -e
W=/Users/shoui/transparent-aquarium/transparent-aquarium/blender/private/work; R=/Users/shoui/transparent-aquarium/transparent-aquarium/blender/private
P=/Users/shoui/transparent-aquarium/transparent-aquarium/.venv/bin/python; SB=/Users/shoui/transparent-aquarium/transparent-aquarium/blender/ct_body_pipeline
BL=/Applications/Blender.app/Contents/MacOS/Blender
D=$W/p144; cd $D
OUT="pose_jar.npz chameleon_body_ct_dec.npz soft_rigged.npz skin_posed.npz skinbody_tables.npz chameleon_body_soft.npz chameleon_body_ct.npz feet_posed.npz hands_posed.npz merged_posed.npz seam_patch.npz m1.npz m2.npz skinbody.log"
for f in $W/*; do b=$(basename "$f"); [ -d "$f" ] && continue; case " $OUT " in *" $b "*) continue;; esac; case "$b" in *.log|diag_*) continue;; esac; [ -e "$b" ] || ln -sf "$f" "$b"; done
cp $R/p102/chameleon_body_ct.npz $R/p102/chameleon_body_ct_dec.npz .
# 姿勢: dump_pose.py（CH_CT_NPZ=p102 の骨）→ pose_jar_orig.npz、open_knee.py pose_jar_orig.npz pose_jar_open.npz 110
cp pose_jar_open.npz pose_jar.npz
export PYTHONPATH=$SB
$P $SB/feet_skin.py $W/digits_h33.npz feet_posed.npz > feet.log 2>&1; echo "足の膜 $(tail -1 feet.log)"
LIMBS=fL_hand,fR_hand $P $SB/feet_skin.py $W/digits_h33.npz hands_posed.npz > hands.log 2>&1; echo "手の膜 $(tail -1 hands.log)"
LIMB_T_FOOT=0.73 $P $SB/skinbody.py > skinbody.log 2>&1; echo "体の膜 $(tail -1 skinbody.log)"
mkdir -p s0 s1 s2; mv soft_rigged.npz skin_posed.npz s0/
export CUT_PAD_MM=${CUT_PAD_MM:-1.2}
$BL -b -P $SB/merge_feet.py -- s0/skin_posed.npz feet_posed.npz m1.npz > merge1.log 2>&1; grep "減らした\|つないだ膜:" merge1.log | tail -1
$P $SB/rig_merged.py m1.npz s0/soft_rigged.npz s0/skin_posed.npz > rig1.log; mv soft_rigged.npz skin_posed.npz s1/
LIMBS=fL_hand,fR_hand $BL -b -P $SB/merge_feet.py -- s1/skin_posed.npz hands_posed.npz m2.npz > merge2.log 2>&1; grep "減らした\|つないだ膜:" merge2.log | tail -1
LIMBS=fL_hand,fR_hand $P $SB/rig_merged.py m2.npz s1/soft_rigged.npz s1/skin_posed.npz > rig2.log; mv soft_rigged.npz skin_posed.npz s2/
$P $SB/seam_patch.py s2/skin_posed.npz seam_patch.npz > seam.log; $P $SB/seam_project.py s2/skin_posed.npz seam_patch.npz merged_posed.npz >> seam.log
LIMBS= $P $SB/rig_merged.py merged_posed.npz s2/soft_rigged.npz s2/skin_posed.npz > rig3.log
$P $SB/pack_soft.py > pack.log; $P $SB/claws_mesh.py chameleon_body_ct.npz $W/digits_h33.npz chameleon_body_soft.npz soft_claw.npz > claws.log; mv soft_claw.npz chameleon_body_soft.npz
$P $SB/diag_inside.py > diag_inside.log 2>&1; $P $SB/chk_soft.py > chk_soft.log 2>&1; $P $SB/diag_bones.py > diag_bones.log 2>&1
echo "穴 $(tail -1 diag_inside.log | cut -c1-90)"; grep -v "0.00%" chk_soft.log | grep -v "claw\|soft " || true
grep -E "outside>0.1mm +[1-9]" diag_bones.log | head -8 || true
echo done

#!/bin/zsh
# 段ごとの検算: 1 つの段を、元の中間ファイル（work/・mesh/）を入力にして走らせ、書いたファイルを元と比べる。
#   使い方: blender/ct_hammerhead/check_stage.sh <スクリプト> [引数 ...]        （Python の段）
#           BLENDER=1 blender/ct_hammerhead/check_stage.sh <スクリプト>          （Blender の段。-b で走らせる）
# work/ と mesh/ には書かない。rebuild/check/ に APFS の複製（cp -c。中身が同じ間は場所を取らない）を作り、そこで走らせる。
# 比べたあと、書かれたファイルを元の複製へ戻すので、次の段も元の入力で走る（元に無いファイルは残す）。
set -e
H=${0:A:h}
CK=$H/rebuild/check
export HH_WORK=$CK/work HH_MESH=$CK/mesh HH_DOCS=$CK/docs HH_GLB=$CK/specimen_hammerhead.glb HH_SCRIPTS=$H
PY=$H/../../.venv/bin/python
if [[ ! -d $CK/work ]]; then
  mkdir -p $CK/work $CK/mesh $CK/docs
  cp -c $H/work/* $CK/work/
  cp -c $H/mesh/* $CK/mesh/
fi
script=$1; shift
mark=$CK/.mark; touch $mark; sleep 1
start=$(date +%s)
if [[ -n $BLENDER ]]; then
  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P $H/$script -- "$@" 2>&1 | grep -v DeprecationWarning | tail -20
else
  $PY $H/$script "$@" 2>&1 | tail -20
fi
echo "--- $script $* : $(( $(date +%s) - start )) s"
changed=( ${(f)"$(find $CK/work $CK/mesh -newer $mark -type f ! -name '*.png' | sort)"} )
for f in $changed; do
  [[ -z $f ]] && continue
  d=${f:h:t}   # work か mesh
  $PY $H/compare_work.py $H/$d ${f:h} ${f:t}
  if [[ -e $H/$d/${f:t} ]]; then rm -f $f; cp -c $H/$d/${f:t} $f; fi   # 元に無いもの（書き起こした段の出力）は、次の段の入力として残す
done
find $CK/work $CK/mesh -newer $mark -name '*.png' -exec mv {} $CK/docs/ \; 2>/dev/null || true

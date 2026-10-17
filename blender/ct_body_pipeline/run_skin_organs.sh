#!/bin/bash
# 膜から臓器まで: skinbody → organs_cav → organs → organs_mesh → eyes_mesh → hyoidcart_mesh → pack_soft
# 作業フォルダ（中間ファイルのある所。Mac では blender/private/work/）に入って実行する。
#   cd blender/private/work && bash ../../ct_body_pipeline/run_skin_organs.sh
# 結果の chameleon_body_soft.npz を blender/private/ に置いてから glb を書き出す。
# Python は環境変数 PY（既定はリポジトリ直下の .venv）。Mac の skinbody は約 6.5 分、全体で約 8 分（2026-10-17）。
HERE="$(cd "$(dirname "$0")" && pwd)"
PY="${PY:-$HERE/../../.venv/bin/python}"
"$PY" "$HERE/skinbody.py" > skinbody.log 2>&1 || { echo FAIL skinbody; tail -5 skinbody.log; exit 1; }
for f in organs_cav.py organs.py organs_mesh.py eyes_mesh.py hyoidcart_mesh.py pack_soft.py; do
  "$PY" "$HERE/$f" > ${f%.py}.log 2>&1 || { echo FAIL $f; tail -5 ${f%.py}.log; exit 1; }
done
echo DONE

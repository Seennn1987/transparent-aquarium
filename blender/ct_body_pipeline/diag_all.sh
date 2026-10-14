#!/bin/bash
# 膜の自己検証（展示の姿勢）: 内側の升 → 骨のはみ出し → 太さの表
set -e
python3 diag_inside.py | tail -1
python3 diag_bones.py | tail -14
python3 diag_profile.py

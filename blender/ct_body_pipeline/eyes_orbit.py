"""眼球を眼窩の穴に合わせる（計画書 C の記録 25・26、案 ③C。2026-10-17 プロデューサー決定）。

  python eyes_orbit.py <入力の eyes.json> <眼窩.json> <出力の eyes.json>

眼窩.json（記録 25 で測った。p25/orbit.json）: 眼ごとに、横から（ページの座標の Z の向きに）写した頭骨の像の、眼窩の穴の重心 hole_cen [mm]
（ページの X・Y。左は眼の中の輪の骨を除いた）と、面積が同じ円の半径 hole_req [mm]、今の眼の中心 eye_c と半径 eye_r [mm]。
・中心: 展示の姿勢での眼の中心の X・Y（ページの座標）を穴の重心へ。左右（Z）は今のまま
・半径: 左右の穴の hole_req の平均（5.02 mm）。左右で同じにする
ページの座標 g と pose_jar の座標 b は g = (b0, b2, −b1)。静止の中心は頭の行列の逆で戻す。
"""
import json
import sys
import numpy as np

src, orb, dst = sys.argv[1:4]
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; k = float(P['k']); Mh = P['M'][bn.index('head')]
O = json.load(open(orb)); E = json.load(open(src))
R = float(np.mean([O[e]['hole_req'] for e in ('eye_l', 'eye_r')]))
for e, v in E.items():
    b = np.array(v['centre_model']); g = np.array([b[0], b[2], -b[1]])
    g[:2] = np.array(O[e]['hole_cen']) * k
    bnew = np.array([g[0], -g[2], g[1]])
    v['centre_model'] = bnew.tolist()
    v['centre_rest_model'] = (np.linalg.inv(Mh[:3, :3]) @ (bnew - Mh[:3, 3])).tolist()
    print(e, '中心を %.2f mm 動かした、半径 %.2f → %.2f mm' % (np.linalg.norm(bnew - b) / k, v['radius_mm'], R))
    v['radius_mm'] = R
json.dump(E, open(dst, 'w'), indent=1)

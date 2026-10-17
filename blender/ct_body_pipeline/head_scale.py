"""頭を大きくする（計画書 C の記録 21、案 1A。2026-10-17 プロデューサー決定）。epiphysis_relabel.py の後に走らせる。

  python head_scale.py <入力の骨.npz> <出力の骨.npz> <入力の eyes.json> <出力の eyes.json> [倍率=1.45] [舌骨の倍率=倍率]

舌骨の倍率（2026-10-17、記録 25 の案）: 舌骨（骨と軟骨）だけ別の倍率にする。記録 21 は頭と同じ 1.45 で、喉・頸が太くなった

頭骨（head）・舌骨（hyoid）の骨と、舌骨の軟骨（cart__ のうち骨 'hyoid'）、眼球（eyes.json）を、後頭顆（骨組みの head の付け根
rig__head）のまわりに一様に拡大する。形は Digimorph の CT のまま。骨組み（rig__）は変えないので、全身の縮尺 k（generate_chameleon_ct_body.py の
SKULL_LENGTH_L ÷ 頭の骨の長さ）は変わらない。
根拠: 頭骨（吻端〜後頭）÷ 肩–股関節の直線が、今のモデル 0.30、写真 06 で 0.43、生体の背腹 X 線で 0.48（記録 20）。0.43 / 0.30 ≈ 1.45
"""
import json
import sys
import numpy as np

src, dst, ey_src, ey_dst = sys.argv[1:5]
S = float(sys.argv[5]) if len(sys.argv) > 5 else 1.45
SH = float(sys.argv[6]) if len(sys.argv) > 6 else S
d = dict(np.load(src))
names = [str(n) for n in d['rig__names']]
c = d['rig__head'][names.index('head')].astype(np.float64)                  # 後頭顆（CT の座標）
for k, f in (('head__v', S), ('hyoid__v', SH)):
    d[k] = (c + (d[k].astype(np.float64) - c) * f).astype(d[k].dtype)
m = d['cart__bone'] == 'hyoid'
for k in ('cart__a', 'cart__b'):
    a = d[k].astype(np.float64); a[m] = c + (a[m] - c) * SH; d[k] = a.astype(d[k].dtype)
d['cart__r'] = np.where(m, d['cart__r'] * SH, d['cart__r']).astype(d['cart__r'].dtype)
np.savez_compressed(dst, **d)

# 眼球: 静止（モデルの座標）と展示の姿勢の中心を、それぞれの後頭顆のまわりに。半径と正中からの距離も同じ倍率
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; k = float(P['k'])
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
Mh = P['M'][bn.index('head')]
cr = ct2m(c); cp = Mh[:3, :3] @ cr + Mh[:3, 3]
EY = json.load(open(ey_src))
for e in EY.values():
    e['centre_rest_model'] = (cr + (np.array(e['centre_rest_model']) - cr) * S).tolist()
    e['centre_model'] = (cp + (np.array(e['centre_model']) - cp) * S).tolist()
    e['radius_mm'] *= S; e['lateral_mm'] *= S
json.dump(EY, open(ey_dst, 'w'), indent=1)
print('hyoid x%.2f;' % SH, 'head x%.2f about the occipital condyle %s; eyes r %.2f mm' % (S, np.round(c, 2), EY['eye_r']['radius_mm']))

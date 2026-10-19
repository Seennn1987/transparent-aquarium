"""膜をつないだ所の段を、頂点を動かすだけで直す（記録 36 の案。2026-10-19）。seam_patch.py のパッチ（作り直した面）へ、つなぎ目の帯にある膜の
頂点を寄せる。面のつながりを変えないので穴は開かない（Blender のブール演算の和は、パッチと元の膜がほぼ重なる所で崩れた）。

  cd <案の作業フォルダ> && python seam_project.py <膜 skin_posed.npz> <seam_patch.npz> <出力 merged_posed.npz>

頂点ごとに、パッチと同じ重み w（つなぎ目の平面から ±BAND_MM で 1 → 0、箱の端では 0）を求め、パッチの面の最も近い所へ、法線の向きに w だけ動かす。
"""
import os
import sys
import numpy as np
from scipy.spatial import cKDTree

skin_p, patch_p, out_p = sys.argv[1:4]
BAND = float(os.environ.get('BAND_MM', '1.2')); OVL, EDGE = 0.2, 0.3
k = float(np.load('pose_jar.npz')['k']); MM = k
S = np.load(skin_p); v = S['v'].astype(np.float64); f = S['f']; Z = np.load(patch_p)
limbs = sorted({k_[6:] for k_ in Z.files if k_.startswith('frame_')})
e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]; src = np.r_[e[:, 0], e[:, 1]]; dst = np.r_[e[:, 1], e[:, 0]]
deg = np.bincount(src, minlength=len(v)).astype(float)
def avg(X):
    out = np.zeros_like(X); np.add.at(out, src, X[dst]); return out / np.maximum(deg, 1)[:, None]
RELAX = int(os.environ.get('RELAX', '30'))
moved = np.zeros(len(v))
for n in limbs:
    fr = Z['frame_' + n]; plane, R = fr[0], fr[1:].T; lo_p, hi_p = Z['box_' + n][:3], Z['box_' + n][3:]
    q = (v - plane) @ R / MM
    edge = np.minimum.reduce([q[:, i] - lo_p[i] for i in range(3)] + [hi_p[i] - q[:, i] for i in range(3)])
    u = np.clip(1 - np.abs(q[:, 2]) / BAND, 0, 1); w = u * u * (3 - 2 * u) * np.clip((edge - OVL - EDGE) / 0.2, 0, 1)
    sel = np.where(w > 0)[0]
    pv = Z['patch_' + n + '__v']; pf = Z['patch_' + n + '__f']
    fn = np.cross(pv[pf[:, 1]] - pv[pf[:, 0]], pv[pf[:, 2]] - pv[pf[:, 0]]); pn = np.zeros_like(pv)
    for i in range(3): np.add.at(pn, pf[:, i], fn)
    pn /= np.linalg.norm(pn, axis=1, keepdims=True) + 1e-12
    dd, j = cKDTree(pv).query(v[sel], workers=-1)
    disp = np.einsum('ij,ij->i', pv[j] - v[sel], pn[j])[:, None] * pn[j]     # パッチの面への法線の向きの差
    v[sel] += w[sel, None] * disp
    # 並べ直す: 帯の中で隣の平均へ寄せてから、作り直した面へ戻すのを繰り返す（ブール演算でできた細長い三角形がつなぎ目に並び、
    #   向きがばらついて折れ目に見えた）
    kd = cKDTree(pv)
    for _ in range(RELAX):
        v[sel] += 0.5 * w[sel, None] * (avg(v)[sel] - v[sel])
        dd, j = kd.query(v[sel], workers=-1)
        v[sel] += w[sel, None] * np.einsum('ij,ij->i', pv[j] - v[sel], pn[j])[:, None] * pn[j]
    moved[sel] = np.maximum(moved[sel], np.linalg.norm(w[sel, None] * disp, axis=1) / MM)
    print(n, '動かした頂点', len(sel), '最大 %.3f mm、中央値 %.3f mm' % ((np.linalg.norm(disp, axis=1) / MM).max(), np.median(np.linalg.norm(w[sel, None] * disp, axis=1) / MM)))
np.savez_compressed(out_p, v=v.astype(np.float32), f=f.astype(np.int32)); print('saved', out_p)

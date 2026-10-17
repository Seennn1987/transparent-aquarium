"""肋骨の付け根を動かす（計画書 C の記録 22 の案。2026-10-17）。trunk_widen.py の後に走らせる。

  python rib_roots.py <入力の骨.npz> <出力の骨.npz> <ct|attach> [つなぐ長さ mm=5] [CT の肋骨.npz=chameleon_body_ct_v1_ribs.npz]

付け根 = 肋骨の点のうち体軸（rig__axis）に最も近い 3% の重心。付け根からの距離が「つなぐ長さ」までの点を、なめらかに減る重み（1 → 0）で動かす。
- ct: 付け根を CT の元の肋骨（記録 8 の並べ直しの前、chameleon_body_ct_v1_ribs.npz）の付け根の位置へ。体軸に沿った前後は今のまま
- attach: 付け根を、椎骨（骨組みの親）の最も近い点へ、すき間が 0 になるまで寄せる（0.1 mm 重ねる）
- socket（案 D）: 付け根を、今の付け根より背側へ RAISE_MM 上げた点に最も近い椎骨の表面の点へ寄せ、椎骨の中へ 0.3 mm 差し込む。
  肋骨は椎骨の側面から出て、つなぐ長さのあいだで今の肋骨（後ろ下へ下りる）へ曲がる（写真 06 の肋骨は椎骨の横から出る。記録 22）
"""
import sys
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter1d

src, dst, mode = sys.argv[1:4]
LT = float(sys.argv[4]) if len(sys.argv) > 4 else 5.0
ctf = sys.argv[5] if len(sys.argv) > 5 else 'chameleon_body_ct_v1_ribs.npz'
RAISE_MM = 1.0
d = dict(np.load(src)); names = [str(n) for n in d['rig__names']]; par = [str(n) for n in d['rig__parent']]
A = d['rig__axis'].astype(np.float64); D = d['rig__dorsal'].astype(np.float64)
D = gaussian_filter1d(D, 20, axis=0, mode='nearest')
T = np.gradient(A, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
kd = cKDTree(A)
C = np.load(ctf) if mode == 'ct' else None


def head(x):
    i = kd.query(x)[1]; rel = x - A[i]; dist = np.linalg.norm(rel - (rel * T[i]).sum(1, keepdims=True) * T[i], axis=1)
    return x[dist <= np.percentile(dist, 3)].mean(0)


gaps = []
for k in [k for k in d if k.startswith('rib') and k.endswith('__v')]:
    b = k[:-3]; x = d[k].astype(np.float64); h = head(x)
    if mode == 'ct':
        if k not in C.files: continue
        hc = head(C[k].astype(np.float64)); j = kd.query(h)[1]
        mv = (hc - h); mv -= T[j] * (mv @ T[j])                    # 前後は今のまま
    elif mode == 'attach':
        v = d[par[names.index(b)] + '__v'].astype(np.float64); tv = cKDTree(v)
        dd, jj = tv.query(x); p = int(np.argmin(dd))
        mv = (v[jj[p]] - x[p]) * (1 + 0.1 / max(dd[p], 1e-6)) if dd[p] > 0 else np.zeros(3)
    else:
        v = d[par[names.index(b)] + '__v'].astype(np.float64); tv = cKDTree(v)
        j = kd.query(h)[1]; Dj = D[j] - T[j] * (D[j] @ T[j]); Dj /= np.linalg.norm(Dj)
        q = v[tv.query(h + RAISE_MM * Dj)[1]]                       # 背側へ上げた所に最も近い椎骨の表面
        inward = q - h; inward -= T[j] * (inward @ T[j]); inward /= max(np.linalg.norm(inward), 1e-9)
        mv = (q + 0.3 * inward) - h
    u = np.clip(np.linalg.norm(x - h, axis=1) / LT, 0, 1); w = 1 - u * u * (3 - 2 * u)
    d[k] = (x + w[:, None] * mv).astype(d[k].dtype)
    gaps.append(np.linalg.norm(mv))
np.savez_compressed(dst, **d)
print(mode, '付け根を動かした量 中央値 %.2f mm、最大 %.2f mm（%d 本）' % (np.median(gaps), np.max(gaps), len(gaps)))

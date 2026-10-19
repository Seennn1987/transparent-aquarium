"""膜をつないだ所（足首・手首の上）の段を、つないだ後の膜そのものから作り直す（記録 36 の案。2026-10-19）。

  cd <案の作業フォルダ> && python seam_patch.py <つないだ膜 skin_posed.npz> <出力 seam_patch.npz>

手足ごとに（展示の姿勢のモデルの座標）:
・つなぎ目の平面（足首・手首から下腿の向きへ CUT_MM = 1.0 mm 上。merge_feet.py と同じ）のまわりに、下腿の向きの箱をとる
  （下腿の向きに −2.5〜+1.5 mm、横は下腿の軸から 4 mm 以内の膜の範囲 + 0.6 mm）
・箱の中で、膜の内外（z 向きの光線の偶奇）から符号つき距離の場を 0.04 mm の格子で作り、つなぎ目の帯（平面から ±BAND_MM）だけを
  σ BLUR_MM でぼかす。帯の外と箱の端 0.3 mm はぼかさない（元の面のまま）
・面にする箱（パッチ）は切る箱より各面 0.2 mm 大きく、端は平面で閉じる。merge_seam.py（Blender）で、膜から切る箱を引いてパッチを足す。
  重なる 0.2 mm では両方とも元の面なので、差は格子 1 つ分（0.04 mm）以内
出力: 手足ごとの cut_<骨>（切る箱の 8 頂点）と patch_<骨>__v / __f（外向き）
"""
import os
import sys
import numpy as np
import scipy.ndimage as nd
from scipy.spatial import cKDTree
from skimage import measure

skin_p, out_p = sys.argv[1:3]
VOX = float(os.environ.get('SEAM_VOX_MM', '0.04')); BAND = float(os.environ.get('BAND_MM', '1.2')); BLUR = float(os.environ.get('BLUR_MM', '0.3'))
CUT_MM = float(os.environ.get('CUT_MM', '1.0')); LIMBS = os.environ.get('LIMBS', 'hL_foot,hR_foot,fL_hand,fR_hand').split(',')
T0, T1, PAD, OVL, EDGE = -2.5, 1.5, 0.6, 0.2, 0.3
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; k = float(P['k']); MM = k
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
def posed(n, x): M = P['M'][bn.index(n)]; return ct2m(x) @ M[:3, :3].T + M[:3, 3]
d = np.load('chameleon_body_ct.npz'); rn = [str(s) for s in d['rig__names']]
S = np.load(skin_p); V = S['v'].astype(np.float64); Fc = S['f']


def inside_grid(Vb, F, lo, shape, vox):
    """閉じた面の内側を z 向きの光線の偶奇で格子に求める（feet_skin.py と同じ）。"""
    T = Vb[F]; hi = lo + (np.array(shape) - 1) * vox
    # z の範囲では落とさない（箱の下の三角形との交差も数える。落とすと、箱の底を突き抜ける下腿で内外が逆になった）
    T = T[np.all((T.max(1)[:, :2] >= lo[:2] - vox) & (T.min(1)[:, :2] <= hi[:2] + vox), axis=1)]
    cnt = np.zeros(shape, np.int16)
    for p0, p1, p2 in T:
        mn = np.floor((np.minimum(np.minimum(p0, p1), p2) - lo) / vox).astype(int); mx = np.ceil((np.maximum(np.maximum(p0, p1), p2) - lo) / vox).astype(int)
        ia = np.arange(max(mn[0], 0), min(mx[0], shape[0] - 1) + 1); ib = np.arange(max(mn[1], 0), min(mx[1], shape[1] - 1) + 1)
        if len(ia) == 0 or len(ib) == 0: continue
        A, B = np.meshgrid(lo[0] + ia * vox, lo[1] + ib * vox, indexing='ij'); A = A.ravel(); B = B.ravel()
        dd = (p1[0] - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (p1[1] - p0[1])
        if abs(dd) < 1e-18: continue
        l1 = ((A - p0[0]) * (p2[1] - p0[1]) - (p2[0] - p0[0]) * (B - p0[1])) / dd; l2 = ((p1[0] - p0[0]) * (B - p0[1]) - (A - p0[0]) * (p1[1] - p0[1])) / dd
        m = (l1 >= 0) & (l2 >= 0) & (l1 + l2 <= 1)
        if not m.any(): continue
        z = p0[2] + l1[m] * (p1[2] - p0[2]) + l2[m] * (p2[2] - p0[2])
        kz = np.ceil((z - lo[2]) / vox).astype(int)
        ii = np.repeat(ia, len(ib))[m]; jj = np.tile(ib, len(ia))[m]; ok = (kz >= 0) & (kz < shape[2])
        np.add.at(cnt, (ii[ok], jj[ok], kz[ok]), 1)
        np.add.at(cnt, (ii[kz < 0], jj[kz < 0], np.zeros(int((kz < 0).sum()), int)), 1)
    return (np.cumsum(cnt, axis=2) % 2) == 1


out = {}
for n in LIMBS:
    side = n.split('_')[0]
    ankle = posed(n, d['rig__head'][rn.index(n)][None])[0]; knee = posed(side + '_lower', d['rig__head'][rn.index(side + '_lower')][None])[0]
    ax = ankle - knee; ax /= np.linalg.norm(ax); plane = ankle - ax * CUT_MM * MM
    e1 = np.cross(ax, [0, 0, 1.0]); e1 = e1 / np.linalg.norm(e1) if np.linalg.norm(e1) > 1e-6 else np.array([1.0, 0, 0]); e2 = np.cross(ax, e1)
    R = np.c_[e1, e2, ax]                                              # 箱の座標: (e1, e2, 下腿の向き)
    q = (V - plane) @ R / MM
    sel = (q[:, 2] > T0) & (q[:, 2] < T1) & (np.hypot(q[:, 0], q[:, 1]) < 4.0)
    lo_c = np.r_[q[sel, :2].min(0) - PAD, T0]; hi_c = np.r_[q[sel, :2].max(0) + PAD, T1]      # 切る箱 [mm]
    lo_p = lo_c - OVL; hi_p = hi_c + OVL                                                         # パッチの箱
    shape = tuple(np.ceil((hi_p - lo_p) / VOX).astype(int) + 1)
    print(n, 'box', np.round(hi_c - lo_c, 2), 'mm, grid', shape, flush=True)
    qb = (V - plane) @ R / MM                                          # 膜の頂点を箱の座標（mm）で
    INS = inside_grid(qb, Fc, lo_p, shape, VOX)
    sdf = (nd.distance_transform_edt(~INS) - nd.distance_transform_edt(INS)) * VOX            # [mm]、外で正
    G = np.stack(np.meshgrid(*[lo_p[i] + np.arange(shape[i]) * VOX for i in range(3)], indexing='ij'), -1)
    u = np.clip(1 - np.abs(G[..., 2]) / BAND, 0, 1); w = u * u * (3 - 2 * u)
    edge = np.minimum.reduce([G[..., i] - lo_p[i] for i in range(3)] + [hi_p[i] - G[..., i] for i in range(3)])
    w *= np.clip((edge - OVL - EDGE) / 0.2, 0, 1)                      # 箱の端（重なり + 0.3 mm）ではぼかさない
    f = (1 - w) * sdf + w * nd.gaussian_filter(sdf, BLUR / VOX)
    f = np.maximum(f, -edge + 2 * VOX)                                 # パッチの端を平面で閉じる
    vv, ff, _, _ = measure.marching_cubes(f, 0.0, spacing=(VOX,) * 3); vv = vv + lo_p
    vol = np.einsum('ij,ij->i', vv[ff[:, 0]], np.cross(vv[ff[:, 1]], vv[ff[:, 2]])).sum()
    if vol < 0: ff = ff[:, ::-1]                                       # 外向き
    e = np.sort(np.r_[ff[:, [0, 1]], ff[:, [1, 2]], ff[:, [2, 0]]], 1); _, ce = np.unique(e, axis=0, return_counts=True)
    corners = np.array([[a, b, c] for a in (lo_c[0], hi_c[0]) for b in (lo_c[1], hi_c[1]) for c in (lo_c[2], hi_c[2])])
    out['cut_' + n] = (plane + corners * MM @ R.T).astype(np.float64); out['frame_' + n] = np.r_[plane[None], R.T]; out['box_' + n] = np.r_[lo_p, hi_p]
    out['patch_' + n + '__v'] = (plane + vv * MM @ R.T).astype(np.float64); out['patch_' + n + '__f'] = ff.astype(np.int32)
    print(n, 'patch', len(vv), 'vertices', len(ff), 'faces, open edges', int((ce != 2).sum()), flush=True)
np.savez(out_p, **out); print('saved', out_p)

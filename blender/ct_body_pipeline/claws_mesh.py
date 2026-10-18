"""爪の鞘（角質）を、爪の骨（末節骨）のまわりに作り、chameleon_body_soft.npz に臓器の 1 つ（org_claw、ページでは Organ_claw）として
足す（計画書 C の記録 31 の案。2026-10-18）。CT は骨だけで、角質の爪は写っていない。

  python claws_mesh.py <骨.npz> <digit_labels.py の出力> <入力の soft.npz> <出力の soft.npz>

爪ごと（静止 = CT の座標）に:
・爪の骨の頂点から SHEATH_MM（仮 0.12 mm）外の面
・爪の骨の先から、先の向き（爪の骨の付け根の重心 → 先の頂点）へ TIP_MM（仮 0.5 mm）伸ばし、先へ細くなる（半径 → 0.02 mm）
・二つを合わせた形を 0.06 mm の格子で面にする（面を減らすと穴が開いたので減らさない）。重みは、その足（手）の骨に 1
"""
import os
import sys
import numpy as np
from scipy.spatial import cKDTree
from skimage import measure
import pyfqmr

bones_p, lab_p, soft_in, soft_out = sys.argv[1:5]
SHEATH_MM = float(os.environ.get('SHEATH_MM', '0.12')); TIP_MM = float(os.environ.get('TIP_MM', '0.5')); VOX = float(os.environ.get('CLAW_VOX', '0.06'))
FACES = int(os.environ.get('CLAW_FACES', '0')); AGG = int(os.environ.get('CLAW_AGG', '7'))
d = np.load(bones_p); L = np.load(lab_p)
bones = sorted({k.split('__')[0] for k in L.files})
V, F, WI = [], [], []; nv = 0
for bi, b in enumerate(bones):
    v = d[b + '__v'].astype(np.float64); lab = L[b + '__label']; claw = L[b + '__claw']; tip = L[b + '__tip']
    for k in range(1, 6):
        q = np.where(claw & (lab == k))[0]
        if len(q) < 10: continue
        P = v[q]; tq = tip[q]
        tip_pt = P[np.argmin(tq)]; base = P[tq >= np.percentile(tq, 80)].mean(0)
        ax = tip_pt - base; ax /= np.linalg.norm(ax)
        r0 = np.median(np.linalg.norm(P[tq < np.percentile(tq, 10)] - P[tq < np.percentile(tq, 10)].mean(0), axis=1)) + SHEATH_MM
        s = np.linspace(0, TIP_MM, 12)
        C = tip_pt + s[:, None] * ax; R = r0 + (0.02 - r0) * s / TIP_MM
        pad = max(R.max(), SHEATH_MM) + 4 * VOX                       # 格子の端で面が切れない（閉じていない辺が 54 本出た）
        lo = np.minimum(P.min(0), C.min(0)) - pad; hi = np.maximum(P.max(0), C.max(0)) + pad
        shape = tuple(np.ceil((hi - lo) / VOX).astype(int) + 1)
        G = np.stack(np.meshgrid(*[lo[i] + np.arange(shape[i]) * VOX for i in range(3)], indexing='ij'), -1).reshape(-1, 3)
        f1 = cKDTree(P).query(G, workers=-1)[0] - SHEATH_MM
        f2 = (np.linalg.norm(G[:, None, :] - C[None], axis=2) - R[None]).min(1)
        fld = np.minimum(f1, f2).reshape(shape)
        vv, ff, _, _ = measure.marching_cubes(fld, 0.0, spacing=(VOX, VOX, VOX)); vv = vv + lo
        if FACES > 0:
            simp = pyfqmr.Simplify(); simp.setMesh(vv, ff); simp.simplify_mesh(target_count=FACES, aggressiveness=AGG, preserve_border=True, verbose=False)
            vv, ff, _ = simp.getMesh()
        # いちばん大きい塊だけ残し（離れた小さな面が浮いた）、面を外向きに（符号つき体積が正）
        from scipy.sparse import coo_matrix; from scipy.sparse.csgraph import connected_components
        e = np.r_[ff[:, [0, 1]], ff[:, [1, 2]], ff[:, [2, 0]]]
        nc, lb = connected_components(coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), (len(vv), len(vv))), directed=False)
        keepv = lb == np.argmax(np.bincount(lb)); ff = ff[keepv[ff[:, 0]]]
        used = np.unique(ff); remap = -np.ones(len(vv), int); remap[used] = np.arange(len(used)); vv = vv[used]; ff = remap[ff]
        c0 = vv.mean(0)
        if np.einsum('ij,ij->i', vv[ff[:, 0]] - c0, np.cross(vv[ff[:, 1]] - c0, vv[ff[:, 2]] - c0)).sum() < 0: ff = ff[:, ::-1]
        e = np.sort(np.r_[ff[:, [0, 1]], ff[:, [1, 2]], ff[:, [2, 0]]], 1); _, ce = np.unique(e, axis=0, return_counts=True)
        if (ce != 2).any(): print('  閉じていない辺', int((ce != 2).sum()))
        V.append(vv); F.append(ff + nv); WI.append(np.full(len(vv), bi)); nv += len(vv)
        print('%s 指%d: 爪の鞘 長さ %.2f mm（骨の先から %.2f mm）、先の半径 %.2f mm、%d 面' % (
            b, k, np.ptp((vv - base) @ ax), TIP_MM, r0, len(ff)))
V = np.concatenate(V).astype(np.float32); F = np.concatenate(F).astype(np.int32); WI = np.concatenate(WI)
S = dict(np.load(soft_in))
S['org_claw__v'] = V; S['org_claw__f'] = F
S['org_claw__w_idx'] = np.stack([WI, WI], 1).astype(np.int16); S['org_claw__w_val'] = np.tile(np.array([1.0, 0.0], np.float32), (len(V), 1))
S['org_claw__names'] = np.array(bones)
np.savez_compressed(soft_out, **S); print('claws', len(V), 'vertices', len(F), 'faces ->', soft_out)

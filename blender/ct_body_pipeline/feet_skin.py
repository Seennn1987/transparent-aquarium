"""後ろ足の膜だけを細かい格子で作る（記録 31 の案。2026-10-18）。体の膜（skinbody.py、格子 0.25 mm）では指のあいだの切れ込みが
格子 1 つ分しかなく埋まったので、足だけを FEET_VOX_MM（既定 0.05 mm）で作り、merge_feet.py（Blender）で体の膜につなぐ。

  cd <案の作業フォルダ> && python feet_skin.py <digit_labels.py の出力> <出力 feet_posed.npz>

場は skinbody.py の LIMB_DIGITS と同じ（爪の骨を除く、指 DIGIT_T_MM・付け根 LIMB_T_FOOT、指のあいだの切れ込み CLEFT_MM、
骨から CLEFT_KEEP_MM より内は切らない）に加えて、同じ束の指は指先の離れた部分の外で幅 WEB_MM のなめらかな最小でつなぎ（水かき）、
付け根・下腿とは JOIN_MM でつなぎ、場を BLUR_MM でぼかす（骨のふくらみの写しの玉の連なりをならす）。それに下腿の骨の足首側 ANKLE_MM（既定 3 mm）を下腿の厚み（skinbody の LIMB_T の lower_h）で足し、
体の膜と重なる「のりしろ」にする。座標は展示の姿勢のモデルの座標（skin_posed.npz と同じ）。面は skin_posed.npz と同じ向き（内向き）にそろえる。
"""
import os
import sys
import numpy as np
from scipy.spatial import cKDTree
from skimage import measure
import scipy.ndimage as nd

lab_p, out_p = sys.argv[1:3]
VOX = float(os.environ.get('FEET_VOX_MM', '0.05')); ANKLE = float(os.environ.get('ANKLE_MM', '3.0'))
T_BASE = float(os.environ.get('LIMB_T_FOOT', '0.73')); T_DIG = float(os.environ.get('DIGIT_T_MM', '0.5'))   # 手の付け根も 0.73 mm（skinbody.py の LIMB_T['hand']）
LIMBS = os.environ.get('LIMBS', 'hL_foot,hR_foot').split(',')            # 手は LIMBS=fL_hand,fR_hand（記録 33）
T_LOWS = {'h': (1.25 + 1.36) / 2, 'f': (0.68 + 1.25) / 2}                   # skinbody.py の LIMB_T['lower_h']・['lower_f']
def lower_of(n): return n.split('_')[0] + '_lower'
CW = float(os.environ.get('CLEFT_MM', '0.6')); KEEP = float(os.environ.get('CLEFT_KEEP_MM', '0.15'))
R_WEB = float(os.environ.get('WEB_MM', '0.6')); R_JOIN = float(os.environ.get('JOIN_MM', '0.3')); BLUR = float(os.environ.get('BLUR_MM', '0.12'))
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; k = float(P['k']); MM = k
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
def posed(n, x): M = P['M'][bn.index(n)]; return ct2m(x) @ M[:3, :3].T + M[:3, 3]
d = np.load('chameleon_body_ct.npz'); L = np.load(lab_p)
V, F = [], []; nv = 0
for n in LIMBS:
    T_LOW = T_LOWS[n[0]]
    x = posed(n, d[n + '__v']); lab = L[n + '__label']; claw = L[n + '__claw']; free = L[n + '__free']; bundle = L[n + '__bundle']
    keep = ~claw
    trees = [cKDTree(x[keep & (lab == i)]) for i in range(6)]; frees = [free[keep & (lab == i)] for i in range(6)]
    low = posed(lower_of(n), d[lower_of(n) + '__v'])
    ankle = posed(n, d['rig__head'][[str(s) for s in d['rig__names']].index(n)][None])[0]
    low = low[np.linalg.norm(low - ankle, axis=1) < ANKLE * MM]; tl = cKDTree(low)
    pad = 1.5 * MM
    lo = np.minimum(x.min(0), low.min(0)) - pad; hi = np.maximum(x.max(0), low.max(0)) + pad
    shape = tuple(np.ceil((hi - lo) / (VOX * MM)).astype(int) + 1)
    print(n, 'grid', shape, '%.0f M' % (np.prod(shape) / 1e6), flush=True)
    fld = np.full(np.prod(shape), 1.0 * MM, np.float32)
    gi = np.stack(np.meshgrid(*[np.arange(s) for s in shape], indexing='ij'), -1).reshape(-1, 3)
    cap = 2.5 * MM                                   # 1.2 mm だと下腿（厚み 1.3 mm）の距離の上限で場が飛び、足首の上に格子の段が出た
    def smin(a, b, r):
        """なめらかな最小（r = 0 で普通の最小）。"""
        m = np.minimum(a, b); r = np.maximum(r, 1e-9)
        return m - r * np.log1p(np.exp(-np.abs(a - b) / r))
    for c0 in range(0, len(gi), 4_000_000):
        g = lo + gi[c0:c0 + 4_000_000] * VOX * MM
        D = np.full((len(g), 6), cap); Fr = np.zeros((len(g), 6))
        for i in range(6):
            dd, j = trees[i].query(g, workers=-1, distance_upper_bound=cap); ok = np.isfinite(dd); D[ok, i] = dd[ok]
            if i > 0: Fr[ok, i] = frees[i][j[ok]]
        o = np.argsort(D[:, 1:], axis=1)[:, :2] + 1; r = np.arange(len(g)); a, b = o[:, 0], o[:, 1]; da, db = D[r, a], D[r, b]
        same = bundle[a] == bundle[b]
        ramp = np.where(same, np.minimum(Fr[r, a], Fr[r, b]), np.clip((D[:, 0] - da) / MM, 0, 1))
        # 同じ束の指は、指先の離れた部分の外ではなめらかにつなぐ（水かき。本物は束の中の指が皮膚でつながる）
        fdig = smin(da - T_DIG * MM, db - T_DIG * MM, np.where(same, R_WEB * MM * (1 - ramp), 0))
        fall = smin(D[:, 0] - T_BASE * MM, fdig, R_JOIN * MM)
        cut = np.minimum((CW * MM - (db - da)) / 2 - (1 - ramp) * 10 * MM, da - KEEP * MM)
        fo = np.maximum(fall, cut)
        dl = tl.query(g, workers=-1, distance_upper_bound=cap)[0]; fl = np.where(np.isfinite(dl), dl, cap) - T_LOW * MM
        fld[c0:c0 + 4_000_000] = smin(fo, fl, R_JOIN * MM)
    # 表面の玉の連なり（骨のふくらみの写し）をならす
    fld = nd.gaussian_filter(fld.reshape(shape), BLUR / VOX).ravel()
    vv, ff, _, _ = measure.marching_cubes(fld.reshape(shape), 0.0, spacing=(VOX * MM,) * 3); vv = vv + lo
    vol = np.einsum('ij,ij->i', vv[ff[:, 0]], np.cross(vv[ff[:, 1]], vv[ff[:, 2]])).sum() / 6
    if vol > 0: ff = ff[:, ::-1]                                             # skin_posed.npz と同じ内向き
    e = np.sort(np.r_[ff[:, [0, 1]], ff[:, [1, 2]], ff[:, [2, 0]]], 1); _, ce = np.unique(e, axis=0, return_counts=True)
    print(n, len(vv), 'vertices', len(ff), 'faces, open edges', int((ce != 2).sum()), 'volume %.2f mm3' % (abs(vol) / MM ** 3), flush=True)
    V.append(vv); F.append(ff + nv); nv += len(vv)
np.savez_compressed(out_p, v=np.concatenate(V).astype(np.float32), f=np.concatenate(F).astype(np.int32))
print('saved', out_p)

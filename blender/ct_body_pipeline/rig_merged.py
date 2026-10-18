"""merge_feet.py でつないだ膜に、元の膜の重みを写して soft_rigged.npz と skin_posed.npz を書く（記録 31 の案。2026-10-18）。

  cd <案の作業フォルダ> && python rig_merged.py <merged_posed.npz> <元の soft_rigged.npz> <元の skin_posed.npz>

・重み: 展示の姿勢で、元の膜の最も近い頂点の重み（上位 3 本）。ただし足の膜として新しくできた頂点（元の膜に同じ位置の頂点が無く、足の骨から 4 mm 以内）は、
  足と下腿の骨のどちらに近いかで、skinbody.py と同じ exp(-(距離の差)/0.4 mm) の重み
・静止の形: skinbody.py と同じく、重みで混ぜた骨の行列の逆を掛ける
"""
import sys
import numpy as np
from scipy.spatial import cKDTree

mp, rig_p, posed_p = sys.argv[1:4]
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; k = float(P['k']); MM = k
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
def m2ct(m): m = np.asarray(m, float) / k; return np.stack([-m[..., 2], m[..., 0], -m[..., 1]], -1)
def posed(n, x): M = P['M'][bn.index(n)]; return ct2m(x) @ M[:3, :3].T + M[:3, 3]
d = np.load('chameleon_body_ct.npz')
Mz = np.load(mp); v = Mz['v'].astype(float); f = Mz['f']
R = np.load(rig_p); names = [str(x) for x in R['names']]; O = np.load(posed_p)
dj, j = cKDTree(O['v']).query(v, workers=-1)
new = dj > 1e-6 * MM                     # 足の膜として新しくできた頂点（元の膜の頂点はブール演算の後も同じ位置）
top = R['w_idx'][j].astype(int); tw = R['w_val'][j].astype(float)
import os
for limb in os.environ.get('LIMBS', 'hL_foot,hR_foot').split(','):          # 手は LIMBS=fL_hand,fR_hand（記録 33）
    side = limb.split('_')[0]
    xf = posed(limb, d[limb + '__v']); xl = posed(side + '_lower', d[side + '_lower__v'])
    df = cKDTree(xf).query(v, workers=-1)[0]; dl = cKDTree(xl).query(v, workers=-1)[0]
    m = new & (df < 4 * MM)               # 4 mm だけで選ぶと、右足に近い横腹の膜まで足の重みになり、書き出しで三角形が伸びた
    wf = 1.0 / (1.0 + np.exp(-(dl[m] - df[m]) / (0.4 * MM)))
    top[m] = 0; tw[m] = 0
    top[m, 0] = names.index(limb); tw[m, 0] = wf
    top[m, 1] = names.index(side + '_lower'); tw[m, 1] = 1 - wf
    print(side, '足の膜の頂点', int(m.sum()))
tw /= np.maximum(tw.sum(1, keepdims=True), 1e-9)
Ms = np.array([P['M'][bn.index(b)] for b in names])
Mv = np.einsum('vk,vkij->vij', tw, Ms[top])
vr = np.einsum('vij,vj->vi', np.linalg.inv(Mv), np.c_[v, np.ones(len(v))])[:, :3]
np.savez_compressed('soft_rigged.npz', v=m2ct(vr).astype(np.float32), f=f.astype(np.int32),
                    w_idx=top.astype(np.int16), w_val=tw.astype(np.float32), names=np.array(names))
np.savez_compressed('skin_posed.npz', v=v.astype(np.float32), f=f.astype(np.int32))
print('saved soft_rigged.npz, skin_posed.npz', len(v), 'vertices')

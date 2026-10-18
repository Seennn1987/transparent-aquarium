"""手・足の指の 2 つの束と、付け根（束が分かれる前）を頂点ごとに分ける（計画書 C の記録 30 の案。2026-10-18）。
skinbody.py の LIMB_CLEFT が読み、束と束のあいだの膜に切れ込みを入れる。

  python foot_bundles.py <骨.npz> <出力の束.npz> [図.png] [--bones=hL_foot,hR_foot]

骨ごとに、静止（CT の座標）で:
・いちばん大きい塊の頂点に、足首（骨組みの付け根に最も近い頂点）から面に沿った距離を付ける
・その距離の 0.2 mm ごとに、それより遠い頂点だけで面のつながりを数え、大きい塊（遠い側の 3% 以上）が初めて 2 つ以上に
  なった所を分かれ目（付け根 0 との境）とする
・指は、遠い側の大きい塊が NDIG（足 5、手 5）つになった所で 1 本ずつに分かれる。指の先の向き（分かれ目の重心から指の
  重心へ）で 2 つの束に分ける: 足は内側 2 本・外側 3 本（Diaz & Trainor 2015 の (1,2)(3,4,5)）、手は 3 本・2 本。
  分け方のうち、束の中の向きのばらつきが最も小さいものを採る
・分かれ目より遠い頂点は、最も近い指の束へ。主成分の向きや、最初に 2 つになった塊で分けると、開いた束が T 字・C 字に
  なっていたり、束の中の指が先に離れたりして、指 1 本と残りに分かれてしまった（2026-10-18）
・小さな塊（足根骨・種子骨など）は、最も近い大きい塊の頂点と同じ
"""
import sys
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

src, dst = sys.argv[1], sys.argv[2]
opts = [a for a in sys.argv[3:] if a.startswith('--')]; rest = [a for a in sys.argv[3:] if not a.startswith('--')]
fig = rest[0] if rest else None
BONES = ('hL_foot', 'hR_foot')
for o in opts:
    if o.startswith('--bones='): BONES = tuple(o.split('=', 1)[1].split(','))
d = np.load(src); names = [str(x) for x in d['rig__names']]
out = {}; panels = []
for b in BONES:
    v = d[b + '__v'].astype(np.float64); f = d[b + '__f']
    e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
    w = np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1)
    A = sparse.coo_matrix((w, (e[:, 0], e[:, 1])), (len(v), len(v))).tocsr(); A = A.maximum(A.T)
    nc, lab = connected_components(A, directed=False); m = lab == np.argmax(np.bincount(lab))
    wr = d['rig__head'][names.index(b)].astype(np.float64)
    c0 = v[m].mean(0); ax0 = np.linalg.svd(v[m] - c0, full_matrices=False)[2][0]
    im = np.where(m)[0]; i_w = im[np.argmin(np.linalg.norm(v[m] - wr, axis=1))]
    p = dijkstra(A, indices=i_w); p[~m] = 0
    label = np.zeros(len(v), np.int8); split = None; digits = None
    NDIG = 5
    def comps(g, frac):
        idx = np.where(m & (p > g))[0]; n2, l2 = connected_components(A[idx][:, idx], directed=False)
        cnt = np.bincount(l2); return idx, l2, np.where(cnt >= frac * len(idx))[0]
    for g in np.arange(1.0, p[m].max() - 1.0, 0.2):
        idx, l2, big = comps(g, 0.03)
        if split is None and len(big) >= 2: split = g
        if len(big) == NDIG: digits = [idx[l2 == c] for c in big]; break
    if split is None or digits is None:
        print('%s: 指が %d 本に分かれる所が見つからない。分けない' % (b, NDIG)); continue
    fork = v[m & (np.abs(p - split) < 0.3)].mean(0)
    dirs = np.array([(v[q].mean(0) - fork) / np.linalg.norm(v[q].mean(0) - fork) for q in digits])
    from itertools import combinations
    best = None
    for g1 in combinations(range(NDIG), 2):
        g2 = [i for i in range(NDIG) if i not in g1]; cost = 0
        for G in (list(g1), g2):
            mu = dirs[G].mean(0); cost += ((dirs[G] - mu / np.linalg.norm(mu)) ** 2).sum()
        if best is None or cost < best[0]: best = (cost, list(g1), g2)
    for k, G in enumerate((best[1], best[2]), 1):
        for i in G: label[digits[i]] = k
    far = m & (p > split) & (label == 0)
    kd = cKDTree(v[label > 0]); label[far] = label[label > 0][kd.query(v[far])[1]]
    j = cKDTree(v[m]).query(v[~m])[1]; label[~m] = label[m][j]
    ang = np.degrees(np.arccos(np.clip(dirs[best[1]].mean(0) @ dirs[best[2]].mean(0) / np.linalg.norm(dirs[best[1]].mean(0)) / np.linalg.norm(dirs[best[2]].mean(0)), -1, 1)))
    print('%s: 束の向きの開き %.0f°' % (b, ang))
    out[b] = label; out[b + '__split'] = np.float32(split)
    print('%s: 分かれ目 足首から面に沿って %.1f mm（最も遠い所 %.1f mm）、付け根 %d・束 1 %d・束 2 %d 頂点' % (
        b, split, p[m].max(), (label == 0).sum(), (label == 1).sum(), (label == 2).sum()))
    panels.append((b, v, label, ax0, c0))
np.savez(dst, **out)
if fig:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fg, axs = plt.subplots(1, max(len(panels), 1), figsize=(6 * max(len(panels), 1), 5), squeeze=False)
    for k, (b, v, label, ax0, c0) in enumerate(panels):
        U = np.linalg.svd(v - c0, full_matrices=False)[2]; P = (v - c0) @ U[:2].T
        ax = axs[0, k]; ax.scatter(P[:, 0], P[:, 1], c=label, s=0.2, cmap='brg'); ax.set_aspect('equal'); ax.set_title(b)
    fg.savefig(fig, dpi=70)

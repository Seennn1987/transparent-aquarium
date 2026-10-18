"""手・足の骨の頂点に、指ごとの印を付ける（計画書 C の記録 31 の案。2026-10-18）。skinbody.py の LIMB_DIGITS と claws_mesh.py が読む。

  python digit_labels.py <骨.npz> <出力.npz> [図.png] [--bones=hL_foot,hR_foot] [--free=3.0] [--claw=0.3]

骨ごとに、静止（CT の座標）で（足首・手首から面に沿った距離 s は foot_bundles.py と同じ）:
・指: s の 0.2 mm ごとに、それより遠い頂点の面のつながりを数え、大きい塊（3% 以上）が 5 つになった所の 5 つの塊。
  残りは付け根（0）。指の番号 1〜5 は塊の大きい順（解剖の番号ではない）
・束: 指の向きで 2 つにまとめる（foot_bundles.py と同じ。足は 2 本・3 本、Diaz & Trainor 2015 の (1,2)(3,4,5)）
・爪の骨（末節骨）: 指先（指の向きでいちばん先の頂点）から面に沿った距離で、骨の太さ（0.15 mm ごとの断面の半径の中央値）の
  指先から 0.8 mm より先で最初の山（最後の関節のふくらみ）の CLAW_MM 手前まで。長さは 1.0〜2.2 mm に収める（記録 33）。足の指の骨の数は 2・3・4・4・3 で（同じ論文）、どの指もいちばん先が爪の骨
・指先の離れた部分（free）: 指先から FREE_MM 以内。同じ束の指は、ここだけ膜を分ける（本物は束の中の指が皮膚でつながり、
  指先だけ 1 本ずつ分かれる。Diaz & Trainor 2015 図 1 B。FREE_MM は仮）
"""
import sys
import numpy as np
from itertools import combinations
from scipy import sparse
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

src, dst = sys.argv[1], sys.argv[2]
opts = dict(a[2:].split('=', 1) for a in sys.argv[3:] if a.startswith('--'))
rest = [a for a in sys.argv[3:] if not a.startswith('--')]
fig = rest[0] if rest else None
BONES = tuple(opts.get('bones', 'hL_foot,hR_foot').split(','))
FREE_MM = float(opts.get('free', '3.0')); CLAW_MM = float(opts.get('claw', '0.3'))
CLAW_MIN, CLAW_MAX = float(opts.get('clawmin', '1.0')), float(opts.get('clawmax', '2.2'))
d = np.load(src); names = [str(x) for x in d['rig__names']]
out = {}; panels = []
for b in BONES:
    v = d[b + '__v'].astype(np.float64); f = d[b + '__f']
    e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
    w = np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1)
    A = sparse.coo_matrix((w, (e[:, 0], e[:, 1])), (len(v), len(v))).tocsr(); A = A.maximum(A.T)
    nc, lab = connected_components(A, directed=False); m = lab == np.argmax(np.bincount(lab))
    wr = d['rig__head'][names.index(b)].astype(np.float64)
    im = np.where(m)[0]; p = dijkstra(A, indices=im[np.argmin(np.linalg.norm(v[m] - wr, axis=1))]); p[~m] = 0
    digits = None; split = None
    for g in np.arange(1.0, p[m].max() - 1.0, 0.2):
        idx = np.where(m & (p > g))[0]; n2, l2 = connected_components(A[idx][:, idx], directed=False)
        cnt = np.bincount(l2); big = np.where(cnt >= 0.03 * len(idx))[0]
        if split is None and len(big) >= 2: split = g
        if len(big) == 5: digits = [idx[l2 == c] for c in big[np.argsort(-cnt[big])]]; break
    if digits is None: print('%s: 指が 5 本に分かれる所が見つからない' % b); continue
    label = np.zeros(len(v), np.int8)
    for k, q in enumerate(digits, 1): label[q] = k
    # 分かれ目より遠い残りの頂点（指の付け根の近く）は最も近い指へ
    far = m & (p > split) & (label == 0)
    kd = cKDTree(v[label > 0]); label[far] = label[label > 0][kd.query(v[far])[1]]
    # 束
    fork = v[m & (np.abs(p - split) < 0.3)].mean(0)
    dirs = np.array([(v[q].mean(0) - fork) / np.linalg.norm(v[q].mean(0) - fork) for q in digits])
    best = None
    for g1 in combinations(range(5), 2):
        g2 = [i for i in range(5) if i not in g1]
        cost = sum(((dirs[G] - dirs[G].mean(0) / np.linalg.norm(dirs[G].mean(0))) ** 2).sum() for G in (list(g1), g2))
        if best is None or cost < best[0]: best = (cost, list(g1), g2)
    bundle = np.zeros(6, np.int8)
    for i in best[1]: bundle[i + 1] = 1
    for i in best[2]: bundle[i + 1] = 2
    # 爪の骨と指先
    claw = np.zeros(len(v), bool); free = np.zeros(len(v), np.float32); tip = np.zeros(len(v), np.float32)
    info = []
    for k, q in enumerate(digits, 1):
        q = np.where(label == k)[0]
        # 指先: 指の向き（分かれ目 → 指の重心）でいちばん先の頂点。足首から面に沿って最も遠い点にすると、左手の 1 本で指の途中を
        #   指先とし、爪の骨が指先から 5 mm 離れた（記録 33）
        tv = q[np.argmax(v[q] @ dirs[k - 1])]
        Aq = A[q][:, q]; dt = dijkstra(Aq, indices=int(np.where(q == tv)[0][0]))
        dt[~np.isfinite(dt)] = dt[np.isfinite(dt)].max()
        bins = np.arange(0, dt.max(), 0.15); rad = []
        for x0 in bins:
            qq = q[(dt >= x0) & (dt < x0 + 0.15)]
            rad.append(np.median(np.linalg.norm(v[qq] - v[qq].mean(0), axis=1)) if len(qq) >= 5 else np.nan)
        rad = np.array(rad); ok = (bins > 0.8) & ~np.isnan(rad)
        pk = [i for i in range(1, len(bins) - 1) if ok[i] and rad[i] >= np.nanmax(rad[max(0, i - 3):i + 4])]
        d_joint = bins[pk[0]] if pk else 2.0
        L_claw = float(np.clip(d_joint - CLAW_MM, CLAW_MIN, CLAW_MAX))   # 最後の関節の山が近すぎる・遠すぎる指（0.4 mm、5 mm）があった
        claw[q[dt < L_claw]] = True
        tip[q] = dt
        free[q] = np.clip((FREE_MM - dt) / 0.5, 0, 1)
        info.append('指%d 束%d 爪の骨 %.1f mm' % (k, bundle[k], L_claw))
    j = cKDTree(v[m]).query(v[~m])[1]
    for arr in (label, claw, free, tip): arr[~m] = arr[m][j]
    claw[~m] = False
    out[b + '__label'] = label; out[b + '__bundle'] = bundle; out[b + '__claw'] = claw; out[b + '__free'] = free; out[b + '__tip'] = tip
    print(b + ':', '、'.join(info))
    panels.append((b, v, label, claw))
np.savez(dst, **out)
if fig:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fg, axs = plt.subplots(1, len(panels), figsize=(7 * len(panels), 6), squeeze=False)
    for k, (b, v, label, claw) in enumerate(panels):
        U = np.linalg.svd(v - v.mean(0), full_matrices=False)[2]; P = (v - v.mean(0)) @ U[:2].T
        ax = axs[0, k]; ax.scatter(P[:, 0], P[:, 1], c=label, s=0.2, cmap='tab10', vmin=0, vmax=9)
        ax.scatter(P[claw, 0], P[claw, 1], c='k', s=0.3); ax.set_aspect('equal'); ax.set_title(b + ' (black = ungual)')
    fg.savefig(fig, dpi=70)

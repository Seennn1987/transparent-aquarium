"""手・足の指の 2 つの束をトングのように開く（計画書 C の記録 28 の案。2026-10-17）。

  python digits_open.py <入力の骨.npz> <出力の骨.npz> <片側の角度 [度]> [図.png] [--bones=fL_hand,fR_hand]

--bones: 開く骨（既定は手・足の 4 本）。記録 29（2026-10-18）の本番は手だけ（--bones=fL_hand,fR_hand）

CT の個体の手・足は、指の 2 つの束（カメレオンの指は 2 束に分かれて向かい合う）が手首の先で分かれ、指先どうしで再びくっついて閉じた輪に
なっている（つかんだまま保存された形。記録 27）。写真 06 の手・足は束が開いている。
骨（fL_hand、fR_hand、hL_foot、hR_foot）ごとに、静止（CT の座標）で:
・いちばん大きい塊の頂点を主成分に分け、第 1 主成分 = 手首から指先へ、第 3 主成分 = 輪の面の法線（輪は第 1・第 2 主成分の面にある）
・輪になっていない骨（2026-10-17 の CT では右足 hR_foot: 束がすでに開いている）は動かさない
・束の分かれ目: 手首（骨組みの付け根）に近い側で、第 2 主成分の向きに穴（輪の内側）が始まる所（第 1 主成分で穴の手首側の端）
・束の割り当て: 分かれ目より先で第 2 主成分が ±0.6 mm を超える頂点はその符号、残りは決まった頂点から面に沿って近い方
・開く: 束ごとに、分かれ目を軸（第 3 主成分の向き）にして、互いに離れる向きへ角度だけ回す。分かれ目の手首側 1.5 mm から指先側 1.0 mm で
  回す量をなめらかに 0 → 1 にする。小さな塊（手根骨・種子骨など）は、最も近い大きい塊の頂点と同じだけ動かす
"""
import sys
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import connected_components, dijkstra
from scipy.spatial import cKDTree

src, dst = sys.argv[1], sys.argv[2]
ANG = float(sys.argv[3])
opts = [a for a in sys.argv[4:] if a.startswith('--')]; rest = [a for a in sys.argv[4:] if not a.startswith('--')]
fig = rest[0] if rest else None
BONES = ('fL_hand', 'fR_hand', 'hL_foot', 'hR_foot')
for o in opts:
    if o.startswith('--bones='): BONES = tuple(o.split('=', 1)[1].split(','))
d = dict(np.load(src)); names = [str(x) for x in d['rig__names']]


def rot(axis, deg):
    a = axis / np.linalg.norm(axis); t = np.radians(deg); K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K


panels = []
for b in BONES:
    v = d[b + '__v'].astype(np.float64); f = d[b + '__f']
    e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]; w = np.linalg.norm(v[e[:, 0]] - v[e[:, 1]], axis=1)
    A = sparse.coo_matrix((w, (e[:, 0], e[:, 1])), (len(v), len(v))).tocsr(); A = A.maximum(A.T)
    nc, lab = connected_components(A, directed=False); big = np.argmax(np.bincount(lab)); m = lab == big
    wr = d['rig__head'][names.index(b)].astype(np.float64)
    c0 = v[m].mean(0); U, S, Vt = np.linalg.svd(v[m] - c0, full_matrices=False)
    ax0, ax1, ax2 = Vt
    if (wr - c0) @ ax0 > 0: ax0 = -ax0                            # 第 1 主成分を手首 → 指先に
    ax2 = np.cross(ax0, ax1)
    P = (v - c0) @ np.c_[ax0, ax1, ax2]
    # 束の分かれ目: 第 1 主成分の帯ごとに、第 2 主成分の向きの真ん中（|p1| < 0.4 mm）に頂点が無くなる最初の帯
    bins = np.arange(P[m, 0].min(), P[m, 0].max(), 0.2); split = None
    for x0 in bins:
        q = m & (P[:, 0] >= x0) & (P[:, 0] < x0 + 0.2)
        if q.sum() > 30 and (np.abs(P[q, 1]) < 0.4).sum() == 0 and (P[q, 1] > 0).any() and (P[q, 1] < 0).any():
            split = x0; break
    if split is None:
        print('%s: 束の分かれ目（輪の穴）が見つからない。輪になっていない（束がすでに開いている）ので動かさない' % b); continue
    # 束の割り当て
    # 分かれ目より先で第 2 主成分が ±0.6 mm を超える頂点はその符号。残り（くっついた指先、分かれ目の近く）は、決まった頂点から面に
    # 沿って近い方（束は 2〜3 本の指が重なるので、1 点からの距離だけでは分けきれなかった）
    lab_u = m & (P[:, 0] > split) & (P[:, 1] > 0.6); lab_l = m & (P[:, 0] > split) & (P[:, 1] < -0.6)
    Du = dijkstra(A, indices=np.where(lab_u)[0], min_only=True); Dl = dijkstra(A, indices=np.where(lab_l)[0], min_only=True)
    side = np.where(Du < Dl, 1.0, -1.0)
    sU = np.where(lab_u)[0][0]; sL = np.where(lab_l)[0][0]
    hinge = c0 + split * ax0
    t = np.clip((P[:, 0] - (split - 1.5)) / 2.5, 0, 1); t = t * t * (3 - 2 * t)
    # 小さな塊は、最も近い大きい塊の頂点の重みと向き
    kd = cKDTree(v[m]); j = kd.query(v[~m])[1]
    t[~m] = t[m][j]; side[~m] = side[m][j]
    out = v.copy()
    for sg in (1.0, -1.0):
        R = rot(ax2, sg * ANG)
        sel = side == sg
        moved = (v[sel] - hinge) @ R.T + hinge
        out[sel] = v[sel] + (moved - v[sel]) * t[sel][:, None]
    d[b + '__v'] = out.astype(d[b + '__v'].dtype)
    tipU = P[m & (side > 0), 0].max(); gap0 = np.linalg.norm(v[sU] - v[sL])
    Pn = (out - c0) @ np.c_[ax0, ax1, ax2]
    tip_i = [np.where(m & (side == s))[0][np.argmax(P[m & (side == s), 0])] for s in (1, -1)]
    print('%s: 分かれ目 第 1 主成分 %.1f mm、束の指先どうしの距離 %.2f → %.2f mm' % (b, split, np.linalg.norm(v[tip_i[0]] - v[tip_i[1]]), np.linalg.norm(out[tip_i[0]] - out[tip_i[1]])))
    panels.append((b, P, Pn, m, side, split))
np.savez_compressed(dst, **d)
if fig:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fg, axs = plt.subplots(2, max(len(panels), 1), figsize=(16, 7), squeeze=False)
    for k, (b, P, Pn, m, side, split) in enumerate(panels):
        for r, Q in enumerate((P, Pn)):
            ax = axs[r, k]; ax.scatter(Q[m, 0], Q[m, 1], c=side[m], s=0.2, cmap='coolwarm'); ax.axvline(split, color='k', lw=0.5)
            ax.set_aspect('equal'); ax.set_title(f'{b} {"before" if r == 0 else "after"}')
    fg.savefig(fig, dpi=70)

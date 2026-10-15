# 舌骨を作り直す（2026-10-15、計画書 C の記録 12・13）
#   使い方: python3 hyoid_rebuild.py 入力.npz 出力.npz   （strip_strays.py の後。ento_line.npy = entotrace.py の舌の芯の中心線）
#   1. 舌骨の骨 = 頭骨のメッシュの中の左右の第 1 角鰓骨（長さ 約 13.5 mm の 2 本の棒）だけにする。
#      これまで舌骨に入れていた胸の 5 本（A〜E、hyoid5.py と hyoid_relabel.py が移した棒）は外す: 舌骨の体から 10 mm 以上離れ、
#      生の CT で E の前の端は肋骨 07_L の骨の先に 0.8 mm で続き（向きの cos 0.99）、5 本は肋骨 4〜10 の腹の端の間にある
#      = 肋骨の腹側の部分が骨になったもの、と考える（仮）。肋骨は ribmodel2 で腹の正中まで骨として作り直してあるので、二重にしない
#      左の肩帯に 0.08 mm で触れる小さなかけら（1.6 mm）は fL_girdle へ戻す。ほかの 0.5 mm 未満のかけらは外す
#   2. 舌骨の軟骨（cart__、骨 'hyoid'）を足す:
#      舌内突起（舌の芯）: CT の薄い殻の管（外径 約 0.8 mm、長さ 23.6 mm、濃さ 約 40〜45）の中心線に沿う半径 0.4 mm の筒。
#        先の 2 mm を半径 0.2 mm へ細める（Herrel et al. 2001: 舌内突起は先の 2〜3 mm だけ細くなる）
#      基舌骨: 左右の第 1 角鰓骨の下の端を結ぶ、半径 0.35 mm の短い棒（Herrel et al. 2001: 強く小さくなった基舌骨。形と太さは仮）
#      角舌骨: 基舌骨の前の背側から、上へ前へ傾いて伸びる左右 1 対（Herrel et al. 2001: 軟骨だけで短い、横から見て上へ伸び前へ
#        傾く）。長さ 2.0 mm、半径 0.2 mm、向きは頭骨の枠で 前 0.5・上 0.8・横 ±0.3（すべて仮。CT には写らない）
import numpy as np, sys, json
import scipy.sparse as sp; from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
import scipy.ndimage as nd
src, dst = sys.argv[1], sys.argv[2]
d = dict(np.load(src))
def comps(v, f):
    A = sp.coo_matrix((np.ones(3 * len(f)), (f[:, [0, 1, 2]].ravel(), f[:, [1, 2, 0]].ravel())), shape=(len(v), len(v)))
    return connected_components(A, directed=False)[1]
def sub(v, f, keepv):
    idx = -np.ones(len(v), int); idx[keepv] = np.arange(keepv.sum()); ff = f[keepv[f[:, 0]]]
    return v[keepv], idx[ff]
def pc_len(x):
    m = x.mean(0); u = np.linalg.svd(x - m, full_matrices=False)[2][0]; t = (x - m) @ u
    return np.ptp(t), u, t
# ---- 1. 第 1 角鰓骨を頭骨のメッシュから取り出す ----
hv, hf = d['head__v'], d['head__f']; hl = comps(hv, hf); sz = np.bincount(hl)
cb = []
for c in np.argsort(-sz)[1:12]:
    x = hv[hl == c]; L = pc_len(x)[0]
    if 2000 <= sz[c] <= 8000 and L > 10: cb.append(c)
assert len(cb) == 2, cb
mcb = np.isin(hl, cb)
cbv, cbf = sub(hv, hf, mcb); d['head__v'], d['head__f'] = sub(hv, hf, ~mcb)
print('first ceratobranchials: %s vertices, lengths %s mm' % ([int((hl == c).sum()) for c in cb], [round(pc_len(hv[hl == c])[0], 1) for c in cb]))
# ---- 古い舌骨のかけら ----
ov, of = d['hyoid__v'], d['hyoid__f']; ol = comps(ov, of); osz = np.bincount(ol)
gk = cKDTree(d['fL_girdle__v'])
dropped = []
for c in range(len(osz)):
    x = ov[ol == c]; L = pc_len(x)[0] if len(x) > 3 else 0
    if gk.query(x)[0].min() < 0.3 and L < 3:
        gv, gf = sub(ov, of, ol == c); n0 = len(d['fL_girdle__v'])
        d['fL_girdle__v'] = np.concatenate([d['fL_girdle__v'], gv]).astype(np.float32)
        d['fL_girdle__f'] = np.concatenate([d['fL_girdle__f'], gf + n0]).astype(np.int32)
        print('to fL_girdle: %d vertices, length %.1f mm' % (len(x), L))
    else:
        dropped.append((int(osz[c]), round(float(L), 1)))
print('dropped from the old hyoid (vertices, length mm):', sorted(dropped, reverse=True))
d['hyoid__v'], d['hyoid__f'] = cbv.astype(np.float32), cbf.astype(np.int32)
# ---- 2. 軟骨 ----
F = np.load('skull_frame_ct.npy'); fwd, up, lat = F            # 頭骨の枠（CT の mm）: 前・背・横
# 第 1 角鰓骨の下の端（舌骨の体の側）: 2 本の棒の、もう一方の棒に近い端
ends = []
for c in cb:
    x = hv[hl == c]; L, u, t = pc_len(x); e0, e1 = x[t < t.min() + 0.5].mean(0), x[t > t.max() - 0.5].mean(0)
    ends.append((e0, e1))
(a0, a1), (b0, b1) = ends
pairs = [(np.linalg.norm(p - q), p, q) for p in (a0, a1) for q in (b0, b1)]
_, pa, pb = min(pairs, key=lambda z: z[0])
carts = []
# 舌内突起
E = nd.gaussian_filter1d(np.load('ento_line.npy'), 2, axis=0)
arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(E, axis=0), axis=1))]
keep = np.r_[0, np.where(np.diff(np.floor(arc / 0.5)) > 0)[0] + 1, len(E) - 1]; E = E[np.unique(keep)]
arc = np.r_[0, np.cumsum(np.linalg.norm(np.diff(E, axis=0), axis=1))]; Lt = arc[-1]
for i in range(len(E) - 1):
    sm = 0.5 * (arc[i] + arc[i + 1]); r = 0.4 if sm < Lt - 2.0 else 0.4 - 0.2 * (sm - (Lt - 2.0)) / 2.0
    carts.append((E[i], E[i + 1], r))
print('entoglossal process: %.1f mm, %d segments' % (Lt, len(E) - 1))
# 基舌骨
mid = 0.5 * (pa + pb)
carts.append((pa, mid, 0.35)); carts.append((mid, pb, 0.35))
print('basihyal: %.1f mm between the lower ends of the ceratobranchials' % np.linalg.norm(pa - pb))
# 角舌骨（仮）
for sgn in (1, -1):
    base = mid + fwd * 0.3 + up * 0.2 + lat * sgn * 0.5
    dr = 0.5 * fwd + 0.8 * up + 0.3 * sgn * lat; dr /= np.linalg.norm(dr)
    pts = [base + dr * s_ for s_ in np.linspace(0, 2.0, 5)]
    for i in range(4): carts.append((pts[i], pts[i + 1], 0.2))
d['cart__a'] = np.concatenate([d['cart__a'], np.array([c[0] for c in carts], np.float32)])
d['cart__b'] = np.concatenate([d['cart__b'], np.array([c[1] for c in carts], np.float32)])
d['cart__r'] = np.concatenate([d['cart__r'], np.array([c[2] for c in carts], np.float32)])
d['cart__bone'] = np.concatenate([d['cart__bone'], np.array(['hyoid'] * len(carts))])
np.savez_compressed(dst, **d)
json.dump(dict(ceratobranchial_lengths=[round(float(pc_len(hv[hl == c])[0]), 2) for c in cb], entoglossal_mm=round(float(Lt), 2),
               basihyal_mm=round(float(np.linalg.norm(pa - pb)), 2), ceratohyal_mm=2.0, dropped=dropped),
          open('hyoid_rebuild.json', 'w'), indent=1)
print('saved', dst, 'cartilage segments added', len(carts))

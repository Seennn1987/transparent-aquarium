# 骨端（長い骨の端の別の骨。成長板をはさんで骨幹に載る）を、載っている骨のメッシュへ移す（2026-10-17、計画書 C の記録 18・19）
#   使い方: python3 epiphysis_relabel.py 入力.npz 出力.npz   （hyoid_rebuild.py の後）
#   わけ: CT のラベルで、肘・膝・肩・股の骨端のいくつかが関節の向こうの骨に入っていた。展示の姿勢では関節の角度が CT と違うので、
#     骨端が向こうの骨と一緒に動いて関節から外へずれ、膜がそれを包んでこぶになった（図 joint_epiphyses.png）。
#     トカゲの長い骨は端に骨の骨端をつくる（Carter, Mikić & Padian 1998, Zool J Linn Soc 123:163–178）。カメレオンは膝蓋骨と
#     肘の種子骨を持たない（Regnault et al. 2016 J Anat; Regnault et al. 2017 J Morphol）ので、種子骨とは読まない
#   決め方: 手足の各メッシュの主の骨（上腕・大腿・肢帯は最大の成分 1 つ、前腕・下腿は 2 つ）以外の、頂点 150 以上の成分について、
#     各主の骨から 0.4 mm 以内にある頂点の数（触れている面の広さ）を数える。成長板の面は広く、関節の向こうの骨とは点で触れる。
#     ほかのメッシュの主の骨との触れ方が自分のメッシュの主の骨の CONTACT_RATIO 倍以上なら、そのメッシュへ移す
#   範囲: 肩・股（肢帯 ↔ 上腕・大腿）と肘・膝（上腕・大腿 ↔ 前腕・下腿）だけ。手首・足首は手根骨・足根骨（足根の近位 3 要素は 1 つに
#     癒合する: Diaz & Trainor 2015）が間にあり、骨端と見分けていないので動かさない（記録に残す）
import numpy as np, sys, json
import scipy.sparse as sp; from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree
src, dst = sys.argv[1], sys.argv[2]
d = dict(np.load(src))
CONTACT_MM, CONTACT_RATIO, MIN_VERTS = 0.4, 3.0, 150
def comps(v, f):
    M = sp.coo_matrix((np.ones(3 * len(f)), (f[:, [0, 1, 2]].ravel(), f[:, [1, 2, 0]].ravel())), shape=(len(v), len(v)))
    return connected_components(M, directed=False)[1]
def sub(v, f, keep):
    idx = -np.ones(len(v), int); idx[keep] = np.arange(keep.sum()); ff = f[keep[f[:, 0]] & keep[f[:, 1]] & keep[f[:, 2]]]
    return v[keep], idx[ff]
log = []; moves = []
for side in ('fL', 'fR', 'hL', 'hR'):
    segs = ['girdle', 'upper', 'lower']
    meshes = [f'{side}_{g}' for g in segs if f'{side}_{g}__v' in d]
    if side == 'hR' and 'hR_girdle__v' not in d and 'hL_girdle__v' in d: meshes = ['hL_girdle'] + meshes   # 腰帯は 1 つのメッシュ
    main, pieces = {}, []
    for n in meshes:
        v, f = d[n + '__v'], d[n + '__f']; lab = comps(v, f); sz = np.bincount(lab); order = np.argsort(-sz)
        nmain = 2 if n.endswith('lower') else 1
        for r, c in enumerate(order):
            if r < nmain: main[(n, c)] = cKDTree(v[lab == c])
            elif sz[c] >= MIN_VERTS and not (n == 'hL_girdle' and side == 'hR'): pieces.append((n, lab == c, c))
    for n, m, c in pieces:
        x = d[n + '__v'][m]; cnt = {}
        for (mn, mc), t in main.items():
            cnt.setdefault(mn, 0); cnt[mn] += int((t.query(x, distance_upper_bound=CONTACT_MM)[0] < CONTACT_MM).sum())
        own = cnt.get(n, 0); best = max((k for k in cnt if k != n), key=lambda k: cnt[k])
        rec = dict(piece=f'{n}#{c}', verts=int(len(x)), contact=cnt)
        if cnt[best] >= CONTACT_RATIO * max(own, 1) and cnt[best] > 50:
            rec['to'] = best; moves.append((n, m, best, c))
        log.append(rec); print(rec)
# まとめて移す（取り出す前の頂点の番号で）
take = {}
for n, m, to, c in moves: take.setdefault(n, []).append((m, to, c))
add = {}
for n, lst in take.items():
    v, f = d[n + '__v'], d[n + '__f']; rm = np.zeros(len(v), bool)
    for m, to, c in lst:
        add.setdefault(to, []).append(sub(v, f, m)); rm |= m
        print('move %s#%d (%d verts) -> %s' % (n, c, m.sum(), to))
    kv, kf = sub(v, f, ~rm); d[n + '__v'], d[n + '__f'] = kv.astype(np.float32), kf.astype(np.int32)
for to, lst in add.items():
    for pv, pf in lst:
        n0 = len(d[to + '__v'])
        d[to + '__v'] = np.concatenate([d[to + '__v'], pv]).astype(np.float32); d[to + '__f'] = np.concatenate([d[to + '__f'], pf + n0]).astype(np.int32)
np.savez_compressed(dst, **d)
json.dump(log, open('epiphysis_relabel.json', 'w'), indent=1)
print('saved', dst)

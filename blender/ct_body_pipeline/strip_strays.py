# 腹の中の、椎骨 v16 のラベルの細い棒 2 本（体の正中、腹へ 5〜15 mm、体軸 74〜99 mm、長さ 16 mm と 8 mm）を消す（2026-10-14）
#   有鱗目に腹肋骨は無く、カメレオンの骨格のどの骨にも当てはまらない。胃腸の中の餌（昆虫の脚など）か CT の切り分けの誤りと見る
#   （餌の昆虫の外骨格はアリザリンで赤く染まらないので、どちらでも標本では見えない）。仮
#   使い方: python3 strip_strays.py 入力.npz 出力.npz
import numpy as np, sys
import scipy.sparse as sp; from scipy.sparse.csgraph import connected_components
d = dict(np.load(sys.argv[1]))
v = d['v16__v']; f = d['v16__f']
A = sp.coo_matrix((np.ones(3 * len(f)), (f[:, [0, 1, 2]].ravel(), f[:, [1, 2, 0]].ravel())), shape=(len(v), len(v)))
nc, lab = connected_components(A, directed=False)
big = np.argmax(np.bincount(lab)); cb = v[lab == big].mean(0)
drop = [c for c in range(nc) if c != big and (lab == c).sum() >= 500 and np.linalg.norm(v[lab == c].mean(0) - cb) > 6]
assert len(drop) == 2, drop
keep = ~np.isin(lab, drop)
idx = -np.ones(len(v), int); idx[keep] = np.arange(keep.sum())
fk = f[keep[f[:, 0]]]
d['v16__v'] = v[keep].astype(np.float32); d['v16__f'] = idx[fk].astype(np.int32)
print('dropped from v16: %d vertices in %d pieces' % ((~keep).sum(), len(drop)))
np.savez_compressed(sys.argv[2], **d)

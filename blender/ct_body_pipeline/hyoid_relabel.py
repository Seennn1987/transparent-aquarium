# 舌骨の左の角が椎骨 v05 のメッシュに入っていた（CT のラベルの誤り）: v05 の連結成分のうち、
# 椎骨の本体から腹へ 13 mm 以上離れた細い棒（舌骨の右の角と左右対の位置）を、舌骨のメッシュへ移す
#   使い方: python3 hyoid_relabel.py 入力.npz 出力.npz
import numpy as np, sys
import scipy.sparse as sp; from scipy.sparse.csgraph import connected_components
src, dst = sys.argv[1], sys.argv[2]
d = dict(np.load(src))
v = d['v05__v']; f = d['v05__f']
A = sp.coo_matrix((np.ones(3 * len(f)), (f[:, [0, 1, 2]].ravel(), f[:, [1, 2, 0]].ravel())), shape=(len(v), len(v)))
nc, lab = connected_components(A, directed=False)
# 椎骨の本体（いちばん大きい成分）の重心から 10 mm 以上離れた、100 頂点以上の成分
big = np.argmax(np.bincount(lab)); cb = v[lab == big].mean(0)
move = [c for c in range(nc) if c != big and (lab == c).sum() >= 100 and np.linalg.norm(v[lab == c].mean(0) - cb) > 10]
assert len(move) == 1, move
mv = lab == move[0]
print('move from v05 to hyoid: %d vertices, centroid %.1f mm from the vertebral body' % (mv.sum(), np.linalg.norm(v[mv].mean(0) - cb)))
fm = mv[f[:, 0]]
def sub(vv, ff, keepv):
    idx = -np.ones(len(vv), int); idx[keepv] = np.arange(keepv.sum()); return vv[keepv], idx[ff]
v5, f5 = sub(v, f[~fm], ~mv)
vh, fh = sub(v, f[fm], mv)
d['v05__v'], d['v05__f'] = v5.astype(np.float32), f5.astype(np.int32)
n0 = len(d['hyoid__v'])
d['hyoid__v'] = np.concatenate([d['hyoid__v'], vh]).astype(np.float32)
d['hyoid__f'] = np.concatenate([d['hyoid__f'], fh + n0]).astype(np.int32)
np.savez_compressed(dst, **d)
print('saved', dst)

# 体腔の内臓（褐色の一塊）を、同じ全身 CT の軟部から取り出す。
#   肺: 体腔の背側の、空気で黒い大きな空洞（cavity_half.npy）。カメレオンの肺は体腔の背側にあり、腹側縁と尾側縁から
#       盲嚢（diverticula）が出る（Klaver 1977, Beaufortia 25:167–199。C. calyptratus は 7 本）。トカゲの肺は肝臓の背側で、
#       体腔の背壁に接する（Cassel 2014, VIN）。空洞は肺として扱い、内臓に入れない
#   内臓 = 胴（v03〜v21）の、その椎骨と前後 1 個の肋骨で囲まれた所（椎骨の枠の横・腹の面に写した肋骨の点の凸包の 0.5 mm 内側、
#          体軸より 1 mm 以上腹側）の中で、
#          肺・骨でなく、軟部の密度（20 以上の割合を σ 0.6 mm でぼかした値）が 0.3 以上の所。
#          手足の骨の方が近い所は外す（CT では手足が胴に押し付けられている）
#   いちばん大きな一塊だけを残す（計画書: 臓器には分けず、褐色の一塊）
#   変形・面・重みは膜と同じ（softvol2.py / softmesh2.py の考え方）。重みは体軸の骨（椎骨・肋骨）だけ
#   出力: viscera_rigged.npz（soft_rigged.npz と同じ形）
import numpy as np, scipy.ndimage as nd, json, os, time
from scipy.spatial import cKDTree, ConvexHull
from skimage import measure
import pyfqmr, ribrestore
t0 = time.time()
DENS = float(os.environ.get('VISCERA_DENSITY', '0.3'))
HULL_IN = 0.5 / 0.104      # 肋骨の凸包から 0.5 mm 内側（肋骨のまわりの筋肉を入れない）
BELOW_AXIS = 1.0 / 0.104   # 体軸から 1 mm 腹側より下
V = np.load('ct_ms50726_vol4.npz')['v']; B = np.load('B_h10.npy'); cav = np.load('cavity_half.npy')
names = json.load(open('bone_names.json')); SIDE = json.load(open('sides.json'))
def rename(n): return SIDE.get(n[:2], n[:2]) + n[2:] if n[:2] in SIDE else n
H = tuple(s // 2 for s in V.shape)
dens = nd.gaussian_filter((V >= 20).reshape(H[0], 2, H[1], 2, H[2], 2).mean((1, 3, 5)).astype(np.float32), 3.0)
P = np.argwhere(B > 0); L = B[tuple(P.T)].astype(np.int32)
isrib = (L >= 160) & (L < 202); isvert = (L >= 102) & (L < 160)
limb_labels = [int(l) for l, n in names.items() if n.startswith(('fA', 'fB', 'hA', 'hB')) and not n.endswith('girdle')]
islimb = np.isin(L, limb_labels)
print('labels', f'{time.time()-t0:.0f}s', flush=True)
bone_h = np.zeros(H, bool); bone_h[tuple(((P - 0.5) // 2).astype(int).T)] = True
cand = (dens >= DENS) & ~cav & ~nd.binary_dilation(bone_h, iterations=2)
Q = np.argwhere(cand); X = Q * 2 + 0.5
# 各点の椎骨: 体軸（axis5、0.1 mm 刻み）のいちばん近い点の弧長を、椎骨の境（J）で区切る
AX = np.load('axis5_s.npy') * 2 + 0.5; J = np.load('J.npy')
ai = cKDTree(AX).query(X, workers=-1)[1]; arc = ai * 0.1
kk = np.searchsorted(J, arc) + 1
mask = np.zeros(H, bool)
for k in range(3, 22):
    m = kk == k
    if not m.any(): continue
    ks = [k - 1, k, k + 1]
    sel = isrib & np.isin((L - 160) // 2 + 1, ks)
    if sel.sum() < 50: continue
    c, t, r, v = ribrestore.frame(k)
    p2 = np.stack([(P[sel] - c) @ r, (P[sel] - c) @ v], 1)
    q2 = np.stack([(X[m] - c) @ r, (X[m] - c) @ v], 1)
    eq = ConvexHull(p2).equations
    inside = np.ones(len(q2), bool)
    for e in eq: inside &= q2 @ e[:2] + e[2] <= -HULL_IN
    inside &= q2[:, 1] >= BELOW_AXIS          # 体軸より腹側だけ（背の筋肉を入れない）
    mask[tuple(Q[m][inside].T)] = True
    print('k', k, int(m.sum()), int(inside.sum()), f'{time.time()-t0:.0f}s', flush=True)
# 手足の骨の方が近い所を外す
kt_ax = cKDTree(P[isrib | isvert][::4]); kt_lb = cKDTree(P[islimb][::4])
Q = np.argwhere(mask); X = Q * 2 + 0.5
da = kt_ax.query(X, workers=-1)[0]; dl = kt_lb.query(X, workers=-1)[0]
mask[tuple(Q[dl < da].T)] = False
lab, n = nd.label(mask); sz = np.bincount(lab.ravel()); sz[0] = 0
mask = lab == sz.argmax()          # いちばん大きな一塊だけ（骨盤の近くの小さな塊は背側の筋肉で、内臓ではない）
print('viscera voxels', int(mask.sum()), 'volume mm3', round(float(mask.sum()) * 0.208 ** 3, 1), 'pieces', int((sz >= 200).sum()), f'{time.time()-t0:.0f}s')
np.save('viscera_half.npy', mask)
# 戻した空間へ（softvol2.py と同じ動き）
surf = B > 0; surf &= ~nd.binary_erosion(surf)
sm = surf[tuple(P.T)]; Ps = P[sm].astype(np.float64); Ls = L[sm]
rs = (Ls >= 160) & (Ls < 202)
disp = np.zeros_like(Ps); disp[rs] = ribrestore.restore(Ps[rs], Ls[rs]) - Ps[rs]
kt = cKDTree(Ps)
Q = np.argwhere(mask).astype(np.float64) * 2 + 0.5
d, j = kt.query(Q, k=24, workers=-1)
w = np.exp(-0.5 * (d * 0.104 / 1.0) ** 2)
R = Q + (w[..., None] * disp[j]).sum(1) / np.maximum(w.sum(1, keepdims=True), 1e-9)
lo = np.floor(R.min(0) / 2).astype(int) - 6; hi = np.ceil(R.max(0) / 2).astype(int) + 7
G = np.zeros(tuple(hi - lo), bool); G[tuple((np.round((R - 0.5) / 2).astype(int) - lo).T)] = True
G = nd.binary_closing(np.pad(G, 3), iterations=2)[3:-3, 3:-3, 3:-3]
G = nd.binary_fill_holes(G)
F = nd.gaussian_filter(np.pad(G, 3).astype(np.float32), 1.5)
v, f, _, _ = measure.marching_cubes(F, 0.5)
simp = pyfqmr.Simplify(); simp.setMesh(v.astype(np.float64), f.astype(np.int32))
simp.simplify_mesh(target_count=int(os.environ.get('VISCERA_FACES', '20000')), aggressiveness=7, preserve_border=True, verbose=False)
v, f, _ = simp.getMesh()
Vv = ((v - 3) + lo) * 2 + 0.5
# 重み: 体軸の骨だけ（戻した位置）
ax = isrib | isvert
Pr = P[ax].astype(np.float64); La = L[ax]
rr_ = (La >= 160) & (La < 202)
for l in np.unique(La[rr_]):
    m = La == l; Pr[m] = ribrestore.restore(Pr[m], np.full(int(m.sum()), l))
kr = cKDTree(Pr[::2]); Lr = La[::2]
d, j = kr.query(Vv, k=48, workers=-1); lab_k = Lr[j]
w = np.exp(-0.5 * (d * 0.104 / 2.0) ** 2)
labs = sorted(np.unique(Lr).tolist()); lid = {l: i for i, l in enumerate(labs)}
W = np.zeros((len(Vv), len(labs)), np.float32); li = np.vectorize(lid.get)(lab_k)
for c in range(48): np.add.at(W, (np.arange(len(Vv)), li[:, c]), w[:, c])
top = np.argsort(-W, 1)[:, :3]; tw = np.take_along_axis(W, top, 1); tw = tw / np.maximum(tw.sum(1, keepdims=True), 1e-9)
np.savez_compressed('viscera_rigged.npz', v=(Vv * 0.104).astype(np.float32), f=f.astype(np.int32),
                    w_idx=top.astype(np.int16), w_val=tw.astype(np.float32), names=np.array([rename(names[str(l)]) for l in labs]))
print('viscera mesh verts', len(Vv), 'faces', len(f), f'{time.time()-t0:.0f}s')

# 膜の作り直し 1/2: 軟部の体積を、肋骨を戻した空間（ribrestore）へ移し、骨ごとの持ち主を付ける。
#   入力: soft_solid_half.npy（softmesh.py の軟部。半分の解像度 0.208 mm、体の中の空洞は埋めてある）、B_h11.npy（骨ラベル）
#   1. 軟部の各ボクセルの持ち主 = 戻した空間で、いちばん近い骨のボクセルのラベル（重みと同じ空間で決める）
#   2. 動き = 近い骨のボクセル（24 点、σ 1 mm）の、肋骨の復元での動きの重み付き平均（softrig.py と同じ）。肋骨以外の骨は動かない
#   3. 戻した空間の格子へ置き、置いたときのすき間を閉じる
#   出力: soft2_vol.npz（own: 持ち主のラベル（0 = 外）、origin: 格子の原点（全解像度のボクセル座標）、bone: 戻した骨のボクセル（全解像度）、bone_lab）
import numpy as np, scipy.ndimage as nd, json, time
from scipy.spatial import cKDTree
import ribrestore
t0 = time.time()
S = np.load('soft_solid_half.npy'); B = np.load('B_h11.npy'); names = json.load(open('bone_names.json'))
P = np.argwhere(B > 0); L = B[tuple(P.T)].astype(np.int32)
ok = np.array([str(l) in names for l in np.unique(L)]); good = set(np.unique(L)[ok].tolist())
m = np.isin(L, list(good)); P = P[m]; L = L[m]
# 骨の表面のボクセルだけで十分（近さを測るため）
surf = B > 0; surf &= ~nd.binary_erosion(surf)
sm = surf[tuple(P.T)]; Ps = P[sm].astype(np.float64); Ls = L[sm]
isrib = (Ls >= 160) & (Ls < 202)
disp = np.zeros_like(Ps); disp[isrib] = ribrestore.restore(Ps[isrib], Ls[isrib]) - Ps[isrib]
print('bone surface voxels', len(Ps), 'rib', int(isrib.sum()), f'{time.time()-t0:.0f}s')
kt = cKDTree(Ps)
Q = np.argwhere(S).astype(np.float64) * 2 + 0.5            # 全解像度のボクセル座標
d, j = kt.query(Q, k=24, workers=-1)
own = Ls[j[:, 0]]
w = np.exp(-0.5 * (d * 0.104 / 1.0) ** 2)
move = (w[..., None] * disp[j]).sum(1) / np.maximum(w.sum(1, keepdims=True), 1e-9)
R = Q + move
print('soft voxels', len(Q), 'max move mm', round(float(np.linalg.norm(move, axis=1).max()) * 0.104, 2), f'{time.time()-t0:.0f}s')
# 戻した骨（全部のボクセル）
isr = (L >= 160) & (L < 202)
Pr = P.astype(np.float64).copy()
# 肋骨の全ボクセルの復元は重いので、ラベルごとに
for l in np.unique(L[isr]):
    mm = L == l; Pr[mm] = ribrestore.restore(Pr[mm], np.full(int(mm.sum()), l))
print('ribs restored', f'{time.time()-t0:.0f}s')
lo = np.floor(np.minimum(R.min(0), Pr.min(0)) / 2).astype(int) - 4
hi = np.ceil(np.maximum(R.max(0), Pr.max(0)) / 2).astype(int) + 5
shape = tuple(hi - lo)
own_g = np.zeros(shape, np.int16)
idx = np.round((R - 0.5) / 2).astype(int) - lo
# 持ち主は戻した空間の骨で決め直す（CT の位置で決めると、戻した肋骨のそばの軟部が手足の持ち物になることがある）
surf_r = sm.copy()
kr = cKDTree(Pr[surf_r]); own = L[surf_r][kr.query(R, workers=-1)[1]]
own_g[tuple(idx.T)] = own
# すき間を閉じる: 空いた所は、近くに置いたボクセルの持ち主で埋める
filled = own_g > 0
closed = nd.binary_closing(np.pad(filled, 3), iterations=2)[3:-3, 3:-3, 3:-3]
gap = closed & ~filled
if gap.any():
    _, ind = nd.distance_transform_edt(~filled, return_indices=True)
    own_g[gap] = own_g[tuple(ind[:, gap])]
print('grid', shape, 'filled', int(filled.sum()), 'gap filled', int(gap.sum()), f'{time.time()-t0:.0f}s')
np.savez_compressed('soft2_vol.npz', own=own_g, origin=lo * 2, bone=Pr.astype(np.float32), bone_lab=L.astype(np.int16))

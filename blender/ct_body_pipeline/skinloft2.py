# 膜の作り直し 3: CT で測った「断面の太さの表」から、展示の姿勢でなめらかな一枚の膜を作る。
#   CT の軟部は点々にしか写らない（体の内側の 62% が 0）ので、その表面をそのまま面にするとでこぼこが残り、
#   動かすと崩れて見える。形を太さの表にまとめ、表から膜を作り直す。
#   体軸（頸〜尾の先）: 背骨の軸（rig__axis、0.1 mm 刻み）に沿った断面ごとに、軸のまわりの角 θ（48 方向）の太さ。
#     太さ = その断面に入る軟部のボクセル（椎骨・肋骨・舌骨の持ち物）の、軸からの距離の 90% 点。軸に沿って σ 2 mm、角に σ 3 升でぼかす
#     断面は 0.5 mm ごと。ボクセルはいちばん近い軸の点の断面に入れる
#   頭: 頭骨の軸（後頭顆→吻端）のまわり、48 方向
#   四肢の骨（肢帯を含む）: 骨の軸のまわり、24 方向。骨の両端から 1 mm 先まで表を延ばす（関節で切れ目ができないように）
#   膜は骨を必ず包む: 升ごとの太さを、その升の骨の外側 + 0.3 mm 以上にする（ボクセルの少ない腹側で、肋骨が膜の外に出ていた）
#   中身の少ない升は近くの升で埋め、軸に沿って σ 1 mm、角の向きに σ 2 升でぼかす
#   展示の姿勢（POSE_JAR、dump_pose.py の変形）で「軸からの距離 − 太さ」を並べ、なめらかな最小（幅 0.4 mm）で一つにして面にする。
#   CT で胴に押し付けられていた手足も、展示の姿勢で離れた形で作られる。面は外さない
#   重み: 体軸は断面の位置で前後の椎骨に分け、近い肋骨にも分ける（呼吸用）。手足は部位の距離の差で、つながる骨だけを混ぜる
#   静止の形: 頂点を重みで混ぜた変形の逆で静止の姿勢へ戻す
#   出力: soft_rigged.npz（v は CT の mm、f、w_idx、w_val、names）、skin_posed.npz（展示の姿勢の形）
import numpy as np, scipy.ndimage as nd, json, os, time
from scipy.spatial import cKDTree
from skimage import measure
import pyfqmr
t0 = time.time()
Q = 90
VOX_MM = float(os.environ.get('LOFT_VOX_MM', '0.25'))
SMOOTH_MM = 0.4
z = np.load('soft2_vol.npz'); own = z['own'].astype(np.int32); lo = z['origin'] // 2
m2 = np.load('soft2_mask.npy')
names = json.load(open('bone_names.json')); SIDE = json.load(open('sides.json'))
def rename(n): return SIDE.get(n[:2], n[:2]) + n[2:] if n[:2] in SIDE else n
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; Mpose = P['M']; k = float(P['k'])
Hm = P['head']; Tm = P['tail']
d = np.load('chameleon_body_ct.npz')
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
def m2ct(m): m = np.asarray(m, float) / k; return np.stack([-m[..., 2], m[..., 0], -m[..., 1]], -1)
MM = k
def Mof(n): return Mpose[bn.index(n)]
def apply(M, x): return x @ M[:3, :3].T + M[:3, 3]
# 軟部のボクセル（戻した空間、モデル座標）と持ち主
idx = np.argwhere(m2 & (own > 0))
X = ct2m((((idx + lo) * 2 + 0.5) * 0.104))
on = np.array([rename(names.get(str(int(o)), '')) for o in np.unique(own[own > 0])])
omap = dict(zip(np.unique(own[own > 0]).tolist(), on.tolist()))
ow = np.array([omap.get(int(o), '') for o in own[tuple(idx.T)]])
is_axial = np.array([n.startswith(('v', 'rib', 'hL_girdle', 'hR_girdle')) or n == 'hyoid' for n in ow])   # 腰帯は体軸と一緒に動くので体軸に入れる
is_head = ow == 'head'
# 骨のボクセル（戻した位置）。膜は骨を必ず包む: 升ごとの太さを、骨の外側 + BONE_MARGIN 以上にする
BONE_MARGIN = 0.3
Xb = ct2m(z['bone'].astype(float) * 0.104)
bmap = {l: rename(names.get(str(int(l)), '')) for l in np.unique(z['bone_lab'])}
owb = np.array([bmap[int(l)] for l in z['bone_lab']])
print('soft voxels', len(X), 'axial', int(is_axial.sum()), 'head', int(is_head.sum()), f'{time.time()-t0:.0f}s')

def bone_table(rho, th, si, ns, nth, span=3):
    Rb = np.zeros((ns, nth))
    ti = ((th + np.pi) / (2 * np.pi) * nth).astype(int) % nth
    ok_ = (si >= 0) & (si < ns)
    np.maximum.at(Rb, (si[ok_], ti[ok_]), rho[ok_])
    Rb = nd.maximum_filter(Rb, size=(span, 3), mode=('nearest', 'wrap'))
    return nd.gaussian_filter1d(Rb, span / 3, axis=0, mode='nearest') if span > 3 else Rb
def with_bone(R, Rb, sig_s, sig_t):
    if Rb is None: return R
    R = np.maximum(R, np.where(Rb > 0, Rb + BONE_MARGIN * MM, 0))
    R = nd.gaussian_filter1d(nd.gaussian_filter1d(R, 1.0, axis=1, mode='wrap'), 1.0, axis=0, mode='nearest')
    return np.maximum(R, np.where(Rb > 0, Rb + 0.5 * BONE_MARGIN * MM, 0))
def table(rho, th, si, ns, nth, sig_s, sig_t):
    R = np.full((ns, nth), np.nan)
    ti = ((th + np.pi) / (2 * np.pi) * nth).astype(int) % nth
    key = si * nth + ti; o = np.argsort(key); ks = key[o]; rs = rho[o]
    u, st, c = np.unique(ks, return_index=True, return_counts=True)
    for kk, a0, cc in zip(u, st, c):
        if cc >= 4: R.flat[kk] = np.percentile(rs[a0:a0 + cc], Q)
    if np.isnan(R).all(): return None
    ind = nd.distance_transform_edt(np.isnan(R), return_distances=False, return_indices=True)
    R = R[tuple(ind)]
    return nd.gaussian_filter1d(nd.gaussian_filter1d(R, sig_t, axis=1, mode='wrap'), sig_s, axis=0, mode='nearest')

def lookup(R, fs, th):
    nth = R.shape[1]; ft = np.mod((th + np.pi) / (2 * np.pi) * nth - 0.5, nth)
    return nd.map_coordinates(np.concatenate([R, R[:, :1]], 1), [np.clip(fs, 0, R.shape[0] - 1), ft], order=1, mode='nearest')

# ---- 体軸 ----
C = ct2m(d['rig__axis']); Dv = np.asarray(d['rig__dorsal'], float); Dv = np.stack([Dv[:, 1], -Dv[:, 2], -Dv[:, 0]], -1)
J = np.asarray(d['rig__J'], float); step = float(d['rig__axis_step'])
T = np.gradient(C, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
Dd = Dv - T * (Dv * T).sum(1, keepdims=True); Dd /= np.linalg.norm(Dd, axis=1, keepdims=True)
E2 = np.cross(T, Dd)
arc = np.arange(len(C)) * step
SEC = 5                                   # 0.5 mm ごとの断面
xa = X[is_axial]
j = cKDTree(C).query(xa, workers=-1)[1]
q = xa - C[j]; a_ = (q * Dd[j]).sum(1); b_ = (q * E2[j]).sum(1)
NSA = (len(C) + SEC - 1) // SEC
RA = table(np.hypot(a_, b_), np.arctan2(b_, a_), j // SEC, NSA, 48, 4.0, 3.0)
selb = np.array([n.startswith(('v', 'rib', 'hL_girdle', 'hR_girdle')) or n == 'hyoid' for n in owb])
xb = Xb[selb]; jb = cKDTree(C).query(xb, workers=-1)[1]; qb = xb - C[jb]
ab = (qb * Dd[jb]).sum(1); bb_ = (qb * E2[jb]).sum(1)
# 肋骨の先どうしの間も腹の壁でつなぐ: 骨の外側を体軸に沿って 7.5 mm（肋骨 2 本分）の幅で最大にしてからならす
RA = with_bone(RA, bone_table(np.hypot(ab, bb_), np.arctan2(bb_, ab), jb // SEC, NSA, 48, span=15), 4.0, 3.0)
# 断面の椎骨: 弧長を椎骨の境（J）で区切る。境の前後は 2 つの椎骨の変形を混ぜる
vk = np.clip(np.searchsorted(J, arc), 1, len(J))            # 1..55
centre = np.array([0.5 * (J[kk - 1] + (J[kk] if kk < len(J) else arc[-1])) for kk in range(1, len(J) + 1)])
def vert_weights(s):
    i = np.clip(np.searchsorted(centre, s), 1, len(centre) - 1)
    w1 = np.clip((s - centre[i - 1]) / (centre[i] - centre[i - 1]), 0, 1)
    return i - 1, i, w1                    # 椎骨の番号（0 始まり）と、後ろの重み
va, vb, wb = vert_weights(arc)
MA = np.array([Mof(f'v{i+1:02d}') for i in range(len(J))])
Mst = (1 - wb)[:, None, None] * MA[va] + wb[:, None, None] * MA[vb]
Cp = np.einsum('nij,nj->ni', Mst[:, :3, :3], C) + Mst[:, :3, 3]
def rot(Mx, v):
    w = np.einsum('nij,nj->ni', Mx[:, :3, :3], v); return w / np.linalg.norm(w, axis=1, keepdims=True)
Tp = rot(Mst, T); Dp = rot(Mst, Dd); Dp = Dp - Tp * (Dp * Tp).sum(1, keepdims=True); Dp /= np.linalg.norm(Dp, axis=1, keepdims=True); E2p = np.cross(Tp, Dp)
print('axial table', RA.shape, f'{time.time()-t0:.0f}s')

# ---- 頭と四肢 ----
tubes = {}
def tube(name, Xs, nth, ext_mm, sig_t, Xbone=None):
    i = bn.index(name); h = Hm[i]; t = Tm[i] - h; L = np.linalg.norm(t); t /= L
    ref = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
    e1 = ref - t * (ref @ t); e1 /= np.linalg.norm(e1); e2 = np.cross(t, e1)
    q = Xs - h; s = q @ t; a = q @ e1; b = q @ e2
    ds = 0.5 * MM; s0 = min(np.percentile(s, 1), 0) - ext_mm * MM; s1 = max(np.percentile(s, 99), L) + ext_mm * MM
    ns = int(np.ceil((s1 - s0) / ds)); si = np.clip(((s - s0) / ds).astype(int), 0, ns - 1)
    R = table(np.hypot(a, b), np.arctan2(b, a), si, ns, nth, 2.0, sig_t)
    if R is not None and Xbone is not None and len(Xbone):
        qb = Xbone - h; sb = qb @ t; sib = ((sb - s0) / ds).astype(int)
        R = with_bone(R, bone_table(np.hypot(qb @ e1, qb @ e2), np.arctan2(qb @ e2, qb @ e1), sib, ns, nth), 2.0, sig_t)
    if R is not None: tubes[name] = (h, t, e1, e2, s0, ds, R)
tube('head', X[is_head], 48, 0.0, 2.0, Xb[owb == 'head'])
for n in bn:
    if n.startswith(('fR', 'fL', 'hR', 'hL')) and n not in ('hL_girdle', 'hR_girdle'):
        sel = ow == n
        # 肩帯は端を延ばさない（延ばすと、表の端の太さのまま円錐が突き出た）
        if sel.sum() >= 50: tube(n, X[sel], 24, 0.0 if n.endswith('_girdle') else 1.0, 2.0, Xb[owb == n])
print('tubes', list(tubes), f'{time.time()-t0:.0f}s')

def tube_posed(name):
    h, t, e1, e2, s0, ds, R = tubes[name]; M = Mof(name); Rm = M[:3, :3]
    return apply(M, h[None])[0], Rm @ t, Rm @ e1, Rm @ e2, s0, ds, R
def tube_dist(name, x):
    h, t, e1, e2, s0, ds, R = tube_posed(name)
    q = x - h; s = q @ t; rho = np.hypot(q @ e1, q @ e2); th = np.arctan2(q @ e2, q @ e1)
    fs = (s - s0) / ds - 0.5; over = np.maximum(np.abs(fs - np.clip(fs, 0, R.shape[0] - 1)) - 0.5, 0) * ds
    dd = rho - lookup(R, fs, th)
    return np.where(over > 0, np.maximum(dd, over), dd)
# 体軸: 細かい点（0.1 mm）で最も近い断面
kd_ax = cKDTree(Cp)
def axial_dist(x):
    dd, jj = kd_ax.query(x, workers=-1)
    q = x - Cp[jj]; along = (q * Tp[jj]).sum(1)
    a = (q * Dp[jj]).sum(1); b = (q * E2p[jj]).sum(1)
    r = lookup(RA, jj / SEC - 0.5 + 0.0, np.arctan2(b, a))
    end = ((jj == 0) & (along < 0)) | ((jj == len(Cp) - 1) & (along > 0))
    over = np.where(end, np.abs(along), 0)
    dd = np.hypot(a, b) - r
    return np.where(over > 0, np.maximum(dd, over), dd), jj

# ---- 場 ----
boxes = []
rmaxA = RA.max(); boxes += [Cp.min(0) - rmaxA, Cp.max(0) + rmaxA]
for nme in tubes:
    h, t, e1, e2, s0, ds, R = tube_posed(nme); a = h + t * s0; b = h + t * (s0 + ds * R.shape[0])
    boxes += [np.minimum(a, b) - R.max(), np.maximum(a, b) + R.max()]
boxes = np.array(boxes); gmin = boxes.min(0) - 2 * MM; gmax = boxes.max(0) + 2 * MM
vox = VOX_MM * MM; shape = tuple(np.ceil((gmax - gmin) / vox).astype(int) + 1)
print('grid', shape, f'{np.prod(shape)/1e6:.0f} M', f'{time.time()-t0:.0f}s')
kS = SMOOTH_MM * MM
acc = np.zeros(shape, np.float32)
def add(dist, g):
    acc[tuple(g.T)] += np.exp(-np.clip(dist, -20 * kS, 30 * kS) / kS).astype(np.float32)
def grid_pts(lo_, hi_):
    lo_i = np.maximum(((lo_ - gmin) / vox).astype(int), 0); hi_i = np.minimum(((hi_ - gmin) / vox).astype(int) + 1, np.array(shape))
    return np.stack(np.meshgrid(*[np.arange(p, q_) for p, q_ in zip(lo_i, hi_i)], indexing='ij'), -1).reshape(-1, 3)
# 体軸は区間に分けて（メモリのため）
for c0 in range(0, len(Cp), 100):
    seg = Cp[c0:c0 + 100]
    g = grid_pts(seg.min(0) - rmaxA - MM, seg.max(0) + rmaxA + MM)
    x = gmin + g * vox
    dist, jj = axial_dist(x)
    m = (jj >= c0) & (jj < c0 + 100)
    add(dist[m], g[m])
for nme in tubes:
    h, t, e1, e2, s0, ds, R = tube_posed(nme); a = h + t * s0; b = h + t * (s0 + ds * R.shape[0])
    g = grid_pts(np.minimum(a, b) - R.max() - MM, np.maximum(a, b) + R.max() + MM)
    add(tube_dist(nme, gmin + g * vox), g)
F = -kS * np.log(np.maximum(acc, 1e-30)); F = nd.gaussian_filter(F, 1.0)
print('field', f'{time.time()-t0:.0f}s')
v, f, _, _ = measure.marching_cubes(F, 0.0); v = gmin + v * vox
lab = None
simp = pyfqmr.Simplify(); simp.setMesh(v.astype(np.float64), f.astype(np.int32))
simp.simplify_mesh(target_count=int(os.environ.get('SOFT_FACES', '150000')), aggressiveness=7, preserve_border=True, verbose=False)
v, f, _ = simp.getMesh()
# 面のしわ・継ぎ目をならす（Taubin。体積がほとんど縮まない）
import scipy.sparse as sp
TAUBIN = int(os.environ.get('SKIN_TAUBIN', '20'))
E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]); E = np.concatenate([E, E[:, ::-1]])
A = sp.coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(len(v), len(v))).tocsr(); A.data[:] = 1
deg = np.asarray(A.sum(1)).ravel(); Lap = sp.diags(1 / np.maximum(deg, 1)) @ A
for _ in range(TAUBIN):
    v = v + 0.5 * (Lap @ v - v)
    v = v - 0.53 * (Lap @ v - v)
print('mesh', len(v), len(f), f'{time.time()-t0:.0f}s')
# ---- 重み ----
cols = ['AX'] + list(tubes)
D = np.zeros((len(v), len(cols)), np.float32)
D[:, 0], jv = axial_dist(v)
for c, nme in enumerate(cols[1:], 1): D[:, c] = tube_dist(nme, v)
ROOTV = {'fR': 6, 'fL': 5, 'hL': 23, 'hR': 23}
SEG = {'girdle': 0, 'upper': 1, 'lower': 2, 'hand': 3, 'foot': 3}
def joinable(a, b):
    if a == b: return True
    if 'AX' in (a, b):
        o = b if a == 'AX' else a
        return o == 'head' or o.endswith('_girdle') or (o.endswith('_upper') and o.split('_')[0][0] == 'h')
    if 'head' in (a, b): return False
    la, sa = a.split('_'); lb, sb = b.split('_')
    return la == lb and abs(SEG[sa] - SEG[sb]) <= 1
OK = np.array([[joinable(a, b) for b in cols] for a in cols])
prim = np.argmin(D, 1)
W = np.exp(-(D - D[np.arange(len(v)), prim][:, None]) / (0.4 * MM)); W[~OK[prim]] = 0
# 体軸の重みを椎骨へ。手足の付け根（上腕）は、付け根の椎骨と混ぜる
bones = [f'v{i+1:02d}' for i in range(len(J))] + list(tubes)
WB = np.zeros((len(v), len(bones)), np.float32)
ia, ib_, wb_ = va[jv], vb[jv], wb[jv]
np.add.at(WB, (np.arange(len(v)), ia), W[:, 0] * (1 - wb_)); np.add.at(WB, (np.arange(len(v)), ib_), W[:, 0] * wb_)
for c, nme in enumerate(cols[1:], 1): WB[:, len(J) + c - 1] += W[:, c]
# 胴の膜は、近い肋骨にも重みを分ける（呼吸で肋骨が動くと胴の膜も動く）。肋骨から 2 mm で半分ほど
ribn = sorted({n for n in owb if n.startswith('rib')})
bones += ribn
WB = np.concatenate([WB, np.zeros((len(v), len(ribn)), np.float32)], 1)
selr = np.array([n.startswith('rib') for n in owb])
Xr = Xb[selr][::3]; Lr_ = owb[selr][::3]
Mr = {n: Mof(n) for n in ribn}
Xr_p = np.concatenate([apply(Mr[n], Xr[Lr_ == n]) for n in ribn]); Lr_p = np.concatenate([np.full(int((Lr_ == n).sum()), i) for i, n in enumerate(ribn)])
dr, jr = cKDTree(Xr_p).query(v, workers=-1)
wr = 0.7 * np.exp(-0.5 * (dr / (2.0 * MM)) ** 2) * W[:, 0] / np.maximum(W.sum(1), 1e-9)   # 体軸の分の中だけ
axs = WB[:, :len(J)].sum(1); keep = 1 - wr
WB[:, :len(J)] *= keep[:, None]
np.add.at(WB, (np.arange(len(v)), len(J) + len(tubes) + Lr_p[jr]), wr * np.maximum(axs, 1e-9))
top = np.argsort(-WB, 1)[:, :3]; tw = np.take_along_axis(WB, top, 1); tw /= np.maximum(tw.sum(1, keepdims=True), 1e-9)
Ms = np.array([Mof(b) for b in bones])
Mv = np.einsum('vk,vkij->vij', tw, Ms[top])
vr = np.einsum('vij,vj->vi', np.linalg.inv(Mv), np.c_[v, np.ones(len(v))])[:, :3]
# 場は内側が負なので、marching_cubes の面は内向き。外向きにそろえる（Web で厚みを裏 − 表の深さで測るため）
f = f[:, ::-1]
np.savez_compressed('soft_rigged.npz', v=m2ct(vr).astype(np.float32), f=f.astype(np.int32),
                    w_idx=top.astype(np.int16), w_val=tw.astype(np.float32), names=np.array(bones))
np.savez_compressed('skin_posed.npz', v=v.astype(np.float32), f=f.astype(np.int32))
print('saved', f'{time.time()-t0:.0f}s')

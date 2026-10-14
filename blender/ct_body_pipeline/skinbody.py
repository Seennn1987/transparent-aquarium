# 膜の作り直し 5（段階 2、2026-10-14）: CT の軟部を形に使わず、展示の姿勢の骨から膜を作る
#   CT の個体は保存で縮んで押し付けられた体で（Klaver 1973: 保存したカメレオンの肺はよく縮む）、
#   その軟部から作った膜は波打ち、頭に余計な袋が付き、手足と胴の間に水かきができた。
#   ここでは形を骨（段階 1 で作り直した肋骨・軟骨を含む）だけから決める。
#   体軸（頸〜尾の先）: 体軸に直角な断面ごとに、断面の前後 HULL_WIN_MM の骨の点の「凸包」（断面の平面で）を取り、
#     軸からの向き 48 方向の半径の表にする。肋骨は輪なので、凸包 = 肋骨・軟骨の輪の外形。
#     左右は鏡で大きい方にそろえる（左右対称）。軸に沿って σ AX_SIG_MM でならす。
#     膜の厚み: 胴・頸は WALL_MM（仮。皮膚と腹の壁が薄いとして）。
#     尾: 尾椎の凸包 + 尾の肉の厚み。肉の厚みは CT の尾で測る（尾は保存で潰れにくいとして。
#     軟部の軸からの 90% 点 − 尾椎の凸包、の向きの中央値、断面ごと。σ 4 mm でならす）。尾は先へ細くなる一方
#   頭: 頭骨の軸（後頭顆→吻端）に直角な断面ごとに、頭骨と舌骨（喉の中）の点の凸包 + HEAD_WALL_MM（仮）。
#     凸包なので、下あごの間（喉）・眼窩・口はふさがり、トサカの横は平らな面になる
#   手足: skinloft3 と同じ（展示の姿勢の骨の表面から LIMB_T）。胴の外形は骨だけで決めるので、手足の付け根より先に水かきはできない
#   一つの面: 距離のなめらかな最小（幅 SMOOTH_MM）、marching cubes、減らす、Taubin でならす（skinloft3 と同じ）
#   重み・静止の形・出力の形式は skinloft3 と同じ（soft_rigged.npz、skin_posed.npz）
import numpy as np, scipy.ndimage as nd, json, os, time
from scipy.spatial import cKDTree, ConvexHull
from skimage import measure
import pyfqmr
t0 = time.time()
VOX_MM = float(os.environ.get('LOFT_VOX_MM', '0.25'))
SMOOTH_MM = 0.4
WALL_MM = float(os.environ.get('WALL_MM', '0.6'))          # 仮
HEAD_WALL_MM = float(os.environ.get('HEAD_WALL_MM', '0.4'))  # 仮
HULL_WIN_MM = float(os.environ.get("HULL_WIN_MM", "4.5"))   # 肋骨の間隔（約 4.7 mm）と同じくらい: 窓に肋骨がいつも 2 本入る
AX_SIG_MM = float(os.environ.get("AX_SIG_MM", "3.0"))
NTH = 48
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; Mpose = P['M']; k = float(P['k'])
Hm = P['head']; Tm = P['tail']
d = np.load('chameleon_body_ct.npz')                        # 段階 1 の骨（ribmodel2 の肋骨と軟骨）
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
def m2ct(m): m = np.asarray(m, float) / k; return np.stack([-m[..., 2], m[..., 0], -m[..., 1]], -1)
MM = k
def Mof(n): return Mpose[bn.index(n)]
def apply(M, x): return x @ M[:3, :3].T + M[:3, 3]
# ---- 骨の点（静止 = CT のモデル座標、と展示の姿勢）----
rest = {}
for n in bn:
    if n + '__v' in d.files: rest[n] = ct2m(d[n + '__v'])
# 軟骨: 1.5 mm の筒（a→b、半径 r）を点に
ca, cb, cr, cown = ct2m(d['cart__a']), ct2m(d['cart__b']), d['cart__r'] * MM, d['cart__bone']
cpts, clab = [], []
for a_, b_, r_, o_ in zip(ca, cb, cr, cown):
    t = b_ - a_; L = np.linalg.norm(t)
    if L < 1e-6: continue
    t = t / L
    ref = np.array([0, 0, 1.0]) if abs(t[2]) < 0.9 else np.array([1.0, 0, 0])
    e1 = np.cross(t, ref); e1 /= np.linalg.norm(e1); e2 = np.cross(t, e1)
    s = np.linspace(0, L, max(int(L / (0.15 * MM)), 2)); ph = np.linspace(0, 2 * np.pi, 12, endpoint=False)
    p = a_ + s[:, None, None] * t + r_ * (np.cos(ph)[None, :, None] * e1 + np.sin(ph)[None, :, None] * e2)
    cpts.append(p.reshape(-1, 3)); clab += [str(o_)] * p.reshape(-1, 3).shape[0]
cpts = np.concatenate(cpts); clab = np.array(clab)
rest_cart = {n: cpts[clab == n] for n in np.unique(clab)}
def posed(n):
    x = rest[n] if n in rest else np.zeros((0, 3))
    if n in rest_cart: x = np.concatenate([x, rest_cart[n]])
    return apply(Mof(n), x)
AXN = [n for n in bn if n.startswith(('v', 'rib')) or n in ('fR_girdle', 'fL_girdle', 'hL_girdle', 'hR_girdle', 'hyoid', 'head')]
PX = {n: posed(n) for n in AXN if n in rest}
print('bones', len(PX), 'cartilage points', len(cpts), f'{time.time()-t0:.0f}s', flush=True)

def ray_hull(pts2, nth):
    """凸包（2D）の、原点から向き θ への半径。原点が外なら、向きの升ごとの最大で代える"""
    th = (np.arange(nth) + 0.5) / nth * 2 * np.pi - np.pi; u = np.stack([np.cos(th), np.sin(th)], 1)
    out = np.zeros(nth)
    if len(pts2) < 3: return out
    try: h = ConvexHull(pts2)
    except Exception: return out
    V = pts2[h.vertices]; Q = np.roll(V, -1, 0); E = Q - V
    cr = lambda a, b: a[..., 0] * b[..., 1] - a[..., 1] * b[..., 0]
    den = cr(u[:, None, :], E[None])                         # (nth, ne)
    r = cr(V[None], E[None]) / np.where(np.abs(den) < 1e-12, np.nan, den)
    # 辺の上の点か: p = r u、t = cr(p − V, u)/cr(E, u) が 0..1
    p = r[..., None] * u[:, None, :]
    tt = cr(p - V[None], u[:, None, :]) / np.where(np.abs(cr(E[None], u[:, None, :])) < 1e-12, np.nan, cr(E[None], u[:, None, :]))
    ok = (r > 0) & (tt >= -1e-6) & (tt <= 1 + 1e-6)
    r = np.where(ok, r, -np.inf).max(1)
    if not np.isfinite(r).all():                             # 原点が外
        ang = np.arctan2(pts2[:, 1], pts2[:, 0]); ti = ((ang + np.pi) / (2 * np.pi) * nth).astype(int) % nth
        rr = np.zeros(nth); np.maximum.at(rr, ti, np.hypot(pts2[:, 0], pts2[:, 1])); r = np.where(np.isfinite(r), r, rr)
    return r
def hull_table(a, b, si, ns, win):
    """断面 s の表 = 断面 s−win..s+win の点の凸包。点は先に (断面, 96 向き) の最も外の点に減らす"""
    th = np.arctan2(b, a); rho = np.hypot(a, b); ti = ((th + np.pi) / (2 * np.pi) * 96).astype(int) % 96
    key = si * 96 + ti; o = np.lexsort((-rho, key)); ks = key[o]
    first = np.r_[True, ks[1:] != ks[:-1]]; o = o[first]
    A, B, S = a[o], b[o], si[o]
    order = np.argsort(S); A, B, S = A[order], B[order], S[order]
    st = np.searchsorted(S, np.arange(ns + 1))
    R = np.zeros((ns, NTH))
    for s in range(ns):
        i0 = st[max(s - win, 0)]; i1 = st[min(s + win + 1, ns)]
        if i1 - i0 >= 3: R[s] = ray_hull(np.stack([A[i0:i1], B[i0:i1]], 1), NTH)
    return R
def lookup(R, fs, th):
    nth = R.shape[1]; ft = np.mod((th + np.pi) / (2 * np.pi) * nth - 0.5, nth)
    return nd.map_coordinates(np.concatenate([R, R[:, :1]], 1), [np.clip(fs, 0, R.shape[0] - 1), ft], order=1, mode='nearest')
def fill_zero(R):
    """点の無い断面（0）を、軸に沿って近い断面の値で埋める"""
    z = (R <= 0).all(1)
    if z.all() or not z.any(): return R
    ind = nd.distance_transform_edt(z, return_distances=False, return_indices=True)[0]
    return R[ind]

# ---- 体軸の枠（静止と展示の姿勢）: skinloft3 と同じ ----
C = ct2m(d['rig__axis']); Dv = np.asarray(d['rig__dorsal'], float); Dv = np.stack([Dv[:, 1], -Dv[:, 2], -Dv[:, 0]], -1)
J = np.asarray(d['rig__J'], float); step = float(d['rig__axis_step'])
T = np.gradient(C, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
Dd = Dv - T * (Dv * T).sum(1, keepdims=True); Dd /= np.linalg.norm(Dd, axis=1, keepdims=True)
E2 = np.cross(T, Dd)
arc = np.arange(len(C)) * step
SEC = 5; NSA = (len(C) + SEC - 1) // SEC; secmm = SEC * step
vk = np.clip(np.searchsorted(J, arc), 1, len(J))
centre = np.array([0.5 * (J[kk - 1] + (J[kk] if kk < len(J) else arc[-1])) for kk in range(1, len(J) + 1)])
def vert_weights(s):
    i = np.clip(np.searchsorted(centre, s), 1, len(centre) - 1)
    w1 = np.clip((s - centre[i - 1]) / (centre[i] - centre[i - 1]), 0, 1)
    return i - 1, i, w1
va, vb, wb = vert_weights(arc)
MA = np.array([Mof(f'v{i+1:02d}') for i in range(len(J))])
Mst = (1 - wb)[:, None, None] * MA[va] + wb[:, None, None] * MA[vb]
Cp = np.einsum('nij,nj->ni', Mst[:, :3, :3], C) + Mst[:, :3, 3]
def rot(Mx, v):
    w = np.einsum('nij,nj->ni', Mx[:, :3, :3], v); return w / np.linalg.norm(w, axis=1, keepdims=True)
Tp = rot(Mst, T); Dp = rot(Mst, Dd); Dp = Dp - Tp * (Dp * Tp).sum(1, keepdims=True); Dp /= np.linalg.norm(Dp, axis=1, keepdims=True); E2p = np.cross(Tp, Dp)
st_tail_ax = int(np.ceil(J[23] / secmm))                     # 最初の尾椎（v24）の頭の断面（体軸だけの番号）
# ---- 頭から尾の先までの一本の軸（展示の姿勢）: 吻端 → 後頭顆（頭骨の軸）→ 体軸の始まり → 尾の先 ----
#   頭と体軸を別々の膜にすると、継ぎ目に襟・ひだができた（skinbody_v1）。一本の軸の断面にして、頸は軸に沿ってならす
ih = bn.index('head'); Mh = Mof('head')
h0 = Hm[ih]; th_ = Tm[ih] - h0; th_ /= np.linalg.norm(th_)
hP = apply(Mh, h0[None])[0]; tP = Mh[:3, :3] @ th_                 # 後頭顆、吻端への向き
sk = (PX['head'] - hP) @ tP; smax = sk.max() + 0.3 * MM
dstep = step * MM                                                  # 軸の点の間隔（モデル座標、体軸と同じ 0.1 mm）
sH = np.arange(smax, 0, -dstep)                                    # 吻端 → 後頭顆
gap = np.linalg.norm(Cp[0] - hP); nbr = max(int(np.ceil(gap / dstep)), 1)
bri = hP + (Cp[0] - hP) * (np.arange(nbr) / nbr)[:, None]
pre = np.concatenate([hP + tP * sH[:, None], bri])
npad = (-len(pre)) % SEC
if npad: pre = np.concatenate([hP + tP * (smax + dstep * np.arange(npad, 0, -1))[:, None], pre])
NH = len(pre); OFF = NH // SEC
tdir = Cp[-1] - Cp[-20]; tdir /= np.linalg.norm(tdir)
ext = Cp[-1] + tdir * (dstep * np.arange(1, int(1.0 / step) + 1))[:, None]      # 尾の先の椎骨は体軸の終わりより先まである: 1 mm 延ばす
Cc = np.concatenate([pre, Cp, ext])
# 姿勢の体軸は椎骨ごとの変形を混ぜたもので、椎骨の長さ（約 4 mm）ごとに軸と向きが小さく揺れる。揺れは膜の輪の縞になったので、
# 軸の点を σ 1.5 mm、背の向きを σ 3 mm でならす（表もならした軸で作るので、骨との関係は変わらない）
Cc = nd.gaussian_filter1d(Cc, 1.5 / step, axis=0, mode='nearest')
Tc = np.gradient(Cc, axis=0); Tc /= np.linalg.norm(Tc, axis=1, keepdims=True)
Tc[:NH - nbr] = -tP                                                 # 頭の部分は頭骨の軸（尾の向きが正）
Tc = nd.gaussian_filter1d(Tc, 1.5 / step, axis=0, mode='nearest'); Tc /= np.linalg.norm(Tc, axis=1, keepdims=True)
Dc = np.concatenate([np.repeat(Dp[:1], NH, 0), Dp, np.repeat(Dp[-1:], len(ext), 0)])
Dc = nd.gaussian_filter1d(Dc, 3.0 / step, axis=0, mode='nearest')
Dc = Dc - Tc * (Dc * Tc).sum(1, keepdims=True); Dc /= np.linalg.norm(Dc, axis=1, keepdims=True); Ec = np.cross(Tc, Dc)
NSC = (len(Cc) + SEC - 1) // SEC; st_tail = st_tail_ax + OFF
print('one axis: head part %.1f mm, bridge %.2f mm, sections %d' % (NH * dstep / MM, gap / MM, NSC), flush=True)
kd_ax = cKDTree(Cc)
# ---- 断面の表（展示の姿勢の骨すべて: 頭骨・舌骨・椎骨・肋骨・軟骨・肩帯・腰帯）----
xa = np.concatenate([PX[n] for n in PX]); na_ = np.concatenate([np.full(len(PX[n]), n) for n in PX])
jj = kd_ax.query(xa, workers=-1)[1]; q = xa - Cc[jj]
a_ = (q * Dc[jj]).sum(1); b_ = (q * Ec[jj]).sum(1); sec = jj // SEC
win = int(round(HULL_WIN_MM / secmm))
R_w = hull_table(a_, b_, sec, NSC, win)                            # 胴: 肋骨 2 本が入る広い窓
R_n = hull_table(a_, b_, sec, NSC, 2)                              # 頭・尾: 1 mm の窓
R_w, R_n = fill_zero(R_w), fill_zero(R_n)
def sm(R, sig_mm): return nd.gaussian_filter1d(nd.gaussian_filter1d(R, 1.0, axis=1, mode='wrap'), sig_mm / secmm, axis=0, mode='nearest')
ss_c = np.arange(NSC)
# 頭（後頭顆まで）は細かい窓・弱いならし、頸（後頭顆 → 肩 U0）で胴の作り方へ移る。尾の始まりから先は細かい窓
s_occ = (NH - nbr) / SEC; s_sh = OFF + 9.5 / secmm
wt = np.clip((ss_c - s_occ) / max(s_sh - s_occ, 1), 0, 1)          # 0 = 頭、1 = 胴
wtail = np.clip((ss_c - st_tail) / (3.0 / secmm) + 0.5, 0, 1)
# 胴: 窓の凸包を、軸に沿って窓の幅でさらに最大にしてからならす（上の包み）。ならしただけだと肋骨の所で表が肋骨より低くなり、
# 骨の床（下）で肋骨ごとの輪の縞が出た
R_wm = nd.maximum_filter1d(R_w, size=2 * win + 1, axis=0, mode='nearest')
def sm_above(R, sig_mm, n=6):
    # ならしても下（R）より低くならないように: 最大を取ってならす、を繰り返す（出っ張りは σ の幅のなめらかなふくらみになる）
    X = sm(R, sig_mm)
    for _ in range(n): X = sm(np.maximum(X, R), sig_mm)
    return np.maximum(X, R)
RA_head = sm_above(R_n, 0.7); RA_trunk = sm_above(R_wm, AX_SIG_MM); RA_tail = sm_above(R_n, 1.5)
RA = ((1 - wt) * 1)[:, None] * RA_head + (wt * (1 - wtail))[:, None] * RA_trunk + (wt * wtail)[:, None] * RA_tail
RA = np.maximum(RA, RA[:, ::-1])                                   # 左右対称（大きい方）
print('hull table', RA.shape, 'max %.1f mm' % (RA.max() / MM), f'{time.time()-t0:.0f}s', flush=True)
# ---- 尾の肉の厚み（CT の尾で測る。静止の体軸の枠）----
z = np.load('soft2_vol.npz'); own = z['own'].astype(np.int32); lo = z['origin'] // 2
m2 = np.load('soft2_mask.npy')
names = json.load(open('bone_names.json')); SIDE = json.load(open('sides.json'))
def rename(n): return SIDE.get(n[:2], n[:2]) + n[2:] if n[:2] in SIDE else n
idx = np.argwhere(m2 & (own > 0))
omap = {int(o): rename(names.get(str(int(o)), '')) for o in np.unique(own[own > 0])}
ow = np.array([omap.get(int(o), '') for o in own[tuple(idx.T)]])
tailv = {f'v{i:02d}' for i in range(24, 56)}
selt = np.isin(ow, list(tailv))
Xs = ct2m((((idx[selt] + lo) * 2 + 0.5) * 0.104)); del idx, own, m2
kd_r = cKDTree(C)
js = kd_r.query(Xs, workers=-1)[1]; qs = Xs - C[js]
as_ = (qs * Dd[js]).sum(1); bs_ = (qs * E2[js]).sum(1)
xr = np.concatenate([rest[n] for n in tailv if n in rest]); jr = kd_r.query(xr, workers=-1)[1]; qr = xr - C[jr]
RHr = hull_table((qr * Dd[jr]).sum(1), (qr * E2[jr]).sum(1), jr // SEC, NSA, 2)
# 軟部の 90% 点（断面 × 向き、4 点以上の升）
ss = js // SEC; th = np.arctan2(bs_, as_); ti = ((th + np.pi) / (2 * np.pi) * NTH).astype(int) % NTH
rho = np.hypot(as_, bs_); key = ss * NTH + ti; o = np.argsort(key); ks = key[o]; rs = rho[o]
u, stt, cnt = np.unique(ks, return_index=True, return_counts=True)
R90 = np.full((NSA, NTH), np.nan)
for kk, a0, cc in zip(u, stt, cnt):
    if cc >= 4: R90.flat[kk] = np.percentile(rs[a0:a0 + cc], 90)
thick = np.full(NSA, np.nan)
for s in range(st_tail_ax, NSA):
    m = np.isfinite(R90[s]) & (RHr[s] > 0)
    if m.sum() >= 12: thick[s] = np.median(R90[s, m] - RHr[s, m])
ok = np.isfinite(thick)
ss_ = np.arange(NSA)
thick = np.interp(ss_, ss_[ok], thick[ok])
thick = nd.gaussian_filter1d(thick, 4.0 / secmm, mode='nearest')
thick = np.clip(thick, 0.3 * MM, 3.0 * MM)
print('tail flesh thickness (CT) mm: base %.2f mid %.2f tip %.2f' % (thick[st_tail_ax] / MM, thick[(st_tail_ax + NSA) // 2] / MM, thick[-1] / MM), flush=True)
thick = np.concatenate([np.full(OFF, thick[0]), thick, np.full(NSC, thick[-1])])[:NSC]
# 膜の厚みを足す: 頭 HEAD_WALL_MM、頸で WALL_MM へ、尾は CT で測った肉の厚み
wall = (1 - wt) * HEAD_WALL_MM * MM + wt * WALL_MM * MM
wall = (1 - wtail) * wall + wtail * thick
RA = RA + wall[:, None]
RA[st_tail:] = np.minimum.accumulate(RA[st_tail:], axis=0)  # 尾は先へ細くなる一方
RA[st_tail:] = nd.gaussian_filter1d(RA[st_tail:], 1.5 / secmm, axis=0, mode='nearest')
# 骨の床: ならしで椎骨の棘・尾椎の先が膜から 0.5 mm ほど出た（diag_bones）。ならす前の凸包（1 mm の窓）+ BONE_MARGIN_MM を下限にする
BONE_MARGIN_MM = 0.25
Rraw = np.maximum(R_n, R_n[:, ::-1]) + BONE_MARGIN_MM * MM
RA = np.maximum(RA, Rraw)
RA = nd.gaussian_filter1d(nd.gaussian_filter1d(RA, 0.7, axis=1, mode='wrap'), 0.5 / secmm, axis=0, mode='nearest')
RA = np.maximum(RA, Rraw)
# 凸包の表は向きの升の中心の半径で、升の間は線形に補間されるので、凸包のとがった角（舌骨の角・あごの角）の点は補間の外に出る。
# 表の外に出る骨の点だけ、その点を補間する 4 つの升を、点の半径 + BONE_MARGIN_MM まで上げる（2 回）
rho_ = np.hypot(a_, b_); thp = np.arctan2(b_, a_)
fs_ = jj / SEC - 0.5; ft_ = np.mod((thp + np.pi) / (2 * np.pi) * NTH - 0.5, NTH)
for it in range(10):
    need = rho_ + BONE_MARGIN_MM * MM
    have = nd.map_coordinates(np.concatenate([RA, RA[:, :1]], 1), [np.clip(fs_, 0, NSC - 1), ft_], order=1, mode='nearest')
    bad = have < need - 1e-6
    print('points outside the table (pass %d): %d' % (it, bad.sum()), 'by bone:', dict(zip(*np.unique(na_[bad], return_counts=True))) if it == 0 else '', flush=True)
    if not bad.any(): break
    s0 = np.clip(np.round(fs_[bad]).astype(int), 0, NSC - 1); t0_ = np.round(ft_[bad]).astype(int) % NTH
    defi = np.zeros_like(RA); np.maximum.at(defi, (s0, t0_), (need - have)[bad] + 0.02 * MM)
    if it < 8:   # 足りない分を、軸に沿って σ 1 mm・向きに σ 1 升の山にして足す（山の頂が足りない分になるよう 2 倍）
        RA = RA + 2.0 * nd.gaussian_filter1d(nd.gaussian_filter1d(defi, 1.0, axis=1, mode='wrap'), 1.0 / secmm, axis=0, mode='nearest') * (2 * np.pi) ** 0.5 * (1.0 / secmm) ** 0.5
    else:        # 残りは、その点を補間する 4 つの升を上げる
        for ds in (0, 1):
            for dt in (0, 1):
                np.maximum.at(RA, (np.clip(np.floor(fs_[bad]).astype(int) + ds, 0, NSC - 1), (np.floor(ft_[bad]).astype(int) + dt) % NTH), need[bad])
    RA = np.maximum(RA, RA[:, ::-1])
np.savez('skinbody_tables.npz', RA=RA, arc=(ss_c - OFF) * secmm, thick=thick, st_tail=st_tail, OFF=OFF, J=J)
def axial_dist(x):
    dd, j = kd_ax.query(x, workers=-1)
    q = x - Cc[j]; al = (q * Tc[j]).sum(1)
    a = (q * Dc[j]).sum(1); b = (q * Ec[j]).sum(1)
    r = lookup(RA, j / SEC - 0.5, np.arctan2(b, a))
    end = ((j == 0) & (al < 0)) | ((j == len(Cc) - 1) & (al > 0))
    over = np.where(end, np.abs(al), 0)
    dd = np.hypot(a, b) - r
    return np.where(over > 0, np.maximum(dd, over), dd), j
# ---- 手足（skinloft3 と同じ厚み）----
LIMB_T = {'upper_f': (1.31 + 1.29) / 2, 'lower_f': (0.68 + 1.25) / 2, 'hand': (0.78 + 0.68) / 2,
          'upper_h': (1.39 + 1.79) / 2, 'lower_h': (1.25 + 1.36) / 2, 'foot': (1.45 + 0.78) / 2}
def limb_t(n):
    seg = n.split('_')[1]; return LIMB_T[seg if seg in ('hand', 'foot') else seg + '_' + n[0]]
limbs = {}
for n in bn:
    if n.startswith(('fR', 'fL', 'hR', 'hL')) and n.split('_')[1] in ('upper', 'lower', 'hand', 'foot') and n in rest:
        pb = posed(n); limbs[n] = (cKDTree(pb), limb_t(n) * MM, pb.min(0), pb.max(0))
def limb_dist(n, x):
    kd, tt, _, _ = limbs[n]; return kd.query(x, workers=-1)[0] - tt
# ---- 場 ----
allp = np.concatenate([PX[n] for n in PX] + [posed(n) for n in limbs])
rmaxA = RA.max()
boxes = np.array([Cc.min(0) - rmaxA, Cc.max(0) + rmaxA, allp.min(0) - 3 * MM, allp.max(0) + 3 * MM])
gmin = boxes.min(0) - 2 * MM; gmax = boxes.max(0) + 2 * MM
vox = VOX_MM * MM; shape = tuple(np.ceil((gmax - gmin) / vox).astype(int) + 1)
print('grid', shape, f'{np.prod(shape)/1e6:.0f} M', f'{time.time()-t0:.0f}s', flush=True)
kS = SMOOTH_MM * MM
acc = np.zeros(shape, np.float32)
def add(dist, g):
    acc[tuple(g.T)] += np.exp(-np.clip(dist, -20 * kS, 30 * kS) / kS).astype(np.float32)
def grid_pts(lo_, hi_):
    lo_i = np.maximum(((lo_ - gmin) / vox).astype(int), 0); hi_i = np.minimum(((hi_ - gmin) / vox).astype(int) + 1, np.array(shape))
    return np.stack(np.meshgrid(*[np.arange(p, q_) for p, q_ in zip(lo_i, hi_i)], indexing='ij'), -1).reshape(-1, 3)
for c0 in range(0, len(Cc), 100):
    seg = Cc[c0:c0 + 100]; rr = RA[c0 // SEC:(c0 + 100) // SEC + 2].max()
    g = grid_pts(seg.min(0) - rr - MM, seg.max(0) + rr + MM)
    for c1 in range(0, len(g), 4_000_000):
        gg = g[c1:c1 + 4_000_000]
        dist, j = axial_dist(gmin + gg * vox)
        m = (j >= c0) & (j < c0 + 100) & (dist < 30 * kS)
        add(dist[m], gg[m])
print('axial added', f'{time.time()-t0:.0f}s', flush=True)
for nme, (kd, tt, a, b) in limbs.items():
    g = grid_pts(a - tt - 3 * kS - MM, b + tt + 3 * kS + MM)
    for c0 in range(0, len(g), 2_000_000):
        gg = g[c0:c0 + 2_000_000]
        dd = kd.query(gmin + gg * vox, workers=-1, distance_upper_bound=tt + 3 * kS + 0.5 * MM)[0]
        ok = np.isfinite(dd); add(dd[ok] - tt, gg[ok])
    del g
print('limbs added', f'{time.time()-t0:.0f}s', flush=True)
F = -kS * np.log(np.maximum(acc, 1e-30)); del acc
F = nd.gaussian_filter(F, 1.0)
v, f, _, _ = measure.marching_cubes(F, 0.0); v = gmin + v * vox; del F
simp = pyfqmr.Simplify(); simp.setMesh(v.astype(np.float64), f.astype(np.int32))
simp.simplify_mesh(target_count=int(os.environ.get('SOFT_FACES', '150000')), aggressiveness=7, preserve_border=True, verbose=False)
v, f, _ = simp.getMesh()
import scipy.sparse as sp
TAUBIN = int(os.environ.get('SKIN_TAUBIN', '20'))
E = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]); E = np.concatenate([E, E[:, ::-1]])
A = sp.coo_matrix((np.ones(len(E)), (E[:, 0], E[:, 1])), shape=(len(v), len(v))).tocsr(); A.data[:] = 1
deg = np.asarray(A.sum(1)).ravel(); Lap = sp.diags(1 / np.maximum(deg, 1)) @ A
for _ in range(TAUBIN):
    v = v + 0.5 * (Lap @ v - v)
    v = v - 0.53 * (Lap @ v - v)
print('mesh', len(v), len(f), f'{time.time()-t0:.0f}s', flush=True)
# ---- 重み（skinloft3 と同じ。肩帯の筒は無くなったので、前肢の上腕は体軸とつなぐ）----
cols = ['AX'] + list(limbs)
D = np.zeros((len(v), len(cols)), np.float32)
D[:, 0], jv = axial_dist(v)
for c, nme in enumerate(cols[1:], 1): D[:, c] = limb_dist(nme, v)
SEG = {'upper': 1, 'lower': 2, 'hand': 3, 'foot': 3}
def joinable(a, b):
    if a == b: return True
    if 'AX' in (a, b):
        o = b if a == 'AX' else a
        return o.endswith('_upper')
    la, sa = a.split('_'); lb, sb = b.split('_')
    return la == lb and abs(SEG[sa] - SEG[sb]) <= 1
OK = np.array([[joinable(a, b) for b in cols] for a in cols])
prim = np.argmin(D, 1)
W = np.exp(-(D - D[np.arange(len(v)), prim][:, None]) / (0.4 * MM)); W[~OK[prim]] = 0
bones = [f'v{i+1:02d}' for i in range(len(J))] + ['head'] + cols[1:]
HI = len(J)
# 一本の軸の点 → 骨: 頭の部分は頭骨、橋（後頭顆 → 体軸の始まり）で頭骨から v01 へ、その先は椎骨（skinloft3 と同じ）
ne = len(ext)
cA = np.concatenate([np.full(NH, HI), va, np.full(ne, va[-1])]); cB = np.concatenate([np.full(NH - nbr, HI), np.zeros(nbr, int), vb, np.full(ne, vb[-1])])
cW = np.concatenate([np.zeros(NH - nbr), (np.arange(nbr) + 1) / (nbr + 1), wb, np.full(ne, wb[-1])])
WB = np.zeros((len(v), len(bones)), np.float32)
ia, ib_, wb_ = cA[jv], cB[jv], cW[jv]
np.add.at(WB, (np.arange(len(v)), ia), W[:, 0] * (1 - wb_)); np.add.at(WB, (np.arange(len(v)), ib_), W[:, 0] * wb_)
for c in range(1, len(cols)): WB[:, HI + c] += W[:, c]
ribn = sorted(n for n in PX if n.startswith('rib'))
bones += ribn
WB = np.concatenate([WB, np.zeros((len(v), len(ribn)), np.float32)], 1)
Xr_p = np.concatenate([PX[n][::3] for n in ribn]); Lr_p = np.concatenate([np.full(len(PX[n][::3]), i) for i, n in enumerate(ribn)])
dr, jr = cKDTree(Xr_p).query(v, workers=-1)
wr = 0.7 * np.exp(-0.5 * (dr / (2.0 * MM)) ** 2) * W[:, 0] / np.maximum(W.sum(1), 1e-9)
axs = WB[:, :HI].sum(1); keepw = 1 - wr
WB[:, :HI] *= keepw[:, None]
np.add.at(WB, (np.arange(len(v)), HI + len(cols) + Lr_p[jr]), wr * np.maximum(axs, 1e-9))
top = np.argsort(-WB, 1)[:, :3]; tw = np.take_along_axis(WB, top, 1); tw /= np.maximum(tw.sum(1, keepdims=True), 1e-9)
Ms = np.array([Mof(b) for b in bones])
Mv = np.einsum('vk,vkij->vij', tw, Ms[top])
vr = np.einsum('vij,vj->vi', np.linalg.inv(Mv), np.c_[v, np.ones(len(v))])[:, :3]
f = f[:, ::-1]
np.savez_compressed('soft_rigged.npz', v=m2ct(vr).astype(np.float32), f=f.astype(np.int32),
                    w_idx=top.astype(np.int16), w_val=tw.astype(np.float32), names=np.array(bones))
np.savez_compressed('skin_posed.npz', v=v.astype(np.float32), f=f.astype(np.int32))
print('saved', f'{time.time()-t0:.0f}s')

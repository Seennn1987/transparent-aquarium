# 膜の作り直し 6（2026-10-14）: 頭と胴を別の膜にして、後頭部でだけつなぐ
#   5（skinbody_v5.py）は吻端から尾の先までの 1 本の軸の断面ごとに骨の凸包を取った。展示の姿勢で頭が下を向くと
#   トサカの後ろ端が肩の後ろまで頸の上に張り出し、凸包がトサカの先と椎骨の間を埋めて、トサカと背中が一枚になった。
#   実物（写真 01、生体の X 線）ではトサカの後ろ端は頸と離れた板で、背中の始まりとの間にくぼみがある。
#   胴の膜（頸〜尾の先）: 体軸の断面ごとに、椎骨・肋骨・軟骨・肢帯・舌骨の後ろの角の凸包（5 と同じ作り方）。頭骨は入れない
#   頭の膜: 頭骨の軸（吻端 → トサカの後ろ端）の断面ごとに、頭骨・舌骨の前（喉の中）・眼球（eyes.py）の凸包 + HEAD_WALL_MM
#   2 つは幅 JOIN_MM のなめらかな最小でつなぐ。背の正中に小さな円錐のとげの列（生体の X 線の背の縁から、間隔・高さは目測で仮）
#   尾の肉の厚み・手足・重み・出力は 5 と同じ
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
st_tail = int(np.ceil(J[23] / secmm))                        # 最初の尾椎（v24）の頭の断面
# ---- 頭の枠（展示の姿勢）: 後頭顆 hP、吻端への向き tP ----
ih = bn.index('head'); Mh = Mof('head')
h0 = Hm[ih]; th_ = Tm[ih] - h0; th_ /= np.linalg.norm(th_)
hP = apply(Mh, h0[None])[0]; tP = Mh[:3, :3] @ th_
# 舌骨（2026-10-15 に作り直し、hyoid_rebuild.py）: 骨は左右の第 1 角鰓骨（長さ 約 13.5 mm）だけ、軟骨は舌内突起・基舌骨・角舌骨。
#   どれも喉と下あごの間にあり頭について動くので、頭の膜に入れる（HY_FRONT）。胸へ伸びる棒はもう無い（HY_BACK は空）
#   第 1 角鰓骨は上の端が頭骨の後ろに触れ、下の端が下あごの後ろより 3 mm 下に出る（Digimorph の Chamaeleo calyptratus:
#   舌を引いたときの第 1 角鰓骨は前背側へ向く）。喉が下あごから角の下の端までなめらかな面になるように、角の点は頸の膜にも入れ
#   （CERATO）、頭の膜の後ろの断面は窓を広げて下あごとつなぐ
HY_FRONT = PX['hyoid']; HY_BACK = np.zeros((0, 3))
CERATO = apply(Mof('hyoid'), rest['hyoid'])
print('first ceratobranchials (hyoid bone): %d points' % len(CERATO), flush=True)
# 眼球（eyes.py）: 球の面の点
EY = json.load(open('eyes.json'))
def sphere_pts(c, r, n=800):
    i = np.arange(n) + 0.5; ph = np.arccos(1 - 2 * i / n); th = np.pi * (1 + 5 ** 0.5) * i
    return c + r * np.stack([np.cos(th) * np.sin(ph), np.sin(th) * np.sin(ph), np.cos(ph)], 1)
EYE_PTS = np.concatenate([sphere_pts(np.array(e['centre_model']), e['radius_mm'] * MM) for e in EY.values()])
print('hyoid: %d points to the head, %d to the neck; eyes %s' % (len(HY_FRONT), len(HY_BACK), {n: round(e['radius_mm'], 2) for n, e in EY.items()}), flush=True)

def sm(R, sig_mm, sec_mm):
    return nd.gaussian_filter1d(nd.gaussian_filter1d(R, 1.0, axis=1, mode='wrap'), sig_mm / sec_mm, axis=0, mode='nearest')
def sm_above(R, sig_mm, sec_mm, n=6):
    # ならしても下（R）より低くならないように: 最大を取ってならす、を繰り返す（出っ張りは σ の幅のなめらかなふくらみになる）
    X = sm(R, sig_mm, sec_mm)
    for _ in range(n): X = sm(np.maximum(X, R), sig_mm, sec_mm)
    return np.maximum(X, R)
BONE_MARGIN_MM = 0.25
def cover(RA, a_, b_, jj, names_, label):
    """表の外に出る骨の点だけ、足りない分を σ 1 mm の山で上げる（最後は点を補間する 4 升を上げる）"""
    NS = RA.shape[0]; rho_ = np.hypot(a_, b_); thp = np.arctan2(b_, a_)
    fs_ = jj / SEC - 0.5; ft_ = np.mod((thp + np.pi) / (2 * np.pi) * NTH - 0.5, NTH)
    for it in range(10):
        need = rho_ + BONE_MARGIN_MM * MM
        have = nd.map_coordinates(np.concatenate([RA, RA[:, :1]], 1), [np.clip(fs_, 0, NS - 1), ft_], order=1, mode='nearest')
        bad = have < need - 1e-6
        if it == 0: print(label, 'points outside the table:', int(bad.sum()), dict(zip(*np.unique(names_[bad], return_counts=True))), flush=True)
        if not bad.any(): break
        s0 = np.clip(np.round(fs_[bad]).astype(int), 0, NS - 1); t0_ = np.round(ft_[bad]).astype(int) % NTH
        defi = np.zeros_like(RA); np.maximum.at(defi, (s0, t0_), (need - have)[bad] + 0.02 * MM)
        if it < 8:
            RA = RA + 2.0 * nd.gaussian_filter1d(nd.gaussian_filter1d(defi, 1.0, axis=1, mode='wrap'), 1.0 / secmm, axis=0, mode='nearest') * (2 * np.pi) ** 0.5 * (1.0 / secmm) ** 0.5
        else:
            for ds in (0, 1):
                for dt in (0, 1):
                    np.maximum.at(RA, (np.clip(np.floor(fs_[bad]).astype(int) + ds, 0, NS - 1), (np.floor(ft_[bad]).astype(int) + dt) % NTH), need[bad])
        RA = np.maximum(RA, RA[:, ::-1])
    return RA
class Body:
    """軸（点 Cc、向き Tc・背 Dc）の断面ごとの半径の表 RA（48 向き）。dist(x) = 軸からの距離 − 表の半径（端は平らなふた）"""
    def __init__(s, Cc, Tc, Dc, RA):
        s.Cc, s.Tc, s.Dc, s.Ec, s.RA = Cc, Tc, Dc, np.cross(Tc, Dc), RA; s.kd = cKDTree(Cc)
    def frame(s, x):
        j = s.kd.query(x, workers=-1)[1]; q = x - s.Cc[j]
        return j, (q * s.Dc[j]).sum(1), (q * s.Ec[j]).sum(1), (q * s.Tc[j]).sum(1)
    def dist(s, x):
        j, a, b, al = s.frame(x)
        r = lookup(s.RA, j / SEC - 0.5, np.arctan2(b, a))
        end = ((j == 0) & (al < 0)) | ((j == len(s.Cc) - 1) & (al > 0))
        dd = np.hypot(a, b) - r
        return np.where(end, np.maximum(dd, np.abs(al)), dd), j

# ---- 胴の膜（頸〜尾の先）: 頭骨・前の舌骨を入れない（トサカが頸の上に張り出しても、膜をトサカまで張らない）----
dstep = step * MM
tdir = Cp[-1] - Cp[-20]; tdir /= np.linalg.norm(tdir)
ext = Cp[-1] + tdir * (dstep * np.arange(1, int(1.0 / step) + 1))[:, None]      # 尾の先の椎骨は体軸の終わりより先まである: 1 mm 延ばす
Cc = np.concatenate([Cp, ext])
# 姿勢の体軸は椎骨ごとの変形を混ぜたもので、椎骨の長さ（約 4 mm）ごとに軸と向きが小さく揺れる。揺れは膜の輪の縞になったので、
# 軸の点を σ 1.5 mm、背の向きを σ 3 mm でならす（表もならした軸で作るので、骨との関係は変わらない）
Cc = nd.gaussian_filter1d(Cc, 1.5 / step, axis=0, mode='nearest')
Tc = np.gradient(Cc, axis=0); Tc /= np.linalg.norm(Tc, axis=1, keepdims=True)
Dc = nd.gaussian_filter1d(np.concatenate([Dp, np.repeat(Dp[-1:], len(ext), 0)]), 3.0 / step, axis=0, mode='nearest')
Dc = Dc - Tc * (Dc * Tc).sum(1, keepdims=True); Dc /= np.linalg.norm(Dc, axis=1, keepdims=True)
NSC = (len(Cc) + SEC - 1) // SEC
trunk_names = [n for n in PX if n not in ('head', 'hyoid')]
xa = np.concatenate([PX[n] for n in trunk_names] + [HY_BACK, CERATO]); na_ = np.concatenate([np.full(len(PX[n]), n) for n in trunk_names] + [np.full(len(HY_BACK), 'hyoid'), np.full(len(CERATO), 'ceratobranchial')])
T0 = Body(Cc, Tc, Dc, np.zeros((NSC, NTH)))
jj, a_, b_, _ = T0.frame(xa); sec = jj // SEC
win = int(round(HULL_WIN_MM / secmm))
R_w = fill_zero(hull_table(a_, b_, sec, NSC, win)); R_n = fill_zero(hull_table(a_, b_, sec, NSC, 2))
ss_c = np.arange(NSC)
wt = np.clip(ss_c * secmm / 9.5, 0, 1)                              # 頸（体軸 0 → 肩 9.5 mm）で細かい窓から胴の作り方へ
wtail = np.clip((ss_c - st_tail) / (3.0 / secmm) + 0.5, 0, 1)
R_wm = nd.maximum_filter1d(R_w, size=2 * win + 1, axis=0, mode='nearest')
RA = ((1 - wt)[:, None] * sm_above(R_n, 0.7, secmm) + (wt * (1 - wtail))[:, None] * sm_above(R_wm, AX_SIG_MM, secmm)
      + (wt * wtail)[:, None] * sm_above(R_n, 1.5, secmm))
RA = np.maximum(RA, RA[:, ::-1])

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
for s in range(st_tail, NSA):
    m = np.isfinite(R90[s]) & (RHr[s] > 0)
    if m.sum() >= 12: thick[s] = np.median(R90[s, m] - RHr[s, m])
ok = np.isfinite(thick)
ss_ = np.arange(NSA)
thick = np.interp(ss_, ss_[ok], thick[ok])
thick = nd.gaussian_filter1d(thick, 4.0 / secmm, mode='nearest')
thick = np.clip(thick, 0.3 * MM, 3.0 * MM)
print('tail flesh thickness (CT) mm: base %.2f mid %.2f tip %.2f' % (thick[st_tail] / MM, thick[(st_tail + NSA) // 2] / MM, thick[-1] / MM), flush=True)
thick = np.concatenate([thick, np.full(NSC, thick[-1])])[:NSC]

wall = (1 - wt) * HEAD_WALL_MM * MM + wt * WALL_MM * MM
wall = (1 - wtail) * wall + wtail * thick
RA = RA + wall[:, None]
RA[st_tail:] = np.minimum.accumulate(RA[st_tail:], axis=0)  # 尾は先へ細くなる一方
RA[st_tail:] = nd.gaussian_filter1d(RA[st_tail:], 1.5 / secmm, axis=0, mode='nearest')
Rraw = np.maximum(R_n, R_n[:, ::-1]) + BONE_MARGIN_MM * MM
RA = np.maximum(RA, Rraw)
RA = nd.gaussian_filter1d(nd.gaussian_filter1d(RA, 0.7, axis=1, mode='wrap'), 0.5 / secmm, axis=0, mode='nearest')
RA = np.maximum(RA, Rraw)
RA = cover(RA, a_, b_, jj, na_, 'trunk')
TRUNK = Body(Cc, Tc, Dc, RA)
np.savez('skinbody_tables.npz', RA=RA, arc=ss_c * secmm, thick=thick, st_tail=st_tail, J=J)
print('trunk table', RA.shape, f'{time.time()-t0:.0f}s', flush=True)

# ---- 頭の膜: 頭骨・前の舌骨・眼球の、頭骨の軸に直角な断面ごとの凸包 + HEAD_WALL_MM ----
#   トサカの後ろ端は頸の上に張り出しても頭の膜の中だけで閉じ、胴の膜とは離れた板になる（写真 01、生体の X 線）
xh = np.concatenate([PX['head'], HY_FRONT, EYE_PTS]); nh_ = np.concatenate([np.full(len(PX['head']), 'head'), np.full(len(HY_FRONT), 'hyoid'), np.full(len(EYE_PTS), 'eye')])
sk = (xh - hP) @ tP; s_hi = sk.max() + 0.3 * MM; s_lo = sk.min() - 0.3 * MM
CH = hP + tP * np.arange(s_hi, s_lo, -dstep)[:, None]               # 吻端 → トサカの後ろ端
TH = np.repeat(-tP[None], len(CH), 0)
# 頭の背: 胴の軸の始まりの背の向きを頭骨の軸に直交させたもの
dh = Dc[0] - tP * (Dc[0] @ tP); dh /= np.linalg.norm(dh)
DH = np.repeat(dh[None], len(CH), 0)
H0 = Body(CH, TH, DH, np.zeros(((len(CH) + SEC - 1) // SEC, NTH)))
jh, ah, bh, _ = H0.frame(xh); NSH = H0.RA.shape[0]
RH = fill_zero(hull_table(ah, bh, jh // SEC, NSH, 2))
# 後頭顆より後ろ（と前 3 mm まで）の断面は窓を ±3 mm に広げ、下あごの後ろの端と角の下の端を一つの喉の面にする
RHw = fill_zero(hull_table(ah, bh, jh // SEC, NSH, int(round(3.0 / secmm))))
s_sec = (s_hi - (np.arange(NSH) + 0.5) * SEC * dstep) / MM           # 断面の、後頭顆からの頭骨の軸の位置 [mm]
wr_ = np.clip((3.0 - s_sec) / 3.0, 0, 1)[:, None]                    # 後頭顆の前 3 mm から後ろで広い窓へ
RH = np.maximum(RH, wr_ * RHw)
RH = sm_above(RH, 0.7, secmm) + HEAD_WALL_MM * MM
RH = cover(RH, ah, bh, jh, nh_, 'head')
HEAD = Body(CH, TH, DH, RH)
print('head table', RH.shape, 'from %.1f to %.1f mm along the skull' % (s_hi / MM, s_lo / MM), f'{time.time()-t0:.0f}s', flush=True)

# ---- 背のとげの列（生体の X 線の背の縁のぎざぎざ: 間隔 約 2.0 mm、高さ 約 0.3 mm の揺れ。目測、仮）----
#   背の膜の正中の上に、高さ CREST_H・底の半径 CREST_R の円錐を CREST_GAP ごとに。肩（体軸 9.5 mm）から尾の付け根の 10 mm 先まで
CREST_GAP, CREST_H, CREST_R = 2.0, 0.6, 0.5
us_c = np.arange(9.5, J[23] + 10.0, CREST_GAP)
ic = np.clip((us_c / step).round().astype(int), 0, len(Cc) - 1)
rtop = lookup(RA, ic / SEC - 0.5, np.zeros(len(ic)))                # 背（θ = 0）の膜の半径
cbase = Cc[ic] + Dc[ic] * (rtop - 0.15 * MM)[:, None]; caxis = Dc[ic]
def crest_dist(x):
    kd = cKDTree(cbase); dd, i = kd.query(x, workers=-1)
    q = x - cbase[i]; h = (q * caxis[i]).sum(1); r = np.linalg.norm(q - h[:, None] * caxis[i], axis=1)
    H, Rb = CREST_H * MM, CREST_R * MM
    side = (r - Rb * (1 - h / H)) * H / np.hypot(H, Rb)                 # 円錐の側面までの距離（近似）
    return np.maximum.reduce([side, -h, h - H])

# ---- 手足（skinloft3 と同じ厚み）----
LIMB_T = {'upper_f': (1.31 + 1.29) / 2, 'lower_f': (0.68 + 1.25) / 2, 'hand': (0.78 + 0.68) / 2,
          'upper_h': (1.39 + 1.79) / 2, 'lower_h': (1.25 + 1.36) / 2, 'foot': (1.45 + 0.78) / 2}
if os.environ.get('LIMB_T_FOOT'): LIMB_T['foot'] = float(os.environ['LIMB_T_FOOT'])   # 記録 30 の案（足を手と同じ 0.73 mm など）
def limb_t(n):
    seg = n.split('_')[1]; return LIMB_T[seg if seg in ('hand', 'foot') else seg + '_' + n[0]]
limbs = {}
for n in bn:
    if n.startswith(('fR', 'fL', 'hR', 'hL')) and n.split('_')[1] in ('upper', 'lower', 'hand', 'foot') and n in rest:
        pb = posed(n); limbs[n] = (cKDTree(pb), limb_t(n) * MM, pb.min(0), pb.max(0))
def limb_dist(n, x):
    kd, tt, _, _ = limbs[n]; return kd.query(x, workers=-1)[0] - tt
# 束ごとの膜（記録 30 の案。2026-10-18）: LIMB_CLEFT は foot_bundles.py の出力。指の 2 つの束のあいだ（両方の束から等しい距離の
#   面のまわり、幅 CLEFT_MM）を膜の外にして、束ごとに膜を分ける。付け根（束が分かれる前）に近い所では 1 mm かけて切れ込みを 0 にする
CLEFT = {}
CLEFT_MM = float(os.environ.get('CLEFT_MM', '0.4'))
CLEFT_KEEP_MM = float(os.environ.get('CLEFT_KEEP_MM', '0.5'))
if os.environ.get('LIMB_CLEFT'):
    LB = np.load(os.environ['LIMB_CLEFT'])
    for n in limbs:
        if n not in LB.files: continue
        lab = LB[n]; pb = posed(n)
        if len(pb) > len(lab):                                           # 軟骨の点は最も近い骨の頂点と同じ束
            lab = np.concatenate([lab, lab[cKDTree(pb[:len(lab)]).query(pb[len(lab):])[1]]])
        CLEFT[n] = [cKDTree(pb[lab == i]) for i in (0, 1, 2)]
    print('cleft between digit bundles:', sorted(CLEFT), 'width %.2f mm' % CLEFT_MM, flush=True)
def limb_field(n, x, ub):
    """手足の骨 n の場の距離（膜の面で 0、外で正）。ub より遠い所は inf。"""
    kd, tt, _, _ = limbs[n]
    if n not in CLEFT: return kd.query(x, workers=-1, distance_upper_bound=ub)[0] - tt
    dB, dU, dL = [np.minimum(t.query(x, workers=-1, distance_upper_bound=ub + 2 * MM)[0], ub + 2 * MM) for t in CLEFT[n]]
    dmin = np.minimum.reduce([dB, dU, dL])
    ramp = np.clip((dB - np.minimum(dU, dL)) / MM, 0, 1)
    # 切れ込みは骨から CLEFT_KEEP_MM より内へは入れない（束の骨どうしが CLEFT_MM より近い所で骨を削り、骨の点が膜の外に出た。
    #   0.25 mm でも、膜をならす段で骨の点が 0.3〜2.8% 外に出た）
    #   付け根（ramp 0）では切れ込みを効かせない。ramp を掛けるだけだと付け根の骨で値が 0（膜の面）になり、骨が膜の外に出た
    cut = np.minimum((CLEFT_MM * MM - np.abs(dU - dL)) / 2 - (1 - ramp) * 10 * MM, np.minimum(dU, dL) - CLEFT_KEEP_MM * MM)
    out = np.maximum(dmin - tt, cut)
    out[dmin > ub] = np.inf
    return out

# ---- 場: 胴（＋手足・背のとげ）と頭を別々に作り、継ぎ目は幅 JOIN_MM のなめらかな最小でつなぐ ----
#   （同じ幅 SMOOTH_MM で混ぜると首に段ができ、一本の軸にするとトサカと背中が一枚になった。頭と頸は後頭部でだけ触れる）
JOIN_MM = 1.0
allp = np.concatenate([PX[n] for n in PX] + [posed(n) for n in limbs] + [EYE_PTS])
rmax = max(TRUNK.RA.max(), HEAD.RA.max())
boxes = np.array([Cc.min(0) - rmax, Cc.max(0) + rmax, CH.min(0) - rmax, CH.max(0) + rmax, allp.min(0) - 3 * MM, allp.max(0) + 3 * MM])
gmin = boxes.min(0) - 2 * MM; gmax = boxes.max(0) + 2 * MM
vox = VOX_MM * MM; shape = tuple(np.ceil((gmax - gmin) / vox).astype(int) + 1)
print('grid', shape, f'{np.prod(shape)/1e6:.0f} M', f'{time.time()-t0:.0f}s', flush=True)
kS = SMOOTH_MM * MM
accT = np.zeros(shape, np.float32); accH = np.zeros(shape, np.float32)
def add(acc, dist, g):
    acc[tuple(g.T)] += np.exp(-np.clip(dist, -20 * kS, 30 * kS) / kS).astype(np.float32)
def grid_pts(lo_, hi_):
    lo_i = np.maximum(((lo_ - gmin) / vox).astype(int), 0); hi_i = np.minimum(((hi_ - gmin) / vox).astype(int) + 1, np.array(shape))
    return np.stack(np.meshgrid(*[np.arange(p, q_) for p, q_ in zip(lo_i, hi_i)], indexing='ij'), -1).reshape(-1, 3)
def add_body(acc, B):
    for c0 in range(0, len(B.Cc), 100):
        seg = B.Cc[c0:c0 + 100]; rr = B.RA[c0 // SEC:(c0 + 100) // SEC + 2].max()
        g = grid_pts(seg.min(0) - rr - MM, seg.max(0) + rr + MM)
        for c1 in range(0, len(g), 4_000_000):
            gg = g[c1:c1 + 4_000_000]
            dist, j = B.dist(gmin + gg * vox)
            m = (j >= c0) & (j < c0 + 100) & (dist < 30 * kS)
            add(acc, dist[m], gg[m])
add_body(accT, TRUNK); add_body(accH, HEAD)
print('bodies added', f'{time.time()-t0:.0f}s', flush=True)
for nme, (kd, tt, a, b) in limbs.items():
    g = grid_pts(a - tt - 3 * kS - MM, b + tt + 3 * kS + MM)
    for c0 in range(0, len(g), 2_000_000):
        gg = g[c0:c0 + 2_000_000]
        dd = limb_field(nme, gmin + gg * vox, tt + 3 * kS + 0.5 * MM)
        ok = np.isfinite(dd); add(accT, dd[ok], gg[ok])
    del g
g = grid_pts(cbase.min(0) - 2 * MM, cbase.max(0) + 2 * MM)
for c0 in range(0, len(g), 4_000_000):
    gg = g[c0:c0 + 4_000_000]; dd = crest_dist(gmin + gg * vox); m = dd < 30 * kS; add(accT, dd[m], gg[m])
print('limbs and crest added', f'{time.time()-t0:.0f}s', flush=True)
# 骨から遠い膜を切る（2026-10-14 の 3 回目）: 断面ごとの凸包は、断面の平面の中で離れた骨どうしを結ぶので、トサカの後ろの角・
#   尾の付け根と後肢の間・喉の下に、中に骨の無い膜が張られた（diag_excess.py で 145 mm²、右から）。
#   頭の膜と頸（体軸 NECK_CUT_MM まで）の膜は、骨（軟骨・眼球を含む）から BONE_REACH_MM より遠くへ出さない:
#   場 = なめらかな最大（場、骨からの距離 − BONE_REACH_MM）。BONE_REACH_MM = 3.0 mm（仮）。
#   胴全体に掛けると肋骨の間で膜がへこみ、やせた体に見えたので、胴（肋骨の輪）と尾には掛けない
BONE_REACH_MM = float(os.environ.get('BONE_REACH_MM', '3.0'))
occ = np.zeros(shape, bool)
allb = np.concatenate([PX[n] for n in PX] + [posed(n) for n in limbs] + [EYE_PTS])
gi = np.clip(np.round((allb - gmin) / vox).astype(int), 0, np.array(shape) - 1); occ[tuple(gi.T)] = True
ov = int(np.ceil((BONE_REACH_MM + 1.0) * MM / vox)) + 2
ax_ = int(np.argmax(shape)); Dist = np.empty(shape, np.float32)
for c0 in range(0, shape[ax_], 100):
    lo_ = max(c0 - ov, 0); hi_ = min(c0 + 100 + ov, shape[ax_])
    sl = [slice(None)] * 3; sl[ax_] = slice(lo_, hi_)
    e = nd.distance_transform_edt(~occ[tuple(sl)]).astype(np.float32) * vox
    keep = [slice(None)] * 3; keep[ax_] = slice(c0 - lo_, c0 - lo_ + min(100, shape[ax_] - c0))
    dst = [slice(None)] * 3; dst[ax_] = slice(c0, min(c0 + 100, shape[ax_]))
    Dist[tuple(dst)] = np.minimum(e[tuple(keep)], (BONE_REACH_MM + 1.0) * MM)
del occ
G2 = Dist - BONE_REACH_MM * MM; del Dist
kc = 0.3 * MM
def smax(A, B):
    mx = np.maximum(A, B); return mx + kc * np.log(np.exp((A - mx) / kc) + np.exp((B - mx) / kc))
print('cut at %.1f mm from the bones' % BONE_REACH_MM, f'{time.time()-t0:.0f}s', flush=True)
FT = -kS * np.log(np.maximum(accT, 1e-30)); del accT
FH = -kS * np.log(np.maximum(accH, 1e-30)); del accH
# 頭: 3 次元の骨からの距離で切ると、トサカの枠（頭頂の稜と鱗状骨）の中の穴（側頭窓）まで膜がへこんだ。生体ではトサカの横は
#   皮膚と筋肉で埋まり、輪郭は骨の枠に沿う。頭の膜は、横から写した頭骨・眼球の像（穴を埋め、半径 HEAD_CLOSE_MM で閉じる）の
#   外へ出さない（像の外形 + HEAD_WALL_MM で、横向きに押し出した形と重ねる）。上・前から写した像も同じ
HEAD_CLOSE_MM = 2.0
CASQUE_OPEN = bool(int(os.environ.get('CASQUE_OPEN', '0')))       # 1 でかぶとの輪の穴を横の像で埋めない（記録 25 の案）
CASQUE_HOLE_MM2 = float(os.environ.get('CASQUE_HOLE_MM2', '4.0'))
lat = np.array(EY['eye_r']['centre_model']) - np.array(EY['eye_l']['centre_model']); lat /= np.linalg.norm(lat)
e1 = tP - lat * (tP @ lat); e1 /= np.linalg.norm(e1); e2 = np.cross(lat, e1)
hp = np.concatenate([PX['head'], HY_FRONT, EYE_PTS])                  # 舌骨（骨と軟骨）も頭の像に入れる（喉の下の舌の芯・基舌骨）
hb = grid_pts(np.min([CH.min(0), hp.min(0)], 0) - HEAD.RA.max() - MM, np.max([CH.max(0), hp.max(0)], 0) + HEAD.RA.max() + MM)
xq = gmin + hb * vox; ih_ = tuple(hb.T)
# 横・上・前の 3 つの向きから写した像の外へ出さない（3 つの像を押し出した形の重なり。横だけだと頬が頭骨より 1.5〜3 mm 外へ出た）
for (u1, u2, nm_) in ((e1, e2, 'side'), (e1, lat, 'top'), (lat, e2, 'front')):
    H2 = np.c_[hp @ u1, hp @ u2] / MM
    px2 = 0.1; lo2 = H2.min(0) - 6; sh2 = tuple(np.ceil((H2.max(0) + 6 - lo2) / px2).astype(int) + 1)
    im2 = np.zeros(sh2, bool); g2 = ((H2 - lo2) / px2).round().astype(int); im2[tuple(g2.T)] = True
    im2 = nd.distance_transform_edt(~im2) * px2 <= HEAD_CLOSE_MM + 0.15          # 閉じる（ふくらませて戻す）
    im2 = nd.distance_transform_edt(im2) * px2 > HEAD_CLOSE_MM
    filled = nd.binary_fill_holes(im2)
    if CASQUE_OPEN and nm_ == 'side':
        # かぶとの輪の穴（眼の点を含まない、CASQUE_HOLE_MM2 より大きい穴）は埋めない（記録 25 の案。写真 06 の輪の内側は白く抜ける）
        holes, nh = nd.label(filled & ~im2)
        ge = ((np.c_[EYE_PTS @ u1, EYE_PTS @ u2] / MM - lo2) / px2).round().astype(int)
        eye_lab = set(holes[tuple(ge.T)].ravel()) - {0}
        for lb in range(1, nh + 1):
            if lb not in eye_lab and (holes == lb).sum() * px2 * px2 > CASQUE_HOLE_MM2:
                filled[holes == lb] = False
    im2 = filled
    sd2 = (nd.distance_transform_edt(~im2) - nd.distance_transform_edt(im2)) * px2   # 外が正（mm）
    q2 = (np.c_[xq @ u1, xq @ u2] / MM - lo2) / px2
    dq = nd.map_coordinates(sd2, [q2[:, 0], q2[:, 1]], order=1, mode='nearest') - HEAD_WALL_MM
    FH[ih_] = smax(FH[ih_], (dq * MM).astype(np.float32))
del hb, xq, q2, dq, ih_
print('head kept within its side, top and front outlines (closed %.1f mm)' % HEAD_CLOSE_MM, flush=True)
NECK_CUT_MM = 12.0
nb = grid_pts(Cc[:int(NECK_CUT_MM / step)].min(0) - rmax, Cc[:int(NECK_CUT_MM / step)].max(0) + rmax)
jn = TRUNK.kd.query(gmin + nb * vox, workers=-1)[1]; nb = nb[jn * step < NECK_CUT_MM]
iv = tuple(nb.T); FT[iv] = smax(FT[iv], G2[iv]); del G2, nb, jn
kJ = JOIN_MM * MM
m_ = np.minimum(FT, FH)
F = m_ - kJ * np.log(np.exp(-(FT - m_) / kJ) + np.exp(-(FH - m_) / kJ)); del FT, FH, m_
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
# ---- 膜をならす（計画書 C の記録 21、案 3B。2026-10-17 プロデューサー決定「頭を除いてならす」）----
#   上の Taubin（μ −0.53）は通す帯が広く、肋骨ごとの横の筋（波長 約 4.5 mm）が残った（記録 20）。μ −0.505（通す帯 約 0.02）で
#   SKIN_SMOOTH 回ならす。頭の膜（頭骨からの距離が胴の体軸からの距離より近い所）は動かさず、境目はなめらかに移す。
#   ならすと膜が縮むので、10 回ごとに、骨（軟骨を含む）までの距離が min（元の距離, SMOOTH_CLEAR_MM）より近くなった頂点を戻す
SKIN_SMOOTH = int(os.environ.get('SKIN_SMOOTH', '120'))
SMOOTH_CLEAR_MM = float(os.environ.get('SMOOTH_CLEAR_MM', '0.6'))
if SKIN_SMOOTH:
    dAX = TRUNK.dist(v)[0]; dHD = HEAD.dist(v)[0]
    wsm = np.clip((dHD - dAX) / (1.0 * MM) + 0.5, 0, 1)
    for _ in range(4): wsm = Lap @ wsm
    XB = np.concatenate([posed(n)[::2] for n in bn if n in rest or n in rest_cart])
    TB = cKDTree(XB); d0 = TB.query(v, workers=-1)[0]; dmin = np.minimum(d0, SMOOTH_CLEAR_MM * MM)
    nback = 0
    for it in range(0, SKIN_SMOOTH, 10):
        vp = v.copy()
        for _ in range(min(10, SKIN_SMOOTH - it)):
            v = v + (0.5 * wsm)[:, None] * (Lap @ v - v)
            v = v + (-0.505 * wsm)[:, None] * (Lap @ v - v)
        bad = TB.query(v, workers=-1)[0] < dmin
        v[bad] = vp[bad]; nback += int(bad.sum())
    print('smoothed %d times outside the head (%d vertex steps held back near bone)' % (SKIN_SMOOTH, nback), f'{time.time()-t0:.0f}s', flush=True)
# ---- 重み: 胴の膜は椎骨（と近い肋骨）、頭の膜は頭骨、手足は skinloft3 と同じ ----
cols = ['AX', 'HD'] + list(limbs)
D = np.zeros((len(v), len(cols)), np.float32)
D[:, 0], jv = TRUNK.dist(v); D[:, 1] = HEAD.dist(v)[0]
for c, nme in enumerate(cols[2:], 2): D[:, c] = limb_dist(nme, v)
SEG = {'upper': 1, 'lower': 2, 'hand': 3, 'foot': 3}
def joinable(a, b):
    if a == b: return True
    if {a, b} == {'AX', 'HD'}: return True
    if 'HD' in (a, b): return False
    if 'AX' in (a, b):
        o = b if a == 'AX' else a
        return o.endswith('_upper')
    la, sa = a.split('_'); lb, sb = b.split('_')
    return la == lb and abs(SEG[sa] - SEG[sb]) <= 1
OK = np.array([[joinable(a, b) for b in cols] for a in cols])
prim = np.argmin(D, 1)
W = np.exp(-(D - D[np.arange(len(v)), prim][:, None]) / (0.4 * MM)); W[~OK[prim]] = 0
bones = [f'v{i+1:02d}' for i in range(len(J))] + ['head'] + cols[2:]
HI = len(J)
ne = len(ext)
cA = np.concatenate([va, np.full(ne, va[-1])]); cB = np.concatenate([vb, np.full(ne, vb[-1])]); cW = np.concatenate([wb, np.full(ne, wb[-1])])
WB = np.zeros((len(v), len(bones)), np.float32)
ia, ib_, wb_ = cA[jv], cB[jv], cW[jv]
np.add.at(WB, (np.arange(len(v)), ia), W[:, 0] * (1 - wb_)); np.add.at(WB, (np.arange(len(v)), ib_), W[:, 0] * wb_)
WB[:, HI] += W[:, 1]
for c in range(2, len(cols)): WB[:, HI + c - 1] += W[:, c]
ribn = sorted(n for n in PX if n.startswith('rib'))
bones += ribn
WB = np.concatenate([WB, np.zeros((len(v), len(ribn)), np.float32)], 1)
Xr_p = np.concatenate([PX[n][::3] for n in ribn]); Lr_p = np.concatenate([np.full(len(PX[n][::3]), i) for i, n in enumerate(ribn)])
dr, jr = cKDTree(Xr_p).query(v, workers=-1)
wr = 0.7 * np.exp(-0.5 * (dr / (2.0 * MM)) ** 2) * W[:, 0] / np.maximum(W.sum(1), 1e-9)
axs = WB[:, :HI].sum(1); keepw = 1 - wr
WB[:, :HI] *= keepw[:, None]
np.add.at(WB, (np.arange(len(v)), HI + len(cols) - 1 + Lr_p[jr]), wr * np.maximum(axs, 1e-9))
top = np.argsort(-WB, 1)[:, :3]; tw = np.take_along_axis(WB, top, 1); tw /= np.maximum(tw.sum(1, keepdims=True), 1e-9)
Ms = np.array([Mof(b) for b in bones])
Mv = np.einsum('vk,vkij->vij', tw, Ms[top])
vr = np.einsum('vij,vj->vi', np.linalg.inv(Mv), np.c_[v, np.ones(len(v))])[:, :3]
f = f[:, ::-1]
np.savez_compressed('soft_rigged.npz', v=m2ct(vr).astype(np.float32), f=f.astype(np.int32),
                    w_idx=top.astype(np.int16), w_val=tw.astype(np.float32), names=np.array(bones))
np.savez_compressed('skin_posed.npz', v=v.astype(np.float32), f=f.astype(np.int32))
print('saved', f'{time.time()-t0:.0f}s')

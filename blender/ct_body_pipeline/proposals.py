"""振り返り 第 9 節の点検で見つかった点の、直す案の glb を作る（2026-10-17。案の絵のため。本番の形は変えない）。

作業フォルダ（blender/private/work/）で実行する。
  python ../../ct_body_pipeline/proposals.py <元の glb> <出力フォルダ>
出力: <出力フォルダ>/<案>.glb と <案>_skin_posed.npz（膜の展示の姿勢、pose_jar の座標。diag_*.py で検査できる）、proposals.json（数）

案（どれも展示の姿勢 t = 0 の頂点を動かす。glb_deform.py）
- 頭と胴の比（頭骨 ÷ 肩–股関節の直線が、今 0.30、写真 06 で 0.43）
  - head_A: 頭（頭と舌骨の重みの頂点）を後頭の関節のまわりに 1.45 倍
  - head_B: 胴（股関節〜肩）を背骨に沿って 0.69 倍に縮める（肋骨の間が詰まる）。肩から前は縮めずに後ろへ寄せる
  - head_C: 頭 1.2 倍と胴 0.83 倍（あいだ）
- 胴の幅と形（背中から。肩–股関節に対する胴の最大の幅が、今 0.22、生体の背腹 X 線 0.41〜0.42）
  - width_A: 幅も形も X 線に合わせる
  - width_B: 形は X 線、幅は今と X 線のあいだ
  - width_C: 最大の幅は今のまま、形だけ X 線の紡錘形（肩と腰の近くが細くなる）
  幅は左右（Z）だけを、背骨からの距離に倍率を掛けて変える。膜・軟骨・臓器と、骨のうち肋骨の重みの分。椎骨と手足は変えない
- 膜の表面（肋骨ごとの筋、腹の正中の折り目、腰の段、頭の後ろの継ぎ目）
  - surf_A: 胴だけならす（Taubin λ 0.5・μ −0.505、60 回）
  - surf_B: 頭を除く膜をならす（120 回）
  - surf_C: 膜の全部を強くならす（240 回）
"""
import json
import os
import sys
import numpy as np
from PIL import Image
from scipy import sparse
from scipy.ndimage import uniform_filter1d, gaussian_filter1d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from glb_deform import GLB

SRC, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
G0 = GLB(SRC)
NAMES = G0.jname
VERT = [f'v{i:02d}' for i in range(22, 0, -1)]               # 腰（v22）から頸（v01）へ
HEADG = {'head', 'hyoid'}

# ---- 背骨の折れ線と、骨ごとの位置 u（腰 = 0、頭へ増える。ページの座標の長さ）----
chain = [G0.joint_pos(n) for n in VERT] + [G0.joint_pos('head')]
pts = [chain[0]]
for p in chain[1:]:
    if np.linalg.norm(p - pts[-1]) > 1e-6: pts.append(p)
pts = np.array(pts); seg = np.linalg.norm(np.diff(pts, axis=0), axis=1); U = np.r_[0, np.cumsum(seg)]


def P(u):
    u = np.clip(u, 0, U[-1]); return np.stack([np.interp(u, U, pts[:, k]) for k in range(3)], -1)


def project(x):
    us = np.linspace(0, U[-1], 4000); q = P(us); return us[np.argmin(((q - x) ** 2).sum(1))]


vu = {n: U[min(i, len(U) - 1)] for i, n in enumerate(VERT)}
for n in VERT: vu[n] = project(G0.joint_pos(n))
u_head = project(G0.joint_pos('head'))
O = G0.joint_pos('head')                                       # 後頭の関節（頭を大きくする中心）


def joint_u(name):
    if name in HEADG: return u_head
    i = G0.name[name]
    while True:
        nm = G0.J['nodes'][i].get('name')
        if nm in vu: return vu[nm]
        if i not in G0.parent: return 0.0
        i = G0.parent[i]


JU = np.array([joint_u(n) for n in NAMES])
u_sh = project((G0.joint_pos('fL_upper') + G0.joint_pos('fR_upper')) / 2)
u_hp = project((G0.joint_pos('hL_upper') + G0.joint_pos('hR_upper')) / 2)
SH = u_sh - u_hp


def vert_u(G, mesh):
    _, jo, we = G.skin_data(mesh); we = we / we.sum(1, keepdims=True); return (we * JU[jo]).sum(1)


# ---- 頭と胴の比 ----
def head_trunk(G, kh, f):
    for m in G.mesh_names():
        p = G.posed(m); u = vert_u(G, m); h = G.weights_of(m, HEADG)
        p = p + (h * (kh - 1))[:, None] * (p - O)
        un = np.where(u <= u_hp, u, np.where(u <= u_sh, u_hp + f * (u - u_hp), u - (1 - f) * SH))
        p = p + (P(un) - P(u))
        G.set_posed(m, p)


# ---- 胴の幅 ----
def xray_width(fn, y0, y1, xl, xr, ysh, yhp):
    a = np.asarray(Image.open(fn).convert('L')).astype(float); out = []
    for y in range(y0, y1, 5):
        r = uniform_filter1d(a[y - 2:y + 3].mean(0), 5)[xl:xr]; xs = np.where(r > 25)[0]
        if len(xs): out.append(((y - ysh) / (yhp - ysh), (xs[-1] - xs[0]) / (yhp - ysh)))
    return np.array(out)


prof = np.load('inspect/outline_profile.npz')['rows']                       # t, 幅/SH, ...
x46 = xray_width('inspect/melero_p46_0.jpeg', 600, 965, 120, 480, 420, 1185)
x44 = xray_width('inspect/melero_p44_0.jpeg', 600, 965, 150, 480, 375, 1085)
T = np.linspace(0, 1, 101)
wm = np.interp(T, prof[:, 0], prof[:, 1])
xr = (np.interp(T, x46[:, 0], x46[:, 1], left=np.nan, right=np.nan) + np.interp(T, x44[:, 0], x44[:, 1], left=np.nan, right=np.nan)) / 2
ok = ~np.isnan(xr); t0, t1 = T[ok][0], T[ok][-1]
# X 線の無い所（肩と腰の近く: 前肢と腿が重なる）は、端で今の幅へ余弦でつなぐ
xr_full = xr.copy()
xr_full[T < t0] = wm[T < t0] + (xr[ok][0] - wm[T < t0]) * (0.5 - 0.5 * np.cos(np.pi * T[T < t0] / t0))
xr_full[T > t1] = wm[T > t1] + (xr[ok][-1] - wm[T > t1]) * (0.5 - 0.5 * np.cos(np.pi * (1 - T[T > t1]) / (1 - t1)))
xr_full = gaussian_filter1d(xr_full, 3)


def fill_ends(x):
    """X 線の読める範囲（t0〜t1）の外を、端で今の幅へ余弦でつなぐ。"""
    y = x.copy(); a, b = x[ok][0], x[ok][-1]
    y[T < t0] = wm[T < t0] + (a - wm[T < t0]) * (0.5 - 0.5 * np.cos(np.pi * T[T < t0] / t0))
    y[T > t1] = wm[T > t1] + (b - wm[T > t1]) * (0.5 - 0.5 * np.cos(np.pi * (1 - T[T > t1]) / (1 - t1)))
    return gaussian_filter1d(y, 3)


TARGET = {'width_A': xr_full, 'width_B': (wm + xr_full) / 2, 'width_C': fill_ends(xr * wm.max() / np.nanmax(xr))}


def widen(G, target):
    fac = target / wm
    for m in G.mesh_names():
        p = G.posed(m); u = vert_u(G, m); t = (u_sh - u) / SH
        w = np.where((t >= 0) & (t <= 1), np.interp(t, T, fac), 1.0)
        r = G.weights_of(m, {n for n in NAMES if n.startswith('rib')}) if m == 'CH_Skeleton' else np.ones(len(p))
        c = P(u)[:, 2]
        p[:, 2] = c + (p[:, 2] - c) * (1 + (w - 1) * r)
        G.set_posed(m, p)
    return fac


# ---- 膜の表面 ----
def taubin(G, n_iter, region):
    m = 'CH_Skin'; p = G.posed(m); f = G.acc(G.prim(m)['indices']).reshape(-1, 3); n = len(p)
    e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
    A = sparse.coo_matrix((np.ones(len(e) * 2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), (n, n)).tocsr(); A.data[:] = 1
    W = sparse.diags(1 / np.asarray(A.sum(1)).ravel()) @ A
    u = vert_u(G, m); t = (u_sh - u) / SH
    # 0〜1 のなめらかな重み（境目に段を作らない）
    if region == 'trunk':
        mask = np.clip(np.minimum(t + 0.1, 1.1 - t) / 0.1, 0, 1) * (1 - G.weights_of(m, {x for x in NAMES if x[:2] in ('fL', 'fR', 'hL', 'hR')}))
    elif region == 'nohead':
        mask = 1 - G.weights_of(m, HEADG)
    else:
        mask = np.ones(n)
    for _ in range(4): mask = W @ mask
    for _ in range(n_iter):
        for lam in (0.5, -0.505):          # 通す帯 kPB = 1/λ + 1/μ ≈ 0.02: 波長 4〜5 mm（辺 15〜20 本）の肋骨の筋も弱める
            p = p + (lam * mask)[:, None] * (W @ p - p)
    G.set_posed(m, p)


def bumps(G):
    m = 'CH_Skin'; p = G.posed(m); f = G.acc(G.prim(m)['indices']).reshape(-1, 3); n = len(p)
    e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
    A = sparse.coo_matrix((np.ones(len(e) * 2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), (n, n)).tocsr(); A.data[:] = 1
    W = sparse.diags(1 / np.asarray(A.sum(1)).ravel()) @ A
    s = p.copy()
    for _ in range(6): s = 0.5 * s + 0.5 * (W @ s)
    fn = np.cross(p[f[:, 1]] - p[f[:, 0]], p[f[:, 2]] - p[f[:, 0]])
    vn = np.zeros_like(p); np.add.at(vn, f.ravel(), np.repeat(fn, 3, 0)); vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12
    b = np.abs(((p - s) * vn).sum(1)); return b


def save(G, name, info):
    G.save(f'{OUT}/{name}.glb')
    p = G.posed('CH_Skin'); f = G.acc(G.prim('CH_Skin')['indices']).reshape(-1, 3)
    np.savez(f'{OUT}/{name}_skin_posed.npz', v=np.stack([p[:, 0], -p[:, 2], p[:, 1]], 1).astype(np.float32), f=f.astype(np.int32))   # ページ → pose_jar の座標
    b = bumps(G); info['凹凸_95'] = float(np.percentile(b, 95)); info['凹凸_99'] = float(np.percentile(b, 99)); info['凹凸_最大'] = float(b.max())
    k = float(np.load('pose_jar.npz')['k'])
    info['凹凸_単位'] = 'mm'; [info.__setitem__(x, info[x] / k) for x in ('凹凸_95', '凹凸_99', '凹凸_最大')]
    res[name] = info; print(name, info, flush=True)


res = {}
save(GLB(SRC), 'now', {})
for name, kh, f in (('head_A', 1.45, 1.0), ('head_B', 1.0, 0.69), ('head_C', 1.2, 0.83)):
    G = GLB(SRC); head_trunk(G, kh, f); save(G, name, {'頭の倍率': kh, '胴の倍率': f, '頭骨÷肩股_見込み': 0.297 * kh / f})
for name, tg in TARGET.items():
    G = GLB(SRC); fac = widen(G, tg); save(G, name, {'最大の幅/SH': float(tg.max()), '倍率の最大': float(fac.max()), '倍率の最小': float(fac.min())})
for name, it, reg in (('surf_A', 60, 'trunk'), ('surf_B', 120, 'nohead'), ('surf_C', 240, 'all')):
    G = GLB(SRC); taubin(G, it, reg); save(G, name, {'回数': it, '範囲': reg})
np.savez(f'{OUT}/width_targets.npz', T=T, now=wm, **TARGET)
json.dump(res, open(f'{OUT}/proposals.json', 'w'), ensure_ascii=False, indent=1)

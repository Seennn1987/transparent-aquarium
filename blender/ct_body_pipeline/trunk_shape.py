"""胴の横の形を、展示の姿勢で直す（計画書 C の記録 81 の案。方針 B・背の線・C。2026-10-25）。方針 A（背骨を弓に）は姿勢（CH_TRUNK_ARCH）で入れる。

  cd <案の作業フォルダ> && python trunk_shape.py <merged_posed.npz> <出力 merged_posed.npz> <出力の骨.npz> <前の姿勢の skin_posed.npz> <前の pose_jar.npz>

座標: 展示の姿勢。股関節（hL/hR_upper の頭の中点）→ 肩（fL/fR_upper の頭の中点）を u = 0 → 1、その長さ L を 1 とし、背の向き h（背骨の側が +）で測る。
・腹（方針 B、記録 78）: 腹の目標 = 前の姿勢（弓にする前）の腹の線の、u 0.3〜0.7 の中央の高さ + L × B78(u)
  （B78: 股関節 0.04 → u 0.5 で 0 → 肩 0.06 の折れ線を、なめらかにならしたもの）。いまの腹がそれより低い所は動かさない（下げるだけ）
・背の線（記録 80）: いまの背の線の、u 0.80〜1.06 を前後の値から pchip でつないだ線にする（肩の上の段を消す。上げるだけ）
・動かし方: 体軸の背骨の高さ hs(u) を 0 として、腹は hs から腹の線へ 0 → 1、背は hs から背の線へ 0 → 1 の重みで、上の差だけ動かす。u の両端
  （−0.05〜0.05、1.0〜1.1）でなめらかに 0 へ。肩から先（u 0.8〜1.06）の腹の目標は、胸・のどの膜まで 1 本のなめらかな線でつなぐ。膜の頂点（胴の骨に近いもの。手足の骨のほうが近い頂点はその差でなめらかに減らす）、肋骨、軟骨を同じだけ動かす
・ならす（方針 C）: 動かした胴の膜を Taubin（λ 0.5, μ −0.505）で SMOOTH 回ならす。骨（肋骨・軟骨・椎骨）までの距離が min（元, 0.3 mm）より近くなった頂点は戻す
・骨は、動かした姿勢の位置に、その骨の姿勢の行列の逆を掛けて静止の座標へ戻す
"""
import os
import sys
import numpy as np
from scipy.spatial import cKDTree
from scipy.interpolate import PchipInterpolator
from scipy import sparse

src, dst, bones_out, prev_skin, prev_pose = sys.argv[1:6]
SMOOTH = int(os.environ.get('TRUNK_SMOOTH', '30'))
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; k = float(P['k']); MM = k
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
def m2ct(m): m = np.asarray(m, float) / k; return np.stack([-m[..., 2], m[..., 0], -m[..., 1]], -1)
def Mof(PP, n): return PP['M'][[str(x) for x in PP['names']].index(n)]
def posed(PP, n, x): M = Mof(PP, n); return ct2m(x) @ M[:3, :3].T + M[:3, 3]
d = dict(np.load('chameleon_body_ct.npz'))
names = [str(x) for x in d['rig__names']]
def joint(PP, n): return posed(PP, n, d['rig__head'][names.index(n)][None])[0]


def frame(PP):
    hip = (joint(PP, 'hL_upper') + joint(PP, 'hR_upper')) / 2; sh = (joint(PP, 'fL_upper') + joint(PP, 'fR_upper')) / 2
    fw = sh - hip; L = np.linalg.norm(fw); fw /= L
    lat = joint(PP, 'fL_upper') - joint(PP, 'fR_upper'); lat -= fw * (lat @ fw); lat /= np.linalg.norm(lat)
    up = np.cross(lat, fw)
    mid = np.mean([joint(PP, f'v{i:02d}') for i in range(8, 20)], 0)
    if (mid - hip) @ up < 0: up = -up
    return hip, fw, up, lat, L


def uh(fr, x): hip, fw, up, lat, L = fr; r = x - hip; return r @ fw / L, r @ up / L


TRUNK = tuple(f'v{i:02d}' for i in range(1, 24)) + tuple(n for n in names if n.startswith('rib'))
LIMB = tuple(n for n in names if n[:2] in ('fL', 'fR', 'hL', 'hR') and not n.endswith('girdle'))
def bone_pts(PP, sel, step=4):
    X, lab = [], []
    for n in sel:
        if n + '__v' in d: x = posed(PP, n, d[n + '__v'][::step]); X.append(x); lab += [n] * len(x)
    return np.concatenate(X), np.array(lab)


def profile(fr, v, trunk_mask, bins):
    u, h = uh(fr, v)
    top = np.full(len(bins) - 1, np.nan); bot = np.full(len(bins) - 1, np.nan)
    idx = np.digitize(u, bins) - 1
    for b in range(len(bins) - 1):
        m = trunk_mask & (idx == b)
        if m.sum() > 5: top[b] = h[m].max(); bot[b] = h[m].min()
    return top, bot


bins = np.linspace(-0.15, 1.2, 68); uc = (bins[:-1] + bins[1:]) / 2
fr = frame(P)
Z = np.load(src); v = Z['v'].astype(float); f = Z['f']
TP, _ = bone_pts(P, TRUNK); LP, _ = bone_pts(P, LIMB)
dt = cKDTree(TP).query(v, workers=-1)[0]; dl = cKDTree(LP).query(v, workers=-1)[0]
w_trunk = 1 / (1 + np.exp(-(dl - dt) / (1.0 * MM)))          # 胴の骨のほうが近いほど 1
trunk = w_trunk > 0.5
top, bot = profile(fr, v, trunk, bins)
# 前の姿勢（弓にする前）の腹の高さ
P0 = np.load(prev_pose); fr0 = frame(P0); v0 = np.load(prev_skin)['v'].astype(float)
TP0, _ = bone_pts(P0, TRUNK); LP0, _ = bone_pts(P0, LIMB)
t0m = cKDTree(TP0).query(v0, workers=-1)[0] < cKDTree(LP0).query(v0, workers=-1)[0]
_, bot0 = profile(fr0, v0, t0m, bins)
base = np.nanmedian(bot0[(uc > 0.3) & (uc < 0.7)])
B78 = PchipInterpolator([-0.15, 0.0, 0.25, 0.5, 0.75, 1.0, 1.2], [0.06, 0.04, 0.015, 0.0, 0.025, 0.06, 0.08])
belly_t = base + B78(uc)
ok = np.isfinite(top) & np.isfinite(bot)
# 背の線: u 0.80〜1.06 を前後からなめらかにつなぐ
# 首から先（u > 1.0）は頭の膜（かぶとの後ろ）が入るので、つなぐ先は肩の上（u 0.95〜0.99）。段が無ければ、ほぼ元の線のまま
keep = ok & ((uc < 0.80) | ((uc > 0.95) & (uc < 0.99)))
top_s = top.copy(); top_s[ok] = PchipInterpolator(uc[keep], top[keep])(uc[ok])
d_back = np.where(ok, np.maximum(top_s - top, 0), 0) * (os.environ.get('TRUNK_BACK', '1') == '1')   # TRUNK_BACK=0 で背の線を動かさない
d_belly = np.where(ok, np.minimum(belly_t - bot, 0), 0)
def taper(u): a = np.clip((u + 0.05) / 0.1, 0, 1); b = np.clip((1.1 - u) / 0.1, 0, 1); return a * a * (3 - 2 * a) * b * b * (3 - 2 * b)
d_back *= taper(uc)
# 肩から先（u 0.8〜1.1）は、腹の目標を、u 0.8 の目標から胸・のど（u 1.06 の膜）まで 1 本のなめらかな線でつなぎ直す（段を作らない）
okb = np.isfinite(bot)
anch_x = [0.70, 0.75, 0.80, 1.06, 1.10]; anch_y = [base + B78(0.70), base + B78(0.75), base + B78(0.80), np.interp(1.06, uc[okb], bot[okb]), np.interp(1.10, uc[okb], bot[okb])]
front = (uc > 0.80) & (uc < 1.06)
belly_t[front] = PchipInterpolator(anch_x, anch_y)(uc[front])
d_belly = np.where(ok, np.minimum(belly_t - bot, 0), 0) * taper(uc)
hs_tab = np.array([uh(fr, joint(P, f'v{i:02d}')) for i in range(1, 24)]); o = np.argsort(hs_tab[:, 0])
hs = lambda u: np.interp(u, hs_tab[o, 0], hs_tab[o, 1])
for name, arr in (('背を上げる', d_back), ('腹を下げる', d_belly)):
    j = np.argmax(np.abs(arr)); print(f'{name}: 最大 {arr[j] * fr[4] / MM:+.1f} mm（u {uc[j]:.2f}）')


def displace(x, w=None):
    u, h = uh(fr, x); s = hs(u)
    tp = np.interp(u, uc[ok], top[ok]); bt = np.interp(u, uc[ok], bot[ok])
    wb = np.clip((s - h) / np.maximum(s - bt, 1e-6), 0, 1); wt = np.clip((h - s) / np.maximum(tp - s, 1e-6), 0, 1)
    dh = wb * np.interp(u, uc, d_belly) + wt * np.interp(u, uc, d_back)
    if w is not None: dh *= w
    return x + np.outer(dh * fr[4], fr[2])


v1 = displace(v, w_trunk)
# 骨: 肋骨と軟骨
for n in names:
    if n.startswith('rib') and n + '__v' in d:
        x = displace(posed(P, n, d[n + '__v']))
        M = Mof(P, n); d[n + '__v'] = m2ct((x - M[:3, 3]) @ np.linalg.inv(M[:3, :3]).T).astype(d[n + '__v'].dtype)
cb = [str(x) for x in d['cart__bone']]
for key in ('cart__a', 'cart__b'):
    A = d[key].astype(float).copy()
    for i, n in enumerate(cb):
        M = Mof(P, n); x = displace(posed(P, n, A[i:i + 1]))
        A[i] = m2ct((x - M[:3, 3]) @ np.linalg.inv(M[:3, :3]).T)[0]
    d[key] = A.astype(d[key].dtype)
# ならす（方針 C）: 胴の膜だけ
moved_bones, _ = bone_pts(P, [n for n in TRUNK], step=2)
# 動かした後の骨の位置で距離を見る
mb = np.concatenate([posed(P, n, d[n + '__v'][::2]) for n in TRUNK if n + '__v' in d])
kd = cKDTree(mb); d_orig = kd.query(v1, workers=-1)[0]
e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
A = sparse.coo_matrix((np.ones(len(e)), (e[:, 0], e[:, 1])), (len(v1), len(v1))).tocsr(); A = ((A + A.T) > 0).astype(float)
deg = np.asarray(A.sum(1)).ravel(); Wn = sparse.diags(1 / np.maximum(deg, 1)) @ A
u_all, _ = uh(fr, v1); wsm = (w_trunk * taper(u_all))[:, None]
x = v1.copy()
for it in range(SMOOTH):
    for lam in (0.5, -0.505):
        x = x + lam * wsm * (Wn @ x - x)
    if (it + 1) % 10 == 0 or it == SMOOTH - 1:
        dn = kd.query(x, workers=-1)[0]; bad = dn < np.minimum(d_orig, 0.3 * MM)
        x[bad] = v1[bad]
print(f'ならした: {SMOOTH} 回、戻した頂点 {int(bad.sum())}、動いた量の 99% {np.percentile(np.linalg.norm(x - v1, axis=1), 99) / MM:.2f} mm')
np.savez_compressed(dst, v=x.astype(np.float32), f=f.astype(np.int32))
np.savez_compressed(bones_out, **d)
top2, bot2 = profile(fr, x, trunk, bins)
np.savez('trunk_profile.npz', uc=uc, top0=top, bot0=bot, top1=top2, bot1=bot2, belly_t=belly_t, top_t=top_s, base=base, L=fr[4] / MM)
print('saved', dst, bones_out)

"""胸郭を紡錘形に広げる（計画書 C の記録 21、案 2B。2026-10-17 プロデューサー決定）。head_scale.py の後に走らせる。

  python trunk_widen.py <入力の骨.npz> <出力の骨.npz> <幅の目標.npz> <今の膜 soft_rigged.npz> [案の名前=width_B]

幅の目標（proposals.py の width_targets.npz）: 肩（t = 0）〜股関節（t = 1）の位置ごとの、膜の左右の幅 ÷ 肩–股関節。
width_B は、形を生体の背腹 X 線（Melero Jurado 2020 図 5.1.4・5.1.2）の紡錘形にし、幅を今と X 線のあいだにした線（最大 0.30）。
X 線の読める 0.24〜0.72 の外は、端で今の幅へ余弦でつないである。
肋骨（rib*）と肋骨の軟骨（cart__ のうち肋骨の分）の点を、体軸（rig__axis）からの左右の距離（体軸に直角、背の向き rig__dorsal にも直角）に
倍率を掛けて動かす。背腹と前後は動かさない。椎骨・肢帯・手足・頭は動かさない。
倍率は膜の幅の目標から決める: 膜の幅 = 肋骨の幅 + 膜と肋骨のあいだ（今の値のまま）なので、
肋骨の倍率 = （目標の膜の幅 − 今の膜と肋骨のあいだ）÷ 今の肋骨の幅。どれも静止（CT の座標）で、t の 0.02 ごとに測ってならす。
"""
import sys
import numpy as np
from scipy.spatial import cKDTree
from scipy.ndimage import gaussian_filter1d

src, dst, tg, soft = sys.argv[1:5]
case = sys.argv[5] if len(sys.argv) > 5 else 'width_B'
# 付け根で拡大を 0 にする長さ [mm]（記録 22: 付け根まで外へ開いて椎骨とのすき間が 0.49 → 1.05 mm になった）。0 なら記録 21 のまま
ROOT_TAPER_MM = float(sys.argv[6]) if len(sys.argv) > 6 else 0.0
d = dict(np.load(src)); names = [str(n) for n in d['rig__names']]
A = d['rig__axis'].astype(np.float64); D = d['rig__dorsal'].astype(np.float64)
T = np.gradient(A, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
D = gaussian_filter1d(D, 20, axis=0, mode='nearest'); D -= T * (D * T).sum(1, keepdims=True); D /= np.linalg.norm(D, axis=1, keepdims=True)
L = np.cross(T, D)
tree = cKDTree(A)
def hd(n): return d['rig__head'][names.index(n)].astype(np.float64)
i_sh = tree.query((hd('fL_upper') + hd('fR_upper')) / 2)[1]; i_hp = tree.query((hd('hL_upper') + hd('hR_upper')) / 2)[1]


def t_lat(x):
    i = tree.query(x)[1]; return (i - i_sh) / (i_hp - i_sh), ((x - A[i]) * L[i]).sum(1), i


def width_by_t(x, edges):
    t, lat, _ = t_lat(x); w = np.full(len(edges) - 1, np.nan)
    for j, (a, b) in enumerate(zip(edges[:-1], edges[1:])):
        m = (t >= a) & (t < b)
        if m.sum() > 10: w[j] = lat[m].max() - lat[m].min()
    return w


ribk = [k for k in d if k.startswith('rib') and k.endswith('__v')]
rib = np.concatenate([d[k].astype(np.float64) for k in ribk])
cm = np.char.startswith(d['cart__bone'].astype(str), 'rib')
rib_all = np.concatenate([rib, d['cart__a'][cm], d['cart__b'][cm]])
S = np.load(soft); sn = [str(x) for x in S['names']]; own = np.array([sn[i] for i in S['w_idx'][:, 0]])
trunk = np.array([o.startswith('rib') or (o[0] == 'v' and o[1:].isdigit() and int(o[1:]) <= 22) for o in own])
skin = S['v'][trunk].astype(np.float64)
edges = np.linspace(-0.05, 1.05, 56); tc = (edges[:-1] + edges[1:]) / 2
Wr = width_by_t(rib_all, edges); Ws = width_by_t(skin, edges)
G = np.load(tg); ratio = np.interp(tc, G['T'], G[case] / G['now'], left=1, right=1)
ok = ~np.isnan(Wr) & ~np.isnan(Ws)
fac = np.ones_like(tc)
fac[ok] = (ratio[ok] * Ws[ok] - (Ws[ok] - Wr[ok])) / Wr[ok]
fac[(tc < 0) | (tc > 1)] = 1.0
fac = gaussian_filter1d(fac, 1.5)
print('t     肋骨の幅 膜の幅 膜の倍率 肋骨の倍率 [mm]')
for j in range(0, len(tc), 5): print('%5.2f %8.1f %6.1f %8.2f %9.2f' % (tc[j], Wr[j], Ws[j], ratio[j], fac[j]))


def widen(x):
    t, lat, i = t_lat(x); w = np.interp(t, tc, fac, left=1, right=1)
    return x + ((w - 1) * lat)[:, None] * L[i]


def root_weight(x):
    """付け根（体軸に最も近い 3% の点の重心）からの距離で 0 → 1。ROOT_TAPER_MM が 0 なら 1。"""
    if ROOT_TAPER_MM <= 0: return np.ones(len(x))
    _, _, i = t_lat(x); rel = x - A[i]; dist = np.linalg.norm(rel - (rel * T[i]).sum(1, keepdims=True) * T[i], axis=1)
    h = x[dist <= np.percentile(dist, 3)].mean(0)
    u = np.clip(np.linalg.norm(x - h, axis=1) / ROOT_TAPER_MM, 0, 1); return u * u * (3 - 2 * u)


for k in ribk:
    x = d[k].astype(np.float64); w = root_weight(x)
    d[k] = (x + (widen(x) - x) * w[:, None]).astype(d[k].dtype)
for k in ('cart__a', 'cart__b'):
    a = d[k].astype(np.float64); a[cm] = widen(a[cm]); d[k] = a.astype(d[k].dtype)
np.savez_compressed(dst, **d)
np.savez(dst.replace('.npz', '_factor.npz'), t=tc, rib_factor=fac, skin_ratio=ratio, rib_width=Wr, skin_width=Ws)
print('saved', dst)

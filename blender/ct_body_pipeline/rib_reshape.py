"""肋骨の横から見た形を作り直す（計画書 C の記録 49 の案。2026-10-21）。

  python rib_reshape.py <入力の骨.npz> <出力の骨.npz> [--lean=度] [--bow=0.06] [--round=0.30] [--belly=0.10] [図.png]

肋骨ごとに、静止（CT の座標）で、付け根の位置の胴の枠（体軸 rig__axis の向き a = 尾へ、rig__dorsal の逆 h = 腹へ、l = 左右）をとる。
芯の線（付け根から面に沿った距離 0.5 mm ごとの断面の重心、σ 0.75 mm でならす）を (a, l, h) で表し、横から見た形 a(h) だけを作り直す
（前から見た輪の形 l(h) はそのまま）:
・寝る角 --lean: 背側の部分の a/h の傾き = tan(寝る角)。指定しなければ今の傾き（芯の線の深さ 10〜45% の部分の直線のあてはめ）
・腹側の部分: 今の曲がり目の深さ（今の背側・腹側の線の交点）から、今の腹の端の前後の位置へ結ぶ（腹の端は尾へずらさない）
・曲がり目の丸み --round: 2 本の線をなめらかな最小で結ぶ（丸める幅 ≒ 肋骨の深さ × round。写真 04 で全長の 26〜38%）。0 なら V 字の角
・背側の弓なり --bow: 背側の部分を尾の向きへ sin の弓でふくらませる（弦 × bow、写真 04 で 0.04〜0.075）
・お腹のふくらみ --belly: 肩（t 0）〜股関節（t 1）で sin(πt) の山。腹の端の深さを「肩–股関節 × (belly − 今の 0.036)」だけ深くし、
  深さの比 u = h / H の 3 乗で付け根 0 → 腹の端 1 に混ぜる（前から見た輪は下へ伸びる）
頂点は、芯の線の上の同じ距離の点の動きと同じだけ動かす（断面の太さ 0.4 mm ほどなので回転は入れない）。肋骨の軟骨（cart__a・cart__b のうち
肋骨の分）は、最も近い頂点の動きで動かす。付け根から 1.5 mm は動かさない（rib_roots.py で椎骨に差し込んだ所）
"""
import os
import sys
import numpy as np
from scipy import sparse
from scipy.sparse.csgraph import dijkstra, connected_components
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

src, dst = sys.argv[1], sys.argv[2]
opts = dict(a[2:].split('=', 1) for a in sys.argv[3:] if a.startswith('--'))
rest = [a for a in sys.argv[3:] if not a.startswith('--')]
LEAN = float(opts['lean']) if 'lean' in opts else None
BOW = float(opts.get('bow', '0.06')); VENTRAL = opts.get('ventral', 'tip'); DLEAN = float(opts.get('dlean', '0')); TB0 = float(opts.get('tb0', '0.7')); TF0 = float(opts.get('tf0', '-0.2')); TF1 = float(opts.get('tf1', '-0.19')); FRONT_ALL = opts.get('front_all', '0') == '1'; ROUND = float(opts.get('round', '0.30')); BELLY = float(opts.get('belly', '0.10'))
d = dict(np.load(src)); names = [str(n) for n in d['rig__names']]
A = d['rig__axis'].astype(np.float64); D = d['rig__dorsal'].astype(np.float64)
T = np.gradient(A, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
D = gaussian_filter1d(D, 20, axis=0, mode='nearest'); D -= T * (D * T).sum(1, keepdims=True); D /= np.linalg.norm(D, axis=1, keepdims=True)
Lt = np.cross(T, D); tree = cKDTree(A)
def hd(n): return d['rig__head'][names.index(n)].astype(np.float64)
i_sh = tree.query((hd('fL_upper') + hd('fR_upper')) / 2)[1]; i_hp = tree.query((hd('hL_upper') + hd('hR_upper')) / 2)[1]
SH_HP = np.linalg.norm(A[i_hp] - A[i_sh])
vert = np.concatenate([d[k] for k in d if k[0] == 'v' and k.endswith('__v') and k[1:3].isdigit()]).astype(np.float64)
kv = cKDTree(vert)
cm = np.char.startswith(d['cart__bone'].astype(str), 'rib')
ca = d['cart__a'].astype(np.float64); cb = d['cart__b'].astype(np.float64); cbone = d['cart__bone'].astype(str)

# お腹の今のふくらみ（肋骨の腹の端の深さの、肩–股関節での線からのふくらみ）を先に測る
ribs = sorted(k[:-3] for k in d if k.startswith('rib') and k.endswith('__v'))
info = {}
for n in ribs:
    x = d[n + '__v'].astype(np.float64); f = d[n + '__f']
    e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]; w = np.linalg.norm(x[e[:, 0]] - x[e[:, 1]], axis=1)
    G = sparse.coo_matrix((w, (e[:, 0], e[:, 1])), (len(x), len(x))).tocsr(); G = G.maximum(G.T)
    nc, lab = connected_components(G, directed=False); m = lab == np.argmax(np.bincount(lab))
    im = np.where(m)[0]; r0 = im[np.argmin(kv.query(x[m])[0])]
    g = dijkstra(G, indices=r0); g[~np.isfinite(g)] = 0
    root = x[r0]; i = tree.query(root)[1]
    fr = np.c_[T[i], Lt[i], -D[i]]                                     # a 尾へ, l 左右, h 腹へ
    q = (x - root) @ fr
    step = 0.5 / 0.104 * 0.104 if False else None
    s_bins = np.arange(0, g.max() + 1e-9, max(g.max() / 80, 1e-6))
    C = np.array([q[(g >= s0) & (g < s0 + s_bins[1])].mean(0) if ((g >= s0) & (g < s0 + s_bins[1])).sum() else np.full(3, np.nan) for s0 in s_bins])
    ok = ~np.isnan(C[:, 0]); s_c = s_bins[ok] + s_bins[1] / 2; C = gaussian_filter1d(C[ok], 1.5, axis=0, mode='nearest')
    t = (i - i_sh) / (i_hp - i_sh)
    info[n] = dict(x=x, g=g, q=q, fr=fr, root=root, s=s_c, C=C, t=t, m=m)
# 今のお腹のふくらみは、膜の腹の線で測った値（記録 48: 肩–股関節の 0.036）。肋骨の端の深さは付け根から測るので、比べられない
BELLY_NOW = float(opts.get('belly_now', '0.036'))
print('お腹のふくらみ 今 %.3f → %.3f（肩–股関節 %.1f の比）' % (BELLY_NOW, BELLY, SH_HP))

def smax(x, y, r):
    if r <= 0: return np.maximum(x, y)
    return np.maximum(x, y) + r * np.log1p(np.exp(-np.abs(x - y) / r))

panels = []
MODE = opts.get('mode', 'rib')
if MODE == 'field':
    # 場で動かす（記録 51、2026-10-22）: 肋骨ごとに形を決めると、前後の肋骨で動きがばらついて重なり・追い越しが出た（記録 50）。
    #   動きを「胴の位置 t と、付け根からの深さ h」のなめらかな関数にし、どの肋骨にも同じ関数を当てる。隣の肋骨は t が近いので
    #   ほぼ同じだけ動き、並び（前後の順）は変わらない。関数の係数（今の寝る角、曲がり目の深さ、肋骨の深さ）は、肋骨ごとに測って
    #   t に沿ってならした値
    rows_ = []
    for n in ribs:
        I = info[n]; C = I['C']; a, h = C[:, 0], C[:, 2]; H = h.max()
        if H <= 0: continue
        u = h / H; dm = (u > 0.10) & (u < 0.45); vm = (u > 0.60) & (u < 0.95)
        if dm.sum() < 3 or vm.sum() < 3: continue
        kd_ = np.polyfit(h[dm], a[dm], 1); kv_ = np.polyfit(h[vm], a[vm], 1)
        hk = np.clip((kv_[1] - kd_[1]) / (kd_[0] - kv_[0]), 0.2 * H, 0.9 * H) if kd_[0] != kv_[0] else 0.55 * H
        rows_.append((n, I['t'], np.arctan(kd_[0]), hk, H))
    tt_ = np.array([r[1] for r in rows_]); o_ = np.argsort(tt_)
    def smooth_t(vals):
        v = np.array(vals)[o_]; vs = gaussian_filter1d(v, 2.5, mode='nearest'); out = np.empty_like(vs); out[o_] = vs; return out
    lean_s = smooth_t([r[2] for r in rows_]); hk_s = smooth_t([r[3] for r in rows_]); H_s = smooth_t([r[4] for r in rows_])
    par = {r[0]: (lean_s[i], hk_s[i], H_s[i]) for i, r in enumerate(rows_)}
    for n in ribs:
        if n not in par: continue
        I = info[n]; C = I['C']; a, l, h = C[:, 0], C[:, 1], C[:, 2]; t = I['t']
        lean0, hk, Hs = par[n]
        tb = np.clip((t - TB0) / (1.0 - TB0), 0, 1); tb = tb * tb * (3 - 2 * tb); tf = 1 - tb
        tfr = np.clip((t - TF0) / (TF1 - TF0), 0, 1); tf *= tfr * tfr * (3 - 2 * tfr)   # 肩の前後の短い肋骨（3〜5）も寝かせ方を弱める（寝かせると後ろの肋骨を追い越した）
        hc = np.maximum(h, 0)
        S = hc - (hc - hk) * (hc > hk)                                       # min(h, hk)
        S = -smax(-hc, -np.full_like(hc, hk), ROUND * Hs / 6)              # なめらかな min（曲がり目の角を丸める分を兼ねる）
        dk = (np.tan(lean0 + np.radians(DLEAN)) - np.tan(lean0)) * tf if DLEAN else 0.0
        da = dk * S
        da = da + BOW * np.hypot(hk, np.tan(lean0) * hk) * np.sin(np.pi * np.clip(hc / hk, 0, 1)) * (hc <= hk)
        da = da - ROUND * Hs * 0.12 * np.exp(-((hc - hk) / (0.18 * Hs)) ** 2)   # 曲がり目の角を前へ引いて丸める
        da = da * (tfr * tfr * (3 - 2 * tfr) if FRONT_ALL else 1.0)   # --front_all=1: 弓なりと丸めも肩の前後で弱める
        dh = 0.0
        if 0 <= t <= 1 and BELLY > 0: dh = max(0.0, (BELLY - BELLY_NOW) * SH_HP) * np.sin(np.pi * t)
        dhh = dh * np.clip(hc / Hs, 0, 1.3) ** 3
        s_ = I['s']; wroot = np.clip((s_ - 1.5) / 1.5, 0, 1)
        Cn = np.c_[a + da * wroot, l, h + dhh * wroot]
        I['Cn'] = Cn; I['wroot'] = wroot
        if n.endswith('_L') and n[3:5] in ('06', '10', '14', '18'): panels.append((n, C, Cn))
for n in (ribs if MODE != 'field' else []):
    I = info[n]; C = I['C']; a, l, h = C[:, 0], C[:, 1], C[:, 2]
    H = h.max()
    if H <= 0: continue
    u = np.clip(h / H, 0, 1)
    dm = (u > 0.10) & (u < 0.45); vm = (u > 0.60) & (u < 0.95)
    if dm.sum() < 3 or vm.sum() < 3: continue
    kd_ = np.polyfit(h[dm], a[dm], 1); kv_ = np.polyfit(h[vm], a[vm], 1)
    k_d = np.tan(np.radians(LEAN)) if LEAN is not None else kd_[0]
    if os.environ.get('RIB_DEBUG') and n[3:5] in ('04','05','06','07','08'): print('  ', n, '今の寝る角 %.0f°' % np.degrees(np.arctan(kd_[0])), '腹側 %.0f°' % np.degrees(np.arctan(kv_[0])), '深さ %.1f 曲がり目 %.2f' % (H, hk / H))
    if DLEAN:   # --dlean: 今の寝る角に同じ角を足す（肋骨ごとに同じ角を指定すると、今の角の違いの分だけ動きがばらつき、前後で追い越した。記録 51）
        k_d = np.tan(np.arctan(kd_[0]) + np.radians(DLEAN))
    # 後ろの肋骨（股関節の手前 t 0.7〜1.0）は今の傾きへ戻す（同じ角で寝かせると、最後の肋骨が骨盤の中まで尾へ伸びた）
    tb = np.clip((I['t'] - TB0) / (1.0 - TB0), 0, 1); tb = tb * tb * (3 - 2 * tb); k_d = k_d + (kd_[0] - k_d) * tb   # 戻す幅 TB0〜1（急に戻すと前の肋骨が追い越した）
    # 背側の線: 付け根から（a = k_d × h）。腹側の線: 今の傾きで、今の曲がり目（2 本の今の線の交点の深さ）で背側の線と交わる
    hk = np.clip((kv_[1] - kd_[1]) / (kd_[0] - kv_[0]), 0.2 * H, 0.9 * H) if kd_[0] != kv_[0] else 0.55 * H
    # 新しい深さ（お腹のふくらみ）
    t = I['t']; dh = 0.0
    if 0 <= t <= 1 and BELLY > 0: dh = max(0.0, (BELLY - BELLY_NOW) * SH_HP) * np.sin(np.pi * t)
    h_new = h + dh * u ** 3; Hn = H + dh; hk_n = hk * Hn / H
    a_d = k_d * h_new
    # 腹側の線: 新しい曲がり目から、今の腹の端の前後の位置へ（腹の端が尾へずれると、隣の肋骨や腹の正中の軟骨とずれる）
    a_tip = a[np.argmax(h)]; k_v = (a_tip - k_d * hk_n) / max(Hn - hk_n, 1e-6)
    if VENTRAL == 'shift':
        # 腹側も曲がり目と同じだけ尾へずらし、今の傾きのまま（寝る角を大きくしても、同じ深さでは隣の肋骨と同じだけ動くので追い越さない。記録 51）
        k_v = kv_[0]
    a_v = k_d * hk_n + k_v * (h_new - hk_n)
    r = ROUND * Hn / 2.5                                                   # なめらかな最小の丸める幅は約 2.5r
    a_new = -smax(-a_d, -a_v, r)                                           # 2 本のうち前（a の小さい方）を、丸めて
    # 背側の弓なり: 背側の部分（付け根 → 曲がり目）を尾の向きへ
    ud = np.clip(h_new / hk_n, 0, 1)
    chord_len = np.hypot(hk_n, k_d * hk_n)
    a_new = a_new + BOW * chord_len * np.sin(np.pi * ud) * (h_new <= hk_n)
    # 付け根から 1.5 mm（CT の単位は mm ÷ 0.104 ではなく、骨のファイルの長さの単位）は動かさない
    s = I['s']; wroot = np.clip((s - 1.5) / 1.5, 0, 1)
    Cn = np.c_[a + (a_new - a) * wroot, l, h + (h_new - h) * wroot]
    I['Cn'] = Cn; I['wroot'] = wroot
    if n.endswith('_L') and n[3:5] in ('06', '10', '14', '18'): panels.append((n, C, Cn))

# 同じ側の肋骨の間隔を保つ（記録 51、2026-10-22。プロデューサー「肋骨が前後の肋骨と重なっていたり、追い越してクロスしていたりなんておかしくない？」）:
#   胴の中ほどの枠（体軸の向き Tm、背の向き Dm）で横から写し、同じ深さ（0.25 mm ごと）で、後ろの肋骨が前の肋骨より GAP 以上後ろにあるようにする。
#   足りない分は前後に半分ずつ押し分け（付け根の近くは動かさない重み）、全体を 60 回くり返す。押した量は肋骨に沿って σ 1 mm でならす
GAP = float(opts.get('gap', '2.0')); ITER = int(opts.get('iter', '200')); SIDEPASS = opts.get('side', '1') == '1'
im_ = (i_sh + i_hp) // 2; Tm = T[im_]; Dm = -D[im_]
for side in ('L', 'R'):
    R_ = sorted([n for n in ribs if n.endswith('_' + side) and 'Cn' in info[n] and 3 <= int(n[3:5]) <= 21], key=lambda n: int(n[3:5]))
    P_ = {n: info[n]['root'] + info[n]['Cn'] @ info[n]['fr'].T for n in R_}
    P0 = {n: info[n]['root'] + info[n]['C'] @ info[n]['fr'].T for n in R_}       # 今の形（付け根の近くは前の肋骨と重なって並ぶので、要る間隔は今の間隔までにする）
    # 3 次元で押し分ける（横から写した前後の位置だけで見ると、後ろの肋骨の腹側のように体軸に沿って寝た所では深さの向きに重なった）。
    #   同じ側で 5 本先までの組について、b の芯の点から a の芯の線までの距離が要る距離より短ければ、離れる向きに半分ずつ押す。
    #   要る距離 = min(GAP, 今の距離 × 0.8)（付け根の近くのように今も近い所は、今の近さまで許す）
    from scipy.spatial import cKDTree as _K
    def pass3d():
        moved = 0.0
        for ia in range(len(R_)):
            for ib in range(ia + 1, min(ia + 6, len(R_))):
                a_, b_ = R_[ia], R_[ib]
                pa, pb = P_[a_], P_[b_]
                dd, jj = _K(pa).query(pb); d0 = _K(P0[a_]).query(P0[b_])[0]
                short = np.maximum(np.minimum(GAP, 0.8 * d0) - dd, 0)
                if short.max() <= 1e-4: continue
                vec = pb - pa[jj]; vec /= np.maximum(np.linalg.norm(vec, axis=1, keepdims=True), 1e-9)
                push = gaussian_filter1d(short * 0.5, 1.5)[:, None] * vec
                P_[b_] = pb + push * info[b_]['wroot'][:, None]
                acc = np.zeros_like(pa); np.add.at(acc, jj, -push)
                P_[a_] = pa + gaussian_filter1d(acc, 1.5, axis=0) * info[a_]['wroot'][:, None]
                moved = max(moved, short.max())
        return moved
    def pass_side():
        # 横から写して、同じ深さで後ろの肋骨が前の肋骨より前に出ないように（3 次元で離れていても、横へずれて追い越すことがあった）
        moved = 0.0
        for ia in range(len(R_)):
            for ib in range(ia + 1, min(ia + 6, len(R_))):
                a_, b_ = R_[ia], R_[ib]
                pa, pb = P_[a_], P_[b_]; ha, hb = pa @ Dm, pb @ Dm; ga, gb = pa @ Tm, pb @ Tm
                oa = np.argsort(ha); ga_at_b = np.interp(hb, ha[oa], ga[oa], left=np.nan, right=np.nan)
                q0a, q0b = P0[a_], P0[b_]; h0a = q0a @ Dm; o0 = np.argsort(h0a)
                orig = (q0b @ Tm) - np.interp(q0b @ Dm, h0a[o0], (q0a @ Tm)[o0], left=np.nan, right=np.nan)
                need = np.where(np.isfinite(orig) & np.isfinite(ga_at_b), np.minimum(0.5 * GAP, np.where(orig > 0, 0.5 * orig, orig)), -1e9)
                short = np.maximum(np.nan_to_num(ga_at_b + need - gb, nan=-1), 0)
                if short.max() <= 1e-4: continue
                push_b = gaussian_filter1d(short * 0.5, 1.5) * info[b_]['wroot']
                ob = np.argsort(hb); push_a = gaussian_filter1d(np.interp(ha, hb[ob], (short * 0.5)[ob], left=0, right=0), 1.5) * info[a_]['wroot']
                P_[b_] = pb + push_b[:, None] * Tm; P_[a_] = pa - push_a[:, None] * Tm
                moved = max(moved, short.max())
        return moved
    it = -1; moved = 0.0
    for it in range(ITER):
        moved = max(pass3d(), pass_side() if SIDEPASS else 0.0)
        if moved < 0.02: break
    print(side, '間隔を保つ: くり返し %d 回、最後の不足 %.3f' % (it + 1, moved))
    for n in R_: info[n]['Cn'] = (P_[n] - info[n]['root']) @ info[n]['fr']

for n in ribs:
    I = info[n]
    if 'Cn' not in I: continue
    disp_c = I['Cn'] - I['C']; s = I['s']
    disp = np.c_[[np.interp(I['g'], s, disp_c[:, j]) for j in range(3)]].T
    I['x_new'] = I['x'] + disp @ I['fr'].T
    d[n + '__v'] = I['x_new'].astype(d[n + '__v'].dtype)
    I['disp_world'] = disp @ I['fr'].T
# 肋骨の軟骨の端も、最も近い頂点の動きで
for j in np.where(cm)[0]:
    n = cbone[j]
    if n not in info or 'x_new' not in info[n]: continue
    kk = cKDTree(info[n]['x'])
    for arr in (ca, cb):
        arr[j] = arr[j] + info[n]['disp_world'][kk.query(arr[j])[1]]
d['cart__a'] = ca.astype(d['cart__a'].dtype); d['cart__b'] = cb.astype(d['cart__b'].dtype)
np.savez_compressed(dst, **d); print('saved', dst, 'lean', LEAN, 'bow', BOW, 'round', ROUND, 'belly', BELLY)
if rest:
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    fg, axs = plt.subplots(1, len(panels), figsize=(4 * len(panels), 5), squeeze=False)
    for k, (n, C, Cn) in enumerate(panels):
        ax = axs[0, k]; ax.plot(C[:, 0], -C[:, 2], 'k-', label='now'); ax.plot(Cn[:, 0], -Cn[:, 2], 'r-', label='new')
        ax.set_aspect('equal'); ax.set_title(n + ' side (a: tail ->)'); ax.legend()
    fg.savefig(rest[0], dpi=70)

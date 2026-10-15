# A8 背骨を部品から作る（2026-10-15、プロデューサー「背骨も円状の何かが繋がっているように見えており、背骨っぽくありません」「背骨の案を作ってください」）
#  CT に写る椎骨は椎体の外側の薄い石灰化した殻だけで（計画書 第 9 節「A の出口の見直し」）、殻の面を透かすと輪の並ぶ管に見えた。
#  形の出典: BIODIDAC の Squalus sp. の胴の椎骨の写真（横と端から、J. Houseman、CC BY-NC 4.0、https://omeka.uottawa.ca/biodidac/items/show/3946）。
#   椎体は中の詰まった太鼓形（中に砂時計形の模様）、各椎体の上に背の弓（神経弓）の三角の板（椎体の高さの約 0.6 倍）、胴の腹側は小さな突起。
#  位置と大きさは CT から: 椎骨の境目（vert_bounds.npy、元の CT の断面の番号 × 0.5 mm。長すぎる区間は等分）、椎体の半径（a4_spine_field.npy の
#   殻の外の半径の 95%、9 個の中央値でならす）、背骨の中心の高さ（尾の反り: tail_keep_v − tail_bend_offset）。
#  出力: mesh/HH_vert_centra.ply（椎体、Bone の部品）、mesh/HH_vert_arches.ply（背と腹の弓、Cartilage の部品）、a8_vertebrae.json
#  座標: z 吻端→尾、u 左右、v 背−/腹+（mm）。Blender は (z, u, −v)/1000
import hh_paths; hh_paths.cd_work()
import numpy as np, json, os
from scipy import ndimage as nd
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
VX = 0.735; U0, V0 = -180.0, -150.0
S = np.load('a4_spine_field.npy', mmap_mode='r')
vs = V0 + np.arange(S.shape[1]) * VX; us = U0 + np.arange(S.shape[2]) * VX
keep = np.load('tail_keep_v.npy'); off = np.load('tail_bend_offset_mm.npy')
vc = lambda z: np.interp(z * 2, np.arange(len(keep)), keep) - np.interp(z, np.arange(len(off)), off)
GAP = float(os.environ.get('HH_VERT_GAP', 0.5))          # 椎体の間のすき間 mm
ARCH = os.environ.get('HH_VERT_ARCH', '1') == '1'
# 境目: 長すぎる区間（近くの中央値の 1.6 倍より長い）を等分
b = np.load('vert_bounds.npy') * 0.5
L = np.diff(b); med = nd.median_filter(L, size=15)
B = [b[0]]
for i, l in enumerate(L):
    n = max(1, int(round(l / med[i])))
    B += list(b[i] + l * np.arange(1, n + 1) / n)
B = np.array(B)
# 1010 mm より後ろ（尾の先）も、最後の長さで背骨の終わり（殻の写る最後の断面）まで
zend = max(k for k in range(0, S.shape[0], 2) if (np.asarray(S[k]) > 250).any()) * VX
while B[-1] + med[-1] * 0.9 < zend: B = np.append(B, B[-1] + med[-1] * 0.9)
# 半径
def shell_r(z):
    k = int(round(z / VX)); s = np.asarray(S[k]) > 250
    if not s.any(): return np.nan
    vi, ui = np.nonzero(s); r = np.hypot(us[ui], vs[vi] - vc(z)); r = r[r < 12]
    return np.percentile(r, 95) if len(r) > 5 else np.nan
mid = (B[:-1] + B[1:]) / 2
R = np.array([shell_r(z) for z in mid]); ok = np.isfinite(R); R = np.interp(mid, mid[ok], R[ok])
R = nd.median_filter(R, size=9); R = np.clip(R, 1.5, 7.0)
def frame(z):
    dv = (vc(z + 1) - vc(z - 1)) / 2
    t = np.array([1.0, 0.0, dv]); t /= np.linalg.norm(t)
    d = np.array([dv, 0.0, -1.0]); d /= np.linalg.norm(d)            # 背側
    return t, np.array([0.0, 1.0, 0.0]), d
VV = {'c': [], 'a': [], 'r': [], 'cr': []}; FF = {'c': [], 'a': [], 'r': [], 'cr': []}
def add(key, V, F):
    n = sum(len(v) for v in VV[key]); VV[key].append(V); FF[key].append(F + n)
NT, NA = 28, 7
# 2026-10-15 案 C の乱れ（プロデューサー「歯車のような規則正しさを崩してから並べてください」）: 決まった種の、隣どうしでなめらかに変わる乱数で
#  弓の高さ（× 1 ± 0.15 J）、峰の前後の位置（± 0.25 J × 半分の長さ）、幅（× 1 ± 0.15 J）を変え、峰を後ろへ 0.3 J × 高さ寝かせる（神経棘は後ろへ傾く）。
#  J = HH_VERT_JITTER（0 で乱れなし）
J = float(os.environ.get('HH_VERT_JITTER', 0)); rng = np.random.default_rng(20261015)
def smooth_noise(n, w): return nd.gaussian_filter1d(rng.standard_normal(n), w) / max(nd.gaussian_filter1d(rng.standard_normal(4000), w).std(), 1e-6)
NH, NP, NW = (np.clip(smooth_noise(len(mid), 1.5), -2, 2) for _ in range(3))
for i in range(len(mid)):
    z0, z1 = B[i] + GAP / 2, B[i + 1] - GAP / 2; L_ = z1 - z0; zc = mid[i]; r = R[i]
    t, s, d = frame(zc); c = np.array([zc, 0.0, vc(zc)])
    # 椎体: 腰のくびれた太鼓（両端を閉じる）
    th = np.linspace(0, 2 * np.pi, NT, endpoint=False); ta = np.linspace(0, 1, NA)
    rr = r * (0.86 + 0.14 * (2 * ta - 1) ** 2)
    P = []
    for j, a in enumerate(ta):
        ax = (a - 0.5) * L_
        for q in th: P.append(c + ax * t + rr[j] * (np.cos(q) * s + np.sin(q) * d))
    SH = float(os.environ.get('HH_VERT_SHELL', 0))   # 2026-10-15 案 F2: 0 より大きいと、椎体を外側の厚さ SH mm の筒にする（実物で青いのは外側の層）
    F = []
    for j in range(NA - 1):
        for k in range(NT):
            a0 = j * NT + k; a1 = j * NT + (k + 1) % NT; b0 = a0 + NT; b1 = a1 + NT
            F += [[a0, a1, b1], [a0, b1, b0]]
    if SH > 0:
        n0 = len(P)
        for j, a in enumerate(ta):
            ax = (a - 0.5) * L_
            for q in th: P.append(c + ax * t + max(rr[j] - SH, 0.3) * (np.cos(q) * s + np.sin(q) * d))
        P = np.array(P)
        for j in range(NA - 1):              # 内側の面（向きを逆に）
            for k in range(NT):
                a0 = n0 + j * NT + k; a1 = n0 + j * NT + (k + 1) % NT; b0 = a0 + NT; b1 = a1 + NT
                F += [[a0, b1, a1], [a0, b0, b1]]
        for k in range(NT):                  # 両端の輪
            o0, o1 = k, (k + 1) % NT; i0, i1 = n0 + k, n0 + (k + 1) % NT
            F += [[o0, i1, o1], [o0, i0, i1]]
            e = (NA - 1) * NT; o0, o1 = e + k, e + (k + 1) % NT; i0, i1 = n0 + e + k, n0 + e + (k + 1) % NT
            F += [[o0, o1, i1], [o0, i1, i0]]
    else:
        P.append(c - 0.5 * L_ * t); P.append(c + 0.5 * L_ * t); P = np.array(P)
        c0, c1 = NA * NT, NA * NT + 1
        for k in range(NT):
            F.append([c0, (k + 1) % NT, k]); F.append([c1, (NA - 1) * NT + k, (NA - 1) * NT + (k + 1) % NT])
    add('c', P, np.array(F))
    if not ARCH: continue
    # 背の弓（三角の板）と、腹側（胴は小さな突起、尾は腹の弓）
    AH = float(os.environ.get('HH_VERT_ARCHH', 1.2)); SOFT = os.environ.get('HH_VERT_SOFT') == '1'
    # 2026-10-16 案（プロデューサー「尾の骨（血道弓・尾びれの鰭条・肋骨）の案を…作って」）: HH_VERT_HAEMAL=1 で、腹側の弓を、肛門のすぐ後ろ
    #  （腹びれの付け根 464 mm の後ろ、HH_VERT_HAEMAL_Z 既定 490 mm）から 60 mm で HH_VERT_HAEMAL_H 倍（既定 1.4）の高さの血道弓にする
    #  （Griffin 1922・Goodrich 1930: 尾の椎骨の血道弓は左右の板が腹側で合わさり、尾では腹側へ伸びる血道棘になる。ピサの骨格標本の写真でも腹びれから尾びれまで並ぶ）。
    #  前は 520 mm より後ろで 0.66 倍（AH 0.8 × 0.83）
    if os.environ.get('HH_VERT_HAEMAL') == '1':
        _a = np.clip((zc - float(os.environ.get('HH_VERT_HAEMAL_Z', 490))) / 60, 0, 1); _vh = (0.45 * (1 - _a) + float(os.environ.get('HH_VERT_HAEMAL_H', 1.4)) * _a) * r
    else:
        _vh = (AH * 0.83 if zc > 520 else 0.45) * r
    for side, hgt in ((1, AH * r), (-1, _vh)):
        w = 0.35 * r; base = 0.75 * r; hl = (0.5 * L_ + GAP / 2) if SOFT else 0.45 * L_
        if SOFT:   # 2026-10-15 案 C: 付け根を隣とつなぎ（すき間なし）、先を丸めた山（6 点の外形）
            hgt = hgt * (1 + 0.15 * J * NH[i] / 2); w = w * (1 + 0.15 * J * NW[i] / 2)
            pk = 0.25 * J * NP[i] / 2 * hl + 0.3 * J * hgt * (1 if side > 0 else 0.5)      # 峰の位置（後ろへ寝かせる分を含む）
            tri = [(-hl, base), (hl, base), (0.55 * hl + 0.5 * pk, base + 0.55 * hgt), (0.2 * hl + pk, base + 0.92 * hgt), (-0.2 * hl + pk, base + 0.92 * hgt), (-0.55 * hl + 0.5 * pk, base + 0.55 * hgt)]
        else:
            tri = [(-hl, base), (hl, base), (0.0, base + hgt)]            # (軸の位置, 中心からの高さ)
        m = len(tri); P = []
        for su in (-w, w):
            for ax, h in tri: P.append(c + ax * t + su * s + side * h * d)
        P = np.array(P); F = []
        for k in range(1, m - 1): F += [[0, k + 1, k], [m, m + k, m + k + 1]]          # 両面
        for k in range(m): F += [[k, (k + 1) % m, m + (k + 1) % m], [k, m + (k + 1) % m, m + k]]   # 側面
        F = np.array(F)
        if side < 0: F = F[:, ::-1]
        add('a', P, F)

# 2026-10-16 案: 肋骨と尾びれの鰭条（どちらも CT に写らず、文献と骨格標本の写真から作る。部品名に「推定」を付ける: a6a_export_gltf.py の Rib・CaudalRay）
#  板の棒（断面は横 0.9 mm × 前後 0.6 × 椎骨の長さ、先へ細る）を、椎体の表面から外へ置く
def rod(key, p0, p1, wa, wb, side_v, fore_v):
    """p0 → p1 の細る棒。wa・wb: 根元・先の半幅（side_v 方向、mm）。前後の半幅は fore_v の長さ"""
    P = []
    for p, k in ((p0, 1.0), (p1, 0.45)):
        for a, b_ in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            P.append(p + a * (wa if k == 1.0 else wb) * side_v + b_ * k * fore_v)
    F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    V = np.array(P)
    n_ = np.cross(V[F[:, 1]] - V[F[:, 0]], V[F[:, 2]] - V[F[:, 0]]); cen = V.mean(0)
    if (np.einsum('ij,ij->i', n_, V[F].mean(1) - cen) < 0).sum() > 6: F = F[:, ::-1]   # 外向きにそろえる
    add(key, V, F)
# 肋骨（HH_VERT_RIBS=1）: 胴の椎骨（胸びれの付け根 233 mm の後ろ 250 mm 〜 肛門の前 480 mm）の左右に 1 本ずつ。ツノザメ類の肋骨は短い軟骨の棒で、
#  椎体の腹側寄りの横から外・下・後ろへ伸びる（Griffin 1922、Goodrich 1930）。長さ HH_VERT_RIB_L（椎体の半径の倍、既定 2.5）、下へ 35°・後ろへ 25°（向きは推定）
if os.environ.get('HH_VERT_RIBS') == '1':
    RL = float(os.environ.get('HH_VERT_RIB_L', 2.5))
    for i in range(len(mid)):
        zc = mid[i]
        if not 250 <= zc <= 480: continue
        r = R[i]; L_ = B[i + 1] - B[i]; t, s_, d = frame(zc); c = np.array([zc, 0.0, vc(zc)])
        for sg in (1, -1):
            out = sg * s_ * np.cos(np.radians(35)) - d * np.sin(np.radians(35)); out = out * np.cos(np.radians(25)) + t * np.sin(np.radians(25)); out /= np.linalg.norm(out)
            base = c + 0.85 * r * (sg * s_ * np.cos(np.radians(35)) - d * np.sin(np.radians(35)))
            fore = t - out * (t @ out); fore /= np.linalg.norm(fore); side = np.cross(out, fore)
            rod('r', base, base + RL * r * out, 0.5, 0.3, side, 0.25 * L_ * fore)
# 尾びれの鰭条（HH_VERT_RADIALS=1）: 尾びれの前（737 mm）〜背骨の終わりの椎骨ごとに、背骨の上と下に 1 本ずつ。後ろへ 40° 寝かせ（向きは推定）、
#  長さは、椎体の表面から体の膜（a5_S.npy、正中の面 u = 0）の縁までの HH_VERT_RAD_F 倍（既定 0.7）。2 mm より短いものは置かない。
#  ピサの骨格標本の写真で、尾びれの中に長い棒が背骨の上下にすき間なく並ぶ（計画書 第 9 節「胴の形と長さ、尾の腹側の骨の検証」）
if os.environ.get('HH_VERT_RADIALS') == '1':
    SK = np.load('a5_S.npy', mmap_mode='r'); RF = float(os.environ.get('HH_VERT_RAD_F', 0.7)); nrad = 0
    def to_skin(c, u):
        k = int(round(c[0] / VX)); last = 0.0
        for st in np.arange(0, 160, 0.5):
            p = c + st * u; k = int(round(p[0] / VX)); iv = int(round((p[2] - V0) / VX)); iu = int(round((0 - U0) / VX))
            if not (0 <= k < SK.shape[0] and 0 <= iv < SK.shape[1]) or not SK[k, iv, iu]: return st
        return 160.0
    for i in range(len(mid)):
        zc = mid[i]
        if zc < 737: continue
        r = R[i]; L_ = B[i + 1] - B[i]; t, s_, d = frame(zc); c = np.array([zc, 0.0, vc(zc)])
        for sd in (1, -1):
            u = sd * d * np.cos(np.radians(40)) + t * np.sin(np.radians(40)); u /= np.linalg.norm(u)
            e = to_skin(c, u); ln = RF * (e - r)
            if ln < 2: continue
            fore = t - u * (t @ u); fore /= np.linalg.norm(fore)
            rod('cr', c + r * u, c + (r + ln) * u, 0.45, 0.25, s_, 0.3 * L_ * fore); nrad += 1
    print('caudal radials', nrad)
def signed_vol(V, F):
    a, b_, c_ = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    return np.einsum('ij,ij->i', a, np.cross(b_, c_)).sum() / 6
info = dict(source='BIODIDAC Squalus sp. trunk vertebrae photo (J. Houseman, CC BY-NC 4.0) https://omeka.uottawa.ca/biodidac/items/show/3946; positions and radii from CT',
            vertebrae=int(len(mid)), z_mm=[round(float(B[0]), 1), round(float(B[-1]), 1)], bounds_mm=[round(float(x), 2) for x in B],
            spine_v_mm={str(int(z)): round(float(vc(z)), 2) for z in range(0, 1001, 5)}, length_median_mm=round(float(np.median(np.diff(B))), 2),
            radius_mm={str(z): round(float(np.interp(z, mid, R)), 1) for z in (150, 300, 500, 700, 900)}, gap_mm=GAP, arches=ARCH, jitter=J, seed=20261015)
for key, name in (('c', 'HH_vert_centra'), ('a', 'HH_vert_arches'), ('r', 'HH_vert_ribs'), ('cr', 'HH_vert_radials')):
    if not VV[key]: continue
    V = np.concatenate(VV[key]); F = np.concatenate(FF[key])
    Vb = np.stack([V[:, 0], V[:, 1], -V[:, 2]], 1) / 1000.0         # Blender の座標（v を反転すると向きも反転する）
    vol = signed_vol(Vb, F)
    if vol < 0: F = F[:, ::-1]                                       # 外向きにそろえる
    write_ply(f'{OUT}/{name}.ply', Vb, F[:, ::-1])                   # write_ply は面を並べ替えて書く（marching cubes 用）
    info[name] = dict(faces=int(len(F)), volume_ml=round(abs(vol) * 1e6, 2))
if not ARCH and os.path.exists(f'{OUT}/HH_vert_arches.ply'): os.remove(f'{OUT}/HH_vert_arches.ply')
json.dump(info, open('a8_vertebrae.json', 'w'), ensure_ascii=False, indent=1); print(info)

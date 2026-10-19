# A5 胸びれの軟骨を、透明標本の写真のつくりから作る（2026-10-20 案。HH_PECT_PHOTO=1 のときだけ。a5d_pect_membrane.py の後）
#  プロデューサー「他のヒレに進んでください」（腹びれの直しの後）。ひれの形を見本と比べた結果（計画書「ひれの軟骨の形を見本と比べる」）:
#  いまの胸びれの軟骨（CT）は付け根から先へ斜めの帯だけで、付け根から先までの 40% の所で膜の前後 81 mm のうち 38 mm、80% の所で 49 mm のうち 4 mm。
#  前の縁の側に軟骨が無い。実物（Summers のウチワシュモクザメの透明標本）は 3 節の放射軟骨が扇に開き、前の縁から後ろの縁まで幅いっぱいに並ぶ
#  ひれの外形（膜）は変えない: a5d と同じ NOAA の写真の外形・付け根・向き（後ろへ 35°・下へ 15°）・厚さ（付け根 4 mm → 先 1.5 mm）。ただし CT の軟骨を足してふくらませない
#  軟骨の形の元: Summers の写真（© Adam Summers、手元で見るだけ、git に入れない）の、下に写る胸びれ。写真 2100 × 1400 px の x 1150〜1450・y 560〜1000 を 4 倍にし、
#   体軸が横になるよう 20.4° 回して、赤の値が周り（15 px）より 18 以上暗い所か、赤の値 < 120 を軟骨とする（淡い青の放射軟骨は赤の値だけでは取れない）。
#   肩帯（回した絵の x 1250 より右）と、胸びれより上（y 1290 より上）は使わない
#  置き方: 写真の付け根（x 1240・y 1360）をひれの付け根に合わせ、付け根のまわりの向きで割り振る。写真で後ろの縁（内側）〜前の縁の向きの幅を、外形の後ろの縁〜前の縁の
#   向きの幅へ（両端は ANG_IN 度内側）。半径は、それぞれの向きで写真の軟骨のいちばん遠い所が、外形の付け根から縁までの HH_PECT_REACH（既定 0.80）に来るように。
#   0.80 は前の版の軟骨の届き（82%）に合わせた。plesodic の胸びれは放射軟骨がひれの 50% より先まで届く（Compagno 1988、Maia, Wilga & Lauder 2012）
import hh_paths; hh_paths.cd_work()
import numpy as np, json, os
from scipy import ndimage as nd
from skimage.measure import marching_cubes
from PIL import Image
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
PHOTO = os.path.join(hh_paths.ROOT, 'docs', 'references', 'hammerhead', 'ref_summers_bonnethead_cleared_stained.jpg')
if not os.path.exists(PHOTO): raise SystemExit(f'見本の写真がありません（git に入れていない）: {PHOTO}')
REACH = float(os.environ.get('HH_PECT_REACH', 0.80)); ANG_IN = float(os.environ.get('HH_PECT_ANG_IN', 3.0))
VX = 0.735; U0, V0 = -180.0, -150.0
# 1. 写真の胸びれの軟骨（回した絵の画素）
im = Image.open(PHOTO).convert('RGB').crop((1150, 560, 1450, 1000)); im = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)
im = im.rotate(20.4, resample=Image.BICUBIC, fillcolor=(255, 255, 255), expand=True)
Rr = np.asarray(im)[..., 0].astype(float); H, W = Rr.shape; yy, xx = np.mgrid[0:H, 0:W]
m = (((nd.grey_closing(Rr, size=(15, 15)) - Rr) > 18) | (Rr < 120)) & (yy > 1290) & (xx < 1250) & (Rr < 215)
cl, n = nd.label(m); sz = nd.sum(m, cl, range(1, n + 1)); m = np.isin(cl, 1 + np.nonzero(sz >= 40)[0])
XB, YB = 1240.0, 1360.0
py_, px_ = np.nonzero(m); dxp, dyp = px_ - XB, py_ - YB
psi = np.degrees(np.arctan2(dyp, -dxp)); rp = np.hypot(dxp, dyp)       # 後ろ（−x）から測る向き。前の縁（外・下）が +
# 2. 膜の外形と板（a5d と同じ式）
d = np.load('photo_pect.npz'); fin = d['L']; L0, R0, L1, R1 = d['trunk']
tl, tr = np.array([326, 86.]), np.array([554, 66.]); ang = np.arctan2(tr[1] - tl[1], tr[0] - tl[0]); mid = (tl + tr) / 2; s_ph = 266.0 / np.linalg.norm(tr - tl)
def to_mm(x, y):
    p = np.stack([x - mid[0], y - mid[1]], 1); c, sn = np.cos(-ang), np.sin(-ang)
    q = np.stack([p[:, 0] * c - p[:, 1] * sn, p[:, 0] * sn + p[:, 1] * c], 1) * s_ph
    return -q[:, 0], q[:, 1]
fy, fx = np.nonzero(fin); pu, pz = to_mm(fx.astype(float), fy.astype(float))
a_ = (fy - 195) / 110.0; edge = L0 * (1 - a_) + L1 * a_; base = np.abs(fx - edge) <= 2
Bp = np.array([pu[base].mean(), pz[base].mean()])
dd = np.hypot(pu - Bp[0], pz - Bp[1]); tip = np.array([pu[np.argmax(dd)], pz[np.argmax(dd)]])
ex = (tip - Bp) / np.linalg.norm(tip - Bp); ey = np.array([ex[1], -ex[0]])
if ey[1] > 0: ey = -ey
X = (pu - Bp[0]) * ex[0] + (pz - Bp[1]) * ex[1]; Y = (pu - Bp[0]) * ey[0] + (pz - Bp[1]) * ey[1]
pe = json.load(open('pect_posed.json')); B = np.array(pe['base_right_uzv'])
sd, dn = np.radians(35), np.radians(15)
a1 = np.array([np.cos(dn) * np.cos(sd), np.cos(dn) * np.sin(sd), np.sin(dn)])
nv = np.array([0, 0, 1.0]); nv = nv - np.dot(nv, a1) * a1; nv /= np.linalg.norm(nv); a2 = np.cross(nv, a1)
if a2[1] > 0: a2 = -a2
t = float(json.load(open('a5_pectmem.json'))['surface_from_base_mm']); P0 = B + (t - 6.0) * a1
G = 0.25
x0, y0 = X.min() - 4, Y.min() - 4; GX, GY = np.meshgrid(np.arange(x0, X.max() + 4, G), np.arange(y0, Y.max() + 4, G), indexing='ij')
O = np.zeros(GX.shape, bool); O[np.round((X - x0) / G).astype(int), np.round((Y - y0) / G).astype(int)] = True
O = nd.binary_fill_holes(nd.binary_closing(O, iterations=int(1.5 / G) + 2))
O = nd.gaussian_filter(O.astype(np.float32), 0.5 / G) > 0.5               # 外形（写真の画素の段を 0.5 mm ならす）
# 3. 軟骨を外形へ割り振る。付け根のまわりの向きで割り振る版は、放射軟骨が 1 本の曲がった線から羽のように生えた形になった（実物は基底の軟骨に沿って放射軟骨が並ぶ）。
#  腹びれ（a5f）と同じく、ひれの長さの向き（付け根 → 先、写真では付け根 x 1240 → ひれのいちばん後ろの端）の各位置で、
#  写真の内側の縁（上の縁: 後鰭基軟骨の側）〜放射軟骨の先を、外形の後ろの縁〜前の縁へ割り振る。前の縁の側は HH_PECT_REACH（既定 0.80）より先を空ける
# 写真のひれは斜め（付け根から左下）に伸びるので、付け根のまわりに回して、付け根 → いちばん遠い先を −x の向きにそろえてから列ごとに読む
_py, _px = np.nonzero(m); _k = np.argmax(np.hypot(_px - XB, _py - YB)); ROT_P = float(np.degrees(np.arctan2(_py[_k] - YB, -(_px[_k] - XB))))
m = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).rotate(-ROT_P, resample=Image.BILINEAR, center=(XB, YB))) > 127
cols = np.arange(W); has = m.any(0)
_ymin = np.where(has, np.argmax(m, 0), 0).astype(float); _ymax = np.where(has, H - 1 - np.argmax(m[::-1], 0), 0).astype(float)
XL = float(cols[has].min()); XR = XB; kc = has & (cols >= XL) & (cols <= XR)
# 内側の縁の線は、写真の内側の後ろの隅で巻き込む放射軟骨（回した絵で上へ飛び出す所）に引っぱられないよう、線より 30 px 以上上の列を除いて 2 回当てはめる。
#  線より 10 px 以上上の軟骨は使わない（そのままでは、巻き込みがひれの真ん中に塊として写った）
_cf = np.polyfit(cols[kc], _ymin[kc], 3)
for _ in range(2):
    _ok = kc & (_ymin >= np.polyval(_cf, cols) - 30); _cf = np.polyfit(cols[_ok], _ymin[_ok], 3)
ymed = np.polyval(_cf, cols.astype(float)); ytip = np.polyval(np.polyfit(cols[kc], _ymax[kc], 3), cols.astype(float))
m &= yy >= np.interp(xx, cols, ymed) - 10
Xmin_o, Xmax_o = float(GX[O].min()), float(GX[O].max())
kx = np.round((GX[O] - x0) / G).astype(int); nb = GX.shape[0]
ylo = np.full(nb, np.inf); yhi = np.full(nb, -np.inf); np.minimum.at(ylo, kx, GY[O]); np.maximum.at(yhi, kx, GY[O])
okb = np.isfinite(ylo); xc = x0 + np.arange(nb) * G
ylo = nd.median_filter(np.interp(xc, xc[okb], ylo[okb]), 9); yhi = nd.median_filter(np.interp(xc, xc[okb], yhi[okb]), 9)
Ylo = np.interp(GX, xc, ylo); Yhi = np.interp(GX, xc, yhi)
xsrc = XR - ((GX - Xmin_o) / (Xmax_o - Xmin_o)) * (XR - XL)   # 外形の付け根の側の端（前の縁は付け根の中点より前から始まる）〜先
tau = (GY - Ylo) / np.maximum(REACH * (Yhi - Ylo), 0.5)
ysrc = np.interp(xsrc, cols, ymed) + tau * (np.interp(xsrc, cols, ytip) - np.interp(xsrc, cols, ymed))
cart2 = (nd.map_coordinates(m.astype(np.float32), [ysrc.ravel(), xsrc.ravel()], order=1, cval=0).reshape(GX.shape) > 0.5) & (tau >= 0) & (tau <= 1) & O
cart2 &= nd.binary_erosion(O, iterations=int(1.0 / G))
pp0 = pp1 = pm0 = pm1 = 0.0
# 4. 厚さ（片側、mm）と面
dt = nd.distance_transform_edt(cart2) * G; hc = np.clip(nd.gaussian_filter(dt, 0.5), 0, 1.5); hc[~cart2] = 0
hm = np.clip(4.0 - 2.5 * np.clip(GX, 0, None) / max(GX[O].max(), 1), 1.5, 4.0) / 2
hm = np.maximum(hm, nd.gaussian_filter(nd.maximum_filter(np.where(cart2, hc + 0.6, 0), size=int(2.0 / G)), 0.5 / G))
hm = np.maximum(hm, np.where(cart2, hc + 0.5, 0))
NW = int(np.ceil(3.0 / G)); gw = np.arange(-NW, NW + 1) * G
def solid(h2, region):
    F = (h2[..., None] - np.abs(gw)[None, None, :]); F[~region] = -1
    return nd.gaussian_filter(F.astype(np.float32), [0.6, 0.6, 0.6])
def write(name, F, side):
    v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=-1), 0.0, allow_degenerate=False); v = v - 1
    Xv = x0 + v[:, 0] * G; Yv = y0 + v[:, 1] * G; Wv = v[:, 2] * G - NW * G
    Q = P0[None] + Xv[:, None] * a1 + Yv[:, None] * a2 + Wv[:, None] * nv   # (u, z, v) の mm
    Vb = np.stack([Q[:, 1], side * Q[:, 0], -Q[:, 2]], 1) / 1000.0         # Blender（x = z、y = u、z = −v）。左は鏡映
    vol = np.einsum('ij,ij->i', Vb[f[:, 0]], np.cross(Vb[f[:, 1]], Vb[f[:, 2]])).sum() / 6
    if vol > 0: f = f[:, ::-1]                                             # write_ply が裏返して書くので、内向きにそろえて渡す
    write_ply(f'{OUT}/{name}.ply', Vb, f); return round(abs(vol) * 1e6, 3), len(f)
Fc = solid(hc, cart2); Fm = solid(hm, O)
rep = {'reach': REACH, 'photo_cols': [XL, XR], 'photo_rot_deg': round(ROT_P, 1),
       'cart_area_mm2': round(float(cart2.sum() * G * G), 1), 'memb_area_mm2': round(float(O.sum() * G * G), 1), 'cart_in_memb': round(float(cart2.sum() / O.sum()), 3)}
for side, sfx in ((1, 'R'), (-1, 'L')):
    rep[f'cart_{sfx}'] = write(f'HH_pect_{sfx}', Fc, side); rep[f'memb_{sfx}'] = write(f'HH_pectmem_{sfx}', Fm, side)
json.dump(rep, open('a5_pectphoto.json', 'w'), ensure_ascii=False, indent=1); print(rep)

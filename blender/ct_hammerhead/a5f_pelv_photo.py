# A5 腹びれの軟骨と膜を、透明標本の写真の形から作る（2026-10-19 案。HH_PELV_PHOTO=1 のときだけ。a5e_pelv_membrane.py の後）
#  プロデューサー「腹びれの軟骨と膜を、腰帯・基鰭軟骨・放射軟骨のつくりに合わせて直す案を、見本・前の版と並べて見せてください」
#  前の版は、CT の腹びれ（閾値 175）がひれの付け根の前の内側に固まり、膜は軟骨の外形を 5 mm 広げて 1.4 倍にした丸い形で、
#  横へ 60% の所で膜の前後 53 mm のうち軟骨 6 mm だった（計画書「ひれの軟骨の形を見本と比べる」）。CT の右の腹びれは丸まった 1 枚の膜のように写り、棒に分かれない
#  見本: ウチワシュモクザメ（Sphyrna tiburo、シュモクザメ科）の透明標本の写真（© Adam Summers、手元で見るだけ、git に入れない）の、下に写る腹びれ。
#   写真 2100 × 1400 px の x 800〜1020・y 520〜730 を 4 倍にし、体軸が横になるよう 20.4° 回して、赤の値 < 140 を軟骨とする。
#   腰帯は正中（回した絵の y 565）まで、交尾器（クラスパー、x < 470 かつ y < 580 の後ろへ伸びる 2 本の棒）は、この CT の標本の性が分からないので入れない
#  形の移し方: 写真は腹から見た絵なので、ひれの板（a5e と同じ e1・e2、付け根 B）の中の点を、腹から見たときに写真の点と同じ所に来るように置く。
#   写真の腰帯と基鰭軟骨のつなぎ目（回した絵の x 740・y 640）を付け根 B に。大きさは、膜の付け根から先までの長さを前の版の膜（a5_pelvmem.json）と同じにする
#  厚さ: 軟骨は、写真の形の中で縁からの距離（mm）を厚さの半分にする（細い放射軟骨は薄く、腰帯・基鰭軟骨は厚く。上限 1.5 mm、片側）。
#   膜は付け根 3 mm → 先 1.5 mm（a5e と同じ）で、軟骨のある所は軟骨より 1 mm 厚く。膜の外形は軟骨の扇を閉じて、縁の外へ HH_PELV_FRINGE（付け根から先までの長さの割合、既定 0.10）広げる
import hh_paths; hh_paths.cd_work()
import numpy as np, json, os
from scipy import ndimage as nd
from skimage.measure import marching_cubes
from PIL import Image
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
PHOTO = os.path.join(hh_paths.ROOT, 'docs', 'references', 'hammerhead', 'ref_summers_bonnethead_cleared_stained.jpg')
if not os.path.exists(PHOTO): raise SystemExit(f'見本の写真がありません（git に入れていない）: {PHOTO}')
FRINGE = float(os.environ.get('HH_PELV_FRINGE', 0.10))
# 正中のすき間（片側、mm）: a6a で付け根を体の幅に合わせて動かし下へ回すと、0.3 mm では左右の膜が正中で重なった（重なる所は道のりを 2 回数える）
MIDGAP = float(os.environ.get('HH_PELV_MIDGAP', 0.6))   # 下へ回して横へ動かした後の、正中から膜の内側の縁まで
# 1. 写真の腹びれの形（回した絵の画素）
im = Image.open(PHOTO).convert('RGB').crop((800, 520, 1020, 730)); im = im.resize((im.width * 4, im.height * 4), Image.LANCZOS)
im = im.rotate(20.4, resample=Image.BICUBIC, fillcolor=(255, 255, 255), expand=True)
Rch = np.asarray(im)[..., 0].astype(float); H, W = Rch.shape; yy, xx = np.mgrid[0:H, 0:W]
m = (Rch < 140) & (yy >= 565) & ~((xx < 470) & (yy < 580))
cl, n = nd.label(m); sz = nd.sum(m, cl, range(1, n + 1)); m = np.isin(cl, 1 + np.nonzero(sz >= 40)[0])
XJ, YJ, YAX = 740.0, 640.0, 565.0
# 輪の内側（左右の基鰭軟骨にはさまれた所）は体で、ひれの膜ではない。両側の軟骨を閉じて埋めた中で、軟骨の無い所を輪の内側とする（回した絵の x 600・y 560 を含む塊）
_all = (Rch < 140); _all = np.isin(nd.label(_all)[0], [nd.label(_all)[0][560, 640]]) | _all
_fill = nd.binary_fill_holes(nd.binary_closing(_all, iterations=4)); _hl, _ = nd.label(_fill & ~nd.binary_dilation(_all, iterations=2))
HOLE = (_hl == _hl[560, 600]) if _hl[560, 600] > 0 else np.zeros_like(_all)
py_, px_ = np.nonzero(m); A = (px_ - XJ); Lt = (py_ - YJ)          # A: 前（頭）へ +、Lt: 外（正中から離れる）へ +（画素）
# 2. ひれの板（a5e と同じ）
P = np.load('a4_pelv175_pts.npz')['right'].astype(float) if os.environ.get('HH_PELV_CT175') == '1' else np.load('pelvic_posed.npz')['right'].astype(float)
c = P.mean(0); w_, Vv = np.linalg.eigh(np.cov((P - c).T)); e1, e2, nrm = Vv[:, 2], Vv[:, 1], Vv[:, 0]
B = np.array(json.load(open('pelvic_info.json'))['right_base_uzv'])
if np.dot(c - B, e1) < 0: e1 = -e1
# (u, z, v): u = 右へ +（右のひれは u > 0）、z = 吻端から後ろへ +。腹から見た絵の (前, 外) = (−z, +u)
# 下へ回す（HH_PELV_DOWN、度）は a6a でなくここで、CT の付け根 B を中心に体軸のまわりに回す（a6a は膜の内側の縁の近くを中心に回すので、写真の形では後ろの深い所が正中へ 5 mm 寄り、左右の膜が重なった）
DOWN = np.radians(float(os.environ.get('HH_PELV_DOWN', 0) or 0))
# 体の幅を参考に合わせた分（a6a の dy と同じ式。a6a は膜の内側の縁の近くで測るので、写真の形では 3 mm 寄って左右が正中で重なった）も、ここで付け根 B の所の値で動かす
_tw = json.load(open('a5_trunk_width.json')) if os.path.exists('a5_trunk_width.json') else None
DY = (np.interp(B[1], _tw['z_mm'], _tw['width_new_mm']) - np.interp(B[1], _tw['z_mm'], _tw['width_old_mm'])) / 2 if _tw else 0.0
def rot(Q):   # (u, z, v) の mm。v は腹へ +。右のひれの先（u が大きい）が下へ。回した後に DY だけ横へ
    du, dv = Q[..., 0] - B[0], Q[..., 2] - B[2]
    R_ = Q.copy(); R_[..., 0] = B[0] + du * np.cos(DOWN) - dv * np.sin(DOWN) + DY; R_[..., 2] = B[2] + du * np.sin(DOWN) + dv * np.cos(DOWN); return R_
Mp = np.array([[-e1[1], -e2[1]], [e1[0], e2[0]]])                   # (X, Y) → (前, 外) の mm
Minv = np.linalg.inv(Mp)
L_old = float(json.load(open('a5_pelvmem.json'))['fin_len_mm'])
# 膜の外形（画素）: 腰帯（つなぎ目より前）を除いた軟骨を閉じて穴を埋める
fin_px = m & (xx < XJ - 5)
memb_px = nd.binary_fill_holes(nd.binary_closing(fin_px, iterations=10)) & ~HOLE
GIRD_px = m & (xx >= XJ - 5)                                          # 腰帯（基鰭軟骨とのつなぎ目より前）
my_, mx_ = np.nonzero(memb_px)
XYm = (Minv @ np.stack([mx_ - XJ, my_ - YJ])).T                     # 1 画素 = 1 mm としたときの板の中の点
# 大きさ: 膜の板の中の面積を前の版の膜（a5e の外形: CT の軟骨を 5 mm 広げて HH_PELV_SCALE 倍）と同じにする。
#  長さ（付け根から先）をそろえると、写真のひれは体軸の向きに長いので 130 mm になった（前の版の 1.6 倍）
_X = (P - B) @ e1; _Y = (P - B) @ e2; _G = 0.4; _ps = float(os.environ.get('HH_PELV_SCALE', '1') or 1)
_xi = np.round(_X / _G).astype(int); _yi = np.round(_Y / _G).astype(int); _P2 = np.zeros((_xi.max() - _xi.min() + 41, _yi.max() - _yi.min() + 41), bool); _P2[_xi - _xi.min() + 20, _yi - _yi.min() + 20] = True
_P2 = nd.binary_dilation(nd.binary_fill_holes(nd.binary_closing(_P2, iterations=6)), iterations=int(5 / _G)); AREA_OLD = _P2.sum() * _G * _G * _ps * _ps
# 3. 板の中の格子（0.25 mm）に写真の形を写す。大きさ s（mm / 画素）は、膜の面積が AREA_OLD になるまで 3 回直す
G = 0.25
def build(s):
    global to_px, x0, y0, GX, GY
    def to_px(X, Y):   # 板の中の mm → 回した絵の画素
        fa = Mp @ np.stack([X, Y]) / s; return fa[0] + XJ, fa[1] + YJ
    XYc = (Minv @ np.stack([A, Lt])).T * s
    pad = L_old * FRINGE + 6
    x0, x1 = XYc[:, 0].min() - pad, XYc[:, 0].max() + pad; y0, y1 = XYc[:, 1].min() - pad, XYc[:, 1].max() + pad
    gx = np.arange(x0, x1, G); gy = np.arange(y0, y1, G); GX, GY = np.meshgrid(gx, gy, indexing='ij')
    qx, qy = to_px(GX.ravel(), GY.ravel())
    sample = lambda mask: nd.map_coordinates(mask.astype(np.float32), [qy, qx], order=1, cval=0).reshape(GX.shape) > 0.5
    cart2 = sample(m & ~GIRD_px); memb2 = sample(memb_px)
    U = rot(B[None, None] + GX[..., None] * e1 + GY[..., None] * e2)[..., 0]   # 回した後の正中からの距離（右が +）
    cart2 &= U > MIDGAP + 1.2   # 膜の縁より 1.2 mm 内まで（後ろで寄り合う基鰭軟骨の先が膜の縁の外に出ないように）
    # 膜の縁を広げてならす（ぎざぎざにしない）。縁の幅は付け根から先までの長さ（前の版）の FRINGE
    memb2 = nd.binary_dilation(memb2 & (U > MIDGAP), iterations=int(round(L_old * FRINGE / G)))
    memb2 = (nd.gaussian_filter(memb2.astype(np.float32), 1.0 / G) > 0.5)
    memb2 = (memb2 | nd.binary_dilation(cart2, iterations=int(1.0 / G))) & (U > MIDGAP)   # 基鰭軟骨の内側の縁も 1 mm 以上覆う（輪の内側を除いたとき、縁の頂点が膜の外に出た）
    return cart2, memb2
s = 0.25
for _ in range(3):
    cart2, memb2 = build(s); s *= np.sqrt(AREA_OLD / (memb2.sum() * G * G))
cart2, memb2 = build(s)
# 4. 厚さ（片側、mm）
dt = nd.distance_transform_edt(cart2) * G; hc = np.clip(nd.gaussian_filter(dt, 0.5), 0, 1.5); hc[~cart2] = 0
Xr = np.clip(GX, 0, None) / max(GX[memb2].max(), 1)
hm = np.clip(3.0 - 1.5 * Xr, 1.5, 3.0) / 2
# 軟骨のある所は軟骨より片側 0.5 mm 以上厚く。ぼかすだけでは細い放射軟骨の上で膜が軟骨より薄くなり、軟骨の下の面が膜の外に出た（2372 頂点）ので、先に 2 mm の幅で最大をとる
hm = np.maximum(hm, nd.gaussian_filter(nd.maximum_filter(np.where(cart2, hc + 0.6, 0), size=int(2.0 / G)), 0.5 / G))
hm = np.maximum(hm, np.where(cart2, hc + 0.5, 0))
NW = int(np.ceil(2.6 / G)); gw = np.arange(-NW, NW + 1) * G
def solid(h2, region):
    F = (h2[..., None] - np.abs(gw)[None, None, :]); F[~region] = -1
    return nd.gaussian_filter(F.astype(np.float32), [0.6, 0.6, 0.6])
def write(name, F, side, extra=None):
    v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=-1), 0.0, allow_degenerate=False); v = v - 1
    X = x0 + v[:, 0] * G; Y = y0 + v[:, 1] * G; Wv = v[:, 2] * G - NW * G
    Q = rot(B[None] + X[:, None] * e1 + Y[:, None] * e2 + Wv[:, None] * nrm)   # (u, z, v) の mm、下へ回した後
    Vb = np.stack([Q[:, 1], side * Q[:, 0], -Q[:, 2]], 1) / 1000.0       # Blender（x = z、y = u、z = −v）。左は鏡映
    if extra is not None:   # 腰帯の面を足す（向きは下でまとめてそろえる。それぞれ閉じた塊）
        Vg, fg = extra(name, None, side); fg = fg.copy()
        volg = np.einsum('ij,ij->i', Vg[fg[:, 0]], np.cross(Vg[fg[:, 1]], Vg[fg[:, 2]])).sum(); volf = np.einsum('ij,ij->i', Vb[f[:, 0]], np.cross(Vb[f[:, 1]], Vb[f[:, 2]])).sum()
        if np.sign(volg) != np.sign(volf): fg = fg[:, ::-1]
        f = np.r_[f, fg + len(Vb)]; Vb = np.r_[Vb, Vg]
    vol = np.einsum('ij,ij->i', Vb[f[:, 0]], np.cross(Vb[f[:, 1]], Vb[f[:, 2]])).sum() / 6
    if vol > 0: f = f[:, ::-1]                                           # write_ply が裏返して書くので、内向きにそろえて渡す
    write_ply(f'{OUT}/{name}.ply', Vb, f); return abs(vol) * 1e6, len(f)
Fc = solid(hc, cart2); Fm = solid(hm, memb2)
# 腰帯: ひれの板の中に置くと、ひれと一緒に下へ回って腹の外へ出た（2473 頂点）。腰帯は体の中の横の棒なので、付け根 B の高さの水平の面に置く。
#  左右は、写真の正中（y 565）からつなぎ目（y 640）までを、体の正中（u = 0）から付け根の u まで（CT の付け根）に縮める。前後は s のまま
#  前後も同じ割合（kg）で縮める（前後だけ s のままでは、腰帯が体軸の向きに 27 mm の帯になった）。正中の側は HH_PELV_GIRDLE_U0 まで（a6a で付け根が正中へ 1.3〜2.1 mm 寄るので、左右が重ならないように）
kg = B[0] / (YJ - YAX); GU0 = float(os.environ.get('HH_PELV_GIRDLE_U0', 0.5)) - DY   # 動かした後に正中から 0.5 mm
gy_, gx_ = np.nonzero(GIRD_px); ga = (gx_ - XJ) * kg
gz0, gz1 = B[1] - ga.max() - 2, B[1] - ga.min() + 2; gu0, gu1 = GU0, B[0] + 2
GZ, GU = np.meshgrid(np.arange(gz0, gz1, G), np.arange(gu0, gu1, G), indexing='ij')
qx2 = XJ + (B[1] - GZ) / kg; qy2 = YAX + GU / kg
gm = nd.map_coordinates(GIRD_px.astype(np.float32), [qy2.ravel(), qx2.ravel()], order=1, cval=0).reshape(GZ.shape) > 0.5
gdt = np.clip(nd.distance_transform_edt(gm) * G, 0, 1.5); gdt[~gm] = 0
Fg = solid(gdt, gm)
def write_g(name, F, side):
    v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=-1), 0.0, allow_degenerate=False); v = v - 1
    Q = np.stack([gu0 + v[:, 1] * G + DY, gz0 + v[:, 0] * G, B[2] + v[:, 2] * G - NW * G], 1)
    return np.stack([Q[:, 1], side * Q[:, 0], -Q[:, 2]], 1) / 1000.0, f
rep = {'scale_mm_per_px': round(float(s), 4), 'fin_len_mm': round(L_old, 1), 'fringe': FRINGE,
       'cart_area_mm2': round(float(cart2.sum() * G * G), 1), 'memb_area_mm2': round(float(memb2.sum() * G * G), 1),
       'cart_in_memb': round(float((cart2 & memb2).sum() / memb2.sum()), 3), 'area_old_mm2': round(float(AREA_OLD), 1)}
for side, sfx in ((1, 'R'), (-1, 'L')):
    rep[f'cart_{sfx}'] = write(f'HH_pelv_{sfx}', Fc, side, extra=lambda n_, F_, sd: write_g(n_, Fg, sd)); rep[f'memb_{sfx}'] = write(f'HH_pelvmem_{sfx}', Fm, side)
rep['dy_mm'] = round(float(DY), 2); rep['girdle_mm'] = {'z': [round(float(B[1] - ga.max()), 1), round(float(B[1] - ga.min()), 1)], 'u': [GU0, round(float(B[0]), 1)], 'kg_mm_per_px': round(float(kg), 4)}
json.dump(rep, open('a5_pelvphoto.json', 'w'), ensure_ascii=False, indent=1); print(rep)

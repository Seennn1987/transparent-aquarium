# A5 第 1 背びれの軟骨を、シロシュモクザメの骨格標本の写真から作る（2026-10-20 案。HH_DFIN1_PHOTO=1 のときだけ。a4e_mesh.py fins の後）
#  プロデューサー「胸びれはこの案を既定にして、次のひれ（第 1 背びれ）に進んでください」。ひれの形を見本と比べた結果（計画書「ひれの軟骨の形を見本と比べる」）:
#  いまの第 1 背びれの軟骨（CT）は、付け根の高さ 15% で膜 132 mm のうち前から 18〜87 mm だけで、前と後ろが空き、中ほどで高さ 45〜55% まで盛り上がる。
#  見本: ピサ大学自然史博物館の骨格標本 P 415（シロシュモクザメ、Stefano Puzzuoli、CC BY-SA 4.0、docs/references/hammerhead/ref1_pisa_sphyrna_zygaena_skeleton_lateral.jpg）の
#   第 1 背びれ。白い放射軟骨の帯が付け根に沿い、帯の上の境は後ろ（頂点の下）で低く（高さの約 26%）、前の低い所ではほぼ全部が棒。後端の細い所には棒が無い
#  写真 4059 × 2706 px の、2000 px に縮めたときの x 1130〜1400・y 630〜905 を元の画素で切り出し、左右を返す（頭を左に）。
#   ひれ = 明るさ > 60 のいちばん大きな塊（背骨より上）。放射軟骨 = 棒の間の黒いすき間のある帯の中の明るい所（下の 2026-10-20 の注）
#  置き方: ひれの外形（hh_fins.py の dfin1、a6a が膜の板を作る形）と写真のひれを、付け根の前の端（s 0）・後端（s 1.33）・頂点の高さ（h 1）で合わせる（前後と高さで別の倍率）。
#   軟骨は外形の 1 mm 内まで。体の線より下は CT の軟骨（下の 2026-10-20 直し）。左右の厚さは、写真の棒の縁からの距離を半分の厚さに（上限 1.2 mm。膜の板は ±1.6 mm）
import hh_paths; hh_paths.cd_work()
import numpy as np, json, os
from scipy import ndimage as nd
from skimage.measure import marching_cubes
from PIL import Image, ImageOps
from matplotlib.path import Path as _Path
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
import hh_fins, sys
# 2026-10-20（プロデューサー「進んで」、第 1 背びれの次）: 引数 dfin2 で第 2 背びれ。ピサの標本に第 2 背びれは付いていないので、同じつくりの臀びれ
#  （Compagno 1988 の背びれ・臀びれの骨格: 基底の軟骨と平行な放射軟骨）を上下・左右に返して使う。外形は前の版の膜（CT の軟骨に合わせた外形、a6a の FIT_FD）のまま
NAME = sys.argv[1] if len(sys.argv) > 1 else 'dfin1'
CFG = {'dfin1': dict(crop=(1130, 630, 1400, 905), flip=False),
       'dfin2': dict(crop=(680, 890, 900, 1020), flip=True)}[NAME]
PHOTO = os.path.join(hh_paths.ROOT, 'docs', 'references', 'hammerhead', 'ref1_pisa_sphyrna_zygaena_skeleton_lateral.jpg')
if not os.path.exists(PHOTO): raise SystemExit(f'見本の写真がありません（git に入れていない）: {PHOTO}')
im = Image.open(PHOTO).convert('RGB'); sc = im.width / 2000
im = ImageOps.mirror(im.crop(tuple(int(v * sc) for v in CFG['crop'])))
if CFG['flip']: im = ImageOps.flip(im)
A = np.asarray(im).astype(float); Hh, Ww = A.shape[:2]; yy, xx = np.mgrid[0:Hh, 0:Ww]
mn = A.min(2); mx = A.max(2); sat = (mx - mn) / np.maximum(mx, 1)
col_y = int(0.86 * Hh) if NAME == 'dfin1' else 132                           # 背骨（第 1 背びれ: 切り出しの下の 14%、臀びれ: 血道弓と透けた膜の y 132）より上だけ
fin = (mx > 60) & (yy < col_y); cl, n = nd.label(fin); fin = cl == (1 + np.argmax(nd.sum(fin, cl, range(1, n + 1))))
fin = nd.binary_fill_holes(fin)
# 放射軟骨の帯: 帯の上の境（放射軟骨と膜の境の明るい筋）を、左右を返した切り出し（548 × 558 px）で目で読んだ点（x, y）を結ぶ:
#  (60, 345) (100, 322) (150, 307) (200, 300) (250, 301) (300, 310) (340, 328) (380, 350) (420, 372) (460, 392) (500, 412) (520, 425)。
#  色や暗いすき間だけで帯を探す版は、照明の暗い後ろ半分が抜けたり、膜の後ろの縁の筋まで拾ったりした。
#  帯 = ひれの中で境の線より下。棒 = 帯の中で、周り（4 px でぼかした値）より明るい所（棒の間は茶色く暗い）
SEAM = np.array([(60, 345), (100, 322), (150, 307), (200, 300), (250, 301), (300, 310), (340, 328), (380, 350), (420, 372), (460, 392), (500, 412), (520, 425)], float)
YLIM = 452
if NAME == 'dfin2':
    # 臀びれ（上下・左右に返した 446 × 264 px）: 棒の帯の外の境を目で読んだ点。棒の付け根の側は y 128 まで（その下は透けた膜と血道弓）
    SEAM = np.array([(95, 92), (140, 80), (190, 68), (240, 64), (265, 78), (285, 100), (300, 110)], float); YLIM = 128
band = fin & (yy >= np.interp(xx, SEAM[:, 0], SEAM[:, 1])) & (xx >= SEAM[0, 0] - 30)
rad = band & (mn > nd.gaussian_filter(mn, 4) + 2) & (yy <= YLIM)
if NAME == 'dfin2':   # 臀びれの写真は小さく（棒の間 約 6 px）、4 px ぼかし + 2 では棒が切れ切れになった（軟骨が膜の 15%）。3 px ぼかしより明るい所（帯の 54%）
    rad = band & (mn > nd.gaussian_filter(mn, 3)) & (yy <= YLIM)   # 付け根の下の破れた縁と、留めの針金（y 455 より下）は使わない
cl, n = nd.label(rad); sz = nd.sum(rad, cl, range(1, n + 1)); rad = np.isin(cl, 1 + np.nonzero(sz >= (20 if NAME == 'dfin1' else 8))[0])
fy, fx = np.nonzero(fin)
ybase = float(np.percentile(fy, 99)); apex_y = float(fy.min())
x_or = float(fx[fy > ybase - 0.10 * (ybase - apex_y)].min()); x_rear = float(fx.max()); x_apex = None
fd = hh_fins.FINS[NAME]
if NAME == 'dfin2':
    # 臀びれの写真の目印（目で読んだ）: 付け根の前の端 x 72、頂点 x 305・y 22、後ろの細い端 x 410。外形の s 0・0.8（頂点）・1.8（後端）に合わせる
    x_or, x_apex, x_rear, apex_y = 72.0, 305.0, 410.0, 22.0
    kl, kz, o_mm = [float(v) for v in os.environ.get('HH_DFIN2_MEMB', '0.86,0.97,628.0').split(',')]   # 前の版の膜（a6a の fin_membrane_fit_HH_dfin2）
    TL_ = hh_fins.TL_MM; fd = dict(fd, o=o_mm / TL_, i=(o_mm + (fd['i'] - fd['o']) * TL_ * kl) / TL_, H=fd['H'] * kz)
    if os.environ.get('HH_DFIN2_OUTLINE') == 'raver': fd = hh_fins.dfin2_raver_fd()   # Raver の図の外形（a6a の膜の板も同じ）
TLm = hh_fins.TL_MM; Lb = (fd['i'] - fd['o']) * TLm; Hm = fd['H'] * TLm; s_rear = max(s for s, h in fd['poly'])
sf = json.load(open('a5_side_fit.json')); top = lambda x: np.interp(x, sf['z_mm'], sf['top_target_mm'])
poly = [(fd['o'] * TLm + s * Lb, (h * Hm if h > 0 else -4.0)) for s, h in fd['poly']]     # (体軸 mm, 体の線からの高さ mm)
G = 0.25
# 2026-10-20 直し（プロデューサー「ヒレの根元に一部かけている部分があり…」→「体の背から上はピサの写真の放射軟骨の帯にし、写真の付け根を列ごとに外形の付け根へ合わせ、
#  体の中は CT の軟骨をつなげる案を…」）: 前の試しは写真の付け根を 1 本の水平の線（y 470、破れた縁と針金を含む）で合わせたので、帯が体の背から 2〜13 mm 浮いた
#  （写真の付け根は後ろで上がる）。写真の列ごとに、棒のいちばん下（3 次の式でならす）を外形の付け根（体の線）に合わせる。高さの倍率は付け根の中ほど〜頂点で決める
# 2026-10-20（プロデューサー「第 2 背びれは案 A（臀びれの CT を写す）にして、付け根を列ごとに体の線へ合わせ、体の中は CT とつなげる直しを足して…」）:
#  HH_DFIN2_SRC=ct で、写真の代わりに案 A の軟骨（a4d3_fin_ct_mesh.py dfin2 を HH_DFIN2_FROM_ANAL=1 で作った面、mesh/HH_dfin2_fromanal.ply）を横から見た形を使う。
#  0.1 mm の格子に面を塗り、体の線より上だけ。前後と高さは mm のまま（倍率 1）で、付け根だけ列ごとに体の線へ合わせる
SRC_CT = NAME == 'dfin2' and os.environ.get('HH_DFIN2_SRC') == 'ct'
if SRC_CT:
    from PIL import ImageDraw as _IDraw
    _b = open(f'{OUT}/HH_dfin2_fromanal.ply', 'rb').read(); _h = _b.index(b'end_header\n') + 11; _hd = _b[:_h].decode()
    _nv = int(_hd.split('element vertex ')[1].split()[0]); _nf = int(_hd.split('element face ')[1].split()[0])
    _V = np.frombuffer(_b, '<f4', _nv * 3, _h).reshape(-1, 3).astype(float) * 1000; _F = np.frombuffer(_b, np.dtype([('n', 'u1'), ('i', '<i4', 3)]), _nf, _h + _nv * 12)['i']
    _hgt = _V[:, 2] + np.interp(_V[:, 0], sf['z_mm'], sf['top_target_mm'])     # 体の線からの高さ（mm）
    RES = 0.1; XMIN = _V[:, 0].min() - 1; HMAX = _hgt.max() + 1
    Ww = int((_V[:, 0].max() + 1 - XMIN) / RES) + 1; Hh = int((HMAX + 4) / RES) + 1
    _img = Image.new('1', (Ww, Hh), 0); _d = _IDraw.Draw(_img); _P = np.c_[(_V[:, 0] - XMIN) / RES, (HMAX - _hgt) / RES]
    for t_ in _F: _d.polygon([tuple(_P[i]) for i in t_], fill=1)
    rad = np.asarray(_img).copy(); rad[int(HMAX / RES) + 1:] = False      # 体の線より上だけ（体の中は第 2 背びれの CT）
    yy, xx = np.mgrid[0:Hh, 0:Ww]; apex_y = 0.0; x_or, x_rear = 0.0, float(Ww - 1)
XC = np.arange(Ww); _hasr = rad.any(0); _yb = np.where(_hasr, Hh - 1 - np.argmax(rad[::-1], 0), 0).astype(float)
_k = _hasr & (XC >= x_or) & (XC <= x_rear); YB = np.polyval(np.polyfit(XC[_k], _yb[_k], 3), np.clip(XC, XC[_k].min(), XC[_k].max()).astype(float))
#  棒のある列の外は端の値のまま（3 次の式を伸ばすと、第 2 背びれでは棒の無い後ろで付け根が 200 px 上へ外れた）
kh = (float(np.median(YB[_k])) - apex_y) / Hm                                # 写真の画素 / mm（高さ）
if SRC_CT: kh = 1.0 / RES
X0, X1 = fd['o'] * TLm - 5, fd['o'] * TLm + s_rear * Lb + 5; Z0, Z1 = -34.0, Hm + 5; YW = 6.0
gx = np.arange(X0, X1, G); gz = np.arange(Z0, Z1, G); gy = np.arange(-YW, YW + G / 2, G)
GX, GZ = np.meshgrid(gx, gz, indexing='ij')
OUT2 = _Path(poly).contains_points(np.c_[GX.ravel(), GZ.ravel()]).reshape(GX.shape)
INNER = nd.binary_erosion(OUT2, iterations=int(1.0 / G))
s_g = (GX - fd['o'] * TLm) / Lb
px = ((GX - XMIN) / RES) if SRC_CT else (x_or + s_g / s_rear * (x_rear - x_or)) if x_apex is None else np.interp(s_g, [0, 0.8, s_rear], [x_or, x_apex, x_rear]); py = np.interp(px, XC, YB) - np.clip(GZ, 0, None) * kh - np.clip(GZ, None, 0) * 0   # 体の線より下は棒のいちばん下の行をそのまま下へ（CT とつなぐため 2.5 mm まで）
cart2 = (nd.map_coordinates(rad.astype(np.float32), [py.ravel(), px.ravel()], order=1, cval=0).reshape(GX.shape) > 0.5) & (INNER | ((GZ < 0.5) & OUT2)) & (GZ >= -2.5)
# 2026-10-21（プロデューサー「Mivart の図 1 とピサの写真から、第 1 背びれの軟骨を 3 段の放射軟骨（先の段まで）で作り直す案を…」）: HH_DFIN1_DISTAL=1 で、
#  帯の上の境（中の段と先の段の継ぎ目）より上の先の段の放射軟骨も入れる。根拠: Mivart 1879 の Zygaena malleus（シロシュモクザメ）の第 1 背びれ（図版 LXXIV 図 1、本文:
#  放射軟骨は基部 26・中 29・先 29 本の 3 段、先の段が最も長い）。先の段の棒の形はピサの写真の、継ぎ目より上の細い筋（周り（4 px ぼかし）より 2 以上明るい所）から。
#  軟骨のある範囲は Mivart の図 1 から: 図版 2112 × 3198 px の x 40〜1060・y 260〜1460 を 800 × 941 px に縮めた画面（頭が右）で目で読み、左右を返した点 (x', y)
#  （x' = 400 − x）。ひれの前の端 x' 20・頂点 x' 325・y 18・細い後端 x' 385、体の線 y 325。軟骨の外の線（前の縁に沿う膜の帯と、頂点の下の後ろの縁を除く）:
MIV = [(65, 330), (70, 290), (150, 200), (210, 140), (250, 100), (275, 90), (290, 95), (295, 110), (290, 200), (275, 265), (305, 290), (330, 318), (290, 330)]
MIV_X = (20.0, 325.0, 385.0); MIV_Y = (325.0, 18.0)
RODS = []; RESID = []
if NAME == 'dfin2' and os.environ.get('HH_DFIN2_SRC') == 'trace':
    # 2026-10-20（プロデューサー「…軟骨はピサの臀びれの写真の棒を 1 本ずつたどって割り振る案を…」）: 写真の棒を 1 本ずつ中心線でたどり、それぞれの太さのまま外形へ写す。
    #  写真を画素のまま写す版は、写真が小さく（棒の間 約 10 px）棒が切れ切れになった。CT を横から塗る版は棒どうしが重なって塊になった。
    #  たどり方: 帯の中で 3 px ぼかしより明るい所（棒）を、つながった塊ごとに 1 本の棒の切れ端とする（10 px 以上）。塊の点の主軸（主成分）を中心線、
    #  長さ = 主軸の向きの広がり（両端の 2% と 98%）、太さ = 面積 ÷ 長さ。1 行ずつ明るい所へ寄せてたどる版は、となりの棒へ移ったり同じ棒を何度もたどったりした
    #  2026-10-20 直し: 明るい所をそのまま使うと、帯の中で棒どうしがつながって 13 本の太い塊になった。細い明るい筋を強める処理（skimage の sato、太さ 1〜2 px）を
    #  かけて、帯の中の上位 25% を棒の切れ端とする
    from skimage.filters import sato as _sato
    _bb = band & (yy <= YLIM); _rr = _sato(mn / 255.0, sigmas=[1.0, 1.5, 2.0], black_ridges=False) * _bb
    _r = _rr > np.percentile(_rr[_bb], 75)
    #  筋の形をそのまま写す版は、筋が切れ切れ（帯の 10%）になった。写真が小さく、筋を画素のまま使うのは無理なので、棒を 1 本ずつ数と位置で読む:
    #  帯の中ほどの 2 本の行（y 106・116）で筋の強さの山（間 5 px 以上）を棒の通る所とし、そこでの濃淡の向き（構造テンソル、半径 6 px）に沿って、
    #  帯の外の境（SEAM）と付け根（y 128）まで伸ばす。太さはその行で山の強さが半分になる幅。2 本の行で同じ棒（線の距離 3 px 以内）は 1 本にする
    _g = nd.gaussian_filter(mn, 1.0); _gy, _gx = np.gradient(_g)
    _J = [nd.gaussian_filter(q_, 6) for q_ in (_gx * _gx, _gy * _gy, _gx * _gy)]
    _th = 0.5 * np.arctan2(2 * _J[2], _J[0] - _J[1]) + np.pi / 2               # 棒の向き（画像の x 右・y 下）
    lines = []
    for yr in (106, 116):
        prof = _rr[yr]; pk = [x for x in range(3, Ww - 3) if _bb[yr, x] and prof[x] == prof[x - 2:x + 3].max() and prof[x] > np.percentile(_rr[_bb], 70)]
        for x0 in pk:
            d_ = np.array([np.cos(_th[yr, x0]), np.sin(_th[yr, x0])]); d_ = -d_ if d_[1] > 0 else d_   # 上（y が減る）向きへ
            p0 = np.array([float(x0), float(yr)])
            if any(abs(L_[1][0] * (p0 - L_[0])[1] - L_[1][1] * (p0 - L_[0])[0]) < 3 for L_ in lines): continue
            half = prof[x0] / 2; a_ = b_ = x0
            while a_ > 0 and prof[a_ - 1] > half and x0 - a_ < 5: a_ -= 1
            while b_ < Ww - 1 and prof[b_ + 1] > half and b_ - x0 < 5: b_ += 1
            wpx = (b_ - a_ + 1) * abs(d_[1])                                      # 横の幅 → 棒に直角の幅
            ends = []
            for sg in (1, -1):
                t = 0.0
                while True:
                    q_ = p0 + sg * (t + 0.5) * d_; xi, yi = int(round(q_[0])), int(round(q_[1]))
                    if not (0 <= xi < Ww and 0 <= yi < Hh) or not _bb[yi, xi]: break
                    t += 0.5
                ends.append(p0 + sg * t * d_)
            if np.linalg.norm(ends[0] - ends[1]) < 8: continue
            lines.append((p0, d_, ends, wpx))
    _angs = np.array([np.degrees(np.arctan2(-L_[1][1], L_[1][0])) % 180 for L_ in lines]); _med = float(np.median(_angs))
    RODS = [L_ for L_, a_ in zip(lines, _angs) if abs(a_ - _med) < 12]          # 向きが中央値から 12° より外れた線（帯の縁・膜のしわを拾ったもの）は使わない
    _YB0 = np.polyval(np.polyfit(XC[_k], _yb[_k], 1), XC.astype(float))         # 付け根はまっすぐな線（3 次の式では棒の向きが場所ごとにゆがんだ）
    from PIL import ImageDraw as _ID
    _img = Image.new('L', (GX.shape[0], GX.shape[1]), 0); _d = _ID.Draw(_img)
    def _tomm(q_):
        return fd['o'] * TLm + (q_[0] - x_or) / kh, (float(np.interp(q_[0], XC, _YB0)) - q_[1]) / kh
    for p0, d_, ends, wpx in RODS:
        (xa, za), (xb, zb) = _tomm(ends[0]), _tomm(ends[1]); w_ = float(np.clip(wpx / kh, 0.4, 1.6))
        # 棒の先へ細くなる（写真の棒も先が細い）: 3 つに分けて、付け根の側 1.0・中 0.85・先 0.6 倍
        for f0, f1, kw in ((0.0, 0.4, 1.0), (0.4, 0.75, 0.85), (0.75, 1.0, 0.6)):
            pa = (xb + (xa - xb) * f0, zb + (za - zb) * f0); pb = (xb + (xa - xb) * f1, zb + (za - zb) * f1)   # b が付け根の側（下）
            _d.line([((pa[0] - X0) / G, (pa[1] - Z0) / G), ((pb[0] - X0) / G, (pb[1] - Z0) / G)], fill=255, width=max(1, int(round(w_ * kw / G))))
    cart2 = (np.asarray(_img).T > 127) & (INNER | ((GZ < 0.5) & OUT2)) & (GZ >= 0)
if NAME == 'dfin2':
    # 体の線の 2.5 mm 下〜体の線: 棒のいちばん下の行をそのまま下へ伸ばすと、縦の歯のような筋が並んだ。ここは基底の軟骨（棒の付け根をつなぐ 1 本の板。Compagno 1988）なので、
    #  体の線から 1 mm 上までに棒のある所の前後 ±1 mm を、つながった帯にする
    _lo = (GZ >= -2.5) & (GZ < 0.0); _cols = (cart2 & (GZ >= 0) & (GZ < 1.0)).any(1)
    _cols = nd.binary_closing(nd.binary_dilation(_cols, iterations=int(1.0 / G)), iterations=int(2.0 / G))
    cart2 = (cart2 & ~_lo) | (_lo & _cols[:, None] & OUT2)
if NAME == 'dfin1' and os.environ.get('HH_DFIN1_DISTAL') == '1':
    s_apex1 = max(fd['poly'], key=lambda q: q[1])[0]
    _cpoly = [(fd['o'] * TLm + float(np.interp(x_, MIV_X, [0, s_apex1, s_rear])) * Lb, (MIV_Y[0] - y_) / (MIV_Y[0] - MIV_Y[1]) * Hm) for x_, y_ in MIV]
    CREG = _Path(_cpoly).contains_points(np.c_[GX.ravel(), GZ.ravel()]).reshape(GX.shape)
    _rall = fin & (mn > nd.gaussian_filter(mn, 4) + 2) & (yy <= YLIM) & (xx >= SEAM[0, 0] - 30) & (yy < np.interp(xx, SEAM[:, 0], SEAM[:, 1]))
    cl_, n_ = nd.label(_rall); sz_ = nd.sum(_rall, cl_, range(1, n_ + 1)); _rall = np.isin(cl_, 1 + np.nonzero(sz_ >= 20)[0])
    _rall = nd.binary_dilation(_rall, iterations=int(os.environ.get('HH_DFIN1_DISTAL_DIL', 1)))   # 筋は幅 2 px ほどと細く、0.25 mm の格子に写すと半分ほど消えた（2026-10-21: 2 px 広げる版も）
    distal = (nd.map_coordinates(_rall.astype(np.float32), [py.ravel(), px.ravel()], order=1, cval=0).reshape(GX.shape) > 0.5) & CREG & INNER & (GZ > 0)
    # 継ぎ目（中の段と先の段の境）は 0.4 mm のすき間（Mivart の図でも棒が継ぎ目で切れる）
    _sx = np.interp(SEAM[:, 0], [x_or, x_rear], [0, s_rear]) * Lb + fd['o'] * TLm; _sz = (np.interp(SEAM[:, 0], XC, YB) - SEAM[:, 1]) / kh
    _seam = np.zeros(GX.shape, bool); _gi = np.round((_sx - X0) / G).astype(int); _gj = np.round((_sz - Z0) / G).astype(int)
    from PIL import ImageDraw as _ID2
    _im2 = Image.new('L', (GX.shape[0], GX.shape[1]), 0); _ID2.Draw(_im2).line(list(zip(_gi.tolist(), _gj.tolist())), fill=255, width=max(1, int(round(0.4 / G))))
    _seam = np.asarray(_im2).T > 127
    cart2 = (cart2 | distal) & ~_seam
    rep_distal = {'distal_area_mm2': round(float(distal.sum() * G * G), 1), 'creg_area_mm2': round(float((CREG & (GZ > 0)).sum() * G * G), 1)}
else:
    rep_distal = {}
dt = nd.distance_transform_edt(cart2) * G; hc = np.clip(nd.gaussian_filter(dt, 0.5), 0, 1.2); hc[~cart2] = 0
if NAME == 'dfin1' and os.environ.get('HH_DFIN1_DISTAL') == '1':
    hc = np.where(cart2, np.maximum(hc, 0.5), 0)   # 先の段の細い棒も左右に片側 0.5 mm 以上
    # 2026-10-21（プロデューサー「先の段の棒を下の 2 段と同じくらいはっきり見えるようにした版を作って…」）: 下の 2 段の棒は左右に片側 約 1.0〜1.2 mm（縁からの距離）。
    #  先の段は写真の筋が細く 0.5 mm になっていたので、HH_DFIN1_DISTAL_T（片側 mm）までそろえる
    _dt_ = float(os.environ.get('HH_DFIN1_DISTAL_T', 0) or 0)
    if _dt_ > 0: hc = np.where(distal & cart2, np.maximum(hc, _dt_), hc)
if NAME == 'dfin2': hc = np.where(cart2, np.maximum(hc, 0.6), 0)   # 棒は幅 0.3 mm ほどと細く、縁からの距離のままでは左右も 0.15 mm になってほとんど写らなかった。左右は片側 0.6 mm 以上
Fp = hc[..., None] - np.abs(gy)[None, None, :]; Fp[~cart2] = -1
# 体の中（体の線より下）: CT の第 1 背びれ（a4_dfin1.npz、a4e と同じ体積）を、a6a が CT の軟骨にしていたのと同じく体の線の動き（a5_trunk_width.json の dtop）だけ動かして使う
ct = np.load(f'a4_{NAME}.npz'); fld = ct['field']; org = ct['origin']; VX_ = 0.735; U0_, V0_ = -180.0, -150.0
_tw = json.load(open('a5_trunk_width.json')) if os.path.exists('a5_trunk_width.json') else None
dtop = np.interp(gx, _tw['z_mm'], _tw['dtop_mm']) if _tw and 'dtop_mm' in _tw else np.zeros_like(gx)
GX3, GZ3, GY3 = np.meshgrid(gx, gz, gy, indexing='ij')
zf = -top(GX3) + GZ3 - np.interp(GX3, gx, dtop)                              # CT の Blender の z（mm、dtop を足す前）
iz = GX3 / VX_ - org[0]; iv = (-zf - V0_) / VX_ - org[1]; iu = (GY3 - U0_) / VX_ - org[2]
Fc = nd.map_coordinates(fld.astype(np.float32), [iz.ravel(), iv.ravel(), iu.ravel()], order=1, cval=0).reshape(GX3.shape) - 0.5
Fc[GZ3 > -2.0] = -1                                                           # 体の線の 2 mm 下より上は写真の帯（CT は左右に ±3 mm ほど広く、そこまで使うと体の背の膜の外に出た: 198 頂点）
F = np.maximum(Fp, Fc * 2.0)
F = nd.gaussian_filter(F.astype(np.float32), [0.6, 0.6, 0.6])
v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=-1), 0.0, allow_degenerate=False); v = v - 1
Xv = X0 + v[:, 0] * G; Zv = Z0 + v[:, 1] * G; Yv = -YW + v[:, 2] * G
Vb = np.stack([Xv, Yv, -top(Xv) + Zv], 1) / 1000.0                          # Blender（x = 体軸、y = 左右、z = 背）。体の線は z = −top_target
vol = np.einsum('ij,ij->i', Vb[f[:, 0]], np.cross(Vb[f[:, 1]], Vb[f[:, 2]])).sum() / 6
if vol > 0: f = f[:, ::-1]                                                  # write_ply が裏返して書くので、内向きにそろえて渡す
write_ply(f'{OUT}/HH_{NAME}.ply', Vb, f)
memb = OUT2 & (GZ > 0)
ctin = (Fc > 0).any(2)
rep = {**rep_distal, 'rods': len(RODS), 'photo_px': {'origin_x': x_or, 'rear_x': x_rear, 'apex_y': apex_y, 'base_y_fit': [round(float(YB[int(x_or)]), 1), round(float(YB[int(x_rear)]), 1)]}, 'kh_px_per_mm': round(kh, 3),
       'cart_area_mm2': round(float((cart2 & (GZ > 0)).sum() * G * G), 1), 'memb_area_mm2': round(float(memb.sum() * G * G), 1), 'cart_in_memb': round(float((cart2 & memb).sum() / memb.sum()), 3),
       'ct_below_line_mm': round(float(-GZ[ctin].min()), 1) if ctin.any() else None, 'volume_ml': round(abs(vol) * 1e6, 3), 'faces': int(len(f))}
json.dump(rep, open(f'a5_{NAME}photo.json', 'w'), ensure_ascii=False, indent=1); print(rep)
# 2026-10-20 鰭条（プロデューサー「既定にする前に、ひれの先の鰭条を薄く描く案も作って、見本と並べて見せてください」→「強で規定にした上で後で色を調整できるように
#  編集パネルに機能追加して」）: HH_DFIN1_RAYS=<mm> で、鰭条（ceratotrichia、コラーゲンに近い糸で軟骨ではない）を別の部品 HH_dfin1ray（ページの Dorsal1Ray）にする。
#  ピサの写真の膜に見える鰭条（帯の上の境より 4 px 以上上の膜で、周り（3 px ぼかし）より 4 以上明るい所、8 px 以上の塊）に沿う細い帯で、左右の厚さは片側 <mm>
#  （膜の板 ±1.6 mm の中）。色と濃さはページの調整の欄で変える（既定は、膜を鰭条に沿って左右 0.6 mm 厚くした版と同じ見え方）。
#  前の試し（膜そのものを鰭条に沿って厚くする）は、色を膜と別に変えられなかった
RAYS = float(os.environ.get('HH_DFIN1_RAYS', 0) or 0) if NAME == 'dfin1' else 0.0
if RAYS > 0:
    membp = fin & (yy < np.interp(xx, SEAM[:, 0], SEAM[:, 1]) - 4); membp = nd.binary_erosion(membp, iterations=3)
    fib = membp & (mn > nd.gaussian_filter(mn, 3) + 4)
    cl, n = nd.label(fib); sz = nd.sum(fib, cl, range(1, n + 1)); fib = np.isin(cl, 1 + np.nonzero(sz >= 8)[0])
    fib2 = nd.map_coordinates(nd.gaussian_filter(fib.astype(np.float32), 0.7), [py.ravel(), px.ravel()], order=1, cval=0).reshape(GX.shape) * (GZ > 0)
    fib2 = np.clip(fib2 / 0.5, 0, 1) * nd.binary_erosion(OUT2, iterations=int(0.5 / G))
    hr = RAYS * fib2
    gy2 = np.arange(-RAYS - G, RAYS + G * 1.5, G)
    Fr = hr[..., None] - np.abs(gy2)[None, None, :]; Fr[fib2 < 0.15] = -1
    Fr = nd.gaussian_filter(Fr.astype(np.float32), [0.4, 0.4, 0.0])
    v, f, _, _ = marching_cubes(np.pad(Fr, 1, constant_values=-1), 0.0, allow_degenerate=False); v = v - 1
    Xv = X0 + v[:, 0] * G; Zv = Z0 + v[:, 1] * G; Yv = gy2[0] + v[:, 2] * G
    Vr = np.stack([Xv, Yv, -top(Xv) + Zv], 1) / 1000.0
    volr = np.einsum('ij,ij->i', Vr[f[:, 0]], np.cross(Vr[f[:, 1]], Vr[f[:, 2]])).sum() / 6
    if volr > 0: f = f[:, ::-1]
    write_ply(f'{OUT}/HH_dfin1ray.ply', Vr, f)
    rep['rays'] = {'half_thickness_mm': RAYS, 'fiber_area_mm2': round(float((fib2 > 0.5).sum() * G * G), 1), 'volume_ml': round(abs(volr) * 1e6, 3), 'faces': int(len(f))}
    json.dump(rep, open('a5_dfin1photo.json', 'w'), ensure_ascii=False, indent=1); print('rays', rep['rays'])

"""
メンダコ 手順 A2: 殻・顎板・眼を、A1 の外形（決定）の中に置く。外形の内側に入るかを数で確かめ、3 方向の図を作る。

  .venv/bin/python -I blender/mendako/a2_parts.py

入力: docs/mendako/a1_outline_lines.json（A1 の決定。上の線と正面の線、横は正面と同じ = 案 a）
出力:
  blender/mendako/work/a2_*.obj           部品の面（git に入れない。このスクリプトで作り直せる）
  docs/mendako/a2_parts.json              置いた位置・大きさ・外形からの余り
  docs/mendako/a2_parts.jpg               3 方向（上・正面・横）と、部品ごとの参考との並べ

軸: glTF と同じ。+Y が背（上）、+Z が前、+X が体の左。単位は横幅 W = 1（成熟した雄で約 138 mm。Meyer 1906 図 1 と図 5 の縮尺から）。
  上から見て前が上の図では、体の左は図の左（背を見下ろすので）。

外形の入れ物: 上から見た輪郭 R(θ)（A1 の上の線）と、断面の高さ v（A1 の正面の線。横も同じ形）から、
  高さ h(x, z) = v(ρ)、ρ = 中心からの距離 ÷ その向きの輪郭までの距離。口側（腹）は平ら（y = 0、砂の上で休む姿勢 B）。

置く元（第 2.3 節・第 7 節と同じ測り。手で読んだ点は方眼 ±10〜20 px）:
  眼: 左右の間 0.31 W（3 枚でそろった値）。前後は前の端から 0.42（Meyer 図 1、成熟した雄）。高さは正面の写真で
      (1990 − 1139) ÷ 2465 = 0.345（Sunshine2）と (1785 − 1003) ÷ 2500 = 0.31（Sunshine4）の平均 0.33。
      写真の高さは表面に見える眼の開口なので、開口を外形の表面に置き、眼球の中心は表面の法線に沿って半径ぶん内へ入れる。
      径は成熟した雄の Taki 1963（O. japonica = 本種）「眼の軸の長さ ≈ 背側の外套長 ÷ 2.5」: 45 mm ÷ 2.5 = 18 mm、全幅 150 mm → 0.12 W。
      原記載の本文 9 mm ÷ 55 mm = 0.16 W は若い雄の値なので使わない
  殻: 横幅 35 mm ÷ 138 mm = 0.25 W（Meyer 本文と図）。前後は前の端から 0.53（Meyer 図 1 のひれの高さ。本文「ひれと同じ高さ」）。
      上からの形（奥行き・弓）は Meyer 図 5 の左半分、後ろからの曲がりは Verhoeff 2024 図 12 G（Sasaki 1929）の 16 点。
      翼の先の高さは、正面の写真でひれが体から出る高さ 0.28（Sunshine2 の左のひれの付け根 y 約 1300）
  顎板: 口は口側の中心（原記載 図 3）。大きさは原記載 図 4・5（3 倍）: 下顎 160 × 115 px、上顎 143 × 165 px、
      図 2 の横幅 835 px = 55 mm から 15.2 px/mm。横幅に対する比で 0.065 W（長さ）。
      横からの形は図 4・5 の輪郭。左右の厚みは図に無いので、その列の高さの 0.6 倍の楔にした（形の細部は手順 A5 で見直す）
"""

import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as nd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(ROOT, "docs", "references", "mendako")
OUT = os.path.join(ROOT, "docs", "mendako")
WORK = os.path.join(os.path.dirname(__file__), "work")
FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FONT_B = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"
W_MM = 138.0

EYE = dict(spacing=0.31, from_front=0.42, height=0.33, diameter=0.12)
SHELL = dict(span=0.25, from_front=0.53, tip_height=0.28, thickness=0.035)   # thickness は span に対する比（図 12 G の帯 約 25 px ÷ 720 px）
# Verhoeff 2024 図 12 G（30-verhoeff2024-fig12.png、300 dpi）で読んだ帯の中心。x 1265〜1985、中心 1625、鞍 y 590
G_LEFT = [(1480, 630), (1450, 670), (1420, 720), (1390, 765), (1330, 790), (1265, 815)]
G_RIGHT = [(1720, 625), (1780, 660), (1810, 700), (1840, 740), (1880, 765), (1940, 785), (1985, 805)]
G_CX, G_SADDLE_Y, G_SPAN = 1625, 590, 720
BEAK = dict(length=0.065)
PEAK = 0.198   # 頭の頂を後ろへずらす量（W）。2026-10-17 プロデューサー決定「横の線は C」。頂は前の端から 0.69、眼の開口 0.33


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


# ------------------------------------------------------------------
# 外形の入れ物
# ------------------------------------------------------------------
class Body:
    """peak = 頭の頂（断面の高さの中心）を、上から見た輪郭の中心から後ろへずらす量（W）。0 が A1 案 a"""

    def __init__(self, peak=None):
        if peak is None:
            peak = PEAK
        L = json.load(open(os.path.join(OUT, "a1_outline_lines.json"), encoding="utf-8"))
        self.peak = peak
        self.th = np.radians(np.array(L["dorsal"]["theta_deg"]))
        self.r = np.array(L["dorsal"]["r"]) * 0.5            # W = 1 なので半幅 = 0.5
        self.u = np.array(L["front"]["u"])
        self.v = np.array(L["front"]["v"])
        self.z_front = self.R(0.0)
        self.z_back = -self.R(np.pi)
        # 輪郭の点を、ずらした中心 (0, −peak) から見た角度と距離に直す
        px, pz = np.sin(self.th) * self.r, np.cos(self.th) * self.r
        phi = np.arctan2(px, pz + peak)
        o = np.argsort(phi)
        self.phi, self.D = phi[o], np.hypot(px, pz + peak)[o]

    def Dc(self, t):
        """ずらした中心から、角度 t の向きの輪郭までの距離"""
        t = np.mod(t + np.pi, 2 * np.pi) - np.pi
        return np.interp(t, self.phi, self.D, period=2 * np.pi)

    def R(self, t):
        t = np.mod(t, 2 * np.pi)
        return np.interp(t, np.append(self.th, 2 * np.pi), np.append(self.r, self.r[0]))

    def h(self, x, z):
        zz = z + self.peak
        t = np.arctan2(x, zz)       # θ = 0 が前（+z）。左右対称なので向きの符号は問わない
        rho = np.hypot(x, zz) / self.Dc(t)
        return np.where(rho <= 1, np.interp(rho, self.u[self.u >= 0], self.v[self.u >= 0]), 0.0)

    def z_at(self, frac):
        """前の端からの割合 → z"""
        return self.z_front - frac * (self.z_front - self.z_back)

    def mesh(self, n_r=60, n_t=144):
        rr = np.linspace(0, 1, n_r)
        tt = np.linspace(0, 2 * np.pi, n_t, endpoint=False)
        verts, faces = [], []
        for top in (True, False):
            base = len(verts)
            for t in tt:
                Rt = float(self.Dc(np.array([t]))[0])
                for rho in rr:
                    x, z = np.sin(t) * rho * Rt, np.cos(t) * rho * Rt - self.peak
                    y = float(np.interp(rho, self.u[self.u >= 0], self.v[self.u >= 0])) if top else 0.0
                    verts.append((x, y, z))
            for i in range(n_t):
                j = (i + 1) % n_t
                for k in range(n_r - 1):
                    a, b, c, d = base + i * n_r + k, base + j * n_r + k, base + j * n_r + k + 1, base + i * n_r + k + 1
                    faces += [(a, c, b), (a, d, c)] if top else [(a, b, c), (a, c, d)]
        return np.array(verts), np.array(faces)


# ------------------------------------------------------------------
# 部品
# ------------------------------------------------------------------
def ellipsoid(c, rad, n=24):
    verts, faces = [], []
    for i in range(n + 1):
        ph = np.pi * i / n
        for j in range(2 * n):
            t = np.pi * j / n
            verts.append((c[0] + rad[0] * np.sin(ph) * np.cos(t), c[1] + rad[1] * np.cos(ph), c[2] + rad[2] * np.sin(ph) * np.sin(t)))
    for i in range(n):
        for j in range(2 * n):
            a, b = i * 2 * n + j, i * 2 * n + (j + 1) % (2 * n)
            c2, d = a + 2 * n, b + 2 * n
            faces += [(a, b, c2), (b, d, c2)]
    return np.array(verts), np.array(faces)


def shell_profile():
    """後ろから見た下がり d(s)（span に対する比）、s = 中心からの割合 0..0.5。図 12 G の左右を平均"""
    pts = [(0.0, 0.0)]
    for (x, y) in G_LEFT + G_RIGHT:
        pts.append((abs(x - G_CX) / G_SPAN, (y - G_SADDLE_Y) / G_SPAN))
    pts.sort()
    s = np.array([p[0] for p in pts])
    d = np.array([p[1] for p in pts])
    grid = np.linspace(0, 0.5, 26)
    dd = np.interp(grid, s, d)
    dd = nd.gaussian_filter1d(np.concatenate([dd[::-1], dd[1:]]), 1.2)[len(grid) - 1:]
    return grid, dd - dd[0]


def shell_top():
    """上から見た奥行き w(s) と弓 a(s)（どちらも span に対する比）。Meyer 図 5 の左半分（10-meyer1906-taf11-left.jpg）"""
    a = np.asarray(Image.open(os.path.join(REF, "10-meyer1906-taf11-left.jpg")).convert("RGB")).astype(float)
    y0, x0 = 3650, 400
    a = a[y0:4000, x0:2600]
    paper = np.median(a[-40:, :200].reshape(-1, 3), 0)
    m = np.sqrt(((nd.gaussian_filter(a, (2, 2, 0)) - paper) ** 2).sum(-1)) > 30
    m = nd.binary_opening(nd.binary_fill_holes(nd.binary_closing(m, iterations=4)), iterations=2)
    lab, n = nd.label(m)
    m = lab == 1 + int(np.argmax(nd.sum(m, lab, range(1, n + 1))))
    cx, xl = 1490 - x0, 507 - x0           # 中心は左右の先（507 と 2470）の中点 約 1490
    half = cx - xl
    grid = np.linspace(0, 0.5, 26)
    w, mid = [], []
    for s in grid:
        x = int(round(cx - s / 0.5 * half))
        c = np.nonzero(m[:, x])[0]
        w.append((c.max() - c.min()) if len(c) else 0)
        mid.append((c.max() + c.min()) / 2 if len(c) else np.nan)
    w = np.array(w, float) / (2 * half)
    mid = np.array(mid)
    mid = np.interp(np.arange(len(mid)), np.nonzero(np.isfinite(mid))[0], mid[np.isfinite(mid)])
    arc = -(mid - mid[0]) / (2 * half)     # 図の上 = 前（vo）。前へ出るほど +
    # 付け根の楕円（tab）の所は輪郭が乱れるので、奥行きを外へ膨らむ形でならす
    w = nd.maximum_filter1d(w, 3)
    w = nd.gaussian_filter1d(w, 1.0)
    w[-1] = 0.0
    return grid, w, nd.gaussian_filter1d(arc, 1.0)


def shell_mesh(body):
    span = SHELL["span"]
    gs, drop = shell_profile()
    gt, w, arc = shell_top()
    z0 = body.z_at(SHELL["from_front"])
    tip_drop = float(drop[-1]) * span
    y_saddle = SHELL["tip_height"] + tip_drop
    th = SHELL["thickness"] * span
    n = 61
    s = np.linspace(-0.5, 0.5, n)
    verts, faces = [], []
    ring = 8
    for si in s:
        a = abs(si)
        dz = np.interp(a, gt, w) * span / 2
        dz = max(dz, 0.004 * span)
        cz = z0 + np.interp(a, gt, arc) * span
        cy = y_saddle - np.interp(a, gs, drop) * span
        cx = si * span
        for k in range(ring):
            t = 2 * np.pi * k / ring
            verts.append((cx, cy + np.sin(t) * th / 2, cz + np.cos(t) * dz))
    for i in range(n - 1):
        for k in range(ring):
            a, b = i * ring + k, i * ring + (k + 1) % ring
            faces += [(a, a + ring, b), (b, a + ring, b + ring)]
    verts = np.array(verts)
    # 両端を閉じる
    for end, flip in ((0, True), (n - 1, False)):
        c = len(verts)
        verts = np.vstack([verts, verts[end * ring:(end + 1) * ring].mean(0)])
        for k in range(ring):
            a, b = end * ring + k, end * ring + (k + 1) % ring
            faces.append((c, b, a) if flip else (c, a, b))
    info = dict(span=span, z=z0, y_saddle=y_saddle, y_tips=SHELL["tip_height"], drop_over_span=float(drop[-1]),
                depth_over_span_max=float(w.max()), arc_over_span_tip=float(arc[-1]))
    return verts, np.array(faces), info


def beak_outline(box):
    a = np.asarray(Image.open(os.path.join(REF, "01-ijima-ikeda-1895-pl33.jpg")).convert("L")).astype(float)
    a = a[box[1]:box[3], box[0]:box[2]]
    paper = np.percentile(a, 95)
    m = nd.gaussian_filter(a, 1.5) < paper - 22
    m = nd.binary_fill_holes(nd.binary_closing(m, iterations=3))
    lab, n = nd.label(m)
    return lab == 1 + int(np.argmax(nd.sum(m, lab, range(1, n + 1))))


def beak_mesh(body):
    """図 4（下顎）・図 5（上顎）の横からの輪郭を、口へ向けて置く。口は口側の中心（y = 0 の少し上）"""
    parts = []
    L = BEAK["length"]
    for name, box in (("lower", (230, 270, 420, 410)), ("upper", (1600, 260, 1770, 450))):
        m = beak_outline(box)
        ys, xs = np.nonzero(m)
        sc = L / (xs.max() - xs.min())
        # 図の輪郭を (z, y) に。図の上 = 体の下（口）へ向けるため上下を反転し、口側の面の少し上に置く
        step = 3
        verts, faces = [], []
        cols = list(range(xs.min(), xs.max() + 1, step))
        for ci, x in enumerate(cols):
            c = np.nonzero(m[:, x])[0]
            top, bot = (c.min(), c.max()) if len(c) else (ys.mean(), ys.mean())
            hgt = (bot - top) * sc
            hw = 0.3 * max(hgt, 0.002)   # 左右の厚みの半分（図に無いので高さの 0.3 倍）
            z = (x - (xs.min() + xs.max()) / 2) * sc
            y_top = (ys.max() - top) * sc
            y_bot = (ys.max() - bot) * sc
            for (yy, xx) in ((y_bot, -hw), (y_bot, hw), (y_top, hw), (y_top, -hw)):
                verts.append((xx, yy, z))
        nC = len(cols)
        for i in range(nC - 1):
            for k in range(4):
                a, b = i * 4 + k, i * 4 + (k + 1) % 4
                faces += [(a, b, a + 4), (b, b + 4, a + 4)]
        verts = np.array(verts)
        z_mouth = (body.z_front + body.z_back) / 2
        verts[:, 2] += z_mouth
        verts[:, 1] = verts[:, 1] - verts[:, 1].min() + 0.01   # 口側の面から 0.01 W 上
        if name == "upper":
            verts[:, 1] += 0.012
        parts.append((name, verts, np.array(faces)))
    return parts


def save_obj(path, v, f):
    with open(path, "w") as fp:
        for p in v:
            fp.write(f"v {p[0]:.5f} {p[1]:.5f} {p[2]:.5f}\n")
        for t in f:
            fp.write(f"f {t[0] + 1} {t[1] + 1} {t[2] + 1}\n")


def signed_volume(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6)


def clearance(body, v):
    """各頂点の、上の面までの余り（h − y）と口側の面からの高さ y の最小。W に対する比"""
    hv = body.h(v[:, 0], v[:, 2])
    return float((hv - v[:, 1]).min()), float(v[:, 1].min())


# ------------------------------------------------------------------
# 描画（不透明の診断用。正射影、Lambert）
# ------------------------------------------------------------------
VIEWS = {
    "top": (lambda p: (p[:, 0] * -1, -p[:, 2]), lambda p: p[:, 1], np.array([0, 1, 0])),   # 前が上、体の左が図の左
    "front": (lambda p: (-p[:, 0], -p[:, 1]), lambda p: p[:, 2], np.array([0, 0, 1])),     # 前から見る: 体の左は図の右
    "side": (lambda p: (-p[:, 2], -p[:, 1]), lambda p: p[:, 0], np.array([1, 0, 0])),      # 体の左から見る: 前が図の左
}


def render(meshes, view, size=600, extent=0.62, alpha_body=True, fit=False):
    """fit = True のときは、最初の面の投影の中心を絵の中心に置く（部品だけの絵）"""
    proj, depth, eye = VIEWS[view]
    off = np.zeros(2)
    if fit:
        X0, Y0 = proj(meshes[0][0])
        off = -np.array([(X0.min() + X0.max()) / 2, (Y0.min() + Y0.max()) / 2])
    img = np.ones((size, size, 3)) * 0.97
    zb = np.full((size, size), -1e9)
    S = size / (2 * extent)
    for v, f, col, alpha in meshes:
        X, Y = proj(v)
        X = (X + off[0]) * S + size / 2
        Y = (Y + off[1]) * S + size / 2 + (0.15 * S if view != "top" and not fit else 0)
        D = depth(v)
        tri = f
        n = np.cross(v[tri[:, 1]] - v[tri[:, 0]], v[tri[:, 2]] - v[tri[:, 0]])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        shade = 0.35 + 0.65 * np.abs(n @ (eye * 0.8 + np.array([0.3, 0.5, 0.2])) / np.linalg.norm(eye * 0.8 + np.array([0.3, 0.5, 0.2])))
        for t, sh in zip(tri, shade):
            xs, ys, ds = X[t], Y[t], D[t]
            x0, x1 = int(max(0, np.floor(xs.min()))), int(min(size - 1, np.ceil(xs.max())))
            y0, y1 = int(max(0, np.floor(ys.min()))), int(min(size - 1, np.ceil(ys.max())))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            d = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
            if abs(d) < 1e-9:
                continue
            l0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / d
            l1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / d
            l2 = 1 - l0 - l1
            inside = (l0 >= 0) & (l1 >= 0) & (l2 >= 0)
            if not inside.any():
                continue
            dd = l0 * ds[0] + l1 * ds[1] + l2 * ds[2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            win = inside & (dd > sub)
            if alpha < 1:
                im = img[y0:y1 + 1, x0:x1 + 1]
                im[inside] = im[inside] * (1 - alpha) + np.array(col) * sh * alpha
                continue
            sub[win] = dd[win]
            img[y0:y1 + 1, x0:x1 + 1][win] = np.array(col) * sh
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def build_parts(body):
    """眼（開口を表面に置き、中心を法線に沿って内へ）・殻・顎板を作る"""
    eye_z = body.z_at(EYE["from_front"])
    eyes = []
    r = EYE["diameter"] / 2
    eye_open = []
    for sx in (1, -1):
        x = sx * EYE["spacing"] / 2
        y = float(body.h(np.array([x]), np.array([eye_z]))[0])
        e = 1e-3
        dhx = float(body.h(np.array([x + e]), np.array([eye_z]))[0] - body.h(np.array([x - e]), np.array([eye_z]))[0]) / (2 * e)
        dhz = float(body.h(np.array([x]), np.array([eye_z + e]))[0] - body.h(np.array([x]), np.array([eye_z - e]))[0]) / (2 * e)
        nrm = np.array([-dhx, 1.0, -dhz])
        nrm /= np.linalg.norm(nrm)
        c = np.array([x, y, eye_z]) - nrm * r
        eye_open.append(dict(opening=[round(x, 4), round(y, 4), round(eye_z, 4)], normal=[round(float(t), 3) for t in nrm]))
        eyes.append(ellipsoid(c, (r, r, r)))
    sv, sf, sinfo = shell_mesh(body)
    beaks = beak_mesh(body)
    return eyes, eye_open, (sv, sf, sinfo), beaks


def main():
    os.makedirs(WORK, exist_ok=True)
    body = Body()
    bv, bf = body.mesh()
    eyes, eye_open, (sv, sf, sinfo), beaks = build_parts(body)
    print("眼の開口（表面）の高さ", [o["opening"][1] for o in eye_open], "写真の測定 0.31〜0.345")

    report = dict(date="2026-10-17", W_mm=W_MM, axes="+Y 背、+Z 前、+X 体の左。単位 W = 1",
                  body=dict(z_front=body.z_front, z_back=body.z_back, height_max=float(body.v.max())),
                  parts={})
    allp = [("eye_left", *eyes[0]), ("eye_right", *eyes[1]), ("shell", sv, sf)] + [("beak_" + n, v, f) for n, v, f in beaks]
    for name, v, f in allp:
        top_gap, bottom = clearance(body, v)
        vol = signed_volume(v, f)
        save_obj(os.path.join(WORK, f"a2_{name}.obj"), v, f)
        report["parts"][name] = dict(center=[round(float(c), 4) for c in v.mean(0)],
                                     size=[round(float(s), 4) for s in v.max(0) - v.min(0)],
                                     top_gap_min=round(top_gap, 4), top_gap_min_mm=round(top_gap * W_MM, 1),
                                     above_oral_min=round(bottom, 4), signed_volume=vol)
        print(f"{name:12s} 中心 {np.round(v.mean(0), 3)} 大きさ {np.round(v.max(0) - v.min(0), 3)} "
              f"上の面までの余り 最小 {top_gap:+.3f} W ({top_gap * W_MM:+.1f} mm) 口側から {bottom:.3f} 体積 {vol:+.2e}")
    report["shell"] = sinfo
    report["eye_opening"] = eye_open
    save_obj(os.path.join(WORK, "a2_body.obj"), bv, bf)
    report["body"]["signed_volume"] = signed_volume(bv, bf)
    with open(os.path.join(OUT, "a2_parts.json"), "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=1)
    sheet(body, bv, bf, eyes, (sv, sf), beaks, report)


def sheet(body, bv, bf, eyes, shell, beaks, report):
    BODY = (0.78, 0.86, 0.9)
    parts = [(eyes[0][0], eyes[0][1], (0.35, 0.35, 0.4), 1), (eyes[1][0], eyes[1][1], (0.35, 0.35, 0.4), 1),
             (shell[0], shell[1], (0.1, 0.35, 0.85), 1)] + [(v, f, (0.75, 0.5, 0.15), 1) for _, v, f in beaks]
    TW = 600
    W = 4 * TW + 100
    H = 120 + 2 * (TW + 150) + 40
    out = Image.new("RGB", (W, H), (248, 247, 244))
    dr = ImageDraw.Draw(out)
    dr.text((20, 16), "メンダコ 手順 A2: 殻・顎板・眼を置く（2026-10-17）", font=font(40, True), fill=(20, 20, 20))
    dr.text((20, 70), "不透明の診断用の絵（正射影）。水色 = 外形（A1 の決定、半透明）、青 = 殻、灰 = 眼、茶 = 顎板。横幅 W = 1（約 138 mm）",
            font=font(22), fill=(60, 60, 60))

    def put(img, x, y, t1, t2):
        img = img.resize((TW, TW))
        out.paste(img, (x, y))
        dr.text((x, y + TW + 8), t1, font=font(23, True), fill=(20, 20, 20))
        yy = y + TW + 42
        f = font(18)
        for para in t2.split("\n"):
            line = ""
            for ch in para:
                if dr.textlength(line + ch, font=f) > TW - 8:
                    dr.text((x, yy), line, font=f, fill=(70, 70, 70)); yy += 24; line = ch
                else:
                    line += ch
            dr.text((x, yy), line, font=f, fill=(70, 70, 70)); yy += 24

    def ref(path, box):
        im = Image.open(path).convert("RGB").crop(box)
        s = min(TW / im.width, TW / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)))
        o = Image.new("RGB", (TW, TW), (255, 255, 255))
        o.paste(im, ((TW - im.width) // 2, (TW - im.height) // 2))
        return o

    meshes = [(bv, bf, BODY, 0.35)] + parts
    p = report["parts"]
    y = 120
    put(render(meshes, "top"), 20, y, "上から（前が上）",
        f"眼の間 0.31、前の端から 0.42。殻は前の端から 0.53、横幅 0.25。顎板は中心（口）")
    put(ref(os.path.join(REF, "10-meyer1906-taf11-left.jpg"), (400, 300, 2200, 2150)), 40 + TW, y, "参考: Meyer 1906 図 1（成熟した雄、背）",
        "眼（Au）・ひれ（Fl）・外套の開口（M）の前後の位置を比べる。PD")
    put(render(meshes, "front"), 60 + 2 * TW, y, "前から",
        f"眼の開口の高さ {report['eye_opening'][0]['opening'][1]:.2f}（写真 0.31〜0.345）。殻の翼の先 0.28、鞍 {report['shell']['y_saddle']:.3f}")
    put(ref(os.path.join(REF, "05-sunshine2-live.jpg"), (600, 700, 3300, 2300)), 80 + 3 * TW, y, "参考: Sunshine2（生体の正面）",
        "眼の高さとひれの付け根を比べる。Totti, CC BY-SA 4.0")
    y += TW + 150
    put(render(meshes, "side"), 20, y, "体の左から（前が左）",
        "横の外形は正面と同じ形（A1 案 a）。眼・殻・顎板の前後と高さ")
    sv, sf = shell
    sh_only = [(sv, sf, (0.1, 0.35, 0.85), 1)]
    put(render(sh_only, "top", extent=0.16, fit=True), 40 + TW, y, "殻だけ: 上から（前が上）",
        f"奥行き 最大 span の {report['shell']['depth_over_span_max']:.3f}、両端が前へ {report['shell']['arc_over_span_tip']:.3f}。下の参考 Meyer 図 5 と比べる")
    put(render(sh_only, "front", extent=0.16, fit=True), 60 + 2 * TW, y, "殻だけ: 前から",
        f"翼の下がり span の {report['shell']['drop_over_span']:.2f}（図 12 G の 0.31 をならした値）。後ろから見ると左右が逆になるだけ")
    # 参考 2 つを縦に
    a = ref(os.path.join(REF, "10-meyer1906-taf11-left.jpg"), (420, 3700, 2600, 3980)).crop((0, 150, TW, 450))
    b = ref(os.path.join(REF, "30-verhoeff2024-fig12.png"), (1240, 540, 2020, 840)).crop((0, 100, TW, 500))
    c = Image.new("RGB", (TW, TW), (255, 255, 255))
    c.paste(a.resize((TW, 200)), (0, 30))
    c.paste(b.resize((TW, 330)), (0, 260))
    put(c, 80 + 3 * TW, y, "参考: 殻（上 Meyer 図 5、下 Verhoeff 2024 図 12 G）",
        "上: 上から（前が上）、PD。下: 後ろから（成熟した雄、Sasaki 1929 の描き直し）、CC BY 4.0")
    out.save(os.path.join(OUT, "a2_parts.jpg"), quality=88)
    print(os.path.join(OUT, "a2_parts.jpg"), out.size)


if __name__ == "__main__":
    main()

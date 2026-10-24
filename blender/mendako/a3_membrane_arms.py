"""
メンダコ 手順 A3: 膜（体の外形）・腕・吸盤・触毛・ひれを作り、面の向き・開いた辺・凹凸・外形との関係を確かめる。

  .venv/bin/python -I blender/mendako/a3_membrane_arms.py

入力: A1 の線（a1_outline_lines.json）と A2 の外形（a2_parts.Body、頭の頂のずらし 0.198 = 決定 C）
出力:
  blender/mendako/work/a3_*.obj        部品の面（git に入れない）
  docs/mendako/a3_parts.json           寸法・数・確認の結果
  docs/mendako/a3_parts.jpg            不透明の診断用の絵（上・口側・前・横・斜め）と参考の並べ

軸: +Y が背、+Z が前、+X が体の左。単位は横幅 W = 1（成熟した雄で約 138 mm）。

元（数は計画書 第 7 節 A3 に、どの画像のどこから何 px かを書く）:
  腕の向き: A1 の上の線の 8 つの山（±13°・±51°・±95°・±143°。180° の山は第 4 腕のあいだの膨らみなので外す）
  腕の先: 膜の縁から先は膜が無く、腕の長さの約 1/5（Taki 1963「腕の先 1/5 は膜が無い」、成熟した雄）。先は背へ巻く
          （原記載 図 2・3、Meyer 図 1、Sasaki の口側の図で、腕の先は鉤のように巻いている）
  吸盤: 1 本の腕に 50（ToL・Sasaki: 雌で 50 余）。5〜19 番目の 15 個が大きい（ToL「5〜20 番目」、Verhoeff 2024「15〜20」）。
        大きい吸盤の径 0.053 W（Verhoeff 2024 図 12 A = Sasaki の雄の口側: 横幅 x 230〜1215 の 985 px に対し約 52 px）、
        ふつうの吸盤 0.02 W（同 約 19 px）。大きい吸盤は押し合ってジグザグに 2 列に見える（Meyer 本文、図 12 A）
  触毛: 吸盤と交互に、腕の両脇に 1 本ずつ。2 番目の吸盤から始まる（ToL）。長さ 最大 0.04 W（Taki: 最長 6 mm ÷ 全幅 150 mm）
  腕の太さ: 半径は付け根 0.03 W、大きい吸盤の所 0.035 W（吸盤の径 0.053 を載せる幅）、先へ細く 0.006 W
  ひれ: 正面の写真（Sunshine2）で、外の端が中心から 0.345 W（横幅の 0.69 の半分）、上下は 0.10〜0.30。
        付け根は殻の高さ（前の端から 0.53）で体の横の面から出る。生体では耳のように立ち、前を向いた面が見える
"""

import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as nd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a2_parts as A  # noqa: E402

ARM_DEG = {"I": 13.0, "II": 51.0, "III": 95.0, "IV": 143.0}
FREE_TIP = 0.2          # 腕の長さのうち膜の無い先の割合
CURL_ANGLE = 1.5 * np.pi   # 先が背へ巻く角度
CURL_STRAIGHT = 0.0        # 膜の無い先のうち、巻く前にまっすぐ伸ばす割合
N_SUCKERS = 50
BIG = range(4, 19)      # 0 始まりで 5〜19 番目
D_BIG, D_SMALL = 0.053, 0.02
CIRRUS_LEN, CIRRUS_R = 0.04, 0.003
FIN = dict(tip_x=0.345, y_low=0.10, y_high=0.30, thick=0.012)


# ------------------------------------------------------------------
# 面の道具
# ------------------------------------------------------------------
def weld(v, f, tol=1e-6):
    key = np.round(v / tol).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.reshape(-1)
    v2 = v[idx]
    f2 = inv[f]
    ok = (f2[:, 0] != f2[:, 1]) & (f2[:, 1] != f2[:, 2]) & (f2[:, 0] != f2[:, 2])
    return v2, f2[ok]


def open_edges(f):
    e = np.sort(np.vstack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _, c = np.unique(e, axis=0, return_counts=True)
    return int((c == 1).sum()), int((c > 2).sum())


def merge(parts):
    vs, fs, off = [], [], 0
    for v, f in parts:
        vs.append(v)
        fs.append(f + off)
        off += len(v)
    return np.vstack(vs), np.vstack(fs)


def frame(path):
    """道の各点の接線 T と、それに直交する 2 本（N は上 +Y に近い向き）"""
    T = np.gradient(path, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    up = np.array([0, 1.0, 0])
    N, B = [], []
    prevN = None
    for t in T:
        ref = up if prevN is None else prevN
        n = ref - t * (ref @ t)
        if np.linalg.norm(n) < 1e-6:
            n = np.cross(t, [1, 0, 0])
        n /= np.linalg.norm(n)
        N.append(n)
        B.append(np.cross(t, n))
        prevN = n
    return T, np.array(N), np.array(B)


def tube(path, radii, ring=10, scale_n=None):
    """道に沿った管。両端は閉じる。scale_n: 断面の N 方向（背腹）の倍率"""
    T, N, Bn = frame(path)
    sn = np.ones(len(path)) if scale_n is None else scale_n
    verts, faces = [], []
    for p, n, b, r, k in zip(path, N, Bn, radii, sn):
        for j in range(ring):
            a = 2 * np.pi * j / ring
            verts.append(p + r * (np.cos(a) * n * k + np.sin(a) * b))
    m = len(path)
    for i in range(m - 1):
        for j in range(ring):
            a, b = i * ring + j, i * ring + (j + 1) % ring
            faces += [(a, b, a + ring), (b, b + ring, a + ring)]
    verts = np.array(verts)
    for end, flip in ((0, True), (m - 1, False)):
        c = len(verts)
        verts = np.vstack([verts, path[end]])
        for j in range(ring):
            a, b = end * ring + j, end * ring + (j + 1) % ring
            faces.append((c, a, b) if flip else (c, b, a))
    v, f = np.array(verts), np.array(faces)
    if A.signed_volume(v, f) < 0:
        f = f[:, ::-1]
    return v, f


def cup(c, axis, d, h, n=16):
    """吸盤: 口側へ向いた短い円柱（上下を閉じる）。c は付け根の中心、axis は開口の向き"""
    axis = axis / np.linalg.norm(axis)
    a1 = np.cross(axis, [0, 0, 1.0])
    if np.linalg.norm(a1) < 1e-6:
        a1 = np.cross(axis, [1.0, 0, 0])
    a1 /= np.linalg.norm(a1)
    a2 = np.cross(axis, a1)
    r = d / 2
    verts = []
    for k, (hh, rr) in enumerate(((0, r * 0.8), (h, r), (h * 1.05, r * 0.55))):
        for j in range(n):
            t = 2 * np.pi * j / n
            verts.append(c + axis * hh + rr * (np.cos(t) * a1 + np.sin(t) * a2))
    verts.append(c)
    verts.append(c + axis * h * 0.7)        # 開口の底（くぼみ）
    faces = []
    for k in range(2):
        for j in range(n):
            a, b = k * n + j, k * n + (j + 1) % n
            faces += [(a, b, a + n), (b, b + n, a + n)]
    cb, ct = 3 * n, 3 * n + 1
    for j in range(n):
        faces.append((cb, (j + 1) % n, j))
        faces.append((ct, 2 * n + j, 2 * n + (j + 1) % n))
    v, f = np.array(verts), np.array(faces)
    if A.signed_volume(v, f) < 0:
        f = f[:, ::-1]
    return v, f


# ------------------------------------------------------------------
# 膜
# ------------------------------------------------------------------
def membrane(body, n_r=70, n_t=180):
    rr = np.linspace(0, 1, n_r)
    tt = np.linspace(0, 2 * np.pi, n_t, endpoint=False)
    uu, vv = body.u[body.u >= 0], body.v[body.u >= 0]
    top, bot = [], []
    for t in tt:
        Rt = float(body.Dc(np.array([t]))[0])
        for rho in rr:
            x, z = np.sin(t) * rho * Rt, np.cos(t) * rho * Rt - body.peak
            top.append((x, float(body.h(np.array([x]), np.array([z]))[0]) if rho < 1 else float(vv[-1]), z))
            bot.append((x, 0.0, z))
    verts = np.array(top + bot)
    nb = len(top)
    faces = []
    for i in range(n_t):
        j = (i + 1) % n_t
        for k in range(n_r - 1):
            a, b, c, d = i * n_r + k, j * n_r + k, j * n_r + k + 1, i * n_r + k + 1
            faces += [(a, c, b), (a, d, c)]
            faces += [(a + nb, b + nb, c + nb), (a + nb, c + nb, d + nb)]
        # 縁の帯（上の縁 → 下の縁）
        a, b = i * n_r + n_r - 1, j * n_r + n_r - 1
        faces += [(a, b, b + nb), (a, b + nb, a + nb)]
    v, f = weld(verts, np.array(faces))
    if A.signed_volume(v, f) < 0:
        f = f[:, ::-1]
    return v, f


# ------------------------------------------------------------------
# 腕・吸盤・触毛
# ------------------------------------------------------------------
def arm_path(body, deg, n=120):
    """口（中心）から膜の縁まで口側の面に沿い、そこから先は背へ巻く。返すのは点と、膜の縁の位置の割合"""
    t = np.radians(deg)
    zc = -body.peak
    mouth = np.array([0.0, 0.0, (body.z_front + body.z_back) / 2])
    Rt = float(body.Dc(np.array([t]))[0])
    edge = np.array([np.sin(t) * Rt, 0.0, np.cos(t) * Rt + zc])
    d = edge - mouth
    L_web = np.linalg.norm(d)
    L = L_web / (1 - FREE_TIP)
    out = d / L_web
    pts = []
    n_web = int(n * (1 - FREE_TIP))
    for s in np.linspace(0, 1, n_web, endpoint=False):
        p = mouth + d * s
        pts.append(p)
    # 先: 外へ出ながら背へ巻く（半径 = 自由な長さ / (1.5π)、約 270°）
    Lf = L - L_web
    Ls = Lf * CURL_STRAIGHT
    rc = (Lf - Ls) / CURL_ANGLE
    n_free = n - n_web
    n_s = int(n_free * CURL_STRAIGHT)
    for k in range(n_s):
        pts.append(edge + out * Ls * k / max(n_s, 1))
    start = edge + out * Ls
    for a in np.linspace(0, CURL_ANGLE, n_free - n_s):
        pts.append(start + out * rc * np.sin(a) + np.array([0, 1.0, 0]) * rc * (1 - np.cos(a)))
    pts = np.array(pts)
    return pts, n_web / n, L


def arm_radius(s):
    """s = 口からの長さの割合"""
    return np.interp(s, [0, 0.12, 0.45, 0.8, 1.0], [0.03, 0.035, 0.03, 0.012, 0.006])


def sucker_sizes():
    d = np.zeros(N_SUCKERS)
    for i in range(N_SUCKERS):
        if i in BIG:
            k = (i - BIG.start) / (len(BIG) - 1)
            d[i] = D_SMALL + (D_BIG - D_SMALL) * np.sin(np.pi * (0.15 + 0.7 * k)) / np.sin(np.pi * 0.5)
        elif i < BIG.start:
            d[i] = D_SMALL * (0.6 + 0.1 * i)
        else:
            k = (i - BIG.stop) / (N_SUCKERS - BIG.stop)
            d[i] = D_SMALL * (1.0 - 0.65 * k)
    return np.minimum(d, D_BIG)


def arm_parts(body, deg, side):
    t = deg if side > 0 else -deg
    path, web_frac, L = arm_path(body, t)
    n = len(path)
    s = np.linspace(0, 1, n)
    r = arm_radius(s)
    # 口側の面（y = 0）に腕の下の縁を合わせ、膜に埋める
    path = path.copy()
    path[: int(n * web_frac), 1] += r[: int(n * web_frac)] * 0.9
    k = int(n * web_frac)
    path[k:, 1] += r[k - 1] * 0.9
    arm = tube(path, r, ring=10, scale_n=np.full(n, 0.85))
    # 吸盤: 口から先端の 0.97 まで。大きい吸盤の所は詰めて置き、ジグザグに左右へずらす
    d = sucker_sizes()
    w = np.where([i in BIG for i in range(N_SUCKERS)], d * 0.55, d * 1.05)
    pos = np.cumsum(w) - w / 2
    pos = 0.03 + pos / pos[-1] * 0.94
    T, Nn, Bn = frame(path)
    suckers, cirri = [], []
    for i, (si, di) in enumerate(zip(pos, d)):
        j = min(int(si * (n - 1)), n - 1)
        p, nn, bb = path[j], Nn[j], Bn[j]
        rr = float(arm_radius(si))
        zig = (0.35 * rr if i % 2 else -0.35 * rr) if i in BIG else 0.0
        base = p - nn * rr * 0.8 + bb * zig
        suckers.append(cup(base, -nn, di, di * 0.45))
        if i >= 1:
            for sgn in (1, -1):
                q0 = p - nn * rr * 0.6 + bb * sgn * rr * 0.9
                ln = CIRRUS_LEN * np.interp(si, [0, 0.3, 1], [0.6, 1.0, 0.4])
                dirc = -nn * 0.7 + bb * sgn * 0.7
                dirc /= np.linalg.norm(dirc)
                cp = np.array([q0 + dirc * ln * a for a in np.linspace(0, 1, 6)])
                cirri.append(tube(cp, np.linspace(CIRRUS_R, CIRRUS_R * 0.4, 6), ring=6))
    return arm, suckers, cirri, dict(deg=t, length=L, web_frac=web_frac)


# ------------------------------------------------------------------
# ひれ
# ------------------------------------------------------------------
def fin(body, side):
    z0 = body.z_at(A.SHELL["from_front"])
    yr = A.SHELL["tip_height"]
    # 付け根: 殻の高さで、体の横の面の上（h(x, z0) = yr の x）
    xs = np.linspace(0, 0.5, 2000)
    hx = body.h(xs, np.full_like(xs, z0))
    x_root = float(xs[np.nonzero((hx < yr) & (xs > 0.05))[0][0]]) - 0.01
    x_tip = FIN["tip_x"]
    n_s, n_t = 24, 16
    verts = []
    for i, s in enumerate(np.linspace(0, 1, n_s)):
        x = x_root + (x_tip - x_root) * s
        yc = yr + (0.5 * (FIN["y_low"] + FIN["y_high"]) - yr) * s
        half = 0.035 + (0.5 * (FIN["y_high"] - FIN["y_low"]) - 0.035) * np.sin(np.pi / 2 * min(1.0, s / 0.75))
        if s > 0.85:
            half *= np.sqrt(max(0.0, 1 - ((s - 0.85) / 0.15) ** 2))
        th = FIN["thick"] * (1 - 0.7 * s)
        for j in range(n_t):
            a = 2 * np.pi * j / n_t
            verts.append((side * x, yc + half * np.cos(a), z0 + 0.5 * th * np.sin(a)))
    faces = []
    for i in range(n_s - 1):
        for j in range(n_t):
            a, b = i * n_t + j, i * n_t + (j + 1) % n_t
            faces += [(a, b, a + n_t), (b, b + n_t, a + n_t)]
    verts = np.array(verts)
    for end, flip in ((0, True), (n_s - 1, False)):
        c = len(verts)
        verts = np.vstack([verts, verts[end * n_t:(end + 1) * n_t].mean(0)])
        for j in range(n_t):
            a, b = end * n_t + j, end * n_t + (j + 1) % n_t
            faces.append((c, a, b) if flip else (c, b, a))
    v, f = verts, np.array(faces)
    if A.signed_volume(v, f) < 0:
        f = f[:, ::-1]
    return v, f, x_root


# ------------------------------------------------------------------
def roughness(body):
    """膜の上の面の凹凸: 高さの場を 0.01 W（約 1.4 mm）でならした面との差（mm）。肩の丸みのような大きな形は数えない"""
    g = np.linspace(-0.6, 0.6, 481)
    X, Z = np.meshgrid(g, g)
    Hh = body.h(X.ravel(), Z.ravel()).reshape(X.shape)
    inside = Hh > 0.035
    Hs = nd.gaussian_filter(Hh, 0.01 / (g[1] - g[0]))
    dev = np.abs(Hh - Hs)[nd.binary_erosion(inside, iterations=20)]
    return float(dev.max() * A.W_MM), float(np.percentile(dev, 95) * A.W_MM)


VIEWS_EXTRA = {
    "oral": (lambda p: (p[:, 0], -p[:, 2]), lambda p: -p[:, 1], np.array([0, -1, 0])),   # 下から（前が上、体の左が図の右）
    "oblique": (lambda p: (-(p[:, 0] * 0.8 - p[:, 2] * 0.6), -(p[:, 1] * 0.94 - (p[:, 0] * 0.6 + p[:, 2] * 0.8) * 0.34)),
                lambda p: (p[:, 0] * 0.6 + p[:, 2] * 0.8) * 0.94 + p[:, 1] * 0.34, np.array([0.5, 0.4, 0.7])),
}
A.VIEWS.update(VIEWS_EXTRA)


def main():
    os.makedirs(A.WORK, exist_ok=True)
    body = A.Body()
    report = dict(date="2026-10-17", W_mm=A.W_MM, peak=body.peak, parts={}, arms={})
    mv, mf = membrane(body)
    oe, nm = open_edges(mf)
    report["parts"]["membrane"] = dict(verts=len(mv), faces=len(mf), open_edges=oe, nonmanifold=nm, signed_volume=A.signed_volume(mv, mf))
    A.save_obj(os.path.join(A.WORK, "a3_membrane.obj"), mv, mf)
    arm_meshes, sucker_meshes, cirri_meshes = [], [], []
    worst_out = 0.0
    for name, deg in ARM_DEG.items():
        for side, sname in ((1, "L"), (-1, "R")):
            arm, suckers, cirri, info = arm_parts(body, deg, side)
            arm_meshes.append(arm)
            sucker_meshes += suckers
            cirri_meshes += cirri
            # 膜のある所（口から膜の縁まで）の腕が、膜の上の面から出ていないか。縁から先の巻いた先は数えない
            v = arm[0]
            n_path = (len(v) - 2) // 10            # 管の輪は 10 点、両端の蓋の中心が 2 点
            idx = np.arange(len(v) - 2) // 10
            web = np.zeros(len(v), bool)
            web[:-2] = idx < int(n_path * (info["web_frac"] - 0.03))   # 膜の縁より 3% 手前まで（巻き始めは数えない）
            out = (v[:, 1] - body.h(v[:, 0], v[:, 2]))[web]
            worst_out = max(worst_out, float(out.max()) if len(out) else 0.0)
            report["arms"][name + sname] = dict(deg=round(info["deg"], 1), length=round(info["length"], 3), web_frac=round(info["web_frac"], 2))
    for key, meshes in (("arms", arm_meshes), ("suckers", sucker_meshes), ("cirri", cirri_meshes)):
        oes = [open_edges(f)[0] for _, f in meshes]
        vols = [A.signed_volume(v, f) for v, f in meshes]
        report["parts"][key] = dict(count=len(meshes), open_edges_total=int(sum(oes)), min_signed_volume=float(min(vols)))
        v, f = merge(meshes)
        A.save_obj(os.path.join(A.WORK, f"a3_{key}.obj"), v, f)
    report["arm_above_membrane_max_mm"] = round(worst_out * A.W_MM, 1)
    fins = []
    for side in (1, -1):
        fv, ff, xr = fin(body, side)
        fins.append((fv, ff))
        report["parts"]["fin_" + ("L" if side > 0 else "R")] = dict(open_edges=open_edges(ff)[0], signed_volume=A.signed_volume(fv, ff), x_root=round(xr, 3))
    v, f = merge(fins)
    A.save_obj(os.path.join(A.WORK, "a3_fins.obj"), v, f)
    report["roughness_mm"] = dict(zip(["max", "p95"], [round(x, 2) for x in roughness(body)]))
    report["sucker_diameters"] = [round(float(x), 4) for x in sucker_sizes()]
    with open(os.path.join(A.OUT, "a3_parts.json"), "w", encoding="utf-8") as fp:
        json.dump(report, fp, ensure_ascii=False, indent=1)
    print(json.dumps({k: report[k] for k in ("parts", "arm_above_membrane_max_mm", "roughness_mm")}, ensure_ascii=False, indent=1))
    sheet(body, (mv, mf), arm_meshes, sucker_meshes, cirri_meshes, fins, report)


def sheet(body, mem, arms, suckers, cirri, fins, report):
    eyes, _, (sv, sf, _), beaks = A.build_parts(body)
    BODY = (0.80, 0.88, 0.92)
    meshes_op = [(mem[0], mem[1], BODY, 0.45)] + \
        [(v, f, (0.30, 0.55, 0.75), 1) for v, f in arms] + \
        [(v, f, (0.95, 0.85, 0.7), 1) for v, f in suckers] + \
        [(v, f, (0.55, 0.7, 0.55), 1) for v, f in cirri] + \
        [(v, f, (0.55, 0.75, 0.85), 1) for v, f in fins] + \
        [(e[0], e[1], (0.35, 0.35, 0.4), 1) for e in eyes] + [(sv, sf, (0.1, 0.35, 0.85), 1)] + \
        [(v, f, (0.75, 0.5, 0.15), 1) for _, v, f in beaks]
    skin_op = [(mem[0], mem[1], (0.85, 0.72, 0.68), 1)] + [(v, f, (0.85, 0.72, 0.68), 1) for v, f in fins] + \
        [(v, f, (0.8, 0.62, 0.58), 1) for v, f in arms]
    TW = 560
    W = 4 * TW + 100
    H = 130 + 3 * (TW + 120) + 40
    out = Image.new("RGB", (W, H), (248, 247, 244))
    dr = ImageDraw.Draw(out)
    dr.text((20, 16), "メンダコ 手順 A3: 膜・腕・吸盤・触毛・ひれ（2026-10-17）", font=A.font(40, True), fill=(20, 20, 20))
    dr.text((20, 70), "不透明の診断用の絵（正射影）。上 2 段: 膜は半透明、腕 = 青、吸盤 = 肌色、触毛 = 緑、ひれ = 水色、眼 = 灰、殻 = 濃い青、顎板 = 茶。"
            "下の段: 膜とひれと腕を不透明にした外の形", font=A.font(21), fill=(60, 60, 60))

    def put(img, x, y, t1, t2=""):
        img = img.resize((TW, TW))
        out.paste(img, (x, y))
        dr.text((x, y + TW + 6), t1, font=A.font(22, True), fill=(20, 20, 20))
        if t2:
            dr.text((x, y + TW + 38), t2, font=A.font(17), fill=(70, 70, 70))

    def ref(path, box):
        im = Image.open(path).convert("RGB").crop(box)
        s = min(TW / im.width, TW / im.height)
        im = im.resize((int(im.width * s), int(im.height * s)))
        o = Image.new("RGB", (TW, TW), (255, 255, 255))
        o.paste(im, ((TW - im.width) // 2, (TW - im.height) // 2))
        return o

    R = A.REF
    y = 130
    put(A.render(meshes_op, "top", size=TW, extent=0.7), 20, y, "上から（前が上）", "腕は口側にあるので膜ごしに見える")
    put(ref(os.path.join(R, "10-meyer1906-taf11-left.jpg"), (400, 300, 2200, 2150)), 40 + TW, y, "参考: Meyer 1906 図 1（成熟した雄、背）", "PD")
    put(A.render(meshes_op, "oral", size=TW, extent=0.7), 60 + 2 * TW, y, "口側から（前が上）", "大きい吸盤は 5〜19 番目、ジグザグ")
    put(ref(os.path.join(R, "30-verhoeff2024-fig12.png"), (200, 260, 1300, 1480)), 80 + 3 * TW, y, "参考: 雄の口側（Sasaki 1929、Verhoeff 2024 図 12 A）", "CC BY 4.0")
    y += TW + 120
    put(A.render(meshes_op, "front", size=TW, extent=0.6), 20, y, "前から", "ひれの外の端 ±0.345、上下 0.10〜0.30")
    put(A.render(meshes_op, "side", size=TW, extent=0.6), 40 + TW, y, "体の左から（前が左）", "頭の頂は前の端から 0.69（決定 C）")
    put(A.render(meshes_op, "oblique", size=TW, extent=0.62), 60 + 2 * TW, y, "斜め前から", "")
    put(ref(os.path.join(R, "04-sunshine1-live.jpg"), (300, 700, 3900, 2900)), 80 + 3 * TW, y, "参考: Sunshine1（生体、斜め）", "Totti, CC BY-SA 4.0")
    y += TW + 120
    put(A.render(skin_op, "front", size=TW, extent=0.6), 20, y, "外の形: 前から", "")
    put(ref(os.path.join(R, "05-sunshine2-live.jpg"), (600, 800, 3300, 2350)), 40 + TW, y, "参考: Sunshine2（生体の正面）", "Totti, CC BY-SA 4.0")
    put(A.render(skin_op, "oblique", size=TW, extent=0.62), 60 + 2 * TW, y, "外の形: 斜め前から", "")
    put(A.render(skin_op, "top", size=TW, extent=0.7), 80 + 3 * TW, y, "外の形: 上から", "")
    out.save(os.path.join(A.OUT, "a3_parts.jpg"), quality=86)
    print(os.path.join(A.OUT, "a3_parts.jpg"), out.size)


if __name__ == "__main__":
    main()

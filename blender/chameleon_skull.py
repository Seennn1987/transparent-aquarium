"""
エボシカメレオン頭骨（手順 1 の作り直し 第 2 版、2026-10-12）

方針: 骨を細い管で組まない。実物の輪郭どおりの「穴のあいた板」と、断面を変えながらつなぐ立体（loft）を作り、
重ねたまま Voxel Remesh で 1 つの殻に融合してならす。表面のざらつきは後回し（RUGOSITY = 0）。

頭の局所座標（generate_chameleon_contour.Head と同じ）:
  a = 方形骨の後縁 0 → 吻端 1（頭骨長 L = 1）、b = 顎の線から背側へ、y = 左右。
  画素 (x, y) は [06] の原寸で a = (x - 3975) / 601、b = (2160 - y) / 601。

形の出どころ:
  [06]  外形・かぶと・眼窩・背側の稜・下顎の下縁（実物の C. calyptratus 標本の側面）
  [p6]  ユーザー保存の頭骨の側面（透かし入り、リポジトリ外）: 下側頭窓・方形骨・下顎の深さ
  [p4][u2] 斜め前: 眼窩はすり鉢状のくぼみで輪は無い、眉が張り出す、眼窩の前に細長い孔が 3〜4 本並ぶ、吻は丸い楔
  [p1]  正面: 眉の高さが最も広い逆三角形、顎へ細くなる。かぶとは正中の薄い刃
  幅の値（眉の高さで半幅 約 0.24 L）は p1 の目測で、測定ではない。

第 2 版での変更（プロデューサーの指摘 4 点ほか）:
  1 正面の幅を逆三角形に（眉で最大、顎で細い）
  2 眼窩の輪をやめ、縁へ向かって面を沈めてすり鉢状に。眉はひさし
  3 方形骨と下顎を、断面の形を変えながらつなぐ立体に（下顎は涙形の断面、方形骨は前後に広い板）
  4 口の中の 2 枚の板を消し、口蓋は細い棒（口蓋骨・翼状骨・外翼状骨）と吻の裏の小さな板に
  5 眼窩前の孔を細長い 3 本に、鼻孔を吻の先へ  6 かぶとを正中の刃＋後ろの 2 本の棒に  7 歯を顎の縁の内側へ
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector, noise

RUGOSITY = 0.0   # 表面のざらつき（後回し）。1.0 で以前の強さ


def px2ab(x, y):
    return ((x - 3975.0) / 601.0, (2160.0 - y) / 601.0)


def interp(table, x):
    return float(np.interp(x, [p[0] for p in table], [p[1] for p in table]))


def smoothstep(e0, e1, x):
    t = min(1.0, max(0.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def ellipse(c, ra, rb, n=40, rot=0.0):
    cr, sr = math.cos(rot), math.sin(rot)
    out = []
    for k in range(n):
        t = 2 * math.pi * k / n
        u, v = ra * math.cos(t), rb * math.sin(t)
        out.append((c[0] + u * cr - v * sr, c[1] + u * sr + v * cr))
    return out


def inside(poly, P):
    """点の配列 P (N,2) が多角形 poly の内側か（偶奇則）。"""
    x, y = P[:, 0], P[:, 1]
    res = np.zeros(len(P), dtype=bool)
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        cond = ((y1 > y) != (y2 > y))
        with np.errstate(divide="ignore", invalid="ignore"):
            xin = (x2 - x1) * (y - y1) / (y2 - y1 + 1e-12) + x1
        res ^= cond & (x < xin)
    return res


def slab(bm, outline, holes, to3d, thick_vec, res=0.008):
    """(u, v) 平面の領域（outline の内側、holes の外側）を格子で埋め、厚みのある閉じた板にする。"""
    us = [p[0] for p in outline]
    vs = [p[1] for p in outline]
    u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
    nu, nv = int((u1 - u0) / res) + 2, int((v1 - v0) / res) + 2
    cu = u0 + (np.arange(nu) + 0.5) * res
    cv = v0 + (np.arange(nv) + 0.5) * res
    G = np.stack(np.meshgrid(cu, cv, indexing="ij"), -1).reshape(-1, 2)
    m = inside(outline, G)
    for h in holes:
        m &= ~inside(h, G)
    m = m.reshape(nu, nv)
    verts = {}

    def V(i, j, layer):
        key = (i, j, layer)
        if key not in verts:
            u, v = u0 + i * res, v0 + j * res
            p = to3d(u, v)
            if layer:
                p = p + thick_vec(u, v)
            verts[key] = bm.verts.new(p)
        return verts[key]

    for i in range(nu):
        for j in range(nv):
            if not m[i, j]:
                continue
            a, b, c, d = (i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)
            bm.faces.new([V(*a, 0), V(*b, 0), V(*c, 0), V(*d, 0)])
            bm.faces.new([V(*d, 1), V(*c, 1), V(*b, 1), V(*a, 1)])
            for (p, q), (di, dj) in (((a, b), (0, -1)), ((b, c), (1, 0)), ((c, d), (0, 1)), ((d, a), (-1, 0))):
                ni, nj = i + di, j + dj
                if not (0 <= ni < nu and 0 <= nj < nv and m[ni, nj]):
                    bm.faces.new([V(*p, 0), V(*p, 1), V(*q, 1), V(*q, 0)])


def loft(bm, centers, ups, section, n=16):
    """centers の点を通る立体。各点で断面 section(i, θ) → (up 方向, 横方向) のずれを返す。両端は閉じる。"""
    rings = []
    m = len(centers)
    for i, c in enumerate(centers):
        T = (centers[min(i + 1, m - 1)] - centers[max(i - 1, 0)]).normalized()
        U = ups[i] - T * ups[i].dot(T)
        U.normalize()
        W = T.cross(U)
        ring = []
        for k in range(n):
            th = 2 * math.pi * k / n
            du, dw = section(i, th)
            ring.append(bm.verts.new(c + U * du + W * dw))
        rings.append(ring)
    for r0, r1 in zip(rings, rings[1:]):
        for k in range(n):
            bm.faces.new((r0[k], r0[(k + 1) % n], r1[(k + 1) % n], r1[k]))
    for ring, rev in ((rings[0], True), (rings[-1], False)):
        c = sum((v.co for v in ring), Vector()) / len(ring)
        cv = bm.verts.new(c)
        for k in range(n):
            a, b = ring[k], ring[(k + 1) % n]
            bm.faces.new((cv, b, a) if rev else (cv, a, b))


# ---------------------------------------------------------------- 形の表（a, b）
DORSAL_RIDGE = [px2ab(x, y) for x, y in ((4600, 2150), (4596, 2080), (4575, 2000), (4545, 1920), (4505, 1850), (4450, 1800))]
# 有鱗類は下側頭弓が無いので、眼窩の後ろの下側頭窓は下が開いている。側面の板は後眼窩骨の柱と上側頭弓の帯だけを後ろへ
LATERAL_OUTLINE = ([(0.405, 0.0), (0.97, 0.0), (1.005, 0.02), (1.02, 0.06)] + DORSAL_RIDGE[2:] +
                   [(0.70, 0.635), (0.55, 0.645), (0.42, 0.635), (0.30, 0.62), (0.18, 0.60), (0.10, 0.578),
                    (0.05, 0.55), (0.04, 0.50), (0.12, 0.465), (0.28, 0.46), (0.345, 0.43), (0.375, 0.34),
                    (0.385, 0.20), (0.39, 0.08)])
ORBIT_C = (0.632, 0.30)
ORBIT_R = (0.20, 0.19)
ORBIT_ROT = 0.25
NOSTRIL = ellipse((0.975, 0.085), 0.026, 0.02, 20)                     # 吻の先
# 眼窩の前の縁に沿って並ぶ細長い孔（[p4][u2]）
SLITS = []
for _k, _ang in enumerate((-0.35, 0.05, 0.45)):
    _c = (ORBIT_C[0] + ORBIT_R[0] * 1.55 * math.cos(_ang), ORBIT_C[1] + ORBIT_R[1] * 1.55 * math.sin(_ang))
    SLITS.append(ellipse(_c, 0.012, 0.042 - 0.006 * _k, 16, rot=_ang))

# 左右の半幅（a に沿って）。正面から見ると眉の高さで最も広い逆三角形（[p1]）
HALF_WIDTH = [(0.0, 0.18), (0.15, 0.205), (0.35, 0.235), (0.55, 0.255), (0.70, 0.24), (0.82, 0.19), (0.92, 0.125), (0.98, 0.075), (1.03, 0.035)]
# 逆三角形はゆるやか: 顎の高さでも眉の 8 割の幅がある（[u2] 下顎は太く丸い。第 2 版で絞りすぎて正面が薄くなった）
HEIGHT_PINCH = [(-0.2, 0.74), (0.0, 0.80), (0.15, 0.87), (0.30, 0.94), (0.45, 1.0), (0.55, 1.0), (0.62, 0.93), (0.66, 0.86)]
HEIGHT_PINCH_SNOUT = [(-0.2, 0.78), (0.0, 0.86), (0.15, 0.95), (0.30, 0.93), (0.45, 0.78), (0.60, 0.58)]
PLATE = 0.042      # 側面の板の厚み（第 2 版 0.026 は正面から紙のように薄く見えた）


def orbit_polar(a, b):
    cr, sr = math.cos(-ORBIT_ROT), math.sin(-ORBIT_ROT)
    du, dv = a - ORBIT_C[0], b - ORBIT_C[1]
    u, v = du * cr - dv * sr, du * sr + dv * cr
    u /= ORBIT_R[0]
    v /= ORBIT_R[1]
    return math.hypot(u, v), math.atan2(v, u)


def lat_skull(a, b):
    f = smoothstep(0.70, 0.88, a)
    pinch = (1 - f) * interp(HEIGHT_PINCH, b) + f * interp(HEIGHT_PINCH_SNOUT, b)
    y = interp(HALF_WIDTH, a) * pinch
    r, th = orbit_polar(a, b)
    # 眼窩: 縁は顔の面からなだらかに盛り上がり（輪を載せない）、縁の内側が穴（くぼみ）になる。
    # 正面から見ると眼窩の縁が最も外へ張り出す（[p1]）。上の縁は眉のひさしとしてさらに外へ
    y += 0.05 * math.exp(-((r - 1.05) / 0.4) ** 2)
    # 眼窩は真横でなく前寄りを向く（[p1] 正面から両目の穴が見える）: 後ろの縁ほど外、前の縁ほど内
    y += 0.35 * (ORBIT_C[0] - a) * math.exp(-((r - 1.0) / 0.9) ** 2)
    y += 0.035 * math.exp(-((r - 1.25) / 0.25) ** 2) * max(0.0, math.sin(th)) ** 1.5
    # 頬骨の帯（眼窩の下）は丸くわずかに外へ
    if a > 0.38:
        y += 0.015 * math.exp(-((b - 0.05) / 0.045) ** 2)
    return y


TOP_EDGE = sorted(DORSAL_RIDGE[2:] + [(0.70, 0.635), (0.55, 0.645), (0.42, 0.635), (0.30, 0.62), (0.18, 0.60),
                                      (0.10, 0.578), (0.05, 0.55)], key=lambda p: p[0])


def top_b(a):
    """背側の輪郭の高さ（屋根の高さ）。側面の板の下側の縁（上側頭弓の下縁など）は混ぜない。"""
    return interp(TOP_EDGE, a)


CASQUE_OUTER = [px2ab(x, y) for x, y in (
    (4030, 1325), (4110, 1345), (4200, 1405), (4280, 1505), (4345, 1605), (4400, 1700), (4450, 1800),
    (4400, 1815), (4280, 1835), (4150, 1820), (4075, 1810), (4048, 1760), (4020, 1665), (3998, 1545),
    (3988, 1430), (3992, 1362))]
CASQUE_INNER = [px2ab(x, y) for x, y in (
    (4040, 1352), (4085, 1385), (4140, 1450), (4200, 1540), (4245, 1620), (4272, 1690), (4255, 1735),
    (4195, 1745), (4130, 1720), (4080, 1660), (4045, 1580), (4022, 1490), (4015, 1410))]
def lat_casque(a, b):
    """前上の帯（頭頂稜）は正中で薄い刃。後ろ下（鱗状骨の 2 本）ほど左右へ開く。"""
    f_low = min(1.0, max(0.0, (1.40 - b) / 0.85))
    f_back = min(1.0, max(0.0, 1.0 - (a - 0.05) / 0.35))
    return 0.006 + 0.15 * (f_low ** 1.3) * f_back


# （第 2 版の刃と棒の分け方。第 3 版では使わない）
CREST = CASQUE_OUTER[:10] + list(reversed(CASQUE_INNER[:8]))
SQUAMOSAL_PATH = [CASQUE_OUTER[0], CASQUE_OUTER[15], CASQUE_OUTER[14], CASQUE_OUTER[13], CASQUE_OUTER[12],
                  CASQUE_OUTER[11], (0.06, 0.62), (0.045, 0.54)]

# 下顎: 上縁（口を閉じて上顎に合う）と下縁、厚み、左右の位置
# 後ろ寄りは上縁が少し高い（上角骨・鉤状骨の高まり、[p6]）。独立した板は立てない
MAND_TOP = [(-0.05, -0.035), (0.02, -0.01), (0.10, 0.012), (0.20, 0.02), (0.30, 0.0), (0.40, -0.016), (0.75, -0.016), (1.03, -0.012)]
MAND_BOT = [(-0.05, -0.08), (0.05, -0.115), (0.20, -0.132), (0.45, -0.135), (0.70, -0.125), (0.88, -0.10), (0.98, -0.068), (1.035, -0.035)]
MAND_THICK = [(-0.05, 0.05), (0.10, 0.07), (0.40, 0.065), (0.80, 0.055), (1.03, 0.04)]
# 下顎は上顎の縁の内側に収まる（正面から見て顎が外へはみ出さない）
MANDIBLE_HALF = [(-0.05, 0.155), (0.1, 0.16), (0.3, 0.165), (0.55, 0.165), (0.8, 0.13), (0.95, 0.075), (1.04, 0.02)]


# ---------------------------------------------------------------- 組み立て
def build_skull_mesh(H, Builder, def_bone, spine, bone_mat, coll, voxel=0.0055, target_faces=70000):
    sk = Builder()
    sk.set_group("Head")
    bm = sk.bm
    ab = H.ab
    LY = Vector((0, 1, 0))

    for side in (-1, 1):
        # 1. 側面の板（上顎・頬骨・前前頭骨・後眼窩骨・上側頭弓の外側の面を 1 枚に）。眼窩のまわりはすり鉢
        holes = [ellipse(ORBIT_C, ORBIT_R[0], ORBIT_R[1], 56, ORBIT_ROT), NOSTRIL] + SLITS
        slab(bm, LATERAL_OUTLINE, holes,
             lambda u, v, s=side: ab(u, v, s * lat_skull(u, v)),
             lambda u, v, s=side: LY * (-s * PLATE), res=0.006)
        # 板の縁を丸く太く（穴と外周に沿って、板の厚みの真ん中に丸棒を通す）
        def edge(pts, r, s=side):
            pp = []
            for (u0, v0), (u1, v1) in zip(pts, pts[1:]):
                for j in range(3):
                    f = j / 3
                    u, v = u0 + (u1 - u0) * f, v0 + (v1 - v0) * f
                    pp.append(ab(u, v, s * (lat_skull(u, v) - PLATE * 0.5)))
            sk.tube(pp, r, sides=10, cap=False)
        orb = ellipse(ORBIT_C, ORBIT_R[0], ORBIT_R[1], 56, ORBIT_ROT)
        edge(orb + orb[:1], PLATE * 0.75)
        edge([(0.40, 0.0), (0.97, 0.0), (1.005, 0.02), (1.02, 0.06)] + DORSAL_RIDGE[2:], PLATE * 0.7)
        edge([(0.04, 0.50), (0.12, 0.465), (0.28, 0.46), (0.345, 0.43), (0.375, 0.34), (0.385, 0.20), (0.39, 0.08), (0.40, 0.0)], PLATE * 0.7)
        # 2. 方形骨: 前後に幅のある平たい骨。上は鱗状骨、下端は下顎と関節するこぶ
        qa = [(0.045, 0.53), (0.045, 0.40), (0.06, 0.26), (0.08, 0.12), (0.10, 0.01)]   # [p6] 下ほど前へ傾く
        qc = [ab(u, v, side * (0.14 + 0.025 * k / 4)) for k, (u, v) in enumerate(qa)]
        depth = [0.06, 0.09, 0.105, 0.095, 0.07]
        loft(bm, qc, [H.A] * len(qc),
             lambda i, th, d=depth: (d[i] * 0.5 * math.cos(th) * (1.0 if math.cos(th) < 0 else 0.7), 0.016 * math.sin(th)), 14)
        sk.ellipsoid(ab(0.10, -0.012, side * 0.165), H.A * 0.045, Vector((0, 0.04, 0)), H.B * 0.032, 10)
        # 3. 下顎: 断面は涙形（下が厚く丸い）。前で浅く、後ろで深い
        us = [1.03 - (1.08) * k / 36 for k in range(37)]
        cs, hs, ts = [], [], []
        for u in us:
            top, bot, t = interp(MAND_TOP, u), interp(MAND_BOT, u), interp(MAND_THICK, u)
            cs.append(ab(u, 0.5 * (top + bot), side * (interp(MANDIBLE_HALF, u) - t * 0.5)))
            hs.append(top - bot)
            ts.append(t)

        def msec(i, th, hs=hs, ts=ts):
            up = 0.5 * hs[i] * math.sin(th)
            fat = 0.6 + 0.4 * (1 - math.sin(th)) * 0.5      # 下ほど厚い
            return up, 0.5 * ts[i] * math.cos(th) * fat
        loft(bm, cs, [H.B] * len(cs), msec, 16)
        # 4. 口蓋の棒: 口蓋骨（吻の裏 → 後ろ）、翼状骨（→ 方形骨の下端）、外翼状骨（上顎の後端 → 翼状骨）
        sk.tube([ab(0.82, 0.035, side * 0.05), ab(0.62, 0.05, side * 0.075), ab(0.46, 0.05, side * 0.09)],
                [0.018, 0.02, 0.02], sides=8, up=LY, flat=0.6)
        sk.tube([ab(0.46, 0.05, side * 0.09), ab(0.30, 0.035, side * 0.11), ab(0.17, 0.015, side * 0.13), ab(0.08, 0.0, side * 0.145)],
                [0.02, 0.018, 0.017, 0.02], sides=8, up=H.B, flat=0.55)
        sk.tube([ab(0.43, 0.02, side * (lat_skull(0.43, 0.02) - 0.015)), ab(0.42, 0.045, side * 0.10)], 0.018, sides=8)
        # 5. かぶと（第 1 版の作りに戻す: 窓を囲む輪の板。前上は正中の刃、後ろ下ほど左右の鱗状骨へ開く。[p6] の輪に近い）
        slab(bm, CASQUE_OUTER, [CASQUE_INNER],
             lambda u, v, s=side: ab(u, v, s * lat_casque(u, v)),
             lambda u, v, s=side: LY * (-s * 0.022), res=0.006)
        back = CASQUE_OUTER[10:] + CASQUE_OUTER[:1]
        sk.tube([ab(u, v, side * (lat_casque(u, v) + 0.004)) for u, v in reversed(back)],
                [0.02] * len(back), sides=10)
        # 鱗状骨の下端から方形骨の上端へ
        sk.tube([ab(*CASQUE_OUTER[10], side * (lat_casque(*CASQUE_OUTER[10]) + 0.004)), ab(0.06, 0.60, side * 0.13), ab(0.045, 0.53, side * 0.14)],
                0.024, sides=10)

    # かぶとの前縁は丸く太い稜
    front = CASQUE_OUTER[:7]
    sk.tube([ab(u - 0.006, v - 0.006, 0.0) for u, v in front], [0.022 + 0.012 * k / 6 for k in range(7)], sides=10)

    # 7. 屋根: 眉のあいだの広い三角の額（前頭骨）と、吻の上の鼻骨
    def roof3d(u, t):
        bt = top_b(u)
        w = lat_skull(u, bt - 0.012) * 0.96
        return ab(u, bt - 0.014 + 0.03 * (1 - t * t), t * w)
    slab(bm, [(0.10, -1.0), (1.015, -1.0), (1.015, 1.0), (0.10, 1.0)], [], roof3d,
         lambda u, t: -H.B * 0.045, res=0.01)
    # 吻の先は丸い（前上顎骨）。左右の板と屋根のあいだの溝を埋める
    sk.ellipsoid(ab(0.975, 0.07, 0.0), H.A * 0.05, Vector((0, 0.05, 0)), H.B * 0.07, 14)
    # 吻の裏の小さな口蓋（前上顎骨・鋤骨）
    slab(bm, [(0.80, -1.0), (1.0, -1.0), (1.0, 1.0), (0.80, 1.0)], [],
         lambda u, t: ab(u, 0.03, t * (lat_skull(u, 0.02) - 0.015)),
         lambda u, t: H.B * 0.02, res=0.01)
    # 8. 脳函（平たく小さく、口蓋の奥）と後頭顆
    sk.ellipsoid(ab(0.20, 0.47, 0.0), H.A * 0.15, Vector((0, 0.06, 0)), H.B * 0.065, 16)
    sk.ellipsoid(ab(0.04, 0.53, 0.0), H.A * 0.035, Vector((0, 0.04, 0)), H.B * 0.035, 10)
    # 9. 歯: 上下の縁の内側に、細かい三角が交互に並ぶ
    for side in (-1, 1):
        for k in range(26):
            u = 0.22 + 0.76 * k / 25
            w = lat_skull(u, 0.0) - PLATE * 0.6
            sk.cone(ab(u, 0.006, side * w), ab(u, -0.022, side * w), 0.011, 4)
            u2 = u + 0.015
            wm = interp(MANDIBLE_HALF, u2) - interp(MAND_THICK, u2) * 0.5
            sk.cone(ab(u2, interp(MAND_TOP, u2) - 0.004, side * wm), ab(u2, interp(MAND_TOP, u2) + 0.02, side * wm), 0.010, 4)
    # 10. 背側の稜の結節（[06] の輪郭でもぎざぎざに見える範囲だけ）
    ridge = []
    for (u0, v0), (u1, v1) in zip(DORSAL_RIDGE, DORSAL_RIDGE[1:]):
        for k in range(6):
            f = k / 6
            ridge.append((u0 + (u1 - u0) * f, v0 + (v1 - v0) * f))
    for side in (-1, 1):
        for u, v in ridge[3:]:
            sk.ellipsoid(ab(u - 0.008, v - 0.004, side * (lat_skull(u, v - 0.01) * 0.85)), H.A * 0.012, Vector((0, 0.012, 0)), H.B * 0.012, 6)

    ob = sk.emit("Skull", bone_mat, coll)
    fuse(ob, voxel, target_faces, H)
    return ob


def fuse(ob, voxel, target_faces, H):
    """板と立体を 1 つの殻に融合 → ならす → （必要なら）ざらつき → 間引き。結果を実メッシュにする。"""
    m = ob.modifiers.new("Fuse", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    m.adaptivity = 0.0
    m.use_smooth_shade = True
    s = ob.modifiers.new("Soften", "SMOOTH")
    s.factor = 0.6
    s.iterations = 8
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)
    if RUGOSITY > 0:
        bmx = bmesh.new()
        bmx.from_mesh(me)
        bmx.normal_update()
        for v in bmx.verts:
            b = (v.co - H.origin).dot(H.B)
            w = min(1.0, max(0.0, (b - 0.15) / 0.4))
            n1 = noise.noise(v.co * 55.0)
            n2 = noise.noise(v.co * 130.0 + Vector((3.1, 1.7, 0.4)))
            v.co += v.normal * RUGOSITY * ((0.0045 * n1 + 0.0025 * n2) * (0.1 + 0.9 * w))
        bmx.to_mesh(me)
        bmx.free()
    if len(me.polygons) > target_faces:
        d = ob.modifiers.new("Thin", "DECIMATE")
        d.ratio = target_faces / len(me.polygons)
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        ob.data = me2
        bpy.data.meshes.remove(me)
        me = me2
    for p in me.polygons:
        p.use_smooth = True
    ob.vertex_groups.clear()
    vg = ob.vertex_groups.new(name="Head")
    vg.add(list(range(len(me.vertices))), 1.0, "REPLACE")

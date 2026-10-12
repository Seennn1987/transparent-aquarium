"""
エボシカメレオン頭骨（手順 1 の作り直し、2026-10-12）

方針: 骨を細い管で組まない。実物の輪郭どおりの「穴のあいた板」と「帯」を作り、
重ねたまま Voxel Remesh で 1 つの殻に融合し、ならしてから表面のざらつきを付ける。

頭の局所座標（generate_chameleon_contour.Head と同じ）:
  a = 方形骨の後縁 0 → 吻端 1（頭骨長 L = 1）、b = 顎の線から背側へ、y = 左右。
  画素 (x, y) は [06] の原寸で a = (x - 3975) / 601、b = (2160 - y) / 601。

形の出どころ:
  [06]  外形・かぶと・眼窩・背側の稜・鼻孔の位置・下顎の下縁（実物の C. calyptratus 標本の側面）
  [p6]  ユーザーが保存した頭骨の側面写真（透かし入り、リポジトリ外）: 側頭窓・眼窩前の孔・方形骨の柱・下顎の高さ
  [p4][p1] 斜め前と正面の写真: 幅（眼窩で最も広く、吻と頭頂へ狭まる。かぶとは正中の薄い刃）
  幅の値（眼窩の高さで半幅 0.24 L）は p1 の目測で、測定ではない。
"""

import math

import bmesh
import bpy
import numpy as np
from mathutils import Vector, noise


def px2ab(x, y):
    return ((x - 3975.0) / 601.0, (2160.0 - y) / 601.0)


def interp(table, x):
    xs = [p[0] for p in table]
    ys = [p[1] for p in table]
    return float(np.interp(x, xs, ys))


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
    """(u, v) 平面の領域（outline の内側、holes の外側）を格子で埋め、厚みのある閉じた板にする。
    to3d(u, v) → 表の面の点、thick_vec(u, v) → 裏へ向かう厚みのベクトル。"""
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


# ---------------------------------------------------------------- 形の表（a, b）
# 頭骨の側面の外周 [06]: 顎の線 → 吻端 → 背側のぎざぎざの稜 → 眼窩の上の屋根 → 後ろの方形骨
DORSAL_RIDGE = [px2ab(x, y) for x, y in ((4600, 2150), (4596, 2080), (4575, 2000), (4545, 1920), (4505, 1850), (4450, 1800))]
# 有鱗類は下側頭弓が無いので、眼窩の後ろの下側頭窓は下が開いている（[p6] 眼窩の後ろから翼状骨が見える）。
# 側面の板は、眼窩の後ろの柱（後眼窩骨）と、その上の上側頭弓の帯だけを後ろへ伸ばす
LATERAL_OUTLINE = ([(0.405, 0.0), (0.98, 0.0), (1.02, 0.04)] + DORSAL_RIDGE[1:] +
                   [(0.70, 0.635), (0.55, 0.645), (0.42, 0.635), (0.30, 0.62), (0.18, 0.60), (0.10, 0.578),
                    (0.05, 0.55), (0.04, 0.50), (0.12, 0.465), (0.28, 0.46), (0.345, 0.43), (0.375, 0.34),
                    (0.385, 0.20), (0.39, 0.08)])
ORBIT_C = (0.632, 0.30)      # [06] 眼球の中心（0.29）より少し上。[p6] 眼窩の上縁は屋根に近い
ORBIT_R = (0.205, 0.19)      # 骨の開口。[p6] 開口の幅は頭骨長の約 0.3、縁を含めて 0.45（[06]）
ORBIT_ROT = 0.25             # 後ろ上がりの卵形（[p6]）
# 眼窩の後ろの下側頭窓 [p6]（眼窩との間に太い後眼窩骨の柱を残す）
TEMPORAL = [(0.13, 0.20), (0.30, 0.15), (0.37, 0.21), (0.375, 0.34), (0.32, 0.45), (0.19, 0.46), (0.115, 0.38), (0.105, 0.28)]
NOSTRIL = ellipse(px2ab(4528, 2095), 0.032, 0.022, 20)                 # [06] 吻の先の明るい点
PREORBITAL = ellipse((0.865, 0.30), 0.02, 0.034, 16, rot=-0.5)        # [p6] 眼窩前の小孔

# 左右の半幅（a に沿って）と、高さによる絞り。眼窩の縁は外へ張り出す
HALF_WIDTH = [(0.0, 0.165), (0.15, 0.185), (0.35, 0.205), (0.55, 0.215), (0.70, 0.20), (0.82, 0.16), (0.92, 0.105), (0.98, 0.06), (1.03, 0.025)]
# 顎の高さでは細く、眼窩の高さで最も広く、屋根へ向かって絞る（[p1][p4]）
HEIGHT_PINCH = [(-0.2, 0.70), (0.0, 0.78), (0.15, 0.94), (0.30, 1.0), (0.45, 0.92), (0.58, 0.72), (0.66, 0.58)]


# 吻では左右の背側の稜が正中へ寄り、顔は上から下へ外へ開く斜面になる（[p4] 吻は楔形）
HEIGHT_PINCH_SNOUT = [(-0.2, 0.75), (0.0, 0.85), (0.15, 0.92), (0.30, 0.80), (0.45, 0.55), (0.60, 0.38)]


def lat_skull(a, b):
    f = min(1.0, max(0.0, (a - 0.70) / 0.15))
    pinch = (1 - f) * interp(HEIGHT_PINCH, b) + f * interp(HEIGHT_PINCH_SNOUT, b)
    y = interp(HALF_WIDTH, a) * pinch
    # 眼窩の縁の張り出し（縁の帯で最大）
    da = (a - ORBIT_C[0]) / ORBIT_R[0]
    db = (b - ORBIT_C[1]) / ORBIT_R[1]
    r = math.hypot(da, db)
    y += 0.05 * math.exp(-((r - 1.12) / 0.3) ** 2)
    # 起伏: 頬骨の丸い帯（眼窩の下）、後眼窩骨の柱、背側の稜は外へ、眼窩と鼻孔のあいだの顔はわずかに凹む
    if a > 0.38:
        y += 0.02 * math.exp(-((b - 0.05) / 0.045) ** 2)
    y += 0.015 * math.exp(-((a - 0.40) / 0.035) ** 2) * (1.0 if b < 0.5 else 0.0)
    y -= 0.012 * math.exp(-((a - 0.86) / 0.06) ** 2 - ((b - 0.22) / 0.12) ** 2)
    return y


def top_b(a):
    """背側の輪郭の高さ（屋根の高さ）。"""
    pts = [p for p in LATERAL_OUTLINE if p[1] > 0.1]
    pts = sorted(pts, key=lambda p: p[0])
    return interp(pts, a)


# かぶと [06]（外周と、内側の窓）
CASQUE_OUTER = [px2ab(x, y) for x, y in (
    (4030, 1325), (4110, 1345), (4200, 1405), (4280, 1505), (4345, 1605), (4400, 1700), (4450, 1800),
    (4400, 1815), (4280, 1835), (4150, 1820), (4075, 1810), (4048, 1760), (4020, 1665), (3998, 1545),
    (3988, 1430), (3992, 1362))]   # 後ろの縁は細い棒（鱗状骨）だけにするため、内側の窓へ寄せた
CASQUE_INNER = [px2ab(x, y) for x, y in (
    (4040, 1352), (4085, 1385), (4140, 1450), (4200, 1540), (4245, 1620), (4272, 1690), (4255, 1735),
    (4195, 1745), (4130, 1720), (4080, 1660), (4045, 1580), (4022, 1490), (4015, 1410))]


def lat_casque(a, b):
    """前上の帯（頭頂稜）は正中で薄い刃。後ろ下（鱗状骨の 2 本）ほど左右へ開く。"""
    f_low = min(1.0, max(0.0, (1.40 - b) / 0.85))
    f_back = min(1.0, max(0.0, 1.0 - (a - 0.05) / 0.35))
    return 0.006 + 0.15 * (f_low ** 1.3) * f_back


# 下顎 [06][p6]: 口は閉じている。後ろほど深く、鉤状突起が上へ立つ
MANDIBLE_OUTLINE = [(1.03, -0.012), (0.75, -0.016), (0.40, -0.016), (0.27, 0.0), (0.20, 0.06), (0.15, 0.055),
                    (0.10, -0.005), (0.02, -0.012), (-0.045, -0.035), (-0.05, -0.08), (0.05, -0.115), (0.20, -0.132),
                    (0.45, -0.135), (0.70, -0.125), (0.88, -0.10), (0.98, -0.068), (1.035, -0.035)]
MANDIBLE_HALF = [(-0.05, 0.135), (0.1, 0.14), (0.3, 0.145), (0.55, 0.145), (0.8, 0.11), (0.95, 0.055), (1.04, 0.015)]


# ---------------------------------------------------------------- 組み立て
def build_skull_mesh(H, Builder, def_bone, spine, bone_mat, coll, voxel=0.0065, target_faces=70000):
    sk = Builder()
    sk.set_group("Head")
    bm = sk.bm
    ab = H.ab
    LY = Vector((0, 1, 0))

    for side in (-1, 1):
        # 1. 側面の板（上顎・頬骨・前前頭骨・後眼窩骨・鱗状骨の外側の面を一枚に）
        holes = [ellipse(ORBIT_C, ORBIT_R[0], ORBIT_R[1], 48, ORBIT_ROT), NOSTRIL, PREORBITAL]
        slab(bm, LATERAL_OUTLINE, holes,
             lambda u, v, s=side: ab(u, v, s * lat_skull(u, v)),
             lambda u, v, s=side: LY * (-s * 0.026))
        # 2. 眼窩の縁の帯（上と前で太く、後ろで細い）
        ring = []
        rads = []
        for k in range(49):
            t = 2 * math.pi * k / 48
            cr, sr = math.cos(ORBIT_ROT), math.sin(ORBIT_ROT)
            du, dv = ORBIT_R[0] * 1.06 * math.cos(t), ORBIT_R[1] * 1.06 * math.sin(t)
            u, v = ORBIT_C[0] + du * cr - dv * sr, ORBIT_C[1] + du * sr + dv * cr
            ring.append(ab(u, v, side * (lat_skull(u, v) + 0.008)))
            top = max(0.0, math.sin(t))
            front = max(0.0, math.cos(t))
            rads.append(0.03 + 0.02 * top + 0.012 * front)
        sk.tube(ring, rads, sides=10, cap=False)
        # 3. 方形骨の柱と、口蓋から下へ張り出す翼状骨
        sk.tube([ab(0.045, 0.53, side * 0.135), ab(0.05, 0.30, side * 0.15), ab(0.07, 0.04, side * 0.155), ab(0.075, -0.015, side * 0.15)],
                [0.03, 0.034, 0.042, 0.05], sides=10)
        slab(bm, [(0.12, 0.10), (0.42, 0.06), (0.40, -0.02), (0.26, -0.07), (0.14, -0.04)], [],
             lambda u, v, s=side: ab(u, v, s * (0.06 + 0.06 * (0.42 - u))),
             lambda u, v, s=side: LY * (-s * 0.02))
        # 4. 上顎の歯の土台（内側へ少し張り出す棚）
        slab(bm, [(0.40, -0.002), (1.0, -0.002), (1.0, 0.035), (0.40, 0.035)], [],
             lambda u, v, s=side: ab(u, v, s * lat_skull(u, 0.0)),
             lambda u, v, s=side: LY * (-s * 0.05))
        # 5. かぶと（頭頂稜の刃と、後ろの 2 本の鱗状骨）
        slab(bm, CASQUE_OUTER, [CASQUE_INNER],
             lambda u, v, s=side: ab(u, v, s * lat_casque(u, v)),
             lambda u, v, s=side: LY * (-s * 0.016), res=0.007)
        # 後ろの縁: 左右の鱗状骨は細い丸い棒（[p6] 2 本が頂で合わさる）
        back = CASQUE_OUTER[10:] + CASQUE_OUTER[:1]
        sk.tube([ab(u, v, side * (lat_casque(u, v) + 0.004)) for u, v in reversed(back)],
                [0.02] * len(back), sides=8)
        # 6. 下顎の板と、丸い下縁
        slab(bm, MANDIBLE_OUTLINE, [],
             lambda u, v, s=side: ab(u, v, s * interp(MANDIBLE_HALF, u)),
             lambda u, v, s=side: LY * (-s * 0.035))
        low = [p for p in MANDIBLE_OUTLINE if p[1] < -0.04]
        low = sorted(low, key=lambda p: p[0])
        sk.tube([ab(u, v + 0.018, side * (interp(MANDIBLE_HALF, u) - 0.022)) for u, v in low],
                [0.026] * len(low), sides=10)

    # 7. 屋根（眼窩の間の前頭骨〜頭頂骨、吻の上の鼻骨）: 背側の輪郭に沿って左右の板をつなぐ
    def roof3d(u, t):
        bt = top_b(u)
        w = lat_skull(u, bt - 0.01) * 0.94
        return ab(u, bt - 0.014 + 0.02 * (1 - t * t), t * w)
    slab(bm, [(0.10, -1.0), (1.015, -1.0), (1.015, 1.0), (0.10, 1.0)], [], roof3d,
         lambda u, t: -H.B * 0.03, res=0.01)
    # かぶとの前縁: 頭頂稜は丸く太い稜（[p4][p6]）
    front = CASQUE_OUTER[:7]
    sk.tube([ab(u - 0.006, v - 0.006, 0.0) for u, v in front], [0.024 + 0.012 * k / 6 for k in range(7)], sides=10)
    # 8. 脳函と後頭顆（外からはほとんど見えない）
    sk.ellipsoid(ab(0.18, 0.45, 0.0), H.A * 0.17, Vector((0, 0.11, 0)), H.B * 0.11, 16)
    sk.ellipsoid(ab(0.04, 0.53, 0.0), H.A * 0.035, Vector((0, 0.04, 0)), H.B * 0.035, 10)
    # 9. 歯: 上下の縁に細かい三角が交互に並ぶ（口を閉じたので、のこぎりの線になる）
    for side in (-1, 1):
        for k in range(26):
            u = 0.20 + 0.78 * k / 25
            w = interp(HALF_WIDTH, u) - 0.012
            sk.cone(ab(u, 0.004, side * w), ab(u, -0.024, side * w), 0.012, 4)
            u2 = u + 0.015
            wm = interp(MANDIBLE_HALF, u2) - 0.006
            sk.cone(ab(u2, -0.02, side * wm), ab(u2, 0.006, side * wm), 0.011, 4)
    # 10. 結節: 背側の稜、眼窩の上縁、かぶとの前縁に並ぶ小さな突起
    ridge = []
    for (u0, v0), (u1, v1) in zip(DORSAL_RIDGE, DORSAL_RIDGE[1:]):
        for k in range(6):
            f = k / 6
            ridge.append((u0 + (u1 - u0) * f, v0 + (v1 - v0) * f))
    for side in (-1, 1):
        for u, v in ridge[2:]:
            sk.ellipsoid(ab(u - 0.01, v, side * (lat_skull(u, v) * 0.85)), H.A * 0.016, Vector((0, 0.016, 0)), H.B * 0.016, 6)
        for k in range(10):
            t = 0.35 + 0.65 * k / 9          # 眼窩の上縁（前上から真上）
            ang = math.pi * (0.25 + 0.5 * t)
            u = ORBIT_C[0] + ORBIT_R[0] * 1.25 * math.cos(ang)
            v = ORBIT_C[1] + ORBIT_R[1] * 1.25 * math.sin(ang)
            sk.ellipsoid(ab(u, v, side * (lat_skull(u, v) + 0.005)), H.A * 0.014, Vector((0, 0.012, 0)), H.B * 0.014, 6)
    for k in range(18):
        f = k / 17
        i = f * (6 - 1)
        i0 = int(i)
        i1 = min(6, i0 + 1)
        (u0, v0), (u1, v1) = CASQUE_OUTER[i0], CASQUE_OUTER[i1]
        g = i - i0
        u, v = u0 + (u1 - u0) * g, v0 + (v1 - v0) * g
        sk.ellipsoid(ab(u - 0.008, v - 0.008, 0.0), H.A * 0.013, Vector((0, 0.02, 0)), H.B * 0.013, 6)

    ob = sk.emit("Skull", bone_mat, coll)
    fuse(ob, voxel, target_faces, H)
    return ob


def fuse(ob, voxel, target_faces, H):
    """板と帯を 1 つの殻に融合 → ならす → 上面のざらつき → 間引き。結果を実メッシュにする。"""
    m = ob.modifiers.new("Fuse", "REMESH")
    m.mode = "VOXEL"
    m.voxel_size = voxel
    m.adaptivity = 0.0
    m.use_smooth_shade = True
    s = ob.modifiers.new("Soften", "SMOOTH")
    s.factor = 0.6
    s.iterations = 6
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    old = ob.data
    ob.data = me
    bpy.data.meshes.remove(old)
    # ざらつき: 背側ほど強い細かな凹凸（[p4] 頭の上の面全体が顆粒状）
    bmx = bmesh.new()
    bmx.from_mesh(me)
    bmx.normal_update()
    org = H.origin
    for v in bmx.verts:
        rel = v.co - org
        b = rel.dot(H.B)
        w = min(1.0, max(0.0, (b - 0.15) / 0.4))
        n1 = noise.noise(v.co * 55.0)
        n2 = noise.noise(v.co * 130.0 + Vector((3.1, 1.7, 0.4)))
        v.co += v.normal * ((0.0045 * n1 + 0.0025 * n2) * (0.1 + 0.9 * w))
    bmx.to_mesh(me)
    bmx.free()
    # 間引き（ウェブで扱える面数へ）
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
    if not me.materials:
        pass

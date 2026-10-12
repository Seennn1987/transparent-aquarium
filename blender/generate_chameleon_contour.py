"""
エボシカメレオン（Chamaeleo calyptratus）透明標本 手順 1「輪郭の静止画」用の骨格生成スクリプト

静止時の軸: 瓶の上 = Blender +Z（尾の渦が上、頭が下）。動物の正中面 = XZ 面、背は -X 側（瓶の壁）、腹と四肢は +X 側。
            動物の左右 = Blender Y（glTF では p.z）。カメラは -Y 側から動物の側面を見る。

使い方:
  - Blender の Scripting で開いて実行（シーンに CH_ コレクションを作り直すだけ。描画はしない）
  - 静止画まで出す: blender --background --factory-startup --python generate_chameleon_contour.py -- <出力.png> [<landmarks.json>]

手順 1 の範囲: 骨だけ（頭蓋・下顎・かぶと・脊椎・肋骨・肩帯・腰帯・四肢・手足）。
  軟骨（青）、眼、舌器、内臓、色の調整、瓶はまだ作らない。骨は無彩色で出す。

寸法の単位: 頭骨長 L（吻端〜方形骨の後縁）= 1。
数値の出どころ（2026-10-12、Claude が自分で計測。計画書 v1.0 の比率は再現できなかったので使わない）:
  [06] docs/references/chameleon/06-lightbox-calyptratus-2.jpg（実物の C. calyptratus 透明標本の側面、5184px）
  [07] 07-erpetologie-chamaeleon-skeleton.jpg（別種 C. chamaeleon の図版。06 で写らない骨長の比の確認だけに使う）
  [01] 01-user-jar-diaphonized.jpg（瓶の中の姿勢だけ。比率は使わない。幼体らしく頭が大きい）
  [D15] Diaz & Trainor 2015, BMC Evol Biol（PMC4574539）: 指骨式 手 2-3-4-4-3 / 足 2-3-4-4-3、
        手の束 (I,II,III)(IV,V)、足の束 (I,II)(III,IV,V)、足根の近位3要素は1つに癒合
  [DM]  Digimorph, Chamaeleo calyptratus（TNHC 62768）: 頸椎 5、肩甲骨は高く細い、体は強く側扁
"""

import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Vector, Matrix

PREFIX = "CH_"
PLATE_SKULL = True    # False で以前の管で組んだ頭骨（比較用）
try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"

# ---------------------------------------------------------------- 測った数（L = 頭骨長）
M = {
    # [06] 頭: 頭骨長 601px を 1 とする
    "head_height": 1.50,          # [06] 下顎の下縁〜かぶとの頂 900px
    "orbit_rim_radius": 0.225,    # [06] 眼窩の骨の縁の径 270px
    "casque_apex": (0.89, 1.42),  # [06] 吻端から後ろへ 0.89、顎の線から上へ 1.42
    # [06] 胴: 頸の付け根〜仙骨の弧長
    "neck_len": 0.45,             # [06] 頸椎 5 個ぶん（[DM] 頸椎 5）
    "trunk_len": 2.96,            # [06] 頸の後ろ〜仙骨
    "cervical": 5,                # [DM]
    "trunk_vertebrae": 16,        # [06] 神経棘を数えた概数（±2）
    "sacral": 2,                  # [06] 腸骨が付く位置の椎骨。2 個として置く（写真では確定できない）
    "tail_len": 5.0,              # [06] 尾の弧長 3007px（巻きをたどって測った）
    "caudal": 55,                 # [06] 神経棘の間隔からの概数
    "tail_turns": 1.6,            # [06] 巻きの合計 575°（TAIL_TURN）
    "body_depth": 1.10,           # [06] 胴の最も深い所の背腹 700px
    "body_half_width": 0.22,      # 推定: 強く側扁（[DM]）。06 は側面なので測れない
    # 四肢（[06] は短縮して写る骨があるので、[07] の 骨長/吻端〜仙骨 の比で確かめて決めた）
    "scapula": 0.47,              # [06] 280px、[07] 0.115 SVL と一致
    "humerus": 0.85,              # [06] ≧0.68（手前に傾いて短く写る）、[07] 0.22 SVL → 0.19 SVL を採る
    "forearm": 0.90,              # [06] 0.92、[07] 0.20 SVL
    "femur": 0.80,                # [06] 0.78、[07] 0.20 SVL
    "tibia": 0.77,                # [06] 0.73、[07] 0.19 SVL
    "ilium": 0.42,                # [06] 0.38〜0.45
    "manus": 0.42,                # [06] 手首〜指先 250px
    "pes": 0.40,                  # [06] 足首〜指先
}
PHALANGES_MANUS = [2, 3, 4, 4, 3]   # [D15]
PHALANGES_PES = [2, 3, 4, 4, 3]     # [D15]
BUNDLE_MANUS = ([0, 1, 2], [3, 4])  # [D15] (I,II,III)(IV,V)
BUNDLE_PES = ([0, 1], [2, 3, 4])    # [D15] (I,II)(III,IV,V)

# ---------------------------------------------------------------- 姿勢（[01] の瓶の中の姿勢）
# 背骨の進む向き（頭→尾）を XZ 面の角度（度、+X から反時計回り）で与える。s は後頭顆からの弧長。
POSES = {
    # 瓶の中（[01]）: 頭が下、背は壁、尾は壁沿いに上がって上で渦を巻く
    "jar": {"trunk": [(0.0, 150.0), (0.45, 145.0), (1.5, 126.0), (2.6, 106.0), (3.41, 95.0)], "head_flex": -25.0, "tail_lift": 0.0},
    # 照合用（[06] のライトボックスの姿勢を左右反転したもの）。描画を左右反転すると 06 に重なる
    # 背骨の画素列（神経棘の頂）から求めた向き
    "lightbox06": {"trunk": [(0.0, 38.7), (0.153, 45.0), (0.259, 45.0), (0.389, 35.5), (0.544, 36.9), (0.712, 29.1),
                             (0.891, 26.6), (1.089, 18.4), (1.288, 15.3), (1.488, 18.4), (1.704, 13.0), (1.914, 14.6),
                             (2.11, 12.3), (2.31, 11.8), (2.503, 5.2), (2.687, 5.2), (2.853, 3.2), (2.999, 3.4),
                             (3.132, 0.0), (3.41, 0.0)], "head_flex": -38.7, "tail_lift": 19.7},
}
# 尾の巻き（[06] の尾をたどった画素列から）: 尾の付け根からの弧長 s [L] と、付け根の向きからの回転 [度]。
# 負 = 腹側へ巻く。根元 1.7L はほぼまっすぐで、そこから先はほぼ一定の強さで巻き、先端 1L で強くなる。合計 1.6 回転
TAIL_TURN = [(0.0, 0.0), (0.421, -3.0), (0.766, -5.7), (1.105, -14.0), (1.439, -19.7), (1.731, -27.3), (1.957, -44.1),
             (2.148, -76.0), (2.363, -105.9), (2.615, -121.0), (2.856, -145.7), (3.08, -173.1), (3.317, -195.9),
             (3.55, -222.3), (3.76, -254.7), (3.962, -284.9), (4.148, -318.8), (4.308, -353.1), (4.457, -386.0),
             (4.598, -429.9), (4.729, -469.7), (4.849, -508.4), (4.953, -569.2), (5.0, -575.0)]
POSE = POSES[os.environ.get("CH_POSE", "jar")]
TRUNK_HEADING = POSE["trunk"]
HEAD_FLEX_DEG = POSE["head_flex"]   # 首の線に対する頭の向き。負で吻を背側へ起こす（頭は下を向く）

BONE_GRAY = (0.62, 0.60, 0.57, 1.0)   # 手順 1 は無彩色


# ================================================================ 幾何の小道具
def rot2(v, deg):
    a = math.radians(deg)
    return Vector((v.x * math.cos(a) - v.z * math.sin(a), 0.0, v.x * math.sin(a) + v.z * math.cos(a)))


def heading_vec(deg):
    a = math.radians(deg)
    return Vector((math.cos(a), 0.0, math.sin(a)))


def lerp_table(tab, s):
    if s <= tab[0][0]:
        return tab[0][1]
    for (s0, v0), (s1, v1) in zip(tab, tab[1:]):
        if s <= s1:
            t = (s - s0) / (s1 - s0)
            return v0 + (v1 - v0) * t
    return tab[-1][1]


class Spine:
    """後頭顆（s=0）から尾の先までの中心線。T=尾へ向かう接線、N=背側、Y=左右。"""

    def __init__(self, ds=0.005):
        self.ds = ds
        self.s_sacrum = M["neck_len"] + M["trunk_len"]
        self.s_end = self.s_sacrum + M["sacral"] * 0.12 + M["tail_len"]
        tail_len = self.s_end - self.s_sacrum
        h_sac = lerp_table(TRUNK_HEADING, self.s_sacrum) + POSE["tail_lift"]   # 尾の付け根の背側への起き上がり
        pts, heads = [], []
        p = Vector((0.0, 0.0, 0.0))
        h = TRUNK_HEADING[0][1]
        n = int(self.s_end / ds) + 1
        for i in range(n):
            s = i * ds
            if s <= self.s_sacrum:
                h = lerp_table(TRUNK_HEADING, s)
            else:
                t = (s - self.s_sacrum) / tail_len * M["tail_len"]
                h = h_sac + lerp_table(TAIL_TURN, t)  # 時計回り = 腹側へ巻く
            pts.append(p.copy())
            heads.append(h)
            p = p + heading_vec(h) * ds
        self.pts, self.heads = pts, heads

    def at(self, s):
        i = max(0, min(len(self.pts) - 1, int(round(s / self.ds))))
        T = heading_vec(self.heads[i])
        N = rot2(T, 90.0)
        return self.pts[i].copy(), T, N

    def local(self, s, t=0.0, n=0.0, y=0.0):
        """背骨上の点 s を起点に、T 方向 t、N 方向 n、左右 y だけずらした点。"""
        P, T, N = self.at(s)
        return P + T * t + N * n + Vector((0.0, y, 0.0))


# ================================================================ メッシュの小道具
# 骨組みの定義（rig_chameleon.py が読む）。名前 → (頭, 尾, 親)。頂点グループも同じ名前
BONES = {}


def def_bone(name, head, tail, parent=None):
    BONES[name] = (Vector(head), Vector(tail), parent)


class Builder:
    def __init__(self):
        self.bm = bmesh.new()
        self.marks = []

    def set_group(self, name):
        """ここから先に作る頂点を、骨 name の頂点グループに入れる（骨は剛体なので重み 1）。"""
        self.marks.append((len(self.bm.verts), name))

    def tube(self, pts, radii, sides=8, up=None, flat=1.0, cap=True):
        """pts を通る管。radii はスカラーか点ごとの値。flat < 1 で up に直交する向きへ潰す。"""
        if len(pts) < 2:
            return
        if not isinstance(radii, (list, tuple)):
            radii = [radii] * len(pts)
        rings = []
        prev_n = None
        for i, p in enumerate(pts):
            if i == 0:
                t = (pts[1] - pts[0])
            elif i == len(pts) - 1:
                t = (pts[-1] - pts[-2])
            else:
                t = (pts[i + 1] - pts[i - 1])
            if t.length < 1e-9:
                t = Vector((1, 0, 0))
            t.normalize()
            ref = up if up is not None else (prev_n if prev_n is not None else Vector((0, 1, 0)))
            n1 = ref - t * ref.dot(t)
            if n1.length < 1e-6:
                n1 = Vector((0, 0, 1)) - t * t.z
                if n1.length < 1e-6:
                    n1 = Vector((1, 0, 0))
            n1.normalize()
            n2 = t.cross(n1)
            prev_n = n1
            r = radii[i]
            ring = []
            for k in range(sides):
                a = 2 * math.pi * k / sides
                off = n1 * (math.cos(a) * r) + n2 * (math.sin(a) * r * flat)
                ring.append(self.bm.verts.new(p + off))
            rings.append(ring)
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(sides):
                self.bm.faces.new((r0[k], r0[(k + 1) % sides], r1[(k + 1) % sides], r1[k]))
        if cap:
            self.bm.faces.new(list(reversed(rings[0])))
            self.bm.faces.new(rings[-1])

    def ellipsoid(self, center, ax, ay, az, seg=10):
        """ax, ay, az は半径を長さに持つ3本のベクトル。"""
        mat = Matrix((
            (ax.x, ay.x, az.x, center.x),
            (ax.y, ay.y, az.y, center.y),
            (ax.z, ay.z, az.z, center.z),
            (0, 0, 0, 1)))
        bmesh.ops.create_uvsphere(self.bm, u_segments=seg, v_segments=max(4, seg // 2 + 1), radius=1.0, matrix=mat)

    def cone(self, base, tip, r, seg=6):
        d = tip - base
        L = d.length
        if L < 1e-9:
            return
        q = Vector((0, 0, 1)).rotation_difference(d.normalized())
        mat = Matrix.Translation(base + d * 0.5) @ q.to_matrix().to_4x4()
        bmesh.ops.create_cone(self.bm, cap_ends=True, segments=seg, radius1=r, radius2=0.0, depth=L, matrix=mat)

    def emit(self, name, mat, coll):
        me = bpy.data.meshes.new(PREFIX + name)
        self.bm.to_mesh(me)
        self.bm.free()
        me.materials.append(mat)
        for p in me.polygons:
            p.use_smooth = True
        ob = bpy.data.objects.new(PREFIX + name, me)
        coll.objects.link(ob)
        n = len(me.vertices)
        for k, (start, gname) in enumerate(self.marks):
            end = self.marks[k + 1][0] if k + 1 < len(self.marks) else n
            if end > start:
                vg = ob.vertex_groups.get(gname) or ob.vertex_groups.new(name=gname)
                vg.add(list(range(start, end)), 1.0, "REPLACE")
        return ob


def bezier_pts(ctrl, per=6):
    """制御点を Catmull-Rom で滑らかにつなぐ。"""
    out = []
    P = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(per):
            t = k / per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(ctrl[-1])
    return out


# ================================================================ 頭
class Head:
    """[06] の側面写真の画素を、そのまま頭の局所座標へ写す。a=吻へ向かう軸、b=背側、y=左右。
    画素 (x, y) → a = (x - 3975) / 601、b = (2160 - y) / 601。後頭顆は (0.0, 0.55)。"""

    X0, Y0, PX = 3975.0, 2160.0, 601.0
    CONDYLE = (0.0, 0.55)   # [06] 頸の神経棘の頂 b=0.67 から椎体の高さぶん下

    def __init__(self, spine):
        P, T, N = spine.at(0.0)
        A = -T
        A = rot2(A, HEAD_FLEX_DEG)            # 正で腹側、負で背側へ回る
        B = rot2(A, -90.0)                     # 背側
        self.A, self.B = A, B
        self.origin = P - A * self.CONDYLE[0] - B * self.CONDYLE[1]

    def px(self, x, y, lat=0.0):
        a = (x - self.X0) / self.PX
        b = (self.Y0 - y) / self.PX
        return self.ab(a, b, lat)

    def ab(self, a, b, lat=0.0):
        return self.origin + self.A * a + self.B * b + Vector((0.0, lat, 0.0))


def resample_loop(pts, n):
    """閉じた折れ線を弧長で n 点に打ち直す（始点は pts[0]）。"""
    P = list(pts) + [pts[0]]
    seg = [(P[i + 1] - P[i]).length for i in range(len(P) - 1)]
    total = sum(seg)
    out, acc, i = [], 0.0, 0
    for k in range(n):
        target = total * k / n
        while i < len(seg) - 1 and acc + seg[i] < target:
            acc += seg[i]
            i += 1
        t = (target - acc) / seg[i] if seg[i] > 0 else 0.0
        out.append(P[i].lerp(P[i + 1], t))
    return out


def band(b, outer, inner, thick, outward):
    """外周と内周（同じ点数）のあいだを埋めた、厚み thick の輪。outward は厚みを付ける向き（点ごと）。"""
    n = len(outer)
    lay = []
    for off in (0.0, 1.0):
        lo = [b.bm.verts.new(p + outward[k] * thick * off) for k, p in enumerate(outer)]
        li = [b.bm.verts.new(p + outward[k] * thick * off) for k, p in enumerate(inner)]
        lay.append((lo, li))
    (o0, i0), (o1, i1) = lay
    for k in range(n):
        k2 = (k + 1) % n
        b.bm.faces.new((o0[k], o0[k2], i0[k2], i0[k]))
        b.bm.faces.new((o1[k], i1[k], i1[k2], o1[k2]))
        b.bm.faces.new((o0[k], o1[k], o1[k2], o0[k2]))
        b.bm.faces.new((i0[k], i0[k2], i1[k2], i1[k]))


def smooth_loop(ctrl, per=6):
    pts = bezier_pts(list(ctrl) + [ctrl[0]], per)
    return pts[:-1]


# [06] 画素でたどった頭の輪郭（x, y）。頭の局所座標へは Head.px で写す
CASQUE_OUTER_PX = [(4030, 1322), (4110, 1338), (4200, 1395), (4290, 1490), (4370, 1600), (4440, 1710), (4490, 1800),
                   (4400, 1805), (4280, 1792), (4150, 1790), (4070, 1810), (4035, 1760), (4000, 1660), (3978, 1540),
                   (3968, 1430), (3978, 1360)]
CASQUE_INNER_PX = [(4035, 1345), (4080, 1380), (4130, 1450), (4185, 1540), (4235, 1630), (4262, 1705), (4240, 1755),
                   (4180, 1755), (4120, 1735), (4075, 1680), (4040, 1590), (4018, 1490), (4010, 1410), (4015, 1362)]
DORSAL_EDGE_PX = [(4490, 1800), (4525, 1860), (4555, 1940), (4575, 2030), (4582, 2110), (4575, 2160)]


def build_skull(spine, bone_mat, coll):
    H = Head(spine)
    sk = Builder()
    sk.set_group("Head")
    up_lat = Vector((0, 1, 0))
    c0 = spine.at(0.0)[0]
    def_bone("Head", c0, c0 + H.A * 0.6, "v00")
    if PLATE_SKULL:
        # 2026-10-12 作り直し: 板と帯を融合した頭骨（chameleon_skull.py）
        sk.bm.free()
        import runpy
        cs = runpy.run_path(os.path.join(HERE, "chameleon_skull.py"), run_name="chameleon_skull")
        cs["build_skull_mesh"](H, Builder, def_bone, spine, bone_mat, coll)
        return H

    def lat_casque(a, b):
        """かぶとの左右の開き: 前上の帯（頭頂稜）は正中に寄り、後ろ下（鱗状骨）ほど外へ開く。"""
        f_low = max(0.0, min(1.0, (1.45 - b) / 1.0))
        f_back = max(0.0, min(1.0, 1.0 - a / 0.55))
        return 0.012 + 0.11 * f_low * f_back + 0.03 * f_low

    n = 64
    outer_ab = [((x - H.X0) / H.PX, (H.Y0 - y) / H.PX) for x, y in CASQUE_OUTER_PX]
    inner_ab = [((x - H.X0) / H.PX, (H.Y0 - y) / H.PX) for x, y in CASQUE_INNER_PX]
    for side in (-1, 1):
        o = resample_loop(smooth_loop([H.ab(a, b, side * lat_casque(a, b)) for a, b in outer_ab]), n)
        i = resample_loop(smooth_loop([H.ab(a, b, side * lat_casque(a, b)) for a, b in inner_ab]), n)
        # 内外の始点（いちばん上）をそろえる
        top_o = max(range(n), key=lambda k: o[k].dot(H.B))
        top_i = max(range(n), key=lambda k: i[k].dot(H.B))
        o = o[top_o:] + o[:top_o]
        i = i[top_i:] + i[:top_i]
        band(sk, o, i, 0.022, [Vector((0, side, 0))] * n)

    # 眼窩の縁（左右）[06] 眼球の径 200px、縁の外径 270px
    oc_a, oc_b = (4350 - H.X0) / H.PX, (H.Y0 - 1990) / H.PX
    r = 0.19
    for side in (-1, 1):
        ring = [H.ab(oc_a + r * math.cos(2 * math.pi * k / 28), oc_b + r * math.sin(2 * math.pi * k / 28), side * 0.18)
                for k in range(29)]
        sk.tube(ring, 0.05, sides=8, cap=False)
        # 背側の縁（前前頭骨〜鼻骨のぎざぎざの稜）: 吻端からかぶとの前の帯へ
        dorsal = bezier_pts([H.px(x, y, side * (0.03 + 0.10 * (1 - abs(y - 1980) / 200) if 1780 < y < 2180 else side * 0.03))
                             for x, y in DORSAL_EDGE_PX[::-1]], 5)
        sk.tube(dorsal, 0.038, sides=8, up=up_lat, flat=0.6)
        # 眼窩の上縁からかぶとの帯の下へ（前頭骨・後眼窩骨）
        sk.tube(bezier_pts([H.ab(oc_a + 0.05, oc_b + r, side * 0.16), H.px(4330, 1790, side * 0.08), H.px(4200, 1790, side * 0.05)], 4),
                0.04, sides=8, up=up_lat, flat=0.6)
        # 後眼窩骨〜頬骨の柱: 眼窩の後ろを下りる
        sk.tube(bezier_pts([H.px(4120, 1800, side * 0.10), H.px(4180, 1950, side * 0.17), H.px(4230, 2100, side * 0.18)], 4),
                0.035, sides=8, up=up_lat, flat=0.6)
        # 頬骨弓（眼窩の下）: 眼窩の後下から吻へ
        sk.tube(bezier_pts([H.px(4040, 2120, side * 0.15), H.px(4230, 2110, side * 0.18), H.px(4400, 2120, side * 0.15),
                            H.px(4560, 2145, side * 0.03)], 5), 0.045, sides=8, up=up_lat, flat=0.55)
        # 上顎骨（歯の並ぶ縁）
        sk.tube(bezier_pts([H.px(4080, 2165, side * 0.13), H.px(4300, 2170, side * 0.12), H.px(4480, 2170, side * 0.07),
                            H.px(4572, 2165, side * 0.015)], 5), 0.03, sides=8, up=up_lat, flat=0.7)
        # 鱗状骨〜方形骨: かぶとの後ろの腕の下から顎関節へ（[06] x≒4000〜4030 の縦の帯）
        sk.tube(bezier_pts([H.px(4045, 1790, side * 0.12), H.px(4025, 1950, side * 0.15), H.px(4010, 2150, side * 0.15)], 4),
                0.03, sides=8, up=up_lat, flat=0.6)
        # 翼状骨（口蓋から方形骨へ）
        sk.tube([H.ab(0.62, 0.06, side * 0.05), H.ab(0.25, 0.10, side * 0.10), H.ab(0.06, 0.10, side * 0.14)], 0.02, sides=6)
    # 吻端の前上顎骨
    sk.ellipsoid(H.px(4575, 2140), H.A * 0.03, Vector((0, 0.035, 0)), H.B * 0.045, 8)
    # 眼窩の間の前頭骨の屋根（正中）
    sk.tube(bezier_pts([H.px(4520, 1880), H.px(4440, 1800), H.px(4300, 1790), H.px(4130, 1800)], 4), 0.035, sides=7, up=up_lat, flat=0.6)
    # 脳函と後頭部
    sk.ellipsoid(H.ab(0.17, 0.48, 0.0), H.A * 0.19, Vector((0, 0.10, 0)), H.B * 0.11, 12)
    sk.ellipsoid(H.ab(0.01, 0.55, 0.0), H.A * 0.04, Vector((0, 0.04, 0)), H.B * 0.035, 8)   # 後頭顆
    sk.emit("Skull", bone_mat, coll)

    # 歯（端生歯の小さな三角）と下顎。口は閉じている（[06]）
    teeth = Builder()
    md = Builder()
    teeth.set_group("Head")
    md.set_group("Head")
    for side in (-1, 1):
        for i in range(16):
            f = 0.15 + 0.80 * i / 15
            lat = side * (0.125 - 0.105 * f)
            base = H.ab(f, -0.005, lat)
            teeth.cone(base, base - H.B * (0.022 + 0.008 * math.sin(f * 3)), 0.011, 5)
        ctrl = [H.px(4570, 2190, side * 0.01), H.px(4450, 2205, side * 0.07), H.px(4250, 2210, side * 0.12),
                H.px(4080, 2205, side * 0.14), H.px(3975, 2185, side * 0.15)]
        md.tube(bezier_pts(ctrl, 6), [0.036] * 24 + [0.03], sides=8, up=H.B, flat=0.6)
        # 鉤状突起（下顎の後ろの立ち上がり）
        md.tube([H.px(4110, 2200, side * 0.14), H.px(4080, 2150, side * 0.14)], 0.03, sides=6)
    md.emit("Mandible", bone_mat, coll)
    teeth.emit("Teeth", bone_mat, coll)
    return H


# ================================================================ 脊柱と肋骨
def vertebra_stations(spine):
    st = []
    nc, nt, ns = M["cervical"], M["trunk_vertebrae"], M["sacral"]
    lc = M["neck_len"] / nc
    for i in range(nc):
        st.append(("cervical", i, lc * (i + 0.5), lc))
    lt = M["trunk_len"] / nt
    for i in range(nt):
        st.append(("trunk", i, M["neck_len"] + lt * (i + 0.5), lt))
    for i in range(ns):
        st.append(("sacral", i, spine.s_sacrum + 0.12 * (i + 0.5), 0.12))
    # 尾椎: 長さが等比で縮み、合計が尾の長さになる
    n = M["caudal"]
    first = 0.16
    lo, hi = 0.80, 0.9999
    for _ in range(60):
        r = 0.5 * (lo + hi)
        total = first * (1 - r ** n) / (1 - r)
        if total > M["tail_len"]:
            hi = r
        else:
            lo = r
    s = spine.s_sacrum + 0.12 * ns
    l = first
    for i in range(n):
        st.append(("caudal", i, s + l * 0.5, l))
        s += l
        l *= r
    return st


def depth_at(s):
    """胴の背腹の深さ（[06]）。"""
    return lerp_table([(0.45, 0.55), (1.2, 0.95), (2.0, M["body_depth"]), (2.9, 0.95), (3.41, 0.62)], s)


def build_axial(spine, bone_mat, coll):
    vb = Builder()
    rb = Builder()
    stations = vertebra_stations(spine)
    i_sac = next(k for k, st in enumerate(stations) if st[0] == "sacral")
    for idx, (kind, i, s, l) in enumerate(stations):
        P, T, N = spine.at(s)
        vname = f"v{idx:02d}"
        # 椎骨の骨: 仙椎を根に、前は頭へ、後ろは尾の先へ連なる
        parent = None if idx == i_sac else (f"v{idx + 1:02d}" if idx < i_sac else f"v{idx - 1:02d}")
        def_bone(vname, P - T * (l * 0.5), P + T * (l * 0.5), parent)
        vb.set_group(vname)
        rb.set_group(vname)
        if kind == "caudal":
            f = i / max(1, M["caudal"] - 1)
            rc = 0.045 * (1 - f) ** 1.1 + 0.006
            spine_h = 0.13 * (1 - f) ** 1.3 + 0.01
        elif kind == "cervical":
            rc, spine_h = 0.04, 0.06 + 0.012 * i
        else:
            rc, spine_h = 0.045, 0.15
        # 椎体（細長い円柱。前後が少し太い）
        a, b = P - T * (l * 0.46), P + T * (l * 0.46)
        vb.tube([a, P, b], [rc * 1.15, rc * 0.85, rc * 1.15], sides=8)
        # 神経棘（[06] 先が平たく広がる）
        top = P + N * (rc + spine_h)
        w_ap = l * 0.22 if kind != "caudal" else min(l * 0.14, 0.02)
        vb.tube([P + N * rc * 0.5, top], [w_ap, w_ap * 0.8], sides=8, up=T, flat=0.35)
        if kind in ("trunk", "sacral") or (kind == "caudal" and i < 25):
            cap_len = l * (0.55 if kind != "caudal" else 0.45)
            vb.tube([top - T * cap_len * 0.5, top + T * cap_len * 0.5], rc * 0.38, sides=6, up=N, flat=0.8)
        # 横突起・関節突起
        for side in (-1, 1):
            vb.tube([P + Vector((0, side * rc * 0.6, 0)), P + Vector((0, side * (rc + 0.03 + (0.02 if kind == "sacral" else 0)), 0)) - N * 0.01],
                    rc * 0.35, sides=5)
        # 尾の血道弓（腹側の短い棘）
        if kind == "caudal" and i < 45:
            f = i / max(1, M["caudal"] - 1)
            hh = 0.09 * (1 - f) ** 1.2 + 0.008
            vb.tube([P - N * rc * 0.6, P - N * (rc + hh) + T * hh * 0.4], rc * 0.3, sides=5)
        # 肋骨
        if kind == "trunk":
            build_rib(spine, rb, i, s, vname)
            rb.set_group(vname)
        if kind == "cervical" and i >= 3:
            for side in (-1, 1):
                rb.tube([spine.local(s, 0, -0.02, side * 0.05), spine.local(s, 0.08, -0.12 - 0.05 * (i - 3), side * 0.09)], 0.012, sides=5)
    vb.emit("Vertebrae", bone_mat, coll)
    rb.emit("Ribs", bone_mat, coll)
    return stations


RIB_LEN = [0.35, 0.55, 0.75, 0.9, 1, 1, 1, 1, 1, 1, 1, 0.95, 0.8, 0.6, 0.4, 0.22]
HOOP = set(range(2, 12))   # 腹側の肋骨が正中で左右つながる範囲（[06] 腹側で前へ折れる線）


def build_rib(spine, rb, i, s, vname):
    D = depth_at(s)
    w = M["body_half_width"] * lerp_table([(0.45, 0.6), (1.5, 1.0), (2.8, 1.0), (3.41, 0.65)], s)
    f = RIB_LEN[min(i, len(RIB_LEN) - 1)]
    for side in (-1, 1):
        bname = f"rib{i:02d}.{'L' if side > 0 else 'R'}"
        rb.set_group(bname)
        # [06] 背側の肋骨は後ろ下へ長く斜めに、腹側の肋骨は前下へ折れて正中へ
        ctrl = [spine.local(s, 0.0, -0.01, side * 0.045),
                spine.local(s, 0.16, -0.16 * D, side * 0.75 * w),
                spine.local(s, 0.44, -0.42 * D, side * 1.0 * w),
                spine.local(s, 0.66, -0.66 * D, side * 0.85 * w)]
        pts = bezier_pts(ctrl, 8)
        cut = max(2, int(len(pts) * f))
        pts = pts[:cut]
        def_bone(bname, ctrl[0], pts[-1], vname)
        rb.tube(pts, [0.016] * len(pts), sides=6)
        if i in HOOP:
            v = [pts[-1], spine.local(s, 0.55, -0.85 * D, side * 0.45 * w), spine.local(s, 0.42, -0.99 * D, side * 0.02)]
            rb.tube(bezier_pts(v, 6), 0.012, sides=5)


# ================================================================ 肢帯と四肢
def unit(v):
    v = Vector(v)
    return v.normalized()


def build_hand(b, wrist, D, G, phal, bundles, length, curl_deg=80.0):
    """D=手の伸びる向き、G=2つの束が向かい合う軸。束は G の + 側と - 側に分かれ、互いへ巻き込む（[D15] の束）。
    指骨は1本ずつ離して置き、関節に小さな隙間を残す。末節は爪の形の円錐。"""
    D, G = D.normalized(), G.normalized()
    H = D.cross(G).normalized()
    # 手根骨・足根骨の小さな塊
    for k in range(3):
        b.ellipsoid(wrist + D * (0.02 + 0.03 * (k % 2)) + H * (k - 1) * 0.035, D * 0.022, G * 0.03, H * 0.02, 8)
    n_meta = 0.34 * length
    longest = max(phal)
    for gi, bundle in enumerate(bundles):
        sgn = 1 if gi == 0 else -1
        for k, d in enumerate(bundle):
            spread = (k - (len(bundle) - 1) / 2) * 0.034
            base = wrist + D * 0.07 + H * spread
            dirm = (D + G * sgn * 0.45).normalized()
            # 中手骨（束の中で1本ずつ）
            p0, p1 = base, base + dirm * n_meta
            b.tube([p0, (p0 + p1) * 0.5, p1], [0.02, 0.016, 0.019], sides=7)
            digit_len = (length - n_meta) * (0.75 + 0.25 * phal[d] / longest)
            seg = digit_len / phal[d]
            dcur, p = dirm, p1 + dirm * 0.008
            for j in range(phal[d]):
                dcur = (Matrix.Rotation(math.radians(-curl_deg / phal[d]), 3, H * sgn) @ dcur).normalized()
                q = p + dcur * seg * (1.0 - 0.06 * j)
                if j < phal[d] - 1:
                    b.tube([p, (p + q) * 0.5, q], [0.017, 0.013, 0.016], sides=6)
                else:
                    b.cone(p, q + dcur * 0.02, 0.014, 6)   # 爪の芯（末節）
                p = q + dcur * 0.008


def limb(b, j0, dirs, lens, radii, paired_offset=0.0, groups=None):
    pts = [j0]
    p = j0
    for d, l in zip(dirs, lens):
        p = p + d.normalized() * l
        pts.append(p)
    for k in range(len(lens)):
        a, c = pts[k], pts[k + 1]
        if groups:
            b.set_group(groups[k])
        if paired_offset > 0 and k == 1:
            # 前腕・下腿は2本（橈骨と尺骨、脛骨と腓骨）
            side = (c - a).cross(Vector((0, 1, 0)))
            if side.length < 1e-6:
                side = Vector((0, 0, 1))
            side = side.normalized() * paired_offset
            b.tube([a + side * 0.3, (a + c) * 0.5 + side, c + side * 0.4], [radii[k] * 0.9] * 3, sides=7)
            b.tube([a - side * 0.3, (a + c) * 0.5 - side, c - side * 0.4], [radii[k] * 0.75] * 3, sides=7)
        else:
            mid = (a + c) * 0.5
            b.tube([a, a + (c - a) * 0.12, mid, c - (c - a) * 0.12, c], [radii[k] * 1.5, radii[k] * 1.1, radii[k], radii[k] * 1.1, radii[k] * 1.45], sides=8)
    return pts


def nearest_station(stations, s):
    k = min(range(len(stations)), key=lambda j: abs(stations[j][2] - s))
    return f"v{k:02d}"


def build_appendicular(spine, bone_mat, coll, stations):
    g = Builder()
    fl = Builder()
    hl = Builder()
    # ---- 肩帯（[DM] 肩甲骨は高く細い）
    s_sh = M["neck_len"] + 0.18
    shoulders = {}
    for side in (-1, 1):
        S = "L" if side > 0 else "R"
        top = spine.local(s_sh, -0.02, -0.08, side * 0.12)
        sh = spine.local(s_sh, 0.04, -0.08 - M["scapula"], side * 0.19)
        g.set_group(f"scapula.{S}")
        def_bone(f"scapula.{S}", top, sh, nearest_station(stations, s_sh))
        g.tube([top, (top + sh) * 0.5 + Vector((0, side * 0.03, 0)), sh], [0.03, 0.026, 0.035], sides=8, up=Vector((0, 1, 0)), flat=0.5)
        # 烏口骨: 肩関節から腹側の正中（胸骨は軟骨なので手順 5）
        g.tube([sh, spine.local(s_sh, -0.06, -0.08 - M["scapula"] - 0.28, side * 0.05)], 0.028, sides=7, up=Vector((0, 1, 0)), flat=0.5)
        shoulders[side] = sh
    # ---- 腰帯
    s_hip = spine.s_sacrum + 0.12
    hips = {}
    g.set_group("pelvis")
    def_bone("pelvis", spine.local(s_hip, 0.0, -0.02), spine.local(s_hip, 0.06, -M["ilium"]), nearest_station(stations, s_hip))
    for side in (-1, 1):
        top = spine.local(s_hip, 0.0, -0.02, side * 0.07)
        ac = spine.local(s_hip, 0.06, -M["ilium"], side * 0.15)
        g.tube([top, ac], [0.032, 0.036], sides=8, up=Vector((0, 1, 0)), flat=0.6)
        g.ellipsoid(ac, Vector((0.035, 0, 0)), Vector((0, 0.03, 0)), Vector((0, 0, 0.035)), 8)
        g.tube([ac, spine.local(s_hip, -0.16, -M["ilium"] - 0.26, side * 0.04)], 0.026, sides=7, up=Vector((0, 1, 0)), flat=0.5)  # 恥骨
        g.tube([ac, spine.local(s_hip, 0.16, -M["ilium"] - 0.22, side * 0.04)], 0.026, sides=7, up=Vector((0, 1, 0)), flat=0.5)   # 坐骨
        hips[side] = ac
    g.emit("Girdles", bone_mat, coll)

    # ---- 四肢: [01] では前肢も後肢も腹側（+X）へほぼ水平に出し、手足は軽く握る
    joints = {}
    for side in (-1, 1):
        S = "L" if side > 0 else "R"
        lat = side * 0.35
        dz = side * 0.12     # [01] 手前と奥の肢が上下に少しずれて見える
        fore = limb(fl, shoulders[side],
                    [Vector((0.86, lat, -0.30 + dz)), Vector((0.95, lat * 0.25, 0.18 + dz))],
                    [M["humerus"], M["forearm"]], [0.038, 0.024], paired_offset=0.026,
                    groups=[f"upperarm.{S}", f"forearm.{S}"])
        joints[("fore", side)] = fore
        dh = Vector((0.9, lat * 0.2, 0.05))
        def_bone(f"upperarm.{S}", fore[0], fore[1], f"scapula.{S}")
        def_bone(f"forearm.{S}", fore[1], fore[2], f"upperarm.{S}")
        def_bone(f"hand.{S}", fore[2], fore[2] + dh.normalized() * M["manus"] * 0.6, f"forearm.{S}")
        fl.set_group(f"hand.{S}")
        build_hand(fl, fore[-1], dh, Vector((0.0, 0.0, 1.0)),
                   PHALANGES_MANUS, BUNDLE_MANUS, M["manus"])
        hind = limb(hl, hips[side],
                    [Vector((0.80, lat, -0.20 + dz)), Vector((0.96, lat * 0.2, 0.25 + dz))],
                    [M["femur"], M["tibia"]], [0.040, 0.026], paired_offset=0.028,
                    groups=[f"thigh.{S}", f"shin.{S}"])
        joints[("hind", side)] = hind
        df = Vector((0.9, lat * 0.2, 0.08))
        def_bone(f"thigh.{S}", hind[0], hind[1], "pelvis")
        def_bone(f"shin.{S}", hind[1], hind[2], f"thigh.{S}")
        def_bone(f"foot.{S}", hind[2], hind[2] + df.normalized() * M["pes"] * 0.6, f"shin.{S}")
        hl.set_group(f"foot.{S}")
        # 足根: 近位の3要素は癒合して1つ（[D15]）
        hl.ellipsoid(hind[-1] + Vector((0.03, 0, 0)), Vector((0.05, 0, 0)), Vector((0, 0.045, 0)), Vector((0, 0, 0.04)), 8)
        build_hand(hl, hind[-1] + Vector((0.04, 0, 0)), Vector((0.9, lat * 0.2, 0.08)), Vector((0.0, 0.0, -1.0)),
                   PHALANGES_PES, BUNDLE_PES, M["pes"])
    fl.emit("Forelimbs", bone_mat, coll)
    hl.emit("Hindlimbs", bone_mat, coll)
    return joints


# ================================================================ シーン
def bone_material():
    mat = bpy.data.materials.get(PREFIX + "BoneGray") or bpy.data.materials.new(PREFIX + "BoneGray")
    mat.use_nodes = True
    # ノード名は UI の言語で訳されるので、種類で探す
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        outn = next((n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None) or mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(bsdf.outputs[0], outn.inputs[0])
    bsdf.inputs["Base Color"].default_value = BONE_GRAY
    bsdf.inputs["Roughness"].default_value = 0.55
    return mat


def clear_previous():
    coll = bpy.data.collections.get(PREFIX + "Chameleon")
    if coll:
        for ob in list(coll.objects):
            me = ob.data if ob.type == "MESH" else None
            bpy.data.objects.remove(ob, do_unlink=True)
            if me and me.users == 0:
                bpy.data.meshes.remove(me)
        bpy.data.collections.remove(coll)
    coll = bpy.data.collections.new(PREFIX + "Chameleon")
    bpy.context.scene.collection.children.link(coll)
    return coll


def landmarks(spine, H, joints, stations):
    lm = {
        "snout": H.ab(1.0, 0.02), "skull_back": H.ab(0.0, 0.02), "casque_apex": H.px(4030, 1312),
        "jaw_low": H.px(4250, 2245), "orbit_c": H.ab((4350 - H.X0) / H.PX, (2160 - 1990) / 601.0),
        "condyle": spine.at(0.0)[0], "sacrum": spine.at(spine.s_sacrum + 0.12)[0],
    }
    # 尾の渦の外縁: 仙骨から最も遠い尾の点
    best, bd = None, -1
    for k in range(int(spine.s_sacrum / spine.ds), len(spine.pts)):
        d = (spine.pts[k] - lm["sacrum"]).length
        if d > bd:
            bd, best = d, spine.pts[k]
    lm["tail_far"] = best
    lm["tail_tip"] = spine.pts[-1]
    return {k: list(v) for k, v in lm.items()}


def build():
    BONES.clear()
    coll = clear_previous()
    mat = bone_material()
    spine = Spine()
    H = build_skull(spine, mat, coll)
    stations = build_axial(spine, mat, coll)
    joints = build_appendicular(spine, mat, coll, stations)
    root = bpy.data.objects.new(PREFIX + "Root", None)
    coll.objects.link(root)
    for ob in coll.objects:
        if ob is not root:
            ob.parent = root
    return spine, H, joints, stations, coll


def render_still(out_png, coll):
    scene = bpy.context.scene
    for ob in list(scene.objects):
        if ob.name.startswith("Cube") or ob.name.startswith("Light") or ob.name == "Camera":
            ob.hide_render = True
    # 全体の外接
    mn = Vector((1e9, 1e9, 1e9)); mx = -mn
    for ob in coll.objects:
        if ob.type != "MESH":
            continue
        for v in ob.data.vertices:
            w = ob.matrix_world @ v.co
            mn = Vector((min(mn.x, w.x), min(mn.y, w.y), min(mn.z, w.z)))
            mx = Vector((max(mx.x, w.x), max(mx.y, w.y), max(mx.z, w.z)))
    c = (mn + mx) * 0.5
    size = max(mx.x - mn.x, mx.z - mn.z) * 1.08
    cam = bpy.data.objects.new(PREFIX + "Cam", bpy.data.cameras.new(PREFIX + "Cam"))
    coll.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size
    cam.location = (c.x, mn.y - 5.0, c.z)
    cam.rotation_euler = (math.radians(90), 0, 0)
    cam.data.clip_end = 100
    scene.camera = cam
    # 白い光: 白い背景＋上前方の面光源
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputWorld")
    lp = nt.nodes.new("ShaderNodeLightPath")
    seen = nt.nodes.new("ShaderNodeBackground")
    seen.inputs["Color"].default_value = (1, 1, 1, 1)
    seen.inputs["Strength"].default_value = 1.0
    amb = nt.nodes.new("ShaderNodeBackground")
    amb.inputs["Color"].default_value = (1, 1, 1, 1)
    amb.inputs["Strength"].default_value = 0.25
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0])
    nt.links.new(amb.outputs[0], mix.inputs[1])
    nt.links.new(seen.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    li = bpy.data.objects.new(PREFIX + "Key", bpy.data.lights.new(PREFIX + "Key", "AREA"))
    li.data.energy = 6.0 * size * size
    li.data.size = size
    li.location = (c.x - size * 0.3, mn.y - size, c.z + size * 0.6)
    li.rotation_euler = (Vector((c.x, c.y, c.z)) - li.location).to_track_quat("-Z", "Y").to_euler()
    coll.objects.link(li)
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 48
    scene.cycles.use_denoising = False
    scene.view_settings.view_transform = "Standard"
    scene.render.resolution_x = int(1400 * (mx.x - mn.x) / size) + 60
    scene.render.resolution_y = int(1400 * (mx.z - mn.z) / size) + 60
    scene.render.resolution_x = scene.render.resolution_y = max(scene.render.resolution_x, scene.render.resolution_y)
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.abspath(out_png)
    bpy.ops.render.render(write_still=True)
    return cam


def project(cam, p):
    from bpy_extras.object_utils import world_to_camera_view
    scene = bpy.context.scene
    co = world_to_camera_view(scene, cam, Vector(p))
    return (co.x * scene.render.resolution_x, (1 - co.y) * scene.render.resolution_y)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    spine, H, joints, stations, coll = build()
    print(f"[Chameleon] 椎骨 {len(stations)} 個（頸 {M['cervical']} / 胴 {M['trunk_vertebrae']} / 仙 {M['sacral']} / 尾 {M['caudal']}）")
    if argv:
        cam = render_still(argv[0], coll)
        lm = landmarks(spine, H, joints, stations)
        lm2 = {k: project(cam, v) for k, v in lm.items()}
        out = {"world": lm, "image_px": lm2, "resolution": [bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y]}
        jpath = argv[1] if len(argv) > 1 else os.path.splitext(argv[0])[0] + "_landmarks.json"
        with open(jpath, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=1)
        print(f"[Chameleon] 静止画: {argv[0]}  目印: {jpath}")


if __name__ == "__main__":
    main()

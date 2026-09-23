"""
イカ（ヤリイカ型 / Loliginidae）透明標本 生成スクリプト
Blender 5.2 LTS で動作確認済み。

使い方:
  - Blenderの「Scripting」でこのファイルを開いて実行 (Mac: Option+P)
  - または MCP for Blender の execute_code にこの内容を渡す
  実行するたびに「TransparentSquid」コレクションを作り直す。

透明標本のイカは、アルシアンブルーで体全体が青緑に染まる。
体の中身を「光を吸う物質」で満たしているので、光が組織を通る距離が長い所ほど色が濃い。
  - 胴（外套膜）は筋肉の壁でできた中空の筒: 壁を斜めに見通す輪郭が濃く、中央は明るく抜ける
  - エンペラは付け根が厚く、包丁の刃のように縁へ向かって薄くなり、縁はほぼ透明に消える
  - 眼は金色がかった半透明の球で、縁ほど濃い金色の輪がぼんやり透ける（黒い核はない）
  - 胴の中央は、中の黄色い消化腺と青緑の壁が重なって黄緑に見える

表現しているもの:
  外套膜（中空）・菱形のエンペラ・頭・漏斗
  8本の腕と2本の触腕（触腕の先は吸盤の並ぶ触腕掌）・腕の吸盤と角質環
  半透明の眼・口球と顎板（カラストンビ）
  体内: 軟甲（背中の芯）・消化腺・盲嚢・生殖巣・墨汁嚢と直腸・鰓

座標系: X=前後（+X が外套の後端、-X が腕の先）、Z=背腹（+Z が背）、Y=左右。
全パーツは外套長(ML)=1 の単位で作り、ルートの空オブジェクトを ML[m] 倍して実寸にする。
"""

import bpy
import bmesh
import json
import math
import random
from mathutils import Vector, Matrix, Euler

SPECIES = {
    "name": "TransparentSquid",
    "mantle_length": 0.10,   # ML [m]
    "arm_suckers_rows": 2,
    "club_sucker_rows": 4,
}

PREFIX = "SQ_"

# 外套膜の太さ（u: 外套の開口0 → 後端1、値は ML=1 基準の半径）
MANTLE_RADIUS = [(0.0, 0.118), (0.08, 0.132), (0.25, 0.132), (0.45, 0.118), (0.65, 0.092),
                 (0.82, 0.058), (0.93, 0.028), (1.0, 0.006)]
MANTLE_FLATTEN = 0.82          # 背腹方向につぶれた断面
MANTLE_WALL = 0.03              # 外套膜の筋肉の壁の厚さ（ML=10cm で 3mm）

# エンペラ（ヤリイカ型の菱形。外套の後ろ半分に付く）
FIN_START, FIN_END = 0.42, 1.0
FIN_MAX_WIDTH = 0.24            # 片側の張り出し
FIN_WIDEST = 0.45               # 最も幅が広くなる位置（エンペラの前端0→後端1）
FIN_BASE_THICKNESS = 0.032      # 付け根の厚さ。縁に向かって刃のように 0 へ近づく

HEAD_FRONT_X = -0.21
EYE_CENTER = (-0.085, 0.070, 0.012)
EYE_RADIUS = 0.05

# 腕（左右対称。角度は背中側0°から腹側180°へ）
ARMS = [  # (名前, 角度, 長さ, 付け根の太さ, 広がり, 先端の巻き)
    ("I", 22, 0.34, 0.022, 0.16, 0.20),
    ("II", 64, 0.42, 0.026, 0.24, -0.25),
    ("III", 110, 0.46, 0.028, 0.26, 0.30),
    ("IV", 158, 0.40, 0.027, 0.18, -0.20),
]
TENTACLE_ANGLE = 135
TENTACLE_LENGTH = 1.0

# 色（体内を通り抜ける光の色）。赤を中程度に吸い、緑と青を少しだけ吸う。
# 赤を吸いすぎると薄い所でも色が飽和して厚みの差が消えるため、
# 薄い所（エンペラの縁・腕の先）は白に近い水色、厚く見通す所（胴の輪郭・尾・頭）ほど深い青緑になる配合にする。
BODY_TINT_STOPS = [   # X を -1.3（触腕の先）→ 1.0（外套の後端）で 0→1 に対応
    (0.00, (0.35, 0.885, 0.90, 1.0)),
    (0.55, (0.35, 0.885, 0.90, 1.0)),
    (1.00, (0.30, 0.875, 0.86, 1.0)),
]
HEAD_TINT_STOPS = [   # 頭は眼の周りが金色に透ける（X を -0.25→0.08 で 0→1）
    (0.00, (0.35, 0.885, 0.90, 1.0)),
    (0.28, (0.70, 0.92, 0.55, 1.0)),
    (0.50, (0.92, 0.93, 0.45, 1.0)),
    (0.75, (0.65, 0.92, 0.55, 1.0)),
    (1.00, (0.35, 0.885, 0.90, 1.0)),
]
BODY_ABSORPTION = 460.0      # 外套の壁・エンペラ [1/m]
ARM_ABSORPTION = 550.0
HEAD_ABSORPTION = 250.0      # 頭は中身が詰まって厚いので、係数は低めでも濃く見える
BODY_SCATTER = 8.0
EYE_ABSORPTION = 90.0         # 眼は色が残りすぎないよう淡く（向こう側がはっきり透ける程度）
COLOR_SKIN = (0.85, 0.97, 1.0, 1.0)
COLOR_SUCKER_RING = (0.82, 0.95, 1.0, 1.0)
COLOR_EYE = (0.94, 0.82, 0.30, 1.0)          # 眼の中を通る光の色（淡い金色）
COLOR_BEAK = (0.12, 0.05, 0.02, 1.0)
COLOR_DIGESTIVE = (0.75, 0.88, 0.25, 1.0)
COLOR_CAECUM = (0.72, 0.90, 0.45, 1.0)
COLOR_GONAD = (0.72, 0.90, 0.62, 1.0)
COLOR_INK = (0.12, 0.18, 0.08, 1.0)
COLOR_GLADIUS = (0.55, 0.70, 0.40, 1.0)
COLOR_GILL = (0.62, 0.90, 0.96, 1.0)
COLOR_BUCCAL = (0.95, 0.82, 0.35, 1.0)

# ------------------------------------------------------------------
# 形状の基礎関数
# ------------------------------------------------------------------
def interp(ctrl, t):
    if t <= ctrl[0][0]:
        return ctrl[0][1]
    if t >= ctrl[-1][0]:
        return ctrl[-1][1]
    for i in range(len(ctrl) - 1):
        t0, v0 = ctrl[i]
        t1, v1 = ctrl[i + 1]
        if t0 <= t <= t1:
            tm, vm = ctrl[i - 1] if i > 0 else (t0 - (t1 - t0), v0 - (v1 - v0))
            tp, vp = ctrl[i + 2] if i + 2 < len(ctrl) else (t1 + (t1 - t0), v1 + (v1 - v0))
            h = t1 - t0
            m0 = (v1 - vm) / (t1 - tm) * h
            m1 = (vp - v0) / (tp - t0) * h
            u = (t - t0) / h
            u2, u3 = u * u, u * u * u
            return ((2 * u3 - 3 * u2 + 1) * v0 + (u3 - 2 * u2 + u) * m0
                    + (-2 * u3 + 3 * u2) * v1 + (u3 - u2) * m1)


def mantle_r(u):
    return interp(MANTLE_RADIUS, u)


def chain(ctrl_pts, per_seg=6):
    pts = [Vector(p) for p in ctrl_pts]
    if len(pts) == 2:
        return [pts[0].lerp(pts[1], i / per_seg) for i in range(per_seg + 1)]
    out = []
    for i in range(len(pts) - 1):
        p0 = pts[i - 1] if i > 0 else pts[0] * 2 - pts[1]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < len(pts) else pts[-1] * 2 - pts[-2]
        for k in range(per_seg):
            u = k / per_seg
            u2, u3 = u * u, u * u * u
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * u3))
    out.append(pts[-1].copy())
    return out


def taper(n, r0, r1, power=1.0):
    return [r0 + (r1 - r0) * ((i / max(n - 1, 1)) ** power) for i in range(n)]


def tangents_of(pts):
    n = len(pts)
    out = []
    for i in range(n):
        d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
        out.append(d.normalized() if d.length > 1e-9 else Vector((1, 0, 0)))
    return out


# ------------------------------------------------------------------
# メッシュ組み立て
# ------------------------------------------------------------------
class MeshBuilder:
    def __init__(self):
        self.verts = []
        self.faces = []
        self.attrs = {}       # 頂点ごとの値（名前→値の列）。使う部位だけ verts と同じ数を入れる

    def mark(self, name, value):
        """前回 mark した所から今までに追加した頂点すべてに、同じ値を付ける（どの腕の頂点か等）"""
        values = self.attrs.setdefault(name, [])
        values.extend([value] * (len(self.verts) - len(values)))

    def tube(self, pts, radii, sides=8, closed=False):
        pts = [Vector(p) for p in pts]
        n = len(pts)
        tangents = tangents_of(pts)
        if closed:
            tangents = [(pts[(i + 1) % n] - pts[i - 1]).normalized() for i in range(n)]
        ref = Vector((0, 1, 0)) if abs(tangents[0].y) < 0.9 else Vector((1, 0, 0))
        normal = tangents[0].cross(ref).normalized()
        base = len(self.verts)
        for i in range(n):
            if i > 0:
                axis = tangents[i - 1].cross(tangents[i])
                if axis.length > 1e-9:
                    normal = Matrix.Rotation(tangents[i - 1].angle(tangents[i]), 3, axis.normalized()) @ normal
                normal = (normal - tangents[i] * normal.dot(tangents[i])).normalized()
            binormal = tangents[i].cross(normal)
            for k in range(sides):
                a = 2 * math.pi * k / sides
                self.verts.append(pts[i] + (normal * math.cos(a) + binormal * math.sin(a)) * radii[i])
        segs = n if closed else n - 1
        for i in range(segs):
            i2 = (i + 1) % n
            for k in range(sides):
                a = base + i * sides + k
                b = base + i * sides + (k + 1) % sides
                c = base + i2 * sides + (k + 1) % sides
                d = base + i2 * sides + k
                self.faces.append((a, d, c, b))
        if closed:
            return
        c0 = len(self.verts)
        self.verts.append(pts[0].copy())
        for k in range(sides):
            self.faces.append((c0, base + (k + 1) % sides, base + k))
        c1 = len(self.verts)
        self.verts.append(pts[-1].copy())
        e = base + (n - 1) * sides
        for k in range(sides):
            self.faces.append((c1, e + k, e + (k + 1) % sides))

    def ellipsoid(self, c, rx, ry, rz, seg=16, rings=10):
        base = len(self.verts)
        for i in range(1, rings):
            th = math.pi * i / rings
            for k in range(seg):
                ph = 2 * math.pi * k / seg
                self.verts.append(Vector((c.x + rx * math.sin(th) * math.cos(ph),
                                          c.y + ry * math.sin(th) * math.sin(ph),
                                          c.z + rz * math.cos(th))))
        pole_top = len(self.verts)
        self.verts.append(Vector((c.x, c.y, c.z + rz)))
        pole_bot = len(self.verts)
        self.verts.append(Vector((c.x, c.y, c.z - rz)))
        for i in range(rings - 2):
            for k in range(seg):
                a = base + i * seg + k
                b = base + i * seg + (k + 1) % seg
                self.faces.append((a, b, b + seg, a + seg))
        last = base + (rings - 2) * seg
        for k in range(seg):
            self.faces.append((pole_top, base + k, base + (k + 1) % seg))
            self.faces.append((pole_bot, last + (k + 1) % seg, last + k))

    def loft(self, rings):
        """同じ頂点数の輪を順につないだ閉じた筒（両端はふさぐ）"""
        ns = len(rings[0])
        base = len(self.verts)
        for ring in rings:
            self.verts.extend(Vector(p) for p in ring)
        for i in range(len(rings) - 1):
            for k in range(ns):
                a = base + i * ns + k
                b = base + i * ns + (k + 1) % ns
                self.faces.append((a, b, b + ns, a + ns))
        for idx, ring in ((0, rings[0]), (len(rings) - 1, rings[-1])):
            c = len(self.verts)
            self.verts.append(sum((Vector(p) for p in ring), Vector()) / ns)
            off = base + idx * ns
            for k in range(ns):
                self.faces.append((c, off + (k + 1) % ns, off + k))

    def hollow(self, outer, inner):
        """外側と内側の輪の列から、壁だけに厚みのある中空の筒を作る（前端は開口、後端は閉じる）"""
        ns = len(outer[0])
        bo = len(self.verts)
        for ring in outer:
            self.verts.extend(Vector(p) for p in ring)
        bi = len(self.verts)
        for ring in inner:
            self.verts.extend(Vector(p) for p in ring)
        for base, rings in ((bo, outer), (bi, inner)):
            for i in range(len(rings) - 1):
                for k in range(ns):
                    a = base + i * ns + k
                    b = base + i * ns + (k + 1) % ns
                    self.faces.append((a, b, b + ns, a + ns))
        for k in range(ns):
            self.faces.append((bo + k, bi + k, bi + (k + 1) % ns, bo + (k + 1) % ns))
        for base, rings in ((bo, outer), (bi, inner)):
            last = base + (len(rings) - 1) * ns
            c = len(self.verts)
            self.verts.append(sum((Vector(p) for p in rings[-1]), Vector()) / ns)
            for k in range(ns):
                self.faces.append((c, last + k, last + (k + 1) % ns))

    def sheet(self, grid_top, grid_bot):
        """上面・下面の格子 [u][v] から閉じた薄板を作る（ひれ・軟甲）"""
        nu, nv = len(grid_top), len(grid_top[0])
        base = len(self.verts)
        for grid in (grid_top, grid_bot):
            for row in grid:
                self.verts.extend(Vector(p) for p in row)
        top = lambda i, j: base + i * nv + j
        bot = lambda i, j: base + nu * nv + i * nv + j
        for i in range(nu - 1):
            for j in range(nv - 1):
                self.faces.append((top(i, j), top(i + 1, j), top(i + 1, j + 1), top(i, j + 1)))
                self.faces.append((bot(i, j), bot(i, j + 1), bot(i + 1, j + 1), bot(i + 1, j)))
        for i in range(nu - 1):
            for j in (0, nv - 1):
                self.faces.append((top(i, j), bot(i, j), bot(i + 1, j), top(i + 1, j)))
        for j in range(nv - 1):
            for i in (0, nu - 1):
                self.faces.append((top(i, j), top(i, j + 1), bot(i, j + 1), bot(i, j)))


# ------------------------------------------------------------------
# マテリアル
# ------------------------------------------------------------------
class NodeGraph:
    def __init__(self, name):
        self.mat = bpy.data.materials.new(PREFIX + name)
        self.mat.use_nodes = True
        self.nt = self.mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new("ShaderNodeOutputMaterial")
        self.coord = self.nt.nodes.new("ShaderNodeTexCoord")
        self.xyz = self.node("ShaderNodeSeparateXYZ", Vector=self.coord.outputs["Object"])

    def node(self, idname, **inputs):
        n = self.nt.nodes.new(idname)
        for key, value in inputs.items():
            self.set(n.inputs[key], value)
        return n

    def set(self, socket, value):
        if isinstance(value, bpy.types.NodeSocket):
            self.nt.links.new(value, socket)
        else:
            socket.default_value = value

    def math(self, op, a, b=0.0, c=0.0, clamp=False):
        n = self.nt.nodes.new("ShaderNodeMath")
        n.operation = op
        n.use_clamp = clamp
        for i, v in enumerate((a, b, c)):
            self.set(n.inputs[i], v)
        return n.outputs[0]

    def map_range(self, value, from_min, from_max, to_min, to_max):
        n = self.nt.nodes.new("ShaderNodeMapRange")
        n.clamp = True
        for i, v in enumerate((value, from_min, from_max, to_min, to_max)):
            self.set(n.inputs[i], v)
        return n.outputs[0]

    def ramp(self, factor, stops):
        n = self.nt.nodes.new("ShaderNodeValToRGB")
        self.set(n.inputs["Factor"], factor)
        els = n.color_ramp.elements
        els.remove(els[1])
        els[0].position, els[0].color = stops[0]
        for pos, col in stops[1:]:
            els.new(pos).color = col
        return n.outputs["Color"]

    def edge_factor(self, facing_min, edge_max, blend=0.35):
        lw = self.node("ShaderNodeLayerWeight", Blend=blend)
        return self.map_range(lw.outputs["Facing"], 0.0, 1.0, facing_min, edge_max)

    def translucent_surface(self, bsdf, facing_min, edge_max, extra=None, scale=None):
        fac = self.edge_factor(facing_min, edge_max)
        if extra is not None:
            fac = self.math("ADD", fac, extra, clamp=True)
        if scale is not None:
            fac = self.math("MULTIPLY", fac, scale)
        mix = self.node("ShaderNodeMixShader", Factor=fac)
        self.set(mix.inputs[1], self.node("ShaderNodeBsdfTransparent").outputs["BSDF"])
        self.set(mix.inputs[2], bsdf.outputs["BSDF"])
        self.set(self.out.inputs["Surface"], mix.outputs["Shader"])
        self.mat.surface_render_method = "BLENDED"
        self.mat.use_backface_culling = False
        self.mat.use_transparency_overlap = True

    def volume(self, absorb_color, absorb_density, scatter_color, scatter_density, anisotropy=0.35):
        absorb = self.node("ShaderNodeVolumeAbsorption", Color=absorb_color, Density=absorb_density)
        scatter = self.node("ShaderNodeVolumeScatter", Color=scatter_color, Density=scatter_density,
                            Anisotropy=anisotropy)
        add = self.node("ShaderNodeAddShader")
        self.set(add.inputs[0], absorb.outputs["Volume"])
        self.set(add.inputs[1], scatter.outputs["Volume"])
        self.set(self.out.inputs["Volume"], add.outputs["Shader"])
        self.mat.volume_intersection_method = "ACCURATE"   # 中空の外套でも壁の厚みだけを数える


def make_tissue_material(name, stops, x_min, x_max, absorption, scatter, facing_min=0.03, edge_max=0.40,
                         viewport_color=(0.2, 0.85, 0.9, 0.25), root_fade=None):
    """透明化した軟体組織: 体内は青緑の吸収体、表面はつるりとした濡れたツヤだけ。
    root_fade=(x_hidden, x_full): 腕の付け根を頭の中で 0 から徐々に濃くし、差し込んだ断面を見せない"""
    g = NodeGraph(name)
    x = g.xyz.outputs["X"]
    tint = g.ramp(g.map_range(x, x_min, x_max, 0.0, 1.0), stops)
    noise = g.node("ShaderNodeTexNoise", Vector=g.coord.outputs["Object"], Scale=4.0, Detail=3.0)
    density = g.math("MULTIPLY_ADD", noise.outputs["Factor"], 0.3, 0.85)
    fade = None
    if root_fade is not None:
        fade = g.map_range(x, root_fade[0], root_fade[1], 0.0, 1.0)
        density = g.math("MULTIPLY", density, fade)
    g.volume(tint, g.math("MULTIPLY", density, absorption),
             (0.92, 0.98, 1.0, 1.0), g.math("MULTIPLY", density, scatter))
    skin = g.node("ShaderNodeBsdfPrincipled", **{"Base Color": COLOR_SKIN, "Roughness": 0.12, "IOR": 1.38,
                                                "Coat Weight": 0.6, "Coat Roughness": 0.04})
    g.translucent_surface(skin, facing_min, edge_max, scale=fade)
    g.mat.diffuse_color = viewport_color
    return g.mat


def make_fin_material():
    """エンペラ: 薄すぎて体積の描画ではにじむため、頂点の厚みから透過色を直接計算する。
    片面ごとの透過率 = exp(-(1-色) × 吸収 × 厚み/2) = 付け根の透過率 ^ (厚みの比)"""
    g = NodeGraph("Fin")
    ml = SPECIES["mantle_length"]
    half = FIN_BASE_THICKNESS * ml / 2
    base = tuple(math.exp(-(1 - c) * BODY_ABSORPTION * half) for c in BODY_TINT_STOPS[-2][1][:3]) + (1.0,)
    thick = g.node("ShaderNodeAttribute")
    thick.attribute_name = "thickness"
    # 刃先でも表皮と結合組織の色は残る（実物も縁まで青緑で輪郭がはっきりしている）
    depth = g.math("MULTIPLY_ADD", thick.outputs["Fac"], 1.1, 0.25)
    transmit = g.node("ShaderNodeGamma", Color=base, Gamma=depth)
    clear = g.node("ShaderNodeBsdfTransparent", Color=transmit.outputs["Color"])
    skin = g.node("ShaderNodeBsdfPrincipled", **{"Base Color": COLOR_SKIN, "Roughness": 0.12, "IOR": 1.38,
                                                "Coat Weight": 0.6, "Coat Roughness": 0.04})
    mix = g.node("ShaderNodeMixShader", Factor=g.edge_factor(0.02, 0.30))
    g.set(mix.inputs[1], clear.outputs["BSDF"])
    g.set(mix.inputs[2], skin.outputs["BSDF"])
    g.set(g.out.inputs["Surface"], mix.outputs["Shader"])
    g.mat.surface_render_method = "BLENDED"
    g.mat.use_backface_culling = False
    g.mat.use_transparency_overlap = True
    g.mat.diffuse_color = (0.2, 0.85, 0.9, 0.2)
    return g.mat


def make_eye_material():
    """眼: 金色がかった半透明の球。表面は角膜のような透明なツヤ"""
    g = NodeGraph("Eye")
    # 核（黒目）は置かず、縁ほど濃くして金色の輪がぼんやり透ける見え方にする
    ex, ey, ez = EYE_CENTER
    local = g.node("ShaderNodeCombineXYZ", X=g.math("SUBTRACT", g.xyz.outputs["X"], ex),
                   Y=g.math("SUBTRACT", g.math("ABSOLUTE", g.xyz.outputs["Y"]), ey),
                   Z=g.math("SUBTRACT", g.xyz.outputs["Z"], ez))
    dist = g.node("ShaderNodeVectorMath", Vector=local.outputs["Vector"])
    dist.operation = "LENGTH"
    rim = g.map_range(dist.outputs["Value"], 0.35 * EYE_RADIUS, EYE_RADIUS, 0.35, 1.6)
    g.volume(COLOR_EYE, g.math("MULTIPLY", rim, EYE_ABSORPTION), (1.0, 0.95, 0.80, 1.0), 6.0)
    cornea = g.node("ShaderNodeBsdfPrincipled", **{"Base Color": (1.0, 1.0, 1.0, 1.0), "Roughness": 0.04,
                                                  "Coat Weight": 1.0, "Coat Roughness": 0.02})
    g.translucent_surface(cornea, 0.0, 0.10)   # 輪郭のツヤが強いと「目玉を貼った」ように見える
    g.mat.diffuse_color = (0.9, 0.75, 0.3, 0.4)
    return g.mat


def make_organ_material(name, color, absorption, scatter, viewport_alpha=0.3):
    """内臓: 表面は描かず、中身の色の濁りだけで見せる"""
    g = NodeGraph(name)
    noise = g.node("ShaderNodeTexNoise", Vector=g.coord.outputs["Object"], Scale=14.0, Detail=3.0)
    density = g.math("MULTIPLY_ADD", noise.outputs["Factor"], 0.8, 0.6)
    g.volume(color, g.math("MULTIPLY", density, absorption),
             (0.95, 0.95, 0.9, 1.0), g.math("MULTIPLY", density, scatter), anisotropy=0.2)
    g.mat.diffuse_color = (color[0], color[1], color[2], viewport_alpha)
    return g.mat


def make_glossy_material(name, color, roughness=0.2, alpha=1.0, coat=0.8, metallic=0.0, facing=(0.05, 0.4)):
    g = NodeGraph(name)
    bsdf = g.node("ShaderNodeBsdfPrincipled", **{"Base Color": color, "Roughness": roughness,
                                                "Coat Weight": coat, "Coat Roughness": 0.03,
                                                "Metallic": metallic})
    if alpha < 1.0:
        g.translucent_surface(bsdf, facing[0] * alpha / 0.5, facing[1])
    else:
        g.set(g.out.inputs["Surface"], bsdf.outputs["BSDF"])
    g.mat.diffuse_color = (color[0], color[1], color[2], alpha)
    return g.mat


def build_materials():
    return {
        "body": make_tissue_material("Body", BODY_TINT_STOPS, -1.3, 1.0, BODY_ABSORPTION, BODY_SCATTER),
        "arm": make_tissue_material("Arm", BODY_TINT_STOPS, -1.3, 1.0, ARM_ABSORPTION, BODY_SCATTER,
                                    root_fade=(HEAD_FRONT_X + 0.03, HEAD_FRONT_X - 0.04)),
        "head": make_tissue_material("Head", HEAD_TINT_STOPS, -0.25, 0.08, HEAD_ABSORPTION, BODY_SCATTER,
                                     viewport_color=(0.6, 0.85, 0.5, 0.3)),
        "sucker": make_glossy_material("SuckerRing", COLOR_SUCKER_RING, roughness=0.2, alpha=0.4, facing=(0.15, 0.6)),
        "eye": make_eye_material(),
        "fin": make_fin_material(),
        "beak": make_glossy_material("Beak", COLOR_BEAK, roughness=0.3, coat=0.5),
        "buccal": make_organ_material("BuccalMass", COLOR_BUCCAL, 260.0, 40.0),
        "digestive": make_organ_material("DigestiveGland", COLOR_DIGESTIVE, 250.0, 20.0),
        "caecum": make_organ_material("Caecum", COLOR_CAECUM, 180.0, 20.0),
        "gonad": make_organ_material("Gonad", COLOR_GONAD, 150.0, 5.0),
        "ink": make_glossy_material("InkSac", COLOR_INK, roughness=0.3, alpha=0.3, coat=0.3, facing=(0.2, 0.6)),
        "gladius": make_glossy_material("Gladius", COLOR_GLADIUS, roughness=0.5, alpha=0.15, coat=0.0,
                                        facing=(0.03, 0.25)),
        "gill": make_glossy_material("Gill", COLOR_GILL, roughness=0.3, alpha=0.25, coat=0.3, facing=(0.1, 0.4)),
    }


# ------------------------------------------------------------------
# 各部位
# ------------------------------------------------------------------
def build_mantle():
    mb = MeshBuilder()
    outer, inner = [], []
    nu, ns = 90, 40
    for i in range(nu + 1):
        u = (1 - math.cos(math.pi * i / nu)) / 2
        r = mantle_r(u)
        ri, rzi = r - MANTLE_WALL, r * MANTLE_FLATTEN - MANTLE_WALL
        ring_o, ring_i = [], []
        for k in range(ns):
            th = 2 * math.pi * k / ns
            # 外套の背側の縁は前方に尖って張り出す
            lip = -0.035 * max(0.0, math.cos(th)) ** 6 * max(0.0, 1 - u / 0.05)
            ring_o.append((u + lip, r * math.sin(th), r * MANTLE_FLATTEN * math.cos(th)))
            ring_i.append((u + lip, ri * math.sin(th), rzi * math.cos(th)))
        outer.append(ring_o)
        if rzi > 0.008:
            inner.append(ring_i)
    mb.hollow(outer, inner)
    return mb


def fin_width(q):
    """菱形: 前端から最大幅まで膨らみ、後端へまっすぐ細くなる（最大幅の角は少し丸める）"""
    if q < FIN_WIDEST:
        w = (q / FIN_WIDEST) ** 0.75
    else:
        w = ((1 - q) / (1 - FIN_WIDEST)) ** 1.15
    w *= 1 - 0.12 * math.exp(-((q - FIN_WIDEST) / 0.08) ** 2)
    return max(FIN_MAX_WIDTH * w, 0.006)


def build_fins(fin_mb):
    nu, nv = 60, 16
    for side in (1, -1):
        top, bot, thick = [], [], []
        for i in range(nu + 1):
            q = i / nu
            u = FIN_START + (FIN_END - 0.005 - FIN_START) * q
            r = mantle_r(u)
            y0, z0 = r * 0.78, r * MANTLE_FLATTEN * 0.5   # 付け根は外套の背側寄りの壁の中
            w = fin_width(q)
            end_taper = min(1.0, w / 0.05)
            row_t, row_b, thick_row = [], [], []
            for j in range(nv + 1):
                v = j / nv
                # 包丁の刃のように、縁へ向かって厚みが急速に 0 へ近づく
                th = FIN_BASE_THICKNESS * end_taper * (1 - v) ** 1.6 + 0.0006
                z = z0 * (1 - v) - 0.012 * v
                y = side * (y0 + (w + r * 0.22) * v)
                row_t.append((u, y, z + th / 2))
                row_b.append((u, y, z - th / 2))
                thick_row.append(th / FIN_BASE_THICKNESS)
            top.append(row_t)
            bot.append(row_b)
            thick.append(thick_row)
        fin_mb.sheet(top, bot)
        # sheet() は上面の格子→下面の格子の順に頂点を並べる
        flat = [t for row in thick for t in row]
        grid_q = [i / nu for i in range(nu + 1) for _ in range(nv + 1)]
        grid_v = [j / nv for _ in range(nu + 1) for j in range(nv + 1)]
        fin_mb.attrs.setdefault("thickness", []).extend(flat + flat)
        fin_mb.attrs.setdefault("fin_q", []).extend(grid_q + grid_q)   # 前端0 → 後端1
        fin_mb.attrs.setdefault("fin_v", []).extend(grid_v + grid_v)   # 付け根0 → 縁1


def build_head(head_mb, body_mb):
    rings = []
    ns = 36
    # 後端は細い首として外套の中へ丸く差し込み、前端は腕の付け根へ向かって丸くすぼまる（輪切りの断面を作らない）
    profile = [(0.075, 0.012, 0.010), (0.068, 0.040, 0.032), (0.05, 0.058, 0.048), (0.015, 0.068, 0.055),
               (-0.03, 0.092, 0.066), (-0.085, 0.112, 0.076), (-0.135, 0.098, 0.070), (-0.18, 0.078, 0.062),
               (HEAD_FRONT_X, 0.064, 0.056), (HEAD_FRONT_X - 0.025, 0.045, 0.040), (HEAD_FRONT_X - 0.035, 0.012, 0.010)]
    xs = [p[0] for p in profile]
    for i in range(60):
        x = xs[0] + (xs[-1] - xs[0]) * i / 59
        ry = interp([(-p[0], p[1]) for p in profile], -x)   # profile は X の降順 → -X は昇順
        rz = interp([(-p[0], p[2]) for p in profile], -x)
        rings.append([(x, ry * math.sin(2 * math.pi * k / ns), rz * math.cos(2 * math.pi * k / ns))
                      for k in range(ns)])
    head_mb.loft(rings)
    # 漏斗（頭の腹側、外套の中から前方へ）
    body_mb.tube(chain([Vector((0.06, 0, -0.075)), Vector((-0.02, 0, -0.082)), Vector((-0.085, 0, -0.080))], 6),
                 taper(13, 0.04, 0.02), 16)


def build_eyes(eye_mb):
    ex, ey, ez = EYE_CENTER
    for side in (1, -1):
        c = Vector((ex, side * ey, ez))
        eye_mb.ellipsoid(c, EYE_RADIUS, EYE_RADIUS * 0.9, EYE_RADIUS * 0.92, seg=28, rings=16)


def add_suckers(body_mb, ring_mb, pts, radii, oral0, s_from, s_to, rows, size=0.32):
    """腕の口側に吸盤（カップ＋角質環）を並べる"""
    tangents = tangents_of(pts)
    lengths = [0.0]
    for a, b in zip(pts, pts[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    total = lengths[-1]
    s = s_from * total
    idx = 0
    row = 0
    while s < s_to * total:
        while idx < len(lengths) - 2 and lengths[idx + 1] < s:
            idx += 1
        f = (s - lengths[idx]) / max(lengths[idx + 1] - lengths[idx], 1e-9)
        p = pts[idx].lerp(pts[idx + 1], f)
        r = radii[idx] + (radii[idx + 1] - radii[idx]) * f
        t = tangents[idx]
        o = (oral0 - t * oral0.dot(t)).normalized()
        lat = t.cross(o)
        offsets = [(-1 + 2 * (k + 0.5) / rows) * 0.8 for k in range(rows)]
        lateral = offsets[row % rows] if rows == 2 else None
        places = [lateral] if lateral is not None else offsets
        rs = r * size
        for off in places:
            c = p + o * (r * 0.82) + lat * (r * off * (0.55 if rows == 2 else 0.75))
            body_mb.ellipsoid(c, rs * 0.8, rs * 0.8, rs * 0.8, seg=8, rings=5)
            ring_c = c + o * (rs * 0.45)
            ring = [ring_c + (t * math.cos(a) + lat * math.sin(a)) * rs * 0.8
                    for a in (2 * math.pi * k / 10 for k in range(10))]
            ring_mb.tube(ring, [rs * 0.18] * 10, 5, closed=True)
        step = rs * (2.3 if rows == 2 else 2.2)
        s += step / (2 if rows == 2 else 1)
        row += 1


def record_limb(lines, body_mb, ring_mb, name, pts, e):
    """腕1本分の頂点に番号を付け、中心線を骨組み用に残す"""
    limb_id = len(lines)
    body_mb.mark("limb_id", float(limb_id))
    ring_mb.mark("limb_id", float(limb_id))
    lines.append({"name": name, "pts": [tuple(p) for p in pts], "radial": tuple(e)})


def build_arms(body_mb, ring_mb, rng, lines):
    ring_r = 0.042
    for name, ang, length, r0, spread, curl in ARMS:
        for side in (1, -1):
            phi = math.radians(ang) * side
            e = Vector((0, math.sin(phi), math.cos(phi)))
            tdir = Vector((0, math.cos(phi), -math.sin(phi)))
            jitter = rng.uniform(-0.04, 0.04)
            ctrl = []
            for k in range(8):
                s = k / 7
                x = HEAD_FRONT_X + 0.05 - (length + 0.04) * s
                radial = ring_r + (spread + jitter) * length * s ** 1.3
                p = Vector((x, 0, 0)) + e * radial + tdir * (curl * side * length * s ** 3)
                p += Vector((length * 0.25 * s ** 4 * abs(curl), 0, 0))
                ctrl.append(p)
            pts = chain(ctrl, 8)
            radii = taper(len(pts), r0, 0.0025, 0.85)
            body_mb.tube(pts, radii, 14)
            add_suckers(body_mb, ring_mb, pts, radii, -e, 0.12, 0.93, 2)
            record_limb(lines, body_mb, ring_mb, f"Arm{name}{'L' if side > 0 else 'R'}", pts, e)


def build_tentacles(body_mb, ring_mb, lines):
    for side in (1, -1):
        phi = math.radians(TENTACLE_ANGLE) * side
        e = Vector((0, math.sin(phi), math.cos(phi)))
        tdir = Vector((0, math.cos(phi), -math.sin(phi)))
        L = TENTACLE_LENGTH
        ctrl = []
        for k in range(12):
            s = k / 11
            x = HEAD_FRONT_X + 0.05 - (L + 0.04) * s
            radial = 0.03 + 0.10 * L * s ** 1.5
            p = Vector((x, 0, 0)) + e * radial + tdir * (0.05 * side * math.sin(2.2 * math.pi * s) * s)
            if s > 0.78:
                c = (s - 0.78) / 0.22
                p -= tdir * (0.12 * side * c * c) + Vector((0.09 * c ** 3, 0, 0))
            ctrl.append(p)
        pts = chain(ctrl, 8)
        n = len(pts)
        radii = []
        for i in range(n):
            s = i / (n - 1)
            if s < 0.72:
                r = 0.014 - 0.005 * s / 0.72
            elif s < 0.88:
                r = 0.009 + 0.010 * math.sin(math.pi * (s - 0.72) / 0.32)
            else:
                r = 0.017 * (1 - (s - 0.88) / 0.12) ** 1.2 + 0.0025
            radii.append(r)
        body_mb.tube(pts, radii, 14)
        add_suckers(body_mb, ring_mb, pts, radii, -e, 0.73, 0.97, SPECIES["club_sucker_rows"], size=0.26)
        record_limb(lines, body_mb, ring_mb, f"Tentacle{'L' if side > 0 else 'R'}", pts, e)


def build_mouth(buccal_mb, beak_mb):
    buccal_mb.ellipsoid(Vector((HEAD_FRONT_X - 0.012, 0, 0)), 0.03, 0.035, 0.035, seg=16, rings=10)
    for zs in (1, -1):
        pts = chain([Vector((HEAD_FRONT_X - 0.005, 0, 0.012 * zs)), Vector((HEAD_FRONT_X - 0.03, 0, 0.008 * zs)),
                     Vector((HEAD_FRONT_X - 0.045, 0, -0.004 * zs))], 5)
        beak_mb.tube(pts, taper(len(pts), 0.013, 0.0012, 0.8), 10)


def build_viscera(mats_mb):
    dig, cae, gon, ink, gladius, gill = (mats_mb[k] for k in ("digestive", "caecum", "gonad", "ink", "gladius", "gill"))
    dig.ellipsoid(Vector((0.40, 0, -0.005)), 0.30, 0.055, 0.05, seg=24, rings=14)
    cae.ellipsoid(Vector((0.74, 0, -0.01)), 0.13, 0.032, 0.026, seg=20, rings=12)
    gon.ellipsoid(Vector((0.86, 0, 0.0)), 0.07, 0.02, 0.016, seg=16, rings=10)
    # 墨汁嚢と直腸（漏斗へ向かう）
    ink.ellipsoid(Vector((0.14, 0, -0.035)), 0.04, 0.012, 0.011, seg=16, rings=10)
    ink.tube(chain([Vector((0.11, 0, -0.04)), Vector((0.05, 0, -0.05)), Vector((0.0, 0, -0.058))], 5),
             taper(11, 0.006, 0.004), 8)

    # 軟甲（背中の芯）: 外套の背側の内面に沿って反った羽根形の薄板＋中央の軸
    nu, nv = 60, 8
    top, bot, rachis = [], [], []
    for i in range(nu + 1):
        u = -0.01 + 0.97 * i / nu
        q = (u + 0.01) / 0.97
        g = 0.03 * (math.sin(math.pi * q) ** 0.6) * (1.2 - 0.45 * q) + 0.002
        r = mantle_r(u)
        row_t, row_b = [], []
        for j in range(nv + 1):
            y = -g + 2 * g * j / nv
            z = r * MANTLE_FLATTEN * math.sqrt(max(0.0, 1 - (y / r) ** 2)) * 0.9 - 0.004
            row_t.append((u, y, z + 0.0015))
            row_b.append((u, y, z - 0.0015))
        top.append(row_t)
        bot.append(row_b)
        rachis.append(Vector((u, 0, r * MANTLE_FLATTEN * 0.9 - 0.006)))
    gladius.sheet(top, bot)
    gladius.tube(rachis, taper(len(rachis), 0.004, 0.0012), 8)

    # 鰓（外套腔の左右、羽根状の鰓葉が並ぶ）
    for side in (1, -1):
        a = Vector((0.04, side * 0.072, -0.035))
        b = Vector((0.36, side * 0.052, -0.042))
        gill.tube([a.lerp(b, i / 10) for i in range(11)], taper(11, 0.006, 0.003), 8)
        for k in range(26):
            f = (k + 0.5) / 26
            c = a.lerp(b, f)
            h = 0.02 * math.sin(math.pi * (0.15 + 0.85 * f)) + 0.004
            gill.ellipsoid(c, 0.0035, h, h * 0.8, seg=10, rings=6)


# ------------------------------------------------------------------
# シーン管理
# ------------------------------------------------------------------
def clear_previous():
    name = SPECIES["name"]
    if name in bpy.data.collections:
        coll = bpy.data.collections[name]
        for obj in list(coll.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        bpy.data.collections.remove(coll)
    for me in list(bpy.data.meshes):
        if me.users == 0 and me.name.startswith(PREFIX):
            bpy.data.meshes.remove(me)
    for mat in list(bpy.data.materials):
        if mat.name.startswith(PREFIX):
            bpy.data.materials.remove(mat)


def hide_default_cube():
    """初期シーンの 2m 立方体の中に標本が埋もれるため、削除せず非表示にする"""
    cube = bpy.data.objects.get("Cube")
    if cube is not None:
        cube.hide_viewport = True
        cube.hide_render = True


def configure_volume_rendering():
    """体内の濁りを細かく描くための EEVEE 設定（初期値だと 0.1m〜100m に粗く割り振られる）"""
    e = bpy.context.scene.eevee
    e.use_volume_custom_range = True
    e.volumetric_start = 0.005
    e.volumetric_end = 3.0
    e.volumetric_tile_size = "2"
    e.volumetric_samples = 128
    e.use_volumetric_shadows = True


def configure_lightbox():
    """透明標本の撮影と同じ「白いライトボックス」の見え方にする。
    AgX（Blender 既定の色処理）は明るい透過光の色を白く飛ばすため、見たままの Standard にする。"""
    scene = bpy.context.scene
    scene.view_settings.view_transform = "Standard"
    world = scene.world
    if world is None:
        world = bpy.data.worlds.new("World")
        scene.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    bg.inputs["Strength"].default_value = 1.0


def emit(name, mb, material, coll, root, smooth=True):
    me = bpy.data.meshes.new(PREFIX + name)
    me.from_pydata([tuple(v) for v in mb.verts], [], mb.faces)
    for attr_name, values in mb.attrs.items():
        if len(values) != len(mb.verts):
            raise ValueError(f"{name}: {attr_name} の数 {len(values)} が頂点数 {len(mb.verts)} と一致しません")
        me.attributes.new(attr_name, "FLOAT", "POINT").data.foreach_set("value", values)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
    me.materials.append(material)
    obj = bpy.data.objects.new(name, me)
    obj["squid_part"] = name   # 同じ名前の物（魚の Eyes など）があると名前が Eyes.001 になるため、部位名は別に持つ
    coll.objects.link(obj)
    obj.parent = root
    return obj


def squid_parts():
    """イカのコレクション内の部位を {部位名: オブジェクト} で返す"""
    coll = bpy.data.collections[SPECIES["name"]]
    return {o["squid_part"]: o for o in coll.objects if "squid_part" in o}


def frame_viewports():
    if bpy.app.background:
        return
    ml = SPECIES["mantle_length"]
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.shading.type = "MATERIAL"
            space.shading.use_scene_world = True
            space.shading.use_scene_lights = True
            space.clip_start = 0.001
            r3d = space.region_3d
            r3d.view_perspective = "PERSP"
            r3d.view_location = (-0.15 * ml, 0.0, 0.0)
            r3d.view_rotation = Euler((math.radians(40), 0.0, math.radians(-15))).to_quaternion()
            r3d.view_distance = ml * 3.6


def main():
    clear_previous()
    hide_default_cube()
    configure_volume_rendering()
    configure_lightbox()

    coll = bpy.data.collections.new(SPECIES["name"])
    bpy.context.scene.collection.children.link(coll)
    root = bpy.data.objects.new(SPECIES["name"] + "_Root", None)
    root.empty_display_size = 0.5
    ml = SPECIES["mantle_length"]
    root.scale = (ml, ml, ml)
    coll.objects.link(root)

    mats = build_materials()
    rng = random.Random(7)

    emit("Mantle", build_mantle(), mats["body"], coll, root)

    fins = MeshBuilder()
    build_fins(fins)
    emit("Fins", fins, mats["fin"], coll, root)

    head, funnel = MeshBuilder(), MeshBuilder()
    build_head(head, funnel)
    emit("Head", head, mats["head"], coll, root)
    emit("Funnel", funnel, mats["body"], coll, root)

    eyes = MeshBuilder()
    build_eyes(eyes)
    emit("Eyes", eyes, mats["eye"], coll, root)

    arms, rings, limb_lines = MeshBuilder(), MeshBuilder(), []
    build_arms(arms, rings, rng, limb_lines)
    build_tentacles(arms, rings, limb_lines)
    arms_obj = emit("Arms", arms, mats["arm"], coll, root)
    arms_obj["limb_lines"] = json.dumps(limb_lines)   # 骨組み（rig_squid.py）が腕の中心線として使う
    emit("SuckerRings", rings, mats["sucker"], coll, root)

    buccal, beak = MeshBuilder(), MeshBuilder()
    build_mouth(buccal, beak)
    emit("BuccalMass", buccal, mats["buccal"], coll, root)
    emit("Beak", beak, mats["beak"], coll, root)

    organs = {k: MeshBuilder() for k in ("digestive", "caecum", "gonad", "ink", "gladius", "gill")}
    build_viscera(organs)
    names = {"digestive": "DigestiveGland", "caecum": "Caecum", "gonad": "Gonad", "ink": "InkSac",
             "gladius": "Gladius", "gill": "Gills"}
    for key, mb in organs.items():
        emit(names[key], mb, mats[key], coll, root)

    frame_viewports()
    print(f"[{SPECIES['name']}] 生成完了: コレクション '{SPECIES['name']}' を確認してください。")


main()

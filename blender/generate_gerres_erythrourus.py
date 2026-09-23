"""
Gerres erythrourus（短鑽嘴魚 / Short Silverbiddy）透明骨格標本 生成スクリプト
Blender 5.2 LTS で動作確認済み（4.5 LTS でも動く想定）。

使い方:
  - Blenderの「Scripting」でこのファイルを開いて実行 (Mac: Option+P)
  - または MCP for Blender の execute_code にこの内容を渡す
  実行するたびに「GerresErythrourus」コレクションを作り直す。

表現しているもの（硬骨=赤紫 / 軟骨=青 / 肉=ほぼ透明）:
  頭骨（神経頭蓋・上後頭骨稜・眼窩・前上顎骨・上顎骨・歯骨・鰓蓋骨群・鰓条骨）
  鰓弓と鰓耙・舌骨軟骨、肩帯（擬鎖骨ほか）、脊柱24個（腹椎10+尾椎14）、
  神経棘・血管棘・肋骨・上肋骨・上神経骨、担鰭骨、
  背鰭(9棘10軟条)・臀鰭(3棘7軟条)・胸鰭(15条)・腹鰭(1棘5軟条)・二叉形の尾鰭と下尾骨

座標系: X=前後（-X が吻、+X が尾）、Z=上下、Y=左右。
全パーツは体長(SL)=1 の単位で作り、ルートの空オブジェクトを SL[m] 倍して実寸にする。
"""

import bpy
import bmesh
import math
from mathutils import Vector, Matrix

SPECIES = {
    "name": "GerresErythrourus",
    "standard_length": 0.12,   # SL [m]
    "vertebra_precaudal": 10,  # Gerreidae の一般値（暫定）
    "vertebra_caudal": 14,
    "dorsal_spines": 9,
    "dorsal_soft_rays": 10,
    "anal_spines": 3,
    "anal_soft_rays": 7,
    "pectoral_rays": 15,
    "pelvic_soft_rays": 5,
    "caudal_principal_rays": 17,
    "branchiostegal_rays": 6,
}

# 体の輪郭（t: 吻端0 → 尾鰭基底1、値は SL=1 基準の Z / 半幅）
# 体高 ≒ SL/2.1、背側が強く盛り上がり、口は下向き
PROFILE_TOP = [(0.0, -0.02), (0.04, 0.05), (0.10, 0.12), (0.18, 0.19), (0.26, 0.235),
               (0.34, 0.255), (0.45, 0.245), (0.58, 0.20), (0.70, 0.14), (0.80, 0.09),
               (0.90, 0.065), (1.0, 0.058)]
PROFILE_BOTTOM = [(0.0, -0.04), (0.04, -0.09), (0.10, -0.14), (0.18, -0.185), (0.28, -0.215),
                  (0.40, -0.225), (0.52, -0.21), (0.62, -0.18), (0.72, -0.12), (0.82, -0.08),
                  (0.90, -0.062), (1.0, -0.055)]
PROFILE_HALF_WIDTH = [(0.0, 0.005), (0.05, 0.03), (0.15, 0.06), (0.30, 0.075), (0.45, 0.072),
                      (0.60, 0.06), (0.75, 0.04), (0.90, 0.022), (1.0, 0.018)]

# 背鰭: 第2棘が最長（第3棘より長い）という記載を反映
DORSAL_SPINE_LENGTHS = [0.10, 0.30, 0.26, 0.22, 0.18, 0.15, 0.12, 0.10, 0.085]
DORSAL_RAY_LENGTHS = [0.11, 0.12, 0.115, 0.11, 0.10, 0.09, 0.08, 0.07, 0.06, 0.05]
# 臀鰭: 第2棘が太く頑丈
ANAL_SPINE_LENGTHS = [0.05, 0.12, 0.10]
ANAL_RAY_LENGTHS = [0.12, 0.115, 0.10, 0.09, 0.08, 0.07, 0.06]

COLOR_BONE = (0.55, 0.01, 0.40, 1.0)       # アリザリンレッドで染まった硬骨
COLOR_CARTILAGE = (0.02, 0.45, 0.95, 1.0)  # アルシアンブルーで染まった軟骨
COLOR_EYE = (0.35, 0.72, 0.95, 1.0)        # 強膜軟骨が青く染まった眼
COLOR_LENS = (0.92, 0.93, 0.90, 1.0)       # 白濁した水晶体

# 透明化された肉（グリセリン置換後の組織）。体内を「光を吸う物質」で満たすので、
# 厚い所ほど色が濃く、ひれや尾柄など薄い所ほど向こう側が透ける。
# 体の前後方向の色（0=吻端, 1=尾）: 頭は青緑、胴は琥珀、尾は淡い色
FLESH_TINT_STOPS = [
    (0.00, (0.38, 0.78, 0.86, 1.0)),
    (0.22, (0.62, 0.82, 0.70, 1.0)),
    (0.45, (0.93, 0.74, 0.42, 1.0)),
    (0.80, (0.95, 0.84, 0.62, 1.0)),
    (1.00, (0.97, 0.92, 0.82, 1.0)),
]
FLESH_ABSORPTION = 420.0    # 色の濃さ（大きいほど濃い）[1/m]
FLESH_SCATTER = 22.0        # 白い濁り（大きいほど乳白色）[1/m]
MYOMERE_FREQ = 220.0        # 筋節（くの字の筋肉の並び）の細かさ
COLOR_SKIN_SHEEN = (0.93, 0.91, 0.84, 1.0)
COLOR_MEMBRANE = (0.90, 0.78, 0.80, 1.0)   # ひれの膜（鰭条の赤みがうっすら移った透明）
COLOR_VISCERA = (0.78, 0.55, 0.36, 1.0)    # 内臓（少し濃い琥珀）
COLOR_SWIM_BLADDER = (0.86, 0.88, 0.90, 1.0)

PREFIX = "GE_"


# ------------------------------------------------------------------
# 形状の基礎関数
# ------------------------------------------------------------------
def interp(ctrl, t):
    """制御点 [(t, v), ...] を通る滑らかな曲線（Catmull-Rom）"""
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


def top(t):
    return interp(PROFILE_TOP, t)


def bot(t):
    return interp(PROFILE_BOTTOM, t)


def half_width(t):
    return interp(PROFILE_HALF_WIDTH, t)


def axis_z(t):
    """脊柱の通り道（体高の中央よりやや背側）"""
    return (top(t) + bot(t)) / 2 + 0.02 * (1 - t)


def P(t, z, y=0.0):
    return Vector((t - 0.5, y, z))


def chain(ctrl_pts, per_seg=6):
    """制御点列を通る滑らかな折れ線"""
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


def mirror_y(pts):
    return [Vector((p.x, -p.y, p.z)) for p in pts]


# ------------------------------------------------------------------
# メッシュ組み立て
# ------------------------------------------------------------------
class MeshBuilder:
    def __init__(self):
        self.verts = []
        self.faces = []

    def tube(self, pts, radii, sides=8):
        pts = [Vector(p) for p in pts]
        n = len(pts)
        tangents = []
        for i in range(n):
            d = pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]
            tangents.append(d.normalized() if d.length > 1e-9 else Vector((1, 0, 0)))
        ref = Vector((0, 1, 0)) if abs(tangents[0].y) < 0.9 else Vector((1, 0, 0))
        normal = tangents[0].cross(ref).normalized()
        base = len(self.verts)
        for i in range(n):
            if i > 0:
                axis = tangents[i - 1].cross(tangents[i])
                if axis.length > 1e-9:
                    ang = tangents[i - 1].angle(tangents[i])
                    normal = Matrix.Rotation(ang, 3, axis.normalized()) @ normal
                normal = (normal - tangents[i] * normal.dot(tangents[i])).normalized()
            binormal = tangents[i].cross(normal)
            for k in range(sides):
                a = 2 * math.pi * k / sides
                self.verts.append(pts[i] + (normal * math.cos(a) + binormal * math.sin(a)) * radii[i])
        for i in range(n - 1):
            for k in range(sides):
                a = base + i * sides + k
                b = base + i * sides + (k + 1) % sides
                c = base + (i + 1) * sides + (k + 1) % sides
                d = base + (i + 1) * sides + k
                self.faces.append((a, d, c, b))
        c0 = len(self.verts)
        self.verts.append(pts[0].copy())
        for k in range(sides):
            self.faces.append((c0, base + (k + 1) % sides, base + k))
        c1 = len(self.verts)
        self.verts.append(pts[-1].copy())
        e = base + (n - 1) * sides
        for k in range(sides):
            self.faces.append((c1, e + k, e + (k + 1) % sides))

    def bone(self, ctrl_pts, r0, r1, sides=8, per_seg=6, power=1.0, mirror=False):
        pts = chain(ctrl_pts, per_seg)
        radii = taper(len(pts), r0, r1, power)
        self.tube(pts, radii, sides)
        if mirror:
            self.tube(mirror_y(pts), radii, sides)
        return pts

    def plate(self, outline_tz, y, thickness, mirror=False):
        """(t, z) の輪郭から薄い板状の骨を作る"""
        for yy in ([y, -y] if mirror else [y]):
            pts = [(t - 0.5, z) for t, z in outline_tz]
            area = sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1]
                       for i in range(len(pts)))
            if area < 0:
                pts.reverse()
            n = len(pts)
            base = len(self.verts)
            for x, z in pts:
                self.verts.append(Vector((x, yy - thickness / 2, z)))
            for x, z in pts:
                self.verts.append(Vector((x, yy + thickness / 2, z)))
            self.faces.append(tuple(base + i for i in range(n)))
            self.faces.append(tuple(base + n + i for i in reversed(range(n))))
            for i in range(n):
                j = (i + 1) % n
                self.faces.append((base + i, base + n + i, base + n + j, base + j))

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

    def strip(self, pts_a, pts_b):
        """2本の鰭条の間に膜を張る"""
        n = min(len(pts_a), len(pts_b))
        ia = [self._add(p) for p in pts_a[:n]]
        ib = [self._add(p) for p in pts_b[:n]]
        for i in range(n - 1):
            self.faces.append((ia[i], ia[i + 1], ib[i + 1], ib[i]))

    def _add(self, p):
        self.verts.append(Vector(p))
        return len(self.verts) - 1


def fin_ray(bone_mb, base, direction, length, r0, spread, spine=False, branch=True,
            bend=None, bend_amount=0.0, n=12):
    """鰭条1本。軟条は先端6割から二股に分岐させる。膜用の軸点列を返す。"""
    d = direction.normalized()
    axis = []
    for i in range(n + 1):
        s = i / n
        p = base + d * (s * length)
        if bend is not None:
            p += bend.normalized() * (bend_amount * length * s * s)
        axis.append(p)
    if spine:
        bone_mb.tube(axis, taper(len(axis), r0, r0 * 0.12, 0.8), 8)
        return axis
    if not branch:
        bone_mb.tube(axis, taper(len(axis), r0, r0 * 0.25), 6)
        return axis
    split = int(n * 0.6)
    shaft = axis[:split + 1]
    bone_mb.tube(shaft, taper(len(shaft), r0, r0 * 0.6), 6)
    sp = spread.normalized() * (0.045 * length)
    for sign in (1, -1):
        fork = []
        for i in range(split, n + 1):
            f = (i - split) / (n - split)
            fork.append(axis[i] + sp * sign * f)
        bone_mb.tube(fork, taper(len(fork), r0 * 0.45, r0 * 0.12), 5)
    return axis


# ------------------------------------------------------------------
# マテリアル
# ------------------------------------------------------------------
def principled(mat):
    return next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")


def make_material(name, color, alpha=1.0, roughness=0.35, emission=0.0, subsurface=0.0):
    mat = bpy.data.materials.new(PREFIX + name)
    mat.use_nodes = True
    bsdf = principled(mat)
    bsdf.inputs["Base Color"].default_value = color
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Emission Color"].default_value = color
    bsdf.inputs["Emission Strength"].default_value = emission
    bsdf.inputs["Subsurface Weight"].default_value = subsurface
    mat.diffuse_color = (color[0], color[1], color[2], alpha)
    if alpha < 1.0:
        mat.surface_render_method = "BLENDED"
        mat.use_backface_culling = False
    return mat


class NodeGraph:
    """シェーダーノードを少ない記述で組むための小道具"""

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

    def math(self, op, a, b=0.0, c=0.0):
        n = self.nt.nodes.new("ShaderNodeMath")
        n.operation = op
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
        """正面から見る所は薄く、輪郭（視線が斜めに通る所）ほど濃くする"""
        lw = self.node("ShaderNodeLayerWeight", Blend=blend)
        return self.map_range(lw.outputs["Facing"], 0.0, 1.0, facing_min, edge_max)

    def translucent_surface(self, bsdf, facing_min, edge_max):
        mix = self.node("ShaderNodeMixShader", Factor=self.edge_factor(facing_min, edge_max))
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


def make_flesh_material():
    g = NodeGraph("Flesh")
    x, z = g.xyz.outputs["X"], g.xyz.outputs["Z"]
    tint = g.ramp(g.map_range(x, -0.5, 0.5, 0.0, 1.0), FLESH_TINT_STOPS)

    # 筋節: 体側の「くの字」に並ぶ筋肉のすじを、密度のわずかな縞として入れる
    chevron = g.math("MULTIPLY_ADD", g.math("ABSOLUTE", z), MYOMERE_FREQ * 0.7, g.math("MULTIPLY", x, MYOMERE_FREQ))
    stripe = g.math("MULTIPLY_ADD", g.math("SINE", chevron), 0.5, 0.5)
    noise = g.node("ShaderNodeTexNoise", Vector=g.coord.outputs["Object"], Scale=6.0, Detail=4.0)
    density = g.math("MULTIPLY", g.math("MULTIPLY_ADD", stripe, 0.35, 0.8),
                     g.math("MULTIPLY_ADD", noise.outputs["Factor"], 0.6, 0.7))
    g.volume(tint, g.math("MULTIPLY", density, FLESH_ABSORPTION),
             (0.95, 0.96, 1.0, 1.0), g.math("MULTIPLY", density, FLESH_SCATTER))

    # 表皮: 濡れたツヤ＋鱗のかすかな凹凸
    scales = g.node("ShaderNodeTexVoronoi", Vector=g.coord.outputs["Object"], Scale=45.0)
    bump = g.node("ShaderNodeBump", Strength=0.08, Distance=0.001, Height=scales.outputs["Distance"])
    skin = g.node("ShaderNodeBsdfPrincipled", **{"Base Color": COLOR_SKIN_SHEEN, "Roughness": 0.22,
                                                "IOR": 1.40, "Coat Weight": 0.5, "Coat Roughness": 0.06,
                                                "Normal": bump.outputs["Normal"]})
    g.translucent_surface(skin, 0.04, 0.45)
    g.mat.diffuse_color = (0.95, 0.85, 0.65, 0.18)
    return g.mat


def make_membrane_material():
    g = NodeGraph("FinMembrane")
    skin = g.node("ShaderNodeBsdfPrincipled", **{"Base Color": COLOR_MEMBRANE, "Roughness": 0.25,
                                                "Coat Weight": 0.4, "Coat Roughness": 0.08})
    g.translucent_surface(skin, 0.22, 0.50)
    g.mat.diffuse_color = (COLOR_MEMBRANE[0], COLOR_MEMBRANE[1], COLOR_MEMBRANE[2], 0.15)
    return g.mat


def make_viscera_material():
    """内臓: 表面は描かず、中身だけ少し濃い琥珀色の濁りにする"""
    g = NodeGraph("Viscera")
    noise = g.node("ShaderNodeTexNoise", Vector=g.coord.outputs["Object"], Scale=12.0, Detail=3.0)
    density = g.math("MULTIPLY_ADD", noise.outputs["Factor"], 0.8, 0.6)
    g.volume(COLOR_VISCERA, g.math("MULTIPLY", density, 110.0),
             (0.95, 0.92, 0.85, 1.0), g.math("MULTIPLY", density, 35.0), anisotropy=0.2)
    g.mat.diffuse_color = (COLOR_VISCERA[0], COLOR_VISCERA[1], COLOR_VISCERA[2], 0.2)
    return g.mat


def make_swim_bladder_material():
    """浮き袋: 空気の入った薄い袋。縁だけ銀色に光る"""
    g = NodeGraph("SwimBladder")
    skin = g.node("ShaderNodeBsdfPrincipled", **{"Base Color": COLOR_SWIM_BLADDER, "Metallic": 0.6,
                                                "Roughness": 0.25})
    g.translucent_surface(skin, 0.03, 0.40)
    g.mat.diffuse_color = (COLOR_SWIM_BLADDER[0], COLOR_SWIM_BLADDER[1], COLOR_SWIM_BLADDER[2], 0.15)
    return g.mat


def build_materials():
    return {
        "bone": make_material("Bone", COLOR_BONE, roughness=0.3, emission=0.15, subsurface=0.2),
        "bone_plate": make_material("BonePlate", COLOR_BONE, alpha=0.7, roughness=0.3, emission=0.15),
        "cartilage": make_material("Cartilage", COLOR_CARTILAGE, alpha=0.85, roughness=0.25, emission=0.3),
        "flesh": make_flesh_material(),
        "membrane": make_membrane_material(),
        "viscera": make_viscera_material(),
        "swim_bladder": make_swim_bladder_material(),
        "eye": make_material("Eye", COLOR_EYE, alpha=0.55, roughness=0.1, emission=0.2),
        "lens": make_material("Lens", COLOR_LENS, roughness=0.35, subsurface=0.5),
    }


def configure_volume_rendering():
    """体内の濁りを細かく描くための EEVEE 設定（初期値だと 0.1m〜100m に粗く割り振られる）"""
    e = bpy.context.scene.eevee
    e.use_volume_custom_range = True
    e.volumetric_start = 0.005
    e.volumetric_end = 3.0
    e.volumetric_tile_size = "2"
    e.volumetric_samples = 128
    e.use_volumetric_shadows = True


# ------------------------------------------------------------------
# シーン管理
# ------------------------------------------------------------------
def clear_previous():
    name = SPECIES["name"]
    if name in bpy.data.collections:
        coll = bpy.data.collections[name]
        for obj in list(coll.all_objects):
            bpy.data.objects.remove(obj, do_unlink=True)
        for child in list(coll.children_recursive):
            bpy.data.collections.remove(child)
        bpy.data.collections.remove(coll)
    for me in list(bpy.data.meshes):
        if me.users == 0:
            bpy.data.meshes.remove(me)
    for mat in list(bpy.data.materials):
        if mat.name.startswith((PREFIX, "Skeleton_Emission", "Body_Transmission")):
            bpy.data.materials.remove(mat)


def hide_default_cube():
    """初期シーンの 2m 立方体の中に標本が埋もれるため、削除せず非表示にする"""
    cube = bpy.data.objects.get("Cube")
    if cube is not None:
        cube.hide_viewport = True
        cube.hide_render = True


def emit(name, mb, material, coll, root, smooth=True):
    me = bpy.data.meshes.new(PREFIX + name)
    me.from_pydata([tuple(v) for v in mb.verts], [], mb.faces)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    if smooth:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(50))
    me.materials.append(material)
    obj = bpy.data.objects.new(name, me)
    coll.objects.link(obj)
    obj.parent = root
    return obj


# ------------------------------------------------------------------
# 各部位
# ------------------------------------------------------------------
def build_body_shell():
    mb = MeshBuilder()
    nt, ns = 80, 36
    rings = []
    for i in range(nt + 1):
        t = (1 - math.cos(math.pi * i / nt)) / 2
        hh = (top(t) - bot(t)) / 2
        zc = (top(t) + bot(t)) / 2
        hw = half_width(t)
        ring = []
        for k in range(ns):
            th = 2 * math.pi * k / ns
            s = math.sin(th)
            y = hw * math.copysign(abs(s) ** 0.8, s)
            ring.append(P(t, zc + hh * math.cos(th), y))
        rings.append(ring)
    for ring in rings:
        mb.verts.extend(ring)
    for i in range(nt):
        for k in range(ns):
            a = i * ns + k
            b = i * ns + (k + 1) % ns
            mb.faces.append((a, b, b + ns, a + ns))
    c0 = len(mb.verts)
    mb.verts.append(P(0.0, (top(0) + bot(0)) / 2))
    c1 = len(mb.verts)
    mb.verts.append(P(1.0, (top(1) + bot(1)) / 2))
    last = nt * ns
    for k in range(ns):
        mb.faces.append((c0, (k + 1) % ns, k))
        mb.faces.append((c1, last + k, last + (k + 1) % ns))
    return mb


def vertebra_positions():
    n = SPECIES["vertebra_precaudal"] + SPECIES["vertebra_caudal"]
    t0, t1 = 0.285, 0.965
    return [t0 + (t1 - t0) * i / (n - 1) for i in range(n)], (t1 - t0) / (n - 1)


def build_axial(bone):
    ts, spacing = vertebra_positions()
    n_pre = SPECIES["vertebra_precaudal"]
    n = len(ts)
    for i, t in enumerate(ts):
        f = i / (n - 1)
        r = 0.021 * (1 - 0.45 * f)
        zc = axis_z(t)
        half = spacing * 0.43
        pts = [P(t - half, axis_z(t - half)), P(t - half * 0.5, axis_z(t - half * 0.5)), P(t, zc),
               P(t + half * 0.5, axis_z(t + half * 0.5)), P(t + half, axis_z(t + half))]
        bone.tube(pts, [r, r * 0.92, r * 0.68, r * 0.92, r], 12)

        # 神経棘（背側へ、後方に傾く）
        tt = t + 0.035 + 0.05 * f
        tip_z = top(tt) - (0.012 if i >= n - 3 else 0.035)
        bone.bone([P(t, zc + r * 0.8), P((t + tt) / 2 - 0.004, (zc + tip_z) / 2 + 0.01), P(tt, tip_z)],
                  0.0055 * (1 - 0.3 * f), 0.0012, per_seg=5)

        if i >= n_pre:
            # 血管棘（腹側へ）
            bz = bot(tt) + (0.012 if i >= n - 3 else 0.03)
            bone.bone([P(t, zc - r * 0.8), P((t + tt) / 2 - 0.004, (zc + bz) / 2 - 0.01), P(tt, bz)],
                      0.0055 * (1 - 0.3 * f), 0.0012, per_seg=5)
        else:
            # 左右の血管弓の突起
            bone.bone([P(t, zc - r * 0.7, 0.01), P(t + 0.01, zc - r * 1.6, 0.018)], 0.004, 0.002,
                      per_seg=2, mirror=True)

        if 2 <= i < n_pre:
            # 肋骨（左右一対、腹腔を抱えるように弧を描く）
            hw = half_width(t)
            bone.bone([P(t, zc - r * 0.6, 0.012),
                       P(t + 0.02, (zc + bot(t)) / 2, hw * 0.8),
                       P(t + 0.05, bot(t + 0.05) + 0.04, hw * 0.45)],
                      0.005, 0.0015, per_seg=8, mirror=True)
        if i < 14:
            # 上肋骨・上神経骨（細い筋間骨）
            hw = half_width(t)
            bone.bone([P(t, zc, 0.012), P(t + 0.05, zc - 0.018, hw * 0.45), P(t + 0.095, zc - 0.035, hw * 0.5)],
                      0.0025, 0.0006, per_seg=5, mirror=True)
            bone.bone([P(t, zc + r * 0.5, 0.01), P(t + 0.05, zc + 0.03, hw * 0.4), P(t + 0.09, zc + 0.05, hw * 0.45)],
                      0.002, 0.0005, per_seg=5, mirror=True)
    return ts


def build_dorsal_fin(bone, membrane):
    ns, nr = SPECIES["dorsal_spines"], SPECIES["dorsal_soft_rays"]
    spine_ts = [0.33 + (0.56 - 0.33) * i / (ns - 1) for i in range(ns)]
    ray_ts = [0.575 + (0.79 - 0.575) * i / (nr - 1) for i in range(nr)]
    axes = []
    spread = Vector((1, 0, 0))
    for i, t in enumerate(spine_ts + ray_ts):
        is_spine = i < ns
        length = DORSAL_SPINE_LENGTHS[i] if is_spine else DORSAL_RAY_LENGTHS[i - ns]
        lean = math.radians(20 + 25 * i / (ns - 1)) if is_spine else math.radians(45 + 15 * (i - ns) / (nr - 1))
        d = Vector((math.sin(lean), 0, math.cos(lean)))
        base = P(t, top(t) - 0.004)
        axes.append(fin_ray(bone, base, d, length, 0.0065 if is_spine else 0.0038, spread,
                            spine=is_spine, bend=Vector((1, 0, 0)), bend_amount=0.08))
        # 担鰭骨（体内へ斜め前下方）
        depth = axis_z(t) + (0.05 if is_spine else 0.04)
        bone.bone([P(t, top(t) - 0.008), P(t - 0.012, (top(t) + depth) / 2), P(t - 0.02, depth)],
                  0.0065 if i < 3 else 0.005, 0.0018, per_seg=5)
    for a, b in zip(axes, axes[1:]):
        membrane.strip(a[:int(len(a) * 0.9)], b[:int(len(b) * 0.9)])
    # 背鰭前方の上神経骨（predorsal bones）
    for k, t in enumerate((0.29, 0.305, 0.32)):
        bone.bone([P(t, top(t) - 0.008), P(t - 0.006, top(t) - 0.06 - 0.01 * k)], 0.005, 0.002, per_seg=3)


def build_anal_fin(bone, membrane):
    ns, nr = SPECIES["anal_spines"], SPECIES["anal_soft_rays"]
    spine_ts = [0.60, 0.625, 0.65]
    ray_ts = [0.67 + (0.80 - 0.67) * i / (nr - 1) for i in range(nr)]
    axes = []
    spread = Vector((1, 0, 0))
    for i, t in enumerate(spine_ts[:ns] + ray_ts):
        is_spine = i < ns
        length = ANAL_SPINE_LENGTHS[i] if is_spine else ANAL_RAY_LENGTHS[i - ns]
        lean = math.radians(20 + 12 * i) if is_spine else math.radians(45 + 12 * (i - ns) / (nr - 1))
        d = Vector((math.sin(lean), 0, -math.cos(lean)))
        r0 = 0.0095 if i == 1 else (0.006 if is_spine else 0.0038)
        base = P(t, bot(t) + 0.004)
        axes.append(fin_ray(bone, base, d, length, r0, spread, spine=is_spine,
                            bend=Vector((1, 0, 0)), bend_amount=0.08))
        up = axis_z(t) - 0.05
        bone.bone([P(t, bot(t) + 0.008), P(t - 0.01, (bot(t) + up) / 2), P(t - 0.016, up)],
                  0.005, 0.0018, per_seg=5)
    # 第1担鰭骨は大きく頑丈（第1・第2棘を支える）
    t = spine_ts[0]
    bone.bone([P(t, bot(t) + 0.01), P(t - 0.02, (bot(t) + axis_z(t)) / 2), P(t - 0.04, axis_z(t) - 0.035)],
              0.012, 0.004, per_seg=6)
    for a, b in zip(axes, axes[1:]):
        membrane.strip(a[:int(len(a) * 0.9)], b[:int(len(b) * 0.9)])


def build_caudal_fin(bone, membrane):
    c = P(0.985, axis_z(0.985))
    # 尾部棒状骨と下尾骨（扇状の板）
    bone.bone([P(0.955, axis_z(0.955)), c, c + Vector((0.02, 0, 0.012))], 0.012, 0.006, per_seg=3)
    angles = [-34, -20, -6, 8, 22]
    for a0 in angles:
        a1 = a0 + 12
        outline = [(c.x + 0.5, c.z)]
        for a in (a0, a1):
            r = 0.055
            outline.append((c.x + 0.5 + r * math.cos(math.radians(a)), c.z + r * math.sin(math.radians(a))))
        bone.plate(outline, 0.0, 0.006)
    # 尾神経骨・準下尾骨
    bone.bone([P(0.95, axis_z(0.95) + 0.02), P(0.985, top(0.985) - 0.004)], 0.0045, 0.002, per_seg=3)
    bone.bone([P(0.96, axis_z(0.96) + 0.018), P(0.995, top(0.995) - 0.002)], 0.004, 0.002, per_seg=3)
    bone.bone([P(0.95, axis_z(0.95) - 0.02), P(0.985, bot(0.985) + 0.004)], 0.0045, 0.002, per_seg=3)

    # 主鰭条（深い二叉形：外側が長く中央が短い）
    n = SPECIES["caudal_principal_rays"]
    axes = []
    for k in range(n):
        a = 36 - 72 * k / (n - 1)
        rad = math.radians(a)
        start = c + Vector((math.cos(rad), 0, math.sin(rad))) * 0.045
        d = Vector((math.cos(math.radians(a * 1.1)), 0, math.sin(math.radians(a * 1.1))))
        length = 0.12 + 0.20 * (abs(a) / 36) ** 1.6
        outer = k in (0, n - 1)
        spread = Vector((-math.sin(rad), 0, math.cos(rad)))
        axes.append(fin_ray(bone, start, d, length, 0.0055 if outer else 0.0042, spread,
                            branch=not outer, bend=Vector((0, 0, 1 if a > 0 else -1)), bend_amount=0.05))
    for a, b in zip(axes, axes[1:]):
        membrane.strip(a, b)
    # 前鰭条（尾柄の上下縁に並ぶ短い棘）
    for k in range(6):
        t = 0.87 + 0.018 * k
        length = 0.03 + 0.008 * k
        for sign, edge in ((1, top(t) - 0.003), (-1, bot(t) + 0.003)):
            ang = math.radians(20 + 3 * k)
            d = Vector((math.cos(ang), 0, sign * math.sin(ang)))
            fin_ray(bone, P(t, edge), d, length, 0.0026, Vector((0, 0, 1)), spine=True, n=6)


def build_paired_fins(bone, membrane):
    # 胸鰭（体側に沿って後方へ伸びる、上側の条が最長）
    n = SPECIES["pectoral_rays"]
    for side in (1, -1):
        base_y = side * (half_width(0.32) * 0.85)
        axes = []
        for k in range(n):
            a = math.radians(20 - 55 * k / (n - 1))
            length = 0.17 if k == 0 else 0.30 - 0.012 * k
            d = Vector((math.cos(a), side * 0.12, math.sin(a)))
            base = P(0.315, -0.035 - 0.0025 * k, base_y)
            spread = Vector((-math.sin(a), 0, math.cos(a)))
            axes.append(fin_ray(bone, base, d, length, 0.0032, spread, branch=k > 0))
        for a, b in zip(axes, axes[1:]):
            membrane.strip(a, b)

    # 腹鰭（1棘5軟条、胸鰭の直下）
    lengths = [0.11, 0.14, 0.15, 0.13, 0.11, 0.09]
    for side in (1, -1):
        axes = []
        for k in range(1 + SPECIES["pelvic_soft_rays"]):
            a = math.radians(-22 - 4 * k)
            d = Vector((math.cos(a), side * 0.15, math.sin(a)))
            base = P(0.34 + 0.003 * k, bot(0.34) + 0.015, side * (0.018 + 0.002 * k))
            spread = Vector((-math.sin(a), 0, math.cos(a)))
            axes.append(fin_ray(bone, base, d, lengths[k], 0.0055 if k == 0 else 0.0032, spread,
                                spine=(k == 0)))
        for a, b in zip(axes, axes[1:]):
            membrane.strip(a, b)
        # 腰骨（前方の擬鎖骨へ向かう）
        bone.bone([P(0.34, bot(0.34) + 0.015, side * 0.02), P(0.30, bot(0.30) + 0.03, side * 0.018),
                   P(0.26, -0.15, side * 0.015)], 0.006, 0.003, per_seg=4)


def build_organs(viscera, bladder):
    # 腸・胃（腹腔の下半分）
    viscera.ellipsoid(P(0.45, axis_z(0.45) - 0.10), 0.13, half_width(0.45) * 0.55, 0.065)
    viscera.ellipsoid(P(0.36, axis_z(0.36) - 0.085), 0.07, half_width(0.36) * 0.5, 0.055)
    # 浮き袋（脊柱のすぐ下）
    bladder.ellipsoid(P(0.47, axis_z(0.47) - 0.035), 0.13, 0.025, 0.028, seg=24, rings=12)


def build_skull(bone, plates, cart, eye, lens):
    E = (0.12, 0.06)
    R = 0.055

    # 神経頭蓋の屋根（前頭骨）と上後頭骨稜
    bone.bone([P(t, top(t) - 0.012) for t in (0.03, 0.08, 0.14, 0.20, 0.26, 0.30)], 0.010, 0.007,
              per_seg=5, sides=10)
    plates.plate([(0.16, top(0.16) - 0.01), (0.22, top(0.22) - 0.004), (0.30, top(0.30) - 0.01),
                (0.30, 0.12), (0.22, 0.10), (0.16, 0.11)], 0.0, 0.006)
    # 脳函（眼窩の後ろ〜第1椎骨）
    plates.plate([(0.17, 0.11), (0.28, 0.10), (0.29, 0.05), (0.28, axis_z(0.28)), (0.18, 0.02), (0.16, 0.06)],
               0.0, 0.035)
    # 副蝶形骨（眼窩の下を通る梁）
    bone.bone([P(0.05, 0.02), P(0.12, -0.005), P(0.20, 0.01), P(0.285, axis_z(0.285) - 0.01)],
              0.0065, 0.005, per_seg=6)
    # 篩骨・鼻骨
    plates.plate([(0.03, 0.02), (0.07, 0.03), (0.075, 0.075), (0.045, 0.06)], 0.0, 0.012)

    # 眼窩縁（下側の涙骨・眼下骨は太め）
    ring = []
    for k in range(33):
        a = 2 * math.pi * k / 32
        ring.append((P(E[0] + (R + 0.008) * math.cos(a), E[1] + (R + 0.008) * math.sin(a)), a))
    for side in (1, -1):
        pts = [p + Vector((0, side * 0.032, 0)) for p, _ in ring]
        radii = [0.004 + 0.0045 * max(0.0, -math.sin(a)) for _, a in ring]
        bone.tube(pts, radii, 8)
        eye.ellipsoid(P(E[0], E[1], side * 0.028), 0.047, 0.03, 0.047, seg=20, rings=12)
        lens.ellipsoid(P(E[0], E[1], side * 0.04), 0.017, 0.017, 0.017, seg=16, rings=10)

    # 前上顎骨（上方突起が長く、口を前下方へ突出できる）
    for side in (1, -1):
        y = side * 0.008
        bone.bone([P(0.005, -0.035, y), P(0.03, 0.02, y), P(0.06, 0.06, y)], 0.0055, 0.003, per_seg=5)
        bone.bone([P(0.005, -0.035, y), P(0.035, -0.06, y * 2), P(0.065, -0.07, y * 3)], 0.0055, 0.003, per_seg=5)
        # 上顎骨
        bone.bone([P(0.02, 0.01, side * 0.02), P(0.05, -0.03, side * 0.022), P(0.075, -0.07, side * 0.025)],
                  0.007, 0.004, per_seg=5)
    # 歯骨（下顎）と角骨・方骨
    plates.plate([(0.0, -0.045), (0.06, -0.065), (0.11, -0.075), (0.13, -0.105), (0.10, -0.11),
                (0.04, -0.075), (0.005, -0.055)], 0.02, 0.006, mirror=True)
    plates.plate([(0.11, -0.07), (0.15, -0.06), (0.17, -0.10), (0.13, -0.11)], 0.03, 0.006, mirror=True)
    # 舌顎骨
    bone.bone([P(0.19, 0.07, 0.035), P(0.185, 0.0, 0.036), P(0.175, -0.07, 0.035)], 0.008, 0.005,
              per_seg=5, mirror=True)
    # 前鰓蓋骨（L字）
    bone.bone([P(0.20, 0.08, 0.05), P(0.205, 0.0, 0.052), P(0.21, -0.08, 0.052), P(0.195, -0.115, 0.05),
               P(0.16, -0.125, 0.045), P(0.13, -0.12, 0.04)], 0.007, 0.004, per_seg=6, mirror=True)
    # 主鰓蓋骨・下鰓蓋骨・間鰓蓋骨
    plates.plate([(0.21, 0.08), (0.25, 0.075), (0.285, 0.03), (0.29, -0.01), (0.26, -0.04), (0.22, -0.06),
                (0.21, 0.0)], 0.056, 0.004, mirror=True)
    plates.plate([(0.22, -0.06), (0.26, -0.045), (0.285, -0.06), (0.25, -0.10), (0.21, -0.10)],
               0.054, 0.004, mirror=True)
    plates.plate([(0.14, -0.12), (0.20, -0.10), (0.22, -0.11), (0.18, -0.14), (0.14, -0.135)],
               0.046, 0.004, mirror=True)

    # 角舌骨と鰓条骨（喉の下で後方へ扇状に広がる）
    bone.bone([P(0.10, -0.11, 0.022), P(0.155, -0.135, 0.028), P(0.21, -0.15, 0.03)], 0.008, 0.006,
              per_seg=5, mirror=True)
    nb = SPECIES["branchiostegal_rays"]
    for k in range(nb):
        f = k / (nb - 1)
        s = P(0.12 + 0.08 * f, -0.128 - 0.02 * f, 0.03 + 0.004 * k)
        e_t = 0.235 + 0.01 * k
        bone.bone([s, P((s.x + 0.5 + e_t) / 2, bot((s.x + 0.5 + e_t) / 2) + 0.012, 0.035 + 0.005 * k),
                   P(e_t, bot(e_t) + 0.02 + 0.012 * k, 0.04 + 0.005 * k)], 0.0035, 0.0015, per_seg=5, mirror=True)

    # 鰓弓と鰓耙（軟骨質＝青）、舌骨の軟骨
    for k in range(4):
        pts = [P(0.13 + 0.02 * k, -0.115), P(0.18 + 0.02 * k, -0.06), P(0.195 + 0.018 * k, 0.0),
               P(0.19 + 0.015 * k, 0.045)]
        for side in (1, -1):
            arc = cart.bone([p + Vector((0, side * (0.02 + 0.004 * k), 0)) for p in pts], 0.006, 0.004, per_seg=6)
            for j in range(2, len(arc) - 2, 2):
                p = arc[j]
                cart.bone([p, p + Vector((-0.016, side * -0.004, 0.004))], 0.0018, 0.0006, per_seg=2)
    cart.ellipsoid(P(0.14, -0.105), 0.06, 0.025, 0.034)
    # 下顎内側のメッケル軟骨・眼窩下の軟骨
    cart.bone([P(0.01, -0.05, 0.012), P(0.06, -0.068, 0.016), P(0.12, -0.085, 0.022)], 0.005, 0.004,
              per_seg=5, mirror=True)
    cart.bone([P(0.07, 0.0, 0.03), P(0.12, -0.012, 0.032), P(0.17, 0.0, 0.034)], 0.005, 0.003,
              per_seg=5, mirror=True)

    # 肩帯：後側頭骨 → 上擬鎖骨 → 擬鎖骨（鰓蓋の後縁を上から喉まで）
    bone.bone([P(0.24, top(0.24) - 0.02, 0.04), P(0.28, 0.14, 0.048)], 0.006, 0.005, per_seg=3, mirror=True)
    bone.bone([P(0.28, 0.14, 0.048), P(0.29, 0.08, 0.05)], 0.007, 0.007, per_seg=3, mirror=True)
    bone.bone([P(0.29, 0.09, 0.05), P(0.305, 0.02, 0.055), P(0.29, -0.06, 0.055), P(0.25, -0.14, 0.045),
               P(0.20, -0.18, 0.03)], 0.011, 0.006, per_seg=6, sides=10, mirror=True)
    bone.bone([P(0.30, -0.02, 0.055), P(0.34, -0.10, 0.05), P(0.35, -0.15, 0.045)], 0.0045, 0.0015,
              per_seg=5, mirror=True)
    plates.plate([(0.29, -0.02), (0.32, -0.03), (0.32, -0.06), (0.29, -0.07)], 0.056, 0.005, mirror=True)


# ------------------------------------------------------------------
# 表示の調整（Blender の画面が開いているときだけ）
# ------------------------------------------------------------------
def frame_viewports():
    if bpy.app.background:
        return
    from mathutils import Euler
    sl = SPECIES["standard_length"]
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type != "VIEW_3D":
                continue
            space = area.spaces.active
            space.shading.type = "MATERIAL"
            space.clip_start = 0.001
            r3d = space.region_3d
            r3d.view_perspective = "PERSP"
            r3d.view_location = (0.1 * sl, 0.0, 0.02 * sl)
            r3d.view_rotation = Euler((math.radians(82), 0.0, math.radians(-12))).to_quaternion()
            r3d.view_distance = sl * 2.2


def main():
    clear_previous()
    hide_default_cube()

    coll = bpy.data.collections.new(SPECIES["name"])
    bpy.context.scene.collection.children.link(coll)
    root = bpy.data.objects.new(SPECIES["name"] + "_Root", None)
    root.empty_display_size = 0.5
    sl = SPECIES["standard_length"]
    root.scale = (sl, sl, sl)
    coll.objects.link(root)

    mats = build_materials()
    configure_volume_rendering()

    skull, skull_plates, skull_cart, eyes, lenses = (MeshBuilder() for _ in range(5))
    build_skull(skull, skull_plates, skull_cart, eyes, lenses)
    emit("Skull", skull, mats["bone"], coll, root)
    emit("Skull_Plates", skull_plates, mats["bone_plate"], coll, root)
    emit("GillArches", skull_cart, mats["cartilage"], coll, root)
    emit("Eyes", eyes, mats["eye"], coll, root)
    emit("EyeLenses", lenses, mats["lens"], coll, root)

    viscera, bladder = MeshBuilder(), MeshBuilder()
    build_organs(viscera, bladder)
    emit("Viscera", viscera, mats["viscera"], coll, root)
    emit("SwimBladder", bladder, mats["swim_bladder"], coll, root)

    axial = MeshBuilder()
    build_axial(axial)
    emit("AxialSkeleton", axial, mats["bone"], coll, root)

    for name, builder in (("DorsalFin", build_dorsal_fin), ("AnalFin", build_anal_fin),
                          ("CaudalFin", build_caudal_fin), ("PairedFins", build_paired_fins)):
        rays, membrane = MeshBuilder(), MeshBuilder()
        builder(rays, membrane)
        emit(name, rays, mats["bone"], coll, root)
        emit(name + "_Membrane", membrane, mats["membrane"], coll, root, smooth=False)

    emit("Body_Shell", build_body_shell(), mats["flesh"], coll, root)

    frame_viewports()
    print(f"[{SPECIES['name']}] 生成完了: コレクション '{SPECIES['name']}' を確認してください。")


main()

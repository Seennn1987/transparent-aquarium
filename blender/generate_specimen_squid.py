"""
透明標本ケース（specimen）用のイカを .glb に書き出すスクリプト
Blender 5.2 LTS で動作確認済み。

使い方（ターミナル）:
  blender --background --factory-startup --python generate_specimen_squid.py -- <出力 .glb のパス>

水槽のイカ（generate_squid.py → rig_squid.py → animate_squid.py → export_squid_gltf.py）を
ファイルは変えずに読み込み、寄りで見る標本に必要な形だけを差し替えて書き出す。水槽の squid.glb は変わらない。
  - 眼: 水晶体（眼の中の玉）と、染まった眼の軟骨の濃い青の三日月形の輪（部位 EyeRings）
  - エンペラ: 縁を薄く波打たせ、縁の濃い縁取りの位置を _rim（縁1 → 付け根0）として焼き込む
  - 軟甲: 中央の軸を細い線として見える太さ・色の別部位に（部位 Rachis）
  - 内臓: 消化腺・盲嚢・生殖巣を、くびれと凹凸のある形に
焼き込む値は export_squid_gltf.py と同じ（色 COLOR_0 と _depth）に、全部位の _rim を加える。
"""

import math
import os
import sys
from mathutils import Vector

BLENDER_DIR = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
if not os.path.isdir(BLENDER_DIR):
    raise FileNotFoundError(f"イカのスクリプトのフォルダが見つかりません: {BLENDER_DIR}")


def stage(name, strip):
    """元のスクリプトから、前の段を読み込む行と最後の実行の行を外した本文を返す"""
    text = open(os.path.join(BLENDER_DIR, name), encoding="utf-8").read()
    for line in strip:
        if text.count(line) != 1:
            raise RuntimeError(f"{name} に「{line.strip()}」が1回だけあることを前提にしています")
        text = text.replace(line, "\n")
    return text


def chained(previous):
    return f'\nexec(open(os.path.join(BLENDER_DIR, "{previous}"), encoding="utf-8").read(), globals())\n'


exec(stage("generate_squid.py", ["\nmain()\n"]), globals())

# ------------------------------------------------------------------
# 形の差し替え（寸法は generate_squid.py と同じ ML=1 単位）
# ------------------------------------------------------------------
LENS_RADIUS = 0.45 * EYE_RADIUS
EYE_RING_THICKNESS = 0.008            # 三日月の一番太い所の半径
EYE_RING_TILT = math.radians(18)      # 水晶体を外側・腹側へ少しずらす
COLOR_EYE_RING = (0.08, 0.40, 0.81, 1.0)
COLOR_RACHIS = (0.55, 0.55, 0.25, 1.0)
RACHIS_RADIUS = 0.003
FIN_RIM_FROM = 0.8                    # 付け根0 → 縁1 のうち、縁取りが始まる位置


def build_eyes(eye_mb, ring_mb=None):
    ex, ey, ez = EYE_CENTER
    for side in (1, -1):
        c = Vector((ex, side * ey, ez))
        facing = Vector((0, side * math.cos(EYE_RING_TILT), -math.sin(EYE_RING_TILT)))
        along, up = Vector((1, 0, 0)), Vector((0, 0, 1))
        eye_mb.ellipsoid(c, EYE_RADIUS, EYE_RADIUS * 0.9, EYE_RADIUS * 0.92, seg=28, rings=16)
        eye_mb.ellipsoid(c + facing * (0.35 * EYE_RADIUS), LENS_RADIUS, LENS_RADIUS, LENS_RADIUS, seg=18, rings=10)
        if ring_mb is None:
            continue
        n = 28
        pts, radii = [], []
        for i in range(n):
            a = 2 * math.pi * i / n
            # In the plane facing the viewer from the back (along × up), so the stain
            # reads as a ring around the eye, thicker toward the outside.
            pts.append(c + (along * math.sin(a) + up * math.cos(a)) * EYE_RADIUS * 1.01)
            radii.append(0.0028 + EYE_RING_THICKNESS * max(-math.cos(a), 0.0) ** 1.2)
        ring_mb.tube(pts, radii, 10, closed=True)
        ring_mb.attrs.setdefault("radius", []).extend(r for r in radii for _ in range(10))


def build_fins(fin_mb):
    nu, nv = 60, 16
    for side in (1, -1):
        top, bot, thick = [], [], []
        for i in range(nu + 1):
            q = i / nu
            u = FIN_START + (FIN_END - 0.005 - FIN_START) * q
            r = mantle_r(u)
            y0, z0 = r * 0.78, r * MANTLE_FLATTEN * 0.5
            w = fin_width(q)
            end_taper = min(1.0, w / 0.05)
            # 縁ほど大きく、前後に細かく波打つ（面の外へのうねりと、縁の出入り）
            ripple = math.sin(2 * math.pi * 6 * q + 0.4) * end_taper
            scallop = 1 + 0.035 * math.sin(2 * math.pi * 9 * q + 1.1) * end_taper
            row_t, row_b, thick_row = [], [], []
            for j in range(nv + 1):
                v = j / nv
                th = FIN_BASE_THICKNESS * end_taper * (1 - v) ** 1.6 + 0.0006
                z = z0 * (1 - v) - 0.012 * v + 0.010 * ripple * v ** 2.5
                y = side * (y0 + (w + r * 0.22) * v * (1 + (scallop - 1) * v * v))
                row_t.append((u, y, z + th / 2))
                row_b.append((u, y, z - th / 2))
                thick_row.append(th / FIN_BASE_THICKNESS)
            top.append(row_t)
            bot.append(row_b)
            thick.append(thick_row)
        fin_mb.sheet(top, bot)
        flat = [t for row in thick for t in row]
        grid_q = [i / nu for i in range(nu + 1) for _ in range(nv + 1)]
        grid_v = [j / nv for _ in range(nu + 1) for j in range(nv + 1)]
        rim = [max(v - FIN_RIM_FROM, 0.0) / (1 - FIN_RIM_FROM) for v in grid_v]
        fin_mb.attrs.setdefault("thickness", []).extend(flat + flat)
        fin_mb.attrs.setdefault("fin_q", []).extend(grid_q + grid_q)
        fin_mb.attrs.setdefault("fin_v", []).extend(grid_v + grid_v)
        fin_mb.attrs.setdefault("rim", []).extend(rim + rim)


def lumpy(mb, c, rx, ry, rz, shape, seg=28, rings=24):
    """X方向に長い楕円体を、shape(t, 周りの角度)（t: 前0→後1）倍に膨らませた袋（くびれ・凹凸）"""
    base = len(mb.verts)
    for i in range(1, rings):
        th = math.pi * i / rings
        t = i / rings
        for k in range(seg):
            ph = 2 * math.pi * k / seg
            f = shape(t, ph)
            mb.verts.append(Vector((c.x - rx * math.cos(th),
                                    c.y + ry * math.sin(th) * math.cos(ph) * f,
                                    c.z + rz * math.sin(th) * math.sin(ph) * f)))
    front = len(mb.verts)
    mb.verts.append(Vector((c.x - rx, c.y, c.z)))
    back = len(mb.verts)
    mb.verts.append(Vector((c.x + rx, c.y, c.z)))
    for i in range(rings - 2):
        for k in range(seg):
            a = base + i * seg + k
            b = base + i * seg + (k + 1) % seg
            mb.faces.append((a, b, b + seg, a + seg))
    last = base + (rings - 2) * seg
    for k in range(seg):
        mb.faces.append((front, base + (k + 1) % seg, base + k))
        mb.faces.append((back, last + k, last + (k + 1) % seg))


def pinch(t, at, depth, width):
    return 1 - depth * math.exp(-((t - at) / width) ** 2)


def build_viscera(mats_mb):
    dig, cae, gon, ink, gladius, gill, rachis_mb = (mats_mb[k] for k in (
        "digestive", "caecum", "gonad", "ink", "gladius", "gill", "rachis"))
    # 消化腺: 2か所でくびれた、表面のなだらかな凸凹のある細長い袋
    lumpy(dig, Vector((0.40, 0, -0.005)), 0.30, 0.055, 0.05,
          lambda t, ph: pinch(t, 0.34, 0.22, 0.06) * pinch(t, 0.7, 0.18, 0.05)
          * (1 + 0.05 * math.sin(7 * math.pi * t + 3 * ph) * math.sin(2 * ph + 1)))
    # 盲嚢: 前後に並ぶ小さなふくらみ
    lumpy(cae, Vector((0.74, 0, -0.01)), 0.13, 0.032, 0.026,
          lambda t, ph: 1 + 0.12 * math.sin(2 * math.pi * 4 * t) + 0.04 * math.sin(3 * ph), seg=22, rings=20)
    # 生殖巣: 房のように分かれた凹凸
    lumpy(gon, Vector((0.86, 0, 0.0)), 0.07, 0.02, 0.016,
          lambda t, ph: 1 + 0.15 * math.sin(3 * ph + 12 * t) * math.sin(math.pi * t), seg=20, rings=14)
    ink.ellipsoid(Vector((0.14, 0, -0.035)), 0.04, 0.012, 0.011, seg=16, rings=10)
    ink.tube(chain([Vector((0.11, 0, -0.04)), Vector((0.05, 0, -0.05)), Vector((0.0, 0, -0.058))], 5),
             taper(11, 0.006, 0.004), 8)

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
    rachis_mb.tube(rachis, taper(len(rachis), RACHIS_RADIUS, 0.0012), 8)

    for side in (1, -1):
        a = Vector((0.04, side * 0.072, -0.035))
        b = Vector((0.36, side * 0.052, -0.042))
        gill.tube([a.lerp(b, i / 10) for i in range(11)], taper(11, 0.006, 0.003), 8)
        for k in range(26):
            f = (k + 0.5) / 26
            c = a.lerp(b, f)
            h = 0.02 * math.sin(math.pi * (0.15 + 0.85 * f)) + 0.004
            gill.ellipsoid(c, 0.0035, h, h * 0.8, seg=10, rings=6)


def build_specimen_extras():
    """main() が作らない部位（眼の輪・軟甲の軸）を足す。軸は build_viscera の中で作る"""
    coll = bpy.data.collections[SPECIES["name"]]
    root = bpy.data.objects[SPECIES["name"] + "_Root"]
    rings = MeshBuilder()
    build_eyes(MeshBuilder(), rings)
    ring_mat = make_glossy_material("EyeRing", COLOR_EYE_RING, roughness=0.3, alpha=0.6, coat=0.3)
    emit("EyeRings", rings, ring_mat, coll, root)


_build_viscera = build_viscera


def build_viscera_with_rachis(mats_mb):
    mats_mb["rachis"] = MeshBuilder()
    _build_viscera(mats_mb)
    coll = bpy.data.collections[SPECIES["name"]]
    root = bpy.data.objects[SPECIES["name"] + "_Root"]
    emit("Rachis", mats_mb.pop("rachis"),
         make_glossy_material("Rachis", COLOR_RACHIS, roughness=0.5, alpha=0.4, coat=0.0), coll, root)


build_viscera = build_viscera_with_rachis
main()
build_specimen_extras()

exec(stage("rig_squid.py", [chained("generate_squid.py"), "\nrig_squid()\n"]), globals())
HEAD_PARTS = HEAD_PARTS + ("EyeRings",)
MANTLE_PARTS = MANTLE_PARTS + ("Rachis",)
rig_squid()

exec(stage("animate_squid.py", [chained("rig_squid.py")]), globals())

exec(stage("export_squid_gltf.py", [chained("animate_squid.py"), "\nmain_export()\n"]), globals())
ORGAN_DEPTH["Rachis"] = RACHIS_RADIUS
_tint_of, _depth_values, _bake_attributes = tint_of, depth_values, bake_attributes


def tint_of(name, co):
    if name == "EyeRings":
        return tuple(COLOR_EYE_RING[:3])
    if name == "Rachis":
        return tuple(COLOR_RACHIS[:3])
    return _tint_of(name, co)


def depth_values(name, me, limb_lines):
    if name == "EyeRings":
        return [a.value for a in me.attributes["radius"].data]
    return _depth_values(name, me, limb_lines)


def bake_attributes(parts):
    _bake_attributes(parts)
    for name, obj in parts.items():
        if obj.type != "MESH":
            continue
        me = obj.data
        if "_rim" in me.attributes:
            me.attributes.remove(me.attributes["_rim"])
        rim = [a.value for a in me.attributes["rim"].data] if name == "Fins" else [0.0] * len(me.vertices)
        me.attributes.new("_rim", "FLOAT", "POINT").data.foreach_set("value", rim)


main_export()

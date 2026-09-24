"""透明標本ケース（SPECIMEN-JAR-001）のガラス瓶・蓋・保存液を生成して .glb に書き出す。

使い方:
  blender --background --python generate_specimen_jar.py -- <出力 .glb のパス>

形は断面（半径, 高さ）を Z 軸まわりに回した回転体。単位はメートル相当で、
床が z=0。ブラウザ側では部位名（Jar_Glass / Jar_Lid / Jar_Liquid / Jar_Meniscus）で材質を付ける。
"""

import math
import os
import sys

import bmesh
import bpy

SEGMENTS = 128

# 胴
OUTER_R = 0.62
WALL = 0.035
BASE = 0.14          # 底の厚み（参考画像の厚いガラス底）
BODY_H = 2.30
LIP_H = 0.05         # 口の少し厚い縁
CORNER = 0.05        # 底の外周の丸み

# 蓋
LID_R = OUTER_R + 0.02
LID_T = 0.07
LID_PLUG = 0.10      # 口に差し込む栓の深さ
KNOB_NECK_R = 0.07
KNOB_NECK_H = 0.10
KNOB_R = 0.15

# 液
FILL = 0.90          # 内側の高さに対する液の割合
LIQUID_GAP = 0.004   # 内壁との隙間（面の重なりのちらつき防止）
MENISCUS = 0.018     # 壁際の液面の盛り上がり


def arc(cx, cz, r, a0, a1, steps):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / steps),
             cz + r * math.sin(a0 + (a1 - a0) * i / steps)) for i in range(steps + 1)]


def jar_profile():
    """外側の底中心 → 外壁 → 口 → 内壁 → 内底中心 の順の断面。"""
    inner_r = OUTER_R - WALL
    pts = [(0.0, 0.0)]
    pts += arc(OUTER_R - CORNER, CORNER, CORNER, -math.pi / 2, 0, 8)
    pts += [(OUTER_R, BODY_H - LIP_H), (OUTER_R + 0.006, BODY_H - LIP_H * 0.5)]
    pts += arc(OUTER_R - 0.012, BODY_H - 0.012, 0.012 + 0.006, 0, math.pi / 2, 5)
    pts += arc(inner_r + 0.012, BODY_H - 0.012, 0.012, math.pi / 2, math.pi, 5)
    pts += [(inner_r, BASE + 0.03)]
    pts += arc(inner_r - 0.03, BASE + 0.03, 0.03, 0, -math.pi / 2, 6)
    pts += [(0.0, BASE)]
    return pts


def lid_profile():
    """栓の下面中心 → 栓の側面 → 鍔 → 上面 → 首 → つまみの球 → 頂点。"""
    inner_r = OUTER_R - WALL
    z0 = BODY_H - LID_PLUG
    plug_r = inner_r - 0.006
    top = BODY_H + LID_T
    pts = [(0.0, z0), (plug_r - 0.015, z0)]
    pts += arc(plug_r - 0.015, z0 + 0.015, 0.015, -math.pi / 2, 0, 4)
    pts += [(plug_r, BODY_H + 0.002)]
    pts += [(LID_R - 0.02, BODY_H + 0.002)]
    pts += arc(LID_R - 0.02, BODY_H + 0.022, 0.02, -math.pi / 2, 0, 4)
    pts += arc(LID_R - 0.025, top - 0.025, 0.025, 0, math.pi / 2, 5)
    pts += [(KNOB_NECK_R + 0.04, top)]
    pts += arc(KNOB_NECK_R + 0.04, top + 0.04, 0.04, -math.pi / 2, -math.pi, 5)
    neck_top = top + KNOB_NECK_H
    pts += [(KNOB_NECK_R, neck_top - 0.02)]
    center_z = neck_top + math.sqrt(max(KNOB_R ** 2 - KNOB_NECK_R ** 2, 0.0))
    start = math.atan2(neck_top - center_z, KNOB_NECK_R)
    pts += arc(0.0, center_z, KNOB_R, start, math.pi / 2, 20)
    pts[-1] = (0.0, center_z + KNOB_R)
    return pts


def liquid_profile():
    inner_r = OUTER_R - WALL - LIQUID_GAP
    bottom = BASE + LIQUID_GAP
    surface = BASE + (BODY_H - BASE) * FILL
    pts = [(0.0, bottom)]
    pts += arc(inner_r - 0.03, bottom + 0.03, 0.03, -math.pi / 2, 0, 6)
    pts += [(inner_r, surface + MENISCUS)]
    # 壁際だけ持ち上がる液面（毛細管現象のふち）
    for i in range(1, 9):
        t = i / 8
        r = inner_r - 0.06 * t
        pts.append((r, surface + MENISCUS * (1 - t) ** 2.2))
    pts += [(0.0, surface)]
    return pts, surface


def revolve(name, profile):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1),
                   angle=math.tau, steps=SEGMENTS, use_duplicate=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    for f in bm.faces:
        f.smooth = True
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    obj["jar_part"] = name
    return obj


def meniscus_ring(surface):
    """液面と壁の境目に光る細い輪（参考画像の液面の線）。"""
    inner_r = OUTER_R - WALL - LIQUID_GAP * 0.5
    pts = [(inner_r - 0.07, surface + 0.0005)]
    for i in range(1, 9):
        t = i / 8
        pts.append((inner_r - 0.07 * (1 - t), surface + MENISCUS * t ** 2.2 + 0.0015))
    return revolve("Jar_Meniscus", pts)


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    revolve("Jar_Glass", jar_profile())
    revolve("Jar_Lid", lid_profile())
    _, surface = liquid_profile()
    revolve("Jar_Liquid", liquid_profile()[0])
    meniscus_ring(surface)
    return surface


def export(path):
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        export_yup=True,
        export_materials="NONE",
        export_extras=True,
        export_normals=True,
        export_animations=False,
        export_cameras=False,
        export_lights=False,
    )


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 1:
        raise ValueError("使い方: -- <出力 .glb のパス>")
    path = os.path.abspath(argv[0])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    surface = build()
    export(path)
    tris = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    print(f"[SpecimenJar] 書き出し完了: {path} ({os.path.getsize(path) / 1e6:.2f} MB), "
          f"面 {tris}, 液面の高さ {surface:.3f}")


main()

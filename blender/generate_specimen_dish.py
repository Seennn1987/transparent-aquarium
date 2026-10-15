"""シロシュモクザメの器（蓋の無い低い円柱、C1。2026-10-15、プロデューサー「まずは前の台だけを替えられるようにしてください（?specimen=hammerhead で、前の台をシュモクザメと低い円柱の器にし、後ろの台はいまの液だけの瓶のまま）。」）

使い方:
  blender --background --python generate_specimen_dish.py -- <出力 .glb のパス>

イカの瓶（generate_specimen_jar.py）と同じ作り方の回転体で、単位も同じ（床が z = 0）。ガラスの肉厚（WALL 0.045）、台座の作り方、液の縁の
メニスカスは瓶から持ってくる。蓋は無く、液面は上に開いている。
  台座: 胴より少し広い薄い円盤 → 内側へ反って胴へ
  胴:   低い円筒。底は厚い無垢のガラス
寸法（2026-10-15 決定: この形のまま、サメを半分に描いて、直径も高さもサメに対して C1 の 2 倍。プロデューサー「2倍、高さも2倍」）。もとの決め方: 胴の半径 1.0（前の台の八角の台、半径 1.15 に載る）。液の深さは、サメ（体高 0.193 m、背びれまで）を
  器の半径に合わせた縮尺（吻端〜尾が壁から 0.12 離れる、約 1.6 倍）で入れて、底と液面からも 0.12 空く深さ（0.555）
部位名・寸法の値は瓶と同じ（Jar_Glass / Jar_Liquid / Jar_Meniscus、jar_*）。jar_lid_profile は空（蓋なし）。
"""

import math
import os
import sys

import bmesh
import bpy

SEGMENTS = 200

BODY_R = 1.0
WALL = 0.045           # 瓶と同じ
FLOOR_Z = 0.12         # 内側の底（その下は無垢の厚いガラス）
FOOT_R = 1.06
FOOT_DISC = 0.06
FOOT_ROUND = 0.025
# 高さ（2026-10-15 プロデューサー「瓶の高さが変わっていません。瓶の高さをまず2倍にして」）: 全高（口）を 0.725 から 2 倍の 1.45 に。
#  底の厚み 0.12 と、液面から口までの 0.05 はそのまま。液の深さは 0.555 → 1.28
RIM_Z = 2 * 0.725
LIQUID_TOP = RIM_Z - 0.05
LIQUID_GAP = 0.004
MENISCUS = 0.018


def arc(cx, cz, r, a0, a1, steps):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / steps),
             cz + r * math.sin(a0 + (a1 - a0) * i / steps)) for i in range(steps + 1)]


def cove(p0, p1, steps):
    (r0, z0), (r1, z1) = p0, p1
    return [(r0 + (r1 - r0) * math.sin(i / steps * math.pi / 2), z0 + (z1 - z0) * i / steps)
            for i in range(1, steps + 1)]


def base_outline():
    pts = [(0.0, 0.0)]
    pts += arc(FOOT_R - FOOT_ROUND, FOOT_ROUND, FOOT_ROUND, -math.pi / 2, 0, 12)
    pts += arc(FOOT_R - FOOT_ROUND, FOOT_DISC - FOOT_ROUND, FOOT_ROUND, 0, math.pi / 2, 12)
    pts += cove((FOOT_R - FOOT_ROUND, FOOT_DISC), (BODY_R, FLOOR_Z), 20)
    return pts


def base_profile():
    return base_outline() + [(0.0, FLOOR_Z)]


def dish_profile():
    inner_r = BODY_R - WALL
    pts = base_outline()
    pts += [(BODY_R, RIM_Z - 0.02)]
    pts += arc(BODY_R - 0.012, RIM_Z - 0.012, 0.012, 0, math.pi / 2, 5)            # 丸めた口の縁
    pts += arc(inner_r + 0.012, RIM_Z - 0.012, 0.012, math.pi / 2, math.pi, 5)
    pts += arc(inner_r - 0.05, FLOOR_Z + 0.05, 0.05, 0, -math.pi / 2, 8)
    pts += [(0.0, FLOOR_Z)]
    return pts


def liquid_profile():
    inner_r = BODY_R - WALL - LIQUID_GAP
    bottom = FLOOR_Z + LIQUID_GAP
    pts = [(0.0, bottom)]
    pts += arc(inner_r - 0.05, bottom + 0.05, 0.05, -math.pi / 2, 0, 8)
    pts += [(inner_r, LIQUID_TOP + MENISCUS)]
    for i in range(1, 9):
        t = i / 8
        pts.append((inner_r - 0.06 * t, LIQUID_TOP + MENISCUS * (1 - t) ** 2.2))
    pts += [(0.0, LIQUID_TOP)]
    return pts


def meniscus_profile():
    inner_r = BODY_R - WALL - LIQUID_GAP * 0.5
    pts = [(inner_r - 0.07, LIQUID_TOP + 0.0005)]
    for i in range(1, 9):
        t = i / 8
        pts.append((inner_r - 0.07 * (1 - t), LIQUID_TOP + MENISCUS * t ** 2.2 + 0.0015))
    return pts


def revolve(name, profile):
    mesh = bpy.data.meshes.new(name)
    bm = bmesh.new()
    verts = [bm.verts.new((r, 0.0, z)) for r, z in profile]
    edges = [bm.edges.new((verts[i], verts[i + 1])) for i in range(len(verts) - 1)]
    bmesh.ops.spin(bm, geom=verts + edges, cent=(0, 0, 0), axis=(0, 0, 1), angle=math.tau, steps=SEGMENTS, use_duplicate=False)
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


def check_profile(name, pts):
    for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
        if math.hypot(r1 - r0, z1 - z0) < 1e-5:
            raise RuntimeError(f"{name}: 同じ位置の点が連続しています ({r0:.4f}, {z0:.4f})")
    if any(r < -1e-9 for r, _ in pts):
        raise RuntimeError(f"{name}: 半径が負の点があります")


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    profiles = {"Jar_Glass": dish_profile(), "Jar_Liquid": liquid_profile(), "Jar_Meniscus": meniscus_profile()}
    for name, pts in profiles.items():
        check_profile(name, pts)
    check_profile("base", base_profile())
    objects = {name: revolve(name, pts) for name, pts in profiles.items()}
    glass = objects["Jar_Glass"]
    glass["jar_vessel"] = "dish"
    glass["jar_knob_centre"] = RIM_Z
    glass["jar_knob_radius"] = 0.0
    glass["jar_body_radius"] = BODY_R
    glass["jar_inner_radius"] = BODY_R - WALL
    glass["jar_foot_radius"] = FOOT_R
    glass["jar_rim_height"] = RIM_Z
    glass["jar_floor_height"] = FLOOR_Z
    glass["jar_liquid_top"] = LIQUID_TOP
    glass["jar_lid_profile"] = []
    glass["jar_base_profile"] = [v for r, z in base_profile() for v in (r, z)]


def export(path):
    bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True, export_materials="NONE", export_extras=True,
                              export_normals=True, export_animations=False, export_cameras=False, export_lights=False)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 1:
        raise ValueError("使い方: -- <出力 .glb のパス>")
    path = os.path.abspath(argv[0])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    build()
    export(path)
    faces = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    print(f"[SpecimenDish] 書き出し完了: {path} ({os.path.getsize(path) / 1e6:.2f} MB), 面 {faces}, 口 {RIM_Z:.3f}, 液 {FLOOR_Z:.2f}〜{LIQUID_TOP:.3f}")


main()

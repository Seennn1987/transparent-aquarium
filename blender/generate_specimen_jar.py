"""透明標本ケース（SPECIMEN-JAR-001/002）のガラス瓶・蓋・保存液を生成して .glb に書き出す。

使い方:
  blender --background --python generate_specimen_jar.py -- <出力 .glb のパス>

形は参考の鳥の透明標本の瓶に合わせた回転体（断面を Z 軸まわりに回す）。単位はメートル相当で床が z=0。
  台座: 胴より広い厚い2段の円盤 → 内側へ反る首 → 玉縁 → 胴
  胴:   真っすぐな円筒（高さは直径の約1.6倍）。底は厚い無垢のガラス
  蓋:   口に差し込む栓 → 胴より少し張り出した丸縁の鍔 → 中空のドーム → 首 → 玉のつまみ
ブラウザ側は部位名（Jar_Glass / Jar_Lid / Jar_Liquid / Jar_Meniscus）で材質を付け、
Jar_Glass の jar_* の値（寸法）を影や屈折の計算に使う。
"""

import math
import os
import sys

import bmesh
import bpy

SEGMENTS = 160

# 胴
BODY_R = 0.62
WALL = 0.045
RIM_Z = 2.40          # 口の上端
FLOOR_Z = 0.26        # 内側の底（その下は無垢の厚いガラス）

# 台座
FOOT_R = 0.73         # 胴の約1.18倍
FOOT_DISC = 0.075     # 一番下の円盤の厚み
FOOT_STEP = 0.045     # 2段目の厚み
BEAD_Z = 0.33         # 胴との境目の玉縁の高さ
BEAD_R = BODY_R + 0.018

# 蓋
PLUG_DEPTH = 0.10
PLUG_WALL = 0.035
FLANGE_R = BODY_R + 0.035
FLANGE_T = 0.06
DOME_TOP_Z = RIM_Z + 0.36
DOME_SHELL = 0.04
NECK_R = 0.06
NECK_H = 0.05
KNOB_R = 0.17
KNOB_CENTRE_Z = DOME_TOP_Z + NECK_H + math.sqrt(KNOB_R ** 2 - NECK_R ** 2)
LID_LIFT = 0.003

# 液
LIQUID_TOP = RIM_Z - PLUG_DEPTH - 0.03
LIQUID_GAP = 0.004
MENISCUS = 0.018


def arc(cx, cz, r, a0, a1, steps):
    return [(cx + r * math.cos(a0 + (a1 - a0) * i / steps),
             cz + r * math.sin(a0 + (a1 - a0) * i / steps)) for i in range(steps + 1)]


def cove(p0, p1, steps):
    """p0 から p1 へ、最初に内側へ大きく入ってから上へ伸びる凹の曲線（台座の反り）。"""
    (r0, z0), (r1, z1) = p0, p1
    return [(r0 + (r1 - r0) * math.sin(i / steps * math.pi / 2), z0 + (z1 - z0) * i / steps)
            for i in range(1, steps + 1)]


def jar_profile():
    inner_r = BODY_R - WALL
    pts = [(0.0, 0.0)]
    # 一番下の円盤（角は丸く）
    pts += arc(FOOT_R - 0.025, 0.025, 0.025, -math.pi / 2, 0, 6)
    pts += arc(FOOT_R - 0.02, FOOT_DISC - 0.02, 0.02, 0, math.pi / 2, 5)
    # 2段目
    step_r = FOOT_R - 0.045
    pts += [(step_r + 0.01, FOOT_DISC)]
    pts += arc(step_r - 0.015, FOOT_DISC + 0.015, 0.025, -math.pi / 4, math.pi / 2, 5)
    top_step = FOOT_DISC + FOOT_STEP
    # 内側へ反りながら胴へ向かう首（凹の曲線）
    pts += cove((step_r - 0.015, top_step - 0.005), (BODY_R - 0.004, BEAD_Z - 0.02), 14)
    # 玉縁
    pts += arc(BEAD_R - 0.018, BEAD_Z, 0.018, -math.pi / 2, math.pi / 2, 8)
    pts += [(BODY_R, BEAD_Z + 0.03)]
    # 胴 → 口（すり合わせの平らな縁）
    pts += [(BODY_R, RIM_Z - 0.03)]
    pts += arc(BODY_R - 0.012, RIM_Z - 0.012, 0.012, 0, math.pi / 2, 5)
    pts += arc(inner_r + 0.01, RIM_Z - 0.01, 0.01, math.pi / 2, math.pi, 4)
    # 内壁 → 厚い底
    pts += arc(inner_r - 0.05, FLOOR_Z + 0.05, 0.05, 0, -math.pi / 2, 8)
    pts += [(0.0, FLOOR_Z)]
    return pts


def lid_profile():
    """つまみの頂点 → 首 → ドームの外面 → 鍔 → 栓 → 栓の内側 → ドームの内面 → 内側の頂点。"""
    inner_r = BODY_R - WALL
    neck_top = DOME_TOP_Z + NECK_H
    centre = KNOB_CENTRE_Z
    pts = [(0.0, centre + KNOB_R)]
    start = math.atan2(neck_top - centre, NECK_R)
    pts += arc(0.0, centre, KNOB_R, math.pi / 2, start, 22)[1:]
    pts += [(NECK_R, DOME_TOP_Z + 0.01)]
    # ドームの外面: 首の周りは平らに近く、鍔へ向かって肩が落ちる
    flange_top = RIM_Z + FLANGE_T
    r0, r1 = NECK_R + 0.02, FLANGE_R - 0.03
    for i in range(1, 19):
        t = i / 18
        drop = (1 - math.cos(t * math.pi / 2)) ** 1.6
        pts.append((r0 + (r1 - r0) * t, DOME_TOP_Z - (DOME_TOP_Z - flange_top) * drop))
    # 丸く巻いた鍔の縁
    pts += arc(FLANGE_R - 0.03, RIM_Z + FLANGE_T / 2, FLANGE_T / 2, math.pi / 2, -math.pi / 2, 8)[1:]
    # 鍔の下面 → 栓
    plug_r = inner_r - 0.006
    pts += [(plug_r + 0.01, RIM_Z + 0.002)]
    pts += [(plug_r, RIM_Z - 0.01)]
    pts += [(plug_r, RIM_Z - PLUG_DEPTH + 0.012)]
    pts += arc(plug_r - 0.012, RIM_Z - PLUG_DEPTH + 0.012, 0.012, 0, -math.pi / 2, 4)[1:]
    pts += [(plug_r - PLUG_WALL, RIM_Z - PLUG_DEPTH)]
    # 栓の内側を上がり、ドームの内面へ
    pts += [(plug_r - PLUG_WALL, RIM_Z + FLANGE_T - DOME_SHELL)]
    shell_top = DOME_TOP_Z - DOME_SHELL
    inner_dome = []
    for i in range(1, 17):
        t = i / 16
        r = (plug_r - PLUG_WALL) * (1 - t)
        z = (RIM_Z + FLANGE_T - DOME_SHELL) + (shell_top - (RIM_Z + FLANGE_T - DOME_SHELL)) * math.sin(t * math.pi / 2) ** 0.6
        inner_dome.append((r, z))
    pts += inner_dome
    pts[-1] = (0.0, shell_top)
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


def check_profile(name, pts):
    for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
        if math.hypot(r1 - r0, z1 - z0) < 1e-5:
            raise RuntimeError(f"{name}: 同じ位置の点が連続しています ({r0:.4f}, {z0:.4f})")
    if any(r < -1e-9 for r, _ in pts):
        raise RuntimeError(f"{name}: 半径が負の点があります")


def build():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    profiles = {
        "Jar_Glass": jar_profile(),
        "Jar_Lid": lid_profile(),
        "Jar_Liquid": liquid_profile(),
        "Jar_Meniscus": meniscus_profile(),
    }
    for name, pts in profiles.items():
        check_profile(name, pts)
    objects = {name: revolve(name, pts) for name, pts in profiles.items()}
    # 鍔の下面が口の平らな縁と同じ高さにならないよう、蓋をわずかに浮かせる
    objects["Jar_Lid"].location.z = LID_LIFT
    glass = objects["Jar_Glass"]
    glass["jar_knob_centre"] = KNOB_CENTRE_Z + LID_LIFT
    glass["jar_knob_radius"] = KNOB_R
    glass["jar_body_radius"] = BODY_R
    glass["jar_inner_radius"] = BODY_R - WALL
    glass["jar_foot_radius"] = FOOT_R
    glass["jar_rim_height"] = RIM_Z
    glass["jar_floor_height"] = FLOOR_Z
    glass["jar_liquid_top"] = LIQUID_TOP


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
    build()
    export(path)
    faces = sum(len(o.data.polygons) for o in bpy.data.objects if o.type == "MESH")
    top = max(v.co.z for o in bpy.data.objects if o.type == "MESH" for v in o.data.vertices)
    print(f"[SpecimenJar] 書き出し完了: {path} ({os.path.getsize(path) / 1e6:.2f} MB), "
          f"面 {faces}, 全高 {top:.3f}, 液 {FLOOR_Z:.2f}〜{LIQUID_TOP:.2f}")


main()

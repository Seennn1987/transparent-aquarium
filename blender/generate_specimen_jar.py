"""透明標本ケース（SPECIMEN-JAR-001/002）のガラス瓶・蓋・保存液を生成して .glb に書き出す。

使い方:
  blender --background --python generate_specimen_jar.py -- <出力 .glb のパス>

形は参考の鳥の透明標本の瓶に合わせた回転体（断面を Z 軸まわりに回す）。単位はメートル相当で床が z=0。
  台座: 胴より広い1枚の厚い円盤（角は丸い） → 内側へ反りながら胴へつながる
  胴:   真っすぐな円筒（高さは直径の約1.6倍）。底は厚い無垢のガラス
  蓋:   口に差し込む厚い栓 → 胴より少し張り出した垂直の帯 → 丸い肩 → 平らに近い天面 → 首 → 玉のつまみ。
        肉厚 0.1 前後の無垢に近い厚いガラスのキャップ
ブラウザ側は部位名（Jar_Glass / Jar_Lid / Jar_Liquid / Jar_Meniscus）で材質を付け、
Jar_Glass の jar_* の値（寸法と、蓋・台座の断面の点列）を影や屈折の計算に使う。
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
FOOT_R = 0.74         # 胴の約1.2倍
FOOT_DISC = 0.10      # 円盤の厚み
FOOT_ROUND = 0.035    # 円盤の角の丸み

# 蓋
PLUG_DEPTH = 0.10
PLUG_WALL = 0.11      # 栓の輪の肉厚
FLANGE_R = BODY_R + 0.03
SKIRT_H = 0.17        # 口の上に立つ垂直の帯の高さ
CAP_TOP_Z = RIM_Z + 0.36
CAP_WALL = 0.11       # 天面の肉厚
TOP_FLAT_R = 0.27     # 肩が終わり天面になる半径
TOP_RISE = 0.02       # 天面が首へ向かって盛り上がる高さ
NECK_R = 0.075
NECK_H = 0.06
KNOB_R = 0.17
NECK_TOP = CAP_TOP_Z + TOP_RISE + NECK_H
KNOB_CENTRE_Z = NECK_TOP + math.sqrt(KNOB_R ** 2 - NECK_R ** 2)
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


def base_outline():
    """床の中心 → 円盤の丸い角 → 内側へ反って胴の外面（z = FLOOR_Z）まで。"""
    pts = [(0.0, 0.0)]
    pts += arc(FOOT_R - FOOT_ROUND, FOOT_ROUND, FOOT_ROUND, -math.pi / 2, 0, 16)
    pts += arc(FOOT_R - FOOT_ROUND, FOOT_DISC - FOOT_ROUND, FOOT_ROUND, 0, math.pi / 2, 16)
    # 内側へ反りながら胴へ向かう首（凹の曲線）。胴の外面へは液の底の高さで入る
    pts += cove((FOOT_R - FOOT_ROUND, FOOT_DISC), (BODY_R, FLOOR_Z), 40)
    return pts


def base_profile():
    """液の底より下の無垢の台座だけの断面（屈折の計算用）。上面は液の底。"""
    return base_outline() + [(0.0, FLOOR_Z)]


def jar_profile():
    inner_r = BODY_R - WALL
    pts = base_outline()
    # 胴 → 口（すり合わせの平らな縁）
    pts += [(BODY_R, RIM_Z - 0.03)]
    pts += arc(BODY_R - 0.012, RIM_Z - 0.012, 0.012, 0, math.pi / 2, 5)
    pts += arc(inner_r + 0.01, RIM_Z - 0.01, 0.01, math.pi / 2, math.pi, 4)
    # 内壁 → 厚い底
    pts += arc(inner_r - 0.05, FLOOR_Z + 0.05, 0.05, 0, -math.pi / 2, 8)
    pts += [(0.0, FLOOR_Z)]
    return pts


def quarter(cx, cz, a, b, power, steps):
    """(cx + a, cz) から (cx, cz + b) への超楕円の 1/4。power が大きいほど角張る。"""
    pts = []
    for i in range(steps + 1):
        t = i / steps * math.pi / 2
        pts.append((cx + a * math.cos(t) ** (2 / power), cz + b * math.sin(t) ** (2 / power)))
    return pts


def lid_profile():
    """つまみの頂点 → 首 → 天面 → 肩 → 垂直の帯 → 下面 → 栓 → 栓の内側 → 内面 → 内側の頂点。"""
    inner_r = BODY_R - WALL
    centre = KNOB_CENTRE_Z
    pts = [(0.0, centre + KNOB_R)]
    start = math.atan2(NECK_TOP - centre, NECK_R)
    pts += arc(0.0, centre, KNOB_R, math.pi / 2, start, 64)[1:]
    # 首は天面へ小さく反って広がる
    fillet = 0.03
    pts += arc(NECK_R + fillet, CAP_TOP_Z + TOP_RISE + fillet, fillet, math.pi, 1.5 * math.pi, 12)
    # 天面: 首から肩へ、わずかに下る
    top = []
    r0, r1 = NECK_R + fillet, TOP_FLAT_R
    for i in range(1, 17):
        t = i / 16
        top.append((r0 + (r1 - r0) * t, CAP_TOP_Z + TOP_RISE * (1 - t * t)))
    pts += top
    # 丸い肩から垂直の帯へ
    skirt_top = RIM_Z + SKIRT_H
    shoulder = quarter(TOP_FLAT_R, skirt_top, FLANGE_R - TOP_FLAT_R, CAP_TOP_Z - skirt_top, 2.6, 80)
    pts += list(reversed(shoulder))[1:]
    # 帯の下の角を丸め、口の縁に載る下面へ
    corner = 0.02
    pts += arc(FLANGE_R - corner, RIM_Z + corner, corner, 0, -math.pi / 2, 12)
    plug_r = inner_r - 0.006
    pts += [(plug_r + 0.012, RIM_Z)]
    pts += [(plug_r, RIM_Z - 0.012)]
    # 栓: 外面を下り、丸い下端から厚い輪の内側へ
    bottom = RIM_Z - PLUG_DEPTH
    pts += [(plug_r, bottom + 0.015)]
    pts += arc(plug_r - 0.015, bottom + 0.015, 0.015, 0, -math.pi / 2, 4)[1:]
    plug_in = plug_r - PLUG_WALL
    pts += arc(plug_in + 0.015, bottom + 0.015, 0.015, -math.pi / 2, -math.pi, 4)
    # 内面: 栓の内側を上がり、天面の裏へ丸く
    inner_top = CAP_TOP_Z - CAP_WALL
    spring = RIM_Z + SKIRT_H - 0.04
    pts += [(plug_in, spring)]
    vault = quarter(0.0, spring, plug_in, inner_top - spring, 2.4, 80)
    pts += vault[1:]
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
    check_profile("base", base_profile())
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
    # 断面の点列 [r0, z0, r1, z1, ...]。軸上の2点を結べば閉じた形になる
    glass["jar_lid_profile"] = [v for r, z in profiles["Jar_Lid"] for v in (r, z + LID_LIFT)]
    glass["jar_base_profile"] = [v for r, z in base_profile() for v in (r, z)]


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

"""
メンダコ: b1 の素材を Blender で 1 つの体に融合してならし、生体の写真と同じ向きで描く（2026-10-24）。

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P blender/mendako/b2_fuse_render.py -- <出力の名前>

入力: blender/mendako/work/b1_body.obj・b1_eyes_bulge.obj・b1_fins.obj・b1_arms.obj（融合する）、b1_eyeballs.obj・b1_suckers.obj・b1_cirri.obj（そのまま）
出力:
  blender/mendako/work/b2_mendako.blend      融合した形（git に入れない）
  docs/mendako/b2_<名前>_{front,oblique,top,oral}.png   描いた絵（粘土色の不透明の材質。形の陰を見るため）

座標: OBJ は +Y 背・+Z 前で書いてある。読み込むと Blender の Z が背、−Y が前になる（前から見る = −Y から +Y を向く）。
融合: 重ねた体積を Voxel Remesh（VOXEL）で 1 つの殻にし、Corrective Smooth でならす（手順書 第 3 節「重ねて Voxel Remesh で
  一つの殻に融合してからならす」）。
"""

import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
WORK = os.path.join(HERE, "work")
OUT = os.path.join(ROOT, "docs", "mendako")
NAME = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else "v1"
VOXEL = 0.0035          # W。ひれの厚み 0.016 を 4 つ以上の格子で持つ
SMOOTH_ITER = 12
RES = (1200, 900)


def check(obj):
    """融合した面: 開いた辺・3 面以上が共有する辺・符号つき体積"""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    open_e = sum(1 for e in bm.edges if len(e.link_faces) == 1)
    nonman = sum(1 for e in bm.edges if len(e.link_faces) > 2)
    vol = bm.calc_volume(signed=True)
    print(f"融合した面: 面 {len(bm.faces)}、開いた辺 {open_e}、3 面以上の辺 {nonman}、符号つき体積 {vol:+.4f}")
    bm.free()


def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_obj(name):
    path = os.path.join(WORK, name)
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=path, forward_axis="NEGATIVE_Z", up_axis="Y")
    new = [o for o in bpy.data.objects if o not in before]
    return new[0]


def fuse(objs):
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    body = bpy.context.view_layer.objects.active
    body.name = "Mendako"
    rm = body.modifiers.new("remesh", "REMESH")
    rm.mode = "VOXEL"
    rm.voxel_size = VOXEL
    rm.adaptivity = 0.0
    bpy.ops.object.modifier_apply(modifier=rm.name)
    sm = body.modifiers.new("smooth", "CORRECTIVE_SMOOTH")
    sm.iterations = SMOOTH_ITER
    sm.factor = 0.5
    sm.use_only_smooth = True
    bpy.ops.object.modifier_apply(modifier=sm.name)
    dec = body.modifiers.new("dec", "DECIMATE")
    dec.ratio = 0.35
    bpy.ops.object.modifier_apply(modifier=dec.name)
    bpy.ops.object.shade_smooth()
    return body


def skin_material():
    m = bpy.data.materials.new("clay")
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (0.42, 0.34, 0.32, 1)
    bsdf.inputs["Roughness"].default_value = 0.55
    return m


def flat_material(name, rgb):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    bsdf.inputs["Roughness"].default_value = 0.5
    return m


def light(name, loc, energy, size, rot):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    lo.rotation_euler = rot
    bpy.context.scene.collection.objects.link(lo)


def look_at(obj, target):
    from mathutils import Vector
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def setup_scene():
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError as e:
        print(e)
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.film_transparent = False
    w = bpy.data.worlds.new("w")
    sc.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.02, 0.02, 0.025, 1)
    bg.inputs["Strength"].default_value = 1.0
    # 光: 正面上のやわらかい光、左右の補い、後ろの縁の光（水族館の写真に近い暗い背景）
    light("key", (1.2, -1.8, 1.8), 120, 1.2, (math.radians(45), 0, math.radians(35)))
    light("fill", (-1.8, -1.0, 0.7), 25, 1.5, (math.radians(70), 0, math.radians(-60)))
    light("rim", (-0.6, 1.8, 1.4), 60, 1.2, (math.radians(-50), 0, math.radians(-15)))
    light("under", (0, 0, -2.0), 60, 2.0, (math.pi, 0, 0))
    cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    return sc, cam


def ground(sc):
    bpy.ops.mesh.primitive_plane_add(size=6, location=(0, 0, -0.002))
    g = bpy.context.active_object
    g.data.materials.append(flat_material("sand", (0.16, 0.15, 0.14)))
    return g


def render(sc, cam, view, path, gnd):
    cd = cam.data
    gnd.hide_render = view in ("oral",)
    for o in bpy.data.objects:
        if o.name.startswith(("a3_", "b1_suckers", "b1_cirri")):
            o.hide_render = view != "oral"      # 吸盤と触毛は口側の絵だけ
    if view == "front":                    # 生体の正面（Sunshine2）: 砂の高さに近い所から前を見る
        cd.type = "PERSP"
        cd.lens = 70
        cam.location = (0, -3.0, 0.16)
        look_at(cam, (0, 0, 0.16))
    elif view == "oblique":                # 斜め前左の上から（Sunshine1 に近い向き）
        cd.type = "PERSP"
        cd.lens = 70
        a = math.radians(-50)
        cam.location = (2.8 * math.sin(a) * -1, -2.8 * math.cos(a), 0.9)
        look_at(cam, (0, 0, 0.12))
    elif view == "top":                    # 背中から（前が上）
        cd.type = "ORTHO"
        cd.ortho_scale = 1.35
        cam.location = (0, 0, 3)
        cam.rotation_euler = (0, 0, 0)
    elif view == "oral":                   # 口側から（前が上）
        cd.type = "ORTHO"
        cd.ortho_scale = 1.35
        cam.location = (0, 0, -3)
        cam.rotation_euler = (math.pi, 0, 0)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


def main():
    clear()
    parts = [import_obj(n) for n in ("b1_body.obj", "b1_eyes_bulge.obj", "b1_fins.obj", "b1_arms.obj")]
    body = fuse(parts)
    body.data.materials.append(skin_material())
    check(body)
    eb = import_obj("b1_eyeballs.obj")
    em = flat_material("eye", (0.06, 0.065, 0.075))
    next(n for n in em.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Roughness"].default_value = 0.15
    eb.data.materials.append(em)
    bpy.context.view_layer.objects.active = eb
    bpy.ops.object.shade_smooth()
    detail = []
    for n, rgb in (("b1_suckers.obj", (0.86, 0.62, 0.58)), ("b1_cirri.obj", (0.82, 0.52, 0.5))):
        o = import_obj(n)
        o.data.materials.append(flat_material(n, rgb))
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.shade_smooth()
        detail.append(o)
    print("面の数", len(body.data.polygons))
    sc, cam = setup_scene()
    gnd = ground(sc)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(WORK, "b2_mendako.blend"))
    for view in ("front", "oblique", "top", "oral"):
        render(sc, cam, view, os.path.join(OUT, f"b2_{NAME}_{view}.png"), gnd)


main()

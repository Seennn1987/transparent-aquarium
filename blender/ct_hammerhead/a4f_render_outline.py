"""シロシュモクザメ A4「輪郭の静止画」: 骨のメッシュ（a4e_mesh.py の PLY）を読み、白い光の静止画を出す。

開いている .blend を壊さないよう、別のシーン HH_A4 を作ってそこで描く（ファイルは保存しない）。
座標: x = 吻→尾（m）、y = 左右、z = 背が上。単位 m（全長 約 1.03 m）。
出す画像（docs/hammerhead_ct/）:
  a4_side.png   横から（写真 Sphyrna zygaena noaa.jpg と重ねる用）
  a4_top.png    背中から（写真 Sphyrna corona-zygaena compare.jpg と重ねる用）
  a4_front.png  前から（頭の翼の反り）
  a4_display.png 展示の姿勢（器の中を回遊。背が上、斜め上から）
骨の色は無彩色（手順 1 と同じ BONE_GRAY）。染まり・膜・内臓はまだ作らない。
使い方: Blender の Python から exec(open(このファイル).read())
"""
import bpy, os, math
import sys as _sys, os as _os
_sys.path.insert(0, _os.environ.get("HH_SCRIPTS", "/Users/shoui/transparent-aquarium/transparent-aquarium/blender/ct_hammerhead"))
import hh_paths
from mathutils import Vector

ROOT = hh_paths.ROOT
MESH = hh_paths.MESH
OUT = hh_paths.DOCS
PARTS = ["HH_skeleton", "HH_girdle", "HH_pect_L", "HH_pect_R", "HH_pelv_L", "HH_pelv_R", "HH_dfin1", "HH_dfin2", "HH_anal"]
BONE_GRAY = (0.62, 0.60, 0.57, 1.0)

sc = hh_paths.blender_scene("HH_A4")
coll = bpy.data.collections.get("HH_A4")
if coll is None:
    coll = bpy.data.collections.new("HH_A4")
    sc.collection.children.link(coll)
for ob in list(coll.objects):
    me = ob.data if ob.type == "MESH" else None
    bpy.data.objects.remove(ob, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)

mat = bpy.data.materials.get("HH_BoneGray") or bpy.data.materials.new("HH_BoneGray")
mat.use_nodes = True
bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
bsdf.inputs["Base Color"].default_value = BONE_GRAY
bsdf.inputs["Roughness"].default_value = 0.55

lc = bpy.context.view_layer.layer_collection.children[coll.name]
bpy.context.view_layer.active_layer_collection = lc
for name in PARTS:
    bpy.ops.wm.ply_import(filepath=f"{MESH}/{name}.ply")
    ob = bpy.context.selected_objects[0]
    ob.name = name
    ob.data.materials.clear(); ob.data.materials.append(mat)
    for p in ob.data.polygons:
        p.use_smooth = True

# 外接
mn = Vector((1e9, 1e9, 1e9)); mx = -mn
for ob in coll.objects:
    for c in ob.bound_box:
        w = ob.matrix_world @ Vector(c)
        mn = Vector((min(mn.x, w.x), min(mn.y, w.y), min(mn.z, w.z)))
        mx = Vector((max(mx.x, w.x), max(mx.y, w.y), max(mx.z, w.z)))
ctr = (mn + mx) * 0.5
print("bbox m", tuple(round(a, 3) for a in mn), tuple(round(a, 3) for a in mx))

# 白い光（カメレオンの手順 1 と同じ: 白い背景 + 面光源）
world = bpy.data.worlds.get("HH_World") or bpy.data.worlds.new("HH_World")
sc.world = world; world.use_nodes = True; nt = world.node_tree
for n in list(nt.nodes): nt.nodes.remove(n)
out = nt.nodes.new("ShaderNodeOutputWorld"); lp = nt.nodes.new("ShaderNodeLightPath")
seen = nt.nodes.new("ShaderNodeBackground"); seen.inputs["Color"].default_value = (1, 1, 1, 1); seen.inputs["Strength"].default_value = 1.0
amb = nt.nodes.new("ShaderNodeBackground"); amb.inputs["Color"].default_value = (1, 1, 1, 1); amb.inputs["Strength"].default_value = 0.25
mix = nt.nodes.new("ShaderNodeMixShader")
nt.links.new(lp.outputs["Is Camera Ray"], mix.inputs[0]); nt.links.new(amb.outputs[0], mix.inputs[1])
nt.links.new(seen.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])

sc.render.engine = "CYCLES"; sc.cycles.samples = 32; sc.cycles.use_denoising = False
sc.view_settings.view_transform = "Standard"; sc.render.image_settings.file_format = "PNG"

cam = bpy.data.objects.new("HH_Cam", bpy.data.cameras.new("HH_Cam")); coll.objects.link(cam); sc.camera = cam
key = bpy.data.objects.new("HH_Key", bpy.data.lights.new("HH_Key", "AREA")); coll.objects.link(key)

def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat("-Z", "Y").to_euler()

def shoot(name, loc, rot=None, ortho=None, res=(1800, 900), lens=50):
    cam.location = loc
    if rot is None:
        cam.rotation_euler = (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    else:
        cam.rotation_euler = tuple(math.radians(a) for a in rot)
    if ortho:
        cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho
    else:
        cam.data.type = "PERSP"; cam.data.lens = lens
    cam.data.clip_end = 100
    size = (mx - mn).length
    key.data.energy = 6.0 * size * size; key.data.size = size
    key.location = cam.location + (Vector((0, 0, 1)) * size * 0.6)
    aim(key, ctr)
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.filepath = f"{OUT}/{name}.png"
    bpy.ops.render.render(write_still=True)
    print("wrote", name)

L = mx.x - mn.x
shoot("a4_side", (ctr.x, mn.y - 5.0, ctr.z), rot=(90, 0, 0), ortho=L * 1.05, res=(1800, 520))      # 右が尾、上が背
shoot("a4_top", (ctr.x, ctr.y, mx.z + 5.0), rot=(0, 0, 0), ortho=L * 1.05, res=(1800, 760))        # 右が尾
shoot("a4_front", (mn.x - 5.0, ctr.y, ctr.z), rot=(90, 0, -90), ortho=(mx.y - mn.y) * 1.1, res=(1200, 600))
shoot("a4_display", (ctr.x - 0.55, ctr.y - 1.35, ctr.z + 0.75), res=(1600, 1000), lens=45)

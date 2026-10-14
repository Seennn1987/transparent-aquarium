"""シロシュモクザメ A7: 頭の部品（頭骨・上あご・下あご・歯・舌の弓・エラの骨）を色分けして、不透明の静止画を出す（形の確認用）。
別シーン HH_HEAD で行い、ファイルは保存しない。出力: docs/hammerhead_ct/a7_head_<向き>.png
使い方（Blender の中）: TAG = "..."; exec(open(この file).read())"""
import bpy, os, math, mathutils
ROOT = "/Users/shoui/transparent-aquarium/transparent-aquarium"
MESH = ROOT + "/blender/ct_hammerhead/mesh"
OUTD = ROOT + "/docs/hammerhead_ct"
TAG = globals().get("TAG", "")
PARTS = [("HH_skel_head", (0.55, 0.62, 0.60, 1)), ("HH_bone", (0.6, 0.25, 0.5, 1)), ("HH_jaw_upper", (0.15, 0.45, 0.95, 1)),
         ("HH_jaw_lower", (1.0, 0.55, 0.1, 1)), ("HH_teeth_upper", (0.95, 0.95, 0.95, 1)), ("HH_teeth_lower", (0.95, 0.95, 0.95, 1)),
         ("HH_hyoid", (0.2, 0.75, 0.25, 1)), ("HH_gill", (0.9, 0.2, 0.3, 1)), ("HH_girdle", (0.55, 0.62, 0.60, 1))] + globals().get("EXTRA", [])
sc = bpy.data.scenes.get("HH_HEAD") or bpy.data.scenes.new("HH_HEAD")
bpy.context.window.scene = sc
coll = bpy.data.collections.get("HH_HEAD")
if coll is None:
    coll = bpy.data.collections.new("HH_HEAD"); sc.collection.children.link(coll)
for ob in list(coll.objects):
    if ob.type != "MESH": continue
    me = ob.data; bpy.data.objects.remove(ob, do_unlink=True)
    if me and me.users == 0: bpy.data.meshes.remove(me)
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]
for name, col in PARTS:
    p = f"{MESH}/{name}.ply"
    if not os.path.exists(p): continue
    bpy.ops.wm.ply_import(filepath=p)
    ob = bpy.context.selected_objects[0]; ob.name = "hd_" + name
    m = bpy.data.materials.get("hd_" + name) or bpy.data.materials.new("hd_" + name)
    m.diffuse_color = col; ob.data.materials.clear(); ob.data.materials.append(m)
    ob.color = col
sc.render.engine = "BLENDER_WORKBENCH"
sh = sc.display.shading; sh.light = "STUDIO"; sh.color_type = "OBJECT"; sh.show_xray = False
sc.display.shading.show_cavity = True
sc.render.resolution_x, sc.render.resolution_y = 1400, 1000
sc.render.film_transparent = False
cam = bpy.data.objects.get("hd_cam")
if cam is None:
    cam = bpy.data.objects.new("hd_cam", bpy.data.cameras.new("hd_cam"))
if cam.name not in coll.objects: coll.objects.link(cam)
sc.camera = cam; cam.data.type = "ORTHO"; cam.data.ortho_scale = globals().get("SCALE", 0.30)
tgt = mathutils.Vector((globals().get("TGT_X", 0.12), 0.0, -0.01))
VIEWS = {"side": (0, -1, 0), "below": (0, 0, -1), "front_below": (-0.8, -0.35, -0.5), "oblique": (-0.45, -0.75, 0.35), "top": (0, 0, 1), "back_below": (0.5, -0.5, -0.7)}
VIEWS = {k: v for k, v in VIEWS.items() if k in globals().get("VSEL", ["side", "below", "front_below", "oblique"])}
for vname, d in VIEWS.items():
    d = mathutils.Vector(d).normalized()
    cam.location = tgt + d * 1.0
    up = mathutils.Vector((0, 0, 1)) if abs(d.z) < 0.9 else mathutils.Vector((-1, 0, 0))
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    if abs(d.z) >= 0.9:
        cam.rotation_euler = mathutils.Euler((math.pi, 0, -math.pi / 2)) if d.z < 0 else mathutils.Euler((0, 0, -math.pi / 2))
    sc.render.filepath = f"{OUTD}/a7_head_{vname}{TAG}.png"
    bpy.ops.render.render(write_still=True, scene=sc.name)
print("rendered", list(VIEWS))

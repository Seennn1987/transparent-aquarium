"""シロシュモクザメ A5「体の膜」: 膜（HH_body.ply）を読み、開いた辺の数を数え、骨と重ねて白い光の静止画を出す。
a4f_render_outline.py の後に、同じシーン HH_A4 で実行する（骨の部品はそのまま使う）。
膜は確かめ用の半透明の灰（染まりと屈折は A6 で作る）。
"""
import bpy, bmesh, os, math
from mathutils import Vector
ROOT = "/Users/shoui/transparent-aquarium/transparent-aquarium"
MESH = ROOT + "/blender/ct_hammerhead/mesh"; OUT = ROOT + "/docs/hammerhead_ct"
sc = bpy.data.scenes["HH_A4"]; bpy.context.window.scene = sc
coll = bpy.data.collections["HH_A4"]
MEMS = ["HH_body", "HH_pectmem_L", "HH_pectmem_R", "HH_pelvmem_L", "HH_pelvmem_R"]
mat = bpy.data.materials.get("HH_BodyCheck") or bpy.data.materials.new("HH_BodyCheck")
mat.use_nodes = True
b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
b.inputs["Base Color"].default_value = (0.80, 0.82, 0.86, 1); b.inputs["Alpha"].default_value = 0.22; b.inputs["Roughness"].default_value = 0.4
try: mat.surface_render_method = "BLENDED"
except Exception: pass
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]
objs = []
for name in MEMS:
    old = bpy.data.objects.get(name)
    if old: bpy.data.objects.remove(old, do_unlink=True)
    bpy.ops.wm.ply_import(filepath=f"{MESH}/{name}.ply")
    o = bpy.context.selected_objects[0]; o.name = name
    bm = bmesh.new(); bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    print(name, "faces", len(bm.faces), "open edges", sum(1 for e in bm.edges if e.is_boundary), "non-manifold", sum(1 for e in bm.edges if not e.is_manifold))
    bm.to_mesh(o.data); bm.free()
    for p in o.data.polygons: p.use_smooth = True
    o.data.materials.clear(); o.data.materials.append(mat); objs.append(o)
ob = objs[0]
cam = bpy.data.objects["HH_Cam"]; key = bpy.data.objects["HH_Key"]
mn = Vector((1e9,)*3); mx = -mn
for o in [ob]:
    for c in o.bound_box:
        w = o.matrix_world @ Vector(c); mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
ctr = (mn + mx) / 2; L = mx.x - mn.x
print("body bbox m", tuple(round(a,3) for a in mn), tuple(round(a,3) for a in mx))
def shoot(name, loc, rot=None, ortho=None, res=(1800, 600), lens=45):
    cam.location = loc
    cam.rotation_euler = tuple(math.radians(a) for a in rot) if rot else (ctr - cam.location).to_track_quat("-Z", "Y").to_euler()
    if ortho: cam.data.type = "ORTHO"; cam.data.ortho_scale = ortho
    else: cam.data.type = "PERSP"; cam.data.lens = lens
    size = (mx - mn).length; key.data.energy = 6.0 * size * size; key.data.size = size
    key.location = cam.location + Vector((0, 0, 1)) * size * 0.6
    key.rotation_euler = (ctr - key.location).to_track_quat("-Z", "Y").to_euler()
    sc.render.resolution_x, sc.render.resolution_y = res; sc.render.filepath = f"{OUT}/{name}.png"
    bpy.ops.render.render(write_still=True); print("wrote", name)
shoot("a5_side", (ctr.x, mn.y - 5.0, ctr.z), rot=(90, 0, 0), ortho=L * 1.05, res=(1800, 620))
shoot("a5_top", (ctr.x, ctr.y, mx.z + 5.0), rot=(0, 0, 0), ortho=L * 1.05, res=(1800, 640))
shoot("a5_front", (mn.x - 5.0, ctr.y, ctr.z), rot=(90, 0, -90), ortho=(mx.y - mn.y) * 1.1, res=(1200, 700))
shoot("a5_display", (ctr.x - 0.55, ctr.y - 1.35, ctr.z + 0.75), res=(1600, 1000))

"""A7: 口の開き方の案の絵。a7e_render_head.py のシーン HH_HEAD（下あごは 30° 開いた面）で、下あごと下の歯を関節の軸のまわりに回して描く。
出力: docs/hammerhead_ct/a7_mouth_<角度>.png"""
import bpy, math, mathutils, json
import sys as _sys, os as _os
_sys.path.insert(0, _os.environ.get("HH_SCRIPTS", "/Users/shoui/transparent-aquarium/transparent-aquarium/blender/ct_hammerhead"))
import hh_paths
ROOT = hh_paths.ROOT
OUTD = hh_paths.DOCS
J = json.load(open(next(p for p in (hh_paths.WORK + "/a7_open.json", hh_paths.DOCS + "/a7_open.json") if _os.path.exists(p))))
BASE = J["angle_deg"]; jl = J["joint_L_zuv_mm"]; jr = J["joint_R_zuv_mm"]; sgn = J["sign"]
pL = mathutils.Vector((jl[0], jl[1], -jl[2])) / 1000; pR = mathutils.Vector((jr[0], jr[1], -jr[2])) / 1000
ax = (pR - pL).normalized()
sc = hh_paths.blender_scene("HH_HEAD")
movers = [sc.objects["hd_HH_jaw_lower"], sc.objects["hd_HH_teeth_lower"]]
for o in movers: o["m0"] = [list(r) for r in o.matrix_world]
cam = sc.objects["hd_cam"]; cam.data.ortho_scale = 0.20
tgt = mathutils.Vector((0.10, 0.0, -0.02)); d = mathutils.Vector((-0.35, -0.9, 0.12)).normalized()
cam.location = tgt + d; cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
for ang in globals().get("ANGLES", [15, 25, 35]):
    # 面での角度（a7c の rot と同じ向き: 腹側が v 正。Blender では z=-v なので回す向きを確かめて合わせる）
    delta = math.radians(ang - BASE)
    R = mathutils.Matrix.Translation(pL) @ mathutils.Matrix.Rotation(-sgn * delta, 4, ax) @ mathutils.Matrix.Translation(-pL)
    for o in movers: o.matrix_world = R @ mathutils.Matrix(o["m0"])
    sc.render.filepath = f"{OUTD}/a7_mouth_{ang}.png"
    bpy.ops.render.render(write_still=True, scene=sc.name)
for o in movers: o.matrix_world = mathutils.Matrix(o["m0"])
print("ok")

"""シロシュモクザメ A6: 骨・軟骨・膜の PLY を組織ごとに 1 つにまとめ、減らして、標本ページ用の glb に書き出す。

開いている .blend を壊さないよう、別のシーン HH_EXPORT で行う（ファイルは保存しない）。
組織は custom property `hh_part` で渡す（hammerhead-material.js が読む）:
  Bone      椎骨の列（HH_bone。Eames et al. 2007 の胚では椎骨が強く石灰化してアリザリンで赤い）
  Cartilage ひれの骨・肩帯・腰帯・尾の骨など（アルシアンで青い。参考の胚では放射軟骨は明るい水色）
  HeadCartilage 頭骨（a6b_split_head.py で分けた。参考の胚では濃い青緑）
  Jaw       上あご・下あご（a7b・a7c で細かい格子から分け、下あごは口を開いた向き）。ひれの軟骨と同じ明るい青
  Teeth     歯（800 HU を超える石灰化した所）。椎骨と同じ赤
  Gill      舌の弓とエラの骨（a7 で作る）。ひれの軟骨と同じ明るい青
  Skin      体と、ひれの膜（透明になった組織）
  Viscera   内臓（a8a_viscera.py、CT の体腔から取り出した。2026-10-15）
CT（Kamminga et al. 2017、figshare、CC0）から作ったので、glb はリポジトリに入れてよい。
"""
import bpy, bmesh, os
import sys as _sys, os as _os
_sys.path.insert(0, _os.environ.get("HH_SCRIPTS", "/Users/shoui/transparent-aquarium/transparent-aquarium/blender/ct_hammerhead"))
import hh_paths
ROOT = hh_paths.ROOT
MESH = hh_paths.MESH
OUT = hh_paths.GLB
PARTS = {
    "Bone": (["HH_bone"], 60000),
    "Cartilage": (["HH_skel_rest", "HH_girdle", "HH_pect_L", "HH_pect_R", "HH_pelv_L", "HH_pelv_R", "HH_dfin1", "HH_dfin2", "HH_anal"], 110000),
    "HeadCartilage": (["HH_skel_head"], 150000),
    "Jaw": (["HH_jaw_upper", "HH_jaw_lower"], 90000),
    "Teeth": (["HH_teeth_upper", "HH_teeth_lower"], 40000),
    "Gill": (["HH_hyoid", "HH_gill"], 60000),
    "Skin": (["HH_body", "HH_pectmem_L", "HH_pectmem_R", "HH_pelvmem_L", "HH_pelvmem_R"], 160000),
}
# A8 内臓（a8a_viscera.py）。面があるときだけ書き出す（2026-10-15）
if os.path.exists(f"{MESH}/HH_viscera.ply"):
    PARTS["Viscera"] = (["HH_viscera"], 120000)
sc = hh_paths.blender_scene("HH_EXPORT")
coll = bpy.data.collections.get("HH_EXPORT")
if coll is None:
    coll = bpy.data.collections.new("HH_EXPORT"); sc.collection.children.link(coll)
for ob in list(coll.objects):
    me = ob.data; bpy.data.objects.remove(ob, do_unlink=True)
    if me and me.users == 0: bpy.data.meshes.remove(me)
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]
report = {}
for part, (names, target) in PARTS.items():
    objs = []
    for n in names:
        bpy.ops.wm.ply_import(filepath=f"{MESH}/{n}.ply")
        o = bpy.context.selected_objects[0]; o.name = f"tmp_{n}"; objs.append(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = f"HH_{part}"; ob.data.name = f"HH_{part}"
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6); bm.to_mesh(ob.data); bm.free()
    n0 = len(ob.data.polygons)
    if n0 > target:
        m = ob.modifiers.new("dec", "DECIMATE"); m.ratio = target / n0
        bpy.ops.object.modifier_apply(modifier=m.name)
    for p in ob.data.polygons: p.use_smooth = True
    ob["hh_part"] = part
    bm = bmesh.new(); bm.from_mesh(ob.data)
    report[part] = (n0, len(ob.data.polygons), sum(1 for e in bm.edges if e.is_boundary)); bm.free()
bpy.ops.object.select_all(action="DESELECT")
for ob in coll.objects: ob.select_set(True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
# 選択は他のシーン（開いているカメレオン）のものまで拾うので、このシーンのこのコレクションだけを書き出す
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_active_scene=True, use_active_collection=True, export_extras=True,
                          export_apply=True, export_normals=True, export_texcoords=False, export_materials="NONE")
print("parts (faces before, after, open edges):", report, "->", OUT, os.path.getsize(OUT))

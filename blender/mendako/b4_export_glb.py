"""
メンダコ: 融合した形（b2_fuse_render.py が保存した work/b2_mendako.blend）と中の部品を、標本ページ用の glb に書き出す（2026-10-24）。

  /Applications/Blender.app/Contents/MacOS/Blender -b --factory-startup -P blender/mendako/b4_export_glb.py -- 水槽/scenes/specimen/assets/specimen_mendako.glb

部品（ノードの extras の md_part。ページの mendako-material.js が部品ごとに吸い方を決める）:
  Body     体（傘・頭・眼の盛り上がり・ひれ・腕を融合した殻）
  Eye      眼球（左右）
  Suckers  吸盤、Cirri 触毛
  Shell    殻（ひれの支え。a2_parts.py の a2_shell.obj）
  Beak     顎板（上と下。a2_beak_upper.obj・a2_beak_lower.obj）
  中の部品（2026-10-24 手順 A5、b6_organs.py の b6_<部品>.obj。面を 0.35 倍に減らす）:
  HeadCartilage 頭の軟骨、Statolith 平衡石、Gut 消化管、DigestiveGland 消化腺、Gill 鰓、Heart 心臓、BranchialHeart 鰓心臓
大きさ: 横幅 W = 1 の面を 0.138 倍して、メートル（成熟した雄で横幅 約 138 mm）。glTF は +Y が背、+Z が前、+X が体の左。
各部品は閉じた面で、符号つき体積が正（外向き）であることを書き出す前に確かめる。
"""

import os
import sys

import bmesh
import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
OUT = sys.argv[sys.argv.index("--") + 1]
SCALE = 0.138
ORGANS = ["HeadCartilage", "Statolith", "Gut", "DigestiveGland", "Gill", "Heart", "BranchialHeart"]


def import_obj(name):
    before = set(bpy.data.objects)
    bpy.ops.wm.obj_import(filepath=os.path.join(WORK, name), forward_axis="NEGATIVE_Z", up_axis="Y")
    return [o for o in bpy.data.objects if o not in before][0]


def close(o):
    """重なった点を結び、開いた穴に蓋をする（眼球の極の重なり、顎板の管の両端）"""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.holes_fill(bm, edges=bm.edges, sides=0)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(o.data)
    bm.free()


def check(o):
    bm = bmesh.new()
    bm.from_mesh(o.data)
    open_e = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    vol = bm.calc_volume(signed=True)
    bm.free()
    print(f"{o['md_part']:8s} 面 {len(o.data.polygons):7d}  開いた辺・3 面以上の辺 {open_e}  符号つき体積 {vol:+.3e} m³")
    if vol <= 0:
        raise RuntimeError(f"{o['md_part']} の面が内向き")


def main():
    bpy.ops.wm.open_mainfile(filepath=os.path.join(WORK, "b2_mendako.blend"))
    keep = {"Mendako": "Body", "b1_eyeballs": "Eye", "b1_suckers": "Suckers", "b1_cirri": "Cirri"}
    sp = import_obj("b1_spots.obj")      # 背の突起の中心の色素の名残（2026-10-24 手順 A6）
    sp["md_part"] = "Spots"
    for o in list(bpy.data.objects):
        name = next((k for k in keep if o.name.startswith(k)), None)
        if o.get("md_part") == "Spots":
            continue
        if o.type != "MESH" or name is None:
            bpy.data.objects.remove(o, do_unlink=True)
        else:
            o["md_part"] = keep[name]
    shell = import_obj("a2_shell.obj")
    shell["md_part"] = "Shell"
    up, lo = import_obj("a2_beak_upper.obj"), import_obj("a2_beak_lower.obj")
    bpy.ops.object.select_all(action="DESELECT")
    up.select_set(True)
    lo.select_set(True)
    bpy.context.view_layer.objects.active = up
    bpy.ops.object.join()
    up["md_part"] = "Beak"
    for name in ORGANS:
        o = import_obj(f"b6_{name}.obj")
        o["md_part"] = name
        if len(o.data.polygons) > 4000:
            dec = o.modifiers.new("dec", "DECIMATE")
            dec.ratio = 0.35
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=dec.name)
    for o in list(bpy.data.objects):        # 名前を変えると一覧の並びが変わるので、先に固定する（同じ部品を 2 度縮めた）
        o.name = o["md_part"]
        if o["md_part"] != "Body":
            close(o)
        o.data.materials.clear()
        o.scale = (SCALE, SCALE, SCALE)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
        check(o)
    os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.path.abspath(OUT), export_format="GLB", export_extras=True, export_yup=True,
                              export_apply=True, export_materials="NONE", export_texcoords=False, export_normals=True)
    print("書き出し", os.path.abspath(OUT), os.path.getsize(os.path.abspath(OUT)) // 1024, "KB")


main()

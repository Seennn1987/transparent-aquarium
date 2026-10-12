"""透明標本のカメレオン（全身 CT の骨・膜・軟骨、骨組み、CH_Hover）を glb に書き出す。

  blender -b -P blender/export_chameleon_gltf.py -- 水槽/scenes/specimen/assets/private/specimen_chameleon.glb

骨の形は MorphoSource 000050726（CAS:HERP:135515、In Copyright – Non-Commercial Use Permitted）から作った。
再配布しないので、書き出し先は git に入れない private/ にする（.gitignore）。

部位はメッシュの custom property `chameleon_part`（Bone / Skin / Cartilage）で渡す。
読み込み側（chameleon-material.js）は、この名前で組織を選ぶ。
"""
import math
import os
import runpy
import sys

import bpy
import numpy as np

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
RIG = os.path.join(HERE, "rig_chameleon_ct.py")
PARTS = {"CH_Skeleton": "Bone", "CH_Skin": "Skin", "CH_Cartilage": "Cartilage"}


def closed_report(ob):
    """閉じた殻か（厚みを表と裏の深さの差で測るので、穴があると色が抜ける）と、面の向き（外向きなら体積が正）。"""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return open_edges, vol


SKIN_DEPTH_MAX = 1.5      # 膜の厚みの上限（モデル単位、頭骨長 L = 1.04）。体の幅より長い光線は抜けとみなす


def bake_skin_depth(ob):
    """膜の各頂点から内向きに、膜の反対側までの距離（その場の組織の厚み）を `_depth` に焼く。
    膜は開いた殻なので、表と裏の深さの差では厚みが測れない。代わりにこの厚みの半分を、
    膜を横切るたびに通る組織の長さとする（入る所と出る所で 1 回ずつ数える）。"""
    from mathutils.bvhtree import BVHTree
    me = ob.data
    bvh = BVHTree.FromObject(ob, bpy.context.evaluated_depsgraph_get(), deform=False)
    depth = np.zeros(len(me.vertices), np.float32)
    for i, v in enumerate(me.vertices):
        n = -v.normal
        hit = bvh.ray_cast(v.co + n * 1e-4, n, SKIN_DEPTH_MAX)
        depth[i] = hit[3] if hit[0] is not None else 0.0
    attr = me.attributes.get("_depth") or me.attributes.new("_depth", "FLOAT", "POINT")
    attr.data.foreach_set("value", depth)
    print(f"[Chameleon glb] 膜の厚み: 中央値 {np.median(depth):.3f}、90% {np.percentile(depth, 90):.3f}、抜け {np.mean(depth == 0):.1%}")
    return depth


def prepare():
    g = runpy.run_path(RIG, run_name="chameleon_ct_export")
    gen = runpy.run_path(g["GEN"], run_name="chameleon_ct")
    coll, rigob, skel, rig = gen["build"]()
    d, _, k = gen["load"]()
    g["build_pose"](rigob, d, k, g["POSE_JAR"])
    bpy.context.view_layer.update()
    g["trim_skin"]()
    frames = g["write_hover"](rigob)
    bake_skin_depth(bpy.data.objects["CH_Skin"])
    report = {}
    for name, part in PARTS.items():
        ob = bpy.data.objects.get(name)
        if ob is None:
            raise RuntimeError(f"{name} がありません")
        ob["chameleon_part"] = part
        report[part] = closed_report(ob)
        print(f"[Chameleon glb] {part}: 面 {len(ob.data.polygons)}、閉じていない辺 {report[part][0]}、体積 {report[part][1]:.4f}")
    return coll, rigob, frames, report


def export(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in bpy.data.objects:
        if ob.name in PARTS or ob.name in ("CH_Rig", "CH_Root"):
            ob.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_materials="NONE",
        export_attributes=True,
        export_extras=True,
        export_skins=True,
        export_def_bones=False,
        export_animations=True,
        export_animation_mode="ACTIONS",
        export_force_sampling=True,
        export_optimize_animation_size=True,
        export_anim_slide_to_zero=True,
        export_morph_animation=False,
        export_cameras=False,
        export_lights=False,
    )
    print(f"[Chameleon glb] {path} {os.path.getsize(path) / 1e6:.1f} MB")


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 1:
        raise SystemExit("使い方: blender -b -P export_chameleon_gltf.py -- <out.glb>")
    prepare()
    export(argv[0])


if __name__ == "__main__":
    main()

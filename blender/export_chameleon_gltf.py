"""透明標本のカメレオン（全身 CT の骨・膜・軟骨、骨組み、CH_Hover）を glb に書き出す。

  blender -b -P blender/export_chameleon_gltf.py -- 水槽/scenes/specimen/assets/private/specimen_chameleon.glb

骨の形は MorphoSource 000050726（CAS:HERP:135515、In Copyright – Non-Commercial Use Permitted）から作った。
再配布しないので、書き出し先は git に入れない private/ にする（.gitignore）。

部位はメッシュの custom property `chameleon_part`（Bone / Skin / Cartilage / Viscera / Organ）で渡す。
Organ は体腔の臓器で、臓器の名前は `chameleon_organ`。
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
PARTS = {"CH_Skeleton": "Bone", "CH_Skin": "Skin", "CH_Cartilage": "Cartilage", "CH_Viscera": "Viscera"}


def closed_report(ob):
    """閉じた殻か（厚みを表と裏の深さの差で測るので、穴があると色が抜ける）と、面の向き（外向きなら体積が正）。"""
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data)
    open_edges = sum(1 for e in bm.edges if not e.is_manifold)
    vol = bm.calc_volume(signed=True)
    bm.free()
    return open_edges, vol


def stretch_report(ob, limit=2.0):
    """展示の姿勢で、静止時より何倍に伸びた辺があるか（膜は面を外さないので、伸びは数えて見るだけ）。"""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg); me = ev.to_mesh()
    P = np.empty(len(me.vertices) * 3, np.float32); me.vertices.foreach_get("co", P); P = P.reshape(-1, 3)
    ev.to_mesh_clear()
    R = np.empty(len(ob.data.vertices) * 3, np.float32); ob.data.vertices.foreach_get("co", R); R = R.reshape(-1, 3)
    E = np.empty(len(ob.data.edges) * 2, np.int32); ob.data.edges.foreach_get("vertices", E); E = E.reshape(-1, 2)
    r = np.linalg.norm(P[E[:, 0]] - P[E[:, 1]], axis=1) / np.maximum(np.linalg.norm(R[E[:, 0]] - R[E[:, 1]], axis=1), 1e-6)
    print(f"[Chameleon glb] 膜の辺の伸び: 中央値 {np.median(r):.2f}、99% {np.percentile(r, 99):.2f}、{limit} 倍より伸びた辺 {int((r > limit).sum())} / {len(r)}")
    return r


def prepare():
    g = runpy.run_path(RIG, run_name="chameleon_ct_export")
    gen = runpy.run_path(g["GEN"], run_name="chameleon_ct")
    coll, rigob, skel, rig = gen["build"]()
    d, _, k = gen["load"]()
    g["build_pose"](rigob, d, k, g["POSE_JAR"])
    bpy.context.view_layer.update()
    # 膜は体積のうちに切り離して作った（ct_body_pipeline/softmesh2.py）ので、伸びた面を外さない
    stretch_report(bpy.data.objects["CH_Skin"])
    frames = g["write_hover"](rigob)
    report = {}
    for name, part in PARTS.items():
        ob = bpy.data.objects.get(name)
        if ob is None:
            raise RuntimeError(f"{name} がありません")
        ob["chameleon_part"] = part
        report[part] = closed_report(ob)
        print(f"[Chameleon glb] {part}: 面 {len(ob.data.polygons)}、閉じていない辺 {report[part][0]}、体積 {report[part][1]:.4f}")
    # 体腔の臓器（generate_chameleon_ct_body.build_organs）: 部位 Organ、臓器の名前は chameleon_organ
    for ob in bpy.data.objects:
        if ob.name.startswith("CH_Organ_"):
            ob["chameleon_part"] = "Organ"
            r = closed_report(ob)
            print(f"[Chameleon glb] Organ {ob['chameleon_organ']}: 面 {len(ob.data.polygons)}、閉じていない辺 {r[0]}、体積 {r[1]:.5f}")
    return coll, rigob, frames, report


def export(path):
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    for ob in bpy.data.objects:
        if ob.name in PARTS or ob.name.startswith("CH_Organ_") or ob.name in ("CH_Rig", "CH_Root"):
            ob.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        use_selection=True,
        export_yup=True,
        export_materials="NONE",
        export_attributes=False,
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

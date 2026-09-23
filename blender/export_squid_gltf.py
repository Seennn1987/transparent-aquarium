"""
透明標本イカを水槽（ブラウザ / Three.js）用の .glb に書き出すスクリプト
Blender 5.2 LTS で動作確認済み。

使い方（ターミナル）:
  blender --background --factory-startup --python export_squid_gltf.py -- <出力 .glb のパス>

animate_squid.py（形 → 骨組み → 動き）を実行してから書き出す。書き出す内容:
  - 部位ごとのメッシュ（名前は squid_part）と骨組み 98 本
  - 動き 4 つ: SQ_Hover / SQ_SwimForward / SQ_SwimBackward / SQ_Jet（その場で動く版。体全体の移動は水槽側で行う）
  - 単位は ML=1（ルートの拡大を 1 に戻して書き出す）。水槽側で好きな大きさに拡大する

Blender の色は「体の中を通る光の吸収」（ボリューム）で出しているが、glTF には入らない。
そこで水槽側が同じ考え方で透過色を計算できるよう、頂点ごとに次の値を焼き込む:
  色（COLOR_0）
    RGB = 組織を通る光の色（make_tissue_material と同じ色の帯を、曲げる前の体の前後位置で引いたもの）
    A   = 濃さの倍率（腕の付け根を頭の中で 0 から徐々に濃くする root_fade。ほかは 1）
  _depth（ML=1 単位）
    かたまり（頭・腕・眼・内臓）: その場所の太さ（半径）。視線が面に垂直なほど長く組織を通る
    膜（外套膜の壁・エンペラ・軟甲）: 膜の厚さの半分。視線が面をかすめるほど長く組織を通る
どちらの計算を使うかと吸収の強さは、部位ごとに水槽側（squid-material.js）で決める。
"""

import bpy
import math
import os
import sys
from mathutils import Vector

BLENDER_DIR = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
if not os.path.isdir(BLENDER_DIR):
    raise FileNotFoundError(f"イカのスクリプトのフォルダが見つかりません: {BLENDER_DIR}")
exec(open(os.path.join(BLENDER_DIR, "animate_squid.py"), encoding="utf-8").read(), globals())

EXPORT_CLIPS = ("Hover", "SwimForward", "SwimBackward", "Jet")

# 形が単純な部位の太さ（ML=1 単位）。generate_squid.py の寸法から
ORGAN_DEPTH = {
    "Eyes": EYE_RADIUS,
    "BuccalMass": 0.033,
    "Beak": 0.008,
    "DigestiveGland": 0.05,
    "Caecum": 0.028,
    "Gonad": 0.018,
    "InkSac": 0.011,
    "Gladius": 0.0015,
    "Gills": 0.004,
    "SuckerRings": 0.0025,
}


def ramp_color(stops, f):
    """Blender のカラーランプ（線形補間）と同じ計算"""
    f = min(max(f, 0.0), 1.0)
    for (p0, c0), (p1, c1) in zip(stops, stops[1:]):
        if f <= p1:
            t = 0.0 if p1 == p0 else (f - p0) / (p1 - p0)
            return tuple(a + (b - a) * t for a, b in zip(c0[:3], c1[:3]))
    return tuple(stops[-1][1][:3])


def tint_of(name, co):
    if name == "Head":
        return ramp_color(HEAD_TINT_STOPS, (co.x + 0.25) / 0.33)
    if name in ("Mantle", "Fins", "Funnel", "Arms"):
        return ramp_color(BODY_TINT_STOPS, (co.x + 1.3) / 2.3)
    colors = {"Eyes": COLOR_EYE, "BuccalMass": COLOR_BUCCAL, "Beak": COLOR_BEAK,
              "DigestiveGland": COLOR_DIGESTIVE, "Caecum": COLOR_CAECUM, "Gonad": COLOR_GONAD,
              "InkSac": COLOR_INK, "Gladius": COLOR_GLADIUS, "Gills": COLOR_GILL,
              "SuckerRings": COLOR_SUCKER_RING}
    if name not in colors:
        raise KeyError(f"{name} の透過色が決まっていません")
    return tuple(colors[name][:3])


def limb_distance(co, pts):
    best = None
    for a, b in zip(pts, pts[1:]):
        ab = b - a
        t = min(max((co - a).dot(ab) / ab.length_squared, 0.0), 1.0)
        d = (a + ab * t - co).length
        best = d if best is None else min(best, d)
    return best


def depth_values(name, me, limb_lines):
    if name == "Mantle":
        return [MANTLE_WALL / 2] * len(me.vertices)
    if name == "Fins":
        # make_fin_material と同じ「刃先でも色が少し残る」厚み
        th = me.attributes["thickness"].data
        return [FIN_BASE_THICKNESS * (th[v.index].value * 1.1 + 0.25) / 2 for v in me.vertices]
    if name == "Head":
        return [max(math.hypot(v.co.y, v.co.z), 0.01) for v in me.vertices]
    if name == "Funnel":
        return [0.03] * len(me.vertices)
    if name == "Arms":
        ids = me.attributes["limb_id"].data
        lines = [[Vector(p) for p in line["pts"]] for line in limb_lines]
        return [max(limb_distance(v.co, lines[int(round(ids[v.index].value))]), 0.002) for v in me.vertices]
    if name not in ORGAN_DEPTH:
        raise KeyError(f"{name} の太さが決まっていません")
    return [ORGAN_DEPTH[name]] * len(me.vertices)


def fade_of(name, co):
    if name != "Arms":
        return 1.0
    x_hidden, x_full = HEAD_FRONT_X + 0.03, HEAD_FRONT_X - 0.04
    return min(max((co.x - x_hidden) / (x_full - x_hidden), 0.0), 1.0)


def bake_attributes(parts):
    limb_lines = json.loads(parts["Arms"]["limb_lines"])
    for name, obj in parts.items():
        if obj.type != "MESH":
            continue
        me = obj.data
        for old in ("SQ_Tint", "_depth"):
            if old in me.attributes:
                me.attributes.remove(me.attributes[old])
        col = me.color_attributes.new("SQ_Tint", "FLOAT_COLOR", "POINT")
        rgba = []
        for v in me.vertices:
            rgba.extend(tint_of(name, v.co) + (fade_of(name, v.co),))
        col.data.foreach_set("color", rgba)
        me.color_attributes.active_color = col
        me.attributes.new("_depth", "FLOAT", "POINT").data.foreach_set("value", depth_values(name, me, limb_lines))


def prepare_scene():
    scene = bpy.context.scene
    coll = bpy.data.collections[SPECIES["name"]]
    keep = set(coll.all_objects)
    for obj in list(scene.objects):
        if obj not in keep:
            bpy.data.objects.remove(obj, do_unlink=True)

    root = bpy.data.objects[SPECIES["name"] + "_Root"]
    if root.animation_data is not None:
        root.animation_data_clear()
    root.location = (0.0, 0.0, 0.0)
    root.scale = (1.0, 1.0, 1.0)

    wanted = {PREFIX + c for c in EXPORT_CLIPS}
    for act in list(bpy.data.actions):
        if act.name.startswith(PREFIX) and act.name not in wanted:
            bpy.data.actions.remove(act)
    missing = wanted - {a.name for a in bpy.data.actions}
    if missing:
        raise RuntimeError(f"書き出す動きが見つかりません: {sorted(missing)}")

    parts = squid_parts()
    rig = parts["Rig"]
    rig.animation_data.action = bpy.data.actions[PREFIX + "Hover"]
    rig.hide_set(False)
    scene.frame_set(1)
    return parts


def export(path):
    bpy.ops.export_scene.gltf(
        filepath=path,
        export_format="GLB",
        export_yup=True,
        export_materials="NONE",
        export_vertex_color="NAME",
        export_vertex_color_name="SQ_Tint",
        export_all_vertex_colors=False,
        export_attributes=True,
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


def main_export():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 1:
        raise ValueError("使い方: -- <出力 .glb のパス>")
    path = os.path.abspath(argv[0])
    parts = prepare_scene()
    bake_attributes(parts)
    export(path)
    meshes = sorted(n for n, o in parts.items() if o.type == "MESH")
    print(f"[{SPECIES['name']}] 書き出し完了: {path} ({os.path.getsize(path) / 1e6:.2f} MB), "
          f"部位 {len(meshes)} 個, 骨 {len(parts['Rig'].data.bones)} 本, 動き {len(EXPORT_CLIPS)} 個")


main_export()

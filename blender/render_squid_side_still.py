"""
水槽の見た目と比べるための、透明標本イカの横向き静止画（白いライトボックス）を書き出すスクリプト

使い方（ターミナル）:
  blender --background --factory-startup --python render_squid_side_still.py -- <出力 PNG のパス>

水槽のカメラはイカをほぼ真横・同じ高さから見るので、同じ向きで撮る。
色・半透明の設定は generate_squid.py のまま（EEVEE・Standard 表示・白い背景）。
"""

import bpy
import os
import sys
from mathutils import Vector

BLENDER_DIR = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
if not os.path.isdir(BLENDER_DIR):
    raise FileNotFoundError(f"イカのスクリプトのフォルダが見つかりません: {BLENDER_DIR}")
exec(open(os.path.join(BLENDER_DIR, "generate_squid.py"), encoding="utf-8").read(), globals())


def main_still():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 1:
        raise ValueError("使い方: -- <出力 PNG のパス>")
    scene = bpy.context.scene
    cam = bpy.data.objects.new(PREFIX + "SideCam", bpy.data.cameras.new(PREFIX + "SideCam"))
    scene.collection.objects.link(cam)
    scene.camera = cam
    cam.data.clip_start, cam.data.clip_end = 0.001, 10.0
    cam.data.lens = 50
    loc, target = Vector((-0.02, -0.55, 0.03)), Vector((-0.02, 0.0, 0.0))
    cam.location = loc
    cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 32
    scene.eevee.volumetric_samples = 128
    scene.render.resolution_x, scene.render.resolution_y = 1200, 500
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = os.path.abspath(argv[0])
    bpy.ops.render.render(write_still=True)
    print(f"[{SPECIES['name']}] 静止画を書き出しました: {scene.render.filepath}")


main_still()

"""
イカの動き確認用の動画（MP4）を書き出すスクリプト

使い方（ターミナル）:
  blender --background --python render_squid_preview.py -- wide  /tmp/squid_demo_wide.mp4
  blender --background --python render_squid_preview.py -- close /tmp/squid_demo_close.mp4

  wide  : 固定カメラで引きの画。体全体が進む・急発進する様子を見る
  close : 体をその場に止め、斜め上から寄った画。エンペラ・胴・腕の動きを細かく見る
動きの確認用なので、画質は軽めの設定にしてある（色・半透明の見え方は静止画の設定と同じ）。
"""

import bpy
import os
import sys
from mathutils import Vector

BLENDER_DIR = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
if not os.path.isdir(BLENDER_DIR):
    raise FileNotFoundError(f"イカのスクリプトのフォルダが見つかりません: {BLENDER_DIR}")
exec(open(os.path.join(BLENDER_DIR, "animate_squid.py"), encoding="utf-8").read(), globals())

CAMERA_NAME = PREFIX + "PreviewCam"


def preview_camera(scene):
    cam = bpy.data.objects.get(CAMERA_NAME)
    if cam is None:
        cam = bpy.data.objects.new(CAMERA_NAME, bpy.data.cameras.new(CAMERA_NAME))
        scene.collection.objects.link(cam)
    cam.data.clip_start, cam.data.clip_end = 0.001, 10.0
    scene.camera = cam
    return cam


def aim(cam, loc, target, lens):
    cam.location = loc
    cam.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = lens


def setup_shot(mode):
    scene = bpy.context.scene
    root = bpy.data.objects[SPECIES["name"] + "_Root"]
    rig = squid_parts()["Rig"]
    rig.hide_render = True
    cam = preview_camera(scene)
    if mode == "wide":
        _, root_ch, _ = sample(DEMO_DURATION, demo_state, limb_info(rig))
        xs = root_ch[("", "location", 0)]
        ml = SPECIES["mantle_length"]
        x0, x1 = min(xs) - 1.35 * ml, max(xs) + 1.05 * ml   # 触腕の先〜尾の先まで入れる
        target = Vector(((x0 + x1) / 2, 0, 0))
        half = (x1 - x0) / 2 * 1.1
        aim(cam, target + Vector((0.25, -0.9, 0.55)).normalized() * half * 2.9, target, 50)
    elif mode == "close":
        root.animation_data.action = None
        root.location = (0, 0, 0)
        aim(cam, Vector((0.12, -0.26, 0.20)), Vector((-0.015, 0, 0)), 50)
    else:
        raise ValueError(f"撮り方は wide か close を指定してください（指定: {mode}）")


def setup_video(path):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16
    scene.eevee.volumetric_samples = 64
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    settings = scene.render.image_settings
    settings.media_type = "VIDEO"
    settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = path


def main_preview():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 2:
        raise ValueError("使い方: -- <wide|close> <出力MP4のパス>")
    mode, path = argv
    setup_shot(mode)
    setup_video(path)
    bpy.ops.render.render(animation=True)
    print(f"[{SPECIES['name']}] 動画を書き出しました: {path}")


main_preview()

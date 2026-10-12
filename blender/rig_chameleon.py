"""
エボシカメレオン透明標本 手順 2「瓶に入る動きを1つ」: 骨組みの自動生成と CH_Hover ループ

使い方:
  - Blender の Scripting で実行するか、MCP for Blender の execute_code に渡す
    （generate_chameleon_contour.py を読み込んで骨格を作り直し、骨組みと CH_Hover を付ける）
  - 動画まで出す: blender --background --factory-startup --python rig_chameleon.py -- <出力フォルダ> [間引き]
    出力フォルダに frame_####.png と hover_bounds.json を書く（mp4 化はスクリプトの外）

静止時の軸は generate_chameleon_contour.py と同じ:
  瓶の上 = +Z、動物の正中面 = XZ 面、背は -X、左右 = Y（glTF では p.z）。
  骨の名前の .L は +Y 側、.R は -Y 側（カメラ側）。

骨組み:
  v00〜v77   椎骨 1 個に骨 1 本。仙椎（v21）が根で、前は頭へ、後ろは尾の先へ連なる
  Head       頭骨・下顎・歯（v00 の子）
  ribNN.L/R  胴椎 NN の左右の肋骨（背側と腹側をまとめて 1 本）
  scapula / upperarm / forearm / hand、pelvis / thigh / shin / foot（左右）
  骨はどれも剛体なので、頂点は 1 本の骨に重み 1 で付ける。

CH_Hover（12 秒、24fps、継ぎ目なしのループ）:
  - 肋骨: 左右の肋骨が背骨の軸まわりに外へ開いて戻る（呼吸）。周期 6 秒は仮。
    安静時の呼吸数は手順 7 の直前に文献で決め、その値に置き換える（計画書 第3節）
  - 尾: 渦が先ほど強く、わずかに締まって戻る（12 秒で 1 往復）
  - 手足: 握った手足が手首・足首でわずかに揺れる（4 秒と 6 秒、左右で位相をずらす）
  - 頭: ごくわずかにうなずく（12 秒）
  歩行・登り・舌の発射・速い移動は作らない。体全体の位置は動かさない（浮遊の移動は手順 3 の瓶の側）。
"""

import bpy
import json
import math
import os
import runpy
import sys
from mathutils import Quaternion, Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
GEN = os.path.join(HERE, "generate_chameleon_contour.py")

FPS = 24
LOOP_SEC = 12.0
BREATH_SEC = 6.0        # 仮。手順 7 で文献値に置き換える
RIB_OPEN_DEG = 5.0      # 肋骨が外へ開く最大角（左右へ）
RIB_SWING_DEG = 4.0     # 肋骨が前へ起きる最大角（腹が深くなる。側面から見える呼吸）
TAIL_TIGHTEN_DEG = 35.0  # 尾全体で足される巻きの最大量（先ほど多く配る）
HAND_SWAY_DEG = 4.0
FOOT_SWAY_DEG = 3.0
HEAD_NOD_DEG = 1.0
ACTION_NAME = "CH_Hover"
LATERAL = Vector((0.0, 1.0, 0.0))


def build_armature(mod, coll):
    BONES = mod["BONES"]
    prefix = mod["PREFIX"]
    arm_data = bpy.data.armatures.new(prefix + "Rig")
    rig = bpy.data.objects.new(prefix + "Rig", arm_data)
    coll.objects.link(rig)
    root = bpy.data.objects.get(prefix + "Root")
    view_layer = bpy.context.view_layer
    if rig.name not in view_layer.objects:
        bpy.context.scene.collection.objects.link(rig)
    view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    eb = arm_data.edit_bones
    for name, (h, t, _) in BONES.items():
        b = eb.new(name)
        b.head, b.tail = h, t
        if (t - h).length < 1e-4:
            b.tail = h + Vector((0, 0, 0.02))
        b.roll = 0.0
    for name, (_, _, parent) in BONES.items():
        if parent:
            eb[name].parent = eb[parent]
    bpy.ops.object.mode_set(mode="OBJECT")
    # 骨格のメッシュを骨組みに付ける（ルートの空オブジェクトの下に骨組みを置く）
    if root:
        rig.parent = root
    for ob in coll.objects:
        if ob.type == "MESH":
            ob.parent = rig
            mo = ob.modifiers.new("Armature", "ARMATURE")
            mo.object = rig
    arm_data.display_type = "STICK"
    rig.show_in_front = True
    return rig


def local_axis(rig, bone_name, world_axis):
    """骨の静止時の局所座標で表した world_axis（骨組みは原点・無回転）。"""
    R = rig.data.bones[bone_name].matrix_local.to_3x3()
    return (R.inverted() @ world_axis).normalized()


def bump(t, period, phase=0.0):
    """0→1→0 のなめらかな往復（cos）。"""
    return 0.5 - 0.5 * math.cos(2 * math.pi * (t / period + phase))


def wave(t, period, phase=0.0):
    return math.sin(2 * math.pi * (t / period + phase))


def plan_channels(rig, mod):
    """骨ごとに、時刻 → 局所の回転（Quaternion）の関数を用意する。"""
    BONES = mod["BONES"]
    ch = []

    def about(name, world_axis, amp_deg, fn):
        ax = local_axis(rig, name, world_axis)
        return lambda tt: Quaternion(ax, math.radians(amp_deg) * fn(tt))

    # 肋骨: 背骨の接線まわりに外へ開き、横軸まわりに前へ起きる（吸気）。符号は端の動きで決める
    for name, (h, t, parent) in BONES.items():
        if not name.startswith("rib"):
            continue
        ph, pt, _ = BONES[parent]
        T = (pt - ph).normalized()
        N = Vector((-T.z, 0.0, T.x))           # 背側（generate の N = T を +90°）
        side = 1.0 if name.endswith(".L") else -1.0
        r = t - h
        test = Quaternion(T, math.radians(1.0)) @ r
        s_out = 1.0 if (test.y - r.y) * side > 0 else -1.0
        test = Quaternion(LATERAL, math.radians(1.0)) @ r
        s_sw = 1.0 if (-test.dot(N)) > (-r.dot(N)) else -1.0
        q_out = about(name, T, s_out * RIB_OPEN_DEG, lambda tt: bump(tt, BREATH_SEC))
        q_sw = about(name, LATERAL, s_sw * RIB_SWING_DEG, lambda tt: bump(tt, BREATH_SEC))
        ch.append((name, lambda tt, a=q_out, b=q_sw: a(tt) @ b(tt)))
    # 尾: 尾椎ごとに横軸まわり。+Y まわりの正の回転が時計回り = 腹側へ巻く向き（generate 側の巻きと同じ）
    caud = [n for n in BONES if n.startswith("v") and int(n[1:]) > 22]
    caud.sort(key=lambda n: int(n[1:]))
    w = [((k + 1) / len(caud)) ** 1.0 for k in range(len(caud))]
    wsum = sum(w)
    for k, name in enumerate(caud):
        ch.append((name, about(name, LATERAL, TAIL_TIGHTEN_DEG * w[k] / wsum, lambda tt: bump(tt, LOOP_SEC))))
    # 手足と頭
    for S, ph in (("L", 0.0), ("R", 0.37)):
        ch.append((f"hand.{S}", about(f"hand.{S}", LATERAL, HAND_SWAY_DEG, lambda tt, ph=ph: wave(tt, 4.0, ph))))
        ch.append((f"forearm.{S}", about(f"forearm.{S}", LATERAL, HAND_SWAY_DEG * 0.3, lambda tt, ph=ph: wave(tt, 6.0, ph + 0.2))))
        ch.append((f"foot.{S}", about(f"foot.{S}", LATERAL, FOOT_SWAY_DEG, lambda tt, ph=ph: wave(tt, 6.0, ph + 0.5))))
        ch.append((f"shin.{S}", about(f"shin.{S}", LATERAL, FOOT_SWAY_DEG * 0.3, lambda tt, ph=ph: wave(tt, 4.0, ph + 0.1))))
    ch.append(("Head", about("Head", LATERAL, HEAD_NOD_DEG, lambda tt: wave(tt, LOOP_SEC))))
    return ch


def write_hover(rig, mod):
    rig.animation_data_create()
    old = bpy.data.actions.get(ACTION_NAME)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(ACTION_NAME)
    rig.animation_data.action = act
    channels = plan_channels(rig, mod)
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    n = int(round(LOOP_SEC * FPS))
    for f in range(n + 1):           # 最後のフレームは最初と同じ値（継ぎ目なし）
        tt = (f % n) / FPS
        for name, fn in channels:
            pb = rig.pose.bones[name]
            pb.rotation_quaternion = fn(tt)
            pb.keyframe_insert("rotation_quaternion", frame=f + 1, group=name)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 1, n
    act.use_cyclic = True
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, n
    return n


def hover_bounds(coll, frames, step=6):
    """ループ中の骨格全体の外接（静止時との差）。手順 3 の瓶の空きに使う。"""
    scene = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    out = None
    rest = None
    for f in list(range(1, frames + 1, step)) + [frames]:
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        mn = Vector((1e9,) * 3); mx = -mn
        for ob in coll.objects:
            if ob.type != "MESH":
                continue
            ev = ob.evaluated_get(dg)
            me = ev.to_mesh()
            for v in me.vertices:
                w = ev.matrix_world @ v.co
                mn = Vector(map(min, mn, w)); mx = Vector(map(max, mx, w))
            ev.to_mesh_clear()
        if rest is None:
            rest = (mn.copy(), mx.copy())
            out = [mn.copy(), mx.copy()]
        out[0] = Vector(map(min, out[0], mn)); out[1] = Vector(map(max, out[1], mx))
    scene.frame_set(1)
    return {"rest_min": list(rest[0]), "rest_max": list(rest[1]), "loop_min": list(out[0]), "loop_max": list(out[1]),
            "grow_max": max(max(r - l for r, l in zip(rest[0], out[0])), max(h - r for r, h in zip(rest[1], out[1])))}


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    mod = runpy.run_path(GEN, run_name="chameleon")
    spine, H, joints, stations, coll = mod["build"]()
    rig = build_armature(mod, coll)
    frames = write_hover(rig, mod)
    b = hover_bounds(coll, frames)
    print(f"[Chameleon] 骨 {len(rig.data.bones)} 本、{ACTION_NAME} {frames} フレーム。ループ中の外接の広がり 最大 {b['grow_max']:.3f} L")
    if argv:
        outdir = os.path.abspath(argv[0])
        stride = int(argv[1]) if len(argv) > 1 else 2
        os.makedirs(outdir, exist_ok=True)
        with open(os.path.join(outdir, "hover_bounds.json"), "w", encoding="utf-8") as f:
            json.dump(b, f, indent=1)
        cam = mod["render_still"](os.path.join(outdir, "rest.png"), coll)
        scene = bpy.context.scene
        scene.cycles.samples = 12
        scene.render.resolution_percentage = 50
        for k, f in enumerate(range(1, frames + 1, stride)):
            scene.frame_set(f)
            scene.render.filepath = os.path.join(outdir, f"frame_{k:04d}.png")
            bpy.ops.render.render(write_still=True)
        print(f"[Chameleon] 動画用のフレーム: {outdir}")


if __name__ == "__main__":
    main()

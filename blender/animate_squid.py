"""
透明標本イカの遊泳アニメーション生成スクリプト
Blender 5.2 LTS で動作確認済み。

使い方:
  - このファイルを実行すると generate_squid.py（形）→ rig_squid.py（骨組み）→ 動きの作成 の順に全部やり直す
  - タイムライン（1〜337フレーム, 24fps）には確認用の通し動作「Demo」が入る
    0〜4秒 ホバリング → 4〜8秒 前進 → 8秒 ジェット噴射で後ろへ急発進 → 11〜14秒 ホバリング

作る動き（その場で動く版。水槽で泳がせるときに使い回す）:
  SQ_Hover         4秒ループ  エンペラの縁が前→後へ細かく波打ち、腕はゆっくり揺れる。体はほぼ静止
  SQ_SwimForward   2秒ループ  エンペラを大きく羽ばたかせ、頭を先にして進む（腕は束ね気味）
  SQ_SwimBackward  2秒ループ  同じ羽ばたきで尾を先にして進む
  SQ_Jet           3秒        胴を一瞬ふくらませてから一気に細く縮めて水を噴き、ゆっくり元に戻る。
                              その間エンペラは体に沿ってたたみ、腕は1本の束にまとまる
  呼吸（胴のわずかな膨らみ・縮み）はすべての動きに常に入っている。

体全体の移動は骨ではなくルートの空オブジェクトを動かす（SQ_DemoRoot）。
"""

import bpy
import json
import math
import os

BLENDER_DIR = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
if not os.path.isdir(BLENDER_DIR):
    raise FileNotFoundError(f"イカのスクリプトのフォルダが見つかりません: {BLENDER_DIR}")
exec(open(os.path.join(BLENDER_DIR, "rig_squid.py"), encoding="utf-8").read(), globals())

FPS = 24

# 各動きの状態（角度は度、速さは ML/秒、+ が尾の方向）
HOVER = dict(fin_amp=7.0, fin_out=1.3, fin_freq=2.0, fin_lag=1.1, fin_wrap=0.0,
             breath_amp=0.025, breath_freq=0.75, mantle=1.0,
             arm_sway=3.5, arm_freq=0.25, bundle=0.15, speed=0.0, bob=0.012)
SWIM_FORWARD = dict(HOVER, fin_amp=20.0, fin_out=1.0, fin_freq=1.5, fin_lag=0.5, breath_freq=1.0,
                    arm_sway=2.0, arm_freq=0.5, bundle=0.7, speed=-0.8, bob=0.0)
SWIM_BACKWARD = dict(SWIM_FORWARD, speed=0.8, bundle=0.5)
JET_HOLD = dict(HOVER, fin_amp=4.0, fin_lag=0.8, fin_wrap=55.0, breath_amp=0.0,
                arm_sway=1.0, bundle=1.0, speed=0.0, bob=0.0)
JET_DURATION = 3.0
JET_PEAK_SPEED = 4.5
DEMO_DURATION = 14.0

# 胴の収縮の効き方（前ほど大きく縮み、エンペラのある後端は少ししか縮まない）
MANTLE_CONTRACT_WEIGHT = [1.0, 1.0, 0.9, 0.6, 0.3]
# 腕を束ねるときの、付け根側から各骨を内側へ曲げる角度（度）
ARM_BUNDLE = [10.0, 6.0, 3.0, 0.0, 0.0, 0.0]
TENTACLE_BUNDLE = [8.0, 5.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def lerp_state(a, b, f):
    return {k: a[k] + (b[k] - a[k]) * f for k in a}


def jet_state(tau, before, after):
    """ジェット噴射開始から tau 秒後の状態"""
    s = lerp_state(before, JET_HOLD, smoothstep(0.0, 0.3, tau))
    s = lerp_state(s, after, smoothstep(1.2, 2.6, tau))
    m = 1.0 + 0.06 * smoothstep(0.0, 0.3, tau)            # 水を吸い込んで少し膨らむ
    m += (0.74 - m) * smoothstep(0.3, 0.5, tau)           # 0.2秒で一気に縮めて噴射
    m += (1.0 - m) * smoothstep(0.5, 1.6, tau)            # ゆっくり膨らみ直す
    s["mantle"] = m
    thrust = JET_PEAK_SPEED * smoothstep(0.3, 0.42, tau) * math.exp(-max(0.0, tau - 0.42) / 0.55)
    s["speed"] = before["speed"] * (1 - smoothstep(0.0, 0.3, tau)) + thrust
    return s


def demo_state(t):
    if t < 4.0:
        return HOVER
    if t < 5.0:
        return lerp_state(HOVER, SWIM_FORWARD, smoothstep(4.0, 5.0, t))
    if t < 8.0:
        return SWIM_FORWARD
    if t < 8.0 + JET_DURATION:
        return jet_state(t - 8.0, SWIM_FORWARD, HOVER)
    return HOVER


# ------------------------------------------------------------------
# 状態 → 骨の角度・太さ
# ------------------------------------------------------------------
def limb_bone_counts(rig):
    names = [line["name"] for line in json.loads(squid_parts()["Arms"]["limb_lines"])]
    counts = []
    for name in names:
        n = sum(1 for b in rig.data.bones if b.name.startswith(name + "_"))
        if n == 0:
            raise RuntimeError(f"{name} の骨が見つかりません。rig_squid.py の骨の名前と一致していません")
        counts.append((name, n))
    return counts


def pose_values(s, ph, limbs):
    out = {}
    breath = 1.0 + s["breath_amp"] * math.sin(ph["breath"])
    for k, w in enumerate(MANTLE_CONTRACT_WEIGHT):
        c = 1.0 - (1.0 - s["mantle"] * breath) * w
        out[(mantle_bone_name(k), "scale", 0)] = c
        out[(mantle_bone_name(k), "scale", 2)] = c

    for tag in "LR":
        for k in range(FIN_STATIONS):
            q = k / (FIN_STATIONS - 1)
            env = 0.6 + 0.4 * math.sin(math.pi * q)
            wave = ph["fin"] - s["fin_lag"] * k                  # 波は前端から後端へ伝わる
            a_in = s["fin_amp"] * env * math.sin(wave) - s["fin_wrap"]
            a_out = s["fin_amp"] * s["fin_out"] * env * math.sin(wave - 0.7) - s["fin_wrap"] * 0.5
            out[(f"Fin{tag}{k}_in", "rotation_euler", 0)] = math.radians(a_in)
            out[(f"Fin{tag}{k}_out", "rotation_euler", 0)] = math.radians(a_out)

    for a, (name, n) in enumerate(limbs):
        tentacle = name.startswith("Tentacle")
        sway = s["arm_sway"] * (0.6 if tentacle else 1.0)
        bundle = TENTACLE_BUNDLE if tentacle else ARM_BUNDLE
        offset = a * 0.83
        for i in range(n):
            c = (i + 1) / n
            lag = ph["arm"] + offset - 0.9 * i                   # 揺れは付け根から先へ遅れて伝わる
            rx = sway * c * math.sin(lag) - s["bundle"] * bundle[i]
            rz = sway * 0.7 * c * math.cos(lag + offset * 0.3)
            out[(f"{name}_{i}", "rotation_euler", 0)] = math.radians(rx)
            out[(f"{name}_{i}", "rotation_euler", 2)] = math.radians(rz)
    return out


def sample(duration, state_fn, limbs):
    """0〜duration 秒を1フレームごとに計算する（周期はフレームごとに積み上げて、速さが変わっても途切れない）"""
    frames = int(round(duration * FPS)) + 1
    dt = 1.0 / FPS
    ph = {"fin": 0.0, "breath": 0.0, "arm": 0.0}
    x = 0.0
    bones, root = {}, {("", "location", 0): [], ("", "location", 2): []}
    for f in range(frames):
        t = f * dt
        s = state_fn(t)
        for key, v in pose_values(s, ph, limbs).items():
            bones.setdefault(key, []).append(v)
        root[("", "location", 0)].append(x * SPECIES["mantle_length"])
        root[("", "location", 2)].append(s["bob"] * math.sin(2 * math.pi * 0.25 * t) * SPECIES["mantle_length"])
        ph["fin"] += 2 * math.pi * s["fin_freq"] * dt
        ph["breath"] += 2 * math.pi * s["breath_freq"] * dt
        ph["arm"] += 2 * math.pi * s["arm_freq"] * dt
        x += s["speed"] * dt
    return bones, root, frames


# ------------------------------------------------------------------
# アクション（動きのデータ）の書き込み
# ------------------------------------------------------------------
def clear_actions():
    for act in list(bpy.data.actions):
        if act.name.startswith(PREFIX):
            bpy.data.actions.remove(act)


def write_action(obj, name, channels, frames, cyclic):
    act = bpy.data.actions.new(PREFIX + name)
    act.use_fake_user = True
    adt = obj.animation_data or obj.animation_data_create()
    adt.action = act
    for (bone, path, index), values in channels.items():
        data_path = f'pose.bones["{bone}"].{path}' if bone else path
        fc = act.fcurve_ensure_for_datablock(obj, data_path, index=index, group_name=bone or "Root")
        fc.keyframe_points.add(len(values))
        fc.keyframe_points.foreach_set("co", [c for f, v in enumerate(values) for c in (f + 1, v)])
        fc.keyframe_points.foreach_set("interpolation", [1] * len(values))   # 1 = LINEAR（毎フレーム計算済み）
        fc.update()
        if cyclic:
            fc.modifiers.new("CYCLES")
    act.use_frame_range = True
    act.frame_start, act.frame_end = 1, frames
    act.use_cyclic = cyclic
    if adt.action_slot is None:
        raise RuntimeError(f"{act.name} が {obj.name} に割り当てられていません")
    return act


def frame_demo_viewports(xs):
    """通し動作で泳ぐ範囲全体（触腕の先〜尾の先）が画面に入るよう、3Dビューを引く"""
    if bpy.app.background:
        return
    ml = SPECIES["mantle_length"]
    x0, x1 = min(xs) - 1.35 * ml, max(xs) + 1.05 * ml
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == "VIEW_3D":
                r3d = area.spaces.active.region_3d
                r3d.view_location = ((x0 + x1) / 2, 0.0, 0.0)
                r3d.view_distance = (x1 - x0) * 1.3


def animate_squid():
    rig = squid_parts()["Rig"]
    root = bpy.data.objects[SPECIES["name"] + "_Root"]
    limbs = limb_bone_counts(rig)
    clear_actions()

    clips = (("Hover", 4.0, lambda t: HOVER, True),
             ("SwimForward", 2.0, lambda t: SWIM_FORWARD, True),
             ("SwimBackward", 2.0, lambda t: SWIM_BACKWARD, True),
             ("Jet", JET_DURATION, lambda t: jet_state(t, HOVER, HOVER), False))
    for name, duration, fn, cyclic in clips:
        bones, _, frames = sample(duration, fn, limbs)
        write_action(rig, name, bones, frames, cyclic)

    bones, root_ch, frames = sample(DEMO_DURATION, demo_state, limbs)
    write_action(rig, "Demo", bones, frames, False)
    write_action(root, "DemoRoot", root_ch, frames, False)

    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, frames
    scene.frame_set(1)
    frame_demo_viewports(root_ch[("", "location", 0)])
    xs = root_ch[("", "location", 0)]
    print(f"[{SPECIES['name']}] 動き完了: {len(bones)} 本の動きの線 × {frames} フレーム, "
          f"移動範囲 X {min(xs):.3f}〜{max(xs):.3f} m")


animate_squid()

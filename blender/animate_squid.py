"""
透明標本イカの遊泳アニメーション生成スクリプト
Blender 5.2 LTS で動作確認済み。

使い方:
  - このファイルを実行すると generate_squid.py（形）→ rig_squid.py（骨組み）→ 動きの作成 の順に全部やり直す
  - タイムライン（1〜385フレーム, 24fps）には確認用の通し動作「Demo」が入る
    0〜4秒 ホバリング → 4〜8秒 前進 → 8秒 ジェット噴射で尾を先に急発進 → 長く滑走 → 腕を広げて止まる
    → 12.5〜16秒 ホバリング

作る動き（その場で動く版。水槽で泳がせるときに使い回す）:
  SQ_Hover         12秒ループ エンペラの縁が前→後へ波打ち、腕は力を抜いて少し広げ・上へ曲げ、常にゆらゆら揺れる
  SQ_SwimForward    6秒ループ エンペラを大きく羽ばたかせ、頭を先にして進む（腕は束ね気味で小さく揺れる）
  SQ_SwimBackward   6秒ループ 同じ羽ばたきで尾を先にして進む
  SQ_Jet          4.5秒       胴を一瞬ふくらませてから一気に細く縮めて水を噴き、ゆっくり元に戻る。
                              エンペラは体に沿ってたたみ、腕は1本の束になって噴射の勢いでしなる。
                              滑走の終わりに腕を広げてブレーキをかける
  呼吸（胴のわずかな膨らみ・縮み）はすべての動きに常に入っている。

腕の動き（実物の観察記録に基づく）:
  - 付け根が横へ動き、先はゆるく遅れてついていく（鞭のように波が付け根→先へ伝わる）ので、腕は直線にならず曲線になる
  - 周期の違う複数のゆっくりした揺れを重ね、腕ごとに少しずつずらして、規則的に見えないようにする
  - ホバリング中は力を抜いて少し広げ、上へ曲げる。背側の1対（第1腕）は角のように少し立てる
  - 触腕は腕の束の中にしまい、腕より小さく揺れる

体全体の移動は骨ではなくルートの空オブジェクトを動かす（SQ_DemoRoot）。
"""

import bpy
import json
import math
import os
import random

BLENDER_DIR = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
if not os.path.isdir(BLENDER_DIR):
    raise FileNotFoundError(f"イカのスクリプトのフォルダが見つかりません: {BLENDER_DIR}")
exec(open(os.path.join(BLENDER_DIR, "rig_squid.py"), encoding="utf-8").read(), globals())

FPS = 24

# 各動きの状態（角度は度、速さは ML/秒、+ が尾の方向）
#   bundle: 腕を束ねる度合い（1=1本の束、負の値=外へ広げる）
#   arm_amp: 腕の揺れの大きさ（付け根の骨1本あたりの度。先の骨ほど大きく揺れる）
#   arm_up: 腕全体を上へ曲げる角度、horns: 背側の第1腕だけさらに立てる角度
HOVER = dict(fin_amp=7.0, fin_out=1.3, fin_freq=1.5, fin_lag=1.1, fin_wrap=0.0,
             breath_amp=0.025, breath_freq=0.75, mantle=1.0,
             arm_amp=5.0, bundle=-0.35, arm_up=10.0, horns=12.0, speed=0.0, bob=0.012)
SWIM_FORWARD = dict(HOVER, fin_amp=20.0, fin_out=1.0, fin_freq=7 / 6, fin_lag=0.5, breath_freq=1.0,
                    arm_amp=2.5, bundle=0.6, arm_up=3.0, horns=4.0, speed=-0.8, bob=0.0)
SWIM_BACKWARD = dict(SWIM_FORWARD, bundle=0.8, arm_up=0.0, horns=0.0, speed=0.8)
JET_HOLD = dict(HOVER, fin_amp=4.0, fin_lag=0.8, fin_wrap=55.0, breath_amp=0.0,
                arm_amp=0.8, bundle=1.0, arm_up=0.0, horns=0.0, speed=0.0, bob=0.0)
JET_BRAKE = dict(HOVER, arm_amp=3.0, bundle=-0.7, arm_up=4.0, horns=6.0, bob=0.0)
JET_DURATION = 4.5
JET_PEAK_SPEED = 7.0         # 噴射直後の速さ [ML/秒]
JET_DRAG_TIME = 0.4          # 水の抵抗で速さが半分になるまでの時間の目安 [秒]
DEMO_DURATION = 16.0

# 胴の収縮の効き方（前ほど大きく縮み、エンペラのある後端は少ししか縮まない）
MANTLE_CONTRACT_WEIGHT = [1.0, 1.0, 0.9, 0.6, 0.3]
# 腕を束ねるときの、付け根側から各骨を内側へ曲げる角度（度）
ARM_BUNDLE = [10.0, 6.0, 3.0, 0.0, 0.0, 0.0]
TENTACLE_BUNDLE = [8.0, 5.0, 3.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]

# 腕の揺れを作るゆっくりした周期 [Hz]。どれも 6秒で割り切れるので、6秒・12秒のループがつながる
ARM_COMMON_FREQS = (1 / 6, 1 / 3)            # 全部の腕がそろって動く成分（頭の付け根からの動き）
ARM_OWN_FREQS = (1 / 3, 1 / 2, 2 / 3)        # 腕ごとに勝手に動く成分
ARM_WAVE_DELAY = 0.10        # 揺れが骨1本分だけ先へ伝わるのにかかる時間 [秒]
TENTACLE_WAVE_DELAY = 0.07


def lerp_state(a, b, f):
    return {k: a[k] + (b[k] - a[k]) * f for k in a}


def jet_speed(tau):
    """噴射の推力で急加速し、その後は水の抵抗でだんだん遅くなる（速いほど強く減速する）"""
    if tau < 0.3:
        return 0.0
    rise = smoothstep(0.3, 0.42, tau)
    coast = 1.0 / (1.0 + max(0.0, tau - 0.42) / JET_DRAG_TIME)
    brake = 1.0 - smoothstep(2.2, 3.8, tau)                   # 最後は腕を広げてブレーキ
    return JET_PEAK_SPEED * rise * coast * brake


def jet_state(tau, before, after):
    """ジェット噴射開始から tau 秒後の状態"""
    s = lerp_state(before, JET_HOLD, smoothstep(0.0, 0.3, tau))
    s = lerp_state(s, JET_BRAKE, smoothstep(1.8, 2.8, tau))
    s = lerp_state(s, after, smoothstep(3.2, 4.4, tau))
    m = 1.0 + 0.06 * smoothstep(0.0, 0.3, tau)            # 水を吸い込んで少し膨らむ
    m += (0.74 - m) * smoothstep(0.3, 0.5, tau)           # 0.2秒で一気に縮めて噴射
    m += (1.0 - m) * smoothstep(0.5, 1.6, tau)            # ゆっくり膨らみ直す
    s["mantle"] = m
    s["speed"] = before["speed"] * (1 - smoothstep(0.0, 0.3, tau)) + jet_speed(tau)
    s["whip"] = math.exp(-max(0.0, tau - 0.4) / 0.35) * smoothstep(0.3, 0.4, tau)
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
# 腕の揺れ
# ------------------------------------------------------------------
def limb_info(rig):
    """腕ごとの (名前, 骨の本数, 付け根から見た外向きの向き, 揺れの位相) を返す"""
    rng = random.Random(11)
    info = []
    for line in json.loads(squid_parts()["Arms"]["limb_lines"]):
        name = line["name"]
        n = sum(1 for b in rig.data.bones if b.name.startswith(name + "_"))
        if n == 0:
            raise RuntimeError(f"{name} の骨が見つかりません。rig_squid.py の骨の名前と一致していません")
        phases = {axis: [rng.uniform(0, 2 * math.pi) for _ in ARM_OWN_FREQS] for axis in "xz"}
        info.append((name, n, line["radial"], phases))
    return info


def sway(t, own_phases, common_phase):
    """複数のゆっくりした揺れの重ね合わせ（-1〜1 程度）"""
    common = sum(math.sin(2 * math.pi * f * t + common_phase + k) for k, f in enumerate(ARM_COMMON_FREQS))
    own = sum(math.sin(2 * math.pi * f * t + p) / (k + 1) for k, (f, p) in enumerate(zip(ARM_OWN_FREQS, own_phases)))
    return 0.35 * common + 0.45 * own


def limb_angles(s, t, name, n, radial, phases):
    tentacle = name.startswith("Tentacle")
    dorsal = name in ("ArmIL", "ArmIR")
    bundle = TENTACLE_BUNDLE if tentacle else ARM_BUNDLE
    delay = TENTACLE_WAVE_DELAY if tentacle else ARM_WAVE_DELAY
    amp = s["arm_amp"] * (0.6 if tentacle else 1.0) * 6 / n     # 骨の本数が違っても腕全体の揺れ幅をそろえる
    # 上へ曲げる: 腕ごとに外向きの向きが違うので、上向きを腕の「外側」と「横」の成分に分けて曲げる
    ey, ez = radial[1], radial[2]
    up = s["arm_up"] + (s["horns"] if dorsal else 0.0)
    whip = s.get("whip", 0.0)
    out = []
    for i in range(n):
        g = 0.4 + 0.6 * i / (n - 1)                     # 先の骨ほど大きく揺れる（力を抜いた腕の先はよくしなる）
        tl = t - i * delay                              # 付け根の動きが遅れて先へ伝わる
        wx = amp * g * sway(tl, phases["x"], 0.0)
        wz = amp * g * sway(tl, phases["z"], 1.7)
        wx += 7.0 * g * whip * math.sin(2 * math.pi * 1.6 * tl)   # 噴射の勢いで腕の束がしなる
        rx = wx - s["bundle"] * bundle[i]
        rz = wz
        if i == 1 or (tentacle and i == 2):             # 付け根の少し先で曲げる（Bent）
            rx += up * ez
            rz += up * ey
        out.append((math.radians(rx), math.radians(rz)))
    return out


# ------------------------------------------------------------------
# 状態 → 骨の角度・太さ
# ------------------------------------------------------------------
def pose_values(s, ph, t, limbs):
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

    for name, n, radial, phases in limbs:
        for i, (rx, rz) in enumerate(limb_angles(s, t, name, n, radial, phases)):
            out[(f"{name}_{i}", "rotation_euler", 0)] = rx
            out[(f"{name}_{i}", "rotation_euler", 2)] = rz
    return out


def sample(duration, state_fn, limbs):
    """0〜duration 秒を1フレームごとに計算する（周期はフレームごとに積み上げて、速さが変わっても途切れない）"""
    frames = int(round(duration * FPS)) + 1
    dt = 1.0 / FPS
    ph = {"fin": 0.0, "breath": 0.0}
    x = 0.0
    bones, root = {}, {("", "location", 0): [], ("", "location", 2): []}
    for f in range(frames):
        t = f * dt
        s = state_fn(t)
        for key, v in pose_values(s, ph, t, limbs).items():
            bones.setdefault(key, []).append(v)
        root[("", "location", 0)].append(x * SPECIES["mantle_length"])
        root[("", "location", 2)].append(s["bob"] * math.sin(2 * math.pi * 0.25 * t) * SPECIES["mantle_length"])
        ph["fin"] += 2 * math.pi * s["fin_freq"] * dt
        ph["breath"] += 2 * math.pi * s["breath_freq"] * dt
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
    limbs = limb_info(rig)
    clear_actions()

    clips = (("Hover", 12.0, lambda t: HOVER, True),
             ("SwimForward", 6.0, lambda t: SWIM_FORWARD, True),
             ("SwimBackward", 6.0, lambda t: SWIM_BACKWARD, True),
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

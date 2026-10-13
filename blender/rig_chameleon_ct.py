"""
エボシカメレオン透明標本（全身 CT）: 骨組みに姿勢を付ける

generate_chameleon_ct_body.py の骨組み（静止姿勢 = CT の姿勢）を、骨の回転だけで別の姿勢にする。
骨の形は変えない。椎骨は「体軸の向き（頭→尾）」と「背の向き」の 2 本で姿勢を決め、四肢は親に対する向きを保つか、
個別に回す。

姿勢の作り方（POSE_JAR）:
  体軸を 1 枚の面（Blender の XZ 面、背は -X、腹は +X、上は +Z）に置いた曲線にする。
  曲線は「体軸に沿った長さ s[mm] → 接線の向き θ[度]（+X から反時計回り）」の表で与える。θ が減る = 腹側へ曲がる。
  頭は下、胴は下から上へ、尾は上で腹側へ巻く（参考写真 01）。尾の巻き方は 06 の尾をたどった表を、尾の長さで伸ばして使う。

CH_Hover（瓶の中・デスクトップ上で繰り返す、12 秒・24fps の継ぎ目なしのループ）:
  瓶の姿勢の上に、骨ごとの小さな回転を足す。回転の軸は瓶の面の法線（Y）。体全体の位置は動かさない。
  - 尾: 尾椎ごとに巻きを足して戻す（先ほど多く配る）
  - 手足: 手首・足首と前腕・下腿がわずかに揺れる（4 本で位相をずらす）
  - 頭: ごくわずかにうなずく
  肋骨は椎骨と一体（generate 側）なので、呼吸の動きはまだ付けていない。振幅と周期は見た目で決めた仮の値。

使い方:
  blender --background --python rig_chameleon_ct.py -- <出力.png>               瓶の姿勢の静止画
  blender --background --python rig_chameleon_ct.py -- --hover <出力フォルダ> [間引き]
      CH_Hover を付け、ループ中の外接（hover_bounds.json）とフレームの画像を書く
  環境変数 CH_REST=1 で姿勢を付けない（CT の姿勢のまま）
"""

import math
import os
import runpy
import sys

import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
GEN = os.path.join(HERE, "generate_chameleon_ct_body.py")

# 06 の尾の巻き（generate_chameleon_contour.TAIL_TURN と同じ表）: 尾の付け根からの長さ [L(06)] → 回転 [度]
TAIL_TURN_06 = [(0.0, 0.0), (0.421, -3.0), (0.766, -5.7), (1.105, -14.0), (1.439, -19.7), (1.731, -27.3), (1.957, -44.1),
                (2.148, -76.0), (2.363, -105.9), (2.615, -121.0), (2.856, -145.7), (3.08, -173.1), (3.317, -195.9),
                (3.55, -222.3), (3.76, -254.7), (3.962, -284.9), (4.148, -318.8), (4.308, -353.1), (4.457, -386.0),
                (4.598, -429.9), (4.729, -469.7), (4.849, -508.4), (4.953, -569.2), (5.0, -575.0)]

POSE_JAR = {
    # 頸〜胴: 01 で背骨の接線を測った値（首 約 140° → 胴の中ほど 約 96° → 腰 約 80°。背側へ凸の C 字）
    "trunk": [(0.0, 140.0), (20.0, 125.0), (40.0, 105.0), (60.0, 96.0), (104.7, 80.0)],
    "tail_start": 107.6,          # 尾の付け根（仙椎の後ろ）[mm]
    "tail_lift": 6.0,             # 尾の付け根で背側へ起こす角
    "head_dir": -57.0,            # 頭骨（後頭顆→吻端）の向き。01 のかぶと→吻端の向き（約 -33°）に合わせて決めた
    # 肩帯（肩甲骨〜関節窩）の、体軸の前向きからの角（横から見た角）[度]。06 で肩甲骨は背骨から関節窩へ、
    # 体軸の頭の向きから 48° 下がる（背骨の接線 (3700,1640)→(3900,1800)、肩甲骨 (3810,1760)→(3825,2005)、原寸の画素）。
    # CT の個体は 16〜19° で、関節窩が頸の 1〜2 番目の椎骨の下まで前へ倒れていた（保存の変形と読む）。肩帯の背の端を中心に起こす
    "girdle_tilt": {"fR": 48.0, "fL": 48.0},
    # 四肢: 骨ごとの向き（面内の角 θ[度]、外へ開く角 φ[度]）。θ は横から見た面内の角（右 = 腹側 0°、上 = 尾側が正）。
    # 前肢（2026-10-13 に測り直し）: 01 の頭（かぶとの後ろの頂 (183,338)、吻端 (278,392)。1 辺 447px）で
    #   展示の姿勢の骨格を 01 に重ね（相似変換）、肘・手首・指先が 01 の点に来る向きを解いた（ct_body_pipeline/forefit の記録）。
    #   01 の点: 手前の肢 肘 (222,266)、手首 (272,251)、指先 (308,250)。奥の肢 肘 (253,281)、手首 (298,277)、指先 (318,276)
    #   （平行な 2 本の骨＝前腕の、体に近い端を肘とした。奥の肘は体に半分隠れていて、手前より不確か）
    #   重ねた骨格の関節窩は 01 の (243,305) に来て、01 の上腕（関節窩から肘へ斜めに上がる骨）の下の端と合う。
    #   φ は、面内に見える長さと骨の長さの比から（外へ開く向きと仮定。01 の正面からは向きの前後を読めない）
    #   以前の値（上腕 +17° など）は、前腕を上腕と取り違えて測っていた（2026-10-13 の指摘「丸で囲った骨の位置がおかしい」）
    # 後肢: 大腿 (165,190)→(230,175) で +13°、下腿 →(280,170) で +6°、足は水平（01、以前の測り方のまま）
    "limbs": {
        "fL_upper": (117.2, 45.1), "fL_lower": (15.5, 23.5), "fL_hand": (0.4, 33.1),
        "fR_upper": (65.2, 69.9), "fR_lower": (3.9, 39.9), "fR_hand": (1.6, 57.9),
        "hL_upper": (13.0, 35.0), "hL_lower": (6.0, 10.0), "hL_foot": (0.0, 0.0),
        "hR_upper": (13.0, 35.0), "hR_lower": (6.0, 10.0), "hR_foot": (0.0, 0.0),
    },
}


S_SIGN = float(Vector((0, 0, 1)).cross(Vector((1, 0, 0))).y)   # 目標の面で D×T が向く Y の符号（θ=0 で T=+X, D=+Z）


def interp(table, x):
    return float(np.interp(x, [a for a, b in table], [b for a, b in table]))


def rot2(deg):
    a = math.radians(deg)
    return Vector((math.cos(a), 0.0, math.sin(a)))


def frame(T, D):
    """T（前後）と D（背）から直交の回転行列（列 = T, D×T, D）。"""
    T = T.normalized()
    D = (D - T * D.dot(T)).normalized()
    S = D.cross(T)
    return Matrix((T, S, D)).transposed()


def head_dorsal(b):
    """頭骨の背の向き: 頭骨の長軸から最も離れた頂点（かぶとの頂）への向き。"""
    ob = bpy.data.objects["CH_Skeleton"]
    vg = ob.vertex_groups["head"].index
    a = b.head_local
    u = (b.tail_local - b.head_local).normalized()
    best, bd = None, -1.0
    for v in ob.data.vertices:
        if any(g.group == vg for g in v.groups):
            r = v.co - a
            r = r - u * r.dot(u)
            if r.length > bd:
                bd, best = r.length, r
    return best.normalized()


def limb_sides(arm, axis_at, J, n, step):
    """肢が体の左右どちら側か（+1 = 背を -X・腹を +X に置いたとき +Y 側）。肢帯の付け根を体軸の横向きに投影する。"""
    out = {}
    for c in ("fR", "fL", "hL", "hR"):
        b = arm.bones.get(c + "_girdle") or arm.bones.get(c + "_upper")
        p = b.head_local
        # 体軸で最も近い点
        best, bs = 1e9, 0.0
        for i in range(0, n, 10):
            q, _, _ = axis_at(i * step)
            if (q - p).length < best:
                best, bs = (q - p).length, i * step
        q, T, D = axis_at(bs)
        S = D.cross(T)
        out[c] = 1.0 if (b.tail_local - q).dot(S) > 0 else -1.0
    return out


GIRDLE_LOG = {}


def build_pose(rigob, d, k, pose):
    ct = lambda p: Vector((p[1], -p[2], -p[0])) * k
    ctd = lambda p: Vector((p[1], -p[2], -p[0]))
    C = d["rig__axis"]
    Dv = d["rig__dorsal"]
    J = [float(x) for x in d["rig__J"]]
    step = float(d["rig__axis_step"])
    n = len(C)

    def axis_at(s):
        i = max(1, min(n - 2, int(round(s / step))))
        return ct(C[i]), (ct(C[i + 1]) - ct(C[i - 1])).normalized(), ctd(Dv[i])

    L_tail_06 = 5.0
    tail_len = (n - 1) * step - pose["tail_start"]
    L_mm = (1.04 / k) / 1.04                 # 1 L（06 の単位）= 頭骨長 / 1.04 [mm]
    scale_tail = tail_len / (L_tail_06 * L_mm)

    def theta(s):
        if s <= pose["tail_start"]:
            return interp(pose["trunk"], s)
        # 尾の付け根で背側へ起こす角は、4 mm かけて入れる（一度に入れると折れ目ができ、膜に継ぎ目の線が出た）
        lift = pose["tail_lift"] * min(1.0, (s - pose["tail_start"]) / 4.0)
        h0 = interp(pose["trunk"], pose["tail_start"]) + lift
        u = (s - pose["tail_start"]) / (L_mm * scale_tail)
        return h0 + interp(TAIL_TURN_06, u)

    arm = rigob.data
    R = {}
    for b in arm.bones:
        name = b.name
        if name.startswith("v"):
            kk = int(name[1:])
            s_c = 0.5 * (J[kk - 1] + (J[kk] if kk < len(J) else (n - 1) * step))
            _, T0, D0 = axis_at(s_c)
            T1 = rot2(theta(s_c))
            D1 = rot2(theta(s_c) + 90.0)
            R[name] = frame(T1, D1) @ frame(T0, D0).inverted()
        elif name == "head":
            T0 = (b.tail_local - b.head_local).normalized()
            D0 = head_dorsal(b)
            T1 = rot2(pose["head_dir"])
            D1 = rot2(pose["head_dir"] - 90.0)
            R[name] = frame(T1, D1) @ frame(T0, D0).inverted()
    # 四肢: 肢帯は親の椎骨と一緒に動き、girdle_tilt があれば背の端を中心に起こす。
    # 上腕・大腿から先は、目標の向きへ最小の回転で向ける（ねじれは親から引き継ぐ）
    side = limb_sides(arm, axis_at, J, n, step)
    GIRDLE_LOG.clear()
    for b in sorted(arm.bones, key=lambda x: len(x.parent_recursive)):
        if b.name in R:
            continue
        Rp = R[b.parent.name] if b.parent is not None else Matrix.Identity(3)
        tgt = pose["limbs"].get(b.name)
        c = b.name.split("_")[0]
        if b.name.endswith("_girdle") and c in pose.get("girdle_tilt", {}):
            best, bs = 1e9, 0.0
            for i in range(0, n, 5):
                q, _, _ = axis_at(i * step)
                if (q - b.head_local).length < best:
                    best, bs = (q - b.head_local).length, i * step
            F = -rot2(theta(bs)); Vn = -rot2(theta(bs) + 90.0)
            g = Rp @ (b.tail_local - b.head_local)
            phi = math.degrees(math.atan2(g.dot(Vn), g.dot(F)))
            A = F.cross(Vn).normalized()
            delta = pose["girdle_tilt"][c] - phi
            R[b.name] = Matrix.Rotation(math.radians(delta), 3, A) @ Rp
            GIRDLE_LOG[c] = (round(phi, 1), round(delta, 1))
            continue
        if tgt is None:
            R[b.name] = Rp.copy()
            continue
        th, ph = tgt
        sg = side[b.name.split("_")[0]] * S_SIGN
        T1 = (rot2(th) * math.cos(math.radians(ph)) + Vector((0.0, sg * math.sin(math.radians(ph)), 0.0))).normalized()
        T0 = Rp @ (b.tail_local - b.head_local).normalized()
        R[b.name] = T0.rotation_difference(T1).to_matrix() @ Rp
    # 根から順に位置をつなぐ
    head_t = {}
    for b in sorted(arm.bones, key=lambda x: len(x.parent_recursive)):
        if b.parent is None:
            head_t[b.name] = b.head_local.copy()
        else:
            p = b.parent
            head_t[b.name] = head_t[p.name] + R[p.name] @ (b.head_local - p.head_local)
    for b in sorted(arm.bones, key=lambda x: len(x.parent_recursive)):
        pb = rigob.pose.bones[b.name]
        Mw = Matrix.Translation(head_t[b.name]) @ R[b.name].to_4x4() @ Matrix.Translation(-b.head_local)
        pb.matrix = Mw @ b.matrix_local
        bpy.context.view_layer.update()


FPS = 24
LOOP_SEC = 12.0
TAIL_TIGHTEN_DEG = 30.0       # 尾全体で足す巻きの最大量（仮）
HAND_SWAY_DEG = 4.0           # 仮
FOOT_SWAY_DEG = 3.0           # 仮
HEAD_NOD_DEG = 1.0            # 仮
# 呼吸（肋骨）: カメレオンの安静時の呼吸数は文献で見つからなかった（2026-10-13）。体重の近いトッケイヤモリ
# （Gekko gecko、36〜151 g）の 24 °C で約 9 回/分（Milsom 1984, J Exp Biol 113:203–214, Table 1）を仮に使う
# （プロデューサー了承）。12 秒のループに収めるため 2 回/12 秒 = 10 回/分にする（表の 9 ± 2 の中）。
# トカゲは肋骨を頭の側・外へ回して吸う（Brainerd & Owerkowicz 2006, Respir Physiol Neurobiol 154:73–88, p.75）。
# 体温が上がると、息を止める時間が短くなって呼吸が増える（Milsom 1984）。吸う・吐くのあとに止める時間を置く。
# 回す角と、吸う・吐く・止める時間の割り振りは、見た目で決めた仮の値
BREATHS_PER_LOOP = 2
RIB_BREATH_DEG = 4.0          # 仮
BREATH_SHAPE = (0.3, 0.3)     # 1 回の呼吸のうち、吸う・吐くの割合（残りは止める）。仮
ACTION_NAME = "CH_Hover"
LATERAL = Vector((0.0, 1.0, 0.0))     # +Y まわりの正の回転 = θ が減る = 腹側へ巻く


def bump(t, period, phase=0.0):
    return 0.5 - 0.5 * math.cos(2 * math.pi * (t / period + phase))


def wave(t, period, phase=0.0):
    return math.sin(2 * math.pi * (t / period + phase))


def breath(t):
    """0 → 1（吸い切り）→ 0、そのあと止める。"""
    period = LOOP_SEC / BREATHS_PER_LOOP
    u = (t % period) / period
    a, b = BREATH_SHAPE
    sm = lambda x: x * x * (3 - 2 * x)
    if u < a: return sm(u / a)
    if u < a + b: return sm(1 - (u - a) / b)
    return 0.0


def rib_axes(rigob):
    """肋骨ごとの、吸うときの回転軸（骨の局所座標）。肋骨を頭の側と外側の間へ回す（Brainerd & Owerkowicz 2006）。"""
    out = {}
    for pb in rigob.pose.bones:
        if not pb.name.startswith("rib"):
            continue
        vb = pb.parent
        d = (pb.tail - pb.head).normalized()
        c = -(vb.tail - vb.head).normalized()                 # 頭の側
        o = Vector((0.0, 1.0 if d.y >= 0 else -1.0, 0.0))    # 外側（展示の姿勢の面の法線の向き）
        ax = d.cross((c + o).normalized())
        if ax.length < 1e-6:
            continue
        out[pb.name] = (pb.matrix.to_3x3().inverted() @ ax.normalized()).normalized()
    return out


def write_hover(rigob):
    """瓶の姿勢（いまの姿勢）の上に CH_Hover を書く。"""
    for pb in rigob.pose.bones:
        pb.rotation_mode = "QUATERNION"
    bpy.context.view_layer.update()
    base = {pb.name: pb.rotation_quaternion.copy() for pb in rigob.pose.bones}
    axis = {pb.name: (pb.matrix.to_3x3().inverted() @ LATERAL).normalized() for pb in rigob.pose.bones}
    ch = []
    names = [pb.name for pb in rigob.pose.bones]
    caud = sorted((n for n in names if n.startswith("v") and int(n[1:]) > 22), key=lambda n: int(n[1:]))
    w = [(i + 1) / len(caud) for i in range(len(caud))]
    ws = sum(w)
    for i, n in enumerate(caud):
        ch.append((n, TAIL_TIGHTEN_DEG * w[i] / ws, lambda t: bump(t, LOOP_SEC)))
    for c, ph in (("fR", 0.0), ("fL", 0.37), ("hL", 0.18), ("hR", 0.55)):
        dist = "hand" if c[0] == "f" else "foot"
        amp = HAND_SWAY_DEG if c[0] == "f" else FOOT_SWAY_DEG
        if f"{c}_{dist}" in names:
            ch.append((f"{c}_{dist}", amp, lambda t, ph=ph: wave(t, 4.0, ph)))
        if f"{c}_lower" in names:
            ch.append((f"{c}_lower", amp * 0.3, lambda t, ph=ph: wave(t, 6.0, ph + 0.2)))
    ch.append(("head", HEAD_NOD_DEG, lambda t: wave(t, LOOP_SEC)))
    for n, ax in rib_axes(rigob).items():
        axis[n] = ax
        ch.append((n, RIB_BREATH_DEG, breath))
    rigob.animation_data_create()
    old = bpy.data.actions.get(ACTION_NAME)
    if old:
        bpy.data.actions.remove(old)
    act = bpy.data.actions.new(ACTION_NAME)
    rigob.animation_data.action = act
    n = int(round(LOOP_SEC * FPS))
    for f in range(n + 1):                       # 最後のフレームは最初と同じ値（継ぎ目なし）
        t = (f % n) / FPS
        for name, amp, fn in ch:
            pb = rigob.pose.bones[name]
            pb.rotation_quaternion = base[name] @ Quaternion(axis[name], math.radians(amp) * fn(t))
            pb.keyframe_insert("rotation_quaternion", frame=f + 1, group=name)
    # 動かさない骨も 1 フレーム目に姿勢を記録しておく（書き出し先で瓶の姿勢が失われないように）
    moved = {c[0] for c in ch}
    for pb in rigob.pose.bones:
        if pb.name not in moved:
            pb.keyframe_insert("rotation_quaternion", frame=1, group=pb.name)
        pb.keyframe_insert("location", frame=1, group=pb.name)
    act.use_frame_range = True
    act.frame_start, act.frame_end = 1, n
    act.use_cyclic = True
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, n
    return n


def hover_bounds(skel, frames, step=12):
    """ループ中の骨格全体の外接と、瓶の姿勢（1 フレーム目）からの広がり。手順 3 の瓶の空きに使う。"""
    sc = bpy.context.scene
    rest = out = None
    for f in list(range(1, frames + 1, step)) + [frames]:
        sc.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        ev = skel.evaluated_get(dg)
        me = ev.to_mesh()
        V = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", V)
        ev.to_mesh_clear()
        V = V.reshape(-1, 3) @ np.array(skel.matrix_world.to_3x3()).T + np.array(skel.matrix_world.translation)
        mn, mx = V.min(0), V.max(0)
        if rest is None:
            rest, out = (mn, mx), [mn.copy(), mx.copy()]
        out[0] = np.minimum(out[0], mn); out[1] = np.maximum(out[1], mx)
    sc.frame_set(1)
    grow = float(max((rest[0] - out[0]).max(), (out[1] - rest[1]).max()))
    return {"rest_min": rest[0].tolist(), "rest_max": rest[1].tolist(), "loop_min": out[0].tolist(),
            "loop_max": out[1].tolist(), "grow_max": grow}


SKIN_STRETCH_MAX = 2.0      # 展示の姿勢で、辺が静止時の何倍より伸びた膜の面を外すか


def trim_skin(max_ratio=SKIN_STRETCH_MAX):
    """展示の姿勢で大きく伸びた膜の面を外す。CT では手足が胴に押し付けられて外形がつながって写るので、
    手足を開くと、その間に膜が引き伸ばされる。そこを穴として外す（静止時のメッシュから消す）。"""
    ob = bpy.data.objects.get("CH_Skin")
    if ob is None:
        return 0
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg); me = ev.to_mesh()
    n = len(me.vertices)
    P = np.empty(n * 3, np.float32); me.vertices.foreach_get("co", P); P = P.reshape(-1, 3)
    ev.to_mesh_clear()
    R = np.empty(n * 3, np.float32); ob.data.vertices.foreach_get("co", R); R = R.reshape(-1, 3)
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data); bm.faces.ensure_lookup_table()
    bad = []
    for f in bm.faces:
        idx = [v.index for v in f.verts]
        r = max(np.linalg.norm(P[idx[a]] - P[idx[a - 1]]) / max(np.linalg.norm(R[idx[a]] - R[idx[a - 1]]), 1e-6) for a in range(len(idx)))
        if r > max_ratio:
            bad.append(f)
    bmesh.ops.delete(bm, geom=bad, context="FACES")
    bm.to_mesh(ob.data); bm.free(); ob.data.update()
    print(f"[Chameleon CT] 膜: 姿勢で {max_ratio} 倍より伸びた面 {len(bad)} を外した")
    return len(bad)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    g = runpy.run_path(GEN, run_name="chameleon_ct")
    coll, rigob, skel, rig = g["build"]()
    d, _, k = g["load"]()
    if not os.environ.get("CH_REST"):
        build_pose(rigob, d, k, POSE_JAR)
        print("[Chameleon CT] 瓶の姿勢を付けました")
        bpy.context.view_layer.update()
        # 膜は体積のうちに切り離して作ったので、伸びた面を外さない（ct_body_pipeline/softmesh2.py。trim_skin は以前の膜用）
    if argv and argv[0] == "--hover":
        import json
        frames = write_hover(rigob)
        b = hover_bounds(skel, frames)
        print(f"[Chameleon CT] {ACTION_NAME} {frames} フレーム。ループ中の外接の広がり 最大 {b['grow_max']:.3f} L")
        if len(argv) > 1:
            outdir = os.path.abspath(argv[1])
            stride = int(argv[2]) if len(argv) > 2 else 4
            os.makedirs(outdir, exist_ok=True)
            with open(os.path.join(outdir, "hover_bounds.json"), "w", encoding="utf-8") as f:
                json.dump(b, f, indent=1)
            setup_render(coll, skel, 0.5, 12)
            sc = bpy.context.scene
            for i, f in enumerate(range(1, frames + 1, stride)):
                sc.frame_set(f)
                sc.render.filepath = os.path.join(outdir, f"frame_{i:04d}.png")
                bpy.ops.render.render(write_still=True)
    elif argv:
        render(coll, skel, argv[0])


def render(coll, skel, path):
    setup_render(coll, skel)
    sc = bpy.context.scene
    sc.render.filepath = os.path.abspath(path)
    bpy.ops.render.render(write_still=True)


def setup_render(coll, skel, scale=1.0, samples=32, margin=1.08):
    """瓶の面を横から見る正射影のカメラ・光・背景（骨格の外接に合わせる）。"""
    sc = bpy.context.scene
    dg = bpy.context.evaluated_depsgraph_get()
    me = skel.evaluated_get(dg).to_mesh()
    V = np.array([skel.matrix_world @ v.co for v in me.vertices])
    skel.evaluated_get(dg).to_mesh_clear()
    mn, mx = V.min(0), V.max(0)
    c = (mn + mx) / 2
    size = float(max(mx[0] - mn[0], mx[2] - mn[2])) * margin
    cam = bpy.data.objects.new("CH_Cam", bpy.data.cameras.new("CH_Cam"))
    coll.objects.link(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = size
    cam.location = (c[0], mn[1] - 5.0, c[2])
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = next(n for n in world.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (1, 1, 1, 1)
    bg.inputs[1].default_value = 0.35
    li = bpy.data.objects.new("CH_Key", bpy.data.lights.new("CH_Key", "SUN"))
    li.data.energy = 4.0
    li.rotation_euler = (math.radians(60), math.radians(-20), math.radians(10))
    coll.objects.link(li)
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.view_settings.view_transform = "Standard"
    sc.render.resolution_x = sc.render.resolution_y = 1400
    sc.render.resolution_percentage = int(scale * 100)


if __name__ == "__main__":
    main()

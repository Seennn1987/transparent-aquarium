"""
透明標本ケース（specimen）用のイカを .glb に書き出すスクリプト
Blender 5.2 LTS で動作確認済み。

使い方（ターミナル）:
  blender --background --factory-startup --python generate_specimen_squid.py -- <出力 .glb のパス>

水槽のイカ（generate_squid.py → rig_squid.py → animate_squid.py → export_squid_gltf.py）を
ファイルは変えずに読み込み、寄りで見る標本に必要な形だけを差し替えて書き出す。水槽の squid.glb は変わらない。
  - 頭: 腕と同じ筋肉の殻（Head）。腕は頭の前端から直接生え、色の切れ目を作らない
    （頭の殻は前端で薄れ、腕は同じ所で濃くなる）。頭が腕と違って見えるのは中身のため
  - 眼: 前後に長い楕円の眼球（Eyes）、角膜（Cornea）、虹彩のひだ（Iris）、虹彩の裏から奥まで覆う
    網膜の杯（Retina）、網膜の裏から視葉へ出る視神経（OpticNerves）。水晶体（Lens）は溶けるので既定では見えない
  - 頭の中: 頭軟骨・項軟骨・漏斗の軟骨（Cartilage）、眼窩の軟骨（OrbitCartilage）、視葉（OpticLobes）、
    食道を囲む脳の輪（Brain）、平衡器（Statocysts）、食道（Esophagus）
  - 口: 口球（BuccalMass）の中に上下の顎板（Beak）と歯舌（Radula）
  - エンペラ: 縁を薄く波打たせ、縁の濃い縁取りの位置を _rim（縁1 → 付け根0）として焼き込む
  - 軟甲: 中央の軸を細い線として見える太さ・色の別部位に（部位 Rachis）
  - 内臓: 消化腺・盲嚢・生殖巣を、くびれと凹凸のある形に
焼き込む値は export_squid_gltf.py と同じ（色 COLOR_0 と _depth）に、全部位の _rim を加える。
"""

import math
import os
import sys
from mathutils import Vector

BLENDER_DIR = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
if not os.path.isdir(BLENDER_DIR):
    raise FileNotFoundError(f"イカのスクリプトのフォルダが見つかりません: {BLENDER_DIR}")


def stage(name, strip):
    """元のスクリプトから、前の段を読み込む行と最後の実行の行を外した本文を返す"""
    text = open(os.path.join(BLENDER_DIR, name), encoding="utf-8").read()
    for line in strip:
        if text.count(line) != 1:
            raise RuntimeError(f"{name} に「{line.strip()}」が1回だけあることを前提にしています")
        text = text.replace(line, "\n")
    return text


def chained(previous):
    return f'\nexec(open(os.path.join(BLENDER_DIR, "{previous}"), encoding="utf-8").read(), globals())\n'


exec(stage("generate_squid.py", ["\nmain()\n"]), globals())

# ------------------------------------------------------------------
# 形の差し替え（寸法は generate_squid.py と同じ ML=1 単位）
# ------------------------------------------------------------------
# 生きている眼: 角膜 → 虹彩/瞳孔 → 球の水晶体（前後移動）→ 虹彩の裏から奥まで覆う網膜 → 視神経 → 視葉。
# 眼は頭軟骨の眼窩に収まり、左右の眼のあいだに脳と視葉がある。
# 透明標本: 水晶体は溶ける。皮膚と筋肉は頭から腕まで同じ空色の一続き。
# 軟骨がいちばん濃い青に染まり、神経は淡く白く濁り、顎板のキチンは琥珀に残る。網膜の色素は脱色で淡い黄緑になる。
COLOR_CARTILAGE = (0.10, 0.45, 0.86, 1.0)
COLOR_IRIS = (0.08, 0.36, 0.82, 1.0)
COLOR_EYE_WALL = (0.70, 0.88, 0.90, 1.0)
COLOR_CORNEA = (0.92, 0.97, 1.0, 1.0)
COLOR_RETINA = (0.80, 0.86, 0.50, 1.0)
COLOR_LENS = (0.95, 0.85, 0.45, 1.0)
COLOR_NERVE = (0.96, 0.93, 0.80, 1.0)
COLOR_STATOCYST = (0.85, 0.93, 0.95, 1.0)
COLOR_BEAK_AMBER = (0.76, 0.60, 0.42, 1.0)
COLOR_RADULA = (0.78, 0.58, 0.32, 1.0)
COLOR_ESOPHAGUS = (0.80, 0.88, 0.55, 1.0)
COLOR_BUCCAL_FADED = (0.90, 0.80, 0.42, 1.0)
COLOR_RACHIS = (0.52, 0.62, 0.38, 1.0)
COLOR_INK_FADED = (0.34, 0.32, 0.40, 1.0)
COLOR_DIGESTIVE_FADED = (0.68, 0.84, 0.32, 1.0)
COLOR_CAECUM_FADED = (0.70, 0.86, 0.48, 1.0)
RACHIS_RADIUS = 0.0016
HEAD_WALL = 0.006               # 頭の筋肉の壁。腕の付け根と同じ濃さに見える厚さ
EYE_WALL = 0.0045
RETINA_WALL = 0.0055            # 網膜は外殻より厚い層
IRIS_THICKNESS = 0.003
CORNEA_THICKNESS = 0.0012
CARTILAGE_THICKNESS = 0.0025
NERVE_RADIUS = 0.0018
EYE_OPEN_ANG = math.radians(48)     # 開口（瞳のまわり）の広さ。光軸からの角度
RETINA_FROM = math.radians(56)      # 網膜は虹彩の付け根のすぐ裏から始まる
EYE_BACK_FLAT = 0.08                # 眼球の奥はやや平たい
FIN_RIM_FROM = 0.8
# 背側の写真で測った比: 眼1つの左右の幅 ≈ 頭の幅の0.35、前後の長さ ≈ 左右の1.5倍、
# 左右の眼のあいだ ≈ 頭の幅の0.28（脳と視葉が入る）。頭の半幅 0.112 から決める。
EYE_CENTER = (-0.085, 0.074, 0.012)
EYE_AXES = (0.064, 0.043, 0.058)    # 前後（体の軸）・光軸（左右）・背腹の半径
LOBE_CENTER = (-0.058, 0.024, 0.008)
# 頭の殻は前端で薄れ、同じ区間で腕が濃くなる（足し合わせて一定）
CROWN_FROM, CROWN_TO = HEAD_FRONT_X + 0.04, HEAD_FRONT_X - 0.035
HEAD_PROFILE = [
    (0.075, 0.012, 0.010),
    (0.068, 0.040, 0.032),
    (0.05, 0.058, 0.048),
    (0.015, 0.068, 0.055),
    (-0.03, 0.092, 0.066),
    (-0.085, 0.112, 0.076),
    (-0.135, 0.098, 0.070),
    (-0.18, 0.078, 0.062),
    # 前端はすぼめない。腕の付け根の輪（腕冠）と同じ太さのまま薄れていく
    (HEAD_FRONT_X, 0.072, 0.059),
    (HEAD_FRONT_X - 0.025, 0.070, 0.057),
    (HEAD_FRONT_X - 0.035, 0.069, 0.056),
]


def crown_fade(x):
    return min(max((x - CROWN_FROM) / (CROWN_TO - CROWN_FROM), 0.0), 1.0)


def head_radii(x):
    ry = interp([(-p[0], p[1]) for p in HEAD_PROFILE], -x)
    rz = interp([(-p[0], p[2]) for p in HEAD_PROFILE], -x)
    return ry, rz


def shell(mb, outer, inner, pole_outer=None, pole_inner=None):
    """周方向に閉じた輪の列2組（外面・内面）から厚みのある殻を作る。
    先頭の輪は縁でつなぐ。pole があれば末端をその点でふさぎ、なければ末端も縁でつなぐ"""
    ns = len(outer[0])
    bases = []
    for rings in (outer, inner):
        b = len(mb.verts)
        bases.append(b)
        for ring in rings:
            mb.verts.extend(Vector(p) for p in ring)
        for i in range(len(rings) - 1):
            for k in range(ns):
                a, c = b + i * ns + k, b + i * ns + (k + 1) % ns
                mb.faces.append((a, c, c + ns, a + ns))
    bo, bi = bases
    last = (len(outer) - 1) * ns
    for k in range(ns):
        k2 = (k + 1) % ns
        mb.faces.append((bo + k, bi + k, bi + k2, bo + k2))
        if pole_outer is None:
            mb.faces.append((bo + last + k, bo + last + k2, bi + last + k2, bi + last + k))
    if pole_outer is None:
        return
    for b, pole in ((bo, pole_outer), (bi, pole_inner)):
        p = len(mb.verts)
        mb.verts.append(Vector(pole))
        for k in range(ns):
            mb.faces.append((p, b + last + k, b + last + (k + 1) % ns))


def cup(mb, rings, pole):
    """1枚の面の杯（膜・軟骨の板。厚みは _depth で持つ）"""
    ns = len(rings[0])
    b = len(mb.verts)
    for ring in rings:
        mb.verts.extend(Vector(p) for p in ring)
    for i in range(len(rings) - 1):
        for k in range(ns):
            a, c = b + i * ns + k, b + i * ns + (k + 1) % ns
            mb.faces.append((a, c, c + ns, a + ns))
    p = len(mb.verts)
    mb.verts.append(Vector(pole))
    last = b + (len(rings) - 1) * ns
    for k in range(ns):
        mb.faces.append((p, last + k, last + (k + 1) % ns))


def blade(mb, pts, widths, thick, seg=16):
    """左右に広く上下に薄い断面を曲線に沿わせた板（顎板・歯舌）"""
    side = Vector((0, 1, 0))
    rings = []
    for p, t, w, h in zip(pts, tangents_of(pts), widths, thick):
        n = t.cross(side).normalized()
        rings.append([p + side * w * math.cos(2 * math.pi * k / seg) + n * h * math.sin(2 * math.pi * k / seg)
                      for k in range(seg)])
    mb.loft(rings)


def build_head(head_mb, body_mb):
    """腕と同じ筋肉の殻。前端（腕冠）は開き、腕がそのまま続く。中身は別の部位"""
    ns = 40
    x_back, x_front = HEAD_PROFILE[0][0], HEAD_PROFILE[-1][0]
    outer, inner = [], []
    for i in range(64):
        x = x_front + (x_back - x_front) * i / 63
        ry, rz = head_radii(x)
        ring_o, ring_i = [], []
        for k in range(ns):
            th = 2 * math.pi * k / ns
            ring_o.append((x, ry * math.sin(th), rz * math.cos(th)))
            ring_i.append((x, max(ry - HEAD_WALL, 0.004) * math.sin(th), max(rz - HEAD_WALL, 0.004) * math.cos(th)))
        outer.append(ring_o)
        inner.append(ring_i)
    shell(head_mb, outer, inner, (x_back + 0.004, 0, 0), (x_back, 0, 0))
    body_mb.tube(chain([Vector((0.06, 0, -0.075)), Vector((-0.02, 0, -0.082)), Vector((-0.085, 0, -0.080))], 6),
                 taper(13, 0.04, 0.02), 16)


def eye_frame(side):
    """開口は左右（±Y）で、背側へ約15°。背側の写真で虹彩が細い楕円に見える傾き。斜め前には向けない"""
    c = Vector((EYE_CENTER[0], side * EYE_CENTER[1], EYE_CENTER[2]))
    facing = Vector((0.03, side, 0.27)).normalized()
    along = Vector((1, 0, 0))
    along = (along - facing * facing.dot(along)).normalized()
    up = facing.cross(along)
    return c, facing, along, up


def eye_point(frame, a, ph, grow=0.0):
    """眼球の楕円体の上の点。a: 光軸（開口）からの角度、ph: 光軸まわりの角度、grow: 面の外への厚み"""
    c, facing, along, up = frame
    ax, bf, cz = (s + grow for s in EYE_AXES)
    back = 1 - EYE_BACK_FLAT * max(0.0, -math.cos(a))
    return c + facing * (bf * math.cos(a) * back) + (along * ax * math.sin(ph) + up * cz * math.cos(ph)) * math.sin(a)


def eye_rings(frame, grow, from_a, to_a, n_lat, n_seg):
    """from_a は数値か、ph から角度を返す関数（縁を不揃いにする）"""
    rings = []
    for i in range(n_lat + 1):
        t = i / n_lat
        ring = []
        for j in range(n_seg):
            ph = 2 * math.pi * j / n_seg
            a0 = from_a(ph) if callable(from_a) else from_a
            ring.append(eye_point(frame, a0 + t * (to_a - a0), ph, grow))
        rings.append(ring)
    return rings


def build_eye_wall(mb, frame):
    """眼球の外殻。開口から奥まで閉じた殻（奥に穴を開けない）"""
    end = math.pi - math.pi / 20
    outer = eye_rings(frame, 0.0, EYE_OPEN_ANG, end, 18, 36)
    inner = eye_rings(frame, -EYE_WALL, EYE_OPEN_ANG, end, 18, 36)
    shell(mb, outer, inner, eye_point(frame, math.pi, 0, 0.0), eye_point(frame, math.pi, 0, -EYE_WALL))


def build_cornea(mb, frame):
    """開口を覆う薄い透明の膜（頭の皮膚から続く）"""
    rim = EYE_OPEN_ANG + math.radians(5)
    outer = eye_rings(frame, 0.003, rim, math.pi / 40, 10, 36)
    inner = eye_rings(frame, 0.003 - CORNEA_THICKNESS, rim, math.pi / 40, 10, 36)
    shell(mb, outer, inner, eye_point(frame, 0, 0, 0.003), eye_point(frame, 0, 0, 0.003 - CORNEA_THICKNESS))


def build_retina(mb, frame):
    """虹彩の付け根の裏から眼の奥までを覆う厚い杯。奥は視神経の出口で、穴ではない"""
    g = -(EYE_WALL + 0.0012)
    end = math.pi - math.pi / 20
    outer = eye_rings(frame, g, RETINA_FROM, end, 16, 36)
    inner = eye_rings(frame, g - RETINA_WALL, RETINA_FROM, end, 16, 36)
    shell(mb, outer, inner, eye_point(frame, math.pi, 0, g), eye_point(frame, math.pi, 0, g - RETINA_WALL))


def build_iris(mb, frame):
    """開口の縁から瞳へ張り出すひだ。幅は場所で違い、瞳は少し横長になる"""
    c, facing, along, up = frame
    n_seg, n_u = 36, 6
    rim_axis = c + facing * (EYE_AXES[1] * math.cos(EYE_OPEN_ANG))
    outer, inner = [], []
    for i in range(n_u + 1):
        u = i / n_u
        ring_o, ring_i = [], []
        for j in range(n_seg):
            ph = 2 * math.pi * j / n_seg
            radial = eye_point(frame, EYE_OPEN_ANG, ph, -EYE_WALL * 0.5) - rim_axis
            pupil = 0.42 + 0.06 * math.cos(2 * ph) + 0.03 * math.sin(3 * ph + 0.7)
            p = rim_axis + radial * (1 - u * (1 - pupil)) - facing * (0.004 * u + 0.0015 * math.sin(math.pi * u))
            half = IRIS_THICKNESS * (1.25 - 0.6 * u) / 2
            ring_o.append(p + facing * half)
            ring_i.append(p - facing * half)
        outer.append(ring_o)
        inner.append(ring_i)
    shell(mb, outer, inner)


def build_lens(mb, frame):
    """水晶体。透明標本では溶けるので、画面側で残りの量を決める（既定0）"""
    c, facing, _, _ = frame
    mb.ellipsoid(c + facing * (EYE_AXES[1] * math.cos(EYE_OPEN_ANG) - 0.012), 0.024, 0.024, 0.024, seg=20, rings=12)


def build_optic_nerves(mb, frame, side):
    """網膜の裏の奥寄りから、後ろ内側の視葉へ扇状に集まる束"""
    lobe = Vector((LOBE_CENTER[0], side * LOBE_CENTER[1], LOBE_CENTER[2]))
    for k in range(9):
        a = math.pi - 0.28 - 0.14 * (k % 3)
        ph = math.pi * (0.22 + 0.56 * k / 8)
        start = eye_point(frame, a, ph, -EYE_WALL)
        end = lobe + (start - lobe).normalized() * 0.011
        mid = start.lerp(end, 0.5) + Vector((0.004, 0, 0))
        mb.tube(chain([start, mid, end], 4), taper(9, NERVE_RADIUS, NERVE_RADIUS * 1.3), 6)


def build_orbit(mb, frame):
    """眼窩の軟骨: 眼球の奥を包む杯。縁は不揃い"""
    end = math.pi - math.pi / 20
    rings = eye_rings(frame, 0.004, lambda ph: math.radians(104 + 12 * math.sin(2 * ph + 0.5)), end, 10, 36)
    cup(mb, rings, eye_point(frame, math.pi, 0, 0.004))


def build_eyes(eye_mb, parts=None):
    """外殻は main() が Eyes として書き出す。parts があれば眼のほかの部品も作る"""
    for side in (1, -1):
        frame = eye_frame(side)
        build_eye_wall(eye_mb, frame)
        if parts is None:
            continue
        build_cornea(parts["Cornea"], frame)
        build_iris(parts["Iris"], frame)
        build_retina(parts["Retina"], frame)
        build_lens(parts["Lens"], frame)
        build_optic_nerves(parts["OpticNerves"], frame, side)
        build_orbit(parts["OrbitCartilage"], frame)


def kidney(side):
    """視葉: 眼に向いた外側がくぼんだ豆の形（lumpy の cos(ph) > 0 が +Y 側）"""
    return lambda t, ph: (1 - 0.28 * max(0.0, side * math.cos(ph)) ** 2 * math.sin(math.pi * t)) \
        * (1 + 0.04 * math.sin(5 * ph + 3 * t))


def build_brain(lobes, brain, statocysts):
    for side in (1, -1):
        c = Vector((LOBE_CENTER[0], side * LOBE_CENTER[1], LOBE_CENTER[2]))
        lumpy(lobes, c, 0.028, 0.012, 0.022, kidney(side), seg=24, rings=16)
        statocysts.ellipsoid(Vector((-0.072, side * 0.011, -0.042)), 0.0075, 0.0075, 0.0075, seg=12, rings=8)
        # 脳と食道の横をつなぐ神経の束（食道を囲む輪）と、視葉へ向かう太い視索
        brain.tube(chain([Vector((-0.083, side * 0.010, 0.016)), Vector((-0.09, side * 0.014, 0.0)),
                          Vector((-0.098, side * 0.010, -0.014))], 4), [0.004] * 9, 8)
        brain.tube(chain([Vector((-0.072, side * 0.008, 0.02)), Vector((-0.064, side * 0.014, 0.012))], 4),
                   taper(5, 0.004, 0.006), 8)
    # 食道の上の脳神経節、下の足神経節、前の腕神経節、後ろの内臓神経節
    lumpy(brain, Vector((-0.078, 0, 0.024)), 0.030, 0.014, 0.012,
          lambda t, ph: 1 + 0.06 * math.sin(4 * math.pi * t + 2 * ph), seg=22, rings=14)
    lumpy(brain, Vector((-0.105, 0, -0.022)), 0.034, 0.015, 0.013,
          lambda t, ph: 1 + 0.05 * math.sin(3 * math.pi * t + 3 * ph), seg=22, rings=14)
    brain.ellipsoid(Vector((-0.145, 0, -0.004)), 0.014, 0.012, 0.010, seg=14, rings=8)
    brain.ellipsoid(Vector((-0.060, 0, -0.026)), 0.020, 0.012, 0.011, seg=14, rings=8)


def build_cartilage(mb):
    """頭軟骨（脳を包む箱）・項軟骨（首の背側の板）・漏斗の付け根の軟骨"""
    lumpy(mb, Vector((-0.088, 0, 0.0)), 0.058, 0.02, 0.046,
          lambda t, ph: 1 + 0.05 * math.sin(3 * math.pi * t + 2 * ph) + 0.03 * math.sin(5 * ph), seg=28, rings=18)
    x = 0.022
    mb.ellipsoid(Vector((x, 0, head_radii(x)[1] - HEAD_WALL - 0.003)), 0.042, 0.02, 0.002, seg=20, rings=8)
    for side in (1, -1):
        mb.ellipsoid(Vector((0.035, side * 0.034, -0.07)), 0.016, 0.006, 0.003, seg=16, rings=8)


def build_mouth(buccal_mb, beak_mb, radula_mb=None):
    """口球の中に上下の顎板（キチンの鉤）と歯舌。黒い三角にはしない"""
    lumpy(buccal_mb, Vector((HEAD_FRONT_X - 0.008, 0, 0)), 0.032, 0.03, 0.03,
          lambda t, ph: 1 + 0.06 * math.sin(2 * math.pi * t) * math.cos(2 * ph), seg=20, rings=14)
    upper = chain([(-0.198, 0, 0.022), (-0.225, 0, 0.020), (-0.245, 0, 0.011), (-0.256, 0, -0.002),
                   (-0.254, 0, -0.011)], 4)
    lower = chain([(-0.195, 0, -0.024), (-0.225, 0, -0.021), (-0.243, 0, -0.012), (-0.251, 0, 0.0),
                   (-0.247, 0, 0.007)], 4)
    # 翼の後ろの縁は丸く細り、先の嘴（くちばし）へ尖る
    wing = lambda n, w: [w * math.sin(math.pi * (0.08 + 0.92 * i / (n - 1))) ** 0.6 * (1 - i / (n - 1)) ** 0.8
                         + 0.001 for i in range(n)]
    blade(beak_mb, upper, wing(len(upper), 0.019), taper(len(upper), 0.004, 0.0008))
    blade(beak_mb, lower, wing(len(lower), 0.023), taper(len(lower), 0.004, 0.0008))
    if radula_mb is not None:
        ribbon = chain([(-0.236, 0, -0.006), (-0.222, 0, -0.012), (-0.205, 0, -0.010), (-0.19, 0, -0.004)], 4)
        blade(radula_mb, ribbon, taper(len(ribbon), 0.005, 0.003), [0.0008] * len(ribbon), seg=10)


def build_esophagus(mb):
    """口球から脳の輪の中を通り、消化腺へ"""
    pts = chain([(-0.215, 0, 0.0), (-0.17, 0, 0.004), (-0.12, 0, 0.002), (-0.09, 0, 0.0), (-0.05, 0, 0.002),
                 (0.02, 0, 0.008), (0.08, 0, 0.008), (0.115, 0, 0.0)], 5)
    mb.tube(pts, taper(len(pts), 0.004, 0.0035), 10)


def build_fins(fin_mb):
    nu, nv = 60, 16
    for side in (1, -1):
        top, bot, thick = [], [], []
        for i in range(nu + 1):
            q = i / nu
            u = FIN_START + (FIN_END - 0.005 - FIN_START) * q
            r = mantle_r(u)
            y0, z0 = r * 0.78, r * MANTLE_FLATTEN * 0.5
            w = fin_width(q)
            end_taper = min(1.0, w / 0.05)
            # 縁ほど大きく、前後に細かく波打つ（面の外へのうねりと、縁の出入り）
            ripple = math.sin(2 * math.pi * 6 * q + 0.4) * end_taper
            scallop = 1 + 0.035 * math.sin(2 * math.pi * 9 * q + 1.1) * end_taper
            row_t, row_b, thick_row = [], [], []
            for j in range(nv + 1):
                v = j / nv
                th = FIN_BASE_THICKNESS * end_taper * (1 - v) ** 1.6 + 0.0006
                z = z0 * (1 - v) - 0.012 * v + 0.010 * ripple * v ** 2.5
                y = side * (y0 + (w + r * 0.22) * v * (1 + (scallop - 1) * v * v))
                row_t.append((u, y, z + th / 2))
                row_b.append((u, y, z - th / 2))
                thick_row.append(th / FIN_BASE_THICKNESS)
            top.append(row_t)
            bot.append(row_b)
            thick.append(thick_row)
        fin_mb.sheet(top, bot)
        flat = [t for row in thick for t in row]
        grid_q = [i / nu for i in range(nu + 1) for _ in range(nv + 1)]
        grid_v = [j / nv for _ in range(nu + 1) for j in range(nv + 1)]
        rim = [max(v - FIN_RIM_FROM, 0.0) / (1 - FIN_RIM_FROM) for v in grid_v]
        fin_mb.attrs.setdefault("thickness", []).extend(flat + flat)
        fin_mb.attrs.setdefault("fin_q", []).extend(grid_q + grid_q)
        fin_mb.attrs.setdefault("fin_v", []).extend(grid_v + grid_v)
        fin_mb.attrs.setdefault("rim", []).extend(rim + rim)


def lumpy(mb, c, rx, ry, rz, shape, seg=28, rings=24):
    """X方向に長い楕円体を、shape(t, 周りの角度)（t: 前0→後1）倍に膨らませた袋（くびれ・凹凸）"""
    base = len(mb.verts)
    for i in range(1, rings):
        th = math.pi * i / rings
        t = i / rings
        for k in range(seg):
            ph = 2 * math.pi * k / seg
            f = shape(t, ph)
            mb.verts.append(Vector((c.x - rx * math.cos(th),
                                    c.y + ry * math.sin(th) * math.cos(ph) * f,
                                    c.z + rz * math.sin(th) * math.sin(ph) * f)))
    front = len(mb.verts)
    mb.verts.append(Vector((c.x - rx, c.y, c.z)))
    back = len(mb.verts)
    mb.verts.append(Vector((c.x + rx, c.y, c.z)))
    for i in range(rings - 2):
        for k in range(seg):
            a = base + i * seg + k
            b = base + i * seg + (k + 1) % seg
            mb.faces.append((a, b, b + seg, a + seg))
    last = base + (rings - 2) * seg
    for k in range(seg):
        mb.faces.append((front, base + (k + 1) % seg, base + k))
        mb.faces.append((back, last + k, last + (k + 1) % seg))


def pinch(t, at, depth, width):
    return 1 - depth * math.exp(-((t - at) / width) ** 2)


def build_viscera(mats_mb):
    dig, cae, gon, ink, gladius, gill, rachis_mb = (mats_mb[k] for k in (
        "digestive", "caecum", "gonad", "ink", "gladius", "gill", "rachis"))
    # 消化腺: 2か所でくびれた、表面のなだらかな凸凹のある細長い袋
    lumpy(dig, Vector((0.40, 0, -0.005)), 0.30, 0.055, 0.05,
          lambda t, ph: pinch(t, 0.34, 0.22, 0.06) * pinch(t, 0.7, 0.18, 0.05)
          * (1 + 0.05 * math.sin(7 * math.pi * t + 3 * ph) * math.sin(2 * ph + 1)))
    # 盲嚢: 前後に並ぶ小さなふくらみ
    lumpy(cae, Vector((0.74, 0, -0.01)), 0.13, 0.032, 0.026,
          lambda t, ph: 1 + 0.12 * math.sin(2 * math.pi * 4 * t) + 0.04 * math.sin(3 * ph), seg=22, rings=20)
    # 生殖巣: 房のように分かれた凹凸
    lumpy(gon, Vector((0.86, 0, 0.0)), 0.07, 0.02, 0.016,
          lambda t, ph: 1 + 0.15 * math.sin(3 * ph + 12 * t) * math.sin(math.pi * t), seg=20, rings=14)
    ink.ellipsoid(Vector((0.14, 0, -0.035)), 0.04, 0.012, 0.011, seg=16, rings=10)
    ink.tube(chain([Vector((0.11, 0, -0.04)), Vector((0.05, 0, -0.05)), Vector((0.0, 0, -0.058))], 5),
             taper(11, 0.006, 0.004), 8)

    nu, nv = 60, 8
    top, bot, rachis = [], [], []
    for i in range(nu + 1):
        u = -0.01 + 0.97 * i / nu
        q = (u + 0.01) / 0.97
        g = 0.03 * (math.sin(math.pi * q) ** 0.6) * (1.2 - 0.45 * q) + 0.002
        r = mantle_r(u)
        row_t, row_b = [], []
        for j in range(nv + 1):
            y = -g + 2 * g * j / nv
            z = r * MANTLE_FLATTEN * math.sqrt(max(0.0, 1 - (y / r) ** 2)) * 0.9 - 0.004
            row_t.append((u, y, z + 0.0015))
            row_b.append((u, y, z - 0.0015))
        top.append(row_t)
        bot.append(row_b)
        rachis.append(Vector((u, 0, r * MANTLE_FLATTEN * 0.9 - 0.006)))
    gladius.sheet(top, bot)
    rachis_mb.tube(rachis, taper(len(rachis), RACHIS_RADIUS, 0.0012), 8)

    for side in (1, -1):
        a = Vector((0.04, side * 0.072, -0.035))
        b = Vector((0.36, side * 0.052, -0.042))
        gill.tube([a.lerp(b, i / 10) for i in range(11)], taper(11, 0.006, 0.003), 8)
        for k in range(26):
            f = (k + 0.5) / 26
            c = a.lerp(b, f)
            h = 0.02 * math.sin(math.pi * (0.15 + 0.85 * f)) + 0.004
            gill.ellipsoid(c, 0.0035, h, h * 0.8, seg=10, rings=6)


SPECIMEN_PARTS = {   # 部位名: 3D ビューで見るときの色（書き出しの色は tint_of）
    "Cornea": COLOR_CORNEA,
    "Iris": COLOR_IRIS,
    "Retina": COLOR_RETINA,
    "Lens": COLOR_LENS,
    "OpticNerves": COLOR_NERVE,
    "OrbitCartilage": COLOR_CARTILAGE,
    "OpticLobes": COLOR_NERVE,
    "Brain": COLOR_NERVE,
    "Statocysts": COLOR_STATOCYST,
    "Cartilage": COLOR_CARTILAGE,
    "Radula": COLOR_RADULA,
    "Esophagus": COLOR_ESOPHAGUS,
}


def build_specimen_extras():
    """main() が作らない部位（眼の部品・軟骨・脳と視葉・平衡器・歯舌・食道）を足す"""
    coll = bpy.data.collections[SPECIES["name"]]
    root = bpy.data.objects[SPECIES["name"] + "_Root"]
    parts = {name: MeshBuilder() for name in SPECIMEN_PARTS}
    build_eyes(MeshBuilder(), parts)
    build_brain(parts["OpticLobes"], parts["Brain"], parts["Statocysts"])
    build_cartilage(parts["Cartilage"])
    build_mouth(MeshBuilder(), MeshBuilder(), parts["Radula"])
    build_esophagus(parts["Esophagus"])
    for name, color in SPECIMEN_PARTS.items():
        emit(name, parts[name], make_glossy_material(name, color, roughness=0.45, alpha=0.4, coat=0.0), coll, root)


_build_viscera = build_viscera


def build_viscera_with_rachis(mats_mb):
    mats_mb["rachis"] = MeshBuilder()
    _build_viscera(mats_mb)
    coll = bpy.data.collections[SPECIES["name"]]
    root = bpy.data.objects[SPECIES["name"] + "_Root"]
    emit("Rachis", mats_mb.pop("rachis"),
         make_glossy_material("Rachis", COLOR_RACHIS, roughness=0.55, alpha=0.22, coat=0.0), coll, root)


build_viscera = build_viscera_with_rachis
main()
build_specimen_extras()

exec(stage("rig_squid.py", [chained("generate_squid.py"), "\nrig_squid()\n"]), globals())
HEAD_PARTS = HEAD_PARTS + tuple(SPECIMEN_PARTS)
MANTLE_PARTS = MANTLE_PARTS + ("Rachis",)
rig_squid()

exec(stage("animate_squid.py", [chained("rig_squid.py")]), globals())

exec(stage("export_squid_gltf.py", [chained("animate_squid.py"), "\nmain_export()\n"]), globals())
ORGAN_DEPTH.update({   # 膜・板は1枚あたりの厚み、かたまりは太さ（画面側の film / solid と対）
    "Rachis": RACHIS_RADIUS,
    "Eyes": EYE_WALL / 2,
    "Cornea": CORNEA_THICKNESS / 2,
    "Iris": IRIS_THICKNESS / 2,
    "Retina": RETINA_WALL / 2,
    "Lens": 0.024,
    "OpticNerves": NERVE_RADIUS,
    "OpticLobes": 0.013,
    "Brain": 0.012,
    "Statocysts": 0.0075,
    "Cartilage": CARTILAGE_THICKNESS,
    "OrbitCartilage": CARTILAGE_THICKNESS,
    "Beak": 0.002,
    "Radula": 0.0006,
    "Esophagus": 0.004,
})
_tint_of, _depth_values, _bake_attributes = tint_of, depth_values, bake_attributes
SPECIMEN_TINT = {
    "Rachis": COLOR_RACHIS,
    "Eyes": COLOR_EYE_WALL,
    "Cornea": COLOR_CORNEA,
    "Iris": COLOR_IRIS,
    "Retina": COLOR_RETINA,
    "Lens": COLOR_LENS,
    "OpticNerves": COLOR_NERVE,
    "OpticLobes": COLOR_NERVE,
    "Brain": COLOR_NERVE,
    "Statocysts": COLOR_STATOCYST,
    "Cartilage": COLOR_CARTILAGE,
    "OrbitCartilage": COLOR_CARTILAGE,
    "BuccalMass": COLOR_BUCCAL_FADED,
    "Beak": COLOR_BEAK_AMBER,
    "Radula": COLOR_RADULA,
    "Esophagus": COLOR_ESOPHAGUS,
    "InkSac": COLOR_INK_FADED,
    "DigestiveGland": COLOR_DIGESTIVE_FADED,
    "Caecum": COLOR_CAECUM_FADED,
}


def tint_of(name, co):
    if name == "Head":   # 腕と同じ筋肉の色（水槽の金色の頭はやめる）
        return ramp_color(BODY_TINT_STOPS, (co.x + 1.3) / 2.3)
    if name in SPECIMEN_TINT:
        return tuple(SPECIMEN_TINT[name][:3])
    return _tint_of(name, co)


def depth_values(name, me, limb_lines):
    if name == "Head":
        return [HEAD_WALL / 2] * len(me.vertices)
    return _depth_values(name, me, limb_lines)


def fade_of(name, co):
    """頭の殻と腕を同じ区間で入れ替え、付け根に色の段を作らない"""
    if name == "Arms":
        return crown_fade(co.x)
    if name == "Head":
        return 1.0 - crown_fade(co.x)
    return 1.0


def bake_attributes(parts):
    _bake_attributes(parts)
    for name, obj in parts.items():
        if obj.type != "MESH":
            continue
        me = obj.data
        if "_rim" in me.attributes:
            me.attributes.remove(me.attributes["_rim"])
        rim = [a.value for a in me.attributes["rim"].data] if name == "Fins" else [0.0] * len(me.vertices)
        me.attributes.new("_rim", "FLOAT", "POINT").data.foreach_set("value", rim)


main_export()

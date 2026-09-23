"""
透明標本イカの骨組み（アーマチュア）生成スクリプト
Blender 5.2 LTS で動作確認済み。

使い方:
  - generate_squid.py でイカを作り直したうえで、骨組みを自動で組んで各部位を追従させる
    （このファイルを実行すると generate_squid.py も自動で実行される）
  - MCP for Blender の execute_code にこの内容を渡しても同じ

骨組みの構成（座標は ML=1 の単位。ルートの空オブジェクトで実寸に拡大される）:
  Mantle0〜4 : 胴（外套膜）を前後5区間に分けた骨。骨の太さ方向の拡大縮小で胴を膨らませる／縮める
  Head       : 頭（眼・口・漏斗も一緒に動く）
  Fin{L,R}{k}_in / _out : エンペラ。前後6か所 × 付け根側・縁側の2本。羽ばたき・波打ち・たたみに使う
  {腕の名前}_{i}      : 8本の腕（各6本）と2本の触腕（各10本）の骨の連なり

体全体の移動・向きは骨ではなくルートの空オブジェクトで行う
（色を体の前後位置で決めているため、骨で体全体を動かすと色がずれる）。
"""

import bpy
import json
import math
import os
from mathutils import Vector

BLENDER_DIR = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
if not os.path.isdir(BLENDER_DIR):
    raise FileNotFoundError(f"イカのスクリプトのフォルダが見つかりません: {BLENDER_DIR}")
exec(open(os.path.join(BLENDER_DIR, "generate_squid.py"), encoding="utf-8").read(), globals())

MANTLE_BONES = 5
FIN_STATIONS = 6
ARM_BONES = 6
TENTACLE_BONES = 10
UP = Vector((0, 0, 1))

HEAD_PARTS = ("Head", "Eyes", "BuccalMass", "Beak", "Funnel")
MANTLE_PARTS = ("Mantle", "DigestiveGland", "Caecum", "Gonad", "InkSac", "Gladius", "Gills")
LIMB_PARTS = ("Arms", "SuckerRings")


# ------------------------------------------------------------------
# 骨の配置
# ------------------------------------------------------------------
def mantle_bone_name(k):
    return f"Mantle{k}"


def mantle_index_at(x):
    return min(max(int(x * MANTLE_BONES), 0), MANTLE_BONES - 1)


def fin_station(q, side):
    """build_fins() と同じ式で、前後位置 q のエンペラの付け根・中ほど・縁の点を返す"""
    u = FIN_START + (FIN_END - 0.005 - FIN_START) * q
    r = mantle_r(u)
    y0, z0 = r * 0.78, r * MANTLE_FLATTEN * 0.5
    w = fin_width(q)
    base = Vector((u, side * y0, z0))
    edge = Vector((u, side * (y0 + w + r * 0.22), -0.012))
    return u, base, (base + edge) / 2, edge


def resample(pts, n):
    """点の列を、長さ方向に等間隔な n+1 点へ並べ直す"""
    pts = [Vector(p) for p in pts]
    lengths = [0.0]
    for a, b in zip(pts, pts[1:]):
        lengths.append(lengths[-1] + (b - a).length)
    out, idx = [], 0
    for i in range(n + 1):
        s = lengths[-1] * i / n
        while idx < len(lengths) - 2 and lengths[idx + 1] < s:
            idx += 1
        f = (s - lengths[idx]) / max(lengths[idx + 1] - lengths[idx], 1e-9)
        out.append(pts[idx].lerp(pts[idx + 1], min(max(f, 0.0), 1.0)))
    return out


def limb_chains(lines):
    chains = []
    for line in lines:
        n = TENTACLE_BONES if line["name"].startswith("Tentacle") else ARM_BONES
        chains.append((line["name"], resample(line["pts"], n), Vector(line["radial"])))
    return chains


def edit_context():
    """起動中の Blender から実行されたときは、画面付きの状態で編集モードに入る"""
    if bpy.app.background:
        return {}
    wm = bpy.context.window_manager
    window = wm.windows[0]
    area = next((a for a in window.screen.areas if a.type == "VIEW_3D"), None)
    if area is None:
        raise RuntimeError("3Dビューが見つからないため、骨組みを編集できません")
    return {"window": window, "screen": window.screen, "area": area}


def build_armature(coll, root, chains):
    for arm in list(bpy.data.armatures):
        if arm.users == 0 and arm.name.startswith(PREFIX):
            bpy.data.armatures.remove(arm)
    data = bpy.data.armatures.new(PREFIX + "Rig")
    data.display_type = "STICK"
    rig = bpy.data.objects.new("Rig", data)
    rig["squid_part"] = "Rig"
    rig.show_in_front = True
    coll.objects.link(rig)
    rig.parent = root

    view_layer = bpy.context.view_layer
    with bpy.context.temp_override(**edit_context()):
        if bpy.context.object is not None and bpy.context.object.mode != "OBJECT":
            bpy.ops.object.mode_set(mode="OBJECT")
        for obj in view_layer.objects:
            obj.select_set(False)
        view_layer.objects.active = rig
        rig.select_set(True)
        bpy.ops.object.mode_set(mode="EDIT")
        eb = data.edit_bones

        def bone(name, head, tail, parent=None, roll_to=UP, connect=False):
            b = eb.new(name)
            b.head, b.tail = Vector(head), Vector(tail)
            b.align_roll(roll_to)
            b.parent = parent
            b.use_connect = connect and parent is not None
            b.use_deform = True
            return b

        mantle = []
        for k in range(MANTLE_BONES):
            mantle.append(bone(mantle_bone_name(k), (k / MANTLE_BONES, 0, 0), ((k + 1) / MANTLE_BONES, 0, 0)))
        head = bone("Head", (0.06, 0, 0), (HEAD_FRONT_X, 0, 0))

        for side, tag in ((1, "L"), (-1, "R")):
            for k in range(FIN_STATIONS):
                u, base, mid, edge = fin_station(k / (FIN_STATIONS - 1), side)
                inner = bone(f"Fin{tag}{k}_in", base, mid, mantle[mantle_index_at(u)])
                inner.inherit_scale = "NONE"   # 胴の収縮で付け根は内側へ動くが、エンペラ自体は縮めない
                bone(f"Fin{tag}{k}_out", mid, edge, inner, connect=True)

        for name, pts, radial in chains:
            parent = head
            for i in range(len(pts) - 1):
                parent = bone(f"{name}_{i}", pts[i], pts[i + 1], parent, roll_to=radial, connect=i > 0)

        bpy.ops.object.mode_set(mode="OBJECT")
        rig.select_set(False)

    for pb in rig.pose.bones:
        pb.rotation_mode = "XYZ"
    return rig


# ------------------------------------------------------------------
# 各頂点をどの骨に追従させるか（重み付け）
# ------------------------------------------------------------------
def attach(obj, rig):
    mod = obj.modifiers.new("Rig", "ARMATURE")
    mod.object = rig


def assign(obj, weights):
    """weights: {骨の名前: [(頂点番号, 重み), ...]}"""
    for bone_name, items in weights.items():
        vg = obj.vertex_groups.get(bone_name) or obj.vertex_groups.new(name=bone_name)
        for idx, w in items:
            if w > 1e-4:
                vg.add([idx], w, "REPLACE")


def smoothstep(e0, e1, x):
    t = min(max((x - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)


def weight_rigid(obj, bone_name):
    assign(obj, {bone_name: [(v.index, 1.0) for v in obj.data.vertices]})


def weight_mantle(obj):
    """前後位置で隣り合う胴の骨2本に按分する"""
    weights = {}
    for v in obj.data.vertices:
        s = min(max(v.co.x * MANTLE_BONES - 0.5, 0.0), MANTLE_BONES - 1.0)
        j = min(int(s), MANTLE_BONES - 2)
        f = s - j
        weights.setdefault(mantle_bone_name(j), []).append((v.index, 1 - f))
        weights.setdefault(mantle_bone_name(j + 1), []).append((v.index, f))
    assign(obj, weights)


def weight_fins(obj):
    me = obj.data
    fq = me.attributes["fin_q"].data
    fv = me.attributes["fin_v"].data
    weights = {}
    for v in me.vertices:
        tag = "L" if v.co.y > 0 else "R"
        s = fq[v.index].value * (FIN_STATIONS - 1)
        j = min(int(s), FIN_STATIONS - 2)
        f = s - j
        outer = smoothstep(0.3, 0.7, fv[v.index].value)
        for k, wk in ((j, 1 - f), (j + 1, f)):
            weights.setdefault(f"Fin{tag}{k}_in", []).append((v.index, wk * (1 - outer)))
            weights.setdefault(f"Fin{tag}{k}_out", []).append((v.index, wk * outer))
    assign(obj, weights)


def weight_limbs(obj, chains):
    """各頂点を、自分の腕の中心線上で一番近い位置の骨（と隣の骨）に按分する"""
    me = obj.data
    ids = me.attributes["limb_id"].data
    weights = {}
    for v in me.vertices:
        name, pts, _ = chains[int(round(ids[v.index].value))]
        best, best_s = None, 0.0
        for i in range(len(pts) - 1):
            a, b = pts[i], pts[i + 1]
            ab = b - a
            t = min(max((v.co - a).dot(ab) / ab.length_squared, 0.0), 1.0)
            d = (a + ab * t - v.co).length
            if best is None or d < best:
                best, best_s = d, i + t
        n = len(pts) - 1
        s = min(max(best_s - 0.5, 0.0), n - 1.0)
        j = min(int(s), n - 2)
        f = s - j
        weights.setdefault(f"{name}_{j}", []).append((v.index, 1 - f))
        weights.setdefault(f"{name}_{j + 1}", []).append((v.index, f))
    assign(obj, weights)


def rig_squid():
    coll = bpy.data.collections[SPECIES["name"]]
    root = bpy.data.objects[SPECIES["name"] + "_Root"]
    parts = squid_parts()
    chains = limb_chains(json.loads(parts["Arms"]["limb_lines"]))
    rig = build_armature(coll, root, chains)

    for name in HEAD_PARTS:
        weight_rigid(parts[name], "Head")
    for name in MANTLE_PARTS:
        weight_mantle(parts[name])
    weight_fins(parts["Fins"])
    for name in LIMB_PARTS:
        weight_limbs(parts[name], chains)

    rigged = HEAD_PARTS + MANTLE_PARTS + LIMB_PARTS + ("Fins",)
    missing = [name for name, o in parts.items() if o.type == "MESH" and name not in rigged]
    if missing:
        raise RuntimeError(f"骨組みに追従しない部位があります: {missing}")
    for name in rigged:
        attach(parts[name], rig)
    rig.hide_set(True)   # 骨の線が半透明の体に重なって見づらいため隠す（隠しても体は骨に従って動く）
    print(f"[{SPECIES['name']}] 骨組み完了: 骨 {len(rig.data.bones)} 本")
    return rig


rig_squid()

"""手・足の指の 2 つの束に骨を足す（計画書 C の記録 62 の案。2026-10-24）。export_chameleon_gltf.py が呼ぶ（記録 63 から既定。DIGIT_BONES=0 で止める）。

プロデューサー（2026-10-24）「Blender で手足に指の骨を足し、指の束で枝をつかむ形の案を、本物の写真と並べて見せて下さい。」

カメレオンの指は 2 つの束に分かれて向かい合い、枝を左右からはさむ（前足は内側 3 本・外側 2 本、後ろ足は内側 2 本・外側 3 本。
Diaz & Trainor 2015、ct_body_pipeline/foot_bundles.py）。いままで手・足は骨 1 本（fL_hand など）で、束を開いたり閉じたりできなかった。

骨（手・足ごとに、束ごとに）:
  <手足>_med1・<手足>_med2・<手足>_med_end（内側の束）、<手足>_lat1・<手足>_lat2・<手足>_lat_end（外側の束）
  1 は束の付け根から半ばまで、2 は半ばから指先まで、_end は指先の点（重みなし。ページで向きを取るため）。親は手・足の骨
束と位置は ct_body_pipeline/digit_labels.py の印（work/digits_h33.npz: 頂点ごとの指 1〜5、指ごとの束、指先までの面に沿った距離 tip）から:
  付け根 = その束の頂点のうち tip が大きい方 15% の重心、指先 = tip が小さい方 5% の重心、半ば = その間の BEND_AT
重み: 束の頂点は、付け根→指先の向きに測った割合 f で、付け根の手前（f < 0.1）は手・足の骨へなめらかに戻し、
  BEND_AT のまわり ±BEND_SOFT で 1 から 2 へ移す。膜と爪の鞘は、静止の位置で最も近い骨の頂点と同じ割り振り（手・足の骨にかかっていた重みだけを分ける）
"""
import os

import bpy
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

LIMBS = ("fL_hand", "fR_hand", "hL_foot", "hR_foot")
BEND_AT = float(os.environ.get("DIGIT_BEND_AT", "0.45"))
BEND_SOFT = 0.1


def _smooth(x, a, b):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _ct_to_model(p, k):
    p = np.asarray(p, dtype=np.float64)
    return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k


def plan(d, k, labels_path):
    """手・足ごとの束: {limb: {"med"/"lat": (付け根, 半ば, 指先)}, 頂点ごとの割り振り}。座標はモデルの静止の座標。"""
    L = np.load(labels_path)
    out = {}
    for limb in LIMBS:
        V = _ct_to_model(d[limb + "__v"], k)
        if len(V) != len(L[limb + "__label"]):
            raise RuntimeError(f"{limb}: 骨の頂点数 {len(V)} と印 {len(L[limb + '__label'])} が合わない（digit_labels.py を回し直す）")
        lab = L[limb + "__label"]; bmap = L[limb + "__bundle"]; tip = L[limb + "__tip"]
        hind = limb.startswith("h")
        bundles = {}
        share = np.zeros((len(V), 5))   # 手・足の骨、med1、med2、lat1、lat2
        share[:, 0] = 1.0
        for b in (1, 2):
            digits = [i for i in range(1, 6) if bmap[i] == b]
            side = ("med" if len(digits) == 2 else "lat") if hind else ("med" if len(digits) == 3 else "lat")
            q = np.isin(lab, digits)
            t = tip[q]
            base = V[q][t >= np.percentile(t, 85)].mean(0); end = V[q][t <= np.percentile(t, 5)].mean(0)
            mid = base + BEND_AT * (end - base)
            ax = end - base
            f = (V[q] - base) @ ax / (ax @ ax)
            w_limb = 1.0 - _smooth(f, -0.1, 0.1)
            w2 = _smooth(f, BEND_AT - BEND_SOFT, BEND_AT + BEND_SOFT) * (1.0 - w_limb)
            w1 = 1.0 - w_limb - w2
            j = 1 if side == "med" else 3
            share[q, 0] = w_limb; share[q, j] = w1; share[q, j + 1] = w2
            bundles[side] = (base, mid, end, len(digits))
        out[limb] = {"V": V, "share": share, "bundles": bundles}
    return out


def add_bones(rigob, P):
    """骨組みに束の骨を足す（編集モード）。"""
    arm = rigob.data
    bpy.context.view_layer.objects.active = rigob
    bpy.ops.object.mode_set(mode="EDIT")
    for limb, p in P.items():
        for side, (base, mid, end, n) in p["bundles"].items():
            b1 = arm.edit_bones.new(f"{limb}_{side}1"); b1.head, b1.tail = Vector(base), Vector(mid); b1.parent = arm.edit_bones[limb]
            b2 = arm.edit_bones.new(f"{limb}_{side}2"); b2.head, b2.tail = Vector(mid), Vector(end); b2.parent = b1
            tipdir = Vector(end - mid).normalized() * 0.05
            b3 = arm.edit_bones.new(f"{limb}_{side}_end"); b3.head, b3.tail = Vector(end), Vector(end) + tipdir; b3.parent = b2
            b3.use_deform = True   # 重みはないが、glb の骨に入れる（ページで指先の位置を読む）
    bpy.ops.object.mode_set(mode="OBJECT")


def _names(limb, p):
    s = {side: (f"{limb}_{side}1", f"{limb}_{side}2") for side in p["bundles"]}
    return [limb, s["med"][0], s["med"][1], s["lat"][0], s["lat"][1]]


def reweight(ob, P, rest_of):
    """`ob` の頂点のうち手・足の骨に重みのあるものを、最も近い骨の頂点の割り振りで束の骨へ分ける。`rest_of(ob)` は静止の座標 (n, 3)。"""
    R = rest_of(ob)
    moved = 0
    for limb, p in P.items():
        g = ob.vertex_groups.get(limb)
        if g is None:
            continue
        idx, w = [], []
        for v in ob.data.vertices:
            for e in v.groups:
                if e.group == g.index and e.weight > 0:
                    idx.append(v.index); w.append(e.weight)
        if not idx:
            continue
        idx = np.array(idx); w = np.array(w)
        if "kd" not in p:
            p["kd"] = KDTree(len(p["V"]))
            for i, x in enumerate(p["V"]):
                p["kd"].insert(Vector(x), i)
            p["kd"].balance()
        near = np.array([p["kd"].find(Vector(x))[1] for x in R[idx]])
        sh = p["share"][near] * w[:, None]
        names = _names(limb, p)
        for j, nm in enumerate(names):
            vg = ob.vertex_groups.get(nm) or ob.vertex_groups.new(name=nm)
            q = np.round(sh[:, j] * 64).astype(int)
            for val in np.unique(q):
                sel = idx[q == val].tolist()
                if val > 0:
                    vg.add(sel, val / 64.0, "REPLACE")
                elif j == 0:
                    vg.remove(sel)
        moved += int((sh[:, 0] < w - 1e-6).sum())
    print(f"[digits] {ob.name}: 束の骨へ分けた頂点 {moved}")


def run(rigob, d, k, labels_path):
    P = plan(d, k, labels_path)
    add_bones(rigob, P)

    def rest_of(ob):
        R = np.empty(len(ob.data.vertices) * 3); ob.data.vertices.foreach_get("co", R); return R.reshape(-1, 3)
    for name in ("CH_Skeleton", "CH_Skin", "CH_Organ_claw"):
        ob = bpy.data.objects.get(name)
        if ob is not None:
            reweight(ob, P, rest_of)
    for limb, p in P.items():
        for side, (base, mid, end, n) in p["bundles"].items():
            print(f"[digits] {limb} {side}（指 {n} 本）: 付け根→半ば {np.linalg.norm(mid - base) / k:.2f} mm、半ば→指先 {np.linalg.norm(end - mid) / k:.2f} mm")
    return P

"""
エボシカメレオン透明標本: 全身の骨を CT の形のまま使う骨格（2026-10-12〜）

元データ: MorphoSource Media 000050726（California Academy of Sciences, CAS:HERP:135515,
  Chamaeleo calyptratus calyptratus, oVert）。権利表示 In Copyright – Non-Commercial Use Permitted。
  商用利用は不可。データとここから作ったメッシュは再配布しない（blender/private/ は git に入れない）。
  作り方は build_chameleon_body_from_ct.py。

このスクリプトは blender/private/chameleon_body_ct.npz を読み、
  - 骨 71 本（頭骨 1、椎骨 55、四肢と肢帯 15）を 1 つのメッシュにまとめ、骨ごとの頂点グループ（剛体、重み 1）を付け、
  - CT の関節の位置に骨組みを作る。
基準の姿勢（骨組みの静止姿勢）は CT の姿勢のまま。瓶の姿勢や動きは骨組みの回転だけで作る（rig_chameleon_ct.py）。

軸: CT の (z, y, x)[mm] → Blender (X=y, Y=-x, Z=-z) / 頭骨長。頭骨長（後頭顆〜吻端）= 1.04 L（06 と同じ単位）。
  向きを変えても鏡像にはならない（行列式 +1）。

骨の名前:
  head            頭骨・下顎・強膜輪・舌骨（角鰓骨の長い棒を含む。v01 の子）
  v01〜v55        椎骨（肋骨はその椎骨に含む）。v22 が根（第 1 仙椎の付近）。前は頭へ、後ろは尾の先へ連なる
  fR_* / fL_*     前肢（右・左）。girdle=肩甲骨・烏口骨、upper=上腕、lower=前腕、hand=手根〜指
  hL_* / hR_*     後肢（左・右）。girdle=腰帯（hL のみ。hR 側の腰帯は仙椎に含む）、upper=大腿、lower=下腿、foot=足根〜趾
  左右は ct_body_pipeline/sides.py で、肢帯が体軸のどちら側（前×背の向き）にあるかから決めた。
  CT の断面の並びが右手系であることを仮定している（データに向きの記載がないため、鏡像の可能性は残る）。
"""

import os
import sys

import bpy
import numpy as np
from mathutils import Matrix, Vector

try:
    HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    HERE = "/Users/shoui/transparent-aquarium/transparent-aquarium/blender"
DATA = os.path.join(HERE, "private", "chameleon_body_ct.npz")
PREFIX = "CH_"
FACES_TOTAL = int(os.environ.get("CH_FACES", "450000"))          # 全身の面数の目安（間引き後）
SKULL_LENGTH_L = 1.04
BONE_GRAY = (0.62, 0.60, 0.57, 1.0)
# 胴の肋骨のしなり（soft_rib_weights）: 剛体のままの半径 [mm]、なめらかに移る幅 [mm]、体軸に沿った広がり σ [mm]。None で全て剛体
SOFT_RIBS = None   # 2026-10-13: 肋骨を左右・椎骨ごとの骨にしたので、しなりの重みは使わない（以前は (2.5, 4.0, 4.0)）
TRUNK_END_MM = 104.7          # 胴の終わり（v21 の後ろの関節 = 仙椎の前）


def ct_to_model(p, k):
    p = np.asarray(p, dtype=np.float64)
    return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k


def load():
    d = np.load(DATA)
    names = [str(n) for n in d["rig__names"]]
    i = names.index("head")
    k = SKULL_LENGTH_L / float(np.linalg.norm(d["rig__tail"][i] - d["rig__head"][i]))
    rig = {n: (ct_to_model(d["rig__head"][j], k), ct_to_model(d["rig__tail"][j], k), str(d["rig__parent"][j]) or None)
           for j, n in enumerate(names)}
    return d, rig, k


def decimated_meshes(d, k):
    """骨ごとに間引いたメッシュ（モデル座標）。結果は _dec.npz に保存して次から使う。"""
    dec = DATA.replace(".npz", "_dec.npz")
    if os.path.exists(dec) and os.path.getmtime(dec) >= os.path.getmtime(DATA):
        e = np.load(dec)
        return {n[:-3]: (e[n], e[n[:-3] + "__f"]) for n in e.files if n.endswith("__v")}
    names = sorted({f.split("__")[0] for f in d.files if not f.startswith(("rig__", "soft__", "cart__"))})
    total = sum(len(d[n + "__f"]) for n in names)
    ratio = min(1.0, FACES_TOTAL / total)
    out = {}
    for n in names:
        v = ct_to_model(d[n + "__v"], k).astype(np.float32)
        f = d[n + "__f"][:, ::-1].astype(np.int32)        # 軸の入れ替えで面の向きが反転しないように
        me = bpy.data.meshes.new("_tmp")
        me.from_pydata(v.tolist(), [], f.tolist())
        ob = bpy.data.objects.new("_tmp", me)
        bpy.context.scene.collection.objects.link(ob)
        sm = ob.modifiers.new("S", "SMOOTH")
        sm.factor, sm.iterations = 0.5, 2
        if ratio < 1.0 and len(f) > 400:
            dm = ob.modifiers.new("D", "DECIMATE")
            dm.ratio = max(ratio, 300 / len(f))
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(me)
        me2.calc_loop_triangles()
        V = np.empty(len(me2.vertices) * 3, np.float32)
        me2.vertices.foreach_get("co", V)
        T = np.empty(len(me2.loop_triangles) * 3, np.int32)
        me2.loop_triangles.foreach_get("vertices", T)
        bpy.data.meshes.remove(me2)
        out[n] = (V.reshape(-1, 3), T.reshape(-1, 3))
    np.savez_compressed(dec, **{n + "__v": a for n, (a, b) in out.items()}, **{n + "__f": b for n, (a, b) in out.items()})
    return out


def soft_rib_weights(d, k, V, groups):
    """胴の椎骨（肋骨を含む）の重み。背骨の近くは自分の椎骨だけ（剛体）、体軸から離れるほど
    「体軸で最も近い位置」のまわりの椎骨へなめらかに分ける。
    CT の個体は胴が強く丸まっている（胴で約 130°）。伸ばした姿勢で肋骨を剛体のまま回すと、腹側で肋骨が
    交差したり離れたりする。実物では肋骨の腹側は軟骨でしなるので、腹側ほど体の面に沿って曲がるようにする。
    戻り値: {骨名: (頂点番号, {骨名: 重み})}。"""
    if SOFT_RIBS is None:
        return {}
    r_rigid, r_span = SOFT_RIBS[0] * k, SOFT_RIBS[1] * k
    sigma = SOFT_RIBS[2]                                   # mm（体軸に沿った長さ）
    J = [float(x) for x in d["rig__J"]]
    step = float(d["rig__axis_step"])
    A = ct_to_model(d["rig__axis"], k)
    s_axis = np.arange(len(A)) * step
    trunk = [f"v{i:02d}" for i in range(1, len(J)) if J[i] <= TRUNK_END_MM + 1e-6]
    centers = np.array([0.5 * (J[int(n[1:]) - 1] + J[int(n[1:])]) for n in trunk])
    out = {}
    for n in trunk:
        if n not in groups:
            continue
        a, b = groups[n]
        P = V[a:b]
        # 体軸で最も近い点（ブロックに分けて総当たり）
        best = np.full(len(P), 1e9); si = np.zeros(len(P), int)
        for c0 in range(0, len(A), 256):
            dd = np.linalg.norm(P[:, None, :] - A[None, c0:c0 + 256, :], axis=2)
            j = dd.argmin(1); m = dd[np.arange(len(P)), j] < best
            best[m] = dd[np.arange(len(P)), j][m]; si[m] = c0 + j[m]
        t = np.clip((best - r_rigid) / r_span, 0.0, 1.0)
        alpha = t * t * (3 - 2 * t)
        if not (alpha > 1e-3).any():
            continue
        g = np.exp(-0.5 * ((s_axis[si][:, None] - centers[None, :]) / sigma) ** 2)
        g /= g.sum(1, keepdims=True)
        own = trunk.index(n)
        Wm = alpha[:, None] * g
        Wm[:, own] += 1.0 - alpha
        # 1 頂点 4 本まで（glTF の 1 組の関節数）
        top = np.argsort(-Wm, 1)[:, :4]
        keep = np.zeros_like(Wm, bool); keep[np.arange(len(P))[:, None], top] = True
        Wm = np.where(keep, Wm, 0.0); Wm /= Wm.sum(1, keepdims=True)
        idx = np.arange(a, b)
        out[n] = (idx, {trunk[c]: Wm[:, c] for c in range(len(trunk)) if Wm[:, c].max() > 1e-3})
    return out


SKIN_FACES = int(os.environ.get("CH_SKIN_FACES", "150000"))   # 膜の面数の目安（間引き後）
SKIN_COLOR = (0.90, 0.92, 0.95, 1.0)
SKIN_ALPHA = 0.18           # 仮。透明標本の、白く濁った薄い膜。値は見た目で決めた（第5節の通し光を測り直したら合わせる）


def skin_material():
    mat = bpy.data.materials.get(PREFIX + "Skin") or bpy.data.materials.new(PREFIX + "Skin")
    mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        outn = next((n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None) or mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(bsdf.outputs[0], outn.inputs[0])
    bsdf.inputs["Base Color"].default_value = SKIN_COLOR
    bsdf.inputs["Roughness"].default_value = 0.6
    bsdf.inputs["Alpha"].default_value = SKIN_ALPHA
    try:
        mat.surface_render_method = "BLENDED"
    except Exception:
        pass
    return mat


def build_skin(d, k, coll, rigob, key="soft", name="Skin", material=None):
    """皮膚・筋肉の膜（CT の軟部の外形。ct_body_pipeline/softvol2.py と softmesh2.py）。骨組みに重みで付ける。
    key="visc" で体腔の内臓の一塊（ct_body_pipeline/visceramesh.py）。"""
    soft = DATA.replace("chameleon_body_ct.npz", "chameleon_body_soft.npz")
    if os.path.exists(soft):
        d = np.load(soft)
    if f"{key}__v" not in d.files:
        return None
    V = ct_to_model(d[f"{key}__v"], k).astype(np.float32)
    F = d[f"{key}__f"][:, ::-1].astype(np.int32)
    widx = d[f"{key}__w_idx"]; wval = d[f"{key}__w_val"]; wnames = [str(n) for n in d[f"{key}__names"]]
    me = bpy.data.meshes.new("_skin_tmp"); me.from_pydata(V.tolist(), [], F.tolist())
    tmp = bpy.data.objects.new("_skin_tmp", me); bpy.context.scene.collection.objects.link(tmp)
    if len(F) > SKIN_FACES:
        dm = tmp.modifiers.new("D", "DECIMATE"); dm.ratio = SKIN_FACES / len(F)
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
    bpy.data.objects.remove(tmp); bpy.data.meshes.remove(me)
    me2.name = PREFIX + name
    me2.polygons.foreach_set("use_smooth", np.ones(len(me2.polygons), bool))
    me2.materials.append(material or skin_material())
    ob = bpy.data.objects.new(PREFIX + name, me2); coll.objects.link(ob)
    # 間引いた頂点に、元の最も近い頂点の重みを写す
    from mathutils.kdtree import KDTree
    kd = KDTree(len(V))
    for i, p in enumerate(V):
        kd.insert(p, i)
    kd.balance()
    groups = {}
    for v in me2.vertices:
        _, i, _ = kd.find(v.co)
        for a in range(widx.shape[1]):
            x = float(wval[i, a])
            if x > 1e-3:
                groups.setdefault((wnames[int(widx[i, a])], round(x * 32) / 32), []).append(v.index)
    for (g, x), idx in groups.items():
        vg = ob.vertex_groups.get(g) or ob.vertex_groups.new(name=g)
        vg.add(idx, x, "REPLACE")
    ob.parent = rigob
    mo = ob.modifiers.new("Armature", "ARMATURE"); mo.object = rigob
    print(f"[Chameleon CT] {name} 面 {len(me2.polygons)}")
    return ob


VISCERA_COLOR = (0.50, 0.42, 0.38, 1.0)   # 仮。瓶写真 01 の内臓（液 217 で割った値、1 辺 447px）。Web の色は chameleon-stain.js


def viscera_material():
    mat = bpy.data.materials.get(PREFIX + "Viscera") or bpy.data.materials.new(PREFIX + "Viscera")
    mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is not None:
        bsdf.inputs["Base Color"].default_value = VISCERA_COLOR
    return mat


CART_COLOR = (0.35, 0.55, 0.95, 1.0)   # 仮。軟骨（アルシアンブルーで青）。色は手順 A5 で測った通し光に合わせる


def cartilage_material():
    mat = bpy.data.materials.get(PREFIX + "Cartilage") or bpy.data.materials.new(PREFIX + "Cartilage")
    mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    bsdf.inputs["Base Color"].default_value = CART_COLOR
    bsdf.inputs["Roughness"].default_value = 0.5
    return mat


def build_cartilage(d, k, coll, rigob):
    """肋骨の途切れ（CT で骨の濃さに写らない 0.2〜2 mm の隙間）をつなぐ軟骨の棒（ct_body_pipeline/cartgaps.py）。
    トカゲの腹側の肋骨・胸骨につながる肋骨は軟骨であることが多い（Williston 1925, The Osteology of the Reptiles, 第 3 章）。
    どの隙間も、その肋骨の骨に重み 1 で付ける。"""
    if "cart__a" not in d.files or len(d["cart__a"]) == 0:
        return None
    A = ct_to_model(d["cart__a"], k); Bv = ct_to_model(d["cart__b"], k); R = d["cart__r"] * k; names = [str(n) for n in d["cart__bone"]]
    verts, faces, owner = [], [], []
    NSEG = 8
    for a, b, r, nm in zip(A, Bv, R, names):
        ax = b - a; L = np.linalg.norm(ax)
        if L < 1e-6:
            continue
        u = ax / L; t = np.cross(u, [0, 0, 1.0]); t = t if np.linalg.norm(t) > 1e-3 else np.cross(u, [0, 1.0, 0]); t /= np.linalg.norm(t); w = np.cross(u, t)
        base = len(verts)
        for end in (a - u * r, b + u * r):            # 両端を太さの分だけ骨の中へ差し込む
            for j in range(NSEG):
                th = 2 * np.pi * j / NSEG
                verts.append(end + r * (np.cos(th) * t + np.sin(th) * w)); owner.append(nm)
        for j in range(NSEG):
            j2 = (j + 1) % NSEG
            faces.append((base + j, base + j2, base + NSEG + j2, base + NSEG + j))
        faces.append(tuple(base + j for j in range(NSEG))[::-1]); faces.append(tuple(base + NSEG + j for j in range(NSEG)))
    me = bpy.data.meshes.new(PREFIX + "Cartilage"); me.from_pydata([list(v) for v in verts], [], faces); me.update()
    me.materials.append(cartilage_material())
    ob = bpy.data.objects.new(PREFIX + "Cartilage", me); coll.objects.link(ob)
    for nm in set(owner):
        ob.vertex_groups.new(name=nm).add([i for i, o in enumerate(owner) if o == nm], 1.0, "REPLACE")
    ob.parent = rigob
    mo = ob.modifiers.new("Armature", "ARMATURE"); mo.object = rigob
    print(f"[Chameleon CT] 軟骨（肋骨の途切れ） {len(A)} 本")
    return ob


def bone_material():
    mat = bpy.data.materials.get(PREFIX + "BoneGray") or bpy.data.materials.new(PREFIX + "BoneGray")
    mat.use_nodes = True
    bsdf = next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
    if bsdf is None:
        bsdf = mat.node_tree.nodes.new("ShaderNodeBsdfPrincipled")
        outn = next((n for n in mat.node_tree.nodes if n.type == "OUTPUT_MATERIAL"), None) or mat.node_tree.nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(bsdf.outputs[0], outn.inputs[0])
    bsdf.inputs["Base Color"].default_value = BONE_GRAY
    bsdf.inputs["Roughness"].default_value = 0.55
    return mat


def clear_previous():
    coll = bpy.data.collections.get(PREFIX + "Chameleon")
    if coll:
        for ob in list(coll.objects):
            data = ob.data
            bpy.data.objects.remove(ob, do_unlink=True)
            if data is not None and data.users == 0:
                if isinstance(data, bpy.types.Mesh):
                    bpy.data.meshes.remove(data)
                elif isinstance(data, bpy.types.Armature):
                    bpy.data.armatures.remove(data)
        bpy.data.collections.remove(coll)
    coll = bpy.data.collections.new(PREFIX + "Chameleon")
    bpy.context.scene.collection.children.link(coll)
    return coll


def build():
    d, rig, k = load()
    meshes = decimated_meshes(d, k)
    coll = clear_previous()
    mat = bone_material()
    # 1 つのメッシュにまとめる
    Vs, Fs, groups, off = [], [], {}, 0
    for n, (v, f) in meshes.items():
        Vs.append(v)
        Fs.append(f + off)
        groups[n] = (off, off + len(v))
        off += len(v)
    V = np.concatenate(Vs)
    F = np.concatenate(Fs)
    me = bpy.data.meshes.new(PREFIX + "Skeleton")
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.ravel())
    me.loops.add(F.size)
    me.loops.foreach_set("vertex_index", F.ravel())
    me.polygons.add(len(F))
    me.polygons.foreach_set("loop_start", np.arange(0, F.size, 3))
    me.update()
    me.polygons.foreach_set("use_smooth", np.ones(len(F), bool))
    me.materials.append(mat)
    ob = bpy.data.objects.new(PREFIX + "Skeleton", me)
    coll.objects.link(ob)
    W = soft_rib_weights(d, k, V, groups)
    for n in groups:
        ob.vertex_groups.new(name=n)
    for n, (a, b) in groups.items():
        if n in W:
            continue
        ob.vertex_groups[n].add(list(range(a, b)), 1.0, "REPLACE")
    for n, (idx, wts) in W.items():
        # idx: 頂点番号 (m,)、wts: {骨名: 重み (m,)}。重みを 1/64 刻みにまとめて追加する（頂点ごとの呼び出しは遅い）
        for g, w in wts.items():
            vg = ob.vertex_groups[g]
            qw = np.round(w * 64).astype(int)
            for q in np.unique(qw[qw > 0]):
                vg.add(idx[qw == q].tolist(), q / 64.0, "REPLACE")
    # 骨組み
    arm = bpy.data.armatures.new(PREFIX + "Rig")
    rigob = bpy.data.objects.new(PREFIX + "Rig", arm)
    coll.objects.link(rigob)
    bpy.context.view_layer.objects.active = rigob
    bpy.ops.object.mode_set(mode="EDIT")
    for n, (h, t, p) in rig.items():
        b = arm.edit_bones.new(n)
        b.head, b.tail = Vector(h), Vector(t)
        if (b.tail - b.head).length < 1e-4:
            b.tail = b.head + Vector((0, 0, 0.01))
    for n, (h, t, p) in rig.items():
        if p:
            arm.edit_bones[n].parent = arm.edit_bones[p]
    bpy.ops.object.mode_set(mode="OBJECT")
    arm.display_type = "STICK"
    rigob.show_in_front = True
    ob.parent = rigob
    mo = ob.modifiers.new("Armature", "ARMATURE")
    mo.object = rigob
    build_skin(d, k, coll, rigob)
    build_skin(d, k, coll, rigob, key="visc", name="Viscera", material=viscera_material())
    build_cartilage(d, k, coll, rigob)
    root = bpy.data.objects.new(PREFIX + "Root", None)
    coll.objects.link(root)
    rigob.parent = root
    print(f"[Chameleon CT] 骨 {len(rig)} 本、面 {len(F)}、頭骨長 {SKULL_LENGTH_L} L（{SKULL_LENGTH_L / k:.1f} mm）")
    return coll, rigob, ob, rig


if __name__ == "__main__":
    build()

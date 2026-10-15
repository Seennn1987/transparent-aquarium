"""シロシュモクザメ B1 骨組み（2026-10-15、プロデューサー「B1 をこの案で進めてください」）

a6a_export_gltf.py が組織ごとの部品（HH_Bone など）を作ったあとに、同じ Blender の中で exec される（環境変数 HH_RIG=1）。
軸: Blender の x = 吻端→尾（m）、y = 左右（+ が体の右、u）、z = 背（+）。glTF に書き出すと x はそのまま、+Y が背、+Z = −Blender y。
泳ぎのうねりは、背の軸（Blender z）のまわりに骨を回す左右の曲げ。

骨:
  head          吻端〜126 mm（頭骨・顎・歯・舌の弓。エラの骨は位置で胴の骨と混ぜる）
  spine_00〜    椎骨の境目（a8_vertebrae.json の bounds_mm）を 5 個ずつまとめた区間。背骨の中心の高さは spine_v_mm
  tail          最後の区間〜尾の先（1024 mm）
  pect_L/R      胸びれの付け根（a3d の pect_posed.json の base_right_uzv と鏡映）から外へ。付け根の区間の背骨の骨の子
  pelv_L/R      腹びれの付け根（pelvic_posed.json）から外へ
重み（手順書: いちばん近い骨や重みの和で決めず、体積で切り分けたときの持ち主にする）:
  体軸（x）に沿って骨ごとの区間に切り分け、その区間の骨を持ち主にする。区間の中心と中心の間だけ、隣の骨と直線で混ぜる
  （頭は 100 mm までが頭の骨だけ、100〜140 mm で最初の背骨の骨へ）。
  ひれの骨: 胸びれの付け根の近くの範囲で、体の中心から外へ 40→55 mm でひれの骨へなめらかに移す。腹びれは背骨の重みのまま
  （腹びれの骨は作るが重みは付けない。HH_RIG_PELV=1 で 22→32 mm）。頭は 125 mm まで頭の骨だけ。
環境変数 HH_RIG_TEST=1 のとき: 試しのうねりの姿勢を 4 つ作って、骨が膜から出る量と膜の面の伸びを数え、
  b1_rig_test.json と投影図の点（b1_rig_proj.npz）を HH_WORK に書き、書き出しをせずに終わる。
"""
import bpy, json, math, os
import numpy as np
from mathutils import Vector, Matrix, Quaternion
from mathutils.bvhtree import BVHTree

_work = os.environ.get("HH_WORK") or os.path.join(hh_paths.HERE, "work")
VJ = json.load(open(os.path.join(_work, "a8_vertebrae.json")))
B = np.array(VJ["bounds_mm"]); SV = {int(k): v for k, v in VJ["spine_v_mm"].items()}
def spine_z(xmm):                       # 背骨の中心の Blender z（m）
    ks = np.array(sorted(SV)); return -float(np.interp(xmm, ks, [SV[k] for k in ks])) / 1000.0
PE = json.load(open(os.path.join(hh_paths.DOCS, "pect_posed.json"))); PV = json.load(open(os.path.join(hh_paths.DOCS, "pelvic_posed.json")))
cuts = [0.0] + [float(B[i]) for i in range(5, len(B), 5)] + [1024.0]
cuts = sorted(set([round(c, 2) for c in cuts]))
names = ["head"] + [f"spine_{i:02d}" for i in range(len(cuts) - 3)] + ["tail"]
assert len(names) == len(cuts) - 1

# --- 骨組み ---
arm_data = bpy.data.armatures.new("HH_Rig"); arm = bpy.data.objects.new("HH_Rig", arm_data); coll.objects.link(arm)
bpy.context.view_layer.objects.active = arm; bpy.ops.object.select_all(action="DESELECT"); arm.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
eb = {}
prev = None
for i, nm in enumerate(names):
    a, b = cuts[i], cuts[i + 1]
    e = arm_data.edit_bones.new(nm)
    e.head = Vector((a / 1000, 0, spine_z(a))); e.tail = Vector((b / 1000, 0, spine_z(b)))
    e.roll = 0.0
    if prev is not None: e.parent = prev; e.use_connect = True
    eb[nm] = e; prev = e
def seg_of(xmm): return names[max(0, min(len(names) - 1, int(np.searchsorted(cuts, xmm, side="right") - 1)))]
fins = {}
bu, bz, bv = PE["base_right_uzv"]; pu, pz, pv = PV["base_right_uzv"]
for side, sg in (("R", 1), ("L", -1)):
    for nm, (u, z, v, du) in (("pect", (bu, bz, bv, 70)), ("pelv", (pu, pz, pv, 40))):
        e = arm_data.edit_bones.new(f"{nm}_{side}")
        e.head = Vector((z / 1000, sg * u / 1000, -v / 1000)); e.tail = Vector(((z + du * 0.6) / 1000, sg * (u + du) / 1000, -(v + du * 0.25) / 1000))
        e.parent = eb[seg_of(z)]; fins[(nm, side)] = (z, u, v)
bpy.ops.object.mode_set(mode="OBJECT")
centers = [(cuts[i] + cuts[i + 1]) / 2 for i in range(len(names))]
centers[0] = float(os.environ.get('HH_RIG_HEAD', 125.0))   # 頭: 翼の後ろの端（約 125 mm）までは頭の骨だけ（100 mm では翼の後ろの端が膜から少し出た）

def spine_weights(xmm):
    """体軸の位置 → (骨の名前, 重み) の組。区間の中心どうしの間だけ混ぜる"""
    if xmm <= centers[0]: return [(names[0], 1.0)]
    if xmm >= centers[-1]: return [(names[-1], 1.0)]
    j = int(np.searchsorted(centers, xmm) - 1); t = (xmm - centers[j]) / (centers[j + 1] - centers[j])
    return [(names[j], 1 - t), (names[j + 1], t)]
def smooth(a, b, x): t = min(max((x - a) / (b - a), 0.0), 1.0); return t * t * (3 - 2 * t)
def fin_weight(p_mm):
    """(x, y, z) mm → [(骨, 重み)]: ひれの骨へ移す分"""
    x, y, z = p_mm; out = []
    for (nm, side), (bzm, bum, bvm) in fins.items():
        sg = 1 if side == "R" else -1
        if sg * y <= 0: continue
        if nm == "pelv" and os.environ.get("HH_RIG_PELV") != "1": continue   # 腹びれは背骨の重みのまま（付け根の区間だけで動かすと、後ろの膜が伸びた）
        lat = abs(y)
        if nm == "pect": w = smooth(40, 55, lat) * smooth(bzm - 40, bzm - 25, x) * (1 - smooth(bzm + 70, bzm + 90, x)) * smooth(-z - 10, -z, bvm - 25)
        else: w = smooth(22, 32, lat) * smooth(bzm - 15, bzm - 5, x) * (1 - smooth(bzm + 60, bzm + 75, x)) * smooth(-z, -z + 10, bvm - 15)
        if w > 0: out.append((f"{nm}_{side}", w))
    return out
for ob in [o for o in coll.objects if o.type == "MESH"]:
    me = ob.data; M = ob.matrix_world
    groups = {nm: ob.vertex_groups.new(name=nm) for nm in names + [f"{a}_{s}" for a in ("pect", "pelv") for s in ("L", "R")]}
    for v in me.vertices:
        p = M @ v.co; pm = (p.x * 1000, p.y * 1000, p.z * 1000)
        ws = spine_weights(pm[0]); fw = fin_weight(pm)
        f = min(1.0, sum(w for _, w in fw))
        for nm, w in ws:
            if w * (1 - f) > 1e-4: groups[nm].add([v.index], w * (1 - f), "REPLACE")
        for nm, w in fw: groups[nm].add([v.index], w / max(sum(x for _, x in fw), 1e-9) * f, "REPLACE")
    ob.parent = arm; mod = ob.modifiers.new("Armature", "ARMATURE"); mod.object = arm
print("rig: bones", len(arm_data.bones), "spine segments", len(names))

if os.environ.get("HH_RIG_TEST") == "1":
    # --- 試しのうねり: 尾ほど振れが大きい波（振れ幅は見やすく大きめ）。骨は背の軸（ワールドの z）のまわりに回す ---
    L = 1.024; A_tail = float(os.environ.get("HH_RIG_AMP", 0.12)) * L     # 尾の先の片側の振れ（m）
    lam = float(os.environ.get("HH_RIG_WAVE", 0.9)) * L
    deps = bpy.context.evaluated_depsgraph_get()
    def pose(phase):
        bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="POSE")
        for pb in arm.pose.bones: pb.rotation_mode = "QUATERNION"; pb.rotation_quaternion = (1, 0, 0, 0)
        # 体軸に沿った横のずれ y(s) = A(s) sin(2π(s/λ − phase))、A(s) は頭 0.15、尾 1 の 2 次。各骨はそのずれの傾きの差だけ回す
        s = np.linspace(0, L, 400); A = A_tail * (0.15 + 0.85 * (s / L) ** 2); y = A * np.sin(2 * np.pi * (s / lam - phase))
        ang = np.arctan(np.gradient(y, s))
        prev_world = 0.0
        for nm in names:
            pb = arm.pose.bones[nm]; bone = pb.bone
            a_mid = float(np.interp((bone.head_local.x + bone.tail_local.x) / 2, s, ang))
            d = a_mid - prev_world; prev_world = a_mid
            axis_local = (bone.matrix_local.to_3x3().inverted() @ Vector((0, 0, 1))).normalized()
            pb.rotation_quaternion = Quaternion(axis_local, d)
        bpy.ops.object.mode_set(mode="OBJECT"); bpy.context.view_layer.update()
    def world_verts(ob):
        ev = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()); me = ev.to_mesh()
        V = np.array([ob.matrix_world @ v.co for v in me.vertices]); F = np.array([list(p.vertices) for p in me.polygons]); ev.to_mesh_clear(); return V, F
    skin = coll.objects.get("HH_Skin"); rigid = [coll.objects.get(n) for n in ("HH_Bone", "HH_Centrum", "HH_Arch", "HH_Cartilage", "HH_HeadCartilage", "HH_Gill", "HH_Jaw", "HH_Teeth") if coll.objects.get(n)]
    organs = [coll.objects.get(n) for n in ("HH_Liver", "HH_Gut", "HH_Spiral") if coll.objects.get(n)]
    DIAG = []; diag = {}
    rep = {"tail_amp_m": A_tail, "wave_m": lam, "bones": len(arm_data.bones), "poses": {}}; proj = {}
    def outside_flags(obs, SV, SF, step=7):
        # 膜（体とひれの膜が重なる）のいちばん近い面の外向きの側へ 0.5 mm より外か。重なりで曲げる前から外と出る点があるので、
        # 曲げる前の判定と比べて「新しく外へ出た点」を数える
        bvh = BVHTree.FromPolygons([tuple(map(float, v)) for v in SV], [tuple(map(int, f)) for f in SF])
        fl = []; xs = []; DIAG.clear()
        for ob in obs:
            V, _ = world_verts(ob)
            for p in V[::step]:
                hit = bvh.find_nearest(Vector(p))
                dd = (Vector(p) - hit[0]).dot(hit[1]) if hit[0] is not None else -1.0
                fl.append(dd); xs.append(p[0]); DIAG.append((ob.name, *[float(c) for c in p], *([float(c) for c in hit[0]] if hit[0] is not None else [0, 0, 0])))
        dd = np.array(fl); return dd > 0.0005, np.array(xs), dd
    SV0, SF0 = world_verts(skin)
    E0 = np.unique(np.sort(np.concatenate([SF0[:, [0, 1]], SF0[:, [1, 2]], SF0[:, [2, 0]]]), axis=1), axis=0)
    len0 = np.linalg.norm(SV0[E0[:, 0]] - SV0[E0[:, 1]], axis=1)
    # 骨と膜のずれ: 曲げる前に骨の各点にいちばん近い膜の点を決め、曲げたあと、その差（ベクトル）がどれだけ変わったかを測る
    from mathutils.kdtree import KDTree       # Blender の Python には scipy が無い
    _kd = KDTree(len(SV0))
    for _i, _p in enumerate(SV0): _kd.insert(_p, _i)
    _kd.balance()
    nearest = lambda P: np.array([_kd.find(p)[1] for p in P], int)
    RB0 = np.concatenate([world_verts(o)[0][::5] for o in rigid]); RO0 = np.concatenate([world_verts(o)[0][::5] for o in organs]) if organs else np.zeros((0, 3))
    nnb = nearest(RB0); nno = nearest(RO0) if len(RO0) else np.zeros(0, int)
    off_b0 = RB0 - SV0[nnb]; off_o0 = RO0 - SV0[nno] if len(RO0) else np.zeros((0, 3))
    if os.environ.get("HH_RIG_DEBUG") == "1":
        objs = [skin] + rigid; R0 = {o.name: world_verts(o)[0] for o in objs}
        pose(0.0); dbg = {}
        for o in objs:
            V1 = world_verts(o)[0]; V0 = R0[o.name]; m = V0[:, 0] < 0.118
            if m.sum() < 4: continue
            # 頭の部分（x < 118 mm）が 1 つの剛体の動きか: 頭の骨の行列で戻した残り
            hb = arm.pose.bones["head"]; Mh = np.array(arm.matrix_world @ hb.matrix @ hb.bone.matrix_local.inverted())
            P = np.c_[V0[m], np.ones(m.sum())] @ Mh.T; res = np.linalg.norm(P[:, :3] - V1[m], axis=1) * 1000
            dbg[o.name] = dict(n=int(m.sum()), resid_mm_max=round(float(res.max()), 3), x_at_max=round(float(V0[m][np.argmax(res), 0] * 1000), 1))
        print("DEBUG", dbg); json.dump(dbg, open(os.path.join(_work, "b1_rig_debug.json"), "w"), indent=1); raise SystemExit(0)
    # 追跡式: 曲げる前にいちばん近い膜の面を点ごとに覚え、曲げたあとも同じ面（同じ頂点）の平面までの符号つき距離を測る。
    #  いちばん近い面を毎回探し直すと、薄い膜（ひれ、口のふち）の裏の面に移って符号だけ反転し、動いていない点まで「外」と出た
    bvh0 = BVHTree.FromPolygons([tuple(map(float, v)) for v in SV0], [tuple(map(int, f)) for f in SF0])
    def track_faces(P):
        return np.array([bvh0.find_nearest(Vector(p))[2] for p in P], int)
    def plane_dist(P, SVx, fi):
        a, b_, c_ = SVx[SF0[fi, 0]], SVx[SF0[fi, 1]], SVx[SF0[fi, 2]]
        n = np.cross(b_ - a, c_ - a); n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        return np.einsum('ij,ij->i', P - (a + b_ + c_) / 3, n)
    RBt0 = np.concatenate([world_verts(o)[0][::3] for o in rigid]); OBt = np.concatenate([[o.name] * len(world_verts(o)[0][::3]) for o in rigid])
    ROt0 = np.concatenate([world_verts(o)[0][::3] for o in organs]) if organs else np.zeros((0, 3))
    fb_t = track_faces(RBt0); fo_t = track_faces(ROt0) if len(ROt0) else np.zeros(0, int)
    db_t0 = plane_dist(RBt0, SV0, fb_t); do_t0 = plane_dist(ROt0, SV0, fo_t) if len(ROt0) else np.zeros(0)
    for ph in ("rest", 0.0, 0.25, 0.5, 0.75):
        if ph == "rest":
            bpy.context.view_layer.objects.active = arm; bpy.ops.object.mode_set(mode="POSE")
            for pb in arm.pose.bones: pb.rotation_quaternion = (1, 0, 0, 0)
            bpy.ops.object.mode_set(mode="OBJECT"); bpy.context.view_layer.update()
        else: pose(ph)
        SV, SF = world_verts(skin)
        L1 = np.linalg.norm(SV[E0[:, 0]] - SV[E0[:, 1]], axis=1); st = L1 / np.maximum(len0, 1e-6)
        RB = np.concatenate([world_verts(o)[0][::5] for o in rigid]); dvb = np.linalg.norm((RB - SV[nnb]) - off_b0, axis=1) * 1000
        RO = np.concatenate([world_verts(o)[0][::5] for o in organs]) if organs else np.zeros((0, 3)); dvo = np.linalg.norm((RO - SV[nno]) - off_o0, axis=1) * 1000 if len(RO) else np.zeros(1)
        RBt = np.concatenate([world_verts(o)[0][::3] for o in rigid]); db_t = plane_dist(RBt, SV, fb_t)
        ROt = np.concatenate([world_verts(o)[0][::3] for o in organs]) if organs else np.zeros((0, 3)); do_t = plane_dist(ROt, SV, fo_t) if len(ROt) else np.zeros(0)
        esc = (db_t0 <= 0) & (db_t > 0.0005); esco = (do_t0 <= 0) & (do_t > 0.0005); gain = (db_t - db_t0) * 1000
        track = dict(tracked_sampled=[int(len(db_t)), int(len(do_t))], tracked_bone_escaped=int(esc.sum()), tracked_organ_escaped=int(esco.sum()),
                     tracked_bone_escaped_by_ob={k: int(v) for k, v in zip(*np.unique(OBt[esc], return_counts=True))},
                     tracked_bone_escaped_x_mm=[round(float(x * 1000)) for x in np.percentile(RBt0[esc, 0], [0, 50, 100])] if esc.any() else [],
                     tracked_bone_escaped_mm_max=round(float(db_t[esc].max() * 1000), 2) if esc.any() else 0,
                     tracked_bone_toward_skin_mm_max=round(float(gain.max()), 2), tracked_bone_toward_skin_x_mm=round(float(RBt0[np.argmax(gain), 0] * 1000)),
                     tracked_organ_toward_skin_mm_max=round(float(((do_t - do_t0) * 1000).max()), 2) if len(do_t) else 0)
        drift = dict(**track, bone_vs_skin_shift_mm_max=round(float(dvb.max()), 2), bone_vs_skin_shift_mm_p999=round(float(np.percentile(dvb, 99.9)), 2),
                     bone_shift_over_1mm=int((dvb > 1).sum()), bone_shift_x_mm_where_max=round(float(RB0[np.argmax(dvb), 0] * 1000)),
                     organ_vs_skin_shift_mm_max=round(float(dvo.max()), 2), organ_shift_over_1mm=int((dvo > 1).sum()), sampled_bone=int(len(dvb)))
        fb, xb, db = outside_flags(rigid, SV, SF); DB = list(DIAG); fo, xo, do = outside_flags(organs, SV, SF) if organs else (np.zeros(0, bool), np.zeros(0), np.zeros(0))
        if ph == "rest": rest_b, rest_o, rest_db = fb, fo, db
        nb_new0 = fb & ~rest_b
        diag[str(ph)] = [dict(ob=DB[i][0], p_mm=[round(c * 1000, 1) for c in DB[i][1:4]], hit_mm=[round(c * 1000, 1) for c in DB[i][4:7]], d_mm=round(float(db[i] * 1000), 2), rest_mm=round(float(rest_db[i] * 1000), 2))
                         for i in np.nonzero(nb_new0 & (db > 0.001))[0]]
        nb_new = fb & ~rest_b; no_new = fo & ~rest_o
        big = np.nonzero(st > 1.4)[0]; ex = (SV0[E0[big, 0], 0] * 1000) if len(big) else np.zeros(0)
        rep["poses"][str(ph)] = dict(**drift, bone_newly_outside=int(nb_new.sum()), bone_newly_outside_x_mm=[round(float(x * 1000)) for x in np.percentile(xb[nb_new], [0, 50, 100])] if nb_new.any() else [],
                                     bone_newly_outside_mm_max=round(float(db[nb_new].max() * 1000), 2) if nb_new.any() else 0, bone_newly_outside_rest_mm=round(float(rest_db[nb_new].max() * 1000), 2) if nb_new.any() else 0,
                                     bone_outside_more_than_1mm=int(((db > 0.001) & (rest_db <= 0.001)).sum()), organ_newly_outside=int(no_new.sum()), sampled=[int(len(fb)), int(len(fo))], rest_outside=[int(rest_b.sum()), int(rest_o.sum())],
                                     stretched_edges_x_mm=[round(float(x)) for x in np.percentile(ex, [0, 50, 100])] if len(ex) else [],
                                     skin_edge_stretch_max=round(float(st.max()), 3), skin_edge_stretch_p999=round(float(np.percentile(st, 99.9)), 3),
                                     skin_edges_over_1_5=int((st > 1.5).sum()), skin_edge_shrink_min=round(float(st.min()), 3))
        bV, _ = world_verts(coll.objects.get("HH_Bone")); proj[f"skin_{ph}"] = SV[::3, :2].astype(np.float32); proj[f"bone_{ph}"] = bV[::3, :2].astype(np.float32)
        print("pose", ph, rep["poses"][str(ph)])
    json.dump(rep, open(os.path.join(_work, "b1_rig_test.json"), "w"), ensure_ascii=False, indent=1)
    json.dump(diag, open(os.path.join(_work, "b1_rig_diag.json"), "w"), ensure_ascii=False, indent=0)
    np.savez_compressed(os.path.join(_work, "b1_rig_proj.npz"), **proj)
    raise SystemExit(0)

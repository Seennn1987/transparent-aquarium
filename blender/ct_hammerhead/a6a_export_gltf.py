"""シロシュモクザメ A6: 骨・軟骨・膜の PLY を組織ごとに 1 つにまとめ、減らして、標本ページ用の glb に書き出す。

開いている .blend を壊さないよう、別のシーン HH_EXPORT で行う（ファイルは保存しない）。
組織は custom property `hh_part` で渡す（hammerhead-material.js が読む）:
  Bone      椎骨の列（HH_bone。Eames et al. 2007 の胚では椎骨が強く石灰化してアリザリンで赤い）
  Cartilage ひれの骨・肩帯・腰帯・尾の骨など（アルシアンで青い。参考の胚では放射軟骨は明るい水色）
  HeadCartilage 頭骨（a6b_split_head.py で分けた。参考の胚では濃い青緑）
  Jaw       上あご・下あご（a7b・a7c で細かい格子から分け、下あごは口を開いた向き）。ひれの軟骨と同じ明るい青
  Teeth     歯（800 HU を超える石灰化した所）。椎骨と同じ赤
  Gill      舌の弓とエラの骨（a7 で作る）。ひれの軟骨と同じ明るい青
  Skin      体と、ひれの膜（透明になった組織）
  Viscera   内臓（a8a_viscera.py、CT の体腔から取り出した。2026-10-15）
CT（Kamminga et al. 2017、figshare、CC0）から作ったので、glb はリポジトリに入れてよい。
"""
import bpy, bmesh, os, math
import sys as _sys, os as _os
_sys.path.insert(0, _os.environ.get("HH_SCRIPTS", "/Users/shoui/transparent-aquarium/transparent-aquarium/blender/ct_hammerhead"))
import hh_paths
ROOT = hh_paths.ROOT
MESH = hh_paths.MESH
OUT = hh_paths.GLB
PARTS = {
    "Bone": (["HH_bone"], 60000),
    "Cartilage": (["HH_skel_rest", "HH_girdle", "HH_pect_L", "HH_pect_R", "HH_dfin1", "HH_dfin2", "HH_anal"], 103200),   # 減らす割合は分ける前（110000 / 250025）と同じ
    # 2026-10-15 腹びれの軟骨と膜は別の部品（プロデューサー「パーツ種別ごとに色や濃さを調整できるようにしたい」「腹鰭がかなり透明」）
    "PelvicCartilage": (["HH_pelv_L", "HH_pelv_R"], 6800),
    "HeadCartilage": (["HH_skel_head"], 150000),
    "Jaw": (["HH_jaw_upper", "HH_jaw_lower"], 90000),
    "Teeth": (["HH_teeth_upper", "HH_teeth_lower"], 40000),
    "Gill": (["HH_hyoid", "HH_gill"], 60000),
    "Skin": (["HH_body", "HH_pectmem_L", "HH_pectmem_R"], 152300),   # 同（160000 / 1540502）
    "PelvicSkin": (["HH_pelvmem_L", "HH_pelvmem_R"], 7700),
}
# A8 内臓（a8a_viscera.py）。面があるときだけ書き出す（2026-10-15）
if os.path.exists(f"{MESH}/HH_viscera.ply"):
    PARTS["Viscera"] = (["HH_viscera"], 120000)
# A8 背骨を部品から作った場合（a8c_vertebrae.py）: 椎体は CT の殻（HH_bone）の代わり、弓は軟骨に足す（2026-10-15）
if os.path.exists(f"{MESH}/HH_vert_centra.ply"):
    if os.environ.get("HH_VERT_CENTRA_PART") == "Centrum":   # 案 E: CT の殻（砂時計形）は骨のまま、詰めた椎体は別の部品（ページで淡い青に）
        PARTS["Centrum"] = (["HH_vert_centra"], 60000)
    elif os.environ.get("HH_VERT_CENTRA_PART") == "Cartilage":   # 案 D: CT の殻（砂時計形）は骨のまま、詰めた椎体は軟骨として重ねる
        PARTS["Cartilage"] = (PARTS["Cartilage"][0] + ["HH_vert_centra"], 130000)
    else:
        PARTS["Bone"] = (["HH_vert_centra"], 60000)
if os.path.exists(f"{MESH}/HH_vert_arches.ply"):
    if os.environ.get("HH_VERT_ARCH_PART") == "Arch":   # 案 G: 弓を別の部品に（ページで強さを変える）
        PARTS["Arch"] = (["HH_vert_arches"], 20000)
    else:
        PARTS["Cartilage"] = (PARTS["Cartilage"][0] + ["HH_vert_arches"], 130000)
# 2026-10-16 案: 肋骨と尾びれの鰭条（a8c_vertebrae.py の HH_VERT_RIBS・HH_VERT_RADIALS。CT に無く、文献と骨格標本の写真から作る）
for _p, _f, _n in (("Rib", "HH_vert_ribs", 8000), ("CaudalRay", "HH_vert_radials", 12000)):
    if os.path.exists(f"{MESH}/{_f}.ply"): PARTS[_p] = ([_f], _n)
for _p, _f, _n in (("Liver", "HH_liver", 60000), ("Gut", "HH_gut", 60000), ("Spiral", "HH_spiral", 30000),   # 案 2（a8b_viscera_organs.py）
                   # B5 心臓（b5b_heart.py）。HeartLarge・HeartSmall は見比べの案（試しの glb だけ）
                   ("Heart", "HH_heart", 20000), ("HeartLarge", "HH_heart_large", 20000), ("HeartSmall", "HH_heart_small", 20000)):
    if os.path.exists(f"{MESH}/{_f}.ply"): PARTS[_p] = ([_f], _n)
sc = hh_paths.blender_scene("HH_EXPORT")
coll = bpy.data.collections.get("HH_EXPORT")
if coll is None:
    coll = bpy.data.collections.new("HH_EXPORT"); sc.collection.children.link(coll)
for ob in list(coll.objects):
    me = ob.data; bpy.data.objects.remove(ob, do_unlink=True)
    if me and me.users == 0: bpy.data.meshes.remove(me)
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]
report = {}
# 2026-10-16 案（胴の長さと幅）: 胴を縮める（hh_warp.py、HH_BODY_SHRINK）。胸びれ・腹びれ（軟骨と膜）は形を変えず、付け根の位置だけ動かし、
#  胴の幅の案（a5a_shell.py の a5_trunk_width.json）があれば、胴の幅の増えた分（片側）だけ外へずらす。ほかの面は頂点ごとに縮める
import numpy as _np, json as _json, hh_warp
_RIGID = {"HH_pect_L", "HH_pect_R", "HH_pectmem_L", "HH_pectmem_R", "HH_pelv_L", "HH_pelv_R", "HH_pelvmem_L", "HH_pelvmem_R"}
_twp = os.path.join(hh_paths.WORK, "a5_trunk_width.json"); _TW = _json.load(open(_twp)) if os.path.exists(_twp) else None
def _body_warp(o, n):
    if n in ("HH_dfin1", "HH_dfin2", "HH_anal"):   # 背と腹を足した案（a5a_shell.py の HH_TRUNK_PROFILE=ref）: 背びれ・臀びれの軟骨を膜と同じだけ動かす
        if (_TW is None or "dtop_mm" not in _TW) and hh_warp.SHRINK == 1.0: return
        me = o.data; co = _np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        bx = co[:, 0] * 1000   # 膜（a5a_shell.py の段 4）と同じく、体軸の位置ごとに動かす
        if _TW is not None and "dtop_mm" in _TW:
            co[:, 2] += (_np.interp(bx, _TW["z_mm"], _TW["dtop_mm"]) if n != "HH_anal" else -_np.interp(bx, _TW["z_mm"], _TW["dbot_mm"])) / 1000
        # 2026-10-17 直し（プロデューサー「全てのヒレの色のつき方が変です。サイズを調整した時に色付けする箇所の修正を忘れたのではないでしょうか？」→ 図で示した直しの範囲に「進めて」）:
        #  HH_FIN_CART_REACH（例 0.53）で、第 2 背びれ・臀びれの軟骨を、参考の外形の膜（hh_fins.py）の付け根の線に合わせて背腹へ動かす。
        #  軟骨の先（体から最も離れた所）が、膜の高さ H のその割合に来るようにする。0.53 は第 1 背びれの CT: 軟骨の先が背の線から 63 mm、膜の高さ 119 mm。
        #  前は CT の体の線からの位置のままで、参考の膜の付け根の線（a5_side_fit.json）とずれ、臀びれの軟骨は膜の 2 割までしか届かず体の中に入っていた
        _reach = os.environ.get("HH_FIN_CART_REACH")
        if _reach and n in ("HH_dfin2", "HH_anal") and os.environ.get("HH_FIN_REF") == "1":
            import hh_fins
            fd = hh_fins.FINS["dfin2" if n == "HH_dfin2" else "anal"]; TLm = hh_fins.TL_MM
            _sf = _json.load(open(os.path.join(hh_paths.WORK, "a5_side_fit.json")))
            xm = (fd["o"] + fd["i"]) / 2 * TLm
            line_z = -_np.interp(xm, _sf["z_mm"], _sf["top_target_mm"] if fd["side"] < 0 else _sf["bot_target_mm"]) / 1000   # Blender の z = −v
            tip = co[:, 2].max() if fd["side"] < 0 else co[:, 2].min()
            want = line_z - fd["side"] * float(_reach) * fd["H"] * TLm / 1000
            co[:, 2] += want - tip
            report[f"fin_cart_shift_{n}_mm"] = round(float(want - tip) * 1000, 1)
        co[:, 0] = hh_warp.warp_mm(co[:, 0] * 1000) / 1000
        me.vertices.foreach_set("co", co.ravel()); me.update(); return
    # 同じ直し: HH_LOBE_CART=1 で、尾びれの下の葉の軟骨（HH_skel_rest の、背骨の中心より腹側で 690〜860 mm）を、
    #  膜（a5a_shell.py の HH_TRUNK_LOBE。腹の側を中心から伸ばす）と同じ割合で腹側へ伸ばす。割合 = いまの腹の線までの距離 ÷（それ − 腹の伸び dbot）。
    #  背骨の中心は椎体の面（HH_vert_centra）の 5 mm ごとの平均
    if n == "HH_skel_rest" and os.environ.get("HH_LOBE_CART") == "1" and _TW is not None and "dbot_mm" in _TW:
        me = o.data; co = _np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
        bpy.ops.wm.ply_import(filepath=f"{MESH}/HH_vert_centra.ply"); _c = bpy.context.selected_objects[0]
        cc = _np.array([v.co[:] for v in _c.data.vertices]) * 1000; _cm = _c.data; bpy.data.objects.remove(_c, do_unlink=True); bpy.data.meshes.remove(_cm)
        bins = _np.arange(680, 875, 5.0); vcz = _np.array([cc[_np.abs(cc[:, 0] - b) < 4, 2].mean() for b in bins])
        _sf = _json.load(open(os.path.join(hh_paths.WORK, "a5_side_fit.json")))
        x = co[:, 0] * 1000; z = co[:, 2] * 1000; sel = (x > 690) & (x < 860)
        vc = _np.interp(x, bins, vcz); belly = -_np.interp(x, _sf["z_mm"], _sf["bot_target_mm"]); B1 = vc - belly
        dbot = _np.interp(x, _TW["z_mm"], _TW["dbot_mm"]); k = B1 / _np.maximum(B1 - dbot, 1.0)
        m = sel & (z < vc); z[m] = vc[m] - (vc[m] - z[m]) * k[m]
        report["lobe_cart_k_max"] = round(float(k[sel].max()), 3)
        co[:, 2] = z / 1000; me.vertices.foreach_set("co", co.ravel()); me.update()
    if hh_warp.SHRINK == 1.0 and (_TW is None or n not in _RIGID) and not (n in _RIGID and (os.environ.get("HH_PECT_DOWN") or os.environ.get("HH_PELV_DOWN"))): return
    me = o.data; co = _np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    x = co[:, 0] * 1000
    if n in _RIGID:
        ay = _np.abs(co[:, 1]); bx = float(x[ay < ay.min() + 0.010].mean())   # 付け根（体の中心にいちばん近い所）
        co[:, 0] += (float(hh_warp.warp_mm(bx)) - bx) / 1000
        if _TW is not None:
            dy = (_np.interp(bx, _TW["z_mm"], _TW["width_new_mm"]) - _np.interp(bx, _TW["z_mm"], _TW["width_old_mm"])) / 2 / 1000
            co[:, 1] += _np.sign(co[:, 1].mean()) * dy
        # 2026-10-17 案: 胸びれ・腹びれを付け根のまわりに下へ回す（HH_PECT_DOWN・HH_PELV_DOWN、度。2026-10-14 に決めた姿勢に足す角）。
        #  体軸（Blender x）のまわりに、付け根（体の中心にいちばん近い頂点のまとまり）を中心に回す。右（+y）のひれは −、左は + の向き（先が下へ）
        _deg = float(os.environ.get("HH_PECT_DOWN" if "pect" in n else "HH_PELV_DOWN", 0) or 0)
        if _deg:
            _near = ay < ay.min() + 0.010; c0 = co[_near].mean(0); th = math.radians(_deg) * (-1 if co[:, 1].mean() > 0 else 1)
            yy, zz = co[:, 1] - c0[1], co[:, 2] - c0[2]
            co[:, 1] = c0[1] + yy * math.cos(th) - zz * math.sin(th); co[:, 2] = c0[2] + yy * math.sin(th) + zz * math.cos(th)
    else:
        co[:, 0] = hh_warp.warp_mm(x) / 1000
    me.vertices.foreach_set("co", co.ravel()); me.update()
for part, (names, target) in PARTS.items():
    objs = []
    for n in names:
        bpy.ops.wm.ply_import(filepath=f"{MESH}/{n}.ply")
        o = bpy.context.selected_objects[0]; o.name = f"tmp_{n}"; objs.append(o)
        _body_warp(o, n)
        # B1 骨組み（2026-10-15）: ひれの膜とひれの軟骨は、まとめる前に出どころの頂点グループを付ける（b1_rig.py が、体の膜ではなくひれだけをひれの骨に付けるため）
        if os.environ.get("HH_RIG") == "1" and n in ("HH_pectmem_L", "HH_pectmem_R", "HH_pelvmem_L", "HH_pelvmem_R", "HH_pect_L", "HH_pect_R", "HH_pelv_L", "HH_pelv_R", "HH_jaw_lower", "HH_teeth_lower"):   # B5: 下あご・下の歯は口の骨へ
            o.vertex_groups.new(name=f"src_{n}").add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
    # 2026-10-17 案: HH_FIN_PLATE=1 で、第 1 背びれの膜を参考の外形（hh_fins.py）の板の面にして体の膜に足す。
    #  背の線（a5_side_fit.json、背骨の中心より上の断面の端）から 4 mm 体の中から立て、厚さ 3.2 mm（ひれの先の膜の厚さとして、体積で作るときの最小と同じ）
    if part == "Skin" and os.environ.get("HH_FIN_PLATE") == "1":
        import hh_fins
        _sf = _json.load(open(os.path.join(hh_paths.WORK, "a5_side_fit.json"))); fd = hh_fins.FINS["dfin1"]; TLm = hh_fins.TL_MM
        Lb = (fd["i"] - fd["o"]) * TLm; Hm = fd["H"] * TLm
        bm = bmesh.new(); vs = []
        for s_, h_ in fd["poly"]:
            xm = fd["o"] * TLm + s_ * Lb; vtop = _np.interp(xm, _sf["z_mm"], _sf["top_target_mm"])
            hh = h_ * Hm if h_ > 0 else -4.0
            vs.append(bm.verts.new((xm / 1000, 0.0, -(vtop - hh) / 1000)))
        f = bm.faces.new(vs); bmesh.ops.triangulate(bm, faces=[f], quad_method="BEAUTY", ngon_method="BEAUTY")
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
        bmesh.ops.solidify(bm, geom=bm.faces[:], thickness=0.0032)
        bmesh.ops.translate(bm, verts=bm.verts[:], vec=(0, -0.0016, 0))
        me = bpy.data.meshes.new("tmp_finplate"); bm.to_mesh(me); bm.free()
        ob_ = bpy.data.objects.new("tmp_finplate", me); coll.objects.link(ob_); objs.append(ob_)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = f"HH_{part}"; ob.data.name = f"HH_{part}"
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6); bm.to_mesh(ob.data); bm.free()
    n0 = len(ob.data.polygons)
    if n0 > target:
        m = ob.modifiers.new("dec", "DECIMATE"); m.ratio = target / n0
        bpy.ops.object.modifier_apply(modifier=m.name)
    for p in ob.data.polygons: p.use_smooth = True
    ob["hh_part"] = part
    bm = bmesh.new(); bm.from_mesh(ob.data)
    report[part] = (n0, len(ob.data.polygons), sum(1 for e in bm.edges if e.is_boundary)); bm.free()
# B1 骨組み（2026-10-15）: HH_RIG=1 で骨組みと重みを付けて書き出す（b1_rig.py）
RIG = os.environ.get("HH_RIG") == "1"
if RIG:
    exec(compile(open(hh_paths.script("b1_rig.py"), encoding="utf-8").read(), hh_paths.script("b1_rig.py"), "exec"))
bpy.ops.object.select_all(action="DESELECT")
for ob in coll.objects: ob.select_set(True)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
# 選択は他のシーン（開いているカメレオン）のものまで拾うので、このシーンのこのコレクションだけを書き出す
bpy.context.view_layer.active_layer_collection = bpy.context.view_layer.layer_collection.children[coll.name]
bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", use_active_scene=True, use_active_collection=True, export_extras=True,
                          export_apply=not RIG, export_normals=True, export_texcoords=False, export_materials="NONE")
print("parts (faces before, after, open edges):", report, "->", OUT, os.path.getsize(OUT))

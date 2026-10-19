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
# 2026-10-17 プロデューサー「今、ヒレごとの色の濃さを調整できません。特に背鰭がずっと透明です。」: HH_FIN_PARTS=1 で、ひれごとに軟骨と膜を別の部品にする
#  （ページの調整の欄で、ひれごとに濃さとにごり度を変えるため）。軟骨: 胸びれ・第 1 背びれ・第 2 背びれ・臀びれ（残りの肩帯・腰帯・尾は Cartilage のまま）。
#  膜: 胸びれ（PectSkin）と、参考の外形の板（HH_FIN_PLATE=all で背びれ 2 つと臀びれを板にする）。減らす割合は分ける前と同じ（軟骨 0.44、膜 0.099）
FIN_PARTS = os.environ.get("HH_FIN_PARTS") == "1"
PLATE_FINS = {"dfin1": "Dorsal1Skin", "dfin2": "Dorsal2Skin", "anal": "AnalSkin"} if os.environ.get("HH_FIN_PLATE") == "all" else ({"dfin1": "Skin"} if os.environ.get("HH_FIN_PLATE") == "1" else {})
if FIN_PARTS:
    PARTS["Cartilage"] = (["HH_skel_rest", "HH_girdle"], 0.44)
    PARTS["PectCartilage"] = (["HH_pect_L", "HH_pect_R"], 0.44)
    PARTS["Dorsal1Cartilage"] = (["HH_dfin1"], 0.44); PARTS["Dorsal2Cartilage"] = (["HH_dfin2"], 1.0); PARTS["AnalCartilage"] = (["HH_anal"], 1.0)
    PARTS["Skin"] = (["HH_body"], 0.099)
    PARTS["PectSkin"] = (["HH_pectmem_L", "HH_pectmem_R"], 0.099)
for _fin, _part in PLATE_FINS.items():
    if _part not in PARTS: PARTS[_part] = ([], 1.0)
# 2026-10-18: CT の細かさで作った腹びれの軟骨（HH_PELV_CT175）は、膜を 6.5%（7700 面）まで減らすと薄い所で覆いが欠け、軟骨が膜の外に出た。膜は 30% まで
if os.environ.get("HH_PELV_CT175") == "1": PARTS["PelvicSkin"] = (PARTS["PelvicSkin"][0], 0.30)
# 2026-10-19 案: 写真の形から作った腹びれ（a5f_pelv_photo.py、HH_PELV_PHOTO）は、0.25 mm の格子の面なので面が多い。軟骨は 6800 面では細い放射軟骨がつぶれるので 60000 面、膜は 40000 面まで
if os.environ.get("HH_PELV_PHOTO") == "1": PARTS["PelvicCartilage"] = (PARTS["PelvicCartilage"][0], 60000); PARTS["PelvicSkin"] = (PARTS["PelvicSkin"][0], int(os.environ.get("HH_PELV_PHOTO_SKINF", 40000)))
FIT_FD = {}   # 2026-10-18: 軟骨に合わせて大きくした膜の外形（HH_FINCT_FIT=membrane の臀びれ）。軟骨の部品の後に、膜の板がこれを使う
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
        _membfit = ((n == "HH_anal" and os.environ.get("HH_FINCT_ANAL") == "1") or (n == "HH_dfin2" and os.environ.get("HH_FINCT_DFIN2") == "1")) and os.environ.get("HH_FINCT_FIT") == "membrane"
        if _reach and n in ("HH_dfin2", "HH_anal") and os.environ.get("HH_FIN_REF") == "1" and not _membfit:   # 膜を軟骨に合わせるときは、軟骨は CT の位置のまま
            import hh_fins
            fd = hh_fins.FINS["dfin2" if n == "HH_dfin2" else "anal"]; TLm = hh_fins.TL_MM
            _sf = _json.load(open(os.path.join(hh_paths.WORK, "a5_side_fit.json")))
            xm = (fd["o"] + fd["i"]) / 2 * TLm
            line_z = -_np.interp(xm, _sf["z_mm"], _sf["top_target_mm"] if fd["side"] < 0 else _sf["bot_target_mm"]) / 1000   # Blender の z = −v
            tip = co[:, 2].max() if fd["side"] < 0 else co[:, 2].min()
            want = line_z - fd["side"] * float(_reach) * fd["H"] * TLm / 1000
            co[:, 2] += want - tip
            report[f"fin_cart_shift_{n}_mm"] = round(float(want - tip) * 1000, 1)
        # 2026-10-18 直し（プロデューサー「ヒレの色の染まり方が変です。特に背鰭に色をつけると、皮膚からはみ出ています。」→ 直し B・C）。
        #  膜は参考の外形の板（正中 ±1.6 mm、hh_fins.py）なので、軟骨をその中に収める。体の線より外（ひれの側）の頂点だけを動かし、体の線から 1.5 mm で効き目を 1 にする
        if os.environ.get("HH_FIN_PLATE") == "all" and (os.environ.get("HH_FIN_CART_FLAT") == "1" or os.environ.get("HH_FIN_CART_FIT") == "1"):
            import hh_fins
            def _inside(poly, xx, zz):   # 多角形の中か（偶奇の規則。Blender の Python には matplotlib が無い）
                P_ = _np.array(poly); x1, z1 = P_[:, 0], P_[:, 1]; x2, z2 = _np.roll(x1, -1), _np.roll(z1, -1); r = _np.zeros(len(xx), bool)
                for a_, b_, c_, d_ in zip(x1, z1, x2, z2):
                    cr = ((b_ > zz) != (d_ > zz)) & (xx < (c_ - a_) * (zz - b_) / ((d_ - b_) if d_ != b_ else 1e-12) + a_); r ^= cr
                return r
            fin = {"HH_dfin1": "dfin1", "HH_dfin2": "dfin2", "HH_anal": "anal"}[n]; fd = hh_fins.FINS[fin]; TLm = hh_fins.TL_MM
            _sf = _json.load(open(os.path.join(hh_paths.WORK, "a5_side_fit.json"))); key = "top_target_mm" if fd["side"] < 0 else "bot_target_mm"
            X = co[:, 0] * 1000; Y = co[:, 1] * 1000; Z = co[:, 2] * 1000
            out = lambda: -fd["side"] * (Z + _np.interp(X, _sf["z_mm"], _sf[key]))   # 体の線からひれの側へ（mm）。Blender の z = −v
            w = _np.clip(out() / 1.5, 0, 1)   # 5 mm では、体の線から 1〜6 mm の所が外形と板の外に残った（臀びれ 107 点・132 点）
            # B: ひねりを取る。体軸 3 mm × 高さ 3 mm の区画ごとに、左右の中央を正中へ。それでも ±1.4 mm を超える区画は、その区画の左右を縮める
            WHOLE = (n == "HH_anal" and os.environ.get("HH_FINCT_ANAL") == "1") or (n == "HH_dfin2" and os.environ.get("HH_FINCT_DFIN2") == "1")   # 2026-10-18: CT の細かさで作った臀びれ（a4d3_fin_ct_mesh.py）は、ひれ全体を 1 枚として動かす（棒の並びを崩さない）
            if os.environ.get("HH_FIN_CART_FLAT") == "1" and WHOLE and _membfit:
                # 2026-10-18 直し（プロデューサー「なんでそんなにまだらなんですか？これじゃ組織が欠損していますよね？」）: 頂点ごとに左右を ±1.5 mm に切り詰めると、
                #  正中から横にずれた棒は表と裏の面が同じ 1.5 mm に寄って厚さ 0 になり、ページでは消えていた（CT の軟骨は欠けていない）。
                #  ひれ全体（体の中の部分も）の左右の中心を、体軸と高さの 2 次の面で正中へそろえ、それでも板より厚ければ全体を同じ割合で薄くする（どこも厚さ 0 にしない）
                A_ = _np.c_[_np.ones(len(X)), X, out(), X * X, X * out(), out() ** 2]; cf = _np.linalg.lstsq(A_, Y, rcond=None)[0]
                Y = Y - A_ @ cf
                p99 = float(_np.percentile(_np.abs(Y), 99.5)); sc_ = min(1.0, 1.5 / p99); Y = Y * sc_
                report[f"fin_cart_flat_{n}"] = {"surface": [round(float(v_), 5) for v_ in cf], "p99_5_mm": round(p99, 2), "scale": round(sc_, 3)}
            elif os.environ.get("HH_FIN_CART_FLAT") == "1" and WHOLE:
                mm_ = w > 0.99; A_ = _np.c_[_np.ones(mm_.sum()), X[mm_], out()[mm_]]; cf = _np.linalg.lstsq(A_, Y[mm_], rcond=None)[0]
                Y0 = Y.copy(); Y = Y - w * (cf[0] + cf[1] * X + cf[2] * out())            # ひれの面（左右 = a + b × 体軸 + c × 高さ）を正中の面へ
                p99 = float(_np.percentile(_np.abs(Y[mm_]), 99))
                if p99 > 1.4: Y = Y * (1 - w + w * 1.4 / p99)                            # まだ板より厚ければ、ひれ全体を同じ割合で薄く
                report[f"fin_cart_flat_{n}"] = {"plane": [round(float(v_), 4) for v_ in cf], "p99_mm": round(p99, 2), "after": [round(float(Y[mm_].min()), 1), round(float(Y[mm_].max()), 1)]}
            elif os.environ.get("HH_FIN_CART_FLAT") == "1":
                cell = _np.floor(X / 3).astype(int) * 100000 + _np.floor(out() / 3).astype(int); Y0 = Y.copy()
                for c_ in _np.unique(cell[w > 0]):
                    m_ = cell == c_; Yc = Y0[m_] - _np.median(Y0[m_]); top = _np.abs(Yc).max()
                    if top > 1.4: Yc = Yc * 1.4 / top
                    Y[m_] = (1 - w[m_]) * Y0[m_] + w[m_] * Yc
                report[f"fin_cart_flat_{n}_mm"] = [round(float(Y0[w > 0.99].min()), 1), round(float(Y0[w > 0.99].max()), 1), round(float(Y[w > 0.99].min()), 1), round(float(Y[w > 0.99].max()), 1)]
            # C: 膜の外形（横から）の内側へ。臀びれは前の端がひれの付け根の前の端 + 2 mm に来るよう後ろへずらす。残って外形から出る頂点は、同じ高さで外形の内側 1 mm の所へ前後に寄せる
            if os.environ.get("HH_FIN_CART_FIT") == "1":
                Lb = (fd["i"] - fd["o"]) * TLm; Hm = fd["H"] * TLm; poly = []
                for s_, h_ in fd["poly"]:
                    xm = fd["o"] * TLm + s_ * Lb; hh = h_ * Hm if h_ > 0 else -4.0
                    poly.append((xm, -(_np.interp(xm, _sf["z_mm"], _sf[key]) + fd["side"] * hh)))
                if _membfit:
                    # 2026-10-18（プロデューサー「軟骨って実際にそんなに短いのヒレ全体の３０％程度しかないのでしょうか？」→ 膜を軟骨に合わせる案に「皮膚から飛び出さないようにしてね。修正を承認します」）:
                    #  軟骨は CT の大きさ・位置のまま。参考の外形（hh_fins.py の臀びれ）を同じ形のまま k 倍し、前後にずらして、体の線から 1.5 mm より外の軟骨の頂点が
                    #  すべて外形の内側 1 mm に入る、いちばん小さい k を探す。膜の板（AnalSkin）はこの外形で作る（FIT_FD）
                    # 背腹: CT の位置のままでは軟骨の大半が体の中に入り、膜が大きくならなかった（k 1.0）。付け根（体の線から測った深さの 10% の点）を体の線の 3 mm 内へ
                    sh_ = (-3.0 - float(_np.percentile(out(), 10))); Z = Z - fd["side"] * sh_; co[:, 2] = Z / 1000
                    w = _np.clip(out() / 1.5, 0, 1); report[f"fin_cart_base_shift_{n}_mm"] = round(sh_, 1)
                    # 左右は上の 2 次の面で正中へそろえ、全体を同じ割合で ±1.5 mm に収めてある（頂点ごとに切り詰めると棒が消えた）
                    sel_ = _np.nonzero(w > 0.99)[0][::3]; xs_, zs_ = X[sel_], Z[sel_]
                    # 高さ: 軟骨の先がひれの深さの 0.55 になる高さ（ピサの骨格標本の臀びれで測った割合）。長さ: 軟骨がすべて収まるいちばん小さい倍率（形は参考の外形のまま、縦と横で倍率を変える）
                    REACH_ = 0.55; tipd = float(out().max()); kz = tipd / REACH_ / (fd["H"] * TLm)
                    def _poly(o_mm, k):
                        Lb_, Hm_ = (fd["i"] - fd["o"]) * TLm * k, fd["H"] * TLm * kz
                        return [(o_mm + s_ * Lb_, -(_np.interp(o_mm + s_ * Lb_, _sf["z_mm"], _sf[key]) + fd["side"] * (h_ * Hm_ if h_ > 0 else -4.0))) for s_, h_ in fd["poly"]]
                    x_lo = float(xs_.min()); found = None
                    for k in _np.arange(0.8, 2.51, 0.02):
                        for o_mm in _np.arange(fd["o"] * TLm - 20, fd["o"] * TLm + 10.01, 0.5):   # 付け根の前の端は、参考の位置から前へ 20 mm・後ろへ 10 mm まで（CT の軟骨は参考より 12 mm 前から始まる）
                            P_ = _poly(o_mm, k)
                            if (_inside(P_, xs_, zs_) & _inside(P_, xs_ - 1, zs_) & _inside(P_, xs_ + 1, zs_)).all(): found = (k, o_mm); break
                        if found: break
                    k, o_mm = found if found else (2.5, fd["o"] * TLm)
                    # 2026-10-19 案 A（臀びれの軟骨を第 2 背びれの膜に合わせて縮める）: HH_FINCT_MEMB_<ひれ>="k_len,k_height,o_mm" で、膜は前の版の大きさのまま（探さない）
                    if os.environ.get(f"HH_FINCT_MEMB_{fin}"):
                        k, kz, o_mm = [float(v_) for v_ in os.environ[f"HH_FINCT_MEMB_{fin}"].split(",")]
                    FIT_FD[fin] = dict(fd, o=o_mm / TLm, i=(o_mm + (fd["i"] - fd["o"]) * TLm * k) / TLm, H=fd["H"] * kz)
                    poly = _poly(o_mm, k)
                    report[f"fin_membrane_fit_{n}"] = {"k_len": round(float(k), 2), "k_height": round(float(kz), 2), "tip_mm": round(tipd, 1), "o_mm": round(float(o_mm), 1), "base_mm": round(float((fd["i"] - fd["o"]) * TLm * k), 1), "H_mm": round(float(fd["H"] * TLm * kz), 1)}
                elif fin == "anal":
                    dx = max(0.0, fd["o"] * TLm + 2.0 - float(X[w > 0.99].min())); X = X + dx * w; report[f"fin_cart_dx_{n}_mm"] = round(dx, 1)
                ins = lambda xx, zz: _inside(poly, xx, zz)
                if _membfit:
                    # 体の線のすぐ外（1.5 mm 以内）で外形から出る頂点（付け根の前で体の線に沿う所）は、体の中（体の線から 1.5 mm 内）へ入れる
                    o_ = (out() > -1.5) & ~(ins(X, Z) & ins(X - 1, Z) & ins(X + 1, Z))
                    Z = _np.where(o_, -_np.interp(X, _sf["z_mm"], _sf[key]) + fd["side"] * 1.5, Z); co[:, 2] = Z / 1000
                    report[f"fin_cart_tuck_{n}"] = int(o_.sum())
                elif WHOLE:   # ひれ全体を付け根の中ほどを中心に縮めて、外形から出る頂点を 0.5% 以下に（形は変えない）
                    px = (fd["o"] + fd["i"]) / 2 * TLm; pz = -_np.interp(px, _sf["z_mm"], _sf[key]); best = 1.0
                    for sc in _np.arange(1.0, 0.59, -0.02):
                        X2 = px + (X - px) * (1 - w + w * sc); Z2 = pz + (Z - pz) * (1 - w + w * sc)
                        o_ = (w > 0.99) & ~(ins(X2, Z2) & ins(X2 - 1, Z2) & ins(X2 + 1, Z2))
                        best = sc
                        if o_.sum() <= 0.005 * (w > 0.99).sum(): break
                    X = px + (X - px) * (1 - w + w * best); Z = pz + (Z - pz) * (1 - w + w * best); co[:, 2] = Z / 1000
                    report[f"fin_cart_scale_{n}"] = round(float(best), 2)
                bad = (w > 0) & ~(ins(X, Z) & ins(X - 1, Z) & ins(X + 1, Z)); moved = 0
                offs = _np.r_[0, _np.ravel(_np.c_[_np.arange(0.5, 40.5, 0.5), -_np.arange(0.5, 40.5, 0.5)])]
                for i_ in _np.nonzero(bad)[0]:
                    cand = X[i_] + offs; ok = ins(cand, _np.full(len(cand), Z[i_])) & ins(cand - 1, _np.full(len(cand), Z[i_])) & ins(cand + 1, _np.full(len(cand), Z[i_]))
                    if ok.any(): X[i_] = X[i_] + (cand[_np.argmax(ok)] - X[i_]) * w[i_]; moved += 1
                report[f"fin_cart_fit_{n}"] = [int(bad.sum()), moved]
            co[:, 0] = X / 1000; co[:, 1] = Y / 1000
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
        # 腹の線は体の膜（HH_body）の 5 mm ごとのいちばん下（a5_side_fit.json の腹の線は 720 mm より後ろを測っていない）
        bpy.ops.wm.ply_import(filepath=f"{MESH}/HH_body.ply"); _b = bpy.context.selected_objects[0]
        bb = _np.empty(len(_b.data.vertices) * 3); _b.data.vertices.foreach_get("co", bb); bb = bb.reshape(-1, 3) * 1000; _bm = _b.data; bpy.data.objects.remove(_b, do_unlink=True); bpy.data.meshes.remove(_bm)
        bb = bb[_np.abs(bb[:, 1]) < 3]; bel = _np.array([bb[_np.abs(bb[:, 0] - b) < 2.5, 2].min() for b in bins])
        x = co[:, 0] * 1000; z = co[:, 2] * 1000; sel = (x > 690) & (x < 860)
        vc = _np.interp(x, bins, vcz); belly = _np.interp(x, bins, bel); B1 = vc - belly
        dbot = _np.interp(x, _TW["z_mm"], _TW["dbot_mm"]); k = B1 / _np.maximum(B1 - dbot, 1.0)
        m = sel & (z < vc); z[m] = vc[m] - (vc[m] - z[m]) * k[m]
        report["lobe_cart_k_max"] = round(float(k[sel].max()), 3); report["lobe_cart_k_at"] = [[int(b), round(float(_np.interp(b, x[sel], k[sel]) if sel.any() else 1), 2)] for b in (720, 750, 765, 780, 810)]
        co[:, 2] = z / 1000; me.vertices.foreach_set("co", co.ravel()); me.update()
    if hh_warp.SHRINK == 1.0 and (_TW is None or n not in _RIGID) and not (n in _RIGID and (os.environ.get("HH_PECT_DOWN") or os.environ.get("HH_PELV_DOWN"))): return
    me = o.data; co = _np.empty(len(me.vertices) * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    x = co[:, 0] * 1000
    if n in _RIGID:
        # 2026-10-18: HH_PELV_RODS=1 の腹びれの軟骨（hh_finrods.py、腰帯の横棒が正中まで届く）は、付け根を膜（HH_pelvmem_*）の頂点から決める
        #  （軟骨の頂点から決めると横棒の端が付け根になり、下へ回す中心が膜とずれる）
        ref = co.copy()
        _pect_ph = os.environ.get("HH_PECT_PHOTO") == "1" and n in ("HH_pect_R", "HH_pect_L")   # 2026-10-20: a5g_pect_photo.py の胸びれも、膜と同じ中心で回す
        if ((os.environ.get("HH_PELV_RODS") == "1" or os.environ.get("HH_PELV_CT175") == "1" or os.environ.get("HH_PELV_PHOTO") == "1") and n in ("HH_pelv_R", "HH_pelv_L")) or _pect_ph:   # HH_PELV_PHOTO: a5f_pelv_photo.py（2026-10-19）
            bpy.ops.wm.ply_import(filepath=f"{MESH}/{n.replace('pelv_', 'pelvmem_').replace('pect_', 'pectmem_')}.ply"); _m = bpy.context.selected_objects[0]
            ref = _np.empty(len(_m.data.vertices) * 3); _m.data.vertices.foreach_get("co", ref); ref = ref.reshape(-1, 3); _mm = _m.data
            bpy.data.objects.remove(_m, do_unlink=True); bpy.data.meshes.remove(_mm)
        ay = _np.abs(ref[:, 1]); _near = ay < ay.min() + 0.010; bx = float(ref[_near, 0].mean() * 1000)   # 付け根（体の中心にいちばん近い所）
        sgn = _np.sign(ref[:, 1].mean())
        co[:, 0] += (float(hh_warp.warp_mm(bx)) - bx) / 1000; ref[:, 0] += (float(hh_warp.warp_mm(bx)) - bx) / 1000
        if _TW is not None and not (os.environ.get("HH_PELV_PHOTO") == "1" and "pelv" in n):   # 写真の腹びれは a5f_pelv_photo.py がもう動かしてある
            dy = (_np.interp(bx, _TW["z_mm"], _TW["width_new_mm"]) - _np.interp(bx, _TW["z_mm"], _TW["width_old_mm"])) / 2 / 1000
            co[:, 1] += sgn * dy; ref[:, 1] += sgn * dy
        # 2026-10-17 案: 胸びれ・腹びれを付け根のまわりに下へ回す（HH_PECT_DOWN・HH_PELV_DOWN、度。2026-10-14 に決めた姿勢に足す角）。
        #  体軸（Blender x）のまわりに、付け根（体の中心にいちばん近い頂点のまとまり）を中心に回す。右（+y）のひれは −、左は + の向き（先が下へ）
        _deg = float(os.environ.get("HH_PECT_DOWN" if "pect" in n else "HH_PELV_DOWN", 0) or 0)
        if os.environ.get("HH_PELV_PHOTO") == "1" and "pelv" in n: _deg = 0.0   # a5f_pelv_photo.py が付け根 B を中心にもう回してある
        if _deg:
            c0 = ref[_near].mean(0); th = math.radians(_deg) * (-1 if sgn > 0 else 1)
            yy, zz = co[:, 1] - c0[1], co[:, 2] - c0[2]
            co[:, 1] = c0[1] + yy * math.cos(th) - zz * math.sin(th); co[:, 2] = c0[2] + yy * math.sin(th) + zz * math.cos(th)
        # 2026-10-18（プロデューサー「皮膚から飛び出さないようにしてね」）: CT の細かさで作った腹びれの軟骨（HH_PELV_CT175）は、左右の腹びれの間の正中（左右 5 mm 以内）で
        #  腹の線の下へ出た（108 頂点、腹の線から 0.5〜3 mm）。左右の膜はそこまで届かないので、その頂点を腹の線の 1.5 mm 内へ入れる（正中から離れるほど弱く）
        if os.environ.get("HH_PELV_MIDTUCK") == "1" and n in ("HH_pelv_R", "HH_pelv_L"):   # 試し（既定では働かない）: 形が 1853 頂点ぶん変わったのでやめ、膜の面を減らしすぎない方にした
            _sf2 = _json.load(open(os.path.join(hh_paths.WORK, "a5_side_fit.json")))
            belly = -_np.interp(co[:, 0] * 1000, _sf2["z_mm"], _sf2["bot_target_mm"]) / 1000 + 0.0015
            wm = _np.clip((0.009 - _np.abs(co[:, 1])) / 0.002, 0, 1); low = co[:, 2] < belly   # 正中から 7 mm まで、9 mm で 0（5 mm では 13 頂点が残った）
            co[:, 2] = _np.where(low, co[:, 2] + wm * (belly - co[:, 2]), co[:, 2]); report[f"pelv_mid_tuck_{n}"] = int((low & (wm > 0)).sum())
    else:
        co[:, 0] = hh_warp.warp_mm(x) / 1000
    me.vertices.foreach_set("co", co.ravel()); me.update()
for part, (names, target) in PARTS.items():
    objs = []
    for n in names:
        # 2026-10-18: HH_FIN_RODS=1 で、第 2 背びれ・臀びれの軟骨を CT の代わりに図と写真から作る（hh_finrods.py。外形と体の線は膜の板と同じ）
        if os.environ.get("HH_FIN_RODS") == "1" and n in ("HH_dfin2", "HH_anal"):
            import hh_fins, hh_finrods
            fd = hh_fins.FINS["dfin2" if n == "HH_dfin2" else "anal"]
            _sf = _json.load(open(os.path.join(hh_paths.WORK, "a5_side_fit.json"))); _key = "top_target_mm" if fd["side"] < 0 else "bot_target_mm"
            (Vr, Fr), _poly = hh_finrods.median_fin(fd, lambda xm: -float(_np.interp(xm, _sf["z_mm"], _sf[_key])), hh_fins.TL_MM)
            Vr = Vr.copy(); Vr[:, 0] = hh_warp.warp_mm(Vr[:, 0])
            me_ = bpy.data.meshes.new(f"tmp_{n}"); me_.from_pydata((Vr / 1000).tolist(), [], Fr.tolist()); me_.update()
            o = bpy.data.objects.new(f"tmp_{n}", me_); coll.objects.link(o); objs.append(o)
            report[f"fin_rods_{n}"] = [int(len(Vr) // 8), round(float(_np.einsum("ij,ij->i", Vr[Fr[:, 0]], _np.cross(Vr[Fr[:, 1]], Vr[Fr[:, 2]])).sum() / 6 / 1000), 3)]
            continue
        bpy.ops.wm.ply_import(filepath=f"{MESH}/{n}.ply")
        o = bpy.context.selected_objects[0]; o.name = f"tmp_{n}"; objs.append(o)
        _body_warp(o, n)
        # B1 骨組み（2026-10-15）: ひれの膜とひれの軟骨は、まとめる前に出どころの頂点グループを付ける（b1_rig.py が、体の膜ではなくひれだけをひれの骨に付けるため）
        if os.environ.get("HH_RIG") == "1" and n in ("HH_pectmem_L", "HH_pectmem_R", "HH_pelvmem_L", "HH_pelvmem_R", "HH_pect_L", "HH_pect_R", "HH_pelv_L", "HH_pelv_R", "HH_jaw_lower", "HH_teeth_lower"):   # B5: 下あご・下の歯は口の骨へ
            o.vertex_groups.new(name=f"src_{n}").add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
    # 2026-10-17 案: HH_FIN_PLATE=1 で、第 1 背びれの膜を参考の外形（hh_fins.py）の板の面にして体の膜に足す（HH_FIN_PLATE=all では背びれ 2 つと臀びれを、それぞれの部品に）。
    #  背の線・腹の線（a5_side_fit.json）から 4 mm 体の中から立て、厚さ 3.2 mm（ひれの先の膜の厚さとして、体積で作るときの最小と同じ）
    for _fin, _part in PLATE_FINS.items():
        if part != _part: continue
        import hh_fins
        _sf = _json.load(open(os.path.join(hh_paths.WORK, "a5_side_fit.json"))); fd = FIT_FD.get(_fin, hh_fins.FINS[_fin]); TLm = hh_fins.TL_MM
        Lb = (fd["i"] - fd["o"]) * TLm; Hm = fd["H"] * TLm
        bm = bmesh.new(); vs = []
        for s_, h_ in fd["poly"]:
            xm = fd["o"] * TLm + s_ * Lb; vline = _np.interp(xm, _sf["z_mm"], _sf["top_target_mm"] if fd["side"] < 0 else _sf["bot_target_mm"])
            hh = h_ * Hm if h_ > 0 else -4.0
            vs.append(bm.verts.new((xm / 1000, -0.0016, -(vline + fd["side"] * hh) / 1000)))
        f = bm.faces.new(vs); bmesh.ops.triangulate(bm, faces=[f], quad_method="BEAUTY", ngon_method="BEAUTY")
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
        # 2026-10-18 直し: 前は solidify で押し出し、押し出す向きが面の回る向きで変わって、背びれの板は左右 −4.8〜−1.6 mm に寄り、臀びれの板は 2 重（−4.8〜1.6 mm）になっていた。
        #  左右 −1.6 mm の面を作り、+3.2 mm へ押し出して、正中の 1 枚の閉じた板にする
        ext = bmesh.ops.extrude_face_region(bm, geom=bm.faces[:] + bm.edges[:] + bm.verts[:])
        bmesh.ops.translate(bm, verts=[e for e in ext["geom"] if isinstance(e, bmesh.types.BMVert)], vec=(0, 0.0032, 0))
        _ys = [v.co.y for v in bm.verts]; report[f"plate_y_{_fin}_mm"] = [round(min(_ys) * 1000, 2), round(max(_ys) * 1000, 2), len(bm.verts)]
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])   # 外向きにそろえる（腹へ向けた板は、多角形の回る向きが背の板と逆になる）
        me = bpy.data.meshes.new(f"tmp_plate_{_fin}"); bm.to_mesh(me); bm.free()
        ob_ = bpy.data.objects.new(f"tmp_plate_{_fin}", me); coll.objects.link(ob_); objs.append(ob_)
    if not objs: continue
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active; ob.name = f"HH_{part}"; ob.data.name = f"HH_{part}"
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6); bm.to_mesh(ob.data); bm.free()
    n0 = len(ob.data.polygons)
    if target <= 1: target = int(n0 * target)   # 1 以下は割合（HH_FIN_PARTS の部品）
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

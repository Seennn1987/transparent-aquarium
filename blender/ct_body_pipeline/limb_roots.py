"""手足の付け根（肩帯・腰帯）の位置と、関節の回る点を実物に合わせる（計画書 C の記録 102。記録 101 の方針 A〜D）。

  ../../../.venv/bin/python limb_roots.py <入力の骨.npz> <出力のフォルダ> [図の数の json]

入力の骨（chameleon_body_ct.npz）と同じフォルダの chameleon_body_soft.npz も読み、出力のフォルダに同じ名前で書く。
書き出しは CH_CT_NPZ=<出力のフォルダ>/chameleon_body_ct.npz で export_chameleon_gltf.py を走らせる。

どれも静止（CT の座標、mm）で、体軸（rig__axis）の枠 s = 体軸に沿った長さ（頭 → 尾）、l = 左右（+ が左）、d = 背（+ が背）で測る。
長さの単位 S は、左右の肩関節の中点から左右の股関節の中点までの体軸に沿った長さ（実物の X 線は胴がほぼまっすぐなので、
横から測った S は体軸に沿った長さにあたる。肋骨の幅（記録 21 の X 線の紡錘形）もこの S で合っている）。
実物の数は `収集_2026-10-26/付け根の位置/付け根の位置.md`（リポジトリの外）。

A 回る点: 上腕骨・大腿骨の頭は、骨の体に近い端 2 mm の点に球を当てはめた中心。肘・膝・手首・足首は、向き合う 2 本の骨の端
  （それぞれ端から 1 mm の点の重心）の中点。骨組みの頭と尾をこの点へ置き直す（骨の形は変えない）。
B・C 肩帯: 肩甲骨（肩関節 → 肩甲骨の背の端）を、体軸の向きに対して TARGET_SCAP_DEG（頭の向きから測る）に起こす。
  回すのは肩関節のまわり（以前の瓶の姿勢の girdle_tilt は背の端のまわりに回したので、肩関節が第 4 椎骨の下まで後ろへ動いた）。
  実物: DigiMorph の CT（上半身の側面）で、肩甲骨（肩関節 (548,465) → 上の端 (518,238)）は水平から 97.5°。背骨の向きは
  第 1→2 椎骨 (500,282)→(562,250) で尾へ 27° 上がり、後頭顆→第 1 椎骨 (392,405)→(500,282) で 48.7° 上がるので、頭の向きから
  124.5〜146°。AMNH の組み立て骨格は 134°、写真 06 は 132°（以前の girdle_tilt 48°）。重なる 130° にした。
  そのあと肩関節を s = 後頭顆 + SH_S × S、l = ±SH_L × S、d = −SH_D × S へ平行に動かす（左右は鏡にそろえる）。
  上腕から先の骨は、肩関節と同じだけ平行に動かす。肩帯の親は、肩関節の上の椎骨（v02）にする
D 腰帯: 腰帯は 1 つの骨（hL_girdle）で左右がつながっている。股関節（寛骨臼）の左右の間を HIP_L × S × 2 へ広げる。
  左右それぞれ、寛骨臼の高さの点を全部、その上（仙椎へつく腸骨の背の端）と下（恥骨・坐骨の腹の端）へ向けて 0 になる重みで横へ動かす。
  大腿骨から先の骨は、股関節と同じだけ平行に動かす
膜・爪: 手足の骨に重みのある頂点を、その骨の動き（重みで混ぜる）で動かす（付け根の膜は記録 101 の E で作り直す）。
出力の rig__girdle_upright = 1 があると、rig_chameleon_ct.py は瓶の姿勢の girdle_tilt を使わない（ここで起こしたので）。
"""
import json
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter1d
from scipy.spatial import cKDTree

TARGET_SCAP_DEG = 130.0   # 肩甲骨（肩関節 → 背の端）の向き。体軸の頭の向きから背へ測る（90 = 体軸に直角）
SH_S = 0.03               # 肩関節は後頭顆より S × 0.03 尾の側（X 線 3 枚の中央はほぼ 0、AMNH +0.034、DigiMorph +0.05）
SH_L = 0.10               # 左右の肩関節の間 0.20 S（背腹の X 線 2 枚: 0.203・0.202）
SH_D = 0.133              # 肩関節は背骨の線より 0.133 S 下（側面の 3 資料の中央）
HIP_L = 0.0725            # 左右の股関節の間 0.145 S（背腹の X 線 2 枚: 0.122・0.167 の中ほど）
SHOULDER_PARENT = "v02"

src, outdir = sys.argv[1], sys.argv[2]
fig_json = sys.argv[3] if len(sys.argv) > 3 else None
os.makedirs(outdir, exist_ok=True)
d = {k: v for k, v in np.load(src).items()}
soft_src = os.path.join(os.path.dirname(src), "chameleon_body_soft.npz")
sd = {k: v for k, v in np.load(soft_src).items()}
names = [str(n) for n in d["rig__names"]]
ix = {n: i for i, n in enumerate(names)}

A = d["rig__axis"].astype(np.float64); step = float(d["rig__axis_step"])
T = np.gradient(A, axis=0); T /= np.linalg.norm(T, axis=1, keepdims=True)
D = gaussian_filter1d(d["rig__dorsal"].astype(np.float64), 20, axis=0, mode="nearest")
D -= T * (D * T).sum(1, keepdims=True); D /= np.linalg.norm(D, axis=1, keepdims=True)
L = np.cross(T, D)
# 体軸の点は胴まで（s < 130 mm）に限る。CT の個体は尾を巻いていて、尾の軸が肩のそばを通るので、近い点を探すと尾の点に当たる
NA = int(130.0 / step); kd = cKDTree(A[:NA])


def sld(P):
    P = np.atleast_2d(P); j = kd.query(P)[1]; q = P - A[j]
    return np.stack([j * step + (q * T[j]).sum(1), (q * L[j]).sum(1), (q * D[j]).sum(1)], 1)


def from_sld(q):
    """体軸の枠の点 (s, l, d) → CT の座標。"""
    j = int(np.clip(round(q[0] / step), 0, len(A) - 1))
    return A[j] + T[j] * (q[0] - j * step) + L[j] * q[1] + D[j] * q[2]


def frame_at(p):
    j = kd.query(p)[1]; return T[j], L[j], D[j]


V = {n: d[n + "__v"].astype(np.float64) for n in names if n + "__v" in d}
V0 = {n: v.copy() for n, v in V.items()}
head = {n: d["rig__head"][ix[n]].astype(np.float64) for n in names}
tail = {n: d["rig__tail"][ix[n]].astype(np.float64) for n in names}


def end_cap(P, frm, to, band):
    """骨 P のうち、frm → to の向きで frm 側の端から band 以内の点。"""
    u = (to - frm) / np.linalg.norm(to - frm); t = (P - frm) @ u
    return P[t < t.min() + band]


def sphere_fit(P):
    Aa = np.c_[2 * P, np.ones(len(P))]; b = (P ** 2).sum(1)
    x = np.linalg.lstsq(Aa, b, rcond=None)[0]; c = x[:3]
    return c, float(np.sqrt(x[3] + c @ c))


# A: 回る点
piv, report = {}, {}
for c in ("fL", "fR", "hL", "hR"):
    up, lo, tip = c + "_upper", c + "_lower", c + ("_hand" if c[0] == "f" else "_foot")
    cap = end_cap(V[up], head[up], head[lo], 2.0)
    hc, hr = sphere_fit(cap)
    if np.linalg.norm(hc - cap.mean(0)) > 3.0:      # 球が骨の外へ外れたら端の点の重心
        hc = cap.mean(0)
    e1 = end_cap(V[up], head[lo], head[up], 1.0).mean(0); e2 = end_cap(V[lo], head[lo], head[tip], 1.0).mean(0)
    w1 = end_cap(V[lo], head[tip], head[lo], 1.0).mean(0); w2 = end_cap(V[tip], head[tip], tail[tip], 1.0).mean(0)
    piv[up], piv[lo], piv[tip] = hc, 0.5 * (e1 + e2), 0.5 * (w1 + w2)
    report[c] = {"頭の球の半径": round(hr, 2), "ずれ_mm": {b: round(float(np.linalg.norm(piv[b] - head[b])), 2) for b in (up, lo, tip)}}

# S（体軸に沿った長さ）
s_sh = 0.5 * (sld(piv["fL_upper"])[0, 0] + sld(piv["fR_upper"])[0, 0])
s_hp = 0.5 * (sld(piv["hL_upper"])[0, 0] + sld(piv["hR_upper"])[0, 0])
S = s_hp - s_sh
s_occ = sld(head["head"])[0, 0]
report["S_mm"] = round(float(S), 1)
report["前"] = {c: [round(float(x), 2) for x in sld(piv[c + "_upper"])[0]] for c in ("fL", "fR", "hL", "hR")}


def rot(axis, deg):
    a = np.radians(deg); axis = axis / np.linalg.norm(axis); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K


move = {}   # 骨の名前 → 頂点ごとの動き（静止の座標）
# B・C 肩帯
for c, sg in (("fL", 1.0), ("fR", -1.0)):
    g, up = c + "_girdle", c + "_upper"
    G = piv[up]
    # 向きは、肩帯の親の椎骨（SHOULDER_PARENT）を瓶の姿勢で回すときの枠（rig_chameleon_ct.build_pose: 椎骨の中ほどの体軸の向きと、
    # ならしていない rig__dorsal）。体軸をならした枠でそろえると、姿勢を付けたとき左右の肩関節が 4〜5 mm ずれた
    kk = int(SHOULDER_PARENT[1:]); Jv = [float(x) for x in d["rig__J"]]
    i0 = int(round(0.5 * (Jv[kk - 1] + Jv[kk]) / step))
    Tg = A[i0 + 1] - A[i0 - 1]; Tg /= np.linalg.norm(Tg)
    Dg = d["rig__dorsal"][i0].astype(np.float64); Dg -= Tg * (Dg @ Tg); Dg /= np.linalg.norm(Dg); Lg = np.cross(Tg, Dg)
    sc = head[g] - G                                   # 肩甲骨（肩関節 → 背の端）
    cur = np.degrees(np.arctan2(sc @ Dg, sc @ -Tg))   # 頭の向きから背へ
    R = rot(Lg, (TARGET_SCAP_DEG - cur) * np.sign(np.cross(-Tg, Dg) @ Lg))
    tgt = A[i0] + Tg * (s_occ + SH_S * S - i0 * step) + Lg * (sg * SH_L * S) + Dg * (-SH_D * S)
    newG = tgt
    Vg = (V[g] - G) @ R.T + newG
    move[g] = Vg - V[g]
    newtop = R @ (head[g] - G) + newG
    sc2 = newtop - newG; Tn, Dn = Tg, Dg
    report[c + "_肩甲骨"] = {"前の向き_deg": round(float(cur), 1), "今の向き_deg": round(float(np.degrees(np.arctan2(sc2 @ Dn, sc2 @ -Tn))), 1),
                           "長さ_mm": round(float(np.linalg.norm(sc)), 1)}
    dG = newG - G
    for b in [n for n in names if n.startswith(c + "_") and n != g]:
        if b in V:
            move[b] = np.repeat(dG[None], len(V[b]), 0)
    head[g], tail[g] = newtop, newG
    for b in [n for n in names if n.startswith(c + "_") and n != g]:
        head[b] = head[b] + dG; tail[b] = tail[b] + dG
    for b in (up, c + "_lower", c + "_hand"):
        piv[b] = piv[b] + dG

# D 腰帯
pel = "hL_girdle"; Qp = sld(V[pel])
dtop, dbot = Qp[:, 2].max(), Qp[:, 2].min()
mv = np.zeros_like(V[pel])
hip_now = {c: sld(piv[c + "_upper"])[0] for c in ("hL", "hR")}
mid_l = 0.5 * (hip_now["hL"][1] + hip_now["hR"][1])
# 左右の股関節は、高さと前後もそろえる（標本の腰帯は左右で 2 mm ずつ高さと前後がずれていた。保存の変形と読む）。
# 枠は腰帯の親の椎骨を瓶の姿勢で回すときの枠（肩と同じ）
kk = int(str(d["rig__parent"][ix[pel]])[1:]); Jv = [float(x) for x in d["rig__J"]]
i1 = int(round(0.5 * (Jv[kk - 1] + Jv[kk]) / step))
Th = A[i1 + 1] - A[i1 - 1]; Th /= np.linalg.norm(Th)
Dh = d["rig__dorsal"][i1].astype(np.float64); Dh -= Th * (Dh @ Th); Dh /= np.linalg.norm(Dh); Lh = np.cross(Th, Dh)
hp = {c: piv[c + "_upper"] - A[i1] for c in ("hL", "hR")}
hs = 0.5 * sum(hp[c] @ Th for c in hp); hd = 0.5 * sum(hp[c] @ Dh for c in hp)
for c, sg in (("hL", 1.0), ("hR", -1.0)):
    q = hip_now[c]
    dH = A[i1] + Th * hs + Lh * (sg * HIP_L * S) + Dh * hd - piv[c + "_upper"]
    side = np.sign(Qp[:, 1] - mid_l) == sg
    w = np.where(Qp[:, 2] >= q[2], (dtop - Qp[:, 2]) / max(dtop - q[2], 1e-6), (Qp[:, 2] - dbot) / max(q[2] - dbot, 1e-6))
    w = np.clip(w, 0, 1) ** 0.7
    w *= np.clip(np.abs(Qp[:, 1] - mid_l) / 1.0, 0, 1)        # 正中の 1 mm は動かさない（左右の板が離れて見えないように）
    mv[side] += w[side, None] * dH[None]
    for b in [n for n in names if n.startswith(c + "_") and n != pel]:
        if b in V:
            move[b] = np.repeat(dH[None], len(V[b]), 0)
        head[b] = head[b] + dH; tail[b] = tail[b] + dH
    for b in (c + "_upper", c + "_lower", c + "_foot"):
        piv[b] = piv[b] + dH
move[pel] = mv

# 骨の頂点
for b, m in move.items():
    d[b + "__v"] = (V[b] + m).astype(d[b + "__v"].dtype)
# 骨組み: 回る点へ置き直す（尾は子の頭）
for c in ("fL", "fR", "hL", "hR"):
    up, lo, tip = c + "_upper", c + "_lower", c + ("_hand" if c[0] == "f" else "_foot")
    head[up], head[lo], head[tip] = piv[up], piv[lo], piv[tip]
    tail[up], tail[lo] = piv[lo], piv[tip]
    if c[0] == "f":
        tail[c + "_girdle"] = piv[up]
H2 = d["rig__head"].copy(); T2 = d["rig__tail"].copy(); P2 = d["rig__parent"].copy()
for n in names:
    H2[ix[n]], T2[ix[n]] = head[n], tail[n]
for c in ("fL", "fR"):
    P2[ix[c + "_girdle"]] = SHOULDER_PARENT
d["rig__head"], d["rig__tail"], d["rig__parent"] = H2, T2, P2
d["rig__girdle_upright"] = np.array(1)
report["後"] = {c: [round(float(x), 2) for x in sld(piv[c + "_upper"])[0]] for c in ("fL", "fR", "hL", "hR")}
report["比_S"] = {"肩関節の間": round(float(np.linalg.norm(piv["fL_upper"] - piv["fR_upper"]) / S), 3),
                 "股関節の間": round(float(np.linalg.norm(piv["hL_upper"] - piv["hR_upper"]) / S), 3)}

# 膜と爪: 手足の骨の重みで動かす（骨ごとに、最も近い元の頂点の動き）
trees = {b: cKDTree(V0[b]) for b in move}


def carry(P, widx, wval, wnames):
    out = np.zeros_like(P, dtype=np.float64)
    for a in range(widx.shape[1]):
        for bi in np.unique(widx[:, a]):
            b = str(wnames[int(bi)])
            if b not in move:
                continue
            m = (widx[:, a] == bi) & (wval[:, a] > 1e-4)
            if m.any():
                out[m] += wval[m, a, None] * move[b][trees[b].query(P[m])[1]]
    return out


for key in ("soft", "org_claw"):
    P = sd[key + "__v"].astype(np.float64)
    dm = carry(P, sd[key + "__w_idx"], sd[key + "__w_val"], sd[key + "__names"])
    sd[key + "__v"] = (P + dm).astype(sd[key + "__v"].dtype)
    report[key + "_動いた頂点"] = int((np.linalg.norm(dm, axis=1) > 1e-3).sum())

np.savez_compressed(os.path.join(outdir, "chameleon_body_ct.npz"), **d)
np.savez_compressed(os.path.join(outdir, "chameleon_body_soft.npz"), **sd)
print(json.dumps(report, ensure_ascii=False, indent=1))
if fig_json:
    json.dump(report, open(fig_json, "w"), ensure_ascii=False, indent=1)

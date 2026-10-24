"""
メンダコ: Blender で融合する前の形の素材を作る（2026-10-24 第 2 版。A3 の単純な部品と b1 第 1 版を作り直す）。

  .venv/bin/python -I blender/mendako/b1_shape_parts.py

出力（blender/mendako/work/、git に入れない）。融合するもの:
  b1_body.obj    体: 傘 + 頭（b0_fit_head_skirt.py の当てはめ）。背に腕の筋、口側は腕のあいだが持ち上がる
  b1_eyes_bulge.obj  眼の盛り上がり（球）とまぶたの縁（輪）
  b1_fins.obj    ひれ: 耳の形。外の縁は丸まった管、内は頭の横へつながる膜。下の端は内へ巻く
  b1_arms.obj    腕 8 本（a3 と同じ道。口側に出て、縁から先は背へ巻く）
融合しないもの:
  b1_eyeballs.obj  眼球（まぶたの開口からのぞく暗い球）

軸: +Y 背、+Z 前、+X 体の左。W = 1（約 138 mm）。

形の元（2026-10-24 に生体の写真を見直した）:
  - 頭・傘: b0_head_skirt.json（決めた正面の線に最大 4 mm、眼の位置の面 0.31）
  - 眼: Sunshine1・4 で、頭の前の上の角に半球として飛び出し、まぶたの縁に囲まれた開口が外・前・上を向く。
        開口の位置は A2 と同じ（左右の間 0.31、前の端から 0.42）。盛り上がりの球 半径 0.06、表面から 0.035 出す
  - ひれ: Sunshine4 の左のひれ（原寸 px）: 外の端 x 1100（中心 2112 から横幅 2500 で u −0.81）、上の端 y 1012（v 0.31）、
        下の袋 y 1330〜1425（v 0.14〜0.18）。Sunshine2 では外の端 u −0.70。外の端は 2 枚の間をとって 0.37 W。
        頭の横の、眼より後ろ（前の端から 0.53、殻と同じ高さ）から出る
  - 縁: Sunshine1 で厚く丸まり、腕ごとに波打つ。厚み 0.035 W
"""

import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a2_parts as A  # noqa: E402
import a3_membrane_arms as M  # noqa: E402
from b0_fit_head_skirt import HeadSkirt  # noqa: E402

RIDGE = dict(amp=0.006, width=0.08, start=0.45)   # 第 2 版（幅 0.04、高さ 0.008）はテントの折り目に見えた
ORAL_LIFT = dict(amp=0.022, width=0.05)    # 腕の道からの距離で、腕のあいだの口側を持ち上げる
# 腕の弓なり（2026-10-24 第 12 版）: Verhoeff 2024 図 12 A（Sasaki 1929 の雄の口側、口 x 755・y 1000）の吸盤の列で、どの腕も口の近くでは
#   後ろ寄りに出て、先が前へ曲がる（第 2 腕は横へ出て x 1200 で前へ、第 4 腕は後ろへ下りて外で前へ回り込む）。付け根の向きと弦のずれ
#   約 10°（第 1 腕）・25°（第 2・3 腕）・40°（第 4 腕）から、膨らみ ≈ ずれ（rad）÷ 4
ARM_BOW = {13.0: 0.04, 51.0: 0.10, 95.0: 0.10, 143.0: 0.15}
RIM_ROLL = 0.12    # 縁から内へこの割合（ρ）で、上の面を口側の面へ丸く下ろして閉じる（第 11 版は厚み 0.045 を一定にして平らな帯が出た）
EYE = dict(r=0.048, out=0.022, lid_r=0.03, lid_tube=0.005, dir=(0.62, 0.62, 0.48), ball_out=0.0058, ball_scale=0.90, lid=False)
# 眼（第 11 版、2026-10-24）: Sunshine4 の左の眼の盛り上がりは x 1560〜1800 の約 240 px ÷ 横幅 2500 px = 径 0.096 W（第 10 版は 0.14 で大きすぎ）、
#   開口は約 120 px = 0.048 W。眼球の出し量 0.0058 は、のぞく暗い丸の径が約 0.05 W になる値。まぶたの輪は融合するとボタンの突起に見えた（第 6・7 版）ので使わない
RIM_T = 0.045       # 縁の厚み。第 2 版の 0.035 は薄く見えた
ARM_R = ([0, 0.12, 0.45, 0.8, 1.0], [0.03, 0.035, 0.03, 0.018, 0.012])   # 腕の半径。第 2 版（先 0.006）は先が細い輪に見えた
FIN_ARCH = [(0.0, 0.05), (0.035, 0.065), (0.08, 0.06), (0.115, 0.025), (0.13, -0.03), (0.115, -0.08), (0.08, -0.10)]   # 付け根からの (外, 上)
# ひれ（第 11 版）: Sunshine4 の左のひれ（中心 x 2112、横幅 2500、砂 y 1785）で、頭とのつなぎ x 1480（0.25 W）、外の端 x 1090（0.41 W。Sunshine2 では 0.35）、
#   上の端 y 1010（高さ 0.31）、下の袋 y 1430（0.14）。幅 0.156 W・高さ 0.168 W。第 10 版（幅 0.16 + 付け根の位置、高さ 0.215）は大きすぎた
FIN_X_ROOT = 0.25
FIN_ROOT_Y = 0.245


def load_model():
    p = json.load(open(os.path.join(A.OUT, "b0_head_skirt.json"), encoding="utf-8"))["params"]
    return HeadSkirt([p[k] for k in ("Hs", "p", "a", "c", "zh", "ytop", "n", "m", "Hs_fb")])


def arm_angles():
    out = []
    for deg in M.ARM_DEG.values():
        out += [np.radians(deg), -np.radians(deg)]
    return np.array(out)


def ang_dist(a, b):
    return np.abs((a - b + np.pi) % (2 * np.pi) - np.pi)


def arm_lines():
    """腕の道（膜のある所）を上から見た折れ線 (x, z) にする。b1 の腕（arms()）と同じ道"""
    M.ARM_BOW = ARM_BOW
    body = A.Body(peak=0.0)
    lines = []
    for deg in M.ARM_DEG.values():
        for side in (1, -1):
            pts, web_frac, _ = M.arm_path(body, side * deg)
            k = int(len(pts) * web_frac)
            lines.append(pts[:k][:, [0, 2]])
    return lines


def dist_to_lines(P, lines):
    """点 P (N, 2) から、折れ線の集まりまでの最短距離"""
    best = np.full(len(P), np.inf)
    for L in lines:
        a, b = L[:-1], L[1:]
        ab = b - a
        for k in range(len(a)):
            t = np.clip(((P - a[k]) @ ab[k]) / (ab[k] @ ab[k] + 1e-12), 0, 1)
            d = np.hypot(*(P - (a[k] + t[:, None] * ab[k])).T)
            best = np.minimum(best, d)
    return best


def body_volume(m, n_r=170, n_t=480):
    body = m.body
    rr = np.linspace(0, 1, n_r) ** 0.85
    tt = np.linspace(0, 2 * np.pi, n_t, endpoint=False)
    T, Rr = np.meshgrid(tt, rr, indexing="ij")
    Rt = body.Dc(T.ravel()).reshape(T.shape)
    X, Z = np.sin(T) * Rr * Rt, np.cos(T) * Rr * Rt
    x, z, rho = X.ravel(), Z.ravel(), Rr.ravel()
    h = np.where(rho < 1, m.h(x, z * 0.9999), m.h(x * 0.999, z * 0.999))
    h = np.maximum(h, 0.03)
    d = dist_to_lines(np.stack([x, z], 1), arm_lines())
    ramp = np.clip((rho - RIDGE["start"]) / 0.25, 0, 1)
    h = h + RIDGE["amp"] * ramp * np.exp(-(d / (RIDGE["width"] / 2)) ** 2)
    between = 1 - np.exp(-(d / ORAL_LIFT["width"]) ** 2)
    b = ORAL_LIFT["amp"] * between * np.clip((rho - 0.3) / 0.7, 0, 1) ** 1.5
    b = np.minimum(b, np.maximum(0.0, h - 0.015))
    # 縁: 内から RIM_ROLL の所から、上の面を口側の面へ丸く下ろす（縁で上と下が出会って閉じる）
    sr = np.clip((rho - (1 - RIM_ROLL)) / RIM_ROLL, 0, 1)
    h = b + (h - b) * np.sqrt(np.clip(1 - sr * sr, 0, 1))
    top = np.stack([x, h, z], 1)
    bot = np.stack([x, b, z], 1)
    verts = np.vstack([top, bot])
    nb = len(top)
    faces = []
    for i in range(n_t):
        j = (i + 1) % n_t
        for k in range(n_r - 1):
            a, b2, c, dd = i * n_r + k, j * n_r + k, j * n_r + k + 1, i * n_r + k + 1
            faces += [(a, c, b2), (a, dd, c)]
            faces += [(a + nb, b2 + nb, c + nb), (a + nb, c + nb, dd + nb)]
    v, f = M.weld(verts, np.array(faces))
    if A.signed_volume(v, f) < 0:
        f = f[:, ::-1]
    return v, f


def torus(c, nrm, R, r, n1=40, n2=12):
    nrm = np.array(nrm, float)
    nrm /= np.linalg.norm(nrm)
    a1 = np.cross(nrm, [0, 1.0, 0])
    a1 /= np.linalg.norm(a1)
    a2 = np.cross(nrm, a1)
    verts, faces = [], []
    for i in range(n1):
        u = 2 * np.pi * i / n1
        ring_c = c + R * (np.cos(u) * a1 + np.sin(u) * a2)
        radial = (np.cos(u) * a1 + np.sin(u) * a2)
        for j in range(n2):
            w = 2 * np.pi * j / n2
            verts.append(ring_c + r * (np.cos(w) * radial + np.sin(w) * nrm))
    for i in range(n1):
        for j in range(n2):
            a, b = i * n2 + j, ((i + 1) % n1) * n2 + j
            c2, d = i * n2 + (j + 1) % n2, ((i + 1) % n1) * n2 + (j + 1) % n2
            faces += [(a, b, d), (a, d, c2)]
    v, f = np.array(verts), np.array(faces)
    if A.signed_volume(v, f) < 0:
        f = f[:, ::-1]
    return v, f


def eyes(m):
    body = m.body
    ze = body.z_at(A.EYE["from_front"])
    bulges, balls = [], []
    for s in (1, -1):
        x = s * A.EYE["spacing"] / 2
        y = float(m.h(np.array([x]), np.array([ze]))[0])
        d = np.array([s * EYE["dir"][0], EYE["dir"][1], EYE["dir"][2]])
        d /= np.linalg.norm(d)
        c = np.array([x, y + EYE["out"] - EYE["r"], ze])
        bulges.append(A.ellipsoid(tuple(c), (EYE["r"],) * 3, n=28))
        if EYE["lid"]:
            lid_c = c + d * (EYE["r"] - 0.004)
            bulges.append(torus(lid_c, d, EYE["lid_r"], EYE["lid_tube"]))
        balls.append(A.ellipsoid(tuple(c + d * EYE["ball_out"]), (EYE["r"] * EYE["ball_scale"],) * 3, n=32))
    return bulges, balls


def x_head(m, y, z):
    xs = np.linspace(0, 0.5, 3000)
    hh = m.h(xs, np.full_like(xs, z))
    i = np.nonzero(hh < y)[0]
    return float(xs[i[0]]) if len(i) else 0.3


def fin(m, side):
    """耳: 外の縁（丸まった管）と、縁から頭の横へ張る膜（厚み 0.012、中ほどを後ろへへこませる）"""
    body = m.body
    zf = body.z_at(A.SHELL["from_front"])
    x0 = FIN_X_ROOT
    arch = np.array(FIN_ARCH)
    # なめらかな縁の道（Catmull-Rom）
    pts = []
    P = np.vstack([arch[0], arch, arch[-1]])
    for i in range(1, len(P) - 2):
        for t in np.linspace(0, 1, 10, endpoint=False):
            t2, t3 = t * t, t * t * t
            pts.append(0.5 * ((2 * P[i]) + (-P[i - 1] + P[i + 1]) * t + (2 * P[i - 1] - 5 * P[i] + 4 * P[i + 1] - P[i + 2]) * t2
                              + (-P[i - 1] + 3 * P[i] - 3 * P[i + 1] + P[i + 2]) * t3))
    pts.append(arch[-1])
    pts = np.array(pts)
    n = len(pts)
    s = np.linspace(0, 1, n)
    rim = np.stack([side * (x0 + pts[:, 0]), FIN_ROOT_Y + pts[:, 1], zf + 0.025 * s ** 2], 1)   # 下の端は前へ巻く
    rim_r = 0.012 * (1 - 0.35 * s)
    rim_tube = M.tube(rim, rim_r, ring=12)
    # 膜: 縁の各点から、同じ高さの頭の横の点まで。中ほどを後ろへ
    nt = 14
    top, bot = [], []
    for i in range(n):
        pin = np.array([side * x_head(m, rim[i, 1], zf) * 0.92, rim[i, 1] * 0.97, zf])
        for j, t in enumerate(np.linspace(0, 1, nt)):
            p = rim[i] * (1 - t) + pin * t
            p = p + np.array([0, 0, -0.04 * np.sin(np.pi * t) * np.sin(np.pi * s[i])])
            th = 0.006 + 0.004 * t
            top.append(p + np.array([0, 0, th]))
            bot.append(p - np.array([0, 0, th]))
    verts = np.array(top + bot)
    nb = len(top)
    faces = []
    for i in range(n - 1):
        for j in range(nt - 1):
            a, b, c, d = i * nt + j, (i + 1) * nt + j, (i + 1) * nt + j + 1, i * nt + j + 1
            faces += [(a, b, c), (a, c, d), (a + nb, c + nb, b + nb), (a + nb, d + nb, c + nb)]

    def strip(idx):
        for p, q in zip(idx[:-1], idx[1:]):
            faces.extend([(p, q, q + nb), (p, q + nb, p + nb)])
    strip([i * nt for i in range(n)][::-1])
    strip([i * nt + nt - 1 for i in range(n)])
    strip(list(range(nt)))
    strip([(n - 1) * nt + j for j in range(nt)][::-1])
    mv, mf = M.weld(verts, np.array(faces))
    if A.signed_volume(mv, mf) < 0:
        mf = mf[:, ::-1]
    return [rim_tube, (mv, mf)]


def arms(m):
    M.arm_radius = lambda s: np.interp(s, *ARM_R)
    M.FREE_TIP = 0.08                # 生体では背の膜が腕の先近くまで届く（ToL: web extends nearly to arm tips along dorsal margins）。
                                     # Taki の 1/5 は固定標本。第 5 版（1/5 の半分をまっすぐ）は縁から棘が突き出た
    M.CURL_ANGLE = np.radians(200)
    M.CURL_STRAIGHT = 0.0
    M.ARM_BOW = ARM_BOW
    body = A.Body(peak=0.0)
    out = []
    for deg in M.ARM_DEG.values():
        for side in (1, -1):
            arm, _, _, _ = M.arm_parts(body, deg, side)
            out.append(arm)
    return out


def main():
    os.makedirs(A.WORK, exist_ok=True)
    m = load_model()
    bv, bf = body_volume(m)
    print("体", len(bv), "頂点、開いた辺", M.open_edges(bf), "体積", round(A.signed_volume(bv, bf), 4))
    A.save_obj(os.path.join(A.WORK, "b1_body.obj"), bv, bf)
    bul, balls = eyes(m)
    A.save_obj(os.path.join(A.WORK, "b1_eyes_bulge.obj"), *M.merge(bul))
    A.save_obj(os.path.join(A.WORK, "b1_eyeballs.obj"), *M.merge(balls))
    fins = fin(m, 1) + fin(m, -1)
    for k, (fv, ff) in enumerate(fins):
        print("ひれの部品", k, "開いた辺", M.open_edges(ff), "体積", round(A.signed_volume(fv, ff), 6))
    A.save_obj(os.path.join(A.WORK, "b1_fins.obj"), *M.merge(fins))
    A.save_obj(os.path.join(A.WORK, "b1_arms.obj"), *M.merge(arms(m)))
    print("出力", A.WORK)


if __name__ == "__main__":
    main()

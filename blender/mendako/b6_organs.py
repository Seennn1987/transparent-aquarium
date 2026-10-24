"""
メンダコ 手順 A5: 中の部品（頭の軟骨・平衡石・鰓・心臓・鰓心臓・消化管・消化腺）を作る（2026-10-24）。

  .venv/bin/python -I blender/mendako/b6_organs.py

形は、楕円体と管の符号つき距離をなめらかにつなぎ（smooth union）、マーチングキューブ（scikit-image）で面にする。
出力: blender/mendako/work/b6_<部品>.obj（git に入れない）、docs/mendako/b6_organs.json（置いた所と、体の中に収まるか）

軸: +Y 背、+Z 前、+X 体の左。W = 1（横幅、約 138 mm）。H(x, z) は体の高さ（b0_fit_head_skirt.py の当てはめ、第 12 版）。
置き場所の元（図の座標 → モデルの座標。図は背から見た図で、前が上、図の左が体の左）:
  Meyer 1906 Taf. XI 図 2（11-meyer1906-taf11-right.jpg、1/3 に縮めた座標）: 眼の中心 (145, 525)・(570, 530)、外套の開口 y 1093。
    横は眼の間 420 px = 0.31 W、前後は眼 → 開口 563 px = 0.394 W（Meyer 図 1 の眼 0.42・開口 0.83 の差 × 長さ 0.96 W）から、約 1390 px/W。
    正中 x 357。x = (357 − 図の x) / 1390、z = 0.059 − (図の y − 530) / 1390（0.059 は眼の z）
    食道の膨らみ（黄の管）(330〜420, 560〜660)、消化腺の葉（桃）(320〜420, 640〜760)、第一胃（黄の横長）(270〜430, 770〜850)、
    鰓（左、ひだ）(150〜270, 820〜930)、鰓心臓（灰青の丸）(150〜200, 750〜810)、消化腺のもう一つの葉（黄）(280〜380, 850〜940)
  Meyer 1906 Taf. XIII 図 14（14-meyer1906-taf13.jpg、1/2 に縮めた座標）: 眼の中心 (290, 340)・(705, 340)、正中 x 497、約 1380 px/W。
    頭（脳と頭の軟骨）は眼のあいだ x 430〜565、y 270〜380。心臓（中央の赤い塊）(515, 600)、鰓心臓 (300, 600)・(690, 600)
  原記載 図 9（正中の断面、半ば模式）: 体の厚み（下 y 2550 〜 上 約 2265）に対して、胃の中心 y 2390 は下から 0.56、
    口球 y 2490 は 0.21、腸の曲がり y 2400 は 0.53、肛門 an は前の端から 0.75（x 1130、前の端 60・後ろの端 約 1490）
  鰓葉 6 枚（原記載の本文）、消化腺 2 葉（Verhoeff 2024）、頭の軟骨は脳を囲み、平衡胞の上に孔がある（Meyer 1906 本文）
  大きさの出典が無いもの: 平衡石（画面で見える最小として半径 0.004 W ≈ 0.55 mm）、頭の軟骨の厚み（0.004 W）
"""

import json
import os
import sys

import numpy as np
from skimage.measure import marching_cubes

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a2_parts as A  # noqa: E402
import a3_membrane_arms as M  # noqa: E402
import b1_shape_parts as B  # noqa: E402

STEP = 0.0015
ZE = 0.059          # 眼の z（Body(peak=0).z_at(0.42)）


def fig2(x, y):
    return (357 - x) / 1390, ZE - (y - 530) / 1390


def fig14(x, y):
    return (497 - x) / 1380, ZE - (y - 340) / 1380


def ell(p, c, r):
    """楕円体の符号つき距離の近似（k0 (k0 − 1) / k1）。前の (|p/r| − 1)·min(r) は、細長い楕円体（眼窩の板 0.035 対 0.008）で端が四角い板になった"""
    d = p - np.asarray(c)
    r = np.asarray(r, float)
    k0 = np.linalg.norm(d / r, axis=-1)
    k1 = np.linalg.norm(d / (r * r), axis=-1)
    return k0 * (k0 - 1) / np.maximum(k1, 1e-9)


def capsule(p, a, b, r):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(p - (a + t[..., None] * ab), axis=-1) - (r[0] + (r[1] - r[0]) * t if isinstance(r, tuple) else r)


def smin(a, b, k=0.006):
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1)
    return b * (1 - h) + a * h - k * h * (1 - h)


def mesh_from_sdf(fn, lo, hi):
    xs = np.arange(lo[0], hi[0], STEP)
    ys = np.arange(lo[1], hi[1], STEP)
    zs = np.arange(lo[2], hi[2], STEP)
    P = np.stack(np.meshgrid(xs, ys, zs, indexing="ij"), -1)
    d = fn(P)
    d = np.pad(d, 1, constant_values=1.0)
    v, f, _, _ = marching_cubes(d, 0.0, spacing=(STEP, STEP, STEP))
    v = v - STEP + np.array([xs[0], ys[0], zs[0]])
    if A.signed_volume(v, f) < 0:
        f = f[:, ::-1]
    return v, f


def main():
    m = B.load_model()
    H = lambda x, z: float(m.h(np.array([x]), np.array([z]))[0])   # noqa: E731
    out, info = {}, {}

    # 頭の軟骨（Taf. XIII 図 14: x 430〜565 → ±0.049、y 270〜380 → z 0.110〜0.030）。脳を囲む殻（厚み 0.004）。
    #  2026-10-24: 眼の下の左右の眼窩の板も足していたが、図に描かれておらず出典が無いので外した（ページで四角い板に見えた）
    zc = (fig14(497, 270)[1] + fig14(497, 380)[1]) / 2
    yc = 0.55 * H(0, zc)
    head = dict(c=(0, yc, zc), r=(0.049, 0.03, 0.04))

    def cranium(P):
        return np.abs(ell(P, head["c"], head["r"])) - 0.004
    out["HeadCartilage"] = mesh_from_sdf(cranium, (-0.13, yc - 0.06, zc - 0.07), (0.13, yc + 0.06, zc + 0.07))
    info["HeadCartilage"] = dict(centre=head["c"], half=head["r"], from_="Meyer 1906 Taf. XIII 図 14 の眼のあいだ")

    # 平衡石: 頭の軟骨の中の、腹側・後ろ寄り（平衡胞の上に頭の軟骨の孔、Meyer 本文）
    def statolith(P):
        return np.minimum(*[ell(P, (s * 0.015, yc - 0.018, zc - 0.012), (0.004, 0.003, 0.004)) for s in (1, -1)])
    out["Statolith"] = mesh_from_sdf(statolith, (-0.03, yc - 0.03, zc - 0.03), (0.03, yc, zc + 0.01))

    # 消化管: 口球の上 → 頭の軟骨を抜ける食道 → 食道の膨らみ（図 2 の黄の管）→ 第一胃（黄の横長）→ 盲嚢 → 腸 → 肛門（図 9 の an）
    zm = (m.body.z_front + m.body.z_back) / 2
    crop_a, crop_b = fig2(375, 560), fig2(375, 660)
    st_c = fig2(350, 810)
    yst = 0.56 * H(st_c[0], st_c[1])
    z_anus = m.body.z_front - 0.75 * (m.body.z_front - m.body.z_back)
    y_anus = 0.40 * H(0, z_anus)
    p0 = (0.0, 0.07, zm)
    p1 = (0.0, yc, zc - 0.005)
    p2 = (crop_a[0], yc + 0.01, crop_a[1] - 0.02)
    p3 = (crop_b[0], yst + 0.02, crop_b[1])
    stomach = dict(c=(st_c[0], yst, st_c[1]), r=(0.058, 0.03, 0.03))
    caecum = dict(c=(st_c[0] + 0.055, yst - 0.01, st_c[1] - 0.03), r=(0.022, 0.02, 0.02))
    p5 = (st_c[0] + 0.03, 0.5 * H(0.03, st_c[1] - 0.06), st_c[1] - 0.06)
    p6 = (-0.015, 0.45 * H(0, z_anus + 0.04), z_anus + 0.04)
    p7 = (0.0, y_anus, z_anus)

    def gut(P):
        d = capsule(P, p0, p1, 0.007)
        d = smin(d, capsule(P, p1, p2, 0.008))
        d = smin(d, capsule(P, p2, p3, (0.016, 0.022)), 0.01)
        d = smin(d, ell(P, stomach["c"], stomach["r"]), 0.012)
        d = smin(d, ell(P, caecum["c"], caecum["r"]), 0.008)
        d = smin(d, capsule(P, caecum["c"], p5, 0.007))
        d = smin(d, capsule(P, p5, p6, 0.006))
        d = smin(d, capsule(P, p6, p7, 0.005))
        return d
    out["Gut"] = mesh_from_sdf(gut, (-0.1, 0.02, z_anus - 0.03), (0.12, 0.38, zc + 0.03))
    info["Gut"] = dict(stomach=stomach, crop=[p2, p3], anus=p7)

    # 消化腺 2 葉（図 2 の桃の葉 (320〜420, 640〜760) と、黄の葉 (280〜380, 850〜940)）
    da = fig2(370, 700)
    db = fig2(330, 895)
    lobes = [dict(c=(da[0], 0.55 * H(*da), da[1]), r=(0.042, 0.033, 0.045)), dict(c=(db[0], 0.5 * H(*db), db[1]), r=(0.045, 0.03, 0.035))]

    def dg(P):
        return np.minimum(ell(P, lobes[0]["c"], lobes[0]["r"]), ell(P, lobes[1]["c"], lobes[1]["r"]))
    out["DigestiveGland"] = mesh_from_sdf(dg, (-0.1, 0.05, db[1] - 0.06), (0.1, 0.4, da[1] + 0.07))
    info["DigestiveGland"] = lobes

    # 鰓（図 2 の左の鰓 (150〜270, 820〜930) を左右に）: 半分のオレンジの形。外へ向いた丸い面に、鰓葉 6 枚のひだ
    gc = fig2(210, 875)
    gills = [dict(c=(s * gc[0], 0.42 * H(gc[0], gc[1]), gc[1]), r=(0.045, 0.03, 0.04)) for s in (1, -1)]

    def gill(P):
        ds = []
        for g in gills:
            q = P - np.asarray(g["c"])
            ang = np.arctan2(q[..., 1], q[..., 2])
            d = ell(P, g["c"], g["r"]) + 0.004 * np.sin(6 * ang)
            d = np.maximum(d, -(np.sign(g["c"][0]) * q[..., 0]) - 0.01)   # 内側（正中の側）を平らに切る
            ds.append(d)
        return np.minimum(*ds)
    out["Gill"] = mesh_from_sdf(gill, (-0.2, 0.0, gc[1] - 0.06), (0.2, 0.3, gc[1] + 0.06))
    info["Gill"] = gills

    # 心臓（図 14 の中央の赤い塊）と鰓心臓（図 14 の左右、図 2 の灰青の丸）
    hc = fig14(515, 600)
    heart = dict(c=(0.0, 0.5 * H(0, hc[1]), hc[1]), r=(0.03, 0.016, 0.018))
    out["Heart"] = mesh_from_sdf(lambda P: ell(P, heart["c"], heart["r"]), (-0.05, heart["c"][1] - 0.03, hc[1] - 0.03), (0.05, heart["c"][1] + 0.03, hc[1] + 0.03))
    bh = fig14(300, 600)
    bhs = [dict(c=(s * bh[0], 0.45 * H(bh[0], bh[1]), bh[1]), r=(0.015, 0.015, 0.015)) for s in (1, -1)]
    out["BranchialHeart"] = mesh_from_sdf(lambda P: np.minimum(*[ell(P, b["c"], b["r"]) for b in bhs]), (-0.2, 0.0, bh[1] - 0.03), (0.2, 0.3, bh[1] + 0.03))
    info["Heart"] = heart
    info["BranchialHeart"] = bhs

    report = {}
    for name, (v, f) in out.items():
        oe, nm = M.open_edges(f)
        h = m.h(v[:, 0], v[:, 2])
        gap = float((h - v[:, 1]).min())
        report[name] = dict(faces=len(f), open_edges=oe, nonmanifold=nm, signed_volume=A.signed_volume(v, f),
                            top_gap_mm=round(gap * A.W_MM, 1), bottom_mm=round(float(v[:, 1].min()) * A.W_MM, 1),
                            centre=[round(float(c), 3) for c in v.mean(0)], size=[round(float(s), 3) for s in v.max(0) - v.min(0)])
        A.save_obj(os.path.join(A.WORK, f"b6_{name}.obj"), v, f)
        print(f"{name:15s} 面 {len(f):6d} 開いた辺 {oe} 3 面以上 {nm} 体積 {A.signed_volume(v, f):+.2e} 上の面まで {gap * A.W_MM:+.1f} mm 口側から {v[:, 1].min() * A.W_MM:.1f} mm")
    with open(os.path.join(A.OUT, "b6_organs.json"), "w", encoding="utf-8") as fp:
        json.dump(dict(date="2026-10-24", parts=report, placement=info), fp, ensure_ascii=False, indent=1, default=float)


if __name__ == "__main__":
    main()

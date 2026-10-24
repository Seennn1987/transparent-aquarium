"""
メンダコ: 体を「縁から立ち上がる傘」と「前後に丸い頭（楕円体の帽子）」の和で表し、決めた正面の線（A1）と
眼の開口の高さ 0.33（決定 C）に当てはまる大きさを求める（2026-10-24）。

  .venv/bin/python -I blender/mendako/b0_fit_head_skirt.py

出力: docs/mendako/b0_head_skirt.json（大きさ）と、正面の輪郭の当てはまりの数
高さ H(x, z) = smoothmax( 傘(ρ), 頭(x, z) )。ρ は上から見た輪郭（膜の縁の波）に対する割合（a2_parts.Body.rho、頂のずらし 0）。
  傘(ρ)  = rim + (Hs − rim) · (1 − ρ)^p
  頭(x,z) = ytop · (1 − q^n)^m（m ≥ 1 で縁が寝て傘へつながる。第 4 版の (1 − q^n)^(1/n) は縁が垂直で段になった）、q = √((x/a)² + ((z − zh)/c)²)（q ≥ 1 で 0）
正面の輪郭 = 各 x で z について H の最大。決めた正面の線 v(u)（u = x ÷ 0.5）と比べる。
"""

import json
import os
import sys

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a2_parts as A  # noqa: E402

RIM = 0.045       # 縁の厚み（W）。Sunshine1 で縁は厚く丸まる
K = 0.06          # smoothmax のなめらかさ（W）。第 3 版の 0.025 は傘と頭の境に帽子のつばのような折れ線が出た
# 当てはめの範囲（2026-10-24）。第 5 版は指数 n を自由にして 5.8（箱形の鍋）、n = 2・m = 1 に固定すると傘が消えて頭が前後に短い畝になった。
# 形として無理のない範囲を先に決める: 傘の頂 0.15〜0.30、頭の横の半分 ≤ 0.32・前後の半分 ≥ 0.2、頭の頂は眼より後ろ、n 1.8〜2.6、m 0.7〜1.3
BOUNDS = dict(Hs=(0.15, 0.30), p=(1.0, 3.0), a=(0.22, 0.32), c=(0.20, 0.36), ytop=(0.36, 0.45), n=(1.8, 2.6), m=(0.7, 1.3))
HS_MAX = 0.30      # 傘の円錐の頂は頭より低く抑える（頂が頭を突き抜けて尖らないように。2026-10-24 第 2 版の絵で見つけた）
EYE_TARGET = 0.31  # 眼の盛り上がりを除いた面の高さ。盛り上がり（約 0.02〜0.03）を足して開口 0.33〜0.34


def smax(a, b, k=K):
    return k * np.logaddexp(a / k, b / k)


class HeadSkirt:
    def __init__(self, p):
        self.Hs, self.pw, self.a, self.c, self.zh, self.ytop, self.n, self.m = p
        self.body = A.Body(peak=0.0)

    def skirt(self, x, z):
        rho, rl = self.body.rho(x, z)
        r = np.clip(rho, 0, 1)      # 縁の波は縁の近くだけ（第 3 版は rl を使い、腕のあいだが平らなテントの面になった）
        return np.where(rl <= 1, RIM + (self.Hs - RIM) * (1 - r) ** self.pw, 0.0)

    def head(self, x, z):
        q = np.sqrt((x / self.a) ** 2 + ((z - self.zh) / self.c) ** 2)
        return np.where(q < 1, self.ytop * np.clip(1 - q ** self.n, 0, 1) ** self.m, 0.0)

    def h(self, x, z):
        s, hd = self.skirt(x, z), self.head(x, z)
        _, rl = self.body.rho(x, z)
        return np.where(rl <= 1, smax(s, hd), 0.0)


def front_silhouette(m, xs, zs):
    X, Z = np.meshgrid(xs, zs, indexing="ij")
    return m.h(X.ravel(), Z.ravel()).reshape(X.shape).max(1)


def main():
    L = json.load(open(os.path.join(A.OUT, "a1_outline_lines.json"), encoding="utf-8"))
    u = np.array(L["front"]["u"])
    v = np.array(L["front"]["v"])
    xs = np.linspace(0, 0.5, 51)
    target = np.interp(xs / 0.5, u, v)
    zs = np.linspace(-0.6, 0.6, 121)
    b = A.Body(peak=0.0)
    ze = b.z_at(A.EYE["from_front"])

    def full(p):
        return list(p)

    def loss(p):
        names = ["Hs", "p", "a", "c", "zh", "ytop", "n", "m"]
        for nm, val in zip(names, p):
            if nm in BOUNDS and not (BOUNDS[nm][0] <= val <= BOUNDS[nm][1]):
                return 1e3
        if p[4] > ze - 0.05:
            return 1e3
        m = HeadSkirt(p)
        f = front_silhouette(m, xs, zs)
        e = float(m.h(np.array([0.155]), np.array([ze]))[0])
        return float(np.mean((f - target) ** 2)) + 4 * (e - EYE_TARGET) ** 2

    p0 = [0.26, 1.4, 0.30, 0.28, -0.08, 0.42, 2.2, 1.0]
    r = minimize(loss, p0, method="Nelder-Mead", options=dict(maxiter=4000, xatol=1e-4, fatol=1e-8))
    p = np.array(full(r.x))
    m = HeadSkirt(p)
    f = front_silhouette(m, xs, zs)
    e = float(m.h(np.array([0.155]), np.array([ze]))[0])
    names = ["Hs", "p", "a", "c", "zh", "ytop", "n", "m"]
    out = dict(date="2026-10-24", rim=RIM, k=K, bounds=BOUNDS, params=dict(zip(names, [round(float(x), 4) for x in p])),
               front_dev_max_mm=round(float(np.abs(f - target).max()) * A.W_MM, 1),
               front_dev_rms_mm=round(float(np.sqrt(np.mean((f - target) ** 2))) * A.W_MM, 1),
               eye_surface=round(e, 3), z_front=b.z_front, z_back=b.z_back,
               head_peak_from_front=round(float((b.z_front - p[4]) / (b.z_front - b.z_back)), 3))
    print(json.dumps(out, ensure_ascii=False, indent=1))
    for x, t, g in zip(xs[::5], target[::5], f[::5]):
        print(f"u {x / 0.5:.1f}  決めた線 {t:.3f}  当てはめ {g:.3f}")
    with open(os.path.join(A.OUT, "b0_head_skirt.json"), "w", encoding="utf-8") as fp:
        json.dump(out, fp, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()

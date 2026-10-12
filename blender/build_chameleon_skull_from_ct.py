"""
Digimorph の CT 由来 STL（Chamaeleo calyptratus, TNHC 62768, 上半身）から、頭骨だけを取り出して
標本モデルの頭の局所座標（a, b, lat）に置いたメッシュ（.npz）を作る。

Blender の外（普通の Python 3）で動かす。必要: numpy, scipy, scikit-image, opencv-python, Pillow, matplotlib
  python3 build_chameleon_skull_from_ct.py <Chamaeleo.stl> <06-lightbox-calyptratus-2.jpg> <出力.npz>

出力 .npz（v: 頂点 (a, b, lat)、f: 三角形）はリポジトリに入れない（Digimorph のデータから作ったもの）。
generate_chameleon_contour.py は blender/private/chameleon_skull_ct.npz があればそれを頭骨に使う。

手順:
 1. STL のうち頭の範囲（側面の多角形）だけを取る
 2. 左右対称面を探す（鏡映した点と元の点の最近傍距離が最小になる面）。CT の頭は約 9° 横を向いていた
 3. 対称面へ投影した側面の輪郭を、06（同種の透明標本の側面写真）の頭の輪郭へ重ねて、回転と位置を決める
 4. ボクセル化（0.004 L）→ 連結成分で頭骨・下顎・強膜輪・眼窩中隔だけ残す（舌骨・頸椎・破片を外す）
 5. かぶとの薄い板の CT の欠け（部分容積で抜けた穴）を、側面投影で穴埋めして補う
 6. 1 ボクセル太らせ、各断面の小さな空洞を埋めて中身の詰まった骨にし、マーチングキューブで面を作る
 7. 形は変えずに一様に縮め、吻端〜頭の後縁を 06 の 1.04 L に合わせる（体の比率は 06 で測ってあるため）。
    後頭顆を中心に縮める。CT では環椎が後頭顆にくっついて写るので、その前に切り離す
"""

import json
import math
import sys

import cv2
import numpy as np
import scipy.ndimage as nd
from matplotlib.path import Path
from PIL import Image
from scipy.optimize import minimize
from scipy.spatial import cKDTree
from skimage import measure, morphology

HEAD_POLY = [(-50, 42), (-18, 42), (-14, 10), (-12, -2), (3, -18), (3, -32), (-20, -46), (-52, -46)]  # STL の (Y, Z) [mm]
VOX = 0.004
KEEP_MIN_VOXELS = 3000
TARGET_LENGTH = 1.04    # 06 の吻端（a=1.04）〜頭の後縁（a=0）
ATLAS_CUT_A = 0.12      # 06 に重ねた座標で、これより後ろの正中の骨は環椎（断面で輪になっている）


def load_stl(path):
    d = open(path, "rb").read()
    n = int.from_bytes(d[80:84], "little")
    a = np.frombuffer(d[84:84 + n * 50], dtype=np.dtype([("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")]))
    return a["v"].astype(np.float64)


def symmetry_plane(P):
    P = P[P[:, 1] < -8]
    rng = np.random.default_rng(0)
    P = P[rng.choice(len(P), min(40000, len(P)), replace=False)]
    T = cKDTree(P)

    def cost(q):
        th, ph, d = q
        n = np.array([math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph), math.sin(ph)])
        M = P - 2 * (P @ n - d)[:, None] * n
        dd, _ = T.query(M, distance_upper_bound=3.0)
        return float(np.mean(np.minimum(np.where(np.isinf(dd), 3.0, dd), 3.0)))
    best = min(((cost([th, ph, d]), [th, ph, d]) for th in np.radians(np.arange(-15, 16, 5))
                for ph in np.radians(np.arange(-15, 16, 5)) for d in np.arange(-9, -3.9, 1)), key=lambda t: t[0])
    r = minimize(cost, best[1], method="Nelder-Mead", options={"xatol": 1e-4, "fatol": 1e-5, "maxiter": 400})
    th, ph, d = r.x
    return np.array([math.cos(th) * math.cos(ph), math.sin(th) * math.cos(ph), math.sin(ph)]), d, r.fun


def mask_06(path):
    im = np.asarray(Image.open(path).convert("RGB")).astype(int)
    c = im[1250:2300, 3900:4700]
    bone = (c[..., 1] < 150) & ((c[..., 0] - c[..., 1]) > 40)
    bone = nd.binary_closing(bone, iterations=3)
    lab, n = nd.label(bone)
    m = lab == (np.argmax(nd.sum(bone, lab, range(1, n + 1))) + 1)
    m[:, :65] = False
    return nd.binary_fill_holes(nd.binary_closing(m, iterations=6))


def main():
    stl, photo, out = sys.argv[1:4]
    T = load_stl(stl)
    keep = Path(HEAD_POLY).contains_points(T.mean(1)[:, 1:3])
    T = T[keep]
    V = T.reshape(-1, 3)
    n, d, res = symmetry_plane(V)
    print(f"対称面 n={n.round(3)} d={d:.2f} 残差 {res:.2f} mm")
    e1 = np.array([0, 1, 0.]) - n * n[1]
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(n, e1)
    if e2[2] < 0:
        e2 = -e2
    U, W = V @ e1, V @ e2
    # 側面の輪郭を 06 に重ねる
    S = 12.0
    u0, u1, w0, w1 = U.min() - 2, U.max() + 2, W.min() - 2, W.max() + 2
    img = np.zeros((int((w1 - w0) * S), int((u1 - u0) * S)), bool)
    img[((w1 - W) * S).astype(int), ((U - u0) * S).astype(int)] = True
    C = nd.binary_fill_holes(nd.binary_closing(nd.binary_dilation(img, iterations=2), iterations=5))
    A = mask_06(photo)

    def M(p):
        s, th, tx, ty = p
        c, sn = math.cos(th), math.sin(th)
        return np.array([[-s * c / S, s * sn / S, tx + s * c * (-u0) - s * sn * w1 - 3900],
                         [s * sn / S, s * c / S, ty - s * sn * (-u0) - s * c * w1 - 1250]])

    def iou(p):
        Wp = cv2.warpAffine(C.astype(np.uint8), M(p), (A.shape[1], A.shape[0]), flags=cv2.INTER_NEAREST) > 0
        return (Wp & A).sum() / max(1, (Wp | A).sum())
    k = np.argmin(U)
    su, sw = U[k], W[k]

    def place(s, th):
        c, sn = math.cos(th), math.sin(th)
        return 4600 - s * (c * (-su) - sn * sw), 2150 + s * (sn * (-su) + c * sw)
    best = max(((iou((s, th) + place(s, th)), (s, th) + place(s, th)) for s in np.linspace(11, 16, 11)
                for th in np.radians(np.arange(0, 70, 2.5))), key=lambda t: t[0])
    r = minimize(lambda p: -iou(p), best[1], method="Nelder-Mead", options={"xatol": 0.01, "fatol": 1e-6, "maxiter": 1500})
    s, th, tx, ty = r.x
    print(f"06 への重ね合わせ IoU {-r.fun:.3f}、回転 {math.degrees(th):.1f}°")
    c, sn = math.cos(th), math.sin(th)

    def toab(P):
        U, W, L = P @ e1, P @ e2, P @ n - d
        x = tx + s * (c * (-U) - sn * W)
        y = ty - s * (sn * (-U) + c * W)
        return np.stack([(x - 3975) / 601, (2160 - y) / 601, L * s / 601], -1)
    Tab = toab(T.reshape(-1, 3)).reshape(-1, 3, 3)
    # ボクセル化
    lo = Tab.reshape(-1, 3).min(0) - 0.03
    hi = Tab.reshape(-1, 3).max(0) + 0.03
    G = np.zeros(np.ceil((hi - lo) / VOX).astype(int), bool)
    for k0 in range(0, len(Tab), 20000):
        t = Tab[k0:k0 + 20000]
        e = np.maximum(np.linalg.norm(t[:, 1] - t[:, 0], axis=1), np.linalg.norm(t[:, 2] - t[:, 0], axis=1))
        m = int(np.ceil(e.max() / VOX * 1.5)) + 1
        for i in range(m + 1):
            for j in range(m + 1 - i):
                p = t[:, 0] * (1 - i / m - j / m) + t[:, 1] * (i / m) + t[:, 2] * (j / m)
                q = ((p - lo) / VOX).astype(int)
                G[q[:, 0], q[:, 1], q[:, 2]] = True
    Sx = nd.binary_fill_holes(nd.binary_closing(nd.binary_dilation(G, iterations=1), iterations=1))
    lab, nlab = nd.label(Sx)
    sizes = nd.sum(Sx, lab, range(1, nlab + 1))
    objs = nd.find_objects(lab)
    keep_ids = []
    for kk in np.argsort(-sizes):
        if sizes[kk] < KEEP_MIN_VOXELS:
            break
        sl = objs[kk]
        b0 = lo[1] + sl[1].start * VOX
        b1 = lo[1] + sl[1].stop * VOX
        if b0 < -0.2:           # 舌骨（喉へ下がる長い骨）は外す（手順 5 で軟骨と一緒に作る）
            continue
        if (sl[0].stop - sl[0].start) * VOX < 0.2 and b1 < 0.2:   # 頭の後ろの頸椎のかけら
            continue
        keep_ids.append(kk + 1)
    Mk = np.isin(lab, keep_ids)
    print("残した部品", len(keep_ids))
    # 環椎（第 1 頸椎）が後頭顆にくっついて写っているので切り離す（a<0.12、正中、かぶとより下）
    agrid = lo[0] + np.arange(Mk.shape[0]) * VOX
    bgrid = lo[1] + np.arange(Mk.shape[1]) * VOX
    lgrid0 = lo[2] + np.arange(Mk.shape[2]) * VOX
    cut = (agrid[:, None, None] < ATLAS_CUT_A) & (np.abs(lgrid0)[None, None, :] < 0.10) & \
          (bgrid[None, :, None] > 0.30) & (bgrid[None, :, None] < 0.65)
    Mk &= ~cut
    # かぶとの穴埋め
    na, nb, nl = Mk.shape
    lgrid = lo[2] + np.arange(nl) * VOX
    jb = int((0.62 - lo[1]) / VOX)
    add = np.zeros_like(Mk)
    for side in (-1, 1):
        sel = side * lgrid > -0.015
        sub = Mk[:, jb:, :][:, :, sel]
        O = sub.any(2)
        Of = morphology.remove_small_holes(morphology.binary_closing(O, morphology.disk(9)), max_size=1500)
        lmin = np.argmax(sub, 2)
        lmax = sub.shape[2] - 1 - np.argmax(sub[:, :, ::-1], 2)
        idx = nd.distance_transform_edt(~O, return_distances=False, return_indices=True)
        cols_all = np.nonzero(sel)[0]
        for i, j in zip(*np.nonzero(Of & ~O)):
            ii, jj = idx[0][i, j], idx[1][i, j]
            add[i, jb + j, cols_all[lmin[ii, jj]:lmax[ii, jj] + 1]] = True
    Mk = nd.binary_closing(Mk | add, iterations=1)
    # 中身の詰まった骨に
    Mk = nd.binary_dilation(Mk, iterations=1)
    F = Mk.copy()
    for ax in range(3):
        Mv, Fv = np.moveaxis(Mk, ax, 0), np.moveaxis(F, ax, 0)
        for i in range(Mv.shape[0]):
            Fv[i] |= morphology.remove_small_holes(Mv[i], max_size=80)
    lab, nlab = nd.label(F)
    sizes = nd.sum(F, lab, range(1, nlab + 1))
    F = np.isin(lab, np.nonzero(sizes > 800)[0] + 1)
    v, f, _, _ = measure.marching_cubes(nd.gaussian_filter(F.astype(np.float32), 1.0), 0.5)
    v = lo + v * VOX
    # 一様に縮める（後頭顆を中心に）
    a, b, lat = v.T
    # 後頭顆: 環椎を切った面のすぐ前、正中、かぶとの下（断面で詰まった丸として見える）
    band = (np.abs(lat) < 0.08) & (a > ATLAS_CUT_A) & (a < ATLAS_CUT_A + 0.04) & (b > 0.40) & (b < 0.65)
    condyle = np.array([a[band].min(), np.median(b[band]), 0.0])
    back = a.min()          # 頭の後縁（かぶとの後ろの縁を含む）
    k = TARGET_LENGTH / (a.max() - back)
    v = condyle + (v - condyle) * k
    print(f"縮め率 {k:.3f}、後頭顆 a={condyle[0]:.3f} b={condyle[1]:.3f}、頭の高さ {(v[:,1].max()-v[:,1].min()):.2f} L")
    np.savez_compressed(out, v=v.astype(np.float32), f=f.astype(np.int32), condyle=condyle.astype(np.float32),
                        scale=np.float32(k))
    print("書き出し", out, len(f), "面（間引きは Blender 側）")


if __name__ == "__main__":
    main()

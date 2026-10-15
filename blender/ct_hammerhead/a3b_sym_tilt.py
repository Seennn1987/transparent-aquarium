"""A3: 体の倒れを、断面の外形の左右対称で測り直す（神経弓の値 tilt.npy の ±35° の範囲で探す）。
使い方: python3 a3b_sym_tilt.py <作業フォルダ>   出力: sym_tilt.npy（mm, 角度, 重なり, 神経弓の値）, tilt_sym.npy, derolled2.npy, derolled_mips.npy
断面を、背骨を通る軸で鏡に映し、元の断面と最もよく重なる軸を背腹の軸とする。楕円は 2 本の軸で対称になるので、神経弓の値に近い方だけを探す。"""
import hh_paths
import sys, numpy as np
from scipy.ndimage import map_coordinates, gaussian_filter1d
w = (sys.argv[1] if len(sys.argv) > 1 else hh_paths.WORK).rstrip('/') + '/'
C = np.load(w + 'zyg_clean.npy', mmap_mode='r'); cxs, cys = np.load(w + 'spine_line.npy'); t0 = np.load(w + 'tilt.npy')
R = 70; u, v = np.meshgrid(np.arange(-R, R + 1), np.arange(-R, R + 1)); res = []
for mm in range(100, 1000, 10):
    z = min(int(mm * 2), 2020); m = (np.asarray(C[z]) > -400).astype(np.float32); best = None
    for th in np.arange(t0[z] - 35, t0[z] + 36, 2):
        t = np.radians(th); x = u * np.cos(t) - v * np.sin(t) + cxs[z]; y = u * np.sin(t) + v * np.cos(t) + cys[z]
        a = map_coordinates(m, [y, x], order=0, cval=0); b = a[:, ::-1]
        sc = (a * b).sum() / max(np.maximum(a, b).sum(), 1)
        if best is None or sc > best[1]: best = (th, sc)
    res.append((mm, best[0], best[1], t0[z]))
res = np.array(res); np.save(w + 'sym_tilt.npy', res)
mm = np.arange(C.shape[0]) * 0.5
tilt = gaussian_filter1d(np.interp(mm, np.r_[0, res[:, 0]], np.r_[0, res[:, 1]]), 16); np.save(w + 'tilt_sym.npy', tilt)
Z = C.shape[0] // 2; N = 300; c = N / 2; uu, vv = np.meshgrid(np.arange(N) - c, np.arange(N) - c)
out = np.full((Z, N, N), -1000, np.int16)
for i in range(Z):
    zz = 2 * i; s = np.asarray(C[zz:zz + 2]).astype(np.float32).max(0)
    s = s[:s.shape[0] // 2 * 2, :s.shape[1] // 2 * 2].reshape(s.shape[0] // 2, 2, s.shape[1] // 2, 2).max((1, 3))
    t = np.radians(tilt[zz]); x = uu * np.cos(t) - vv * np.sin(t) + cxs[zz] / 2; y = uu * np.sin(t) + vv * np.cos(t) + cys[zz] / 2
    out[i] = map_coordinates(s, [y, x], order=1, cval=-1000).astype(np.int16)
np.save(w + 'derolled2.npy', out); np.save(w + 'derolled_mips.npy', np.stack([out.max(1), out.max(2)]))

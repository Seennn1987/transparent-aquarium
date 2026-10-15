"""A3 の試し: 測った倒れ（a2c_roll.py）で断面ごとに回し、背骨の中心を一直線にそろえた体積を作る（2 倍に縮めた解像度）。
使い方: python3 a3_unroll_preview.py <作業フォルダ>   出力: tilt.npy（断面ごとの倒れ、度）, derolled2.npy, derolled_mips.npy
倒れ: 吻端 0〜100 mm は 0°（頭の翼が水平）。それより後ろは 20 mm ごとの測定を補間し、約 20 mm でならす。
注意: 背骨の中心線そのものを一直線にしているので、尾びれの上葉へ上がる背骨の自然な曲がりも消えている（試しの図のため）。"""
import hh_paths
import sys, numpy as np
from scipy.ndimage import gaussian_filter1d, map_coordinates
w = (sys.argv[1] if len(sys.argv) > 1 else hh_paths.WORK).rstrip('/') + '/'
o = np.load(w + 'arch_angle.npy'); z, a = o[:, 0], o[:, 1]
cent, vals, prev = [], [], None
for z0 in range(140, 1000, 20):
    sel = (z >= z0 * 2) & (z < z0 * 2 + 80) & ~np.isnan(a); v = np.radians(a[sel])
    if len(v) < 3: continue
    c2 = np.exp(2j * v).mean(); ax = np.degrees(np.angle(c2) / 2)
    cand = [ax, ax + 180 if ax < 0 else ax - 180]
    d = cand[0] if prev is None else min(cand, key=lambda q: abs(((q - prev + 180) % 360) - 180))
    if prev is None and d > 0: d = cand[1]
    prev = d; cent.append(z0 + 20); vals.append(d + 90)
C = np.load(w + 'zyg_clean.npy', mmap_mode='r'); cxs, cys = np.load(w + 'spine_line.npy')
mm = np.arange(C.shape[0]) * 0.5
tilt = gaussian_filter1d(np.interp(mm, np.r_[0, 100, cent], np.r_[0, 0, vals]), 40); np.save(w + 'tilt.npy', tilt)
Z = C.shape[0] // 2; N = 300; c = N / 2
u, v = np.meshgrid(np.arange(N) - c, np.arange(N) - c)
out = np.full((Z, N, N), -1000, np.int16)
for i in range(Z):
    zz = 2 * i; s = np.asarray(C[zz:zz + 2]).astype(np.float32).max(0)
    s = s[:s.shape[0] // 2 * 2, :s.shape[1] // 2 * 2].reshape(s.shape[0] // 2, 2, s.shape[1] // 2, 2).max((1, 3))
    t = np.radians(tilt[zz])
    x = u * np.cos(t) - v * np.sin(t) + cxs[zz] / 2; y = u * np.sin(t) + v * np.cos(t) + cys[zz] / 2
    out[i] = map_coordinates(s, [y, x], order=1, cval=-1000).astype(np.int16)
np.save(w + 'derolled2.npy', out); np.save(w + 'derolled_mips.npy', np.stack([out.max(1), out.max(2)]))

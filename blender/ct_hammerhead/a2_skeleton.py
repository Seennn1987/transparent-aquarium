"""A2（途中）: 骨格（濃さ 250 以上）の塊分けと、背骨の中心線・椎骨の境目。
使い方: python3 a2_skeleton.py <作業フォルダ>
出力: skel_lab.npy / skel_sizes.npy（26 近傍の塊）, axial_profile.npy, spine_line.npy, spine_core.npy, vert_bounds.npy
椎骨の境目 = 中心線の上の濃さの極小（椎体のあいだの、脊索の菱形の暗い所）"""
import hh_paths
import sys, numpy as np
from scipy import ndimage as nd
from scipy.ndimage import gaussian_filter1d, map_coordinates
from scipy.signal import find_peaks
w = (sys.argv[1] if len(sys.argv) > 1 else hh_paths.WORK).rstrip('/') + '/'
C = np.load(w + 'zyg_clean.npy')
S = C > 250; lab, n = nd.label(S, structure=np.ones((3, 3, 3))); sz = nd.sum(S, lab, range(1, n + 1))
np.save(w + 'skel_lab.npy', lab.astype(np.int32)); np.save(w + 'skel_sizes.npy', sz)
axial = int(np.argmax(sz)) + 1          # 頭と背骨がつながった塊
Z = C.shape[0]; area = np.zeros(Z); cx = np.full(Z, np.nan); cy = np.full(Z, np.nan); wx = np.zeros(Z)
for z in range(Z):
    m = lab[z] == axial
    if m.any():
        yy, xx = np.where(m); area[z] = m.sum(); cx[z] = xx.mean(); cy[z] = yy.mean(); wx[z] = np.ptp(xx)
np.save(w + 'axial_profile.npy', np.stack([area, cx, cy, wx]))
zz = np.arange(Z); good = (zz >= 280) & (wx > 0) & (wx < 40)   # 頭の後ろ（断面 280 以降）は椎体だけ
cxs = gaussian_filter1d(np.interp(zz, zz[good], cx[good]), 15); cys = gaussian_filter1d(np.interp(zz, zz[good], cy[good]), 15)
for a in (cxs, cys):
    k = np.polyfit(zz[280:330], a[280:330], 1); a[:280] = np.polyval(k, zz[:280])
np.save(w + 'spine_line.npy', np.stack([cxs, cys]))
end = int(np.where(area > 0)[0].max()); core = np.full(Z, np.nan)
for z in range(190, end):
    s = C[z].astype(np.float32); y, x = cys[z], cxs[z]
    ys, xs = np.mgrid[int(y) - 10:int(y) + 11, int(x) - 10:int(x) + 11]
    ys = np.clip(ys, 0, s.shape[0] - 1); xs = np.clip(xs, 0, s.shape[1] - 1)
    wgt = np.clip(s[ys, xs] - 200, 0, None)
    if wgt.sum() > 0: y, x = (wgt * ys).sum() / wgt.sum(), (wgt * xs).sum() / wgt.sum()
    core[z] = map_coordinates(s, [[y - 1, y, y + 1, y, y], [x, x, x, x - 1, x + 1]], order=1).mean()
np.save(w + 'spine_core.npy', core)
cg = gaussian_filter1d(np.nan_to_num(core[190:end]), 0.8)
mins, _ = find_peaks(-cg, distance=4, prominence=60); np.save(w + 'vert_bounds.npy', mins + 190)
print('塊', n, '最大', int(sz.max()), '椎骨の境目', len(mins))

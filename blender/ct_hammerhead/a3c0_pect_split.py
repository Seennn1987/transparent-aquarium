# A3 胸びれを左右に分ける（計画書 第 9 節「胸びれを左右に分ける（2026-10-14）」）
#  肩帯と左右の胸びれの塊（833）を、起こした後の座標（a3b_sym_tilt.py の tilt_sym と背骨の線）に移す → c833_uvz.npy（z, u, v mm）
#  分け方 → c833_split.npy: z 232 mm より後ろで v が 62 mm より腹側 = 垂れたひれ（赤 1）、z 232 mm より後ろで 62 mm より背側 =
#   押し付けられたひれ（青 2）、v が 95 mm より腹側も赤、残り = 肩帯（0）。境目は目で決めた仮の値（計画書のとおり）
#  付け根（肩帯にいちばん近い 3% の点の平均）と長い軸（主成分）、長さ（付け根から長い軸に沿った距離の 99%）→ pect_info.json
#   計画書の値（赤 付け根 (−10.7, 232, 78.7)・長さ 66 mm、青 (13.7, 233, 40.3)・84 mm）と同じになる
#  2026-10-15 書き起こし: 前の担当の作業フォルダにあった処理が残っていなかったため、計画書の文章から書き起こした。
#  前の work/ の c833_uvz.npy・c833_split.npy と完全に一致することを確かめた（差 3e-14 mm、分け方の違い 0 点）
import hh_paths; hh_paths.cd_work()
import numpy as np, json
from scipy.spatial import cKDTree
L = np.load('skel_lab.npy', mmap_mode='r'); cxs, cys = np.load('spine_line.npy'); t = np.load('tilt_sym.npy')
info = json.load(open('comps_info.json')); z0, z1 = info['833']['z']
zz, yy, xx = np.nonzero(np.asarray(L[z0:z1 + 1]) == 833); z = zz + z0
c = np.cos(np.radians(t[z])); s = np.sin(np.radians(t[z])); dx = xx - cxs[z]; dy = yy - cys[z]
zm = z * 0.5; u = (c * dx + s * dy) * 0.735; v = (-s * dx + c * dy) * 0.735
np.save('c833_uvz.npy', np.stack([zm, u, v]))
lab = np.zeros(len(zm), np.int8); back = zm >= 232
lab[back & (v > 62)] = 1; lab[back & (v <= 62)] = 2; lab[v > 95] = 1
np.save('c833_split.npy', lab)
P = np.stack([u, zm, v], 1); G = P[lab == 0]; out = {}
for name, k in (('red', 1), ('blue', 2)):
    F = P[lab == k]; d = cKDTree(G).query(F)[0]; base = F[d <= np.percentile(d, 3)].mean(0)
    cc = F.mean(0); w, V = np.linalg.eigh(np.cov((F - cc).T)); e1 = V[:, 2]
    if np.dot(cc - base, e1) < 0: e1 = -e1
    out[name] = {'base': base.round(1).tolist(), 'dir': e1.round(2).tolist(), 'len_mm': round(float(np.percentile(np.abs((F - base) @ e1), 99)), 1), 'n': int(len(F))}
json.dump(out, open('pect_info.json', 'w'), ensure_ascii=False, indent=1); print(out)

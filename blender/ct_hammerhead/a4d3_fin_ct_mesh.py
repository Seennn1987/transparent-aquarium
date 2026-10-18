# A4（2026-10-18 足す）: 正中のひれの軟骨を、元の CT の細かさのまま面にしてから、面の頂点を A4 の立て直し（a4d2_median_fins.py）と同じ式で動かす。
#  プロデューサー「第１背鰭、胸鰭、尾鰭の３つの軟骨部分はこのままでOKですが、それ以外のヒレの軟骨表現が変です」→（箱の棒の案に）「そんな直線的で太さも感覚も均一な棒みたいなのを置くのでいいわけないじゃん。」
#  →「その方法で、まず臀びれだけ CT から作り直して、写真と前の版と並べて見せてください」。
#  前のやり方（a4d2 で点を最終の格子 0.735 mm に置き直し、閉じてぼかしてから a4e_mesh.py で面）では、細い棒（約 0.7 mm）が途切れて粒になった。
#  ここでは: 骨の閾値 250 の代わりに HH_FINCT_TH（既定 175。臀びれの切り抜きを閾値 250・200・175・150 で比べ、175 で棒が切れずに離れて並んだ）、
#  元の CT（0.5 × 0.735 × 0.735 mm）を σ 0.5 画素だけぼかして、その値の等値面を作る。残すのは、A2 の骨の塊（臀びれ 4302）を 3 画素広げた所に触れる塊だけ
#  使い方: python3 a4d3_fin_ct_mesh.py anal   → mesh/HH_anal.ply を書き直す（a4e_mesh.py fins の後）
import hh_paths; hh_paths.cd_work()
import numpy as np, json, sys, os
from scipy import ndimage as nd
from skimage.measure import marching_cubes
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
VX = 0.735
FINS = {'anal': 4302, 'dfin2': 4513}
name = sys.argv[1]; labno = FINS[name]
TH = float(os.environ.get('HH_FINCT_TH', 175))
C = np.load('zyg_clean.npy', mmap_mode='r'); L = np.load('skel_lab.npy', mmap_mode='r'); info = json.load(open('comps_info.json'))
cxs, cys = np.load('spine_line.npy'); t = np.load('tilt_sym.npy')
c = info[str(labno)]; z0, z1 = c['z'][0] - 20, c['z'][1] + 21; y0, y1 = max(0, c['y'][0] - 12), min(C.shape[1], c['y'][1] + 12); x0, x1 = max(0, c['x'][0] - 20), min(C.shape[2], c['x'][1] + 20)
sub = nd.gaussian_filter(np.asarray(C[z0:z1, y0:y1, x0:x1]).astype(np.float32), 0.5); lab = np.asarray(L[z0:z1, y0:y1, x0:x1]) == labno
m = sub >= TH; cl, n = nd.label(m, np.ones((3, 3, 3))); keep = np.unique(cl[nd.binary_dilation(lab, iterations=3) & m]); keep = keep[keep > 0]
M = nd.binary_dilation(np.isin(cl, keep), iterations=1)
F = np.where(M, sub, TH - 200.0)                           # 残す塊のまわりだけの値（ほかは閾値より低く）
v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=TH - 200), TH, allow_degenerate=False); v = v - 1
zi, yi, xi = v[:, 0] + z0, v[:, 1] + y0, v[:, 2] + x0   # 元の CT の画素（小数）
# a4d2_median_fins.py と同じ: 背骨の線と傾きで (u, v) へ、付け根の中央へ寄せて傾きを戻し、高さの帯ごとの左右の中央をそろえる
zr = np.arange(len(t)); tt = np.interp(zi, zr, t); cx = np.interp(zi, zr, cxs); cy = np.interp(zi, zr, cys)
cc, ss = np.cos(np.radians(tt)), np.sin(np.radians(tt)); dx = xi - cx; dy = yi - cy
u = (cc * dx + ss * dy) * VX; vv = (-ss * dx + cc * dy) * VX; zm = zi * 0.5
X = np.load(f'a4_{name}_xform.npz'); ub, vb, ang = float(X['ub']), float(X['vb']), float(X['ang'])
du, dv = u - ub, vv - vb; ca, sa = np.cos(ang), np.sin(ang)
u2 = du * ca - dv * sa; v2 = du * sa + dv * ca + vb
u2 = u2 - np.interp(np.round(v2 / 2), X['band_keys'], X['band_med']) * np.clip(np.abs(v2 - vb) / 10, 0, 1)
V = np.stack([zm, u2, -v2], 1) / 1000.0                   # Blender（x = 体軸、y = 左右、z = 背）
vol = np.einsum('ij,ij->i', V[f[:, 0]], np.cross(V[f[:, 1]], V[f[:, 2]])).sum() / 6
if vol > 0: f = f[:, ::-1]                                 # write_ply は面を裏返して書くので、ここでは内向きにそろえておく
write_ply(f'{OUT}/HH_{name}.ply', V, f)
rep = {'name': name, 'label': labno, 'threshold': TH, 'components': int(len(keep)), 'voxels': int(np.isin(cl, keep).sum()), 'volume_ml': round(abs(vol) * 1e6, 3), 'faces': int(len(f))}
json.dump(rep, open(f'a4_{name}_ctmesh.json', 'w'), ensure_ascii=False); print(rep)

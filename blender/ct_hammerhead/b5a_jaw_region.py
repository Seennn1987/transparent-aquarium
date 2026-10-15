# B5 口の動き（2026-10-15、プロデューサー「口も僅かに動かすことを計画に含めて下さい」）: 下あごといっしょに動く体の膜の範囲を、
#  a7c_open_mesh.py と同じ決め方（細かい格子を 2 倍に間引き、いちばん近い骨が下あご・下の歯である所、関節より 6 mm 前まで）で書き出す。
#  b1_rig.py（Blender の Python、scipy が無い）がこの格子を引いて、膜の頂点を下あごの骨に付ける
#  入力: a7_jaw_fine.npz、a7_jawlab.npy、a7_open.json　出力: b5_jaw_region.npz（L0 は開く前の座標の格子）
import hh_paths; hh_paths.cd_work()
import numpy as np, json
from scipy import ndimage as nd
d = np.load('a7_jaw_fine.npz'); o = d['origin']; G = float(d['step']); W = np.load('a7_jawlab.npy')
J = json.load(open('a7_open.json'))
Wd = W[::2, ::2, ::2]; low = (Wd == 3) | (Wd == 6); rest = (Wd == 1) | (Wd == 2) | (Wd == 4) | (Wd == 5)
dl = nd.distance_transform_edt(~low); dr = nd.distance_transform_edt(~rest)
L0 = dl < dr
# 境目からの距離（mm、下あご側が +）: b1_rig.py が、境目の両側 HH_RIG_JAWBAND mm でなめらかに重みを移す（0/1 で切ると、3° 回しただけで膜が 4.5 倍伸びた）
SD = ((dr - dl) * G * 2 / 2).astype(np.float16)      # 2 つの距離の差の半分 ≈ 境目からの距離
np.savez_compressed('b5_jaw_region.npz', L0=np.packbits(L0, axis=None), SD=SD, shape=np.array(L0.shape), origin=o, step=G * 2,
                    joint_L=np.array(J['joint_L_zuv_mm']), joint_R=np.array(J['joint_R_zuv_mm']), angle=J['angle_deg'], sign=J['sign'])
print('L0', L0.shape, int(L0.sum()), 'origin (z,v,u)', o, 'step', G * 2)

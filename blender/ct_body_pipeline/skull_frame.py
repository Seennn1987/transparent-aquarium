# 頭骨の枠（CT の mm の向き）: 前（吻へ）・背・横。展示の姿勢の頭の行列から、モデルの 吻 = −z、背 = −x を CT へ戻す
#   出力: skull_frame_ct.npy（3×3、行 = 前・背・横）。hyoid_rebuild.py の角舌骨の向き（仮）に使う
import numpy as np
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; M = P['M'][bn.index('head')][:3, :3]
def m2ct(m): return np.array([-m[2], m[0], -m[1]])
fwd = m2ct(M.T @ np.array([0, 0, -1.0])); up = m2ct(M.T @ np.array([-1.0, 0, 0]))
fwd /= np.linalg.norm(fwd); up -= fwd * (up @ fwd); up /= np.linalg.norm(up); lat = np.cross(fwd, up)
np.save('skull_frame_ct.npy', np.array([fwd, up, lat])); print('skull frame', np.round([fwd, up, lat], 3))

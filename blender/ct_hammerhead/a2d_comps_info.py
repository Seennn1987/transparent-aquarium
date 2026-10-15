# A2 の続き: 骨の塊ごとの大きさと、元の CT の断面の範囲の表（comps_info.json）。a3o_*・a4d2_median_fins.py が読む
#  z = 塊が写っている最初と最後の断面の番号（zyg_clean の 0.5 mm の断面。最後の断面も含む）
#  2026-10-15 書き起こし: 前の担当の作業フォルダにあった comps_info.json を作る処理が残っていなかったため。
#  確かめ方: a4d2_median_fins.py の出力（a4_dfin1.npz など）が、前の work/ のものと一致すること
import hh_paths; hh_paths.cd_work()
import numpy as np, json
from scipy import ndimage as nd
L = np.load('skel_lab.npy', mmap_mode='r'); sz = np.load('skel_sizes.npy')
info = {}
for i, sl in enumerate(nd.find_objects(np.asarray(L)), start=1):
    if sl is None: continue
    info[str(i)] = {'n': int(sz[i - 1]), 'z': [int(sl[0].start), int(sl[0].stop - 1)], 'y': [int(sl[1].start), int(sl[1].stop - 1)],
                    'x': [int(sl[2].start), int(sl[2].stop - 1)]}
json.dump(info, open('comps_info.json', 'w'))
print('塊', len(info))

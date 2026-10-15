# A7 エラの空気（エラ穴の帯）: a7h_gill_arches.py がエラの骨を置く場所を決めるのに使う
#  a7_slit.npy: エラのまわりの格子（a7_gill_field.npz、0.5 mm）で、体の中の空気。断面ごとに、-300 HU より濃い所を
#    十字の形で 4 回閉じて（エラ穴の口をふさぐ）穴を埋めたものを体とし、その中で -300 HU 未満の所
#  a7_uin.npy: (uin, uout)。前後 z・背腹 v ごとに、左（u < -12 mm）のエラの空気のいちばん内（正中に近い）と外の端（mm）。無い所は nan
#  2026-10-15 書き起こし: 前の担当の作業フォルダにあった処理が残っていなかったため、前の work/ の a7_slit.npy・a7_uin.npy と
#  完全に一致する作り方を探して書いた（違うボクセル 0、違う値 0）
import hh_paths; hh_paths.cd_work()
import numpy as np
from scipy import ndimage as nd
d = np.load('a7_gill_field.npz'); F = d['field']; o = d['origin']; G = float(d['step'])
cross = nd.generate_binary_structure(2, 1)
body = np.stack([nd.binary_fill_holes(nd.binary_closing(F[k] > -300, structure=cross, iterations=4)) for k in range(F.shape[0])])
slit = (F < -300) & body
np.save('a7_slit.npy', slit)
us = o[2] + np.arange(F.shape[2]) * G
U = np.where(slit & (us < -12), us, np.nan)
with np.errstate(all='ignore'):
    uin = np.nanmax(U, 2); uout = np.nanmin(U, 2)
np.save('a7_uin.npy', np.stack([uin, uout]))
print('slit', int(slit.sum()), 'rows with left air', int(np.isfinite(uin).sum()))

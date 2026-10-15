"""A2 の続き: 最大の塊（頭と背骨）を、背骨の中心線から 13 ボクセル以内（断面 195 以降）= 背骨、残り = 頭 に分ける。
使い方: python3 a2b_split_head_spine.py <作業フォルダ>   出力: m_head.npy, m_spine.npy（np.packbits）"""
import hh_paths
import sys, numpy as np
w = (sys.argv[1] if len(sys.argv) > 1 else hh_paths.WORK).rstrip('/') + '/'
lab = np.load(w + 'skel_lab.npy'); sz = np.load(w + 'skel_sizes.npy'); cxs, cys = np.load(w + 'spine_line.npy')
axial = int(np.argmax(sz)) + 1
Z, Y, X = lab.shape; yy, xx = np.mgrid[0:Y, 0:X]
spine = np.zeros(lab.shape, bool)
for z in range(195, Z):
    spine[z] = (lab[z] == axial) & (np.hypot(xx - cxs[z], yy - cys[z]) < 13)
head = (lab == axial) & ~spine
np.save(w + 'm_head.npy', np.packbits(head)); np.save(w + 'm_spine.npy', np.packbits(spine))
print('頭', int(head.sum()), '背骨', int(spine.sum()))

# 舌骨（ラベル 2）に入っていた、もう 1 体の個体（intruder.npy）の指の骨を外す。
#   舌骨のかけらのうち、まわり 1 mm に自分の骨が無く、もう 1 体の骨がある塊を外す（ラベル 0）。
#   2026-10-13 に見つけた 4 本（長さ 6〜9 mm、太さ 1.7〜2.1 mm、先が鉤状に曲がる = 爪）は、もう 1 体の手足の指の中にあった
#   python3 hyoidfix.py B_h10.npy B_h11.npy
import numpy as np, scipy.ndimage as nd, sys
src, dst = sys.argv[1], sys.argv[2]
B = np.load(src); IN = np.load('intruder.npy')
lab, n = nd.label(B == 2)
out = 0
for i, s in enumerate(nd.find_objects(lab), 1):
    sl = tuple(slice(max(0, x.start - 10), x.stop + 10) for x in s)
    m = lab[sl] == i; ring = nd.binary_dilation(m, iterations=10) & ~m
    own = int(((B[sl] > 0) & (B[sl] != 2) & ring).sum()); intr = int((IN[sl] & ring).sum())
    if own == 0 and intr > 0:
        sub = B[sl]; sub[m] = 0; out += int(m.sum())
print('removed voxels', out, 'hyoid left', int((B == 2).sum()))
np.save(dst, B)

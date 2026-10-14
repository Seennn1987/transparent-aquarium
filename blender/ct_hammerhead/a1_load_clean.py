"""A1: シロシュモクザメ ZMA.PISC.108725 の DICOM を読み、撮影台を外した体の体積を作る。
使い方: python3 a1_load_clean.py <zip> <作業フォルダ>
出力: zyg.npy（全体, z,y,x, int16）, body2.npy（2 倍に縮めた体のマスク）, zyg_clean.npy（体の外を -1000、y と x を体の範囲に切った体積）, clean_meta.json
軸: z = 吻→尾（0.5 mm）, y = 背→腹（0.735 mm）, x = 左右（0.735 mm。左右の向きは未確認）"""
import sys, io, json, zipfile, numpy as np, pydicom
from scipy import ndimage as nd
src, out = sys.argv[1], sys.argv[2].rstrip('/') + '/'
z = zipfile.ZipFile(src); sl = []
for n in z.namelist():
    if n.endswith('/'): continue
    try: d = pydicom.dcmread(io.BytesIO(z.read(n)))
    except Exception: continue
    if not hasattr(d, 'ImagePositionPatient'): continue
    sl.append((float(d.ImagePositionPatient[2]), d.pixel_array.astype(np.int16) * int(d.RescaleSlope) + int(d.RescaleIntercept)))
sl.sort(key=lambda t: t[0]); V = np.stack([s[1] for s in sl]); np.save(out + 'zyg.npy', V); del sl
Z = V.shape[0]
# 体の行は 208〜286 付近、撮影台のシートは 286 付近、台は 414 以下。行 300 より上だけを見る
d = np.empty((Z // 2, 150, 256), np.int16)
for i in range(Z // 2):
    a = V[2 * i:2 * i + 2, :300, :].astype(np.float32).mean(0)
    d[i] = a.reshape(150, 2, 256, 2).mean((1, 3))
m = nd.binary_opening(d > -400, iterations=1)       # 薄いシートを切る
lab, n = nd.label(m); sz = nd.sum(m, lab, range(1, n + 1)); B2 = lab == (np.argmax(sz) + 1)
np.save(out + 'body2.npy', B2)
B2d = nd.binary_dilation(B2, iterations=2)
zz, yy, xx = np.where(B2d)
y0, y1 = int(yy.min() * 2), int(min(300, (yy.max() + 1) * 2)); x0, x1 = int(xx.min() * 2), int((xx.max() + 1) * 2)
C = np.empty((Z, y1 - y0, x1 - x0), np.int16)
for zi in range(Z):
    up = np.repeat(np.repeat(B2d[min(zi // 2, B2d.shape[0] - 1)], 2, 0), 2, 1)[y0:y1, x0:x1]
    s = V[zi, y0:y1, x0:x1]
    C[zi] = np.where(up & (s > -400), s, -1000)
np.save(out + 'zyg_clean.npy', C)
json.dump(dict(y0=y0, x0=x0, shape=[int(v) for v in C.shape], spacing_mm=[0.5, 0.735, 0.735]), open(out + 'clean_meta.json', 'w'))

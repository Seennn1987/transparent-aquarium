# 舌骨の軟骨（臓器 hyoid_cartilage）の吸光度を、写真 06 の喉の水色に合わせる（2026-10-15、計画書 C の記録 15）
#   写真 06（Field Museum 66198、05/06-lightbox-calyptratus-*.jpg）: 首の下の水色の斑（x 955〜1005、y 480〜525 px のうち
#   青 > 赤 + 12 かつ 緑 > 赤 + 5 の画素）の、背景（左上の 50 px 角）で割った吸光度の中央値
#   画面（chameleon.html?view=photo06&still=1、色 06、舌骨の軟骨の吸光度 0）: 舌骨の軟骨の通り道（calibrateOrgans）がある画素のうち、
#   骨の通り道の小さい（骨と重ならない）画素で、背景で割った吸光度（下地）を引き、通り道で割った中央値
#   使い方: python3 fit_hyoidcart06.py <写真06.jpg> <画面.png> <cal.npz>
import numpy as np, sys
from PIL import Image
p = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float)
bg = np.median(p[50:100, 50:100].reshape(-1, 3), 0)
reg = p[480:525, 955:1005]; r, g, b = reg[..., 0], reg[..., 1], reg[..., 2]; m = (b > r + 12) & (g > r + 5)
A_ph = np.median(-np.log(np.clip(reg[m] / bg, 1e-3, 1)), 0)
print('photo 06 throat cyan: pixels', int(m.sum()), 'absorbance', A_ph.round(3))
s = np.asarray(Image.open(sys.argv[2]).convert('RGB')).astype(float)
sbg = np.median(s[20:70, 20:70].reshape(-1, 3), 0)
c = np.load(sys.argv[3])
def down(a):
    H, W = a.shape[:2]
    if H == s.shape[0]: return a
    f = H // s.shape[0]; return a.reshape(H // f, f, W // f, f, *a.shape[2:]).mean((1, 3))
hp = np.maximum(down(c['org_hyoid_cartilage']), 0); bone = np.maximum(down(c['paths'][..., 0]), 0)
A_s = -np.log(np.clip(s / sbg, 1e-3, 1))
sel = (hp > np.percentile(hp[hp > 1e-5], 25)) & (bone < 0.002)
print('screen pixels', int(sel.sum()), 'hyoid path median %.4f' % np.median(hp[sel]), 'base absorbance', np.median(A_s[sel], 0).round(3))
k = np.maximum(np.median((A_ph[None] - A_s[sel]) / hp[sel][:, None], 0), 0)
print('hyoid cartilage absorbance per model unit', k.round(2))

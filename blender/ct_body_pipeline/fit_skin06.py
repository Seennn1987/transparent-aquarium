# 色 06 の膜の強さ（SKIN_GAIN）を写真 06 の首の組織に合わせる（2026-10-15、計画書 C の記録 16）
#   写真 06 の首の組織: 背景で割って 0.90 / 0.87 / 0.69（計画書 第 5 節）→ 青の吸光度 0.371、膜の比 0.28 : 0.37 : 1 の青が 1
#   画面（chameleon.html?view=photo06&still=1）: 首の椎骨 v02〜v04 の点から下へ 3〜40 px、左右 ±2 px のうち、骨の通り道が無く
#   膜の通り道がある画素の、膜の通り道（paths3.py の paths の 3 番目）の中央値 → SKIN_GAIN = 0.371 / 中央値
#   使い方: python3 fit_skin06.py <paths.npy（paths3.py）> <lm.json（lm.py に v02〜v04 を足したもの）>
import numpy as np, json, sys
a = np.load(sys.argv[1]); L = json.load(open(sys.argv[2])); f = a.shape[0] // L['size'][1]
bone = a[..., 0]; skin = a[..., 2]; vals = []
for n in ('v02', 'v03', 'v04'):
    x, y = np.array(L[n]) * f
    for dy in range(3 * f, 40 * f):
        for dx in range(-2 * f, 2 * f + 1):
            yy, xx = int(y + dy), int(x) + dx
            if bone[yy, xx] < 1e-4 and skin[yy, xx] > 1e-3: vals.append(skin[yy, xx])
vals = np.array(vals)
print('neck pixels', len(vals), 'skin path median %.3f quartile %.3f' % (np.median(vals), np.percentile(vals, 75)), 'SKIN_GAIN %.3f' % (0.371 / np.median(vals)))

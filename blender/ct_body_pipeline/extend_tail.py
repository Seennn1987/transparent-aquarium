"""CT に写っていない尾の先の尾椎を、細り方に合わせて足す（計画書 C の記録 76 の案。2026-10-25）。

プロデューサー（2026-10-25）「足りない尾椎を細り方に合わせて足し、膜も作り直して尾をのばす案の絵を、今と動画と並べて見せて下さい。」

  python extend_tail.py <骨.npz> <出力の骨.npz> [--count=23] [--last_mm=0.35]

CT（MorphoSource 000050726）の尾椎は v24〜v55 の 32 個で、v55 も長さ 1.4 mm・太さ 1.5 mm あり、細りきっていない。写真 06 の透明標本で
数えた尾椎は約 55（計画書 第 2 節）。足りない COUNT 個（v56〜）を、静止（CT の座標、mm）で:
・長さ: v55 の長さ × r^k（k = 1…COUNT）。r は最後の 1 個の長さが LAST_MM になる値（既定 23 個・0.35 mm で r = 0.942。v50〜v55 の細り 1 個ごと 0.90 より
  ゆるい。尾の先ほどゆっくり細るとして）
・向き: v53→v54→v55 の曲がり（1 mm あたりの回り）を同じだけ続ける（CT の尾の巻きのまま先へ）
・形: v55 のメッシュを、長さの比で縮め、向きを回して置く（太さも同じ比で細る）
・骨組み: rig__names・head・tail・parent に足し、体軸（rig__axis・rig__dorsal、0.1 mm ごと）と関節の位置（rig__J）を先へのばす
"""
import sys
import numpy as np
from scipy.spatial.transform import Rotation as R

src, dst = sys.argv[1], sys.argv[2]
opts = dict(a[2:].split('=', 1) for a in sys.argv[3:] if a.startswith('--'))
COUNT = int(opts.get('count', 23)); LAST_MM = float(opts.get('last_mm', 0.35))
d = dict(np.load(src))
names = [str(x) for x in d['rig__names']]
H = d['rig__head'].astype(float); T = d['rig__tail'].astype(float)
i55 = names.index('v55')
seg = lambda n: T[names.index(n)] - H[names.index(n)]
L55 = np.linalg.norm(seg('v55'))
r = (LAST_MM / L55) ** (1 / COUNT)
# 1 本あたりの曲がり: v53→v54、v54→v55 の向きの回りの平均（回転ベクトル）を、長さで割って 1 mm あたりに
def turn(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    ax = np.cross(a, b); s = np.linalg.norm(ax)
    return np.zeros(3) if s < 1e-9 else ax / s * np.arctan2(s, a @ b)
t1 = turn(seg('v53'), seg('v54')) / np.linalg.norm(seg('v54')); t2 = turn(seg('v54'), seg('v55')) / np.linalg.norm(seg('v55'))
per_mm = (t1 + t2) / 2
print(f'v55 の長さ {L55:.2f} mm、細り r = {r:.3f}、曲がり {np.degrees(np.linalg.norm(per_mm)):.1f}°/mm')

V55 = d['v55__v'].astype(float); F55 = d['v55__f']
head = T[i55].copy(); dirv = seg('v55') / L55; rot = R.identity(); parent = 'v55'
new_names, new_head, new_tail, new_parent = [], [], [], []
ax = list(d['rig__axis'].astype(float)); dors = list(d['rig__dorsal'].astype(float)); J = list(d['rig__J'].astype(float))
step = float(d['rig__axis_step'])
D0 = d['rig__dorsal'][-1].astype(float)
s_axis = (len(ax) - 1) * step
total = 0.0
for k in range(1, COUNT + 1):
    L = L55 * r ** k
    dr = R.from_rotvec(per_mm * L)
    rot = dr * rot; dirv = dr.apply(dirv)
    tail = head + dirv * L
    n = f'v{55 + k:02d}'
    # 形: v55 を、その頭を原点にして縮め、回して、新しい頭へ
    sc = L / L55
    v = rot.apply((V55 - H[i55]) * sc) + head
    d[n + '__v'] = v.astype(d['v55__v'].dtype); d[n + '__f'] = F55.copy()
    new_names.append(n); new_head.append(head.copy()); new_tail.append(tail.copy()); new_parent.append(parent)
    # 体軸を 0.1 mm ごとにのばす（背の向きも同じだけ回す）
    J.append(s_axis)
    m = int(round(L / step))
    for j in range(1, m + 1):
        ax.append(head + dirv * (L * j / m)); dors.append(rot.apply(D0))
    s_axis += m * step
    head = tail; parent = n; total += L
print(f'足した尾椎 {COUNT} 個（{new_names[0]}〜{new_names[-1]}）、長さ {total:.1f} mm、最後 {L55 * r ** COUNT:.2f} mm')
idx = [i for i in range(len(names))]
d['rig__names'] = np.array(names + new_names); d['rig__head'] = np.vstack([H, new_head]); d['rig__tail'] = np.vstack([T, new_tail])
d['rig__parent'] = np.array([str(x) for x in d['rig__parent']] + new_parent)
d['rig__axis'] = np.array(ax, dtype=d['rig__axis'].dtype); d['rig__dorsal'] = np.array(dors); d['rig__J'] = np.array(J)
np.savez_compressed(dst, **d)

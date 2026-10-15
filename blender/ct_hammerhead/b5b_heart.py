# B5 心臓（推定、2026-10-15、プロデューサー「心臓の部品を出典の図から作る案と、エラの穴の動きの案を作って、ブラウザで切り替えて見られるようにしてください」）
#  CT では心臓と周りの筋肉の値が同じで、形を切り出せなかった（中央の縦断面・横断面 190〜280 mm を見た）。そこで形は図、置き場所は骨格から決める（推定）。
#  形の出典: BIODIDAC の Squalus acanthias の心臓の腹側の図（I. Livingstone、CC BY-NC 4.0、https://omeka.uottawa.ca/biodidac/items/show/4275）。
#   注釈つきの図をブラウザで拡大した 426 × 450 px の画像で、心室の幅 W = 145 px（x 125〜270）を 1 として:
#   心房の左右の幅 245 px = 1.7 W（x 85〜330、心室の背側で左右に張り出す）、静脈洞の左右の幅 275 px = 1.9 W（x 35〜310）・太さ 30 px = 0.2 W（y 345〜375）、
#   動脈円錐の長さ 70 px = 0.48 W（y 120〜190）・太さ 33 px = 0.23 W。心室の前後の長さは幅とほぼ同じ（y 185〜370、前の上は心房に隠れる）
#  置き場所（骨格から、Blender の mm: x 吻端→尾、y 左右、z 背+）: 心膜腔は、肩帯の下の棒（烏口骨、(175, −42) から (230, −66) へ斜め）の前、
#   鰓弓の床（底鰓軟骨、x 160 で z −34、x 200 で z −40）の下、腹の膜（x 170〜200 で z −63）の上。その三角の中に収まる大きさとして W = 26 mm
#  部品: 心室（腹側）、心房（背側、左右の葉）、静脈洞（後ろ・背側の横の管）、動脈円錐（前へ）。なめらかな和の場（距離の場）→ 面
#  出力: mesh/HH_heart.ply、b5_heart.json（中心、大きさ、部品ごとの中心。ページの拍動の中心に使う）
import hh_paths; hh_paths.cd_work()
import numpy as np, json, os
from skimage.measure import marching_cubes
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
W = float(os.environ.get('HH_HEART_W', 26.0))
X0 = float(os.environ.get('HH_HEART_X', 168.0))       # 心室の中心の前後（mm）
Z0 = float(os.environ.get('HH_HEART_Z', -54.0))       # 心室の中心の背腹（mm、Blender z）
def ell(P, c, r):   # 楕円体のおおよその符号つき距離（mm）
    q = (P - np.array(c)) / np.array(r); return (np.linalg.norm(q, axis=-1) - 1) * min(r)
def capsule(P, a, b, r):
    a, b = np.array(a), np.array(b); ab = b - a; t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
    return np.linalg.norm(P - (a + t[..., None] * ab), axis=-1) - r
def smin(a, b, k): h = np.clip(0.5 + 0.5 * (b - a) / k, 0, 1); return b * (1 - h) + a * h - k * h * (1 - h)
parts = {
    'ventricle': dict(c=(X0, 0, Z0), r=(0.52 * W, 0.5 * W, 0.24 * W)),
    'atrium_L': dict(c=(X0 + 0.05 * W, -0.5 * W, Z0 + 0.3 * W), r=(0.5 * W, 0.35 * W, 0.2 * W)),
    'atrium_R': dict(c=(X0 + 0.05 * W, 0.5 * W, Z0 + 0.3 * W), r=(0.5 * W, 0.35 * W, 0.2 * W)),
    'atrium_mid': dict(c=(X0 + 0.15 * W, 0, Z0 + 0.32 * W), r=(0.4 * W, 0.5 * W, 0.14 * W)),
}
sinus = dict(a=(X0 + 0.55 * W, -0.95 * W, Z0 + 0.42 * W), b=(X0 + 0.55 * W, 0.95 * W, Z0 + 0.42 * W), r=0.1 * W)
conus = dict(a=(X0 - 0.45 * W, 0, Z0 + 0.05 * W), b=(X0 - 0.45 * W - 0.48 * W, 0, Z0 + 0.15 * W), r=0.115 * W)
G = 0.35
lo = np.array([X0 - 1.2 * W, -1.15 * W, Z0 - 0.45 * W]); hi = np.array([X0 + 0.85 * W, 1.15 * W, Z0 + 0.8 * W])
xs, ys, zs = (np.arange(lo[i], hi[i], G) for i in range(3))
P = np.stack(np.meshgrid(xs, ys, zs, indexing='ij'), -1)
d = ell(P, **parts['ventricle'])
for k in ('atrium_L', 'atrium_R', 'atrium_mid'): d = smin(d, ell(P, **parts[k]), 0.08 * W)
d = smin(d, capsule(P, sinus['a'], sinus['b'], sinus['r']), 0.06 * W)
d = smin(d, capsule(P, conus['a'], conus['b'], conus['r']), 0.06 * W)
v, f, _, _ = marching_cubes(d.astype(np.float32), 0.0, allow_degenerate=False)
V = (lo + v * G) / 1000.0                                         # Blender の m
# 外向きにそろえる（符号つき体積が正）
a, b_, c_ = V[f[:, 0]], V[f[:, 1]], V[f[:, 2]]
vol = np.einsum('ij,ij->i', a, np.cross(b_, c_)).sum() / 6
if vol < 0: f = f[:, ::-1]
write_ply(f'{OUT}/HH_heart.ply', V, f[:, ::-1])                  # write_ply は面を並べ替えて書く（a8c と同じ）
info = dict(source='BIODIDAC Squalus acanthias heart, ventral view (I. Livingstone, CC BY-NC 4.0) https://omeka.uottawa.ca/biodidac/items/show/4275; placement from the skeleton (estimated)',
            estimated=True, W_mm=W, centre_mm=[round(float(x), 1) for x in ((V.min(0) + V.max(0)) / 2 * 1000)],
            ventricle_centre_mm=list(parts['ventricle']['c']), bounds_mm=[[round(float(x), 1) for x in V.min(0) * 1000], [round(float(x), 1) for x in V.max(0) * 1000]],
            volume_ml=round(abs(float(vol)) * 1e6, 2), faces=int(len(f)))
json.dump(info, open('b5_heart.json', 'w'), ensure_ascii=False, indent=1); print(info)

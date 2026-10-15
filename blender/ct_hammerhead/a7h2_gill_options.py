# A7 エラの骨の案（2026-10-15、プロデューサー「エラの骨の案 A・B・C を作って、標本ページで撮って並べて」）
#  形は出典の図（BIODIDAC の Squalus acanthias の内臓骨格の横からの図、I. Livingstone、CC BY-NC 4.0、
#  https://omeka.uottawa.ca/biodidac/items/show/5134）を画面で読んだもの（計画書 第 9 節 A7「エラの骨の形・大きさ・位置の確認」）:
#   1 対ずつ、腹側の前の端から上がるほど後ろへ傾く角鰓 → 後ろへ曲がる上鰓 → 後ろへ水平に伸びる咽鰓。腹側の下鰓は後ろの正中の底鰓へ。
#   角鰓と上鰓は、後ろのふちへ広がる板（鰓条の並ぶ所）。後ろの対ほど背腹に短い
#  出典の図で読んだ比（並びの長さ = 1。並びの長さ = 1 番目の前の端から 5 番目の角鰓の後ろの端）:
#   高さ 0.79、咽鰓の長さ 0.40、板の幅 0.085
#  左右の位置（前から見た輪）は a7h_gill_arches.py と同じ（外の角はエラの空気の内側の端のすぐ内）
#  座標: z 吻端→尾、u 左右（左が負）、v 背−/腹+（背骨の中心が 0）、mm
#  使い方: python3 a7h2_gill_options.py <名前> <前の端 z> <5 番目の角鰓の後ろ z> <背の高さ v> <腹の高さ v>
#   出力: HH_MESH/HH_gill.ply、a7_gill_arches_<名前>.json。腹の端は体の膜（a5_S_open.npy）の 6 mm 内側までに切る
import hh_paths; hh_paths.cd_work()
import numpy as np, json, sys
from scipy import ndimage as nd
from skimage.measure import marching_cubes
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
TAG = sys.argv[1]; ZF, ZB, VT, VB = map(float, sys.argv[2:6])
d = np.load('a7_gill_field.npz'); og = d['origin']; Gg = float(d['step'])
uin, uout = np.load('a7_uin.npy')
def u_inner(z, v):
    iz = int(round((z - og[0]) / Gg)); iv = int(round((v - og[1]) / Gg))
    if not (0 <= iz < uin.shape[0] and 0 <= iv < uin.shape[1]): return -26.0
    win = uin[max(iz - 6, 0):iz + 7, max(iv - 6, 0):iv + 7]; w = win[np.isfinite(win)]
    return float(np.clip(np.median(w), -36, -20)) if w.size > 20 else -26.0
S = np.load('a5_S_open.npy', mmap_mode='r'); VXs = 0.735; U0s, V0s = -180.0, -150.0
vs_g = V0s + np.arange(S.shape[1]) * VXs; us_g = U0s + np.arange(S.shape[2]) * VXs; band = (us_g > -35) & (us_g < -5)
def body_ventral(z):
    m = np.asarray(S[int(round(z / VXs))])[:, band].any(1); return float(vs_g[np.nonzero(m)[0].max()])
SPAN0 = ZB - ZF
LP, WP = 0.40 * SPAN0, 0.085 * SPAN0
def poly(pts, n=40):
    pts = np.asarray(pts, float); t = np.r_[0, np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))]
    s = np.linspace(0, t[-1], n); return np.stack([np.interp(s, t, pts[:, i]) for i in range(3)], 1)
# 1 対ずつの高さ（後ろほど 6% ずつ短く、体の膜の 6 mm 内側まで）と前後の間隔を決める
def heights(z0s):
    return [min(VB - VT, (body_ventral(z) - 6) - VT) * (1 - 0.06 * k) for k, z in enumerate(z0s)]
sp = SPAN0 / 5
for _ in range(20):                                  # 5 番目の角鰓の後ろ（前の端 + 0.22h + 板の幅）が ZB に来る間隔
    z0s = [ZF + k * sp for k in range(5)]; hs = heights(z0s)
    sp = (ZB - ZF - 0.22 * hs[4] - WP) / 4
z0s = [ZF + k * sp for k in range(5)]; hs = heights(z0s)
segs = []; arches = []                               # segs: (点の列, 半径, 後ろへ広げる板の幅)
for k, (z0, h) in enumerate(zip(z0s, hs)):
    vb = VT + h; ua = u_inner(z0 + 0.22 * h, VT + 0.35 * h) + 1.5
    hb = [(z0 + 0.25 * h, -3, vb + 2), (z0, -15, vb)]
    cb = [(z0, -15, vb), (z0 + 0.12 * h, ua + 3, VT + 0.6 * h), (z0 + 0.22 * h, ua, VT + 0.35 * h)]
    eb = [(z0 + 0.22 * h, ua, VT + 0.35 * h), (z0 + 0.40 * h, (ua - 16) / 2 - 2, VT + 0.12 * h), (z0 + 0.55 * h, -16, VT + 0.02 * h)]
    pb = [(z0 + 0.55 * h, -16, VT), (z0 + 0.55 * h + LP * (1 - 0.1 * k), -6, VT + 1)]
    for name, pts, r, w in (('hypobranchial', hb, 1.0, 0), ('ceratobranchial', cb, 1.0, WP), ('epibranchial', eb, 1.0, WP * 0.8), ('pharyngobranchial', pb, 0.9, 0)):
        segs.append((poly(pts, 60), r, w)); arches.append(dict(arch=k + 1, part=name, points_zuv_mm=np.round(np.asarray(pts, float), 1).tolist(), radius_mm=r, plate_mm=round(w, 1)))
bb0 = (z0s[0] + 0.25 * hs[0], 0, VT + hs[0] + 2); bb1 = (z0s[4] + 0.25 * hs[4] + 0.2 * SPAN0, 0, VT + hs[4] + 2)
segs.append((poly([bb0, bb1], 60), 1.6, 0)); arches.append(dict(arch=0, part='basibranchial', points_zuv_mm=np.round([bb0, bb1], 1).tolist(), radius_mm=1.6))
# 体積にして面を作る（0.35 mm）。板は、線から後ろ（+z）へ幅 w の帯
G = 0.35; pts_all = np.concatenate([p for p, _, _ in segs])
Z0, Z1 = pts_all[:, 0].min() - 8, pts_all[:, 0].max() + WP + 8
U0b, U1b = -50.0, 50.0; V0b, V1b = VT - 8, pts_all[:, 2].max() + 8
shape = (int((Z1 - Z0) / G), int((V1b - V0b) / G), int((U1b - U0b) / G))
mark = np.zeros(shape, bool); rad = np.zeros(shape, np.float32)
for P, r, w in segs:
    for sgn in ((-1, 1) if np.abs(P[:, 1]).max() > 0.5 else (1,)):
        Pd = poly(P, int(np.linalg.norm(np.diff(P, axis=0), axis=1).sum() / 0.1) + 2)
        for t in (np.arange(0, w + 1e-6, 0.2) if w > 0 else [0.0]):
            iz = np.round((Pd[:, 0] + t - Z0) / G).astype(int); iv = np.round((Pd[:, 2] - V0b) / G).astype(int); iu = np.round((sgn * Pd[:, 1] - U0b) / G).astype(int)
            rr = r * (1 - 0.5 * t / w) if w > 0 else r            # 板は後ろのふちほど薄く
            mark[iz, iv, iu] = True; rad[iz, iv, iu] = np.maximum(rad[iz, iv, iu], rr)
dist, ind = nd.distance_transform_edt(~mark, sampling=G, return_indices=True)
R = rad[ind[0], ind[1], ind[2]]; fld = nd.gaussian_filter((R - dist).astype(np.float32), 1.2); del ind
v, f, _, _ = marching_cubes(np.pad(fld, 1, constant_values=-5), 0.0, allow_degenerate=False); v -= 1
Pm = np.stack([Z0 + v[:, 0] * G, U0b + v[:, 2] * G, -(V0b + v[:, 1] * G)], 1) / 1000
write_ply(f'{OUT}/HH_gill.ply', Pm, f)
rep = dict(tag=TAG, front_z=ZF, fifth_ceratobranchial_back_z=ZB, dorsal_v=VT, ventral_v_max=VB, spacing_mm=round(sp, 2),
           heights_mm=[round(x, 1) for x in hs], pharyngobranchial_mm=round(LP, 1), plate_mm=round(WP, 1),
           body_ventral_at_front_mm=[round(body_ventral(z), 1) for z in z0s], faces=int(len(f)), elements=arches,
           source='BIODIDAC Squalus acanthias visceral skeleton (I. Livingstone, CC BY-NC 4.0) https://omeka.uottawa.ca/biodidac/items/show/5134')
json.dump(rep, open(f'a7_gill_arches_{TAG}.json', 'w'), ensure_ascii=False, indent=1)
print(TAG, 'z', round(pts_all[:, 0].min(), 1), '〜', round(pts_all[:, 0].max() + WP, 1), 'heights', rep['heights_mm'], 'faces', len(f))

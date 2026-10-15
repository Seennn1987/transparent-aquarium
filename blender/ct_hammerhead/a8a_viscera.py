# A8 内臓（2026-10-15、プロデューサー「内臓から案を作ってください。CT の体腔から内臓を取り出し、標本ページで撮って並べてください」）
#  CT（最終の座標、a4_skel_field.npy）で、腹側の体腔の中の組織を内臓として取り出す。内臓どうし・内臓と体の壁の値は筋肉とほぼ同じ
#  （-20〜40 HU）で、境目は保存液の抜けたすき間（-150 HU 未満）だけに写る。そこで断面ごとに:
#   1. 体（a5_S0、CT の幅のまま）の中で、背骨の中心より 12 mm 以上腹側のすき間（6 画素以上の塊）を拾う
#   2. すき間を包む凸の形を体腔とし、体の壁 4 画素（2.9 mm）を残して切る
#   3. 体腔の中の -150 HU 以上を内臓とする
#  体腔の形は 3 次元でならし（体軸 4・断面 2 ボクセルのガウス）、その中の組織を、すき間（1 ボクセル広げる）を境に別々の塊に分け、
#  2000 ボクセル以上の塊を内臓とする（塊ごとに閉じた面）。範囲は吻端から 170〜530 mm
#  そのあと胴の幅の倍率（a5a_shell.py の kfac、左右だけ）を内臓にもかけ、体の膜（a5_S_open）の 2 画素内側に収める
#  出力: a8_viscera.npy（最終の座標・広げた後、bool）、a8_viscera_ct.npy（広げる前）、mesh/HH_viscera.ply、a8_viscera.json
#  内臓の名前（肝臓・胃・腸）はまだ分けていない
import hh_paths; hh_paths.cd_work()
import numpy as np, json, sys, os
from scipy import ndimage as nd
from skimage.morphology import convex_hull_image
VX = 0.735; U0, V0 = -180.0, -150.0
F = np.load('a4_skel_field.npy', mmap_mode='r'); S0 = np.load('a5_S0.npy', mmap_mode='r'); NZ, NV, NU = F.shape
vs = V0 + np.arange(NV) * VX; us = U0 + np.arange(NU) * VX
Z0, Z1 = 170.0, 530.0; k0, k1 = int(Z0 / VX), int(Z1 / VX)
keep = np.load('tail_keep_v.npy'); off = np.load('tail_bend_offset_mm.npy')
M = np.zeros((k1 - k0, NV, NU), bool)
for k in range(k0, k1):
    f = np.asarray(F[k]).astype(np.float32); m = nd.binary_fill_holes(np.asarray(S0[k]))
    vc = np.interp(k * VX * 2, np.arange(len(keep)), keep) - np.interp(k * VX, np.arange(len(off)), off)   # 背骨の中心の v（尾の反りの分）
    gap = (f < -150) & m & (vs[:, None] > vc + 12)
    lab, n = nd.label(gap)
    if n == 0: continue
    sz = nd.sum(gap, lab, range(1, n + 1)); gap = np.isin(lab, 1 + np.nonzero(sz >= 6)[0])
    if gap.sum() < 20: continue
    M[k - k0] = convex_hull_image(gap) & nd.binary_erosion(m, iterations=4)
# 2026-10-15 直し: 断面ごとの凸の形を 3 次元でならし（段・平らな切り口を消す）、すき間を境に内臓を別々の塊に分ける
H = nd.gaussian_filter(M.astype(np.float32), (4, 2, 2)) > 0.5
GAP = np.zeros_like(H); TIS = np.zeros_like(H)
for k in range(k0, k1):
    f = np.asarray(F[k]); GAP[k - k0] = f < -150; TIS[k - k0] = f > -150
M = H & TIS & ~nd.binary_dilation(GAP & H, iterations=1)
M = nd.binary_opening(M, iterations=1)
lab, n = nd.label(M); sz = nd.sum(M, lab, range(1, n + 1)); big = 1 + np.nonzero(sz >= 2000)[0]
M = np.isin(lab, big); LAB = np.zeros(lab.shape, np.uint8)
for i, b in enumerate(big[np.argsort(-sz[big - 1])]): LAB[lab == b] = min(i + 1, 255)
Mct = np.zeros((NZ, NV, NU), bool); Mct[k0:k1] = M
np.save('a8_viscera_ct.npy', Mct)
Lct = np.zeros((NZ, NV, NU), np.uint8); Lct[k0:k1] = LAB; np.save('a8_viscera_lab_ct.npy', Lct)
# 胴の幅の倍率をかける（a5a_shell.py と同じ kfac）
src = open(hh_paths.script('a5a_shell.py')).read().split("if STAGE=='2':")[0]
_argv = sys.argv; sys.argv = ['a5a_shell.py', 'x']; ns = {}; exec(src, ns); sys.argv = _argv
kfac = ns['kfac']
So = np.load('a5_S_open.npy', mmap_mode='r')
out = np.zeros((NZ, NV, NU), bool); outl = np.zeros((NZ, NV, NU), np.uint8)
for k in range(k0, k1):
    if not Mct[k].any(): continue
    kk = kfac(k * VX); src_u = us / kk                                     # 出力の u を元の u に戻して引く
    iu = np.clip(np.round((src_u - U0) / VX).astype(int), 0, NU - 1)
    w = Mct[k][:, iu] & nd.binary_erosion(np.asarray(So[k]), iterations=2)
    out[k] = w; outl[k] = np.where(w, Lct[k][:, iu], 0)
np.save('a8_viscera.npy', out); np.save('a8_viscera_lab.npy', outl)
info = dict(z_mm=[Z0, Z1], voxels=int(out.sum()), volume_ml=round(float(out.sum() * VX ** 3 / 1000), 1), volume_ct_ml=round(float(Mct.sum() * VX ** 3 / 1000), 1),
            components=int(nd.label(out)[1]), sizes_ml=[round(float((outl == i).sum() * VX ** 3 / 1000), 1) for i in range(1, int(outl.max()) + 1)])
if 'mesh' in sys.argv:
    exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
    from skimage.measure import marching_cubes
    Vs = []; Fs = []; n = 0
    for li in range(1, int(outl.max()) + 1):            # 内臓の塊ごとに閉じた面（境目が透かして見えるように）
        zz, yy, xx = np.nonzero(outl[k0 - 4:k1 + 4] == li)
        if len(zz) == 0: continue
        lo = np.array([zz.min(), yy.min(), xx.min()]) - 3; hi = np.array([zz.max(), yy.max(), xx.max()]) + 4
        sub = (outl[k0 - 4 + lo[0]:k0 - 4 + hi[0], lo[1]:hi[1], lo[2]:hi[2]] == li).astype(np.float32)
        sub = nd.gaussian_filter(sub, 1.0)
        if sub.max() < 0.5: continue
        v, f, _, _ = marching_cubes(np.pad(sub, 1), 0.5, allow_degenerate=False); v = v - 1 + lo + np.array([k0 - 4, 0, 0])
        Vs.append(v); Fs.append(f + n); n += len(v)
    V = to_blender(np.concatenate(Vs)); Fc = np.concatenate(Fs)
    write_ply(f'{OUT}/HH_viscera.ply', V, Fc); info['faces'] = int(len(Fc))
json.dump(info, open('a8_viscera.json', 'w'), ensure_ascii=False, indent=1); print(info)

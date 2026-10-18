# A4（2026-10-18 足す）: 正中のひれの軟骨を、元の CT の細かさのまま面にしてから、面の頂点を A4 の立て直し（a4d2_median_fins.py）と同じ式で動かす。
#  プロデューサー「第１背鰭、胸鰭、尾鰭の３つの軟骨部分はこのままでOKですが、それ以外のヒレの軟骨表現が変です」→（箱の棒の案に）「そんな直線的で太さも感覚も均一な棒みたいなのを置くのでいいわけないじゃん。」
#  →「その方法で、まず臀びれだけ CT から作り直して、写真と前の版と並べて見せてください」。
#  前のやり方（a4d2 で点を最終の格子 0.735 mm に置き直し、閉じてぼかしてから a4e_mesh.py で面）では、細い棒（約 0.7 mm）が途切れて粒になった。
#  ここでは: 骨の閾値 250 の代わりに HH_FINCT_TH（既定 175。臀びれの切り抜きを閾値 250・200・175・150 で比べ、175 で棒が切れずに離れて並んだ）、
#  元の CT（0.5 × 0.735 × 0.735 mm）を σ 0.5 画素だけぼかして、その値の等値面を作る。残すのは、A2 の骨の塊（臀びれ 4302）を 3 画素広げた所に触れる塊だけ
#  使い方: python3 a4d3_fin_ct_mesh.py anal|dfin2|pelv   → mesh/HH_anal.ply・HH_dfin2.ply・HH_pelv_R/L.ply を書き直す（a4e_mesh.py fins の後）
import hh_paths; hh_paths.cd_work()
import numpy as np, json, sys, os
from scipy import ndimage as nd
from skimage.measure import marching_cubes
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
VX = 0.735
FINS = {'anal': [4302], 'dfin2': [4513], 'pelv': [3064, 3149, 3077]}   # pelv: 右の腹びれの塊（a3e_pelvic_options.py と同じ。左は鏡映）
name = sys.argv[1]; labs = FINS[name]
# 2026-10-19 案 A（プロデューサー「臀びれの CT の軟骨を第 2 背びれの膜に合わせて縮める案 A を作り、写真・前の版と並べて見せてください」）:
#  この CT の第 2 背びれには棒が写っていない（計画書「第 2 背びれの軟骨がまだまばらな理由」）。HH_DFIN2_FROM_ANAL=1 で、臀びれの CT の軟骨（塊 4302）を面にし、
#  臀びれの立て直しで正中へ寄せてから、背腹を返して第 2 背びれの付け根へ置く。大きさは、臀びれの膜（軟骨に合わせた外形: 付け根 49.2 mm・高さ 29.2 mm）を
#  第 2 背びれの参考の外形（hh_fins.py: 付け根 41.0 mm・高さ 20.5 mm）にする割合で、体軸と高さを別々に縮める（左右の厚さは変えない）
FROM_ANAL = name == 'dfin2' and os.environ.get('HH_DFIN2_FROM_ANAL') == '1'
SRC = 'anal' if FROM_ANAL else name
if FROM_ANAL: labs = FINS['anal']
TH = float(os.environ.get('HH_FINCT_TH', 175))
C = np.load('zyg_clean.npy', mmap_mode='r'); L = np.load('skel_lab.npy', mmap_mode='r'); info = json.load(open('comps_info.json'))
cxs, cys = np.load('spine_line.npy'); t = np.load('tilt_sym.npy')
cs_ = [info[str(k)] for k in labs]
z0, z1 = min(c['z'][0] for c in cs_) - 20, max(c['z'][1] for c in cs_) + 21; y0, y1 = max(0, min(c['y'][0] for c in cs_) - 12), min(C.shape[1], max(c['y'][1] for c in cs_) + 12)
x0, x1 = max(0, min(c['x'][0] for c in cs_) - 20), min(C.shape[2], max(c['x'][1] for c in cs_) + 20)
sub = nd.gaussian_filter(np.asarray(C[z0:z1, y0:y1, x0:x1]).astype(np.float32), 0.5); lab = np.isin(np.asarray(L[z0:z1, y0:y1, x0:x1]), labs)
m = sub >= TH; cl, n = nd.label(m, np.ones((3, 3, 3))); keep = np.unique(cl[nd.binary_dilation(lab, iterations=3) & m]); keep = keep[keep > 0]
M = nd.binary_dilation(np.isin(cl, keep), iterations=1)
if name == 'pelv':
    # 腹びれ: 正中から 6 mm 以内（付け根の正中の小片）は使わない。ひれと一緒に後ろ・下へ回すと、腹の下で体の外へ出た（2026-10-18、50 頂点）
    zr_ = np.arange(len(t)); zz_ = np.arange(z0, z1)[:, None, None]; yy_ = np.arange(y0, y1)[None, :, None]; xx_ = np.arange(x0, x1)[None, None, :]
    tt_ = np.radians(np.interp(zz_, zr_, t)); uu_ = (np.cos(tt_) * (xx_ - np.interp(zz_, zr_, cxs)) + np.sin(tt_) * (yy_ - np.interp(zz_, zr_, cys))) * VX
    M &= np.abs(uu_) > float(os.environ.get("HH_PELV_MIDCUT", 6.0))
F = np.where(M, sub, TH - 200.0)                           # 残す塊のまわりだけの値（ほかは閾値より低く）
v, f, _, _ = marching_cubes(np.pad(F, 1, constant_values=TH - 200), TH, allow_degenerate=False); v = v - 1
zi, yi, xi = v[:, 0] + z0, v[:, 1] + y0, v[:, 2] + x0   # 元の CT の画素（小数）
# a4d2_median_fins.py と同じ: 背骨の線と傾きで (u, v) へ、付け根の中央へ寄せて傾きを戻し、高さの帯ごとの左右の中央をそろえる
zr = np.arange(len(t)); tt = np.interp(zi, zr, t); cx = np.interp(zi, zr, cxs); cy = np.interp(zi, zr, cys)
cc, ss = np.cos(np.radians(tt)), np.sin(np.radians(tt)); dx = xi - cx; dy = yi - cy
u = (cc * dx + ss * dy) * VX; vv = (-ss * dx + cc * dy) * VX; zm = zi * 0.5
def _write(path, V, f):
    vol = np.einsum('ij,ij->i', V[f[:, 0]], np.cross(V[f[:, 1]], V[f[:, 2]])).sum() / 6
    if vol > 0: f = f[:, ::-1]                             # write_ply は面を裏返して書くので、ここでは内向きにそろえておく
    write_ply(path, V, f); return abs(vol)
if name == 'pelv':
    # 腹びれ: a3f_pelvic_pose.py と同じ置き方（右の付け根 bb・向き e1〜e3 は閾値 250 の点で決めたものをそのまま使い、後ろへ 60°・下へ 20°）
    exec(open(hh_paths.script('a3e_pelvic_options.py')).read().split("D=np.load('derolled2.npy'")[0])
    Puzv = np.stack([u, zm, vv], 1); loc = (Puzv - bb) @ np.stack([e1, e2, e3], 1)
    R_ = place(1, 60, 20, loc); L_ = R_ * np.array([-1, 1, 1])
    np.savez('a4_pelv175_pts.npz', right=R_.astype(np.float32))   # a5e_pelv_membrane.py が膜の形に使う（HH_PELV_CT175）
    vol = _write(f'{OUT}/HH_pelv_R.ply', np.stack([R_[:, 1], R_[:, 0], -R_[:, 2]], 1) / 1000.0, f)
    _write(f'{OUT}/HH_pelv_L.ply', np.stack([L_[:, 1], L_[:, 0], -L_[:, 2]], 1) / 1000.0, f)
else:
    X = np.load(f'a4_{SRC}_xform.npz'); ub, vb, ang = float(X['ub']), float(X['vb']), float(X['ang'])
    du, dv = u - ub, vv - vb; ca, sa = np.cos(ang), np.sin(ang)
    u2 = du * ca - dv * sa; v2 = du * sa + dv * ca + vb
    u2 = u2 - np.interp(np.round(v2 / 2), X['band_keys'], X['band_med']) * np.clip(np.abs(v2 - vb) / 10, 0, 1)
    if FROM_ANAL:
        import hh_fins; fa, fd2 = hh_fins.FINS['anal'], hh_fins.FINS['dfin2']; TLm = hh_fins.TL_MM
        LA, HA = float(os.environ.get('HH_ANAL_FIT_BASE', 49.2)), float(os.environ.get('HH_ANAL_FIT_H', 29.2))   # a6a の fin_membrane_fit_HH_anal（2026-10-18）
        sx, sy = (fd2['i'] - fd2['o']) * TLm / LA, fd2['H'] * TLm / HA
        Xd = np.load('a4_dfin2_xform.npz'); vbd = float(Xd['vb'])
        z_a0 = zm.min(); zm = float(os.environ.get('HH_DFIN2_O', fd2['o'] * TLm)) + 2.0 + (zm - z_a0) * sx   # 前の端を第 2 背びれの膜の前の端（HH_DFIN2_O、mm）の 2 mm 後ろへ
        v2 = vbd - (v2 - vb) * sy                                     # 臀びれは +v（腹）へ、第 2 背びれは −v（背）へ出る
        rep_from = {'from': 'anal', 'scale_len': round(sx, 3), 'scale_height': round(sy, 3)}
    vol = _write(f'{OUT}/HH_{name}.ply', np.stack([zm, u2, -v2], 1) / 1000.0, f)   # Blender（x = 体軸、y = 左右、z = 背）
rep = {**(rep_from if FROM_ANAL else {}), 'name': name, 'labels': labs, 'threshold': TH, 'components': int(len(keep)), 'voxels': int(np.isin(cl, keep).sum()), 'volume_ml': round(vol * 1e6, 3), 'faces': int(len(f))}
json.dump(rep, open(f'a4_{name}_ctmesh.json', 'w'), ensure_ascii=False); print(rep)

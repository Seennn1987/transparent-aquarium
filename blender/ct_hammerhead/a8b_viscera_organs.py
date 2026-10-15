# A8 内臓の案 2（2026-10-15、プロデューサー「内臓は案 1 を短く試して、内臓らしく見えなければ案 2 に進んでください」）
#  CT の取り出し（a8a_viscera.py）では内臓の境目が見えなかったので、内臓を部品ごとに形を作って CT の体腔に置く。
#  並び方の出典: BIODIDAC の Squalus acanthias の消化器（腹側から開いた図、I. Livingstone、CC BY-NC 4.0、
#   https://omeka.uottawa.ca/biodidac/items/show/4272）。肝臓は左右の長い葉と前の中央の葉、胃は J 字（噴門部が後ろへ下り、細い幽門部が
#   前へ折り返す）、らせん弁のある腸が後ろ、その先に直腸、脾臓は胃の曲がりに沿う。
#  置き場所は CT（最終の座標、正中と u = ±12 mm の縦の断面）で読んだ: 前の塊（200〜345 mm、同心の層 = 胃とみる）、
#   くびれ 345 mm、後ろのひだの多い塊（345〜470 mm = らせん弁の腸とみる）、横の長い一様な塊（u +12 mm、230〜470 mm、体腔の背側 = 肝臓の葉とみる）。
#   名前はどれも推定
#  座標: z 吻端→尾、u 左右（左が負）、v 背−/腹+（背骨の中心が 0）、mm。CT の幅のまま作り、体腔（a8a の取り出しを広げた形）で切ってから
#   胴の幅の倍率（a5a_shell.py の kfac）をかけ、体の膜の 2 画素内側に収める
#  出力: mesh/HH_liver.ply・HH_gut.ply・HH_spiral.ply（内臓ごとに閉じた面）、a8_organs.json
import hh_paths; hh_paths.cd_work()
import numpy as np, json, sys, os
from scipy import ndimage as nd
from skimage.measure import marching_cubes
VX = 0.735; U0, V0 = -180.0, -150.0
F = np.load('a4_skel_field.npy', mmap_mode='r'); NZ, NV, NU = F.shape
vs = V0 + np.arange(NV) * VX; us = U0 + np.arange(NU) * VX
# 内臓の形: 中心線（z, u, v）と半径（背腹 r、左右は r × 横の比 a）
ORGANS = {
    'liver_L':  dict(pts=[(195, -9, 18), (240, -14, 22), (320, -14, 24), (400, -12, 24), (450, -9, 24)], r=[9, 10, 8, 6, 3], a=0.8),
    'liver_R':  dict(pts=[(195, 9, 18), (240, 14, 22), (320, 14, 24), (400, 12, 24), (440, 9, 24)], r=[9, 10, 8, 6, 3], a=0.8),
    'liver_M':  dict(pts=[(188, 0, 20), (205, 0, 24), (222, 0, 28)], r=[8, 9, 6], a=1.2),
    'stomach':  dict(pts=[(205, -3, 30), (240, -4, 38), (290, -4, 42), (330, -2, 44), (343, 3, 46)], r=[7, 11, 12, 10, 6], a=0.9),
    'pylorus':  dict(pts=[(343, 3, 46), (335, 8, 50), (315, 9, 52), (300, 7, 50)], r=[5, 4, 4, 4], a=1.0),
    'duodenum': dict(pts=[(300, 7, 50), (315, 4, 46), (345, 2, 40)], r=[4, 4, 5], a=1.0),
    'intestine': dict(pts=[(345, 2, 40), (380, 2, 40), (420, 2, 41), (455, 1, 43), (470, 0, 46)], r=[9, 12, 12, 10, 6], a=0.9),
    'rectum':   dict(pts=[(470, 0, 46), (490, 0, 50), (510, 0, 55)], r=[5, 4, 3], a=1.0),
    'spleen':   dict(pts=[(300, -12, 48), (320, -13, 50), (340, -11, 50)], r=[3, 4, 3], a=0.7),
}
SPIRAL = dict(z=(350, 465), pitch=15.0, center=(2, 41), inner=0.15, thick=0.9)   # らせん弁の仕切り（腸の中）
# 2026-10-15 案 2b（プロデューサー「内臓の高さを CT の体腔に合わせ、らせん弁を漏斗形の段にした案を作って」）:
#  CT の体腔（背骨の真下 ±10 mm）は上の端が背骨の中心から 12〜18 mm、下の端が 51〜62 mm。案 2 は 300 mm より後ろで上の端が 29〜34 mm と低かった。
#  消化管の中心を上げて太くし、肝臓も上げて下へ厚くし、体腔を上から下まで埋める
ORGANS_B = {
    'liver_L':  dict(pts=[(195, -9, 20), (240, -14, 24), (320, -15, 26), (400, -13, 26), (450, -9, 26)], r=[10, 12, 11, 9, 4], a=0.7),
    'liver_R':  dict(pts=[(195, 9, 20), (240, 14, 24), (320, 15, 26), (400, 13, 26), (440, 9, 26)], r=[10, 12, 11, 9, 4], a=0.7),
    'liver_M':  dict(pts=[(188, 0, 20), (205, 0, 24), (222, 0, 28)], r=[8, 9, 6], a=1.2),
    'stomach':  dict(pts=[(205, -3, 28), (240, -4, 32), (290, -4, 33), (330, -2, 34), (343, 3, 36)], r=[9, 15, 17, 15, 9], a=0.85),
    'pylorus':  dict(pts=[(343, 3, 36), (335, 8, 44), (315, 9, 47), (300, 7, 46)], r=[6, 5, 5, 5], a=1.0),
    'duodenum': dict(pts=[(300, 7, 46), (318, 4, 42), (345, 2, 36)], r=[5, 5, 7], a=1.0),
    'intestine': dict(pts=[(345, 2, 33), (380, 2, 33), (420, 2, 34), (455, 1, 37), (470, 0, 42)], r=[12, 17, 17, 14, 8], a=0.85),
    'rectum':   dict(pts=[(470, 0, 42), (490, 0, 48), (510, 0, 54)], r=[6, 5, 3], a=1.0),
    'spleen':   dict(pts=[(300, -13, 46), (320, -14, 48), (340, -12, 47)], r=[3, 4, 3], a=0.7),
}
SPIRAL_B = dict(z=(352, 462), pitch=10.0, center=(2, 34), slope=0.6, thick=0.8)   # 漏斗形の段: 10 mm おきに、後ろへ開く浅い円錐
if os.environ.get('HH_ORGANS') == 'B':
    ORGANS = ORGANS_B; SPIRAL = SPIRAL_B
if os.environ.get('HH_SPIRAL') == 'bowl':   # 2026-10-15 案 2c（プロデューサー「まだ直線的で角があるように見えます」）
    SPIRAL = dict(z=(352, 462), pitch=10.0, center=(2, 34), shape='bowl', depth=9.0, thick=0.9)
def tube(pts, r, a):
    P = np.array(pts, float); R = np.array(r, float)
    lo = P.min(0) - R.max() - 2; hi = P.max(0) + R.max() + 2
    kz = np.arange(int(lo[0] / VX), int(hi[0] / VX) + 1); iu = np.arange(int((lo[1] / a - U0) / VX) - 30, int((hi[1] - U0) / VX) + 30); iv = np.arange(int((lo[2] - V0) / VX), int((hi[2] - V0) / VX) + 1)
    iu = iu[(iu >= 0) & (iu < NU)]; iv = iv[(iv >= 0) & (iv < NV)]
    Z, Vv, Uu = np.meshgrid(kz * VX, V0 + iv * VX, U0 + iu * VX, indexing='ij')
    best = np.full(Z.shape, np.inf)
    for i in range(len(P) - 1):                       # 線分までの距離 ÷ 半径（左右は a 倍の半径）
        A, B = P[i], P[i + 1]; ra, rb = R[i], R[i + 1]
        d = B - A; L2 = (d ** 2).sum()
        t = np.clip(((Z - A[0]) * d[0] + (Uu - A[1]) * d[1] + (Vv - A[2]) * d[2]) / L2, 0, 1)
        cz, cu, cv = A[0] + t * d[0], A[1] + t * d[1], A[2] + t * d[2]; rr = ra + t * (rb - ra)
        q = np.sqrt((Z - cz) ** 2 + ((Uu - cu) / a) ** 2 + (Vv - cv) ** 2) / np.maximum(rr, .1)
        best = np.minimum(best, q)
    return kz, iv, iu, best <= 1.0
# 体腔: a8a の取り出し（CT の幅のまま）を広げて閉じた形
cav = np.load('a8_viscera_ct.npy', mmap_mode='r')
k0, k1 = int(170 / VX), int(530 / VX)
CAV = np.zeros((k1 - k0, NV, NU), bool); CAV[:] = cav[k0:k1]
CAV = nd.binary_closing(nd.binary_dilation(CAV, iterations=3), iterations=3)
LAB = np.zeros((k1 - k0, NV, NU), np.uint8); names = list(ORGANS) + ['spiral']
for li, (name, o) in enumerate(ORGANS.items(), start=1):
    kz, iv, iu, m = tube(o['pts'], o['r'], o['a'])
    sel = (kz >= k0) & (kz < k1); kz, m = kz[sel], m[sel]
    sub = LAB[np.ix_(kz - k0, iv, iu)]; sub[m & (sub == 0)] = li; LAB[np.ix_(kz - k0, iv, iu)] = sub
# らせん弁の仕切り: 腸の中に、軸のまわりを回る薄い板
li_sp = len(ORGANS) + 1; z0s, z1s = SPIRAL['z']; cu, cv = SPIRAL['center']
for k in range(int(z0s / VX), int(z1s / VX)):
    z = k * VX; th = 2 * np.pi * (z - z0s) / SPIRAL['pitch']
    inside = LAB[k - k0] == list(ORGANS).index('intestine') + 1
    if not inside.any(): continue
    UU, VVv = np.meshgrid(us, vs); du, dv = UU - cu, VVv - cv
    ang = np.arctan2(dv, du); rad = np.hypot(du, dv)
    if SPIRAL.get('shape') == 'bowl':   # 2026-10-15 お椀形: 段の面を放物面にし（中心から外へなだらかに曲がる）、段を回してずらす（らせんでつながる）
        Rl = max(float(rad[inside].max()), 3.0)
        off = (z - z0s) - SPIRAL['depth'] * (rad / Rl) ** 2 - SPIRAL['pitch'] * ang / (2 * np.pi)
        rem = off - SPIRAL['pitch'] * np.round(off / SPIRAL['pitch'])
        thick = SPIRAL['thick'] * (1 - 0.5 * (rad / Rl) ** 2)       # ふちほど薄く
        sheet = inside & (np.abs(rem) < thick) & (rad > 1.0)
    elif 'slope' in SPIRAL:   # 漏斗形: 段 i の円錐は z = z_i + slope × 中心からの距離（後ろへ開く）。いちばん近い段だけを見る
        off = (z - z0s) - SPIRAL['slope'] * rad
        rem = off - SPIRAL['pitch'] * np.round(off / SPIRAL['pitch'])
        sheet = inside & (np.abs(rem) < SPIRAL['thick']) & (rad > 1.5)
    else:
        dth = np.abs(((ang - th) + np.pi) % (2 * np.pi) - np.pi)
        sheet = inside & (dth * np.maximum(rad, 1) < SPIRAL['thick'] * 1.5) & (rad > 1.5)
    LAB[k - k0][sheet] = li_sp
# 2026-10-15 直し: 体腔で切ると内臓の上下が平らに切れて箱に見えたので、体腔では切らない（体の膜の内側に収めるだけ）
if os.environ.get('HH_ORGAN_CLIP') == 'cavity': LAB[~CAV] = 0
# 胴の幅の倍率をかける（a5a_shell.py と同じ kfac）
src = open(hh_paths.script('a5a_shell.py')).read().split("if STAGE=='2':")[0]
_argv = sys.argv; sys.argv = ['a5a_shell.py', 'x']; ns = {}; exec(src, ns); sys.argv = _argv
kfac = ns['kfac']; So = np.load('a5_S_open.npy', mmap_mode='r')
OUTL = np.zeros((k1 - k0, NV, NU), np.uint8)
for k in range(k0, k1):
    if not LAB[k - k0].any(): continue
    iu = np.clip(np.round((us / kfac(k * VX) - U0) / VX).astype(int), 0, NU - 1)
    OUTL[k - k0] = np.where(nd.binary_erosion(np.asarray(So[k]), iterations=2), LAB[k - k0][:, iu], 0)
np.save('a8_organs_lab.npy', OUTL)
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
GROUPS = {'HH_liver': ['liver_L', 'liver_R', 'liver_M'], 'HH_gut': ['stomach', 'pylorus', 'duodenum', 'intestine', 'rectum', 'spleen'], 'HH_spiral': ['spiral']}
Vs = []; Fs = []; n = 0; info = {'source': 'BIODIDAC Squalus acanthias digestive system (I. Livingstone, CC BY-NC 4.0) https://omeka.uottawa.ca/biodidac/items/show/4272; positions from CT', 'organs': {}}
for li, name in enumerate(names, start=1):
    zz, yy, xx = np.nonzero(OUTL == li)
    if len(zz) == 0: info['organs'][name] = 0; continue
    lo = np.array([zz.min(), yy.min(), xx.min()]) - 3; hi = np.array([zz.max(), yy.max(), xx.max()]) + 4
    sub = nd.gaussian_filter((OUTL[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] == li).astype(np.float32), (1.1 if SPIRAL.get('shape') == 'bowl' else 0.8) if name == 'spiral' else 1.2)
    if sub.max() < 0.5: continue
    v, f, _, _ = marching_cubes(np.pad(sub, 1), 0.5, allow_degenerate=False); v = v - 1 + lo + np.array([k0, 0, 0])
    Vs.append((name, v, f)); info['organs'][name] = round(float(len(zz) * VX ** 3 / 1000), 1)
info['faces'] = 0
for g, members in GROUPS.items():           # 肝臓・消化管・らせん弁の仕切りを別々の部品に（色を分けるため）
    parts = [(v, f) for nm, v, f in Vs if nm in members]
    if not parts: continue
    vv = []; ff = []; m = 0
    for v, f in parts: vv.append(v); ff.append(f + m); m += len(v)
    Vg = to_blender(np.concatenate(vv)); Fg = np.concatenate(ff); write_ply(f'{OUT}/{g}.ply', Vg, Fg); info['faces'] += int(len(Fg))
if os.path.exists(f'{OUT}/HH_viscera.ply'): os.remove(f'{OUT}/HH_viscera.ply')
info['ORGANS'] = ORGANS; info['SPIRAL'] = SPIRAL
json.dump(info, open('a8_organs.json', 'w'), ensure_ascii=False, indent=1); print({k: v for k, v in info['organs'].items()}, info['faces'])

# 膜の作り直し 2/2: 戻した空間の軟部（softvol2.py）から、閉じた膜の面と骨への重みを作る。
#   以前（softmesh.py → softrig.py）は、CT の丸まった姿勢でつながって写る所（手足と胴、尾の巻きどうし）を
#   面を外して切り、展示の姿勢で伸びた面もさらに外していた（trim_skin）。外した跡が穴になり、縁が欠けた。
#   ここでは面を外さず、体積のうちに切り離す:
#   1. つながってはいけない持ち主どうし（softrig.py と同じ規則）が 2 ボクセル（0.4 mm）以内に並ぶ所を両側から削る。
#      胴と手足のあいだは、手足の側だけを 4 ボクセル削る（胴の側の、肋骨のまわりの組織を残す）
#   2. 小さな切れ端を外し、体の中の穴を埋める
#   3. 点々の CT から来たでこぼこを、閉じる → 開く（半径 2 ボクセル）でならし（骨から 0.4 mm 以内は戻す）、σ 1.5 ボクセルでぼかして面にする
#   4. 面を 15 万に減らす（pyfqmr）
#   5. 重み: 戻した骨のボクセルへの近さ（σ SOFT_WEIGHT_SIGMA_MM、上位 3 本）。主な骨は頂点のいる所の軟部の持ち主で、それとつながらない骨の分は落とす
#   出力: soft_rigged.npz（softrig.py と同じ形: v は CT の mm、f、w_idx、w_val、names）
import numpy as np, scipy.ndimage as nd, json, time, os
WSIG = float(os.environ.get('SOFT_WEIGHT_SIGMA_MM', '1.0'))   # 重みの広がり σ [mm]
from scipy.spatial import cKDTree
from skimage import measure
t0 = time.time()
z = np.load('soft2_vol.npz'); own = z['own'].astype(np.int32); lo = z['origin'] // 2
Pr = z['bone'].astype(np.float64); Lb = z['bone_lab'].astype(np.int32)
names = json.load(open('bone_names.json')); SIDE = json.load(open('sides.json'))
def rename(n): return SIDE.get(n[:2], n[:2]) + n[2:] if n[:2] in SIDE else n
labs = sorted(set(np.unique(own[own > 0]).tolist()) | set(np.unique(Lb).tolist()))
nm = {l: rename(names[str(l)]) for l in labs}
ROOTV = {'fR': 6, 'fL': 5, 'hL': 23, 'hR': 23}
SEG = {'girdle': 0, 'upper': 1, 'lower': 2, 'hand': 3, 'foot': 3}
def info(n):
    if n.startswith('v'): return ('ax', int(n[1:]))
    if n.startswith('rib'): return ('ax', int(n[3:5]))
    if n in ('head', 'hyoid'): return ('ax', 0)
    a, b = n.split('_')[:2]; return (a, b)
TAIL_FROM = 24          # 尾の椎骨（v24〜）は、隣の椎骨とだけつながる（CT で尾が固く巻いている）
JOINT_MM = float(os.environ.get('SOFT_JOINT_MM', '2.5'))
def bad(a, b):
    ia, ib = info(nm[a]), info(nm[b])
    if ia[0] == 'ax' and ib[0] == 'ax':
        lim = 1 if max(ia[1], ib[1]) >= TAIL_FROM else 2
        return abs(ia[1] - ib[1]) > lim
    if ia[0] != 'ax' and ib[0] != 'ax': return ia[0] != ib[0] or abs(SEG[ia[1]] - SEG[ib[1]]) > 1
    limb, ax = (ia, ib) if ia[0] != 'ax' else (ib, ia)
    return limb[1] != 'girdle' or abs(ax[1] - ROOTV[limb[0]]) > 3
BAD = {(a, b) for a in labs for b in labs if a != b and bad(a, b)}
# 同じ肢の隣り合う骨（肢帯と上腕、上腕と前腕…）は、関節（遠い方の骨の根元）から JOINT_MM 以内でだけつながる。
# CT の個体は肘・膝を深く折りたたんでいて、上腕と前腕の間の軟部がつながって写り、伸ばすと引き伸ばされた
rz = np.load('chameleon_body_ct.npz'); rn = [str(x) for x in rz['rig__names']]
JOINT = {}
for a in labs:
    for b in labs:
        ia, ib = info(nm[a]), info(nm[b])
        if ia[0] != 'ax' and ia[0] == ib[0] and SEG[ib[1]] == SEG[ia[1]] + 1 and nm[b] in rn:
            jp = rz['rig__head'][rn.index(nm[b])]
            JOINT[(a, b)] = JOINT[(b, a)] = jp
print('joint-limited pairs', len(JOINT) // 2)
# 1. 削る
ball = np.zeros((5, 5, 5), bool); g = np.indices((5, 5, 5)) - 2; ball[(g ** 2).sum(0) <= 4] = True
carve = np.zeros(own.shape, bool)
ball4 = np.zeros((9, 9, 9), bool); g4 = np.indices((9, 9, 9)) - 4; ball4[(g4 ** 2).sum(0) <= 16] = True
objs = nd.find_objects(own)
for l in labs:
    if l - 1 >= len(objs) or objs[l - 1] is None: continue
    sl = tuple(slice(max(0, s.start - 2), min(n, s.stop + 2)) for s, n in zip(objs[l - 1], own.shape))
    sub = own[sl]
    near = nd.binary_dilation(sub == l, ball)
    others = np.unique(sub[near & (sub > 0) & (sub != l)])
    # 胴と手足がぶつかる所は、手足の側だけを 4 ボクセル（0.8 mm）削る（胴の側を削ると、肋骨が膜の外に出る）
    lax = info(nm[l])[0] == 'ax'
    badm = [m for m in others.tolist() if (l, m) in BAD and not (not lax and info(nm[m])[0] == 'ax')]
    restm = [m for m in badm if not (lax and info(nm[m])[0] != 'ax')]
    if restm: carve[sl] |= near & np.isin(sub, restm)
    if lax:
        sl4 = tuple(slice(max(0, s.start - 4), min(n, s.stop + 4)) for s, n in zip(objs[l - 1], own.shape))
        sub4 = own[sl4]
        near4 = nd.binary_dilation(sub4 == l, ball4)
        limbm = [m for m in np.unique(sub4[near4 & (sub4 > 0)]).tolist() if (l, m) in BAD and info(nm[m])[0] != 'ax']
        if limbm: carve[sl4] |= near4 & np.isin(sub4, limbm)
    for m in others.tolist():
        if (l, m) in JOINT:
            sel = near & (sub == m)
            ii = np.argwhere(sel) + np.array([q.start for q in sl])
            mm_ = ((ii + lo) * 2 + 0.5) * 0.104
            far = np.linalg.norm(mm_ - JOINT[(l, m)], axis=1) > JOINT_MM
            cs = carve[sl]; cs[tuple((ii[far] - np.array([q.start for q in sl])).T)] = True; carve[sl] = cs
mask = (own > 0) & ~carve
print('carved', int(carve.sum()), 'of', int((own > 0).sum()), f'{time.time()-t0:.0f}s')
# 2. 切れ端と穴
lab, n = nd.label(mask); sz = np.bincount(lab.ravel()); sz[0] = 0
keep = np.nonzero(sz >= 300)[0]
mask = np.isin(lab, keep)
print('pieces kept', len(keep), 'sizes', sorted(sz[keep].tolist(), reverse=True)[:12])
# 3. ならす（切り離した所がまたつながらないように、削った所は閉じる操作で埋めない）
r2 = np.zeros((5, 5, 5), bool); r2[(g ** 2).sum(0) <= 4] = True
m2 = nd.binary_closing(np.pad(mask, 4), r2)[4:-4, 4:-4, 4:-4] & ~carve
m2 = nd.binary_opening(m2, r2)
# 開く操作は 0.8 mm より薄い所を消す。腹側の肋骨のまわりの薄い組織も消え、肋骨が膜の外に出た。
# 骨から 0.4 mm 以内の軟部は戻す
bvox = np.zeros(own.shape, bool)
bi = np.round((Pr - 0.5) / 2).astype(int) - lo
okb = np.all((bi >= 0) & (bi < np.array(own.shape)), 1); bvox[tuple(bi[okb].T)] = True
m2 |= nd.binary_dilation(bvox, iterations=2) & (own > 0) & ~carve
m2 = nd.binary_fill_holes(m2)
lab, n = nd.label(m2); sz = np.bincount(lab.ravel()); sz[0] = 0; m2 = np.isin(lab, np.nonzero(sz >= 300)[0])
np.save('soft2_mask.npy', m2)
F = nd.gaussian_filter(np.pad(m2, 3).astype(np.float32), 1.5)
v, f, _, _ = measure.marching_cubes(F, 0.5)
# 面を減らしてから重みを付ける（Blender で間引いて「最も近い元の頂点」の重みを写すと、切り離したすき間の
# 向こう側の頂点を拾い、尾の巻きから腹へ、後ろ足から首へ、細い棘のような面が伸びた）
import pyfqmr
FACES = int(os.environ.get('SOFT_FACES', '150000'))
simp = pyfqmr.Simplify(); simp.setMesh(v.astype(np.float64), f.astype(np.int32))
simp.simplify_mesh(target_count=FACES, aggressiveness=7, preserve_border=True, verbose=False)
v, f, _ = simp.getMesh()
V = ((v - 3) + lo) * 2 + 0.5                       # 全解像度のボクセル座標（戻した空間）
print('pieces', n, 'verts', len(V), 'faces', len(f), f'{time.time()-t0:.0f}s')
# 4. 重み
kt = cKDTree(Pr)
K = 48; d, j = kt.query(V, k=K, workers=-1); lab_k = Lb[j]
w = np.exp(-0.5 * (d * 0.104 / WSIG) ** 2)
lid = {l: i for i, l in enumerate(labs)}
W = np.zeros((len(V), len(labs)), np.float32)
li = np.vectorize(lid.get)(lab_k)
for c in range(K): np.add.at(W, (np.arange(len(V)), li[:, c]), w[:, c])
# 主な骨 = 頂点のいる所の軟部の持ち主（体積で切り離したのと同じ持ち主）。
#   重みの和で選ぶと、大きな骨（頭）が近くの小さな骨（尾の先）に勝ち、頭と尾のあいだに長い面が伸びた。
#   いちばん近い骨で選ぶと、胴に押し付けられた手足の表面の頂点が肋骨の持ち物になり、手足を開くと長い面が伸びた
_, ind = nd.distance_transform_edt(~m2, return_indices=True)
vi = np.clip(np.round((V - 0.5) / 2).astype(int) - lo, 0, np.array(own.shape) - 1)
vown = own[tuple(ind[:, vi[:, 0], vi[:, 1], vi[:, 2]])]
vown = np.where(vown > 0, vown, np.array(labs)[li[:, 0]])
prim = np.vectorize(lid.get)(vown)
BADI = np.zeros((len(labs), len(labs)), bool)
for a_, b_ in BAD: BADI[lid[a_], lid[b_]] = True
W[BADI[prim]] = 0
W[np.arange(len(V)), prim] += 1e-3
top = np.argsort(-W, 1)[:, :3]; tw = np.take_along_axis(W, top, 1)
tw = tw / np.maximum(tw.sum(1, keepdims=True), 1e-9)
np.savez_compressed('soft_rigged.npz', v=(V * 0.104).astype(np.float32), f=f.astype(np.int32),
                    w_idx=top.astype(np.int16), w_val=tw.astype(np.float32), names=np.array([nm[l] for l in labs]))
print('saved', f'{time.time()-t0:.0f}s')

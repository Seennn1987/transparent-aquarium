"""丸まった指の束を、左右の反対の足と同じくらいまでのばす（計画書 C の記録 65 の案。2026-10-24）。

プロデューサー（2026-10-24）「右後ろ足の内側の丸まった 2 本の指を、左後ろ足と同じくらいまで伸ばす案の絵を、今と並べて見せて下さい。」

  python straighten_digits.py <骨.npz> <指の印.npz> <soft.npz> <出力の骨.npz> <出力の soft.npz> [--limb=hR_foot] [--side=med] [--ref=hL_foot] [--alpha=]

CT の右後ろ足の内側の束（指 2 本）は、扇のように開いて丸まっている（束の付け根から指先までのまっすぐな長さ 4.0 mm、面に沿った長さ 8.3 mm）。
束（静止 = CT の座標、mm）を、面に沿った割合 f（分かれ目 0 → 指先 1。chameleon_digit_bones.py と同じ）で BIN_MM ごとの輪切りにし、
輪切りの重心を結んだ中心線の曲がり（隣り合う線分の向きの回転）を (1 − alpha) 倍にして中心線を組み直す。頂点は、その輪切りの
剛体の動き（f の前後の輪切りの間でなめらかに混ぜる）で動かす。分かれ目のそば（f < RAMP）は動きを 0 からなめらかに入れる。
alpha を指定しないときは、束のまっすぐな長さ ÷ 面に沿った長さが、--ref の足の同じ側の束と同じになる alpha を探す。
膜（soft__v）と爪の鞘（org_claw__v）は、いちばん近い骨の頂点がその束にあれば、その頂点と同じ動き（FULL_MM 1.0 mm まで同じ、NEAR_MM 1.6 mm で 0）で動かす。
"""
import sys
import numpy as np
from scipy.spatial import cKDTree
from scipy.spatial.transform import Rotation, Slerp

bones_p, lab_p, soft_p, out_bones, out_soft = sys.argv[1:6]
opts = dict(a[2:].split('=', 1) for a in sys.argv[6:] if a.startswith('--'))
LIMB = opts.get('limb', 'hR_foot'); SIDE = opts.get('side', 'med'); REF = opts.get('ref', 'hL_foot')
BIN_MM, RAMP, NEAR_MM, FULL_MM = 0.5, 0.15, float(opts.get('near', '1.6')), 1.0
d = dict(np.load(bones_p)); L = np.load(lab_p); S = dict(np.load(soft_p))


def bundle(limb, side):
    lab = L[limb + '__label']; bmap = L[limb + '__bundle']; tip = L[limb + '__tip']; hind = limb.startswith('h')
    for b in (1, 2):
        digits = [i for i in range(1, 6) if bmap[i] == b]
        s = ('med' if len(digits) == 2 else 'lat') if hind else ('med' if len(digits) == 3 else 'lat')
        if s == side:
            idx = np.where(np.isin(lab, digits))[0]
            f = np.zeros(len(idx)); path = 0.0
            for i in digits:
                q = lab[idx] == i; f[q] = 1 - tip[idx][q] / tip[idx][q].max(); path = max(path, tip[idx][q].max())
            return idx, f, digits, path
    raise SystemExit(f'{limb} に {side} の束がない')


def chord(V, idx, f, digits, lab):
    base = V[idx][f < 0.05].mean(0)
    end = np.mean([V[idx][lab[idx] == i][np.argmin(L_tip[idx][lab[idx] == i])] for i in digits], 0)
    return np.linalg.norm(end - base)


def deform(V, idx, f, path, alpha):
    """束の頂点の新しい位置と、輪切りごとの剛体の動き（中心線の組み直し）。"""
    nb = max(4, int(np.ceil(path / BIN_MM)))
    edges = np.linspace(0, 1, nb + 1); cen = []
    for j in range(nb):
        q = (f >= edges[j]) & (f <= edges[j + 1])
        cen.append(V[idx][q].mean(0) if q.any() else cen[-1])
    cen = np.array(cen); seg = np.diff(cen, axis=0); ln = np.linalg.norm(seg, axis=1); dirs = seg / ln[:, None]
    # 隣り合う線分の間の回転 → (1 − alpha) 倍。分かれ目のそばは alpha をなめらかに 0 から
    fc = (edges[:-1] + edges[1:]) / 2
    rot_old = [Rotation.identity()]; rot_new = [Rotation.identity()]
    for j in range(1, len(dirs)):
        ax = np.cross(dirs[j - 1], dirs[j]); s_ = np.linalg.norm(ax); c_ = dirs[j - 1] @ dirs[j]
        ang = np.arctan2(s_, c_)
        r = Rotation.from_rotvec(ax / s_ * ang) if s_ > 1e-9 else Rotation.identity()
        a_j = alpha * np.clip((fc[j] - 0.0) / RAMP, 0, 1)
        rs = Rotation.from_rotvec(r.as_rotvec() * (1 - a_j))
        rot_old.append(r * rot_old[-1]); rot_new.append(rs * rot_new[-1])
    # 輪切り j の動き: x → c'_j + Rnew_j Rold_j⁻¹ (x − c_j)
    newc = [cen[0]]
    for j in range(len(dirs)):
        dj = (rot_new[j] * rot_old[j].inv()).apply(dirs[j])
        newc.append(newc[-1] + dj * ln[j])
    newc = np.array(newc)
    R_bin = [rot_new[min(j, len(dirs) - 1)] * rot_old[min(j, len(dirs) - 1)].inv() for j in range(nb)]
    # 頂点: f の位置で、前後の輪切りの動きを混ぜる
    pos = np.clip(f * nb - 0.5, 0, nb - 1); j0 = np.floor(pos).astype(int); j1 = np.minimum(j0 + 1, nb - 1); w = pos - j0
    P = V[idx]
    A = np.array([R_bin[j].apply(P[k] - cen[j]) + newc[j] for k, j in enumerate(j0)])
    B = np.array([R_bin[j].apply(P[k] - cen[j]) + newc[j] for k, j in enumerate(j1)])
    return A * (1 - w)[:, None] + B * w[:, None]


L_tip = None
def ratio(limb, side, V=None):
    global L_tip
    idx, f, digits, path = bundle(limb, side); L_tip = L[limb + '__tip']
    V = d[limb + '__v'].astype(np.float64) if V is None else V
    return chord(V, idx, f, digits, L[limb + '__label']) / path, idx, f, digits, path


r_ref, *_ = ratio(REF, SIDE)
r0, idx, f, digits, path = ratio(LIMB, SIDE)
V0 = d[LIMB + '__v'].astype(np.float64)
if 'alpha' in opts:
    alpha = float(opts['alpha'])
else:
    lo, hi = 0.0, 1.0
    for _ in range(25):
        a = (lo + hi) / 2; V = V0.copy(); V[idx] = deform(V0, idx, f, path, a)
        if ratio(LIMB, SIDE, V)[0] < r_ref: lo = a
        else: hi = a
    alpha = (lo + hi) / 2
V = V0.copy(); V[idx] = deform(V0, idx, f, path, alpha)
r1 = ratio(LIMB, SIDE, V)[0]
moved = V[idx] - V0[idx]
print(f'{LIMB} {SIDE}: 面に沿った長さ {path:.1f} mm、まっすぐな長さ / 面に沿った長さ {r0:.2f} → {r1:.2f}（{REF} は {r_ref:.2f}）、alpha {alpha:.2f}、頂点の動き 最大 {np.linalg.norm(moved, axis=1).max():.2f} mm')
d[LIMB + '__v'] = V.astype(d[LIMB + '__v'].dtype)

# 重なり: のばした束の頂点が、同じ足のほかの頂点（束の外）の 0.15 mm 以内に入った数（前と後）
others = np.setdiff1d(np.arange(len(V)), idx)
kd = cKDTree(V0[others])
before = int((kd.query(V0[idx])[0] < 0.15).sum()); after = int((kd.query(V[idx])[0] < 0.15).sum())
print(f'ほかの骨の 0.15 mm 以内に入った束の頂点: 前 {before} → 後 {after}')

# 膜と爪の鞘: 束の骨の頂点から NEAR_MM 以内は、いちばん近い骨の頂点と同じ動き
kdb = cKDTree(V0[idx])
for key in ('soft__v', 'org_claw__v'):
    if key not in S: continue
    P = S[key].astype(np.float64); dist, near = kdb.query(P)
    # 束の外の骨のほうが近い頂点は動かさない
    d_other = kd.query(P)[0]
    sel = (dist < NEAR_MM) & (dist <= d_other)
    P[sel] += moved[near[sel]] * np.clip((NEAR_MM - dist[sel]) / (NEAR_MM - FULL_MM), 0, 1)[:, None]   # FULL_MM までは同じだけ、NEAR_MM で 0
    S[key] = P.astype(S[key].dtype)
    print(f'{key}: 動かした頂点 {int(sel.sum())}')
np.savez_compressed(out_bones, **d)
np.savez_compressed(out_soft, **S)

"""振り返り 第 9 節の点検: 今の膜の外形を、背骨に沿った幅（左右）と高さ（背腹）の表にする（2026-10-17）。

作業フォルダ（blender/private/work/）で実行する。
  python ../../ct_body_pipeline/inspect_outline.py [skin_posed.npz] → inspect/outline_profile.npz

座標はページの glb と同じにする（pose_jar の (x, y, z) → (x, z, -y)）。展示の姿勢で 背が −X、腹が +X、頭が −Y、左が +Z。
展示の姿勢の胴は XY 面の中でゆるく曲がるので、背骨の折れ線に最も近い点で位置 s を取り、
左右は Z、背腹は XY 面の中で背骨に直交する向きで測る。手足と尾の重みの頂点は除く（胴と頭だけ）。
長さの単位は肩–股関節の長さ（左右の上腕骨・大腿骨の付け根の中点を背骨へ射影した間の弧長）。
"""
import sys
import numpy as np

skin = sys.argv[1] if len(sys.argv) > 1 else 'skin_posed.npz'
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]


def g(p): p = np.asarray(p, float); return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1)


M = P['M']
# 骨の付け根と先: 静止の位置（head、tail）に展示の姿勢の行列を掛ける（skinbody.py の apply と同じ）
H = g(np.einsum('bij,bj->bi', M[:, :3, :3], P['head']) + M[:, :3, 3]); T = g(np.einsum('bij,bj->bi', M[:, :3, :3], P['tail']) + M[:, :3, 3])
def hd(n): return H[bn.index(n)]


v = g(np.load(skin)['v'])
R = np.load('soft_rigged.npz'); rn = [str(x) for x in R['names']]; w0 = R['w_idx'][:, 0]
own = np.array([rn[i] for i in w0])
trunk = np.array([o == 'head' or o == 'hyoid' or (o[0] == 'v' and int(o[1:]) <= 23) or o.startswith('rib') for o in own])
headv = own == 'head'

# 吻端: 頭の重みの頂点のうち、頭の骨の向き（頭の付け根 → 骨の先）に最も遠い点
hax = T[bn.index('head')] - hd('head'); hax /= np.linalg.norm(hax)
snout = v[headv][np.argmax((v[headv] - hd('head')) @ hax)]
spine = np.array([snout, hd('head')] + [hd('v%02d' % i) for i in range(1, 24)])
# 細かい折れ線
seg = np.diff(spine, axis=0); L = np.linalg.norm(seg, axis=1); S = np.r_[0, np.cumsum(L)]
ts = np.linspace(0, S[-1], 4000); pts = np.stack([np.interp(ts, S, spine[:, k]) for k in range(3)], 1)
tan = np.gradient(pts, axis=0); tan /= np.linalg.norm(tan, axis=1, keepdims=True)


def proj(x):
    i = np.argmin(((pts[None] - x[:, None]) ** 2).sum(-1), 1) if len(x) < 2000 else None
    if i is None:
        from scipy.spatial import cKDTree
        i = cKDTree(pts).query(x)[1]
    return i


sh = proj(np.array([(hd('fL_upper') + hd('fR_upper')) / 2]))[0]
hp = proj(np.array([(hd('hL_upper') + hd('hR_upper')) / 2]))[0]
s_sh, s_hp = ts[sh], ts[hp]; SH = s_hp - s_sh
i = proj(v[trunk]); x = v[trunk]
s = (ts[i] - s_sh) / SH
lat = (x[:, 2] - pts[i, 2]) / SH
# 背腹: XY 面で背骨に直交、背（−X 寄り）を正
n2 = np.stack([tan[i, 1], -tan[i, 0]], 1); n2 *= np.sign(-n2[:, :1] + 1e-12)
dv = ((x[:, :2] - pts[i, :2]) * n2).sum(1) / SH
edges = np.arange(np.floor(s.min() * 50) / 50, s.max() + 0.02, 0.02)
rows = []
for a, b in zip(edges[:-1], edges[1:]):
    m = (s >= a) & (s < b)
    if m.sum() < 20: continue
    rows.append(((a + b) / 2, lat[m].max() - lat[m].min(), dv[m].max() - dv[m].min(), lat[m].min(), lat[m].max(), dv[m].min(), dv[m].max()))
rows = np.array(rows)
k = float(P['k'])
print('肩–股関節 %.3f（glb の単位）= %.1f mm、吻端は肩の %.3f SH 前' % (SH, SH / k, s_sh / SH))
print('  位置/SH   幅/SH   高さ/SH   高さ/幅')
for r in rows[::3]: print('  %6.2f   %6.3f   %6.3f   %6.2f' % (r[0], r[1], r[2], r[2] / r[1]))
np.savez('inspect/outline_profile.npz', rows=rows, SH=SH, s_snout=-s_sh / SH, k=k)

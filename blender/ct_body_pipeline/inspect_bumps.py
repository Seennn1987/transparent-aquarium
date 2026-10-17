"""振り返り 第 9 節の点検: 膜の表面の波・段・継ぎ目の筋を、不透明の陰影の絵と数で見る（2026-10-17）。

作業フォルダで実行する。  python ../../ct_body_pipeline/inspect_bumps.py [skin_posed.npz]
凹凸 = 頂点と、面をなめらかにした（隣の平均を 6 回。波長 2 mm ほどの波・段を拾い、手足や尾の細さの縮みは拾いにくい）面との差を、頂点の法線の向きに測った長さ [mm]。
出力: inspect/bumps_<向き>.png（左: 陰影、右: 凹凸の色。0〜0.25 mm）と、数（全体と部位ごとの 95%・99%・最大）。
"""
import sys
import numpy as np
from PIL import Image, ImageDraw
from scipy import sparse

skin = sys.argv[1] if len(sys.argv) > 1 else 'skin_posed.npz'
k = float(np.load('pose_jar.npz')['k'])
z = np.load(skin); v = z['v'].astype(float) / k; f = z['f']        # mm
v = np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1)                       # ページの glb と同じ向き（背 −X、頭 −Y、左 +Z）
n = len(v)
e = np.r_[f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]
A = sparse.coo_matrix((np.ones(len(e) * 2), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])), (n, n)).tocsr()
A.data[:] = 1; deg = np.asarray(A.sum(1)).ravel(); W = sparse.diags(1 / deg) @ A
s = v.copy()
for _ in range(6): s = 0.5 * s + 0.5 * (W @ s)
fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
vn = np.zeros_like(v); np.add.at(vn, f.ravel(), np.repeat(fn, 3, 0)); vn /= np.linalg.norm(vn, axis=1, keepdims=True) + 1e-12
bump = ((v - s) * vn).sum(1)
R = np.load('soft_rigged.npz'); rn = [str(x) for x in R['names']]; own = np.array([rn[i] for i in R['w_idx'][:, 0]])
part = np.where(own == 'head', '頭', np.where(np.char.startswith(own, 'rib') | np.isin(own, ['v%02d' % i for i in range(1, 23)]), '胴',
                np.where(np.char.startswith(own, 'v'), '尾', '手足')))
print('凹凸 [mm]（なめらかな面からの、法線の向きのずれの絶対値）')
for p in ['全体', '頭', '胴', '尾', '手足']:
    m = np.ones(n, bool) if p == '全体' else part == p
    a = np.abs(bump[m]); print('  %s 95%% %.3f  99%% %.3f  最大 %.3f  （頂点 %d）' % (p, np.percentile(a, 95), np.percentile(a, 99), a.max(), m.sum()))

VIEWS = {'side': (np.array([0, 0, 1.]), np.array([0, 1, 0.])), 'dorsal': (np.array([-1, 0, 0.]), np.array([0, -1, 0.])),
         'ventral': (np.array([1, 0, 0.]), np.array([0, -1, 0.])), 'front': (np.array([0, -1, 0.]), np.array([-1, 0, 0.]))}
L = np.array([-0.4, -0.6, 0.7]); L /= np.linalg.norm(L)
fb = np.abs(bump[f]).max(1)
for name, (d, up) in VIEWS.items():
    rgt = np.cross(up, d); X = v @ rgt; Y = v @ up; D = v @ d
    sc = 700 / max(np.ptp(X), np.ptp(Y)); x0, y0 = X.min(), Y.max()
    P2 = np.stack([(X - x0) * sc + 40, (y0 - Y) * sc + 40], 1)
    Wd, Hd = int(np.ptp(X) * sc + 80), int(np.ptp(Y) * sc + 80)
    order = np.argsort(D[f].mean(1))                                  # 遠い面から描く
    fnn = fn / (np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12)
    lam = np.clip(fnn @ (L[0] * rgt + L[1] * up + L[2] * d), 0, 1)
    vis = (fnn @ d) > 0
    imgs = []
    for mode in ('shade', 'bump'):
        im = Image.new('RGB', (Wd, Hd), (235, 235, 235)); dr = ImageDraw.Draw(im)
        for i in order:
            if not vis[i]: continue
            if mode == 'shade': g = int(60 + 190 * lam[i]); col = (g, g, g)
            else:
                t = min(fb[i] / 0.25, 1); g = 0.35 + 0.65 * lam[i]
                col = (int(255 * g * (0.55 + 0.45 * t)), int(255 * g * (0.75 - 0.55 * t)), int(255 * g * (0.8 - 0.7 * t)))
            dr.polygon([tuple(P2[j]) for j in f[i]], fill=col)
        imgs.append(im)
    out = Image.new('RGB', (Wd * 2, Hd), 'white'); out.paste(imgs[0], (0, 0)); out.paste(imgs[1], (Wd, 0))
    out.save('inspect/bumps_%s.png' % name)
np.save('inspect/bumps.npy', bump)

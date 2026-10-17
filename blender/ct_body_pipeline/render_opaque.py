"""膜を不透明にした診断用の陰影の絵（ページと同じ向き）。  python render_opaque.py <skin_posed.npz> <向き> <出力.png> [幅px]
skin_posed.npz は pose_jar の座標（proposals.py・skinbody.py の出力）。向きは side / dorsal / ventral / front（page_check/views.py と同じ）。"""
import sys
import numpy as np
from PIL import Image, ImageDraw

z = np.load(sys.argv[1]); v = z['v'].astype(float); f = z['f']
v = np.stack([v[:, 0], v[:, 2], -v[:, 1]], 1)
_a, _b, _c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
if np.einsum('ij,ij->i', _a, np.cross(_b, _c)).sum() < 0: f = f[:, ::-1]      # 外向きにそろえる
VIEWS = {'side': ([0, 0, 1.], [0, 1, 0.]), 'dorsal': ([-1, 0, 0.], [0, -1, 0.]), 'ventral': ([1, 0, 0.], [0, -1, 0.]), 'front': ([0, -1, 0.], [-1, 0, 0.])}
d, up = map(np.array, VIEWS[sys.argv[2]]); W = int(sys.argv[4]) if len(sys.argv) > 4 else 700
rgt = np.cross(up, d); X = v @ rgt; Y = v @ up; D = v @ d
# 縮尺は固定（案どうしを同じ大きさで比べる）: 1 単位 = W/6 px、中心は (1.8, -2.2, 1.28)
c = np.array([1.8, -2.2, 1.28]); sc = W / 6.5
P2 = np.stack([(X - c @ rgt) * sc + W / 2, (c @ up - Y) * sc + W * 0.62], 1)
L = np.array([-0.4, -0.6, 0.7]); L /= np.linalg.norm(L)
fn = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]); fn /= np.linalg.norm(fn, axis=1, keepdims=True) + 1e-12
lam = np.clip(fn @ (L[0] * rgt + L[1] * up + L[2] * d), 0, 1); vis = (fn @ d) > 0
im = Image.new('RGB', (W, int(W * 1.25)), (235, 235, 235)); dr = ImageDraw.Draw(im)
for i in np.argsort(D[f].mean(1)):
    if vis[i]: g = int(60 + 190 * lam[i]); dr.polygon([tuple(P2[j]) for j in f[i]], fill=(g, g, g))
im.save(sys.argv[3])

# 舌骨の軟骨（舌内突起・基舌骨・角舌骨、hyoid_rebuild.py の cart__ のうち骨 'hyoid' の分）を、臓器 hyoid_cartilage の面にする
#   （2026-10-15、計画書 C の記録 15）。eyes_mesh.py の後、pack_soft.py の前に走らせる
#   わけ: 写真 06 の喉の水色は、肋骨の途切れと同じ軟骨の強さで描くと画面で 約 4 倍濃かった（赤の吸光度 画面 1.9、写真 0.46）。
#   臓器は色の型ごとに自分の吸光度を持てるので、舌骨の軟骨だけ写真 06 の喉の水色に合わせる（fit_hyoidcart06.py）。
#   generate_chameleon_ct_body.py は骨 'hyoid' の軟骨を CH_Cartilage に入れない（二重にしない）。膜の作り（skinbody.py）は cart__ のまま使う
#   形: 筒（a→b、半径 r）の距離の場を 0.04 mm の升で作り、0 の面。重みは舌骨 1（舌骨は頭骨と同じ変形）。頂点は CT の mm（静止の形）
import numpy as np
from skimage import measure
import pyfqmr
d = np.load('chameleon_body_ct.npz')
own = d['cart__bone']; m = own == 'hyoid'
A, B, R = d['cart__a'][m].astype(float), d['cart__b'][m].astype(float), d['cart__r'][m].astype(float)
print('hyoid cartilage segments', m.sum())
VOX = 0.04
lo = np.minimum(A, B).min(0) - R.max() - 0.3; hi = np.maximum(A, B).max(0) + R.max() + 0.3
shape = tuple(np.ceil((hi - lo) / VOX).astype(int) + 1)
g = [lo[i] + np.arange(shape[i]) * VOX for i in range(3)]
X = np.stack(np.meshgrid(*g, indexing='ij'), -1).reshape(-1, 3)
D = np.full(len(X), np.inf, np.float32)
for a, b, r in zip(A, B, R):
    t = b - a; L2 = t @ t
    near = np.all((X > np.minimum(a, b) - r - 0.1) & (X < np.maximum(a, b) + r + 0.1), 1)
    q = X[near] - a; s = np.clip(q @ t / L2, 0, 1)
    dd = np.linalg.norm(q - s[:, None] * t, axis=1) - r
    D[near] = np.minimum(D[near], dd)
D = np.minimum(D, 1.0).reshape(shape)
v, f, _, _ = measure.marching_cubes(D, 0.0); v = lo + v * VOX
def closed(f):
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), 1); _, c = np.unique(e, axis=0, return_counts=True); return bool((c == 2).all())
assert closed(f)
for ag in (7, 5, 3):
    sp = pyfqmr.Simplify(); sp.setMesh(v.astype(np.float64), f.astype(np.int32)); sp.simplify_mesh(target_count=8000, aggressiveness=ag, preserve_border=True, verbose=False)
    v2, f2, _ = sp.getMesh()
    if closed(f2): v, f = v2, f2; break
vol = np.einsum('ij,ij->i', v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])).sum() / 6
if vol < 0: f = f[:, ::-1]
print('faces', len(f), 'closed', closed(f), 'volume mm3 %.2f' % abs(vol))
o = dict(np.load('organs_rigged.npz')); names = [str(x) for x in o['names']]
if 'hyoid' not in names: names.append('hyoid')
hi_ = names.index('hyoid'); organs = [str(x) for x in o['organs']]
n = 'hyoid_cartilage'
# 保存は他の臓器と同じ向き（organs_mesh.py: 外向きにしてから裏返して保存。読むときに反転する）
o[n + '__v'] = v.astype(np.float32); o[n + '__f'] = f[:, ::-1].astype(np.int32)
o[n + '__w_idx'] = np.full((len(v), 2), hi_, np.int16); o[n + '__w_val'] = np.tile(np.array([1.0, 0.0], np.float32), (len(v), 1))
if n not in organs: organs.append(n)
o['names'] = np.array(names); o['organs'] = np.array(organs)
np.savez_compressed('organs_rigged.npz', **o); print('saved', n)

"""膜（CH_Skin）の、すねと足を胴へじかにつなぐ面を外し、外したあとの穴をふさぐ（計画書 C の記録 99）。

  ../../../.venv/bin/python cut_limb_bridges.py <元の glb> <出力の glb>

・膜は展示（瓶）の姿勢で骨のまわりに作ってあり、そこではすねが腹に触れているので、すね・足の膜と胴の膜（肋骨・椎骨）が面でつながっていた
  （左 174 面、右 96 面）。歩く姿勢で脚をのばすと、この面がすねと腹のあいだに薄い膜のように伸び、横から白い筋に見えた
・頂点を、いちばん重みの大きい骨で「胴」（椎骨・肋骨・帯・頭・舌骨）・「上腕・もも」・「すね・足」（*_lower・*_hand・*_foot と指の束）に分け、
  胴とすね・足の両方を含む面を外す（肘・膝のつながりはそのまま）。外したあとの縁（どの縁も、片方の組の頂点だけでできる）を輪にたどり、輪の重心に頂点を一つ足して扇でふさぐ。
  輪が胴 → もも → すね → もも と回るときは、胴の区間の両端のももの頂点どうしを結んで、胴の輪と、もも＋すねの輪に分けてから、それぞれをふさぐ。
  足した頂点の重みは、輪の中のもも以外の頂点のうち重心にいちばん近いもの。面の向きは、残った面とそろえる
・ほかの部位（骨・軟骨・臓器）は変えない。出力は `asset.extras.chameleon_bridges_cut` を付ける
"""
import sys, json, struct
import numpy as np

src, dst = sys.argv[1], sys.argv[2]
raw = open(src, 'rb').read()
jl = struct.unpack('<I', raw[12:16])[0]; J = json.loads(raw[20:20 + jl])
bo = 20 + jl; bl = struct.unpack('<I', raw[bo:bo + 4])[0]; BIN = bytearray(raw[bo + 8:bo + 8 + bl])
CT = {5126: np.float32, 5125: np.uint32, 5123: np.uint16, 5121: np.uint8}
NC = {'SCALAR': 1, 'VEC3': 3, 'VEC4': 4}


def read(ai):
    a = J['accessors'][ai]; v = J['bufferViews'][a['bufferView']]
    n = NC[a['type']]; dt = CT[a['componentType']]
    stride = v.get('byteStride', 0); off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    assert stride in (0, n * np.dtype(dt).itemsize), (ai, stride)
    arr = np.frombuffer(BIN, dt, a['count'] * n, off).reshape(a['count'], n).copy()
    if a.get('normalized') and dt != np.float32: arr = arr.astype(np.float32) / np.iinfo(dt).max
    return a, arr


def append(arr, ctype, atype, target=None, normalized=False):
    global BIN
    while len(BIN) % 4: BIN.append(0)
    data = np.ascontiguousarray(arr).tobytes(); off = len(BIN); BIN += data
    v = {'buffer': 0, 'byteOffset': off, 'byteLength': len(data)}
    if target: v['target'] = target
    J['bufferViews'].append(v)
    a = {'bufferView': len(J['bufferViews']) - 1, 'componentType': ctype, 'count': int(arr.shape[0] if atype != 'SCALAR' else arr.size), 'type': atype}
    if normalized: a['normalized'] = True
    if atype == 'VEC3' and ctype == 5126: a['min'] = arr.min(0).tolist(); a['max'] = arr.max(0).tolist()
    J['accessors'].append(a); return len(J['accessors']) - 1


node = next(n for n in J['nodes'] if n.get('name') == 'CH_Skin')
skin = J['skins'][node['skin']]; bone_names = [J['nodes'][j]['name'] for j in skin['joints']]
pr = J['meshes'][node['mesh']]['primitives']; assert len(pr) == 1; pr = pr[0]
_, P = read(pr['attributes']['POSITION']); _, N = read(pr['attributes']['NORMAL'])
ja, JI = read(pr['attributes']['JOINTS_0']); wa, W = read(pr['attributes']['WEIGHTS_0'])
ia, F = read(pr['indices']); F = F.reshape(-1, 3).astype(np.int64)
main = np.array([bone_names[JI[i, np.argmax(W[i])]] for i in range(len(P))])
import re
distal = np.array([bool(re.match(r'^(h|f)[LR]_(lower|hand|foot)', n) or re.search(r'_(med|lat)\d*$', n)) for n in main])
side = np.array([n[:2] if distal[i] else '' for i, n in enumerate(main)])
upper = np.array([bool(re.match(r'^(h|f)[LR]_upper', n)) for n in main])
grp = np.where(distal, np.char.add('D', side), np.where(upper, 'U', 'T'))
fg = grp[F]; bridge = ~((fg[:, 0] == fg[:, 1]) & (fg[:, 1] == fg[:, 2]))
# 胴とすね・足をまたぐ面だけ（すね同士・左右の足同士はそのまま）
mixT = (fg == 'T').any(1) & (np.char.startswith(fg, 'D')).any(1)
cut = bridge & mixT
print(f'外す面 {int(cut.sum())}（左 {int((cut & (fg == "DhL").any(1)).sum())}・右 {int((cut & (fg == "DhR").any(1)).sum())}・前脚 {int((cut & np.isin(fg, ["DfL", "DfR"]).any(1)).sum())}）')
keep = F[~cut]
# 縁: 1 枚の面にだけ属する向き付きの辺
from collections import defaultdict
cnt = defaultdict(int)
for a, b, c in keep:
    for e in ((a, b), (b, c), (c, a)): cnt[tuple(sorted(e))] += 1
nxt = {}
for a, b, c in keep:
    for u, v in ((a, b), (b, c), (c, a)):
        if cnt[tuple(sorted((u, v)))] == 1: nxt.setdefault(v, []).append(u)   # 残った面の向きに逆らってたどる = 穴の面の向き
loops, used = [], set()
for s0 in list(nxt):
    for s in nxt[s0]:
        if (s0, s) in used: continue
        loop = [s0]; u, v = s0, s
        while True:
            used.add((u, v)); loop.append(v) if v != loop[0] else None
            if v == loop[0]: break
            cands = [w for w in nxt.get(v, []) if (v, w) not in used]
            if not cands: loop = None; break
            u, v = v, cands[0]
        if loop and len(loop) >= 3: loops.append(loop)
print(f'ふさぐ穴 {len(loops)}（頂点の数 {sorted(len(l) for l in loops)[-8:]} …）')
newP, newN, newJ, newW, newF = [P], [N], [JI], [W], [keep]
nv = len(P)
def split(loop):
    """A rim that runs trunk → thigh → shin → thigh (back to trunk) is split into a trunk rim (the trunk's run and the thigh vertex at each end) and a
    thigh+shin rim (the rest and those two vertices), by a new edge between the two thigh vertices next to the trunk's run; each is then closed where it
    is (closing the whole rim about one centre spread one membrane from the belly to the shin, and splitting along the thigh one from the belly to
    the thigh)."""
    gl = grp[np.array(loop)]
    if not ((gl == 'T').any() and np.char.startswith(gl, 'D').any()): return [loop]
    n = len(loop); isT = gl == 'T'
    # the shortest cyclic interval holding every trunk vertex
    starts = [k for k in range(n) if isT[k] and not isT[k - 1]]
    if len(starts) != 1: return [loop]
    a = starts[0]; b = a
    while isT[(b + 1) % n]: b = (b + 1) % n
    a1, b1 = (a - 1) % n, (b + 1) % n
    l1 = [loop[(a1 + t) % n] for t in range((b1 - a1) % n + 1)]
    l2 = [loop[(b1 + t) % n] for t in range((a1 - b1) % n + 1)]
    if len(l1) < 3 or len(l2) < 3 or (grp[np.array(l2)] == 'T').any(): return [loop]
    return [l1, l2]


for loop0 in loops:
  for loop in split(loop0):
    L = np.array(loop); c = P[L].mean(0)
    gl = grp[L]; pick = L[gl != 'U'] if (gl != 'U').any() else L
    near = pick[np.argmin(np.linalg.norm(P[pick] - c, axis=1))]; jj = JI[near].copy(); ww = W[near].astype(np.float32).copy()
    n = N[L].mean(0); n /= max(np.linalg.norm(n), 1e-9)
    newP.append(c[None].astype(P.dtype)); newN.append(n[None].astype(N.dtype)); newJ.append(jj[None]); newW.append(ww[None])
    newF.append(np.array([[L[k], L[(k + 1) % len(L)], nv] for k in range(len(L))]))
    nv += 1
P2 = np.vstack(newP).astype(np.float32); N2 = np.vstack(newN).astype(np.float32); J2 = np.vstack(newJ); W2 = np.vstack(newW).astype(np.float32); F2 = np.vstack(newF).astype(np.uint32)
# 確かめ: 閉じているか（どの辺も 2 枚の面）
c2 = defaultdict(int)
for a, b, c in F2:
    for e in ((a, b), (b, c), (c, a)): c2[tuple(sorted(e))] += 1
open_edges = sum(1 for v in c2.values() if v != 2)
vol = np.einsum('ij,ij->i', P2[F2[:, 0]], np.cross(P2[F2[:, 1]], P2[F2[:, 2]])).sum() / 6
print(f'頂点 {len(P)} → {len(P2)}、面 {len(F)} → {len(F2)}、開いた辺 {open_edges}、符号つき体積 {vol:.4f}')
pr['attributes']['POSITION'] = append(P2, 5126, 'VEC3', 34962)
pr['attributes']['NORMAL'] = append(N2, 5126, 'VEC3', 34962)
jt = J['accessors'][pr['attributes']['JOINTS_0']]['componentType']
pr['attributes']['JOINTS_0'] = append(J2.astype(CT[jt]), jt, 'VEC4', 34962)
pr['attributes']['WEIGHTS_0'] = append(W2, 5126, 'VEC4', 34962)
pr['indices'] = append(F2.reshape(-1), 5125, 'SCALAR', 34963)
J.setdefault('asset', {}).setdefault('extras', {})['chameleon_bridges_cut'] = '計画書 C の記録 99: すね・足と胴をじかにつなぐ膜の面を外し、穴をふさいだ'
J['buffers'][0]['byteLength'] = len(BIN)
js = json.dumps(J, ensure_ascii=False, separators=(',', ':')).encode('utf-8'); js += b' ' * ((4 - len(js) % 4) % 4)
while len(BIN) % 4: BIN.append(0)
out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(BIN)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(BIN), 0x004E4942) + bytes(BIN)
open(dst, 'wb').write(out); print('書き出した', dst)

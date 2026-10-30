"""?shape=88（計画書 C の記録 89）で直した胴の形を、glb の静止の形（各メッシュの頂点）に焼き込む（記録 90）。

  cd blender/ct_body_pipeline/page_check && ../../../.venv/bin/python bake_shape88.py <元の glb> <出力の glb>

・元の glb は、まだ焼き込んでいない glb（export_chameleon_gltf.py の出力）。`水槽/scenes/specimen/assets/private/proposals/<名前>.glb` に置き、
  ページを `chameleon.html?walk=1&still=1&tune=0&shape=88&glb=<名前>` で開いて、shape88() が動かした後の頂点（chameleonPage.meshPositions()）を読む
・glb の POSITION をその値に置き換え、accessor の min・max を直す。動いた頂点（0.1 µm より）の NORMAL は、同じ位置の頂点をまとめて
  面の向きを面積で平均して作り直す（ほかの頂点の NORMAL はそのまま）
・ページは共有の配信（http://127.0.0.1:8080/）から読む。焼き込んだ glb に ?shape=88 をもう一度かけない（2 回かかる）
・形は歩く姿勢の中で計算するので、手足の置き方で結果が変わる。記録 99 のときの歩き方の値（BAKE_Q）で必ず開く（記録 111: 記録 104〜110 で
  歩き方の既定を変えたあとに焼き込むと、お腹の下の縁が RMS 0.08 → 0.3〜0.5 mm に波打った）。足したいクエリは環境変数 CH_BAKE_Q
"""
import sys, os, json, struct, base64, asyncio, shutil
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import browser
from playwright.async_api import async_playwright

src, dst = sys.argv[1], sys.argv[2]
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..'))
PROP = os.path.join(ROOT, '水槽/scenes/specimen/assets/private/proposals')
name = os.path.splitext(os.path.basename(src))[0]
BAKE_Q = '&gait=a&ankleOut=3&wristOut=0&foreShift=0&forePole=old&low=0.32&arch=14&hjRef=1'   # 記録 99 のときの歩き方
if os.path.abspath(os.path.dirname(src)) != os.path.abspath(PROP):
    os.makedirs(PROP, exist_ok=True); shutil.copyfile(src, os.path.join(PROP, name + '.glb'))


async def read_positions():
    async with async_playwright() as p:
        b = await browser.launch(p); pg = await b.new_page(viewport={'width': 800, 'height': 956})
        logs = []; pg.on('console', lambda m: logs.append(m.text))
        await pg.goto(f'{browser.BASE}/scenes/specimen/chameleon.html?walk=1&still=1&tune=0&shape=88&glb={name}' + BAKE_Q + os.environ.get('CH_BAKE_Q', ''))
        await pg.wait_for_function('document.body.dataset.ready||document.body.dataset.error', timeout=240000)
        if await pg.evaluate('document.body.dataset.error'): raise SystemExit('ページの読み込みに失敗: ' + ' / '.join(logs[-5:]))
        print(next((l for l in logs if 'shape88' in l), 'shape88 の記録なし')[:120])
        r = await pg.evaluate('window.chameleonPage.meshPositions()'); await b.close(); return r


meshes = {m['name']: np.frombuffer(base64.b64decode(m['b64']), np.float32).reshape(-1, 3) for m in asyncio.run(read_positions())}
raw = open(src, 'rb').read()
jl = struct.unpack('<I', raw[12:16])[0]; J = json.loads(raw[20:20 + jl])
bo = 20 + jl; bl = struct.unpack('<I', raw[bo:bo + 4])[0]; BIN = bytearray(raw[bo + 8:bo + 8 + bl])


def view(acc_i):
    a = J['accessors'][acc_i]; v = J['bufferViews'][a['bufferView']]
    assert a['componentType'] == 5126 and a['type'] == 'VEC3' and v.get('byteStride', 12) == 12, a
    off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
    return a, np.frombuffer(BIN, np.float32, a['count'] * 3, off).reshape(-1, 3).copy(), off


changed = 0
for node in J['nodes']:
    if 'mesh' not in node or node.get('name') not in meshes: continue
    prims = J['meshes'][node['mesh']]['primitives']; assert len(prims) == 1, node['name']
    pr = prims[0]; new = meshes[node['name']].astype(np.float32)
    a, old, off = view(pr['attributes']['POSITION']); assert old.shape == new.shape, node['name']
    moved = np.linalg.norm(new - old, axis=1) > 1e-7
    if not moved.any(): continue
    BIN[off:off + new.nbytes] = new.tobytes(); a['min'] = new.min(0).tolist(); a['max'] = new.max(0).tolist()
    # 動いた頂点の NORMAL
    an, nrm, noff = view(pr['attributes']['NORMAL'])
    ia = J['accessors'][pr['indices']]; iv = J['bufferViews'][ia['bufferView']]
    dt = {5125: np.uint32, 5123: np.uint16}[ia['componentType']]
    F = np.frombuffer(BIN, dt, ia['count'], iv.get('byteOffset', 0) + ia.get('byteOffset', 0)).reshape(-1, 3).astype(np.int64)
    _, wid = np.unique(np.round(old, 6), axis=0, return_inverse=True); wid = wid.ravel()
    fn = np.cross(new[F[:, 1]] - new[F[:, 0]], new[F[:, 2]] - new[F[:, 0]])   # 面積の 2 倍の長さ
    acc = np.zeros((wid.max() + 1, 3)); np.add.at(acc, wid[F[:, 0]], fn); np.add.at(acc, wid[F[:, 1]], fn); np.add.at(acc, wid[F[:, 2]], fn)
    n2 = acc[wid]; n2 /= np.maximum(np.linalg.norm(n2, axis=1, keepdims=True), 1e-12)
    # 向きは元の NORMAL にそろえる（面の巻き方が逆のメッシュでも）
    flip = np.sum(n2 * nrm, 1) < 0
    if flip.mean() > 0.5: n2 = -n2
    nrm[moved] = n2[moved].astype(np.float32)
    BIN[noff:noff + nrm.nbytes] = nrm.tobytes()
    changed += 1
    print(f"{node['name']}: 動いた頂点 {int(moved.sum())} / {len(new)}、最大 {np.linalg.norm(new - old, axis=1).max():.4f}（glb の単位）")
J.setdefault('asset', {}).setdefault('extras', {})['chameleon_shape88'] = '計画書 C の記録 90: ?shape=88（記録 89）の胴の形を焼き込み済み'
js = json.dumps(J, ensure_ascii=False, separators=(',', ':')).encode('utf-8'); js += b' ' * ((4 - len(js) % 4) % 4)
BIN += b'\0' * ((4 - len(BIN) % 4) % 4)
out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(BIN)) + struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(BIN), 0x004E4942) + bytes(BIN)
open(dst, 'wb').write(out)
print(f'書き出した: {dst}（直したメッシュ {changed}）')

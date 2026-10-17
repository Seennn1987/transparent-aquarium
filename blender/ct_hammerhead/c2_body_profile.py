# C2 回遊の空きの確かめ用: 体の膜（体・胸びれ・腹びれの膜。標本ページの glb の Skin と PelvicSkin）の、吻端からの長さごとの左右の半幅と、背腹の上下の端を表にする（休みの形）。
#  標本ページとギャラリーの回遊（水槽/scenes/specimen/src/hammerhead-path.js）と自動テスト（tests/hammerhead-circle.mjs）が、
#  体の中心線（hammerhead-path.js）にこの半幅を足して、器の壁・液面・底との空きを測る。
#  左右差（ASYM_GLSL）・胸びれを引く動きは入れない（どちらも数 mm）
#  出力: 水槽/scenes/specimen/src/hammerhead-profile.js（glTF の座標、m: x 吻端→尾、y 背+、z 左+）
import hh_paths
import numpy as np, os, json
def readply(p):
    f = open(p, 'rb'); n = 0; props = []; cur = None
    while True:
        l = f.readline().decode().strip()
        if l.startswith('element'): cur = l.split()[1]
        if l.startswith('element vertex'): n = int(l.split()[-1])
        if l.startswith('property') and cur == 'vertex': props.append(l.split()[1])
        if l == 'end_header': break
    return np.frombuffer(f.read(n * 4 * len(props)), dtype='<f4').reshape(n, len(props))[:, :3]
# 2026-10-17: 標本ページの glb（hh_paths.GLB）の Skin と PelvicSkin（休みの形）から測る。第 1 背びれの板（a6a_export_gltf.py の HH_FIN_PLATE）と
#  胸びれ・腹びれを下へ回した向き（HH_PECT_DOWN・HH_PELV_DOWN）は glb にしか無く、PLY から測ると背の端が 0.123 → 0.102 m と低く出た
import json, struct
def glb_parts(path, parts):
    b = open(path, 'rb').read(); n = struct.unpack('<I', b[12:16])[0]; J = json.loads(b[20:20 + n]); off = 20 + n
    BIN = b[off + 8:off + 8 + struct.unpack('<I', b[off:off + 4])[0]]; out = []
    for nd in J['nodes']:
        if 'mesh' not in nd or nd.get('extras', {}).get('hh_part') not in parts: continue
        a = J['accessors'][J['meshes'][nd['mesh']]['primitives'][0]['attributes']['POSITION']]; bv = J['bufferViews'][a['bufferView']]
        o = bv.get('byteOffset', 0) + a.get('byteOffset', 0); out.append(np.frombuffer(BIN[o:o + a['count'] * 12], dtype='<f4').reshape(-1, 3))
    return np.concatenate(out)
G = glb_parts(hh_paths.GLB, ('Skin', 'PelvicSkin', 'PectSkin', 'Dorsal1Skin', 'Dorsal2Skin', 'AnalSkin'))   # 2026-10-17 ひれの膜を部品に分けた（HH_FIN_PARTS）            # glTF: x 吻端→尾、y 背、z 左
P = np.stack([G[:, 0], -G[:, 2], G[:, 1]], 1)
x, lat, up = P[:, 0], np.abs(P[:, 1]), P[:, 2]          # Blender: x 吻端→尾、y 左右、z 背
STEP = 0.01
xs = np.arange(0, x.max() + STEP, STEP)
half, top, bottom = [], [], []
for a in xs:
    m = (x >= a - STEP / 2) & (x < a + STEP / 2)
    if not m.any(): half.append(0.0); top.append(0.0); bottom.append(0.0); continue
    half.append(float(lat[m].max())); top.append(float(up[m].max())); bottom.append(float(up[m].min()))
out = os.path.join(hh_paths.ROOT, '水槽', 'scenes', 'specimen', 'src', 'hammerhead-profile.js')
r4 = lambda v: [round(t, 4) for t in v]
open(out, 'w', encoding='utf-8').write(
    '// 生成: blender/ct_hammerhead/c2_body_profile.py（体と胸びれ・腹びれの膜、休みの形）。手で書き換えない\n'
    '// 吻端からの長さ（m、STEP ごと）の、左右の半幅・背の端・腹の端（glTF の y）\n'
    f'export const HH_PROFILE = {json.dumps(dict(step=STEP, halfWidth=r4(half), top=r4(top), bottom=r4(bottom)))};\n')
print(out, len(xs), 'max half %.3f' % max(half), 'y %.3f..%.3f' % (min(bottom), max(top)))

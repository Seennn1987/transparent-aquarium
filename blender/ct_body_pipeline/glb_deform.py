"""案の絵のための道具: 標本の glb を、展示の姿勢（CH_Hover の t = 0）の形のまま動かして、別の glb に書く（2026-10-17）。

本番の形を作る道具ではない。直す案を、実際の標本ページで撮って見比べるためのもの。骨組み（関節の位置と動き）は変えず、
頂点だけを動かす。t = 0（?still=1 の画面）では正確で、動かすと関節の回る中心が元のままなので少しずれる。

使い方（Python から）
  G = GLB('specimen_chameleon.glb')
  P = G.posed('CH_Skin')            # 展示の姿勢の頂点（ページの座標: 背 −X、腹 +X、頭 −Y、左 +Z）
  G.set_posed('CH_Skin', P2)        # 動かした頂点を戻す（逆の骨の重みの行列で、静止の頂点に直す）
  G.save('out.glb')
"""
import json
import struct
import numpy as np

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def quat_mat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


class GLB:
    def __init__(self, path):
        b = open(path, 'rb').read()
        jl = struct.unpack('<I', b[12:16])[0]
        self.J = json.loads(b[20:20 + jl])
        o = 20 + jl
        bl = struct.unpack('<I', b[o:o + 4])[0]
        self.bin = bytearray(b[o + 8:o + 8 + bl])
        self.name = {n.get('name'): i for i, n in enumerate(self.J['nodes'])}
        self.parent = {}
        for i, n in enumerate(self.J['nodes']):
            for c in n.get('children', []): self.parent[c] = i
        self._world()

    def acc(self, i):
        a = self.J['accessors'][i]; v = self.J['bufferViews'][a['bufferView']]
        dt = CT[a['componentType']]; n = NC[a['type']]
        off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        stride = v.get('byteStride', 0)
        if stride and stride != n * np.dtype(dt).itemsize:
            raise ValueError('interleaved buffer')
        x = np.frombuffer(self.bin, dt, a['count'] * n, off).reshape(a['count'], n).copy()
        if a.get('normalized'): x = x / np.iinfo(dt).max
        return x

    def _trs_at0(self):
        """各ノードの t = 0 の T・R・S（アニメーションがあればその値、無ければノードの値）。"""
        trs = {i: [np.array(n.get('translation', [0, 0, 0]), float), np.array(n.get('rotation', [0, 0, 0, 1]), float),
                   np.array(n.get('scale', [1, 1, 1]), float)] for i, n in enumerate(self.J['nodes'])}
        for an in self.J.get('animations', []):
            for ch in an['channels']:
                s = an['samplers'][ch['sampler']]; t = self.acc(s['input']).ravel(); v = self.acc(s['output'])
                k = {'translation': 0, 'rotation': 1, 'scale': 2}.get(ch['target']['path'])
                if k is None: continue
                if s.get('interpolation', 'LINEAR') == 'CUBICSPLINE': v = v[1::3]
                j = int(np.searchsorted(t, 0.0, side='right') - 1); j = max(j, 0)
                val = v[j].astype(float)
                if k == 1: val /= np.linalg.norm(val)
                trs[ch['target']['node']][k] = val
        return trs

    def _world(self):
        trs = self._trs_at0(); self.W = {}
        def world(i):
            if i in self.W: return self.W[i]
            t, r, s = trs[i]; M = np.eye(4); M[:3, :3] = quat_mat(r) * s; M[:3, 3] = t
            M = (world(self.parent[i]) @ M) if i in self.parent else M
            self.W[i] = M; return M
        for i in range(len(self.J['nodes'])): world(i)
        sk = self.J['skins'][0]
        self.joints = sk['joints']; self.jname = [self.J['nodes'][j].get('name') for j in self.joints]
        self.IBM = self.acc(sk['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
        self.JM = np.array([self.W[j] for j in self.joints]) @ self.IBM          # 骨ごとの「静止 → 展示の姿勢」

    def joint_pos(self, name):
        return self.W[self.name[name]][:3, 3].copy()

    def prim(self, mesh_name):
        for m in self.J['meshes']:
            if m['name'] == mesh_name: return m['primitives'][0]
        raise KeyError(mesh_name)

    def mesh_names(self):
        return [m['name'] for m in self.J['meshes']]

    def skin_data(self, mesh_name):
        p = self.prim(mesh_name); a = p['attributes']
        return self.acc(a['POSITION']).astype(float), self.acc(a['JOINTS_0']).astype(int), self.acc(a['WEIGHTS_0']).astype(float)

    def S(self, mesh_name):
        _, jo, we = self.skin_data(mesh_name)
        we = we / we.sum(1, keepdims=True)
        return np.einsum('vk,vkij->vij', we, self.JM[jo])

    def posed(self, mesh_name):
        v, _, _ = self.skin_data(mesh_name); S = self.S(mesh_name)
        return np.einsum('vij,vj->vi', S[:, :3, :3], v) + S[:, :3, 3]

    def weights_of(self, mesh_name, names):
        """頂点ごとの、names の骨の重みの和。"""
        _, jo, we = self.skin_data(mesh_name); we = we / we.sum(1, keepdims=True)
        m = np.isin(np.array(self.jname, dtype=object)[jo], list(names))
        return (we * m).sum(1)

    def set_posed(self, mesh_name, P2):
        S = self.S(mesh_name)
        v = np.einsum('vij,vj->vi', np.linalg.inv(S[:, :3, :3]), P2 - S[:, :3, 3]).astype(np.float32)
        ai = self.prim(mesh_name)['attributes']['POSITION']; a = self.J['accessors'][ai]; bv = self.J['bufferViews'][a['bufferView']]
        off = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        self.bin[off:off + v.nbytes] = v.tobytes()
        a['min'] = v.min(0).tolist(); a['max'] = v.max(0).tolist()

    def save(self, path):
        j = json.dumps(self.J, separators=(',', ':')).encode()
        j += b' ' * ((4 - len(j) % 4) % 4)
        bn = bytes(self.bin) + b'\0' * ((4 - len(self.bin) % 4) % 4)
        total = 12 + 8 + len(j) + 8 + len(bn)
        with open(path, 'wb') as f:
            f.write(struct.pack('<III', 0x46546C67, 2, total))
            f.write(struct.pack('<II', len(j), 0x4E4F534A)); f.write(j)
            f.write(struct.pack('<II', len(bn), 0x004E4942)); f.write(bn)

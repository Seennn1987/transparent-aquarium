"""2 つの glb を、組織（メッシュ）ごとに比べる: 三角形と頂点の数、外接の箱（mm）、頂点の位置の差。
使い方: python3 compare_glb.py <元の.glb> <作り直した.glb>
同じ順の頂点がすべて一致すれば =。そうでなければ、片方の各頂点からもう片方へのいちばん近い距離（99% と最大）を出す（Blender の面の減らし方で頂点の順が変わることがある）。
"""
import json, struct, sys
import numpy as np
from scipy.spatial import cKDTree


def read(p):
    b = open(p, 'rb').read()
    n = struct.unpack('<I', b[12:16])[0]; j = json.loads(b[20:20 + n])
    bin_ = b[20 + n + 8:]
    def acc(i):
        a = j['accessors'][i]; v = j['bufferViews'][a['bufferView']]
        dt = {5126: '<f4', 5125: '<u4', 5123: '<u2', 5121: 'u1'}[a['componentType']]
        k = {'SCALAR': 1, 'VEC3': 3, 'VEC2': 2, 'VEC4': 4}[a['type']]
        off = v.get('byteOffset', 0) + a.get('byteOffset', 0)
        return np.frombuffer(bin_, dt, a['count'] * k, off).reshape(a['count'], k) if k > 1 else np.frombuffer(bin_, dt, a['count'], off)
    out = {}
    for m in j['meshes']:
        P = [acc(p['attributes']['POSITION']) for p in m['primitives']]
        T = sum(j['accessors'][p['indices']]['count'] // 3 for p in m['primitives'])
        out[m['name']] = (np.concatenate(P).astype(np.float64), T)
    return out


def main():
    A, B = read(sys.argv[1]), read(sys.argv[2])
    for name in sorted(set(A) | set(B)):
        if name not in A or name not in B: print(f'! {name}: 片方だけ'); continue
        (pa, ta), (pb, tb) = A[name], B[name]
        box = np.abs(np.r_[pa.min(0), pa.max(0)] - np.r_[pb.min(0), pb.max(0)]).max() * 1000
        if len(pa) == len(pb) and ta == tb and np.abs(pa - pb).max() == 0:
            mark, how = '=', '同じ順の頂点がすべて一致'
        else:
            da = cKDTree(pb).query(pa)[0] * 1000; db = cKDTree(pa).query(pb)[0] * 1000
            how = (f'いちばん近い頂点まで 元→新 99% {np.percentile(da, 99):.3f} 最大 {da.max():.3f} mm、新→元 99% {np.percentile(db, 99):.3f} 最大 {db.max():.3f} mm'
                   f'（0.01 mm より離れた頂点 {int((da > 0.01).sum())} / {len(pa)}）')
            mark = '~' if max(da.max(), db.max()) < 0.05 else '!'
        print(f'{mark} {name}: 三角形 {ta}→{tb} 頂点 {len(pa)}→{len(pb)} 箱の差の最大 {box:.3f} mm。{how}')


if __name__ == '__main__':
    main()

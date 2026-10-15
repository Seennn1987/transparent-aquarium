"""作り直した中間ファイル・面を、元のものと数で比べる。
使い方: python3 compare_work.py <元のフォルダ> <作り直したフォルダ> [ファイル名 ...]
  ファイル名を省くと、作り直したフォルダのすべて（.npy .npz .json .ply）を比べる。
  .npy/.npz: 形・型・一致か・差の最大と平均・違う要素の数（bool は違うボクセルの数）
  .json: 一致か（数は 1e-6 まで同じとみなす）。違えば、違うキーを最大 10 個
  .ply: 頂点と面の数・外接の箱（mm）・符号つき体積（ml）
  .png は比べない（図の文字の書体が環境で違う）
出力の 1 行目の印: = 一致、~ 小さな差（差の最大が値の幅の 0.1% 未満）、! 違う、? 元が無い
"""
import json, os, sys
import numpy as np


def load_ply(p):
    f = open(p, 'rb'); h = b''
    while not h.endswith(b'end_header\n'): h += f.read(1)
    hs = h.decode(); nv = int(hs.split('element vertex ')[1].split()[0]); nf = int(hs.split('element face ')[1].split()[0])
    V = np.frombuffer(f.read(nv * 12), '<f4').reshape(nv, 3).astype(np.float64)
    F = np.frombuffer(f.read(nf * 13), dtype=[('n', 'u1'), ('i', '<i4', 3)])['i']
    return V, F


def ply_info(p):
    V, F = load_ply(p); a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    vol = np.einsum('ij,ij->i', a, np.cross(b, c)).sum() / 6 * 1e6
    return dict(verts=len(V), faces=len(F), bbox_mm=np.r_[V.min(0), V.max(0)] * 1000, vol_ml=vol)


def cmp_arr(a, b):
    if a.shape != b.shape or a.dtype != b.dtype:
        return '!', f'形・型が違う 元 {a.shape} {a.dtype} / 新 {b.shape} {b.dtype}'
    if a.dtype == bool:
        n = int((a != b).sum()); return ('=' if n == 0 else '!'), f'違うボクセル {n} / 元の真 {int(a.sum())}'
    if np.array_equal(a, b, equal_nan=np.issubdtype(a.dtype, np.floating)):
        return '=', f'{a.shape} {a.dtype} 一致'
    af, bf = a.astype(np.float64), b.astype(np.float64)
    ok = np.isfinite(af) & np.isfinite(bf); d = np.abs(af - bf)[ok]
    span = float(np.nanmax(af[np.isfinite(af)]) - np.nanmin(af[np.isfinite(af)])) if np.isfinite(af).any() else 0.0
    nd_ = int((np.abs(af - bf) > 0).sum() + (np.isfinite(af) != np.isfinite(bf)).sum())
    scale = max(span, float(np.nanmax(np.abs(af[np.isfinite(af)]))) if np.isfinite(af).any() else 0.0)
    mark = '~' if scale > 0 and d.size and d.max() < scale * 1e-3 and (np.isfinite(af) == np.isfinite(bf)).all() else '!'
    return mark, f'{a.shape} {a.dtype} 差の最大 {d.max() if d.size else 0:.4g} 平均 {d.mean() if d.size else 0:.3g} 違う要素 {nd_}/{a.size}（値の幅 {span:.4g}）'


def cmp_json(a, b, path=''):
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b), key=str):
            if k not in a or k not in b: out.append(f'{path}/{k}（片方だけ）')
            else: out += cmp_json(a[k], b[k], f'{path}/{k}')
    elif isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b): out.append(f'{path}（長さ {len(a)}/{len(b)}）')
        else:
            for i, (x, y) in enumerate(zip(a, b)): out += cmp_json(x, y, f'{path}[{i}]')
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if abs(a - b) > 1e-6 * max(1, abs(a)): out.append(f'{path}: {a} → {b}')
    elif a != b: out.append(f'{path}: {a!r} → {b!r}')
    return out


def compare(fa, fb):
    name = os.path.basename(fb)
    if not os.path.exists(fa): return '?', name, '元に無い'
    ext = os.path.splitext(name)[1]
    if ext == '.npy':
        m, msg = cmp_arr(np.load(fa, mmap_mode='r'), np.load(fb, mmap_mode='r')); return m, name, msg
    if ext == '.npz':
        A, B = np.load(fa), np.load(fb); keys = sorted(set(A.files) | set(B.files)); marks, msgs = [], []
        for k in keys:
            if k not in A.files or k not in B.files: marks.append('!'); msgs.append(f'{k}: 片方だけ'); continue
            m, msg = cmp_arr(A[k], B[k]); marks.append(m); msgs.append(f'{k}: {msg}')
        m = '!' if '!' in marks else ('~' if '~' in marks else '='); return m, name, ' | '.join(msgs)
    if ext == '.json':
        d = cmp_json(json.load(open(fa)), json.load(open(fb)))
        return ('=' if not d else '!'), name, '一致' if not d else f'{len(d)} か所: ' + '; '.join(d[:10])
    if ext == '.ply':
        a, b = ply_info(fa), ply_info(fb)
        same = a['verts'] == b['verts'] and a['faces'] == b['faces'] and np.allclose(a['bbox_mm'], b['bbox_mm'], atol=1e-3)
        exact = same and open(fa, 'rb').read() == open(fb, 'rb').read()
        m = '=' if exact else ('~' if same else '!')
        return m, name, (f"頂点 {a['verts']}→{b['verts']} 面 {a['faces']}→{b['faces']} 体積 {a['vol_ml']:.2f}→{b['vol_ml']:.2f} ml "
                         f"箱の差の最大 {np.abs(a['bbox_mm'] - b['bbox_mm']).max():.3f} mm")
    return None


def main():
    da, db = sys.argv[1], sys.argv[2]
    names = sys.argv[3:] or sorted(os.listdir(db))
    worst = '='
    for n in names:
        r = compare(os.path.join(da, n), os.path.join(db, n))
        if r is None: continue
        print(f'{r[0]} {r[1]}: {r[2]}')
        if r[0] == '!' or (r[0] == '~' and worst == '='): worst = r[0]
    return worst


if __name__ == '__main__':
    main()

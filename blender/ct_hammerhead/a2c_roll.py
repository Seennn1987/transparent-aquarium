"""A2 の続き: 体の横倒し（背の向き）を、椎体の脇の弓（神経弓・血管弓）の向きから測る。
使い方: python3 a2c_roll.py <作業フォルダ>   出力: arch_angle.npy（断面, 角度, 画素数, 椎体の半径）
角度: 断面画像の右 = 0°、真上（背側の台から遠い側）= −90°。
480 mm より後ろは上下に弓が 2 つ写るので、角度を 2 倍した平均（軸）を出し、前の区間から続く側を背とする。"""
import hh_paths
import sys, numpy as np
w = (sys.argv[1] if len(sys.argv) > 1 else hh_paths.WORK).rstrip('/') + '/'
C = np.load(w + 'zyg_clean.npy', mmap_mode='r'); cxs, cys = np.load(w + 'spine_line.npy')
out = []
for z in range(280, 2000, 4):
    s = np.asarray(C[z]).astype(np.float32); y, x = cys[z], cxs[z]
    ys, xs = np.mgrid[int(y) - 12:int(y) + 13, int(x) - 12:int(x) + 13]
    ys = np.clip(ys, 0, s.shape[0] - 1); xs = np.clip(xs, 0, s.shape[1] - 1)
    wt = np.clip(s[ys, xs] - 400, 0, None)
    if wt.sum() == 0: continue
    y, x = (wt * ys).sum() / wt.sum(), (wt * xs).sum() / wt.sum()
    Y, X = np.mgrid[0:s.shape[0], 0:s.shape[1]]; d = np.hypot(Y - y, X - x)
    cen = (s > 400) & (d < 14); rc = np.percentile(d[cen], 95) if cen.sum() > 5 else 7
    ann = (d > rc + 1) & (d < rc + 10) & (s > 220)
    if ann.sum() < 3: out.append((z, np.nan, 0, rc)); continue
    v = np.clip(s[ann] - 220, 0, None)
    out.append((z, np.degrees(np.arctan2(((Y[ann] - y) * v).sum(), ((X[ann] - x) * v).sum())), int(ann.sum()), rc))
o = np.array(out); np.save(w + 'arch_angle.npy', o)
z, a = o[:, 0], o[:, 1]; prev = None
for z0 in range(140, 1000, 40):
    sel = (z >= z0 * 2) & (z < z0 * 2 + 80) & ~np.isnan(a); v = np.radians(a[sel])
    if len(v) < 3: continue
    c2 = np.exp(2j * v).mean(); ax = np.degrees(np.angle(c2) / 2)
    cand = [ax, ax + 180 if ax < 0 else ax - 180]
    d = cand[0] if prev is None else min(cand, key=lambda q: abs(((q - prev + 180) % 360) - 180))
    if prev is None and d > 0: d = cand[1]          # 先頭は上半分（背が上寄り）を選ぶ
    prev = d; print(f'{z0} mm: 背の向き {d:.0f}°（真上から右へ {d + 90:.0f}°）R2={abs(c2):.2f}')

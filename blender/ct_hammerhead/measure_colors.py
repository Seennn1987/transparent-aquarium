"""標本ページの色を部位ごとに測る（A6 と同じ分け方。計画書 第 9 節 A6、hammerhead-stain.js の注）。
使い方: python3 measure_colors.py <tools/record-specimen/measure-hammerhead.mjs の出力フォルダ> [view]
値は「光の通り ÷ ライトボックス（253, 247, 251）」の中央値（赤 / 緑 / 青）。道のりは mm の中央値。
  椎骨の列   骨の道のりが、その最大の半分以上（頭の軟骨・歯・エラの骨の無い所）。椎体（Centrum）を描いていれば、それも重なる
  ひれの放射軟骨  骨なし、ひれ・肩帯などの軟骨 ≥ 0.8 mm、膜 < 30 mm、頭の軟骨・顎・エラの骨なし、頭より後ろ
  頭の軟骨   頭の軟骨の道のりが多い方の 30%
  体の組織   膜 ≥ 50 mm、骨格なし
  エラの骨   エラの骨の道のりが多い方の半分、骨・頭の軟骨なし、ほかの軟骨 < 0.2 mm（2026-10-15 に足した分け方）
  顎         顎の道のりが多い方の半分、骨・頭の軟骨なし、ほかの軟骨 < 0.2 mm（同上）
"""
import json, os, sys
import numpy as np
from PIL import Image

BG = np.array([253, 247, 251.0])


def load(d, view):
    info = json.load(open(os.path.join(d, f'{view}.json'))); W, H = info['width'], info['height']
    rgb = np.asarray(Image.open(os.path.join(d, f'{view}_rgb.png')).convert('RGB'), float) / BG
    P = np.fromfile(os.path.join(d, f'{view}_paths.f32'), '<f4').reshape(H, W, 4).clip(0) * 1000   # mm
    part = {p: np.fromfile(os.path.join(d, f'{view}_part_{p}.f32'), '<f4').reshape(H, W) * 1000 for p in info['parts']}
    return rgb, P, part, info.get('weights', {})


def classes(P, part, weights):
    # 部品だけの道のり × その部品の重みを通り道から引くと、ほかの部品の分が残る（色を混ぜた部品があっても分けられる）
    bone, cart, skin, head = P[..., 0], P[..., 1], P[..., 2], P[..., 3]
    gill, jaw, teeth = (part.get(k, np.zeros_like(bone)) for k in ('Gill', 'Jaw', 'Teeth'))
    w = lambda k, i: weights.get(k, [0, 0, 0, 0])[i] if k in part else 0
    other_bone = bone - w('Gill', 0) * gill - w('Jaw', 0) * jaw
    cen = part.get('Centrum', np.zeros_like(bone))
    other_cart = cart - w('Gill', 1) * gill - w('Jaw', 1) * jaw - w('Centrum', 1) * cen
    if weights.get('Teeth', [0])[0] and 'Teeth' in part: other_bone = other_bone - weights['Teeth'][0] * teeth
    out = {}
    vb = (head < 1e-3) & (teeth < 1e-3) & (gill < 1e-3)
    if (bone[vb] > 0).any(): out['椎骨の列'] = vb & (bone >= bone[vb].max() / 2)
    behind = np.zeros_like(bone, bool)
    if (head > 0).any(): behind[:, np.nonzero((head > 0).any(0))[0].max() + 1:] = True
    out['ひれの放射軟骨'] = (bone < 1e-3) & (other_cart >= 0.8) & (skin < 30) & (head < 1e-3) & (gill < 1e-3) & (jaw < 1e-3) & behind
    if (head > 0).any(): out['頭の軟骨'] = head >= np.percentile(head[head > 0], 70)
    out['体の組織'] = (skin >= 50) & (bone < 1e-3) & (cart < 1e-3) & (head < 1e-3)
    for name, p in (('エラの骨', gill), ('顎', jaw)):
        if (p > 0).any():
            out[name] = (p >= np.percentile(p[p > 0], 50)) & (other_bone < 0.05) & (head < 1e-3) & (other_cart < 0.2)
    return out


def main():
    d = sys.argv[1]; view = sys.argv[2] if len(sys.argv) > 2 else 'top'
    rgb, P, part, weights = load(d, view)
    res = {}
    for name, m in classes(P, part, weights).items():
        if m.sum() == 0: res[name] = None; continue
        r = np.median(rgb[m], 0); p = np.median(P[m], 0)
        own = {k: round(float(np.median(v[m])), 2) for k, v in part.items() if (v[m] > 0).any()}
        res[name] = dict(rgb=[round(float(x), 2) for x in r], pixels=int(m.sum()), path_mm=dict(bone=round(float(p[0]), 2), cartilage=round(float(p[1]), 2), skin=round(float(p[2]), 1), head=round(float(p[3]), 2)), part_mm=own)
        print(f"{name}: {' / '.join(f'{x:.2f}' for x in r)}（{m.sum()} 画素。道のり mm 骨 {p[0]:.2f} 軟骨 {p[1]:.2f} 膜 {p[2]:.1f} 頭 {p[3]:.2f}、部品 {own}）")
    json.dump(res, open(os.path.join(d, f'{view}_measure.json'), 'w'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()

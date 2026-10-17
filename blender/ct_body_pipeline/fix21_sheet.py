"""記録 21 の直し（頭 1.45 倍、胸郭を紡錘形に、頭を除いて膜をならす）の、参考・前の版・今の版を同じ向きで並べる（2026-10-17）。
作業フォルダで実行する。  python ../../ct_body_pipeline/fix21_sheet.py → fix21/fix21_sheet.png
前の版の画面は shots/cur_*.png と cal/p01_base.png（直す前の glb）、今の版は fix21/new_*.png（page_check/views.py・shot.py）。
"""
import json
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

F = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
font_manager.fontManager.addfont(F); plt.rcParams['font.family'] = font_manager.FontProperties(fname=F).get_name()
REF06 = '../../../docs/references/chameleon/06-lightbox-calyptratus-2.jpg'
REF01 = '../../../docs/references/chameleon/01-user-jar-diaphonized.jpg'
LM_06 = dict(snout=(4571, 2146), occiput=(4000, 1880), shoulder=(3370, 1910), hip=(2010, 1340))
COL = (('snout', 'm'), ('occiput', 'g'), ('shoulder', 'c'), ('hip', 'y'))
box06 = (1500, 900, 4800, 2500); c06 = np.hypot(*np.subtract(LM_06['shoulder'], LM_06['hip']))


def page_crop(img, lm):
    c = np.hypot(*np.subtract(lm['shoulder'], lm['hip'])); f = c / c06
    x0 = lm['shoulder'][0] - (LM_06['shoulder'][0] - box06[0]) * f; y0 = lm['shoulder'][1] - (LM_06['shoulder'][1] - box06[1]) * f
    bg = Image.new('RGB', (int((box06[2] - box06[0]) * f), int((box06[3] - box06[1]) * f)), img.getpixel((5, 5)))
    bg.paste(img, (int(-x0), int(-y0))); return bg, (x0, y0)


def ratio(lm): return np.hypot(*np.subtract(lm['snout'], lm['occiput'])) / np.hypot(*np.subtract(lm['shoulder'], lm['hip']))


fig = plt.figure(figsize=(26, 30), dpi=70)
fig.suptitle('記録 21 の直し: 参考・前の版・今の版（どれも実際の標本ページ。2026-10-17）\n頭 1.45 倍（案 1A）、胸郭を X 線の紡錘形で幅はあいだ（案 2B）、頭を除いて膜をならす（案 3B）。色は通り道の比で当て直した', fontsize=17, y=0.995)
# 1 段目: 横（写真 06 の向き）
ax = fig.add_axes([0.01, 0.76, 0.32, 0.19]); ax.imshow(Image.open(REF06).crop(box06)); ax.axis('off')
for k, c in COL: ax.plot(LM_06[k][0] - box06[0], LM_06[k][1] - box06[1], 'o', color=c, ms=8, mec='k')
ax.set_title(f'参考: 写真 06（CC BY-SA 4.0 Brianwray26）\n頭骨 ÷ 肩–股関節 {ratio(LM_06):.2f}', fontsize=13)
for j, (img, lmf, key, title) in enumerate([('shots/cur_photo06.png', 'inspect/landmarks_px.json', 'photo06', '前の版'), ('fix21/new_photo06.png', 'fix21/px_new.json', 'photo06', '今の版')]):
    lm = json.load(open(lmf))[key]; im, (x0, y0) = page_crop(Image.open(img).convert('RGB'), lm)
    ax = fig.add_axes([0.34 + j * 0.33, 0.76, 0.32, 0.19]); ax.imshow(im); ax.axis('off')
    for k, c in COL: ax.plot(lm[k][0] - x0, lm[k][1] - y0, 'o', color=c, ms=8, mec='k')
    ax.set_title(f'{title}（?view=photo06、肩–股関節を写真 06 と同じ長さに）\n頭骨 ÷ 肩–股関節 {ratio(lm):.2f}', fontsize=13)
# 2 段目: 背中
ax = fig.add_axes([0.01, 0.44, 0.15, 0.29]); ax.imshow(Image.open('inspect/melero_p46_0.jpeg')); ax.axis('off')
ax.set_title('参考: 生体の背腹 X 線\nMelero Jurado 2020 図 5.1.4', fontsize=12)
for j, (img, t) in enumerate([('shots/cur_dorsal.png', '前の版（背中から）'), ('fix21/new_dorsal.png', '今の版（背中から）')]):
    ax = fig.add_axes([0.17 + j * 0.16, 0.44, 0.15, 0.29]); ax.imshow(Image.open(img).crop((200, 30, 600, 720))); ax.axis('off'); ax.set_title(t, fontsize=12)
Wt = np.load('proposals/width_targets.npz'); rp = np.load('inspect/outline_profile_prev.npz')['rows']; rn = np.load('fix21/outline_profile_new.npz')['rows']
ax = fig.add_axes([0.53, 0.47, 0.44, 0.24])
ax.plot(rp[:, 0], rp[:, 1], 'k-', lw=2.5, label='前の版の膜'); ax.plot(rn[:, 0], rn[:, 1], 'b-', lw=2.5, label='今の版の膜')
ax.plot(Wt['T'], Wt['width_B'], 'tab:orange', lw=2, ls='--', label='目標（案 2B）'); ax.plot(Wt['T'], Wt['width_A'], 'tab:red', lw=1.5, ls=':', label='X 線（案 2A の線）')
ax.set_xlim(-0.6, 1.1); ax.set_xlabel('肩（0）から股関節（1）までの位置（肩–股関節 = 1）'); ax.set_ylabel('胴の左右の幅 ÷ 肩–股関節')
ax.grid(alpha=0.3); ax.legend(fontsize=11); ax.set_title('背中から見た幅（0 より前は頭と頸）', fontsize=13)
# 3 段目: 色 01（既定の向き）
ax = fig.add_axes([0.01, 0.22, 0.2, 0.19]); ax.imshow(Image.open(REF01)); ax.axis('off'); ax.set_title('参考: 写真 01（瓶、透かし入り。git に入れない）', fontsize=12)
for j, (img, t) in enumerate([('cal/p01_base.png', '前の版 ?stain=01'), ('fix21/new_01.png', '今の版 ?stain=01（色を当て直した）')]):
    ax = fig.add_axes([0.22 + j * 0.2, 0.22, 0.19, 0.19]); ax.imshow(Image.open(img).crop((150, 0, 650, 956))); ax.axis('off'); ax.set_title(t, fontsize=12)
for j, (img, t) in enumerate([('shots/cur_side.png', '前の版 色 06（既定）'), ('fix21/new_side.png', '今の版 色 06')]):
    ax = fig.add_axes([0.62 + j * 0.19, 0.22, 0.18, 0.19]); ax.imshow(Image.open(img).crop((150, 0, 650, 956))); ax.axis('off'); ax.set_title(t, fontsize=12)
# 4 段目: 膜の表面（不透明の診断用の絵）
for j, (n, t) in enumerate([('prev', '前の版'), ('new', '今の版')]):
    for i, vw in enumerate(['side', 'ventral', 'dorsal']):
        img = Image.open(f'fix21/opq_{n}_{vw}.png').crop((60, 40, 560, 700) if vw == 'side' else (120, 40, 480, 700))
        ax = fig.add_axes([0.01 + (j * 3 + i) * 0.165, 0.005, 0.16, 0.19]); ax.imshow(img); ax.axis('off')
        ax.set_title(f'{t} 膜を不透明に（{dict(side="横", ventral="腹", dorsal="背中")[vw]}）', fontsize=11)
fig.savefig('fix21/fix21_sheet.png'); print('saved')

"""proposals.py の案を、点検の点ごとに 1 枚の絵にまとめる（2026-10-17）。作業フォルダで実行する。
  python ../../ct_body_pipeline/proposals_sheet.py → proposals/sheet_head.png、sheet_width.png、sheet_surface.png
画面はどれも標本ページ（?still=1）を撮ったもの（page_check/views.py・shot.py）。膜の陰影の絵だけは render_opaque.py。
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
D = 'proposals/'
R = json.load(open(D + 'proposals.json'))
REF06 = '../../../docs/references/chameleon/06-lightbox-calyptratus-2.jpg'
LM_06 = dict(snout=(4571, 2146), occiput=(4000, 1880), shoulder=(3370, 1910), hip=(2010, 1340))
COL = (('snout', 'm'), ('occiput', 'g'), ('shoulder', 'c'), ('hip', 'y'))


def page_crop(img, lm, chord_px, box06):
    """写真 06 の切り出し box06 と同じ縮尺・同じ肩の位置で、ページの画像を切り出す。"""
    c = np.hypot(*np.subtract(lm['shoulder'], lm['hip'])); f = c / chord_px
    x0 = lm['shoulder'][0] - (LM_06['shoulder'][0] - box06[0]) * f; y0 = lm['shoulder'][1] - (LM_06['shoulder'][1] - box06[1]) * f
    W, H = (box06[2] - box06[0]) * f, (box06[3] - box06[1]) * f
    bg = Image.new('RGB', (int(W), int(H)), img.getpixel((5, 5)))
    bg.paste(img, (int(-x0), int(-y0))); return bg, (x0, y0)


def note(ax, text, size=11):
    ax.axis('off'); ax.text(0, 1, text, va='top', fontsize=size, wrap=True)


# ---------------- 1. 頭と胴の比 ----------------
box06 = (1500, 900, 4800, 2500); c06 = np.hypot(*np.subtract(LM_06['shoulder'], LM_06['hip']))
fig = plt.figure(figsize=(24, 17), dpi=75)
fig.suptitle('案 1: 頭と胴の比（頭骨 ÷ 肩–股関節の直線が、今 0.30、写真 06 で 0.43）　どれも写真 06 の肩–股関節と同じ長さにそろえて、写真 06 の向きで並べた', fontsize=15, y=0.995)
ax = fig.add_axes([0.01, 0.52, 0.32, 0.43]); ax.imshow(Image.open(REF06).crop(box06)); ax.axis('off')
for k, c in COL: ax.plot(LM_06[k][0] - box06[0], LM_06[k][1] - box06[1], 'o', color=c, ms=9, mec='k')
ax.set_title('参考: 写真 06（透明標本、CC BY-SA 4.0 Brianwray26）\n桃 = 吻端、緑 = 後頭、水色 = 肩、黄 = 股関節', fontsize=12)
items = [('now', '今', 'shots/cur_photo06.png', 'inspect/landmarks_px.json'),
         ('head_A', '案 A: 頭を大きくする（1.45 倍）', D + 'shot_head_A_photo06.png', D + 'px_head_A.json'),
         ('head_B', '案 B: 胴を短くする（0.69 倍）', D + 'shot_head_B_photo06.png', D + 'px_head_B.json'),
         ('head_C', '案 C: 頭 1.2 倍・胴 0.83 倍', D + 'shot_head_C_photo06.png', D + 'px_head_C.json')]
pos = [[0.34, 0.52, 0.32, 0.43], [0.67, 0.52, 0.32, 0.43], [0.01, 0.06, 0.32, 0.43], [0.34, 0.06, 0.32, 0.43]]
for (key, title, img, lmf), p in zip(items, pos):
    lm = json.load(open(lmf))['photo06']
    im, (x0, y0) = page_crop(Image.open(img).convert('RGB'), lm, c06, box06)
    ax = fig.add_axes(p); ax.imshow(im); ax.axis('off')
    for k, c in COL: ax.plot(lm[k][0] - x0, lm[k][1] - y0, 'o', color=c, ms=9, mec='k')
    sk = np.hypot(*np.subtract(lm['snout'], lm['occiput'])) / np.hypot(*np.subtract(lm['shoulder'], lm['hip']))
    ax.set_title(f'{title}\n画面で測った 頭骨 ÷ 肩–股関節 = {sk:.2f}', fontsize=12)
note(fig.add_axes([0.68, 0.05, 0.31, 0.44]), '''決めると次に起きること

案 A（頭を大きく）: 頭骨（Digimorph の CT の形のまま）を 1.45 倍に
して置き直す。かぶと・眼・舌骨も一緒に大きくなる。胴・手足・尾は
今のまま。頭の膜・臓器（眼）を作り直し、色 01 を当て直す。
頭が胴に比べて大きく、写真 06・X 線の比になる。

案 B（胴を短く）: 頭は今のまま、肩から股関節までの背骨を 0.69 倍に
詰める。肋骨の間が狭くなる（本番では椎骨の長さを縮めて肋骨を並べ
直す。CT の骨の形を変えることになる）。膜・臓器を作り直し、色を
当て直す。胴の幅 ÷ 胴の長さは 0.22 → 0.31 になり、案 2 の「胴が
細い」の半分ほどがこれで直る。

案 C: A と B のあいだ。

どれを選んでも、まず頭骨の大きさ（または胴の長さ）を決め、骨を置き
直してから膜と臓器を作り直す。決める前に本番の形は変えない。

この絵の作り方: 本番の glb の頂点だけを展示の姿勢で動かした下見
（glb_deform.py、proposals.py）。関節の位置は元のままなので、
頸の付け根で膜が少し引き伸ばされる（凹凸の最大 0.8〜1.2 mm）。
本番で作り直すときはこの伸びは出ない。''', 11.5)
fig.savefig(D + 'sheet_head.png'); plt.close(fig)

# ---------------- 2. 胴の幅と形 ----------------
Wt = np.load(D + 'width_targets.npz')
fig = plt.figure(figsize=(24, 17), dpi=75)
fig.suptitle('案 2: 胴の幅と形（背中から。肩–股関節に対する胴の最大の幅が、今 0.22、生体の背腹 X 線 0.41〜0.42）', fontsize=15, y=0.995)
ax = fig.add_axes([0.005, 0.40, 0.15, 0.56]); ax.imshow(Image.open('inspect/melero_p46_0.jpeg')); ax.axis('off')
ax.set_title('参考: 生体の背腹 X 線\nMelero Jurado 2020 図 5.1.4\n（鎮静して腹ばい）', fontsize=11)
for j, (key, title) in enumerate([('now', '今'), ('width_A', '案 A: 幅も形も X 線'), ('width_B', '案 B: 形は X 線、幅はあいだ'), ('width_C', '案 C: 幅は今、形だけ紡錘形')]):
    img = Image.open('shots/cur_dorsal.png' if key == 'now' else D + f'shot_{key}_dorsal.png').crop((200, 30, 600, 720))
    ax = fig.add_axes([0.16 + j * 0.135, 0.40, 0.13, 0.56]); ax.imshow(img); ax.axis('off')
    mx = Wt['now'].max() if key == 'now' else Wt[key].max()
    ax.set_title(f'{title}\n標本ページを背中から\n最大の幅 ÷ 肩–股関節 {mx:.2f}', fontsize=11)
ax = fig.add_axes([0.72, 0.62, 0.27, 0.32])
ax.plot(Wt['T'], Wt['now'], 'k-', lw=2.5, label='今')
for key, c, lab in (('width_A', 'tab:red', '案 A'), ('width_B', 'tab:orange', '案 B'), ('width_C', 'tab:blue', '案 C')):
    ax.plot(Wt['T'], Wt[key], color=c, lw=2, label=lab)
ax.set_xlabel('肩（0）から股関節（1）までの位置'); ax.set_ylabel('胴の幅 ÷ 肩–股関節'); ax.grid(alpha=0.3); ax.legend(fontsize=10)
ax.set_title('胴の幅（左右）の線。X 線が読めるのは 0.24〜0.72\n（その外は前肢と腿が重なるので、端で今の幅へつないだ）', fontsize=11)
for j, key in enumerate(['now', 'width_A', 'width_B', 'width_C']):
    img = Image.open('shots/cur_front.png' if key == 'now' else D + f'shot_{key}_front.png').crop((250, 300, 600, 650))
    ax = fig.add_axes([0.16 + j * 0.135, 0.05, 0.13, 0.30]); ax.imshow(img); ax.axis('off')
    ax.set_title({'now': '今', 'width_A': '案 A', 'width_B': '案 B', 'width_C': '案 C'}[key] + '（正面: 頭の先から）', fontsize=11)
note(fig.add_axes([0.72, 0.05, 0.27, 0.52]), '''決めると次に起きること

本番では、胸郭の幅（ribmodel2.py の肋骨の並べ方。今は X 線の
「胴の幅 ÷ 頭骨 0.80」で合わせてある）を選んだ線に変えて肋骨を
並べ直し、膜・臓器を作り直し、色 01 を当て直す。高さ（背腹）は
変えない。

案 A: X 線と同じ幅（最大 1.9 倍）。腹ばいの生体なので、保存した
透明標本より広い可能性がある。正面から見た断面は横長に近くなる。
案 B: 形は X 線の紡錘形、幅は今と X 線のあいだ（最大 1.45 倍）。
案 C: 最大の幅は今のまま。X 線の読める範囲では今と形の差が小さく
（0.93〜1.04 倍）、見た目はほとんど変わらない。

案 1 で「胴を短くする」を選ぶと、それだけで幅 ÷ 胴の長さは
0.22 → 0.31 になる。案 1 と案 2 は一緒に決めるのがよい。

この絵は下見（glb_deform.py）: 膜・肋骨・軟骨・臓器の頂点を、
背骨からの左右の距離に倍率を掛けて動かした。椎骨と手足は動かさない。''', 11.5)
fig.savefig(D + 'sheet_width.png'); plt.close(fig)

# ---------------- 3. 膜の表面 ----------------
diag = {}
for k in ('surf_A', 'surf_B', 'surf_C'):
    t = open(D + f'diag_{k}.txt').read().split('\n'); diag[k] = [x for x in t if x and x[0].isdigit()][0].split()
fig = plt.figure(figsize=(24, 17), dpi=75)
fig.suptitle('案 3: 膜の表面（肋骨ごとの横の筋は腹と横に出る。上 2 段: 膜を不透明にした診断用の陰影、下の段: 標本ページを腹から）', fontsize=15, y=0.995)
names = [('now', '今'), ('surf_A', '案 A: 胴だけならす'), ('surf_B', '案 B: 頭を除いてならす'), ('surf_C', '案 C: 全部を強くならす')]
for j, (key, title) in enumerate(names):
    for i, vw in enumerate(['side', 'ventral']):
        img = Image.open(D + f'opq_{key}_{vw}.png').crop((60, 40, 560, 700) if vw == 'side' else (150, 40, 450, 700))
        ax = fig.add_axes([0.01 + j * 0.2, [0.58, 0.31][i], 0.19, [0.29, 0.25][i]]); ax.imshow(img); ax.axis('off')
        if i == 0:
            r = R[key]; extra = '' if key == 'now' else f'\n骨のはみ出し 最大 {diag[key][0]} mm（{diag[key][1]}）'
            ax.set_title(f'{title}\n凹凸 95% {r["凹凸_95"]:.3f}・99% {r["凹凸_99"]:.3f} mm' + (extra if key != 'now' else '\n骨のはみ出し 最大 0.27 mm（v36）'), fontsize=11)
    img = Image.open('shots/cur_ventral.png' if key == 'now' else D + f'shot_{key}_ventral.png').crop((250, 30, 610, 700))
    ax = fig.add_axes([0.01 + j * 0.2, 0.01, 0.19, 0.28]); ax.imshow(img); ax.axis('off')
note(fig.add_axes([0.81, 0.05, 0.18, 0.88]), '''見えるもの（向きを直して
描き直した）
・腹と横に、肋骨 1 本ごとの
  横の筋（腹で強い）
・喉（舌骨のあたり）のでこぼこ
・腰の腹側の平らな板と角
・背の正中の線は、記録 10 で
  作った背のとげの列（意図した
  もの。直す対象にしない）

決めると次に起きること
本番では skinbody.py の最後に
「膜をならす」段を足し（選んだ
範囲と強さ）、膜の検査 5 本を回し、
色 01 を当て直す（膜の厚みが少し
変わる）。骨の形は変えない。

案 A: 胴の筋が弱まる。喉・腰は
そのまま。
案 B: 胴・喉・腰・手足・尾が
なめらかになる。頭は今のまま。
案 C: 頭も含めて全部。頭の後ろの
継ぎ目の段も弱まる。

下の段（実際の標本ページ）では、
今でも筋はほとんど見えない。
膜を通る長さの差が小さいため。

ならすほど膜が少し縮み、骨の
はみ出しが増える（最大 0.27 →
0.29〜0.44 mm）。本番では、骨の
外へ出ないように押し戻す処理を
一緒に入れる。

凹凸 = なめらかにした面からの
ずれ（波長 2 mm ほど）。肋骨の筋
（波長 約 4.5 mm）は数より絵で
見る。''', 11.5)
fig.savefig(D + 'sheet_surface.png'); plt.close(fig)
print('saved')

"""肋骨の付け根の案 D（付け根を椎骨の側面へ上げて差し込む。rib_roots.py socket）を、今・案 C・写真 06 と並べる（2026-10-17）。
作業フォルダで実行する。 → prop22/sheet_ribD.png"""
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
F = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
font_manager.fontManager.addfont(F); plt.rcParams['font.family'] = font_manager.FontProperties(fname=F).get_name()
R06 = '../../../docs/references/chameleon/06-lightbox-calyptratus-2.jpg'
fig = plt.figure(figsize=(26, 22), dpi=70)
fig.suptitle('案 D: 肋骨の付け根を椎骨の側面へ上げて差し込む（標本ページ。上: 胴の中ほどに強く寄せて横から、下: 胴の後ろ半分を横と背中から）', fontsize=17, y=0.995)
def im(ax, p, box=None, t=''):
    i = Image.open(p).convert('RGB'); i = i.crop(box) if box else i; ax.imshow(i); ax.axis('off'); ax.set_title(t, fontsize=13)
for j, (p, t) in enumerate([('prop22/close_rib_now.png', '今（すき間 中央値 1.05 mm）'), ('prop22/close_rib_C.png', '案 C: 付け根を椎骨の縁に付ける（0.05 mm）'), ('prop22/close_rib_D.png', '案 D: 付け根を背側へ 1 mm 上げ、椎骨へ 0.3 mm 差し込む（0.03 mm）')]):
    im(fig.add_axes([0.005 + j * 0.2, 0.5, 0.195, 0.45]), p, (0, 0, 800, 800), t)
im(fig.add_axes([0.61, 0.5, 0.2, 0.45]), R06, (2900, 1150, 3500, 1750), '参考: 写真 06（肋骨は椎骨の横から出て、\n斜めに下りる）')
for j, (p, t) in enumerate([('next/new_ribs', '今'), ('prop22/shot_rib_D', '案 D')]):
    im(fig.add_axes([0.005 + j * 0.2, 0.02, 0.095, 0.45]), p + '_side.png', (100, 0, 800, 956), t + '（横）')
    im(fig.add_axes([0.105 + j * 0.2, 0.02, 0.095, 0.45]), p + '_dorsal.png', (150, 0, 650, 956), t + '（背中から）')
ax = fig.add_axes([0.42, 0.02, 0.57, 0.45]); ax.axis('off')
ax.text(0, 1, '''作り方（rib_roots.py の socket）
・案 A（記録 21 の胸郭の拡大を、付け根から 5 mm で 0 に戻す）のあとで、付け根（体軸に最も近い 3% の点の重心）を
  背側へ 1 mm 上げた点に最も近い椎骨の表面へ寄せ、さらに椎骨の中へ 0.3 mm 入れる
・付け根から 6 mm のあいだで、動かす量をなめらかに 1 → 0 にする（その先の肋骨と胴の幅は記録 21 のまま）
・動かした量 中央値 1.32 mm、最大 3.80 mm（41 本）。椎骨とのすき間 中央値 0.03 mm、最大 0.06 mm

見え方
・横から: 今と案 C は、平らに切れた肋骨の端が椎骨の列の横に並ぶ。案 D は端が椎骨の列の中に入り、
  肋骨が椎骨から出て斜めに下りるように見える（写真 06 に近い）
・背中から: 付け根が椎骨の側面に寄り、背骨の両脇のすき間が無くなる

決めると次に起きること
・案 D で本番の骨を作り直す（trunk_widen.py の付け根の扱い 5 mm → rib_roots.py socket）。膜・臓器・glb を作り直し、
  検査と色の比を確かめる。手足は記録 23 の案 B（本番に入れているところ）と一緒に作り直せる
・残ること: 肋骨の端が平らな管の切り口のまま（椎骨の中に隠れる）。肋骨 1 本ごとの太さと曲がりは記録 8 のまま\n・下の段の案 D は、手足を記録 23 の案 B の向きで書き出した（今とは手足の向きが違う。膜は手足の重みで動かした下見）''', va='top', fontsize=13.5)
fig.savefig('prop22/sheet_ribD.png'); print('saved')

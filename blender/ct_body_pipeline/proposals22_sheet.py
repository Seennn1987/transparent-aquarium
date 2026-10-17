"""記録 22 の案（肋骨の付け根、手足の向き）を、参考と同じ向きで並べる（2026-10-17）。作業フォルダで実行する。
  python ../../ct_body_pipeline/proposals22_sheet.py → prop22/sheet_ribs.png、prop22/sheet_limbs.png"""
import json
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
F = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
font_manager.fontManager.addfont(F); plt.rcParams['font.family'] = font_manager.FontProperties(fname=F).get_name()
R06 = '../../../docs/references/chameleon/06-lightbox-calyptratus-2.jpg'; R01 = '../../../docs/references/chameleon/01-user-jar-diaphonized.jpg'


def im(ax, path, box=None, title='', fs=12):
    i = Image.open(path).convert('RGB'); i = i.crop(box) if box else i
    ax.imshow(i); ax.axis('off'); ax.set_title(title, fontsize=fs)


def note(ax, t, fs=12.5): ax.axis('off'); ax.text(0, 1, t, va='top', fontsize=fs)


# ---- 肋骨 ----
fig = plt.figure(figsize=(26, 19), dpi=70)
fig.suptitle('案: 肋骨の付け根（標本ページを胴の後ろ半分に寄って撮った。上: 横、下: 背中から）', fontsize=18, y=0.995)
cols = [('next/prev_ribs', '記録 21 の前\n', '中央値 0.49・1 mm 超 9 本'), ('next/new_ribs', '今\n', '中央値 1.05・1 mm 超 22 本'),
        ('prop22/shot_rib_A', '案 A: 拡大を\n付け根で 0 に', '中央値 0.49・1 mm 超 9 本'),
        ('prop22/shot_rib_B', '案 B: A ＋ 付け根を\nCT の位置へ', '中央値 0.07・1 mm 超 9 本\n（最大 5.8 mm）'),
        ('prop22/shot_rib_C', '案 C: A ＋ 付け根を\n椎骨に付ける', '中央値 0.05・最大 0.09 mm')]
for j, (p, t, g) in enumerate(cols):
    im(fig.add_axes([0.005 + j * 0.155, 0.53, 0.15, 0.42]), p + '_side.png', (100, 0, 800, 956), f'{t}\nすき間 {g}', 12)
    im(fig.add_axes([0.005 + j * 0.155, 0.08, 0.15, 0.42]), p + '_dorsal.png', (150, 0, 650, 956), '', 12)
im(fig.add_axes([0.785, 0.55, 0.21, 0.4]), R06, (2300, 950, 3500, 1900), '参考: 写真 06（肋骨は椎骨から出る）', 12)
note(fig.add_axes([0.785, 0.02, 0.21, 0.5]), '''決めると次に起きること
選んだ案で骨のデータを作り直し
（trunk_widen.py に付け根の扱いを
足す。B・C は rib_roots.py）、膜・
臓器・glb を作り直して検査する。
胴の幅（記録 21 の 0.30）は変わらない
（動かすのは付け根から 5 mm まで）

案 A: 記録 21 の拡大で開いた分だけ
  戻す。記録 8 からの 0.5 mm の下がり
  と、肋骨 18〜21 のすき間（2.5〜3.2
  mm）は残る
案 B: 付け根を CT の元の位置へ。CT の
  付け根が今の椎骨と合わない肋骨が
  あり、すき間が 5.8 mm に広がるもの
  がある
案 C: どの肋骨も椎骨に付く（すき間
  0.1 mm 以下）。付け根から 5 mm の
  あいだで向きが少し変わる

すき間 = 肋骨の点と、骨組みの親の
椎骨の点の最短距離 [mm]

注意: C でも、横から見ると椎骨の列と
肋骨の始まりのあいだの帯は残る。
肋骨の付け根から約 2 mm が体の真横
（見る人の方）へまっすぐ出ていて、
横からは点にしか見えないため。
写真 06 の肋骨は、椎骨から斜め後ろ
下へ下りるのが横から見える。帯を
消すには、付け根の向きを変える案 D
（付け根から後ろ下へ下ろす）が要る。
D はまだ絵にしていない''')
fig.savefig('prop22/sheet_ribs.png'); plt.close(fig)

# ---- 手足 ----
A = json.load(open('prop22/limb_angles.json'))
def tab(k):
    a = A[k]; return '\n'.join(f"{n}: 下へ {v['下']:.0f}° 前へ {v['前']:.0f}° 外へ {v['外']:.0f}° 曲がり {v['曲がり']:.0f}°" for n, v in a.items())
fig = plt.figure(figsize=(26, 34), dpi=65)
fig.suptitle('案: 手足の向き（どれも実際の標本ページ。上から: 写真 06 の向き、写真 01 の向き（色 01）、前肢を正面から、後肢を後ろから）', fontsize=18, y=0.997)
rows = [('photo06', [('fix21/new_photo06.png', None)] + [(f'prop22/shot_limb_{l}_photo06.png', None) for l in 'ABC'], (R06, (1500, 900, 4800, 2600))),
        ('01', [('fix21/new_01.png', (100, 0, 800, 956))] + [(f'prop22/shot_limb_{l}_01.png', (100, 0, 800, 956)) for l in 'ABC'], (R01, (100, 40, 447, 447))),
        ('fore', [('next/new_fore_front.png', (0, 100, 800, 700))] + [(f'prop22/shot_limb_{l}_fore_front.png', (0, 100, 800, 700)) for l in 'ABC'], None),
        ('hind', [('next/new_hind_back.png', (0, 100, 800, 700))] + [(f'prop22/shot_limb_{l}_hind_back.png', (0, 100, 800, 700)) for l in 'ABC'], None)]
titles = ['今', '案 A: 写真 01 から解いた左右の\n向きを平均して鏡にそろえる', '案 B: 文献の構え（大腿は前へ 60°・\n下へ 20°、膝 約 120°。前肢は仮）', '案 C: 写真 01 の横から見た角（A）\nのまま、外へ開く角だけ B']
H = [0.19, 0.2, 0.13, 0.13]; Y = [0.785, 0.565, 0.415, 0.265]
for i, (key, items, ref) in enumerate(rows):
    if ref: im(fig.add_axes([0.005, Y[i], 0.19, H[i]]), ref[0], ref[1], '参考: 写真 06' if key == 'photo06' else '参考: 写真 01（透かし入り）', 12)
    for j, (p, box) in enumerate(items):
        if key == 'photo06': box = (60, 250, 780, 700)
        im(fig.add_axes([0.2 + j * 0.2, Y[i], 0.195, H[i]]), p, box, titles[j] if i == 0 else '', 12)
for j, k in enumerate(['今', '案 A', '案 B', '案 C']):
    note(fig.add_axes([0.2 + j * 0.2, 0.13, 0.195, 0.12]), '上腕・大腿の向き（f = 前肢、h = 後肢）\n' + tab(k), 11)
note(fig.add_axes([0.005, 0.005, 0.99, 0.12]), '''決めると次に起きること: 選んだ案の向きを rig_chameleon_ct.py の POSE_JAR に書き、展示の姿勢（pose_jar.npz）を Blender で出し直して、膜・臓器・glb を作り直す（膜は
姿勢に合わせて作るので、手足の付け根の膜も作り直される）。CH_Hover の手足の揺れはそのまま。決める前に本番の形は変えない。
・案 A: 左右がそろう。写真 01 の見え方に近いが、後肢の大腿は下へ 71° で、文献（13〜28°）より下を向く。前肢の肘の曲がりは 60°
・案 B: 文献の後肢（Higham & Jayne 2004, J Exp Biol 207:233）に合う。前肢は文献が無く仮。写真 01 の見え方からは離れる
・案 C: 写真 01 の横からの角を保ち、奥行きだけ B。大腿は下へ 59°
この絵は、今の骨の形（記録 21）に手足の向きだけ変えた下見。膜は骨組みの重みで動かした（本番では作り直す）''', 13)
fig.savefig('prop22/sheet_limbs.png'); plt.close(fig); print('saved')

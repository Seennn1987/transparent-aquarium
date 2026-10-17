"""記録 25 の案（③ 目、④ 喉の舌骨、⑤ かぶとの輪の内側の膜）を、参考と同じ向きで並べる（2026-10-17）。作業フォルダで実行する。
  → ../p25/sheet_25.png"""
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
F = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
font_manager.fontManager.addfont(F); plt.rcParams['font.family'] = font_manager.FontProperties(fname=F).get_name()
R06 = '../../../docs/references/chameleon/06-lightbox-calyptratus-2.jpg'; R01 = '../../../docs/references/chameleon/01-user-jar-diaphonized.jpg'
Q = '../p25/'
def im(ax, p, box=None, t=''):
    i = Image.open(p).convert('RGB'); i = i.crop(box) if box else i; ax.imshow(i); ax.axis('off'); ax.set_title(t, fontsize=12)
def note(ax, t, fs=12): ax.axis('off'); ax.text(0, 1, t, va='top', fontsize=fs)
fig = plt.figure(figsize=(26, 33), dpi=65)
fig.suptitle('③ 目・④ 喉の舌骨・⑤ かぶとの輪の内側の膜の案（どれも実際の標本ページ）', fontsize=19, y=0.997)
# ③
W = 0.165
im(fig.add_axes([0.005, 0.77, W, 0.2]), R01, (150, 290, 340, 447), '参考: 写真 01 の頭')
for j, (n, t) in enumerate([('now', '今'), ('A', '案 A: 眼球を眼窩の穴の重心へ寄せ、\n半径 4.26 → 5.02 mm（濃さは通り道の比）'), ('B', '案 B: 位置と大きさは今のまま、\n目の色を半分の濃さに'), ('C', '案 C: A ＋ B')]):
    im(fig.add_axes([0.005 + (j + 1) * (W + 0.005), 0.77, W, 0.2]), f'p25/eye_{n}_01.png', (240, 690, 560, 956), t)
note(fig.add_axes([0.005, 0.69, 0.99, 0.07]), '''③ 目: 眼窩の穴（横から写した頭骨の像の穴。左は眼の中の輪の骨を除いた）は楕円で、半径 左 4.15×5.64 mm・右 4.83×6.25 mm。眼球は半径 4.26 mm で、
長い方向に 1.4〜2 mm のすき間（白い三日月）があり、中心も穴の重心から 0.4〜0.8 mm ずれていた。案 A・C は面積の同じ円の半径（左右の平均 5.02 mm）にし、重心へ寄せる。
決めると次に起きること: eyes.json の中心と半径を直し、頭の膜・眼の臓器を作り直す。色 01 の目の濃さを当て直す（写真 01 の目の輪）''')
# ④
im(fig.add_axes([0.005, 0.47, W, 0.2]), R06, (3500, 1500, 4700, 2350), '参考: 写真 06 の頭と喉（喉の水色）')
for j, (n, t) in enumerate([('now', '今（舌骨 1.45 倍）'), ('hy10', '案 A: 舌骨 1.0 倍（頭骨だけ 1.45 倍）'), ('hy12', '案 B: 舌骨 1.2 倍')]):
    im(fig.add_axes([0.005 + (j + 1) * (W + 0.005), 0.47, W, 0.2]), Q + f's_{n}_photo06.png', (480, 330, 800, 620), t)
    im(fig.add_axes([0.005 + (j + 1) * (W + 0.005), 0.30, W, 0.16]), Q + f's_{n}_front.png', (100, 100, 700, 800), t + '（頭の先から）')
note(fig.add_axes([0.68, 0.30, 0.31, 0.37]), '''④ 喉の舌骨
肩の前（肩–股関節を 1 として −0.2〜−0.1）の喉の深さ（背腹）:
  今 0.451、舌骨 1.0 倍 0.381、1.2 倍 0.410
左右の幅は 0.286 でどの案も同じ。
訂正: 記録 22 で「舌骨を 1.45 倍にしたので喉・頸が太い（幅）」と
書いたが、舌骨で変わるのは喉の深さだった。幅が広いのは、
1.45 倍にした頭骨の後ろ（顎の付け根のあたり）が頸に重なる
ため（直すなら頭の大きさの話になる）

見え方: 舌骨 1.0 倍では、下あごの下に見えていた青い舌の芯
（舌骨の軟骨）があごの内側へ短く引っ込む。写真 06 では喉の
水色はあごの後ろ下に見える

決めると次に起きること: head_scale.py の舌骨の倍率を変えて、
膜・臓器・glb を作り直し、色 06 の喉の軟骨の濃さを当て直す''', 12)
# ⑤
im(fig.add_axes([0.005, 0.04, W, 0.24]), R06, (3850, 1350, 4450, 2050), '参考: 写真 06 のかぶと（輪の内側は白い）')
for j, (n, t) in enumerate([('now', '今（頭の膜が輪の穴を埋める）'), ('casque', '案 A: 横から写した頭の像で、\nかぶとの輪の穴を埋めない')]):
    im(fig.add_axes([0.005 + (j + 1) * (W + 0.005), 0.04, W, 0.24]), Q + f's_{n}_casque.png', (100, 100, 700, 800), t)
note(fig.add_axes([0.52, 0.04, 0.47, 0.24]), '''⑤ かぶとの輪の内側の膜
頭の膜は、横・上・前から写した頭骨の像（穴を埋め、2 mm のすき間を閉じる）の外へ出さない作り
（skinbody.py）。案 A は、横の像のうち、眼を含まない 4 mm² より大きい穴（かぶとの輪の穴）を
埋めない（CASQUE_OPEN=1）。
見え方: 輪の内側の上の方が白く抜ける。縁から 2 mm ほどは、すき間を閉じる処理のため膜が残る
（全部抜くには閉じる幅を輪のところだけ小さくする。次の手）

決めると次に起きること: skinbody.py の既定を CASQUE_OPEN=1 にして膜を作り直す。骨から 1.5 mm
より外の膜（右から 169 mm²）は減る見込み

この図の ④・⑤ は、膜を作り直した下見（作業フォルダの p25/ に案ごとに作った）。③ は眼の臓器を
glb の上で動かし、色はページの設定で試した''', 12)
fig.savefig(Q + 'sheet_25.png'); print('saved')

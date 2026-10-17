"""記録 28 の案（⑥ 手・足の指の束を開く）を、参考と同じ向きで並べる（2026-10-17）。作業フォルダで実行する。 → ../p28/sheet_28.png"""
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
F = '/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc'
font_manager.fontManager.addfont(F); plt.rcParams['font.family'] = font_manager.FontProperties(fname=F).get_name()
R06 = '../../../docs/references/chameleon/06-lightbox-calyptratus-2.jpg'; R01 = '../../../docs/references/chameleon/01-user-jar-diaphonized.jpg'
Q = '../p28/'
def im(ax, p, box=None, t=''):
    i = Image.open(p).convert('RGB'); i = i.crop(box) if box else i; ax.imshow(i); ax.axis('off'); ax.set_title(t, fontsize=12)
fig = plt.figure(figsize=(26, 30), dpi=65)
fig.suptitle('⑥ 手・足の指の束を開く案（実際の標本ページ。CT の手・足は 2 つの束が指先でくっついて閉じた輪になっていた）', fontsize=18, y=0.997)
im(fig.add_axes([0.005, 0.74, 0.16, 0.21]), R06, (2600, 2200, 3200, 2800), '参考: 写真 06 の前肢の手')
im(fig.add_axes([0.005, 0.51, 0.16, 0.21]), R06, (1700, 1600, 2300, 2200), '参考: 写真 06 の後肢の足')
im(fig.add_axes([0.005, 0.27, 0.16, 0.22]), R01, (200, 90, 340, 320), '参考: 写真 01 の手足')
cols = [('now', '今（閉じた輪）'), ('open20', '案 A: 片側 20° 開く'), ('open35', '案 B: 片側 35° 開く')]
rows = [('hand_v', '手（腹側から）', 0.74), ('foot_v', '左足（腹側から）', 0.51), ('photo06', '写真 06 の向き', 0.27)]
for j, (n, t) in enumerate(cols):
    for (v, rt, y) in rows:
        box = (40, 250, 790, 700) if v == 'photo06' else None
        im(fig.add_axes([0.17 + j * 0.275, y, 0.27, 0.21 if v != 'photo06' else 0.22]), Q + f'h_{n}_{v}.png', box, f'{t}　{rt}')
ax = fig.add_axes([0.005, 0.01, 0.99, 0.24]); ax.axis('off')
ax.text(0, 1, '''作り方（digits_open.py。骨の形は CT のまま、束を回すだけ）
・手・足の骨（骨組みでは 1 本の骨）のいちばん大きい塊を主成分に分ける: 第 1 = 手首から指先、輪は第 1・第 2 の面にある
・束の分かれ目（輪の穴が始まる所）を軸に、2 つの束を輪の面の中で互いに離れる向きへ回す。手根の側 1.5 mm から指先側 1.0 mm で回す量を 0 → 1 に
・束の割り当て: 分かれ目より先で第 2 主成分が ±0.6 mm を超える頂点はその符号、残り（くっついた指先など）は面に沿って近い方
・指先どうしの距離（案 B）: 左手 1.6 → 11.0 mm、右手 1.0 → 9.1 mm、左足 2.2 → 11.4 mm。右足はもともと輪になっておらず束が開いていたので動かさない
・膜を作り直した下見。検査: 穴 0、骨のはみ出し 0\n・気になる点: 左足（2 段目）は、開くと束の一部が平らな棒を並べたように見える（足の輪は手ほど平らな面に乗っていないためと読む）。足は開かず手だけ開く選び方もできる

決めると次に起きること: 選んだ角度で骨のデータ（chameleon_body_ct.npz）に digits_open.py を足し、膜・臓器・glb を作り直して、色の比を確かめる
（手足の組織が変わるので色 01 は少し動く）。指 1 本ずつの曲がり（関節ごと）は、CT で指の骨どうしがくっついて 1 つの面になっているので今回は変えない''', va='top', fontsize=14)
fig.savefig(Q + 'sheet_28.png'); print('saved')

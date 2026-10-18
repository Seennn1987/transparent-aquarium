"""記録 30 の案の 1 枚: 参考（写真 08・06）と、今・案 A〜E の後ろ足を同じ向きで並べる。
  cd blender/private/work/p30 && python ../../../ct_body_pipeline/proposals30_sheet.py <出力.png>
z_<案>_<向き>.png は shoot_close.sh が撮る。"""
import sys
from PIL import Image, ImageDraw, ImageFont

out = sys.argv[1]
REF = '../../../../docs/references/chameleon/'
F = ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc', 22)
f2 = ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc', 17)
CASES = [('now', '今の版', '足の膜 1.12 mm'),
         ('A', 'A 開く', '左足の束を片側 35°'),
         ('B', 'B 薄く', '膜を手と同じ 0.73 mm'),
         ('C', 'C 開く＋薄く', ''),
         ('D', 'D 開く＋分ける', '束のあいだに切れ込み'),
         ('E', 'E 開く＋薄く＋分ける', '')]
VIEWS = [('hR', '左から（左の後ろ足が手前）', (40, 160, 640, 720)),
         ('hL', '右から（右の後ろ足が手前）', (100, 160, 700, 720)),
         ('hLb', '腹側から 左の後ろ足', (260, 60, 800, 620)),
         ('hR06', '色 06・左から', (40, 160, 640, 720))]
CW, CH = 300, 280
W = 230 + CW * len(CASES); H = 130 + 330 + CH * len(VIEWS) + 50
sheet = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(sheet)
d.text((16, 12), '後ろ足の膜の案（色 01 は膜の青 3 倍、色 06 は膜 3 倍で撮影）', font=F, fill='black')
# 参考
r08 = Image.open(REF + '08-live-calyptratus-male-lateral.jpg'); s = 1.08
r08 = r08.crop((int(1100 * s), int(820 * s), int(1400 * s), int(1030 * s))); r08.thumbnail((420, 300))
r06 = Image.open(REF + '06-lightbox-calyptratus-2.jpg').crop((1759, 1680, 1969, 1870)); r06 = r06.resize((330, 300))
y0 = 60
sheet.paste(r08, (230, y0)); d.text((230, y0 + r08.height + 4), '参考 写真 08: 生きた雄の後ろ足。', font=f2, fill='#333'); d.text((230, y0 + r08.height + 26), '2 つの細い束が枝を挟む', font=f2, fill='#333')
x6 = 230 + r08.width + 30
sheet.paste(r06, (x6, y0)); d.text((x6, y0 + 304), '参考 写真 06: 透明標本の後ろ足の先', font=f2, fill='#333')
yt = y0 + 340
for j, (c, t, sub) in enumerate(CASES):
    x = 230 + j * CW
    d.text((x + 8, yt), t, font=F, fill='black'); d.text((x + 8, yt + 30), sub, font=f2, fill='#555')
for i, (v, label, box) in enumerate(VIEWS):
    y = yt + 60 + i * CH
    d.text((10, y + CH // 2 - 30), label[:8], font=f2, fill='black'); d.text((10, y + CH // 2 - 6), label[8:], font=f2, fill='black')
    for j, (c, _, _) in enumerate(CASES):
        try: im = Image.open(f'z_{c}_{v}.png').convert('RGB').crop(box)
        except FileNotFoundError: continue
        im.thumbnail((CW - 6, CH - 6)); sheet.paste(im, (230 + j * CW, y))
d.text((16, H - 34), '写真 06: Brianwray26, CC BY-SA 4.0。写真 08: Geoff, CC BY-SA 3.0（Wikimedia Commons）', font=f2, fill='#555')
sheet.save(out); print(out, sheet.size)

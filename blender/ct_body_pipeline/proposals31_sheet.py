"""記録 31 の案の 1 枚: 本物（Diaz & Trainor 2015 図 1 B・C）と、今・R1・R2 の後ろ足（ページの絵と、Blender で膜だけ不透明に描いた絵）。
  cd blender/private/work/p31 && python ../../../ct_body_pipeline/proposals31_sheet.py <本物の図の切り抜き.png> <出力.png>"""
import sys
from PIL import Image, ImageDraw, ImageFont

ref_p, out = sys.argv[1:3]
F = ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc', 22)
f2 = ImageFont.truetype('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc', 17)
CASES = [('now', '今の版', '足の膜 1.12 mm、指は 1 つの袋'), ('R1', 'R1 開く＋指ごと＋爪', '左足の束を片側 35°'), ('R2', 'R2 開かない＋指ごと＋爪', '束の向きは今のまま')]
PAGE = [('hR', '左から', (40, 160, 640, 720)), ('hL', '右から', (100, 160, 700, 720)), ('hLb', '腹側から 左足', (260, 60, 800, 620)), ('hR06', '色 06・左から', (40, 160, 640, 720))]
BL = [('hL_foot_c', 'Blender 左足'), ('hR_foot_a', 'Blender 右足')]
CW, CH = 380, 340
W = 170 + CW * len(CASES); H = 600 + CH * (len(PAGE) + len(BL)) + 120
sheet = Image.new('RGB', (W, H), 'white'); d = ImageDraw.Draw(sheet)
d.text((16, 12), '後ろ足の指と爪の案（色 01 は膜の青 3 倍。爪の鞘の色は仮の吸光度 5・9・18）', font=F, fill='black')
ref = Image.open(ref_p).convert('RGB'); ref = ref.resize((ref.width * 2, ref.height * 2), Image.LANCZOS)
sheet.paste(ref, (170, 50))
d.text((170, 50 + ref.height + 6), '本物: 生きたエボシカメレオン（Diaz & Trainor 2015 図 1 B 手・C 足、CC BY 4.0）。束の中の指は皮膚でつながり、', font=f2, fill='#333')
d.text((170, 50 + ref.height + 28), '指先は 1 本ずつ分かれ、爪は皮膚の外に出る', font=f2, fill='#333')
yt = 50 + ref.height + 70
for j, (c, t, sub) in enumerate(CASES):
    x = 170 + j * CW; d.text((x + 6, yt), t, font=F, fill='black'); d.text((x + 6, yt + 30), sub, font=f2, fill='#555')
y = yt + 64
rows = [(f'z_{{c}}_{v}.png', label, box) for v, label, box in PAGE] + [(f'lk_{{c}}_skin_{v}.png', label, None) for v, label in BL]
for tmpl, label, box in rows:
    d.text((10, y + CH // 2 - 12), label, font=f2, fill='black')
    for j, (c, _, _) in enumerate(CASES):
        try:
            im = Image.open(tmpl.format(c=c)).convert('RGB')
        except FileNotFoundError:
            d.text((170 + j * CW + 10, y + CH // 2), '（今の版は Blender で描いていない）' if 'lk_' in tmpl else '（無し）', font=f2, fill='#999'); continue
        if box: im = im.crop(box)
        im.thumbnail((CW - 8, CH - 8)); sheet.paste(im, (170 + j * CW, y))
    y += CH
d.text((16, y + 14), 'ページの絵: chameleon.html?view=photo06&still=1&skin=3。Blender の絵: 膜だけ不透明、爪の鞘は黄（blender_look_feet.py）', font=f2, fill='#555')
sheet.crop((0, 0, W, y + 50)).save(out); print(out)

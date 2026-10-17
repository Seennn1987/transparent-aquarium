"""
メンダコ 手順 0: 計画書 第 3 節の「姿勢・器・色・殻の形」を決めてもらうための、案ごとの絵を並べた 1 枚を作る。

  .venv/bin/python -I blender/mendako/step0_options_sheet.py

出力: docs/mendako/step0_options.jpg
使う画像（出典は docs/references/mendako/SOURCES.md）:
  - 参考の図と写真: docs/references/mendako/、docs/references/chameleon/05-lightbox-calyptratus-1.jpg
  - 実際の標本ページ（ギャラリー）の撮影: docs/mendako/page_gallery_jar_2026-10-17.jpg（index.html?tune=0）、
    page_gallery_dish_2026-10-17.jpg（index.html?specimen=hammerhead&tune=0）。1400×1050、手元の Chrome
色の案の見本は、次の画素の色を、同じ画像の背景で割った通し光で塗る（7×7〜13×13 の中央値）:
  - イカの外套の脇 (688, 470) = (90, 152, 166)、ひれ (650, 410) = (166, 187, 179)、腕 (702, 600) = (27, 117, 155)、
    背景 (600, 470) = (203, 201, 190)。page_gallery_jar の画素
  - カメレオンの肋骨のあいだの膜 (2760, 1800) = (189, 193, 176)、写真の外の背景 (1500, 1000) = (212, 218, 223)。
    05-lightbox-calyptratus-1.jpg の画素
見本の部品の位置: 外形は原記載 図 2 の輪郭（step0 の測定と同じ切り出し・しきい値）。眼の中心とひれは図 2 で測った点、
殻はひれと同じ前後の高さ（Meyer 1906 本文「ひれと同じ高さ」）に長さ 横幅の 0.18（原記載 9〜11 mm ÷ 55 mm）。
頭の軟骨・鰓・内臓は、形をまだ作っていないので描かない。
"""

import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as nd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(ROOT, "docs", "references", "mendako")
OUTDIR = os.path.join(ROOT, "docs", "mendako")
FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FONT_B = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"

TILE_W, TILE_H = 640, 400
LABEL_W = 420
CAP_H = 150
GAP = 16


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def fit(im, w=TILE_W, h=TILE_H, bg=(255, 255, 255)):
    im = im.convert("RGB")
    s = min(w / im.width, h / im.height)
    im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
    out = Image.new("RGB", (w, h), bg)
    out.paste(im, ((w - im.width) // 2, (h - im.height) // 2))
    return out


def crop(path, box):
    return Image.open(path).convert("RGB").crop(box)


def wrap(draw, text, fnt, width):
    lines = []
    for para in text.split("\n"):
        line = ""
        for ch in para:
            if draw.textlength(line + ch, font=fnt) > width:
                lines.append(line)
                line = ch
            else:
                line += ch
        lines.append(line)
    return lines


def text_block(draw, xy, text, fnt, width, fill=(30, 30, 30), gap=6):
    x, y = xy
    for line in wrap(draw, text, fnt, width):
        draw.text((x, y), line, font=fnt, fill=fill)
        y += fnt.size + gap
    return y


# ------------------------------------------------------------------
# 原記載 図 2 の輪郭（step0_ratio_marks と同じ取り方）
# ------------------------------------------------------------------
def dorsal_mask():
    a = np.asarray(Image.open(os.path.join(REF, "01-ijima-ikeda-1895-pl33.jpg")).convert("L")).astype(float)
    a = a[560:1560, 60:980]
    paper = np.percentile(a, 95)
    m = nd.gaussian_filter(a, 2) < paper - 10
    m = nd.binary_closing(m, iterations=6)
    m = nd.binary_fill_holes(m)
    m = nd.binary_opening(m, iterations=2)
    lab, n = nd.label(m)
    k = 1 + int(np.argmax(nd.sum(m, lab, range(1, n + 1))))
    return lab == k


def transmit(rgb, bg):
    return np.clip(np.array(rgb, float) / np.array(bg, float), 0.02, 1.0)


def sketch(body_t, cart_t, fin_t):
    """背から見た見本。body_t などは、参考の画素の厚みでの通し光（0..1）"""
    m = dorsal_mask()
    h, w = m.shape
    # 厚み: 縁で 0、中心で 1。参考の画素は外套の脇・肋骨のあいだ（中くらいの厚み）とみて、厚み 0.5 で一致させる
    d = nd.distance_transform_edt(m)
    thick = (d / d.max()) ** 0.7
    absb = -np.log(body_t) / 0.5
    img = np.ones((h, w, 3))
    img *= np.exp(-thick[..., None] * absb[None, None, :])
    img[~m] = 1.0

    def paint(mask, t):
        img[mask] = img[mask] * t

    yy, xx = np.mgrid[0:h, 0:w]
    W = 835.0
    # ひれ（図 2 の畳まれたひれ、左 x 265–322・右 x 540–600、y 525–555）
    for x0, x1 in [(265, 322), (540, 600)]:
        fm = (xx >= x0) & (xx <= x1) & (np.abs(yy - 540) <= 14)
        paint(fm, fin_t)
    # 殻（ひれと同じ高さ y 540、長さ 0.18 W、厚み 0.012 W）
    cx = (39 + 874) / 2
    L = 0.18 * W
    sm = (np.abs(xx - cx) <= L / 2) & (np.abs(yy - 548 - 0.0006 * (xx - cx) ** 2) <= 0.006 * W)
    paint(sm, cart_t)
    img = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    im = Image.fromarray(img)
    dr = ImageDraw.Draw(im)
    # 眼（中心は図 2 の三日月、径は 9 ÷ 55 の 0.16 W。色素が残るかは未確認なので輪郭だけ）
    r = 0.16 * W / 2
    for (ex, ey) in [(294, 449), (553, 465)]:
        dr.ellipse([ex - r, ey - r, ex + r, ey + r], outline=(110, 110, 110), width=3)
    return im


def container(kind):
    """器の横の断面の模式図。メンダコは B の姿勢（高さ ÷ 横幅 0.44、ひれ 0.69）を、壁から 0.12 空けた最大の大きさで置く"""
    if kind == "jar":
        D, H = 2 * (0.62 - 0.045), 2.40 - 0.26 - 0.10   # 内径、液の深さ（口の下 0.10 を液面とした概略）
    else:
        D, H = 2 * (1.0 - 0.012), 1.40 - 0.035           # 低い器（generate_specimen_dish.py）
    c = 0.12
    w = min(D - 2 * c, (H - 2 * c) / 0.44)
    S = min((TILE_W // 2 - 24) / D, (TILE_H - 90) / H)
    im = Image.new("RGB", (TILE_W // 2, TILE_H), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    ox, oy = (TILE_W // 2 - D * S) / 2, (TILE_H - H * S) / 2 + 10
    dr.rectangle([ox, oy, ox + D * S, oy + H * S], fill=(232, 240, 238), outline=(120, 150, 145), width=3)
    # 体: 下が平たく上が丸い。腕の膜は下の縁へ広がる
    cx, by = ox + D * S / 2, oy + H * S / 2 + 0.22 * w * S
    pts = []
    for i in range(41):
        t = np.pi * i / 40
        x = cx - np.cos(t) * w * S / 2
        y = by - np.sin(t) ** 1.6 * 0.44 * w * S
        pts.append((x, y))
    dr.polygon(pts, fill=(170, 205, 215), outline=(60, 110, 130))
    fw = 0.69 * w * S / 2
    for sgn in (-1, 1):
        dr.ellipse([cx + sgn * fw - 12, by - 0.36 * w * S - 22, cx + sgn * fw + 12, by - 0.36 * w * S + 22],
                   fill=(170, 205, 215), outline=(60, 110, 130))
    f = font(18)
    dr.text((8, 6), f"液の径 {D:.2f}・深さ {H:.2f}", font=f, fill=(60, 60, 60))
    dr.text((8, TILE_H - 28), f"体の横幅 {w:.2f}（内径の {w / D:.0%}）", font=f, fill=(60, 60, 60))
    return im


def pair(left, right):
    out = Image.new("RGB", (TILE_W, TILE_H), (255, 255, 255))
    out.paste(fit(left, TILE_W // 2, TILE_H), (0, 0))
    out.paste(fit(right, TILE_W // 2, TILE_H), (TILE_W // 2, 0))
    return out


def main():
    jar = os.path.join(OUTDIR, "page_gallery_jar_2026-10-17.jpg")
    dish = os.path.join(OUTDIR, "page_gallery_dish_2026-10-17.jpg")

    squid_bg = (203, 201, 190)
    A_body = transmit((90, 152, 166), squid_bg)
    A_fin = transmit((166, 187, 179), squid_bg)
    cart = transmit((27, 117, 155), squid_bg)
    B_body = transmit((189, 193, 176), (212, 218, 223))
    B_fin = np.sqrt(B_body)

    rows = [
        dict(
            title="1. 姿勢",
            note="決めると: この形で、上と横から見た外形の線を作り、線と直す量の図で承認をもらう（手順 A1）",
            options=[
                (fit(crop(os.path.join(REF, "01-ijima-ikeda-1895-pl33.jpg"), (520, 190, 1420, 520))),
                 "A 固定標本のように平たい円盤",
                 "高さ ÷ 横幅 0.25〜0.29。ひれは畳まれて小さい（横幅の 0.40）。原記載 図 1（横、原寸、PD）"),
                (fit(crop(os.path.join(REF, "05-sunshine2-live.jpg"), (600, 800, 3300, 2350))),
                 "B 生きて海底で休む形（おすすめ）",
                 "高さ ÷ 横幅 0.44。丸い頭に耳のようなひれが立つ（横幅の 0.69）。3 秒の見せ場になる。Totti, CC BY-SA 4.0"),
                (fit(crop(os.path.join(REF, "21-monterey-2014-1-swim.jpg"), (400, 800, 4000, 2950))),
                 "C 傘を下ろして浮く形",
                 "泳ぐときのパラシュート形。本種の写真は無く、同じ属の別の種（Monterey Bay Aquarium、CC BY-SA 2.0）"),
            ],
        ),
        dict(
            title="2. 器",
            note="決めると: 器の寸法から、メンダコの大きさと壁からの空き（0.12）を決める。器に入れるのは最後（手順 C）",
            options=[
                (pair(crop(jar, (470, 40, 930, 920)), container("jar")),
                 "A イカと同じ瓶（手順書の決まり）",
                 "断面はそのまま、大きさだけ合わせる。縦長の液に平たい体なので、上下に空きが大きい。左: 実際のギャラリー"),
                (pair(crop(dish, (420, 470, 980, 960)), container("dish")),
                 "B シュモクザメと同じ低い器（おすすめ）",
                 "蓋なし。上から傘とひれの形が見える。手順書 第 8 節に例外として足す。左: 実際のギャラリー（中はシュモクザメ）"),
            ],
        ),
        dict(
            title="3. 色",
            note="決めると: その色を目標に、標本ページの染まりの数を決める（手順 A4）。タコの透明標本の写真は見つかっていない",
            options=[
                (pair(sketch(A_body, cart, A_fin), crop(jar, (600, 330, 830, 640))),
                 "A イカと同じ空色（体の膜も青く染まる）",
                 "左: 原記載 図 2 の輪郭をイカのページの外套の脇・ひれの色で塗った見本。右: 実際のイカのページ"),
                (pair(sketch(B_body, cart, B_fin), crop(os.path.join(ROOT, "docs", "references", "chameleon",
                                                                       "05-lightbox-calyptratus-1.jpg"), (2450, 1550, 3150, 1950))),
                 "B 膜はほぼ無色、軟骨だけ青",
                 "左: 膜をカメレオンの透明標本の肋骨のあいだの色で、殻をイカの腕の青で塗った見本。右: その写真（Brianwray26, CC BY-SA 4.0。赤は骨）"),
            ],
        ),
        dict(
            title="4. 殻の形",
            note="決めると: その形で殻（ひれの支え）を作り、ひれの付け根を両端に付ける（手順 A2）。上から見ると 3 つとも横の棒",
            options=[
                (fit(crop(os.path.join(REF, "01-ijima-ikeda-1895-pl33.jpg"), (90, 1620, 640, 1900))),
                 "A 真っすぐな横の棒（原記載 図 6）",
                 "若い雄、2 倍、上から。左半分だけ描かれている。c = 殻、f = ひれ、m = 筋。PD"),
                (fit(crop(os.path.join(REF, "10-meyer1906-taf11-left.jpg"), (420, 3700, 2600, 3980))),
                 "B 浅い弓形（Meyer 1906 図 5）",
                 "成熟した雄、4 倍、上から。幅約 35 mm・長さ約 2.5 mm、前と下へ開く。両端が細い（tab = ひれの付く所）。PD"),
                (fit(crop(os.path.join(REF, "30-verhoeff2024-fig12.png"), (1160, 300, 2040, 860))),
                 "C 鞍と下へ反る翼（Sasaki 1929）",
                 "成熟した雄（F 上から・G 後ろから）と完模式標本（D・E）。Verhoeff 2024 図 12 の描き直し、CC BY 4.0。後ろから見た曲がりを描いたのはこれだけ"),
            ],
        ),
    ]

    ncol = 3
    W = LABEL_W + ncol * (TILE_W + GAP) + GAP
    head_h = 120
    row_h = TILE_H + CAP_H + 40
    H = head_h + len(rows) * row_h + 70
    sheet = Image.new("RGB", (W, H), (248, 247, 244))
    dr = ImageDraw.Draw(sheet)
    dr.text((GAP, 18), "メンダコ 手順 0: 決めてもらうこと（2026-10-17）", font=font(40, True), fill=(20, 20, 20))
    dr.text((GAP, 72), "計画書 第 3 節。各行で案を 1 つ選ぶ。数は計画書 第 2.3 節の画素の測定。おすすめは理由のあるものだけ付けた",
            font=font(22), fill=(70, 70, 70))
    y = head_h
    for row in rows:
        dr.line([(GAP, y - 8), (W - GAP, y - 8)], fill=(200, 200, 200), width=2)
        dr.text((GAP, y + 4), row["title"], font=font(36, True), fill=(20, 20, 20))
        text_block(dr, (GAP, y + 60), row["note"], font(21), LABEL_W - 2 * GAP, fill=(60, 60, 60))
        for i, (img, cap1, cap2) in enumerate(row["options"]):
            x = LABEL_W + i * (TILE_W + GAP)
            sheet.paste(img, (x, y))
            dr.rectangle([x, y, x + TILE_W, y + TILE_H], outline=(190, 190, 190), width=1)
            yy = text_block(dr, (x + 4, y + TILE_H + 10), cap1, font(25, True), TILE_W - 8, fill=(20, 20, 20))
            text_block(dr, (x + 4, yy + 2), cap2, font(19), TILE_W - 8, fill=(70, 70, 70), gap=4)
        y += row_h
    dr.text((GAP, H - 50), "画像の出典: docs/references/mendako/SOURCES.md。色の見本の部品は外形・眼・ひれ・殻だけ（頭の軟骨・鰓・内臓は形をまだ作っていない）",
            font=font(19), fill=(90, 90, 90))
    out = os.path.join(OUTDIR, "step0_options.jpg")
    sheet.save(out, quality=88)
    print(out, sheet.size)


if __name__ == "__main__":
    main()

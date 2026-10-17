"""
メンダコ 手順 A1: 外形の線（上・正面・横）を参考から作り、ならし、参考と重ねた図を作る。

  .venv/bin/python -I blender/mendako/a1_outline.py

出力:
  docs/mendako/a1_outline_lines.json   ならした線（横幅 = 1 で割った値）
  docs/mendako/a1_outline.jpg          参考・取り出した輪郭・ならした線を重ねた図と、直す量

座標: 上から見た線は、前（第 1 腕のあいだ）が上。正面の線は、横幅の中央が 0、左右の端が ±1、高さは横幅で割る。
  glTF に載せるときは +Y が背（上）、+Z が前、+X が体の左（手順 A3 で接続する前にもう一度書く）。

参考（docs/references/mendako/SOURCES.md）と、手で読んだ点（方眼、±20 px）:
  上: 原記載 図 2（原寸、若い雄）は全体、Meyer 1906 Taf. XI 図 1（約 4/5、成熟した雄）は左半分を鏡に映す
      （右側は紙が綴じ目へ暗くなり、輪郭が漏れるため）。Meyer の正中線は x = 1300（第 1 腕のあいだの切れ込みと外套の開口 M）
  正面: 05-sunshine2-live.jpg と 07-sunshine4-live.jpg（生体、砂の上で休む姿勢 = 決定の姿勢 B）。
      体の左右の端と砂の高さ、ひれの範囲・眼は方眼で読んだ値（下の FRONT）。中心は両眼の中点。
      Sunshine2 のひれ（880〜1349）は最初 883〜1257 と読み、ひれの上の縁を頭に数えていた（2026-10-17 訂正）
  横: 生体の真横の写真は無い。案 a = 正面の線と同じ形、案 b = 原記載 図 1（横、固定）の厚みの分布を正面の高さに合わせたもの
"""

import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as nd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REF = os.path.join(ROOT, "docs", "references", "mendako")
OUT = os.path.join(ROOT, "docs", "mendako")
FONT = "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc"
FONT_B = "/System/Library/Fonts/ヒラギノ角ゴシック W6.ttc"

# 正面の写真で手で読んだ値（原寸の px）
FRONT = {
    "05-sunshine2-live.jpg": dict(xl=721, xr=3186, yb=1990, fins=[(880, 1349), (2342, 2688)],
                                 eyes=[(1555, 1133), (2317, 1145)]),
    "07-sunshine4-live.jpg": dict(xl=900, xr=3400, yb=1785, fins=[(1100, 1525), (2500, 2937)],
                                 eyes=[(1737, 1020), (2487, 987)]),
}
N_THETA = 360
HARMONICS = 12      # 上の線: 腕 8 本の膜の波（8 次）を残し、腕の先の鉤（細かい凹凸）は落とす
FRONT_BIN = 0.02    # 正面の線: |u| の区間の幅。区間ごとに 2 枚の点を平均し、点の無い区間（ひれの裏）は両隣をつなぐ
FRONT_SIGMA = 0.04  # そのあと、この幅（u）のガウスでならす


def font(size, bold=False):
    return ImageFont.truetype(FONT_B if bold else FONT, size)


def largest(m):
    lab, n = nd.label(m)
    k = 1 + int(np.argmax(nd.sum(m, lab, range(1, n + 1))))
    return lab == k


# ------------------------------------------------------------------
# 上から見た線
# ------------------------------------------------------------------
def ijima_dorsal():
    a = np.asarray(Image.open(os.path.join(REF, "01-ijima-ikeda-1895-pl33.jpg")).convert("L")).astype(float)
    x0, y0 = 60, 560
    a = a[y0:1560, x0:980]
    paper = np.percentile(a, 95)
    m = nd.gaussian_filter(a, 2) < paper - 10
    m = nd.binary_closing(m, iterations=6)
    m = largest(nd.binary_opening(nd.binary_fill_holes(m), iterations=2))
    return m, (x0, y0)


def meyer_dorsal():
    a = np.asarray(Image.open(os.path.join(REF, "10-meyer1906-taf11-left.jpg")).convert("RGB")).astype(float)
    x0, y0 = 300, 300
    a = a[y0:2200, x0:2120]
    paper = np.median(a[:150, :150].reshape(-1, 3), 0)
    d = np.sqrt(((nd.gaussian_filter(a, (3, 3, 0)) - paper) ** 2).sum(-1))
    m = d > 25
    m = nd.binary_closing(m, iterations=8)
    m = largest(nd.binary_opening(nd.binary_fill_holes(m), iterations=4))
    return m, (x0, y0)


def best_midline(m):
    """左右の鏡映がいちばん重なる縦の線（列）"""
    ys, xs = np.nonzero(m)
    best = None
    for c2 in range(2 * xs.min() + 40, 2 * xs.max() - 40, 2):   # c2 = 2 × 正中線の x
        mx = c2 - xs
        ok = (mx >= 0) & (mx < m.shape[1])
        iou = m[ys[ok], mx[ok]].sum() / len(xs)
        if best is None or iou > best[0]:
            best = (iou, c2 / 2)
    return best[1], best[0]


def radial(m, cx, cy, half, side=None):
    """中心 (cx, cy) から角度ごとに、いちばん外の輪郭までの距離 ÷ half。θ = 0 が前（上）、右回り"""
    th = np.linspace(0, 2 * np.pi, N_THETA, endpoint=False)
    r = np.full(N_THETA, np.nan)
    rr = np.arange(0, 2.0 * half, 0.5)
    for i, t in enumerate(th):
        x = cx + np.sin(t) * rr
        y = cy - np.cos(t) * rr
        ok = (x >= 0) & (y >= 0) & (x < m.shape[1] - 1) & (y < m.shape[0] - 1)
        inside = np.zeros_like(rr, bool)
        inside[ok] = m[y[ok].astype(int), x[ok].astype(int)]
        if side == "left" and np.sin(t) > 0.02:
            continue
        if inside.any():
            r[i] = rr[np.nonzero(inside)[0].max()] / half
    return th, r


def symmetric(r):
    """左右の鏡映と平均。片側だけ（nan）のときはある側を使う"""
    mir = np.roll(r[::-1], 1)          # θ → −θ
    out = np.nanmean(np.vstack([r, mir]), 0)
    return out


def lowpass(r, k):
    f = np.fft.rfft(r)
    f[k + 1:] = 0
    return np.fft.irfft(f, len(r))


def dorsal_lines():
    res = {}
    m, off = ijima_dorsal()
    mid, iou = best_midline(m)
    ys, xs = np.nonzero(m)
    half = (xs.max() - xs.min()) / 2
    cy = (ys.min() + ys.max()) / 2
    th, r = radial(m, mid, cy, half)
    res["ijima"] = dict(mask=m, off=off, cx=mid, cy=cy, half=half, r=r, iou=iou)
    m2, off2 = meyer_dorsal()
    mid2 = 1300 - off2[0]
    ys2, xs2 = np.nonzero(m2[:, : int(mid2)])
    half2 = mid2 - xs2.min()
    cy2 = (ys2.min() + ys2.max()) / 2
    th, r2 = radial(m2, mid2, cy2, half2, side="left")
    res["meyer"] = dict(mask=m2, off=off2, cx=mid2, cy=cy2, half=half2, r=r2)
    rs = np.vstack([symmetric(res["ijima"]["r"]), symmetric(r2)])
    raw = np.nanmean(rs, 0)
    line = lowpass(raw, HARMONICS)
    return th, res, rs, raw, line


# ------------------------------------------------------------------
# 正面の線
# ------------------------------------------------------------------
def front_points(name, p):
    a = np.asarray(Image.open(os.path.join(REF, name)).convert("RGB")).astype(float)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    body = (r > 70) & (r - b > 25)
    body = nd.binary_closing(nd.binary_opening(body, iterations=3), iterations=5)
    body = nd.binary_fill_holes(largest(body))
    W = p["xr"] - p["xl"]
    xc = (p["eyes"][0][0] + p["eyes"][1][0]) / 2   # 体の正中 = 両眼の中点（左右の端の中点は体の向きでずれる）
    pts, fin_pts = [], []
    for x in range(p["xl"], p["xr"] + 1, 4):
        ys = np.nonzero(body[:, x])[0]
        if not len(ys):
            continue
        y = min(ys.min(), p["yb"])
        u, v = (x - xc) / (W / 2), (p["yb"] - y) / W
        if any(f0 <= x <= f1 for f0, f1 in p["fins"]):
            fin_pts.append((u, v))
        else:
            pts.append((u, v))
    return np.array(pts), np.array(fin_pts), a, (xc, W)


def fit_front(u, v):
    """左右を鏡に映した点 (|u|, v) から、0..1 の区間ごとの平均 → 空きをつなぐ → ならす。返すのは |u| の格子と v"""
    au = np.abs(u)
    edges = np.arange(0, 1 + FRONT_BIN, FRONT_BIN)
    mid = (edges[:-1] + edges[1:]) / 2
    val = np.full(len(mid), np.nan)
    for i in range(len(mid)):
        k = (au >= edges[i]) & (au < edges[i + 1])
        if k.any():
            val[i] = np.mean(v[k])
    ok = np.isfinite(val)
    val = np.interp(mid, mid[ok], val[ok])
    # 端は 0（膜の縁）、中央は鏡映でなめらかにつなぐ
    g = np.concatenate([val[::-1], val, [0.0] * 5])
    gx = np.concatenate([-mid[::-1], mid, 1 + FRONT_BIN * np.arange(1, 6)])
    sm = nd.gaussian_filter1d(g, FRONT_SIGMA / FRONT_BIN, mode="nearest")
    return gx, sm


def eval_front(c, u):
    gx, sm = c
    return np.interp(np.abs(u), gx, sm)


def front_lines():
    data = {}
    allu, allv = [], []
    for name, p in FRONT.items():
        pts, fins, img, (xc, W) = front_points(name, p)
        data[name] = dict(pts=pts, fins=fins, img=img, xc=xc, W=W, p=p)
        allu += list(pts[:, 0]) + list(-pts[:, 0])
        allv += list(pts[:, 1]) * 2
    c = fit_front(np.array(allu), np.array(allv))
    return data, c


# ------------------------------------------------------------------
# 横の線（案）
# ------------------------------------------------------------------
def ijima_side():
    a = np.asarray(Image.open(os.path.join(REF, "01-ijima-ikeda-1895-pl33.jpg")).convert("L")).astype(float)
    x0, y0 = 400, 150
    a = a[y0:620, x0:1500]
    paper = np.percentile(a, 95)
    m = nd.gaussian_filter(a, 2) < paper - 10
    m = largest(nd.binary_opening(nd.binary_fill_holes(nd.binary_closing(m, iterations=6)), iterations=2))
    ys, xs = np.nonzero(m)
    L = xs.max() - xs.min()
    u, t = [], []
    for x in range(xs.min(), xs.max() + 1, 3):
        c = np.nonzero(m[:, x])[0]
        u.append((x - xs.min()) / L * 2 - 1)
        t.append(c.max() - c.min())
    return np.array(u), np.array(t) / L, m, (x0, y0)


# ------------------------------------------------------------------
def main():
    th, dres, rs, raw, line = dorsal_lines()
    fdata, fc = front_lines()
    su, st, smask, soff = ijima_side()
    uu = np.linspace(-1, 1, 201)
    front_v = np.clip(eval_front(fc, uu), 0, None)
    H = float(front_v.max())
    # 横の案 b: 原記載 図 1 の厚みを、ならして正面の高さ H に合わせる
    stc = np.convolve(st, np.ones(15) / 15, mode="same")
    side_b = np.interp(uu, su, stc)
    side_b = side_b / side_b.max() * H

    # ひれ（正面）: 外の端 ÷ 横幅、上下の端は方眼で読む（第 2.3 節）
    fins = {}
    for name, d in fdata.items():
        p = d["p"]
        fins[name] = dict(outer=[(p["fins"][0][0] - d["xc"]) / (d["W"] / 2), (p["fins"][1][1] - d["xc"]) / (d["W"] / 2)])
    lines = dict(
        date="2026-10-17",
        note="横幅 = 1。上の線は中心からの距離 ÷ 横幅の半分（θ = 0 が前、右回り）。正面・横の線は u = −1..1、高さ ÷ 横幅",
        dorsal=dict(theta_deg=list(np.round(np.degrees(th), 2)), r=list(np.round(line, 4)), harmonics=HARMONICS),
        front=dict(u=list(np.round(uu, 3)), v=list(np.round(front_v, 4)), bin=FRONT_BIN, sigma=FRONT_SIGMA,
                   height_over_width=round(H, 4), fins_outer_u=fins),
        side_options=dict(a=list(np.round(front_v, 4)), b=list(np.round(side_b, 4))),
        midline_ijima_iou=round(float(dres["ijima"]["iou"]), 3),
    )
    with open(os.path.join(OUT, "a1_outline_lines.json"), "w", encoding="utf-8") as f:
        json.dump(lines, f, ensure_ascii=False, indent=1)

    # 直す量（ならした線 − 取り出した輪郭）
    dev_dorsal = [np.nanmax(np.abs(line - r)) for r in rs]
    dev_front = {}
    for name, d in fdata.items():
        pu = d["pts"][:, 0]
        dev_front[name] = float(np.max(np.abs(eval_front(fc, pu) - d["pts"][:, 1])))
        dev_front[name + ":p95"] = float(np.percentile(np.abs(eval_front(fc, pu) - d["pts"][:, 1]), 95))
    print("上の線: 正中線の重なり", round(float(dres["ijima"]["iou"]), 3), "直す量の最大（半幅比）", [round(float(x), 3) for x in dev_dorsal])
    print("正面: 高さ ÷ 横幅", round(H, 3), "直す量の最大（横幅比）", {k: round(v, 3) for k, v in dev_front.items()})
    sheet(th, dres, rs, raw, line, fdata, fc, uu, front_v, side_b, su, stc, H, dev_dorsal, dev_front)


def poly_on(draw, pts, color, width):
    draw.line([tuple(map(float, p)) for p in pts], fill=color, width=width)


def sheet(th, dres, rs, raw, line, fdata, fc, uu, front_v, side_b, su, stc, H, dev_dorsal, dev_front):
    TW, TH = 760, 600
    W = 3 * TW + 80
    Hh = 130 + 3 * (TH + 170) + 40
    out = Image.new("RGB", (W, Hh), (248, 247, 244))
    dr = ImageDraw.Draw(out)
    dr.text((20, 16), "メンダコ 手順 A1: 外形の線（2026-10-17）", font=font(40, True), fill=(20, 20, 20))
    dr.text((20, 70), "緑 = 参考から取り出した輪郭、赤 = ならした線（左右対称）、水色 = ならす前の平均。各行の右は横幅で割った重ね", font=font(22), fill=(60, 60, 60))

    def tile(img, x, y):
        img = img.convert("RGB")
        s = min(TW / img.width, TH / img.height)
        img = img.resize((int(img.width * s), int(img.height * s)), Image.LANCZOS)
        out.paste(img, (x + (TW - img.width) // 2, y + (TH - img.height) // 2))
        return s, x + (TW - img.width) // 2, y + (TH - img.height) // 2

    def caption(x, y, t1, t2):
        dr.text((x, y + TH + 10), t1, font=font(24, True), fill=(20, 20, 20))
        yy = y + TH + 46
        f = font(19)
        for para in t2.split("\n"):
            line = ""
            for ch in para:
                if dr.textlength(line + ch, font=f) > TW - 10:
                    dr.text((x, yy), line, font=f, fill=(70, 70, 70)); yy += 26; line = ch
                else:
                    line += ch
            dr.text((x, yy), line, font=f, fill=(70, 70, 70)); yy += 26

    # 行 1: 上
    y = 130
    for i, key in enumerate(["ijima", "meyer"]):
        d = dres[key]
        src = "01-ijima-ikeda-1895-pl33.jpg" if key == "ijima" else "10-meyer1906-taf11-left.jpg"
        ox, oy = d["off"]
        m = d["mask"]
        img = Image.open(os.path.join(REF, src)).convert("RGB").crop((ox, oy, ox + m.shape[1], oy + m.shape[0]))
        e = m ^ nd.binary_erosion(m, iterations=3)
        arr = np.asarray(img).copy()
        arr[e] = [0, 170, 0]
        img = Image.fromarray(arr)
        g = ImageDraw.Draw(img)
        pts = [(d["cx"] + np.sin(t) * rv * d["half"], d["cy"] - np.cos(t) * rv * d["half"]) for t, rv in zip(th, line)]
        poly_on(g, pts + [pts[0]], (220, 0, 0), 5)
        g.line([(d["cx"], 0), (d["cx"], m.shape[0])], fill=(0, 90, 220), width=2)
        tile(img, 20 + i * (TW + 20), y)
    caption(20, y, "上: 原記載 図 2（若い雄、原寸）", f"正中線は鏡映の重なりで探した（重なり {dres['ijima']['iou']:.2f}）。\n直す量の最大: 半幅の {dev_dorsal[0]:.2f}（腕の先の鉤を落とした所）")
    caption(40 + TW, y, "上: Meyer 1906 図 1（成熟した雄、約 4/5）", f"左半分だけ使う（右は紙の陰で輪郭が漏れる）。青 = 正中線 x 1300。\n直す量の最大: 半幅の {dev_dorsal[1]:.2f}")
    # 重ね（極座標を平面に）
    P = Image.new("RGB", (TW, TH), (255, 255, 255))
    g = ImageDraw.Draw(P)
    c, s = (TW / 2, TH / 2), TH * 0.42
    for r, col in zip(rs, [(0, 150, 0), (120, 180, 60)]):
        pts = [(c[0] + np.sin(t) * rv * s, c[1] - np.cos(t) * rv * s) for t, rv in zip(th, r) if np.isfinite(rv)]
        poly_on(g, pts, col, 2)
    pts = [(c[0] + np.sin(t) * rv * s, c[1] - np.cos(t) * rv * s) for t, rv in zip(th, raw)]
    poly_on(g, pts + [pts[0]], (80, 170, 220), 2)
    pts = [(c[0] + np.sin(t) * rv * s, c[1] - np.cos(t) * rv * s) for t, rv in zip(th, line)]
    poly_on(g, pts + [pts[0]], (220, 0, 0), 4)
    g.text((10, 8), "前", font=font(22), fill=(60, 60, 60))
    tile(P, 60 + 2 * TW, y)
    caption(60 + 2 * TW, y, "上の線（横幅の半分 = 1 にそろえた重ね）", f"緑 2 本を左右対称にして平均し、{HARMONICS} 次までの波でならした。\n膜の 8 つの波は残し、腕の先の鉤は落とした")

    # 行 2: 正面
    y = 130 + TH + 170
    for i, (name, d) in enumerate(fdata.items()):
        p = d["p"]
        img = Image.fromarray(d["img"].astype(np.uint8))
        g = ImageDraw.Draw(img)
        gp = [(d["xc"] + u * d["W"] / 2, p["yb"] - v * d["W"]) for u, v in d["pts"]]
        for q in gp:
            g.ellipse([q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5], fill=(0, 200, 0))
        fp = [(d["xc"] + u * d["W"] / 2, p["yb"] - v * d["W"]) for u, v in zip(uu, front_v)]
        poly_on(g, fp, (230, 0, 0), 10)
        g.line([(p["xl"], p["yb"]), (p["xr"], p["yb"])], fill=(255, 255, 0), width=4)
        for u, v in d["fins"]:
            q = (d["xc"] + u * d["W"] / 2, p["yb"] - v * d["W"])
            g.ellipse([q[0] - 5, q[1] - 5, q[0] + 5, q[1] + 5], fill=(80, 160, 255))
        img = img.crop((p["xl"] - 150, p["yb"] - int(0.6 * d["W"]), p["xr"] + 150, p["yb"] + 250))
        tile(img, 20 + i * (TW + 20), y)
        nm = "Sunshine2" if "2" in name else "Sunshine4"
        caption(20 + i * (TW + 20), y, f"正面: {nm}（生体、Totti, CC BY-SA 4.0）",
                f"黄 = 砂の高さ（左右の端 x {p['xl']}〜{p['xr']}、y {p['yb']}）。青の点 = ひれ（線の当てはめから外した）\n直す量: 最大 横幅の {dev_front[name]:.3f}、95% の点で {dev_front[name + ":p95"]:.3f} 以内")
    P = Image.new("RGB", (TW, TH), (255, 255, 255))
    g = ImageDraw.Draw(P)
    sx, sy, oy0 = TW * 0.45, TW * 0.9, TH - 80
    for (name, d), col in zip(fdata.items(), [(0, 150, 0), (120, 180, 60)]):
        for u, v in d["pts"]:
            g.ellipse([TW / 2 + u * sx - 2, oy0 - v * sy - 2, TW / 2 + u * sx + 2, oy0 - v * sy + 2], fill=col)
        for u, v in d["fins"]:
            g.ellipse([TW / 2 + u * sx - 2, oy0 - v * sy - 2, TW / 2 + u * sx + 2, oy0 - v * sy + 2], fill=(150, 190, 255))
    poly_on(g, [(TW / 2 + u * sx, oy0 - v * sy) for u, v in zip(uu, front_v)], (220, 0, 0), 4)
    g.line([(TW / 2 - sx, oy0), (TW / 2 + sx, oy0)], fill=(150, 150, 150), width=1)
    tile(P, 60 + 2 * TW, y)
    caption(60 + 2 * TW, y, f"正面の線（横幅 = 1）。高さ ÷ 横幅 {H:.2f}",
            f"緑 = 2 枚の体の点を左右に鏡映し、|u| の {FRONT_BIN} ごとに平均。点の無い所（ひれの裏）はつなぎ、{FRONT_SIGMA} でならした。薄い青 = ひれの点（外した。ひれは別の部品）")

    # 行 3: 横（案）
    y = 130 + 2 * (TH + 170)
    m = None
    img = Image.open(os.path.join(REF, "01-ijima-ikeda-1895-pl33.jpg")).convert("RGB").crop((400, 150, 1500, 620))
    tile(img, 20, y)
    caption(20, y, "横: 原記載 図 1（固定、原寸）", "左が前とみた（図 9 の正中の断面と同じ向き）。\n案 b はこの厚みの分布を使う")
    img = Image.open(os.path.join(REF, "04-sunshine1-live.jpg")).convert("RGB").crop((300, 900, 3900, 2900))
    tile(img, 40 + TW, y)
    caption(40 + TW, y, "斜め横: Sunshine1（生体、Totti, CC BY-SA 4.0）", "真横の生体写真は無い。斜めから見ると、眼のある頭の丸みが\nいちばん高く、後ろへなだらかに下がる")
    P = Image.new("RGB", (TW, TH), (255, 255, 255))
    g = ImageDraw.Draw(P)
    poly_on(g, [(TW / 2 + u * sx, oy0 - v * sy) for u, v in zip(uu, front_v)], (220, 0, 0), 4)
    poly_on(g, [(TW / 2 + u * sx, oy0 - v * sy) for u, v in zip(uu, side_b)], (240, 140, 0), 4)
    g.line([(TW / 2 - sx, oy0), (TW / 2 + sx, oy0)], fill=(150, 150, 150), width=1)
    g.text((10, 8), "← 前", font=font(22), fill=(60, 60, 60))
    g.text((TW - 230, 8), "赤 = 案 a、橙 = 案 b", font=font(22), fill=(60, 60, 60))
    tile(P, 60 + 2 * TW, y)
    caption(60 + 2 * TW, y, "横の線の案（横幅 = 1）", "a: 正面の線と同じ形（前後対称）\nb: 原記載 図 1 の厚みの分布を、高さだけ正面に合わせた（いちばん高い所が後ろ寄り）")
    out.save(os.path.join(OUT, "a1_outline.jpg"), quality=88)
    print(os.path.join(OUT, "a1_outline.jpg"), out.size)


if __name__ == "__main__":
    main()

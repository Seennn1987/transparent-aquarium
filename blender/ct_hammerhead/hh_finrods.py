"""シロシュモクザメ: 第 2 背びれ・臀びれ・腹びれの軟骨を、図と写真から棒と板で作る（2026-10-18）。

プロデューサー「CTを原本にしない方が良いのでは？もっと良い事例を探してみて」→「その案で進めてください」。
この 3 つのひれの軟骨は、CT（骨の閾値 250）には細い棒が途切れ途切れにしか写らず、面にすると粒になった
（計画書「ひれの軟骨を図と写真から作る」）。形は次の見本から決める:
  臀びれ・第 2 背びれ: シロシュモクザメの骨格標本（ピサ大学自然史博物館 P 415、Stefano Puzzuoli、CC BY-SA 4.0、
    docs/references/hammerhead/ref1_pisa_sphyrna_zygaena_skeleton_lateral.jpg）の臀びれ。1600 px に縮めた写真の x 530〜730・y 700〜830 を
    切り出した画素（以下「臀びれの切り抜き」）で: 付け根の上に土台の板、そこから細い棒が平行に並ぶ。棒の間隔 約 12 px（x 230〜390 に 13 本）、
    傾き 体軸から 32°（棒の 1 本 x 370・y 172 → x 310・y 210）、棒の先はひれの深さの 0.55（付け根 y 172、ひれの縁 y 250、棒の先 y 215）。
    第 2 背びれは骨格標本に付いていないので、同じつくりとする（Compagno 1988 の背びれ・臀びれの骨格: 土台の軟骨と平行な放射軟骨）
  腹びれ: ウチワシュモクザメの透明標本（© Adam Summers、Smithsonian の記事。手元で見比べるだけ、docs/references/hammerhead/ref_summers_bonnethead_cleared_stained.jpg）と、
    ツノザメ類の腹びれの骨格図（Reynolds 1897『The Vertebrate Skeleton』Fig. 8、パブリックドメイン）。腰帯の横棒、内側の縁に沿って後ろへ伸びる長い棒（基鰭軟骨）、
    そこから外へ平行に並ぶ 2 節の棒（Summers の写真で片側 約 17 本、ひれの縁の近くまで届く）
面はどれも閉じた箱（8 頂点・12 面）の集まり。棒どうし・板と棒は重ねない（重なると通り道を 2 回数える）。
"""
import numpy as np


def box(p0, p1, w_dir, w, t_dir, t):
    """p0 → p1 の中心線の箱。w_dir の向きに幅 w、t_dir の向きに厚さ t（どれも同じ単位）。外向きの面の (V, F)"""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    a = np.asarray(w_dir, float) * (w / 2); b = np.asarray(t_dir, float) * (t / 2)
    V = np.array([p0 - a - b, p0 + a - b, p0 + a + b, p0 - a + b, p1 - a - b, p1 + a - b, p1 + a + b, p1 - a + b])
    F = np.array([[0, 2, 1], [0, 3, 2], [4, 5, 6], [4, 6, 7], [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5], [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7]])
    c = V.mean(0); n = np.cross(V[F[0, 1]] - V[F[0, 0]], V[F[0, 2]] - V[F[0, 0]])
    if np.dot(n, V[F[0]].mean(0) - c) < 0: F = F[:, ::-1]   # 外向きにそろえる（a・b・中心線の向きの組で回りが逆になる）
    return V, F


def merge(parts):
    Vs, Fs, n = [], [], 0
    for V, F in parts: Vs.append(V); Fs.append(F + n); n += len(V)
    return (np.concatenate(Vs), np.concatenate(Fs)) if Vs else (np.zeros((0, 3)), np.zeros((0, 3), int))


def inside(poly, x, y):
    """多角形の中か（偶奇の規則）。poly は (N, 2)"""
    P = np.asarray(poly, float); x1, y1 = P[:, 0], P[:, 1]; x2, y2 = np.roll(x1, -1), np.roll(y1, -1)
    x = np.atleast_1d(x).astype(float); y = np.atleast_1d(y).astype(float); r = np.zeros(len(x), bool)
    for a, b, c, d in zip(x1, y1, x2, y2):
        if b == d: continue
        r ^= ((b > y) != (d > y)) & (x < (c - a) * (y - b) / (d - b) + a)
    return r


def clip_ray(poly, p, d, length, margin, step=0.2):
    """p から d の向きに length まで進み、多角形の内側 margin を保てる所までの長さ"""
    s = np.arange(0, length + step, step); q = p[None] + s[:, None] * d[None]
    nrm = np.array([-d[1], d[0]])
    ok = inside(poly, q[:, 0], q[:, 1]) & inside(poly, *(q + margin * d).T) & inside(poly, *(q + margin * nrm).T) & inside(poly, *(q - margin * nrm).T)
    bad = np.nonzero(~ok)[0]
    return float(s[bad[0] - 1]) if len(bad) and bad[0] > 0 else (0.0 if len(bad) else float(length))


# 臀びれの切り抜きで測った値
ROD_SPACING_FRAC = 12 / 195     # 棒の間隔 ÷ 付け根の長さ（付け根 x 205〜400 = 195 px）
ROD_ANGLE_DEG = 32.0            # 体軸からの傾き（ひれの外・後ろへ）
ROD_REACH = 0.55                # 棒の先の深さ ÷ ひれの深さ


def median_fin(fd, line_of_x, TL_MM, rod_w=1.0, rod_t=1.6, plate_t=2.0):   # 棒の幅は間隔の 1/3（臀びれの切り抜きで 棒 約 4 px・間隔 12 px）
    """背びれ・臀びれ（hh_fins.FINS の 1 つ）の軟骨。Blender の座標の mm（x 前後・y 左右・z 背腹）。line_of_x: 体の線の Blender z（mm）"""
    Lb = (fd["i"] - fd["o"]) * TL_MM; Hm = fd["H"] * TL_MM; side = fd["side"]; out = -side   # out: ひれの外への z の向き（背 +1、腹 −1）
    x0 = fd["o"] * TL_MM
    poly = [(x0 + s * Lb, line_of_x(x0 + s * Lb) + out * (h * Hm if h > 0 else -4.0)) for s, h in fd["poly"]]
    parts = []
    # 土台の板: 付け根の 0.05〜0.95、体の線の 3 mm 内から 1.5 mm 外まで
    for s0, s1 in [(0.05, 0.95)]:
        xa, xb = x0 + s0 * Lb, x0 + s1 * Lb
        za, zb = line_of_x(xa), line_of_x(xb)
        zc = lambda z: z + out * (-0.75)
        parts.append(box((xa, 0, zc(za)), (xb, 0, zc(zb)), (0, 0, 1), 4.5, (0, 1, 0), plate_t))
    # 棒: 板の外の縁（体の線 + 1.5 mm）から、体軸に 32° で後ろ・外へ。先は深さ ROD_REACH × H か、外形の内側 1 mm まで
    th = np.radians(ROD_ANGLE_DEG); d = np.array([np.cos(th), out * np.sin(th)])
    n = max(3, int(round(1 / ROD_SPACING_FRAC)))
    for k in range(n):
        xs = x0 + (0.04 + 0.9 * k / (n - 1)) * Lb
        p = np.array([xs, line_of_x(xs) + out * 1.6])
        L = min(ROD_REACH * Hm / np.sin(th), 3 * Hm)
        L = clip_ray(poly, p, d, L, 1.0)
        if L < 2: continue
        q = p + d * L
        parts.append(box((p[0], 0, p[1]), (q[0], 0, q[1]), (-d[1], 0, d[0]), rod_w, (0, 1, 0), rod_t))
    return merge(parts), poly

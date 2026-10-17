"""振り返り 第 9 節の点検の図: 今の膜の外形を、背中（背腹 X 線）・正面（胴の断面）・横（写真 06）の参考と、肩–股関節の長さで重ねる（2026-10-17）。

作業フォルダ（blender/private/work/）で、inspect_outline.py と page_check/views.py・project.py のあとに実行する。
  python ../../ct_body_pipeline/inspect_sheet.py → inspect/outline_sheet.png

参考（どれも git に入れない。出典は図の中に書く）
- 背中: Melero Jurado 2020（UAB 博士論文、CC）図 5.1.4・5.1.2。生きたエボシカメレオンを鎮静して腹ばい（背腹 X 線）
- 正面: 同 図 5.3.2（死後の断面、B〜E）、図 5.3.4（生体の CT、腹ばい、B・C）
- 横: docs/references/chameleon/06-lightbox-calyptratus-2.jpg（透明標本、CC BY-SA 4.0 Brianwray26）
画素の読み（原寸の画像の座標）は下の LM_* に書いた。
"""
import json
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

font_manager.fontManager.addfont('/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc')
plt.rcParams['font.family'] = font_manager.FontProperties(fname='/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc').get_name()

I = 'inspect/'
REF06 = '../../../docs/references/chameleon/06-lightbox-calyptratus-2.jpg'
# 画素の読み（どの画像の、どこ）
LM_P46 = dict(snout=(405, 42), occiput=(310, 395), shoulder_y=420, hip_y=1185)      # 図 5.1.4（608×1317）
LM_P44 = dict(shoulder_y=375, hip_y=1085)                                          # 図 5.1.2（697×1304）。吻端は切れている
LM_06 = dict(snout=(4571, 2146), occiput=(4000, 1880), shoulder=(3370, 1910), hip=(2010, 1340))   # 写真 06（5184×3456）


def xray_edges(fn, y0, y1, xl, xr):
    """背腹 X 線の行ごとの体の左右の縁（輝度 > 25 の、窓 [xl, xr] の中のいちばん外の画素）。"""
    from scipy.ndimage import uniform_filter1d
    a = np.asarray(Image.open(fn).convert('L')).astype(float)
    out = []
    for y in range(y0, y1, 5):
        r = uniform_filter1d(a[y - 2:y + 3].mean(0), 5)[xl:xr]
        xs = np.where(r > 25)[0]
        if len(xs): out.append((y, xs[0] + xl, xs[-1] + xl))
    return np.array(out, float)


prof = np.load(I + 'outline_profile.npz'); rows = prof['rows']
px = json.load(open(I + 'landmarks_px.json'))
fig = plt.figure(figsize=(22, 25), dpi=80)
fig.suptitle('エボシカメレオン 外形の点検（振り返り 第 9 節、2026-10-17）　長さはすべて「肩–股関節」（上腕骨と大腿骨の付け根の間）を 1 とした', fontsize=17, y=0.995)

# ---- 1 段目: 背中 ----
e46 = xray_edges(I + 'melero_p46_0.jpeg', 600, 965, 120, 480)     # 前肢（y < 600）と腿（y > 965）が重ならない行だけ
e44 = xray_edges(I + 'melero_p44_0.jpeg', 600, 965, 150, 480)
ax = fig.add_axes([0.01, 0.70, 0.17, 0.27]); ax.imshow(Image.open(I + 'melero_p46_0.jpeg'), cmap='gray'); ax.axis('off')
for yy, c in ((LM_P46['shoulder_y'], 'c'), (LM_P46['hip_y'], 'y')): ax.axhline(yy, color=c, lw=1)
ax.plot(e46[:, 1], e46[:, 0], 'r-', lw=1); ax.plot(e46[:, 2], e46[:, 0], 'r-', lw=1)
ax.set_title('参考: 生体の背腹 X 線\nMelero Jurado 2020 図 5.1.4\n水色 = 肩、黄 = 股関節、赤 = 読んだ体の縁', fontsize=11)
im = Image.open(I + '../shots/cur_dorsal.png'); ax = fig.add_axes([0.18, 0.70, 0.17, 0.27]); ax.imshow(im); ax.axis('off')
d = px['dorsal']; ax.axhline(d['shoulder'][1], color='c', lw=1); ax.axhline(d['hip'][1], color='y', lw=1)
ax.set_xlim(170, 630); ax.set_ylim(700, 30)
ax.set_title('今: 標本ページを背中から\n（展示の姿勢。頭を上に）', fontsize=11)
ax = fig.add_axes([0.40, 0.72, 0.27, 0.24])
SH46 = LM_P46['hip_y'] - LM_P46['shoulder_y']; SH44 = LM_P44['hip_y'] - LM_P44['shoulder_y']
for e, lm, SHx, lab, c in ((e46, LM_P46, SH46, 'X 線 図 5.1.4', 'tab:red'), (e44, LM_P44, SH44, 'X 線 図 5.1.2', 'tab:orange')):
    t = (e[:, 0] - lm['shoulder_y']) / SHx; mid = (e[:, 1] + e[:, 2]) / 2
    ax.plot(t, (e[:, 1] - mid) / SHx, color=c, lw=2, label=lab); ax.plot(t, (e[:, 2] - mid) / SHx, color=c, lw=2)
ax.plot(rows[:, 0], rows[:, 3], 'b-', lw=2, label='今の膜（左右の端）'); ax.plot(rows[:, 0], rows[:, 4], 'b-', lw=2)
ax.axvline(0, color='c', lw=1); ax.axvline(1, color='y', lw=1); ax.set_xlim(-0.65, 1.1); ax.set_ylim(-0.3, 0.3); ax.set_aspect('equal')
ax.set_xlabel('肩からの位置（肩–股関節 = 1）'); ax.set_ylabel('背骨からの左右'); ax.legend(loc='lower left', fontsize=10); ax.grid(alpha=0.3)
ax.set_title('背中からの外形を重ねた（胴の長さでそろえる）', fontsize=12)
ax = fig.add_axes([0.70, 0.72, 0.29, 0.24]); ax.axis('off')
w46 = (e46[:, 2] - e46[:, 1]).max() / SH46; w44 = (e44[:, 2] - e44[:, 1]).max() / SH44; wm = rows[(rows[:, 0] > 0) & (rows[:, 0] < 1), 1].max()
sk46 = np.hypot(*np.subtract(LM_P46['snout'], LM_P46['occiput'])) / SH46
sk06 = np.hypot(*np.subtract(LM_06['snout'], LM_06['occiput'])) / np.hypot(*np.subtract(LM_06['shoulder'], LM_06['hip']))
txt = ('胴の最大の幅 ÷ 肩–股関節\n'
       f'  X 線 図 5.1.4  {w46:.2f}（{(e46[:, 2] - e46[:, 1]).max():.0f} px ÷ {SH46} px）\n'
       f'  X 線 図 5.1.2  {w44:.2f}（{(e44[:, 2] - e44[:, 1]).max():.0f} px ÷ {SH44} px）\n'
       f'  今の膜          {wm:.2f}（{wm * prof["SH"] / prof["k"]:.1f} mm ÷ {prof["SH"] / prof["k"]:.1f} mm）\n\n'
       '頭骨（吻端〜後頭）÷ 肩–股関節（直線）\n'
       f'  X 線 図 5.1.4  {sk46:.2f}（吻端 y 42〜後頭 y 395 ÷ 肩 y 420〜股 y 1185）\n'
       f'  写真 06          {sk06:.2f}（吻端 (4571,2146)〜後頭 (4000,1880) ÷\n                       肩 (3370,1910)〜股 (2010,1340)）\n'
       '  今のモデル      0.30（23.4 mm ÷ 78.9 mm）\n\n'
       f'胴の幅 ÷ 頭骨: X 線 図 5.1.4 {w46 / sk46:.2f}、今 {wm / 0.266:.2f}\n\n' '読み方: 頭骨の長さで割ると、今の胴の幅は X 線に近い\n（前の担当はこの比で合わせた。記録 8）。胴の長さで割ると\n今の胴は X 線の約半分の幅。今のモデルは、頭が胴に比べて\n小さい（または胴が長い）。写真 06 と X 線は頭骨 0.43〜0.46 で\nそろう。X 線は鎮静して腹ばいの生体なので、幅は広めに出る')
ax.text(0, 1, txt, va='top', fontsize=11.5, family=plt.rcParams['font.family'])

# ---- 2 段目: 正面（胴の断面） ----
R = np.load('skin_posed.npz')
exec(open('../../ct_body_pipeline/inspect_outline.py').read().split('edges =')[0].replace("sys.argv[1] if len(sys.argv) > 1 else 'skin_posed.npz'", "'skin_posed.npz'"))


def model_section(pos, half=0.015):
    m = (s > pos - half) & (s < pos + half)
    from scipy.spatial import ConvexHull
    q = np.stack([lat[m], dv[m]], 1); h = ConvexHull(q); return q[np.r_[h.vertices, h.vertices[0]]]


p79 = Image.open(I + 'melero_p79_0.jpeg'); p81 = Image.open(I + 'melero_p81_0.jpeg')
crops = [('死後の断面 B\n（肺・肝臓、位置 約 0.25）', p79.crop((40, 395, 265, 830)), 0.25),
         ('死後の断面 C\n（胆嚢、約 0.39）', p79.crop((365, 395, 655, 830)), 0.39),
         ('死後の断面 D\n（脂肪体、約 0.90）', p79.crop((770, 395, 985, 840)), 0.90),
         ('生体 CT 腹ばい B\n（胆嚢、約 0.4）', p81.crop((60, 420, 420, 810)), 0.40),
         ('生体 CT 腹ばい C\n（脂肪体、約 0.85）', p81.crop((490, 420, 800, 810)), 0.85)]
hw_ref = ['2.00', '1.48', '2.14', '約 1.1', '約 1.3']
for j, ((title, cim, pos), hw) in enumerate(zip(crops, hw_ref)):
    ax = fig.add_axes([0.01 + j * 0.105, 0.47, 0.10, 0.19]); ax.imshow(cim); ax.axis('off'); ax.set_title(title + f'\n高さ/幅 {hw}', fontsize=10)
for j, pos in enumerate([0.25, 0.39, 0.90]):
    ax = fig.add_axes([0.54 + j * 0.105, 0.47, 0.10, 0.19]); q = model_section(pos)
    ax.fill(q[:, 0], q[:, 1], color='#d9c9a0', ec='b'); ax.set_aspect('equal'); ax.set_xlim(-0.25, 0.25); ax.set_ylim(-0.45, 0.2)
    hw = np.ptp(q[:, 1]) / np.ptp(q[:, 0]); ax.set_title(f'今の膜の断面\n位置 {pos:.2f}\n高さ/幅 {hw:.2f}', fontsize=10); ax.tick_params(labelsize=7); ax.grid(alpha=0.3)
ax = fig.add_axes([0.86, 0.47, 0.13, 0.19]); ax.axis('off')
ax.text(0, 1, '正面（断面）\n\n参考は Melero Jurado 2020\n図 5.3.2（死後、エボシ）\n図 5.3.4（生体 CT、エボシ、\n腹ばいで肺がふくらむ）\n\n位置は CT の矢状断の線から\n目で読んだ（± 0.05）\n\n今の膜は死後の断面に近い\n縦長。胴の後ろ（0.9）は\n死後の 2.1 より横に広い 1.7', va='top', fontsize=10.5)

# ---- 3 段目: 横 ----
r06 = Image.open(REF06)
ax = fig.add_axes([0.01, 0.05, 0.47, 0.33]); ax.imshow(r06.crop((1500, 700, 4800, 2700))); ax.axis('off')
for k_, c in (('snout', 'm'), ('occiput', 'g'), ('shoulder', 'c'), ('hip', 'y')):
    x_, y_ = LM_06[k_]; ax.plot(x_ - 1500, y_ - 700, 'o', color=c, ms=10, mec='k')
ax.set_title('参考: 写真 06（透明標本、CC BY-SA 4.0 Brianwray26）　桃 = 吻端、緑 = 後頭、水色 = 肩、黄 = 股関節', fontsize=11)
# 同じ縮尺: 写真 06 の肩–股関節（直線）とページのそれを同じ長さにして切り出す
c06 = np.hypot(*np.subtract(LM_06['shoulder'], LM_06['hip'])); pp = px['photo06']; cpg = np.hypot(*np.subtract(pp['shoulder'], pp['hip']))
f_ = cpg / c06; cx0 = pp['shoulder'][0] - (LM_06['shoulder'][0] - 1500) * f_; cy0 = pp['shoulder'][1] - (LM_06['shoulder'][1] - 700) * f_
ax = fig.add_axes([0.50, 0.05, 0.47, 0.33]); ax.imshow(Image.open(I + '../shots/cur_photo06.png').crop((int(cx0), int(cy0), int(cx0 + 3300 * f_), int(cy0 + 2000 * f_)))); ax.axis('off')
for k_, c in (('snout', 'm'), ('occiput', 'g'), ('shoulder', 'c'), ('hip', 'y')):
    x_, y_ = pp[k_]; ax.plot(x_ - int(cx0), y_ - int(cy0), 'o', color=c, ms=10, mec='k')
ax.set_title(f'今: 標本ページ ?view=photo06（展示の姿勢）。肩–股関節を左と同じ長さにした\n頭骨 ÷ 肩–股関節: 写真 06 {sk06:.2f}、今 0.30', fontsize=11)
fig.savefig(I + 'outline_sheet.png')
print('saved', w46, w44, wm, sk46, sk06)

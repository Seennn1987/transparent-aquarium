# 胸郭の腹の深さを、生体の横向きの X 線（veterinaryradiology.net、4t2pms の画面写し）の腹の線に合わせる
#   X 線で測った値（2026-10-14、目測、仮）: 肩（上腕骨の頭、x = 335 px）→ 股（大腿骨の頭、x = 470 px）の位置 t で、
#     椎骨の列から腹の皮膚までの深さ ÷ 頭骨の長さ（吻端 → 後頭顆、72 px）
#     t:     0.19  0.33  0.48  0.63  0.78  0.93  1.00
#     深さ:  0.97  1.14  1.22  1.22  1.13  1.00  0.86
#   X 線では、腹側の肋骨（白い線）が腹の皮膚の近くまで写っている → 胸郭の腹の端を、皮膚の深さ − 膜の厚さ − 軟骨の半径にする
#   肋骨の向き（同じ X 線、ぼかしを引いて線を強めた図で 2〜3 本ずつ読んだ、仮）: 背側の部分は腹へ 1 進むごとに後ろへ 0.57、
#     腹側の部分は腹へ 1 進むごとに前へ 1.3（Williston 1925 の V 字の腹肋）。曲がり目は輪の上端から腹の端までの 0.54 の所
#   胸骨（2026-10-14 の 2 回目）: 前の肋骨の腹の端が肩より前（下あごの近く）まで伸び、喉の下に膜の板ができた。
#     前の肋骨は肩帯（烏口骨）のすぐ後ろの胸骨につながるとして:
#     - 腹の端の位置 u は、肩帯の腹の端の u（U_ST）より前へ出さない。肋骨 3 から 1 本ごとに STEP_ST ずつ後ろ（仮）。
#       前へ出る肋骨は、腹側の部分の前への向き（−1.3）を弱める
#     - t < 0.19（X 線で前肢に隠れて測れない所）の深さは、肩帯の腹の端の深さ（胸骨の腹面）から t = 0.19 の X 線の値へ直線で
#       （前の版は t = 0 を根拠なく 0.85 と置いていた）
#   腹側の肋骨は骨の色（写真 01 では腹の縁まで赤、X 線にも写る）にし、軟骨は正中の手前 1.2 mm だけ（RIB_CART_TIP、仮）
#   肋骨ごとに: 展示の姿勢で輪の腹の端の位置 u_b と深さを測り（ribbottom.py）、目標との差を ribmodel2 の深さ Dv に足す。くり返す
import numpy as np, json, os, subprocess
SK = 23.1; U0, UHIP = 9.5, 107.5
TT = [0.19, 0.33, 0.48, 0.63, 0.78, 0.93, 1.00]
RR = [0.97, 1.14, 1.22, 1.22, 1.13, 1.00, 0.86]
WALL = 0.6; CART_R = 0.25; STEP_ST = 2.0
# 肩帯の腹の端（展示の姿勢、体軸の枠）
gird = json.load(open('girdle_ventral.json'))
U_ST = float(np.mean([g[0] for g in gird.values()])); D_ST = float(np.max([g[1] for g in gird.values()]))
u19 = U0 + 0.19 * (UHIP - U0)
def target(u):
    if u >= u19: return float(np.interp((u - U0) / (UHIP - U0), TT, RR)) * SK - WALL - CART_R
    d19 = RR[0] * SK - WALL - CART_R
    return float(np.interp(u, [U_ST, u19], [D_ST, d19]))
print('sternum: u %.1f mm, depth %.1f mm; x-ray from u %.1f mm' % (U_ST, D_ST, u19))
env = dict(os.environ, RIB_SLOPES='0.57,-1.3,0.54', RIB_CART_TIP='1.2', RIB_IN=os.environ.get('RIB_SRC', 'chameleon_body_ct_v1_ribs.npz'), RIB_OUT='ribs_tmp.npz', DV_JSON='dv_override.json')
dv0 = json.load(open('dv_override_v1.json')) if os.path.exists('dv_override_v1.json') else {}
dv = {int(i): float(v[0] if isinstance(v, list) else v) for i, v in dv0.items()}
rv = {i: -1.3 for i in dv}
for it in range(12):
    json.dump({str(i): [dv[i], rv[i]] for i in dv}, open('dv_override.json', 'w'), indent=1)
    subprocess.run(['python3', 'ribmodel2.py'], env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['python3', 'hyoid_relabel.py', 'ribs_tmp.npz', 'ribs_tmp2.npz'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['python3', 'ribbottom.py', 'ribs_tmp2.npz'], check=True, stdout=subprocess.DEVNULL)
    rb = json.load(open('ribbottom.json'))
    err = []
    for i in sorted(dv):
        r = [rb[f'rib{i:02d}_{s}'] for s in 'LR' if f'rib{i:02d}_{s}' in rb]
        ub = np.mean([x[0] for x in r]); vb = np.mean([x[1] for x in r])
        umin = U_ST + STEP_ST * (i - 3)
        e = target(max(ub, umin)) - vb
        # 腹の端が胸骨より前: 腹側の部分の前への向きを弱める（腹側の部分の深さ ≈ 0.46 × 輪の深さ）
        if ub < umin - 0.1: rv[i] = min(rv[i] + (umin - ub) / max(0.46 * dv[i], 1.0), 0.0)
        err.append((i, ub, umin, vb, target(max(ub, umin)), e, rv[i])); dv[i] += e
    print('pass', it, 'max |depth error| %.2f mm, ribs ahead of the sternum %d' % (max(abs(x[5]) for x in err), sum(x[1] < x[2] - 0.1 for x in err)))
for i, ub, umin, vb, tg, e, r in err: print('rib %2d  bottom u %.1f (>= %.1f)  ventral %.1f  target %.1f  ventral slope %.2f' % (i, ub, umin, vb, tg, r))
json.dump({str(i): [dv[i], rv[i]] for i in dv}, open('dv_override.json', 'w'), indent=1)

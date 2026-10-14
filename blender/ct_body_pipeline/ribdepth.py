# 胸郭の腹の深さを、生体の横向きの X 線（veterinaryradiology.net、4t2pms の画面写し）の腹の線に合わせる
#   X 線で測った値（2026-10-14、目測、仮）: 肩（上腕骨の頭、x = 335 px）→ 股（大腿骨の頭、x = 470 px）の位置 t で、
#     椎骨の列から腹の皮膚までの深さ ÷ 頭骨の長さ（吻端 → 後頭顆、72 px）
#     t:     0.19  0.33  0.48  0.63  0.78  0.93  1.00
#     深さ:  0.97  1.14  1.22  1.22  1.13  1.00  0.86     （t = 0 は前肢に隠れて測れないので 0.85 と置いた、仮）
#   X 線では、腹側の肋骨（白い線）が腹の皮膚の近くまで写っている → 胸郭の腹の端を、皮膚の深さ − 膜の厚さ − 軟骨の半径にする
#   肋骨の向き（同じ X 線、ぼかしを引いて線を強めた図で 2〜3 本ずつ読んだ、仮）: 背側の部分は腹へ 1 進むごとに後ろへ 0.57、
#     腹側の部分は腹へ 1 進むごとに前へ 1.3（Williston 1925 の V 字の腹肋）。曲がり目は輪の上端から腹の端までの 0.54 の所
#   肋骨ごとに: 展示の姿勢で輪の腹の端の位置 u_b と深さを測り（ribbottom.py）、目標との差を ribmodel2 の深さ Dv に足す。3 回くり返す
import numpy as np, json, os, subprocess
SK = 23.1; U0, UHIP = 9.5, 107.5
TT = [0.0, 0.19, 0.33, 0.48, 0.63, 0.78, 0.93, 1.00]
RR = [0.85, 0.97, 1.14, 1.22, 1.22, 1.13, 1.00, 0.86]
WALL = 0.6; CART_R = 0.25
def target(u): return float(np.interp((u - U0) / (UHIP - U0), TT, RR)) * SK - WALL - CART_R
env = dict(os.environ, RIB_SLOPES='0.57,-1.3,0.54', RIB_IN=os.environ.get('RIB_SRC', 'chameleon_body_ct_v1_ribs.npz'), RIB_OUT='ribs_tmp.npz', DV_JSON='dv_override.json')
log = json.load(open('ribmodel2.json'))['ribs']
dv = {}
for n, r in log.items():
    i = int(n[3:5]); dv.setdefault(i, []).append(r['Dv'])
dv = {i: float(np.mean(v)) for i, v in dv.items() if i >= 3}
for it in range(6):
    json.dump({str(i): v for i, v in dv.items()}, open('dv_override.json', 'w'), indent=1)
    subprocess.run(['python3', 'ribmodel2.py'], env=env, check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['python3', 'hyoid_relabel.py', 'ribs_tmp.npz', 'ribs_tmp2.npz'], check=True, stdout=subprocess.DEVNULL)
    subprocess.run(['python3', 'ribbottom.py', 'ribs_tmp2.npz'], check=True, stdout=subprocess.DEVNULL)
    rb = json.load(open('ribbottom.json'))
    err = []
    for i in sorted(dv):
        r = [rb[f'rib{i:02d}_{s}'] for s in 'LR' if f'rib{i:02d}_{s}' in rb]
        ub = np.mean([x[0] for x in r]); vb = np.mean([x[1] for x in r]); e = target(ub) - vb
        err.append((i, ub, vb, target(ub), e)); dv[i] += e
    print('pass', it, 'max |error| %.2f mm' % max(abs(x[4]) for x in err))
for i, ub, vb, tg, e in err: print('rib %2d  bottom u %.1f  ventral %.1f  target %.1f' % (i, ub, vb, tg))
json.dump({str(i): v for i, v in dv.items()}, open('dv_override.json', 'w'), indent=1)

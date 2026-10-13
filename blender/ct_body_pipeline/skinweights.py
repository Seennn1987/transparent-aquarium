# skinloft2.py の重みと静止の形だけを、作った膜（skin_posed.npz）に付け直す（場を作り直さない、数十秒）
import numpy as np
src = open('skinloft2.py', encoding='utf-8').read()
exec(src.split('# ---- 場 ----')[0])
z_ = np.load('skin_posed.npz'); v = z_['v'].astype(np.float64); f = z_['f'][:, ::-1].astype(np.int32)   # 保存は外向き。後でもう一度外向きにそろえる
exec('# ---- 重み ----' + src.split('# ---- 重み ----')[1])

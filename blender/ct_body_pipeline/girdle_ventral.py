# 肩帯（烏口骨）の腹の端: 展示の姿勢の体軸の枠で u と腹への深さ → girdle_ventral.json（ribdepth.py の胸骨の位置）
import numpy as np, json
exec(open('diag_profile.py').read().split("z=np.load('diag_inside.npz')")[0])
from scipy.spatial import cKDTree
kp=cKDTree(Cp); out={}
for g in ('fR_girdle','fL_girdle'):
    M=Mof(g); x=ct2m(d[g+'__v'])@M[:3,:3].T+M[:3,3]; j=kp.query(x)[1]; q=x-Cp[j]; vv=-(q*Dp[j]).sum(1)/MM; b=np.argmax(vv)
    out[g]=[float(arc[j[b]]),float(vv[b])]
json.dump(out,open('girdle_ventral.json','w')); print(out)

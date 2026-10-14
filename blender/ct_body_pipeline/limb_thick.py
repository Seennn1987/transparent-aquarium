# 手足の骨ごとに、CT の軟部（その骨の持ち物）の、骨の表面からの距離 [mm]（静止の姿勢、戻した空間）
import numpy as np, json
from scipy.spatial import cKDTree
src=open('skinloft2.py').read(); head=src.split("print('soft voxels'")[0]
exec(head)
out={}
for n in sorted(set(ow)):
    if not n.startswith(('fL','fR','hL','hR')) or n.endswith('girdle'): continue
    xs=X[ow==n]; xb=Xb[owb==n]
    if len(xs)<50 or len(xb)<50: continue
    d=cKDTree(xb).query(xs,workers=-1)[0]/MM
    out[n]=np.percentile(d,[25,50,75,90]).round(2).tolist(); print(n,len(xs),'soft-to-bone mm p25/50/75/90',out[n])
json.dump(out,open('limb_thick.json','w'))

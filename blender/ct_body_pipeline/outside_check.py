# 展示の姿勢で、膜の外へはみ出す骨（骨ごとの、外にある頂点の割合）
import sys, os, runpy, numpy as np, bpy
from mathutils.bvhtree import BVHTree
r=runpy.run_path(os.path.abspath('ctb/rig_chameleon_ct.py'),run_name='y')
g=runpy.run_path(r['GEN'],run_name='x')
coll,rigob,skel,rig=g['build'](); d,_,k=g['load']()
r['build_pose'](rigob,d,k,r['POSE_JAR']); bpy.context.view_layer.update(); r['trim_skin']()
dg=bpy.context.evaluated_depsgraph_get()
sk=bpy.data.objects['CH_Skin'].evaluated_get(dg); bvh=BVHTree.FromObject(sk,dg)
me=skel.evaluated_get(dg).to_mesh(); V=np.array([v.co[:] for v in me.vertices])
gi={vg.index:vg.name for vg in skel.vertex_groups}
dom=[gi[max(v.groups,key=lambda x:x.weight).group] if len(v.groups) else '' for v in skel.data.vertices]
from mathutils import Vector
out=np.zeros(len(V),bool)
for i,p in enumerate(V):
    if i%4: continue
    q,n,_,dist=bvh.find_nearest(Vector(p))
    if q is None: continue
    out[i]=(Vector(p)-q).dot(n)>0.03     # 膜の外 0.7 mm より遠い
# 符号の確認: 背骨の頂点は内側のはず
dom=np.array(dom)
sp=np.isin(dom,[f'v{i:02d}' for i in range(5,20)])&(np.arange(len(V))%4==0)
flip=out[sp].mean()>0.5
if flip: out=~out; out[np.arange(len(V))%4!=0]=False
res={}
for nm in np.unique(dom):
    m=(dom==nm)&(np.arange(len(V))%4==0)
    if m.sum()>20: res[nm]=out[m].mean()
for nm,f in sorted(res.items(),key=lambda x:-x[1])[:25]: print(nm,round(f,2))
print('spine outside frac (after sign fix)',round(out[sp].mean(),3),'flip',flip)

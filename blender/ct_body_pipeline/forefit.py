# 写真 01 の肘・手首・指先に合わせて、前肢の向き（θ, φ）を解く
import runpy, os, sys, math, numpy as np, bpy, json
from mathutils import Vector
HERE=os.path.dirname(os.path.abspath(__file__))
r=runpy.run_path(os.path.join(HERE,'rig_chameleon_ct.py'),run_name='y')
g=runpy.run_path(r['GEN'],run_name='x')
coll,rigob,skel,rig=g['build'](); d,_,k=g['load']()
pose=json.loads(os.environ['POSE']) if os.environ.get('POSE') else None
P=dict(r['POSE_JAR'])
if pose: P['limbs']={**P['limbs'],**{kk:tuple(v) for kk,v in pose.items()}}
r['build_pose'](rigob,d,k,P); bpy.context.view_layer.update()
dg=bpy.context.evaluated_depsgraph_get(); me=skel.evaluated_get(dg).to_mesh()
V=np.array([list(skel.matrix_world@v.co) for v in me.vertices])
vg={x.index:x.name for x in skel.vertex_groups}
gid=np.array([max(v.groups,key=lambda a:a.weight).group if v.groups else -1 for v in skel.data.vertices])
M=rigob.matrix_world; pb=rigob.pose.bones
H=V[gid==[i for i,n in vg.items() if n=='head'][0]]
occ=np.array(M@pb['head'].head); ax=np.array(M@pb['head'].tail)-occ; ax/=np.linalg.norm(ax)
snout=H[np.argmax((H-occ)@ax)]
rr=(H-occ)-np.outer((H-occ)@ax,ax); casque=H[np.argmax(np.linalg.norm(rr,axis=1))]
out={'snout':snout.tolist(),'casque':casque.tolist()}
for c in ('fR','fL','hL','hR'):
    for b in (('upper','lower','hand') if c[0]=='f' else ('upper','lower','foot')):
        out[c+'_'+b]=[list(M@pb[c+'_'+b].head),list(M@pb[c+'_'+b].tail)]
# hand tip: farthest hand vertex from wrist
for c in ('fR','fL','hL','hR'):
    e=('_hand' if c[0]=='f' else '_foot'); Hn=V[gid==[i for i,n in vg.items() if n==c+e][0]]; w=np.array(out[c+e][0])
    out[c+'_tip']=Hn[np.argmax(np.linalg.norm(Hn-w,axis=1))].tolist()
out['axial']={b.name:[list(M@b.head),list(M@b.tail)] for b in pb if b.name.startswith('v') or b.name.endswith('_girdle')}
json.dump(out,open(sys.argv[-1],'w'))
print('ok')

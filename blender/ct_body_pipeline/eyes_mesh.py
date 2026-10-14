# 眼球とレンズを臓器として organs_rigged.npz に足す（2026-10-14、organs_mesh.py の後に走らせる）
#   眼球: eyes.py の中心・半径の球（展示の姿勢）。レンズ: 写真 01 の目は暗い輪の中に淡い円が見えるので、眼球の中に
#   半径 LENS_F × 眼球の半径の球を、眼球の中心から外へ LENS_OFF × 半径ずらして置く（大きさと位置は仮）
#   重みは頭骨 1（目は頭について動く）。頂点は CT の mm（静止の形）に戻して保存
import numpy as np, json
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; k=float(P['k']); MM=k
def m2ct(m): m=np.asarray(m,float)/k; return np.stack([-m[...,2],m[...,0],-m[...,1]],-1)
LENS_F, LENS_OFF = 0.45, 0.35
def icosphere(n=3):
    t=(1+5**0.5)/2
    v=np.array([[-1,t,0],[1,t,0],[-1,-t,0],[1,-t,0],[0,-1,t],[0,1,t],[0,-1,-t],[0,1,-t],[t,0,-1],[t,0,1],[-t,0,-1],[-t,0,1]],float)
    f=np.array([[0,11,5],[0,5,1],[0,1,7],[0,7,10],[0,10,11],[1,5,9],[5,11,4],[11,10,2],[10,7,6],[7,1,8],[3,9,4],[3,4,2],[3,2,6],[3,6,8],[3,8,9],[4,9,5],[2,4,11],[6,2,10],[8,6,7],[9,8,1]])
    v/=np.linalg.norm(v,axis=1,keepdims=True)
    for _ in range(n):
        e=np.sort(np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]]),1); ue,inv=np.unique(e,axis=0,return_inverse=True)
        mid=v[ue].mean(1); mid/=np.linalg.norm(mid,axis=1,keepdims=True); m=len(v)+inv.reshape(3,-1).T
        v=np.concatenate([v,mid]); a,b,c=f.T; ab,bc,ca=m.T
        f=np.concatenate([np.stack([a,ab,ca],1),np.stack([b,bc,ab],1),np.stack([c,ca,bc],1),np.stack([ab,bc,ca],1)])
    return v,f
sv,sf=icosphere(3); sf=sf[:,::-1]   # 面の向きをほかの臓器（marching cubes）とそろえる
o=dict(np.load('organs_rigged.npz')); names=[str(x) for x in o['names']]
if 'head' not in names: names.append('head')
hi=names.index('head'); Mh=Mp[bn.index('head')]; Mi=np.linalg.inv(Mh)
EY=json.load(open('eyes.json')); organs=[str(x) for x in o['organs']]
cs=np.array([e['centre_model'] for e in EY.values()]); mid=cs.mean(0)
for n,e in EY.items():
    c=np.array(e['centre_model']); R=e['radius_mm']*MM; out=(c-mid)/np.linalg.norm(c-mid)
    side=n.split('_')[1]
    for nm,cc,rr in ((f'eye_{side}',c,R),(f'lens_{side}',c+out*LENS_OFF*R,LENS_F*R)):
        vp=cc+rr*sv; vr=vp@Mi[:3,:3].T+Mi[:3,3]
        o[nm+'__v']=m2ct(vr).astype(np.float32); o[nm+'__f']=sf.astype(np.int32)
        o[nm+'__w_idx']=np.full((len(sv),2),hi,np.int16); o[nm+'__w_val']=np.tile(np.array([1.0,0.0],np.float32),(len(sv),1))
        if nm not in organs: organs.append(nm)
        print(nm,'radius %.2f mm'%(rr/MM),'faces',len(sf))
o['names']=np.array(names); o['organs']=np.array(organs)
np.savez_compressed('organs_rigged.npz',**o)

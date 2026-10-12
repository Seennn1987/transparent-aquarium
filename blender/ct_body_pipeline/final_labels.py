import numpy as np, scipy.ndimage as nd, json
from scipy.spatial import cKDTree
M=np.load('Mc.npy'); Wh=np.load('W2.0.npy'); VL=np.load('vertLf.npy')
groups={'head':[81,83,86,104,110,114,115,123,124,126,127,60],
 'fA':[63,30,28,32,56,66,67,74,79],'fB':[35,80,58,69,75,77,89,87,51,57,62],
 'hA':[11,17,1,2,3,9,23,24,25,26,27],'hB':[19,50,41,116,118],
 'drop':[36,38,65,45,40,42,46,47,48,54]}
gid={'head':1,'fA':2,'fB':3,'hA':4,'hB':5,'drop':9}
G=np.zeros(Wh.max()+1,np.int8)
for g,ids in groups.items(): G[ids]=gid[g]
Gh=G[Wh]; Gh[(Wh>0)&(Gh==0)]=0
# upsample group map
Gf=np.zeros(M.shape,np.int8); up=Gh.repeat(2,0).repeat(2,1).repeat(2,2); sz=[min(a,b) for a,b in zip(M.shape,up.shape)]
Gf[:sz[0],:sz[1],:sz[2]]=up[:sz[0],:sz[1],:sz[2]]; del up
Gf[VL>0]=8     # axial
Gf[~M]=0
# fill remaining unlabeled bone voxels by nearest labeled (iterative grey dilation)
for it in range(6):
    un=M&(Gf==0)
    if not un.any(): break
    dil=nd.maximum_filter(Gf,size=3); Gf[un]=dil[un]
un=M&(Gf==0); print('still unlabeled',un.sum())
# small components not in any list near the intruder -> drop already by nearest
J=json.load(open('joints.json'))
chains={'fA':['fA_scap0','fA_shoulder','fA_elbow','fA_wrist','fA_tip'],'fB':['fB_scap0','fB_shoulder','fB_elbow','fB_wrist','fB_tip'],
 'hA':['hA_hip0','hA_hip','hA_knee','hA_ankle','hA_tip'],'hB':['hB_hip','hB_knee','hB_ankle','hB_tip']}
segnames={'fA':['girdle','upper','lower','hand'],'fB':['girdle','upper','lower','hand'],'hA':['girdle','upper','lower','foot'],'hB':['upper','lower','foot']}
B=np.zeros(M.shape,np.int16)
names={}
# vertebrae: 100+k ; segment 1 (pre-atlas) -> head
nv=int(VL.max())
sel=Gf==8; v=VL[sel].astype(np.int16); v[v==1]=-1
B[sel]=np.where(v<0,1,100+v)
B[Gf==1]=1; names[1]='head'
code=10
for c,ks in chains.items():
    P=np.array([J[k] for k in ks]); g=gid[c]
    pts=np.argwhere(Gf==g).astype(np.float32)
    best=np.full(len(pts),1e9); lab=np.zeros(len(pts),np.int16)
    for si,(a,b) in enumerate(zip(P,P[1:])):
        ab=b-a; t=np.clip(((pts-a)@ab)/(ab@ab),0,1); d=np.linalg.norm(pts-(a+t[:,None]*ab),axis=1)
        m=d<best; best[m]=d[m]; lab[m]=code+si
    B[tuple(pts.astype(int).T)]=lab
    for si,n in enumerate(segnames[c]): names[code+si]=f'{c}_{n}'
    code+=10
for k in range(2,nv+1): names[100+k]=f'v{k-1:02d}'
B[Gf==9]=0; np.save("intruder.npy",Gf==9)
np.save('B.npy',B); json.dump({str(k):v for k,v in names.items()},open('bone_names.json','w'))
print('bones',len(np.unique(B))-1)

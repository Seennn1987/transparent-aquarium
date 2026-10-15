# A7c: 口を開く。下あご（メッケル軟骨）と下の歯を、顎の関節（上あごと下あごがいちばん近づく後ろの端、左右 2 点）を
#  通る軸のまわりに回す。体の膜（a5_S）は、いちばん近い骨が下あごである所を同じように回し、上と下の間を口として空ける。
#  使い方: python3 a7c_open_mesh.py <角度°> [mesh]   出力: a7_open.json、a5_S_open.npy、mesh/HH_jaw_*.ply ほか
import hh_paths; hh_paths.cd_work()
import numpy as np, json, sys, os
from scipy import ndimage as nd
from scipy.spatial import cKDTree
from skimage.measure import marching_cubes
exec(open(hh_paths.script('a4e_mesh.py')).read().split("which=sys.argv[1]")[0])
ANG=float(sys.argv[1]); DO_MESH='mesh' in sys.argv
d=np.load('a7_jaw_fine.npz'); Ff=d['field']; o=d['origin']; G=float(d['step']); W=np.load('a7_jawlab.npy')
def f2mm(ix):  # (iz,iv,iu) -> (z,u,v) mm
    return np.stack([o[0]+ix[:,0]*G, o[2]+ix[:,2]*G, o[1]+ix[:,1]*G],1)
# 関節: 左（u<0）で上あご(2)と下あご(3)の点のうち、100 mm より後ろでいちばん近い組の中点。右は鏡映
p2=f2mm(np.argwhere(W==2)); p3=f2mm(np.argwhere(W==3))
p2=p2[(p2[:,0]>100)&(p2[:,1]<-10)]; p3=p3[(p3[:,0]>100)&(p3[:,1]<-10)]
dd,ii=cKDTree(p2).query(p3); # 近い組の上位 1% の中点の平均
sel=dd<=np.percentile(dd,1); JL=((p3[sel]+p2[ii[sel]])/2).mean(0); JR=JL*np.array([1,-1,1])
print('joint L',JL.round(1),'R',JR.round(1),'gap',dd.min().round(2))
ax=(JR-JL)/np.linalg.norm(JR-JL)
def rot(P,ang):  # P: (n,3) in (z,u,v)。軸 ax、点 JL のまわりに ang 度（ロドリゲス）
    t=np.radians(ang); X=P-JL; c,s=np.cos(t),np.sin(t)
    return JL+X*c+np.cross(ax,X)*s+np.outer(X@ax,ax)*(1-c)
# 向き: 前の点（z が小さい）が腹側（v が大きい）へ動く向きを「開く」とする
test=rot(np.array([[JL[0]-50,0,JL[2]]]),10)[0]; SGN=1.0 if test[2]>JL[2] else -1.0
A=SGN*ANG
json.dump(dict(angle_deg=ANG,joint_L_zuv_mm=JL.tolist(),joint_R_zuv_mm=JR.tolist(),sign=SGN),open('a7_open.json','w'),indent=1)
# ---- 体の膜を開く ----
VX=0.735; U0c,V0c=-180.0,-150.0
S=np.load('a5_S.npy',mmap_mode='r'); NZ,NV,NU=S.shape
# 下あごの領域（開く前）: 細かい格子を 2 倍に間引き、いちばん近い骨のラベルで分ける
Wd=W[::2,::2,::2]; low=(Wd==3)|(Wd==6); rest=(Wd==1)|(Wd==2)|(Wd==4)|(Wd==5)
dl=nd.distance_transform_edt(~low); dr=nd.distance_transform_edt(~rest)
L0=(dl<dr)
G2=G*2
def inL0(z,u,v):
    iz=np.round((z-o[0])/G2).astype(int); iv=np.round((v-o[1])/G2).astype(int); iu=np.round((u-o[2])/G2).astype(int)
    ok=(iz>=0)&(iz<L0.shape[0])&(iv>=0)&(iv<L0.shape[1])&(iu>=0)&(iu<L0.shape[2])&(z<JL[0]+6)
    r=np.zeros(len(z),bool); r[ok]=L0[iz[ok],iv[ok],iu[ok]]; return r
k1=int(160/VX)
So=np.lib.format.open_memmap('a5_S_open.npy',mode='w+',dtype=np.bool_,shape=S.shape)
for k0 in range(0,NZ,100): So[k0:k0+100]=S[k0:k0+100]
vv,uu=np.meshgrid(V0c+np.arange(NV)*VX,U0c+np.arange(NU)*VX,indexing='ij')
for k in range(0,k1):
    z=k*VX; P=np.stack([np.full(uu.size,z),uu.ravel(),vv.ravel()],1)
    Sk=np.asarray(S[k]).ravel()
    keep_static=Sk&~inL0(P[:,0],P[:,1],P[:,2])
    Q=rot(P,-A)  # 開いたあとの点を、開く前へ戻す
    iz=np.round(Q[:,0]/VX).astype(int); iv=np.round((Q[:,2]-V0c)/VX).astype(int); iu=np.round((Q[:,1]-U0c)/VX).astype(int)
    ok=(iz>=0)&(iz<NZ)&(iv>=0)&(iv<NV)&(iu>=0)&(iu<NU)
    moved=np.zeros(len(P),bool); idxs=np.nonzero(ok)[0]
    sv=np.asarray(S[np.clip(iz[ok],0,NZ-1).min():np.clip(iz[ok],0,NZ-1).max()+1]) if ok.any() else None
    if ok.any():
        zmin=np.clip(iz[ok],0,NZ-1).min()
        moved[idxs]=sv[iz[ok]-zmin,iv[ok],iu[ok]]&inL0(Q[ok,0],Q[ok,1],Q[ok,2])
    So[k]=(keep_static|moved).reshape(NV,NU)
So.flush(); print('skin opened')
if DO_MESH:
    def write_part(name,field,level,origin_mm,step,rotate=False):
        if field.max()<level: print(name,'empty'); return
        v,f,_,_=marching_cubes(np.pad(field,1,constant_values=-1000).astype(np.float32),level=level,allow_degenerate=False)
        v=v-1; z=origin_mm[0]+v[:,0]*step; vv_=origin_mm[1]+v[:,1]*step; u=origin_mm[2]+v[:,2]*step
        P=np.stack([z,u,vv_],1)
        if rotate: P=rot(P,A)
        Vb=np.stack([P[:,0],P[:,1],-P[:,2]],1)/1000.0
        write_ply(f'{OUT}/{name}.ply',Vb,f); print(name,len(v),len(f))
    for name,labs,lev,rotq in (('HH_jaw_upper',(2,),250,False),('HH_jaw_lower',(3,),250,True),('HH_hyoid',(4,),250,False),
                               ('HH_teeth_upper',(5,),650,False),('HH_teeth_lower',(6,),650,True)):
        m=np.isin(W,labs); m=nd.binary_dilation(m,iterations=1)
        fld=np.where(m,Ff,-1000).astype(np.float32)
        if lev==250: fld=nd.gaussian_filter(fld,0.6)
        write_part(name,fld,lev,o,G,rotq)

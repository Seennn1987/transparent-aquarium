# 膜の太さの、体軸に沿った変化（展示の姿勢）。8 方向に、軸から膜の外まで
import numpy as np, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mpose=P['M']; k=float(P['k']); MM=k
def Mof(n): return Mpose[bn.index(n)]
d=np.load('chameleon_body_ct.npz')
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
C=ct2m(d['rig__axis']); Dv=np.asarray(d['rig__dorsal'],float); Dv=np.stack([Dv[:,1],-Dv[:,2],-Dv[:,0]],-1)
J=np.asarray(d['rig__J'],float); step=float(d['rig__axis_step'])
T=np.gradient(C,axis=0); T/=np.linalg.norm(T,axis=1,keepdims=True)
Dd=Dv-T*(Dv*T).sum(1,keepdims=True); Dd/=np.linalg.norm(Dd,axis=1,keepdims=True)
arc=np.arange(len(C))*step
centre=np.array([0.5*(J[kk-1]+(J[kk] if kk<len(J) else arc[-1])) for kk in range(1,len(J)+1)])
i=np.clip(np.searchsorted(centre,arc),1,len(centre)-1); w1=np.clip((arc-centre[i-1])/(centre[i]-centre[i-1]),0,1)
MA=np.array([Mof(f'v{j+1:02d}') for j in range(len(J))])
Mst=(1-w1)[:,None,None]*MA[i-1]+w1[:,None,None]*MA[i]
Cp=np.einsum('nij,nj->ni',Mst[:,:3,:3],C)+Mst[:,:3,3]
def rot(v): w=np.einsum('nij,nj->ni',Mst[:,:3,:3],v); return w/np.linalg.norm(w,axis=1,keepdims=True)
Tp=rot(T); Dp=rot(Dd); Dp-=Tp*(Dp*Tp).sum(1,keepdims=True); Dp/=np.linalg.norm(Dp,axis=1,keepdims=True); Ep=np.cross(Tp,Dp)
z=np.load('diag_inside.npz'); I=z['inside']; lo=z['lo']; VOX=float(z['vox'])
def inside(p):
    g=((p-lo)/VOX).round().astype(int); ok=(g>=0).all(-1)&(g<np.array(I.shape)).all(-1)
    out=np.zeros(p.shape[:-1],bool); out[ok]=I[tuple(g[ok].T)]; return out
ang=np.deg2rad(np.arange(0,360,45)); names=['背','背右','右','腹右','腹','腹左','左','背左']
rs=np.arange(0,25,0.05)*MM
sel=np.arange(0,len(C),5)
R=np.zeros((len(sel),len(ang)))
for a_i,a in enumerate(ang):
    dirn=np.cos(a)*Dp[sel]+np.sin(a)*Ep[sel]
    pts=Cp[sel][:,None,:]+dirn[:,None,:]*rs[None,:,None]
    ins=inside(pts)
    # 軸から外へ、最初に外に出る所
    first_out=np.argmax(~ins,axis=1); R[:,a_i]=rs[first_out]/MM
np.savez('diag_profile.npz',arc=arc[sel],R=R,J=J)
fig,ax=plt.subplots(2,1,figsize=(16,8))
for a_i in (0,4,2,6): ax[0].plot(arc[sel],R[:,a_i],label=names[a_i],lw=1)
for jj in J: ax[0].axvline(jj,color='0.85',lw=0.5,zorder=0)
ax[0].set_ylabel('軸から膜まで [mm]'); ax[0].legend(); ax[0].set_title('膜の太さ（展示の姿勢）。縦の灰線 = 椎骨の境')
tail=arc[sel]>J[22]
ax[1].plot(arc[sel][tail],R[tail].mean(1),'k',label='8 方向の平均'); 
for jj in J[22:]: ax[1].axvline(jj,color='0.85',lw=0.5,zorder=0)
ax[1].set_xlabel('体軸の長さ [mm]'); ax[1].set_ylabel('[mm]'); ax[1].set_title('尾（仙椎より後ろ）'); ax[1].legend()
plt.tight_layout(); plt.savefig('diag_profile.png',dpi=80)
# 数: 尾の平均半径の、なめらかな傾向からのずれ
import scipy.ndimage as nd
rt=R[tail].mean(1); trend=nd.gaussian_filter1d(rt,40)
print('tail mean radius: residual std %.2f mm, max |res| %.2f mm, local maxima (bulges)'%(np.std(rt-trend),np.abs(rt-trend).max()), int(((rt[1:-1]>rt[:-2])&(rt[1:-1]>rt[2:])).sum()))
dor=R[~tail,0]; print('trunk dorsal radius: residual std %.2f mm'%np.std(dor-nd.gaussian_filter1d(dor,40)))

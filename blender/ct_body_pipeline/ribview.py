# 並べ直した肋骨の確かめ: 横から・断面（前 = いま、後 = 並べ直し）
import numpy as np, pickle, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; k=float(P['k']); MM=k
def ct2m(p): p=np.asarray(p,float); return np.stack([p[...,1],-p[...,2],-p[...,0]],-1)*k
d=np.load('chameleon_body_ct.npz'); c=np.load('organs_cav.npz'); us=c['us']; AP=c['AP']; AV=c['AV']; AR=c['AR']
T=np.gradient(AP,axis=0); T/=np.linalg.norm(T,axis=1,keepdims=True)
R=pickle.load(open('rib_pts.pkl','rb'))
CA=pickle.load(open('cart_pts.pkl','rb'))
V={}
for n in bn:
    if n.startswith('v') and n+'__v' in d.files:
        v=ct2m(d[n+'__v']); M=P['M'][bn.index(n)]; V[n]=v@M[:3,:3].T+M[:3,3]
U=[20,35,50,65,80,95]
fig,ax=plt.subplots(3,len(U),figsize=(4*len(U),13),gridspec_kw={'height_ratios':[1,1,1.3]})
for row,which in enumerate((0,1)):
    for i,u in enumerate(U):
        j=int(np.argmin(np.abs(us-u))); o=AP[j]
        for n,(p0,p1) in R.items():
            p=(p0,p1)[which]; s=(p-o)@T[j]; m=np.abs(s)<1.0*MM
            ax[row,i].scatter(((p[m]-o)@AR[j])/MM,((p[m]-o)@AV[j])/MM,s=0.3,c='C3')
        for n,p in V.items():
            s=(p-o)@T[j]; m=np.abs(s)<1.0*MM; ax[row,i].scatter(((p[m]-o)@AR[j])/MM,((p[m]-o)@AV[j])/MM,s=0.3,c='k')
        if which==1:
            for a_,b_,r_ in CA:
                q=a_+(b_-a_)*np.linspace(0,1,40)[:,None]; s=(q-o)@T[j]; m=np.abs(s)<1.0*MM
                ax[row,i].scatter(((q[m]-o)@AR[j])/MM,((q[m]-o)@AV[j])/MM,s=3,c='C0')
        ax[row,i].set_aspect('equal'); ax[row,i].set_xlim(-15,15); ax[row,i].set_ylim(28,-6)
        ax[row,i].set_title(('いま' if which==0 else '並べ直し')+f'  体軸 {u} mm'); ax[row,i].grid(alpha=0.3)
for a in ax[2]: a.remove()
gs=fig.add_gridspec(3,len(U))
for half,which in enumerate((0,1)):
    a=fig.add_subplot(gs[2,half*3:half*3+3])
    for n,(p0,p1) in R.items():
        p=(p0,p1)[which]
        if n.endswith('_L'): a.scatter(p[::3,0]/MM,p[::3,2]/MM,s=0.2,c='C3')
    for n,p in V.items(): a.scatter(p[::6,0]/MM,p[::6,2]/MM,s=0.2,c='k')
    if which==1:
        for a_,b_,r_ in CA: a.plot([a_[0]/MM,b_[0]/MM],[a_[2]/MM,b_[2]/MM],c='C0',lw=1)
    a.set_aspect('equal'); a.axis('off'); a.set_title(('いま' if which==0 else '並べ直し')+'（左の肋骨、横から）')
plt.tight_layout(); plt.savefig('ribview.png',dpi=60)

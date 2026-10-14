# 写真 01 の色の組（青・淡・赤・内臓）と、画面の同じ割合の画素から、"01" の色を解く
import numpy as np, sys, json
from PIL import Image
from scipy.optimize import nnls
p=np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float)
A=-np.log(np.clip(p/224.0,1e-3,1)); H,W,_=p.shape
x=np.arange(W)[None,:]; y=np.arange(H)[:,None]
inside=(x>108)&(x<318)&(y>62)&(y<398)
chroma=p.max(2)-p.min(2); mean=p.mean(2)
animal=inside&((chroma>12)|(mean<200))
r,g,b=p[...,0],p[...,1],p[...,2]
blue=animal&(b>r+20)&(g>r+5); red=animal&(r>b+15)&(r>g+30); pale=animal&~blue&~red&(mean>150)
na=animal.sum(); sh={'blue':blue.sum()/na,'red':red.sum()/na,'pale':pale.sum()/na}
Aph={'B':np.median(A[blue],0),'P':np.median(A[pale],0),'R':np.median(A[red],0),'V':-np.log(np.array([0.50,0.42,0.38]))}
a=np.maximum(np.load(sys.argv[2]),0); f=np.maximum(np.load(sys.argv[3])[...,0],0)
bone,cart,skin,visc=[a[...,i] for i in range(4)]
t0=0.042; F=t0*(1-np.exp(-bone/t0)); an=skin>1e-4; N=an.sum()
free=an&(F<1e-3)&(visc<1e-4)&(cart<1e-4)
idx=np.where(free.ravel())[0]; o=np.argsort(f.ravel()[idx])
nB=int(sh['blue']*N); nP=int(sh['pale']*N)
cls={'B':idx[o[-nB:]],'P':idx[o[:nP]],'R':np.where((an&(F>=np.percentile(F[an],100-100*sh['red']))).ravel())[0],'V':np.where((an&(visc>=0.13)&(F<1e-3)).ravel())[0]}
# 内臓の一塊（V）を書き出さなくなった（2026-10-14）: その組が空なら、膜の層・膜・骨の 3 つを 3 組（B・P・R）で解く
KEYS='BPRV' if len(cls['V']) else 'BPR'
NC=4 if KEYS=='BPRV' else 3
rows={k:[float(np.median(v.ravel()[ii])) for v in (f,skin,F,visc)][:NC] for k,ii in cls.items() if len(ii)}
M=np.array([rows[k] for k in KEYS]); G=[]; pred=[]
for c in range(3):
    bb=np.array([Aph[k][c] for k in KEYS]); w=1/np.maximum(bb,0.05)
    xx,_=nnls(M*w[:,None],bb*w); G.append(xx); pred.append(M@xx)
G=np.array(G).T; pred=np.array(pred).T
print('rows',{k:[round(v,4) for v in r] for k,r in rows.items()})
for k,pp in zip(KEYS,pred): print(k,'pred',pp.round(3),'photo',Aph[k].round(3))
for nm,row in zip(('film','skin','bone','visc')[:NC],G): print(nm,row.round(5), (row/row.max()).round(3))

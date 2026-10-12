# CT の個体の胸郭の、保存時の変形を戻す（復元）。肋骨の点（CT のボクセル座標）を動かす関数と、その確認。
#   この個体（MorphoSource 000050726）は胴が約 130° 丸まり、胸郭が横へ押されている:
#   左右の肋骨の先がそろって右へ寄り（v09 で右 +14.2 mm、左 +10.5 mm）、左の肋骨は正中を越えている。
#   また胴の中ほどから後ろの肋骨は、背骨に垂直から後ろへ 52〜72° 寝ている（06 で約 50°、Digimorph TNHC 62768 で 53〜59°）。
#   1. 横のずれ（ずり）: 各椎骨の枠（体軸 t、横 r、腹 v）で、横 = 横 − α(k)×腹。α(k) は、左右一対の中心線の先の横の平均 ÷ 腹の深さの平均
#      （一対がそろわない椎骨は前後から補間）。肋骨の形の曲がりは、ずりで一緒に戻る
#   2. 寝る角: RAKE_MAX（50°）より寝ている肋骨を、根元を中心に横軸 r まわりに起こす（剛体の回転）
#   腹側の部分（中心線から 0.3 mm より遠い肋骨の点）は、同じ側の肋骨の中心線への距離で 2 の回転を混ぜる（σ 1.5 mm、近い 3 本）
import numpy as np, json
from scipy.spatial import cKDTree
import os
RAKE_MAX=float(os.environ.get("RIB_RAKE_MAX","50"))   # 06 で約 50°、Digimorph で 53〜59°
C=np.load('axis5_s.npy')*2+0.5; T=np.load('axis5_t.npy'); D=np.load('frame_D.npy'); J=np.load('J.npy'); tk=np.load('ribtracks2.npz')
def frame(kk):
    kk=int(np.clip(kk,1,21)); sc=0.5*(J[kk-1]+J[kk]); i=int(sc/0.1); t=T[i]; d=D[i]-t*(D[i]@t); d/=np.linalg.norm(d); return C[i],t,np.cross(-t,d),-d
def rot(axis,ang):
    a=axis/np.linalg.norm(axis); K=np.array([[0,-a[2],a[1]],[a[2],0,-a[0]],[-a[1],a[0],0]]); return np.eye(3)+np.sin(ang)*K+(1-np.cos(ang))*K@K
# α(k)
pair={}
for k in tk.files:
    l=int(k); kk=(l-160)//2+1; P=tk[k]
    if kk>21 or len(P)*0.208<8: continue
    c,t,r,v=frame(kk); pair.setdefault(kk,{})[(l-160)%2]=((P[-1]-c)@r,(P[-1]-c)@v)
ks=sorted(k_ for k_,x in pair.items() if len(x)==2)
al=[ (pair[k_][0][0]+pair[k_][1][0])/2/((pair[k_][0][1]+pair[k_][1][1])/2) for k_ in ks]
def alpha(kk): return float(np.interp(kk,ks,al))
# 寝る角の回転（各肋骨）
ribs={}
for k in tk.files:
    l=int(k); kk=(l-160)//2+1; P=tk[k].astype(float)
    if kk>21 or len(P)<15: continue
    c,t,r,v=frame(kk); h=P[0]
    # 先にずりを当てた中心線で角を測る
    def shear(X):
        q=X-c; return X-np.outer(alpha(kk)*(q@v),r)
    Ps=shear(P); n=max(5,int(len(Ps)*0.4)); e=Ps[n]-Ps[0]; e/=np.linalg.norm(e)
    rake=np.degrees(np.arctan2(e@t,e@v)); R=np.eye(3)
    if rake>RAKE_MAX and len(P)*0.208>=5:          # 5 mm より短い中心線（頸の小さな肋骨など）は起こさない
        for sg in (1,-1):
            Rt=rot(r,sg*np.radians(rake-RAKE_MAX)); e2=Rt@e
            if abs(np.degrees(np.arctan2(e2@t,e2@v))-RAKE_MAX)<1: R=Rt; break
    ribs[l]={'k':kk,'R':R,'h':shear(h[None])[0],'rake':rake,'track':P}
def restore(X,labels):
    """肋骨の点 X（CT のボクセル座標、(n,3)）と、その点の肋骨ラベル labels を、復元した位置へ。"""
    X=np.asarray(X,float); out=X.copy()
    keys=[l for l in ribs]; dist=np.full((len(X),len(keys)),np.inf)
    for j,l in enumerate(keys):
        same=((labels-160)%2)==((l-160)%2)
        if same.any(): dist[same,j]=cKDTree(ribs[l]['track']).query(X[same])[0]
    own=np.array([keys.index(l) if l in ribs else -1 for l in labels])
    rigid=(own>=0)&(dist[np.arange(len(X)),np.maximum(own,0)]<=3)
    w=np.exp(-0.5*(dist/15.0)**2); top=np.argsort(dist,1)[:,3:]; np.put_along_axis(w,top,0,1); w[rigid]=0; w[rigid,own[rigid]]=1
    ws=w.sum(1); ok=ws>1e-9; w[ok]/=ws[ok][:,None]
    # 1. ずり（点のラベルの椎骨の枠で）
    kk=(labels-160)//2+1; Xs=X.copy()
    for k_ in np.unique(kk):
        m=kk==k_; c,t,r,v=frame(k_); q=X[m]-c; Xs[m]=X[m]-np.outer(alpha(k_)*(q@v),r)
    # 2. 寝る角（重みで混ぜた回転）
    acc=np.zeros_like(X)
    for j,l in enumerate(keys):
        m=w[:,j]>0
        if m.any(): acc[m]+=w[m,j][:,None]*((Xs[m]-ribs[l]['h'])@ribs[l]['R'].T+ribs[l]['h'])
    out[ok]=acc[ok]; out[~ok]=Xs[~ok]
    return out
if __name__=='__main__':
    print('alpha',dict(zip(ks,np.round(al,2))))
    print('rake before (after shear) / rotate',{ribs[l]['k']:round(ribs[l]['rake'],1) for l in sorted(ribs)})

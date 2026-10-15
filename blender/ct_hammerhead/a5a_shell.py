# A5 体の膜（胴の殻）: 最終の座標の CT の値（a4_skel_field.npy。骨以外の組織も入っている）から作る
#  頭（〜160 mm）: A4 で鏡映・縮めた断面の形をそのまま使う（穴を埋めた体の断面）
#  胴（160 mm〜）: 断面ごとに「背骨の中心からの半径の表」（角度 2° ごと）を作って整える
#    - 中心は各断面の背骨（u=0、v=尾の背腹のずれ−尾の反り）
#    - 左右をそろえる（θ と 180°−θ の平均）
#    - 700 mm より前は、すべての向きで角度方向の中央値（60°）より外へ出た分を切る:
#      元の垂れた胸びれ・腹びれの肉と、傾いたままの背びれ・臀びれの肉を胴から外す
#      700 mm より後ろ（尾びれ）は、横の向きだけ切る（尾びれの板は背と腹の向きに残す）
#    - 体軸方向に中央値（5 断面）とガウス（2 断面）でならす
#    - 胴の幅: 左右（u）を k 倍。150 mm まで 1、175 mm で 1.55（決定: 写真の 頭÷胴 = 2.6）、720 mm まで 1.55、780 mm で 1
#  背びれ・第2背びれ・臀びれの膜: 胴から外したひれの肉を、A4 で骨を立て直したのと同じ変換（a4_*_xform.npz）で立て直し、
#    立て直した骨と合わせて別の体積にする
import hh_paths; hh_paths.cd_work()
import numpy as np, json, sys
STAGE=sys.argv[1]
from scipy import ndimage as ndi
from skimage.draw import polygon as skpoly
VX=0.735; U0,V0=-180.0,-150.0
F=np.load('a4_skel_field.npy',mmap_mode='r'); NZ,NV,NU=F.shape
keep=np.load('tail_keep_v.npy'); off=np.load('tail_bend_offset_mm.npy')
def vc_of(z): return np.interp(z*2,np.arange(len(keep)),keep)-np.interp(z,np.arange(len(off)),off)
TH=np.radians(np.arange(0,360,2)); NT=len(TH); ang=np.degrees(TH)
dist_v=np.minimum(np.abs(ang-90),np.abs(ang-270)); lat=dist_v>35
mirror=(np.round((np.pi-TH)%(2*np.pi)/np.radians(2)).astype(int))%NT
STEP=2   # 半径の表は 2 断面ごと（1.47 mm）
zs=np.arange(0,NZ,STEP); R=np.zeros((len(zs),NT)); rs=np.arange(0,400,0.5)
if STAGE!='1': R=np.load('a5_radius_raw.npy')
masks_head={}
for i,k in (enumerate(zs) if STAGE=='1' else []):
    z=k*VX; m=ndi.binary_fill_holes(np.asarray(F[k])>-400)
    lab,n=ndi.label(m)
    if n==0: continue
    cv=(vc_of(z)-V0)/VX; cu=(0-U0)/VX
    l=lab[int(round(cv)),int(round(cu))]
    if l==0: l=np.argmax(ndi.sum(m,lab,range(1,n+1)))+1
    m=lab==l
    for j,t in enumerate(TH):
        uu=cu+rs*np.cos(t); vv=cv+rs*np.sin(t); ok=(uu>=0)&(uu<NU-1)&(vv>=0)&(vv<NV-1)
        hit=m[np.round(vv[ok]).astype(int),np.round(uu[ok]).astype(int)]
        R[i,j]=rs[ok][hit].max()*VX if hit.any() else 0.0
np.save('a5_radius_raw.npy',R)
zmm=zs*VX; Rs=R.copy()
for i in range(len(zs)):
    r=(R[i]+R[i][mirror])/2
    if zmm[i]>=120:
        med=ndi.median_filter(np.r_[r[-15:],r,r[:15]],size=31)[15:-15]
        cut=np.ones(NT,bool) if zmm[i]<700 else lat
        r=np.where(cut,np.minimum(r,med),r)
    Rs[i]=r
Rs=ndi.median_filter(Rs,size=(5,1),mode='nearest'); Rs=ndi.gaussian_filter1d(Rs,2,axis=0,mode='nearest')
# 角度方向にもならす（6°）。尾びれ（700 mm〜）は板の縁を残すためならさない
for i in range(len(zs)):
    if 120<=zmm[i]<700: Rs[i]=ndi.gaussian_filter1d(Rs[i],3,mode='wrap')
def kfac(z):
    if z<=150: return 1.0
    if z<=175: return 1+0.55*(z-150)/25
    if z<=720: return 1.55
    if z<=780: return 1.55-0.55*(z-720)/60
    return 1.0
np.save('a5_radius.npy',Rs)

def kfac(z):
    if z<=150: return 1.0
    if z<=175: return 1+0.55*(z-150)/25
    if z<=720: return 1.55
    if z<=780: return 1.55-0.55*(z-720)/60
    return 1.0
# 胴の幅の目標（2026-10-14 決定: 写真の 頭の幅 ÷ 胴の幅 = 2.6 → 266/2.6 = 102 mm）。
#  写真では頭のすぐ後ろから胸びれの前まで胴の幅がほぼ一定なので、120〜250 mm はこの幅に合わせ、
#  250 mm より後ろは CT の幅の 1.55 倍（250 mm で目標とほぼ同じ）、720〜780 mm で 1 倍へ戻す
TW=266.0/2.6
import os as _os
ct_w=np.array([np.interp(0,np.degrees(TH),Rs[i])+np.interp(180,np.degrees(TH),Rs[i]) for i in range(len(zs))])
# 2026-10-15 決定: 胴の幅を、背骨の高さの幅でなく断面のいちばん広い所の幅（上から見た幅）で測る（既定。前のやり方は HH_TRUNK_WIDTH=spine）。
#  背骨の高さの幅で倍率を決めると、頭のすぐ後ろ（124〜156 mm）の平たい断面では背骨より腹側の広い所まで広がり、上から見た幅が
#  決めた 102 mm を超えて 125 mm になっていた（計画書 第 9 節 A7「頭のすぐ後ろの出っ張り」）
if _os.environ.get('HH_TRUNK_WIDTH', 'max') == 'max':
    ct_w=np.array([max(0,(Rs[i]*np.cos(TH)).max())+max(0,(-Rs[i]*np.cos(TH)).max()) for i in range(len(zs))])
def kfac(z):
    if z<115: return 1.0
    w=np.interp(z,zmm,ct_w)
    if z<=250:
        a=np.clip((z-115)/10,0,1)
        return 1.0*(1-a)+a*np.clip(TW/max(w,1),float(_os.environ.get('HH_TRUNK_KMIN','1.0')),1.6)   # HH_TRUNK_KMIN: 狭める下限（既定 1.0。2026-10-15 に 0.9 を試し、効かなかった）
    if z<=720: return 1.55
    if z<=780: return 1.55-0.55*(z-720)/60
    return 1.0
_zk=np.arange(0,1046,1.0); _K=np.array([kfac(z) for z in _zk]); _K=ndi.gaussian_filter1d(_K,8)   # 体軸方向にならす（8 mm）
if _os.environ.get('HH_TRUNK_WIDTH', 'max') == 'max':
    # 2026-10-15 決定: ならした倍率が、決めた幅 ÷ その位置の幅 を超えないように抑える（120〜250 mm）。後ろの倍率 1.6 がならしで前へ
    #  染み出し、144〜152 mm の幅が 109 mm になっていた
    _cap=TW/np.maximum(np.interp(_zk,zmm,ct_w),1); _in=(_zk>=125)&(_zk<=250)
    _K[_in]=np.minimum(_K[_in],np.maximum(_cap[_in],1.0))
    _K=np.where(_zk<120,_K,ndi.gaussian_filter1d(_K,2))   # 段を消す（2 mm）
kfac_raw=kfac
def kfac(z): return float(np.interp(z,_zk,_K))
if STAGE=='2':
    S=np.lib.format.open_memmap('a5_S.npy',mode='w+',dtype=np.bool_,shape=(NZ,NV,NU))
    S0=np.lib.format.open_memmap('a5_S0.npy',mode='w+',dtype=np.bool_,shape=(NZ,NV,NU))
    for k in range(NZ):
        z=k*VX
        if z<115:
            # 頭: 翼の後ろの端は断面で左右の離れた島になるので、最大の塊だけでなく 30 ボクセル以上の塊をすべて残す
            m=ndi.binary_fill_holes(np.asarray(F[k])>-400); lab,n=ndi.label(m)
            if n:
                sz=ndi.sum(m,lab,range(1,n+1)); m=np.isin(lab,1+np.nonzero(sz>=30)[0]); m=m|m[:,::-1]
            S[k]=m; S0[k]=m; continue
        r=np.array([np.interp(z,zmm,Rs[:,j]) for j in range(NT)]); kk=kfac(z); vc=vc_of(z)
        if r.max()<1: continue
        for arr,kx in ((S0,1.0),(S,kk)):
            pu=r*np.cos(TH)*kx; pv=r*np.sin(TH)+vc
            rr,cc=skpoly((pv-V0)/VX,(pu-U0)/VX,shape=(NV,NU)); arr[k,rr,cc]=True
    S.flush(); S0.flush(); print('stage2 ok')
if STAGE=='3':
    S0=np.load('a5_S0.npy',mmap_mode='r')
    uu_g=U0+np.arange(NU)*VX; vv_g=V0+np.arange(NV)*VX
    for name,zr,side in (('dfin1',(255,410),-1),('dfin2',(625,675),-1),('anal',(590,670),1)):
        x=np.load(f'a4_{name}_xform.npz'); ub,vb,a=float(x['ub']),float(x['vb']),float(x['ang']); ca,sa=np.cos(a),np.sin(a)
        pts=[]
        for k in range(int(zr[0]/VX),int(zr[1]/VX)):
            fl=(np.asarray(F[k])>-400)&~np.asarray(S0[k])
            vi,ui=np.nonzero(fl); u=uu_g[ui]; v=vv_g[vi]
            sel=(np.sign(v)==side)&(np.abs(u)<70); u,v=u[sel],v[sel]
            du,dv=u-ub,v-vb; u2=du*ca-dv*sa; v2=du*sa+dv*ca+vb
            u2=u2-np.interp(np.round(v2/2),x['band_keys'],x['band_med'])*np.clip(np.abs(v2-vb)/10,0,1)
            th=np.abs(u2)<5.0                      # 立て直した後に正中の板（厚さ 10 mm）に入る肉だけ。体の横の肉や押し付けられたひれの肉を拾わない
            u2,v2=u2[th],v2[th]
            pts.append(np.stack([np.full(len(u2),k*VX),u2,v2],1))
        P=np.concatenate(pts)
        b=np.load(f'a4_{name}.npz'); bo=b['field']>0.5; o=b['origin']; z_,v_,u_=np.nonzero(bo)
        iz=np.r_[np.round(P[:,0]/VX).astype(int),z_+o[0]]; iv=np.r_[np.round((P[:,2]-V0)/VX).astype(int),v_+o[1]]; iu=np.r_[np.round((P[:,1]-U0)/VX).astype(int),u_+o[2]]
        lo=np.array([iz.min(),iv.min(),iu.min()])-3; hi=np.array([iz.max(),iv.max(),iu.max()])+4
        M=np.zeros(hi-lo,bool); M[iz-lo[0],iv-lo[1],iu-lo[2]]=True
        M=ndi.binary_closing(M,iterations=2)
        # 骨のひれにつながる塊だけ残す
        lab,n=ndi.label(M); bl=np.unique(lab[z_+o[0]-lo[0],v_+o[1]-lo[1],u_+o[2]-lo[2]]); bl=bl[bl>0]
        M=np.isin(lab,bl)
        np.savez_compressed(f'a5_fin_{name}.npz',mask=M,origin=lo); print(name,'flesh pts',len(P),'membrane voxels',int(M.sum()))
if STAGE=='4':
    S=np.load('a5_S.npy',mmap_mode='r+')
    for name in ('dfin1','dfin2','anal'):
        d=np.load(f'a5_fin_{name}.npz'); M=d['mask']; lo=d['origin']; hi=lo+np.array(M.shape)
        lo2=np.maximum(lo,0); hi2=np.minimum(hi,[NZ,NV,NU])
        sub=np.asarray(S[lo2[0]:hi2[0],lo2[1]:hi2[1],lo2[2]:hi2[2]])
        sub|=M[lo2[0]-lo[0]:hi2[0]-lo[0],lo2[1]-lo[1]:hi2[1]-lo[1],lo2[2]-lo[2]:hi2[2]-lo[2]]
        S[lo2[0]:hi2[0],lo2[1]:hi2[1],lo2[2]:hi2[2]]=sub
    for k in range(NZ): S[k]=ndi.binary_fill_holes(S[k])
    S.flush()
    out=0; tot=0
    for k in range(0,NZ,50):
        b=np.asarray(F[k:k+50])>250; s=np.asarray(S[k:k+50]); out+=int((b&~s).sum()); tot+=int(b.sum())
    print('bone voxels',tot,'outside shell',out,round(out/tot*100,2),'%')

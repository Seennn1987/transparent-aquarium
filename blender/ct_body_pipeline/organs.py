# 体腔の臓器を、出典の配置と大きさで、展示の姿勢の体腔（膜の内側）に置く（organs_cav.py の後）
#   出典: Melero et al. 2023, Open Vet J 13(9):1071–1081（エボシカメレオン 17 頭、102.0 ± 16.8 g の CT）。
#   本文の配置（Results）と Table 1・3 の大きさ（中央値）。ここの数値の出所は ORGANS の各行
#   大きさの倍率 sL: 論文の心臓の VHS 4.61（長軸 + 短軸 = 16.7 + 9.1 mm を椎骨の長さで数えた値）から、論文の個体の椎骨は
#   25.8 / 4.61 = 5.60 mm。この CT の胴の椎骨（v04〜v12）は平均 4.61 mm。sL = 4.61 / 5.60 = 0.82
#   出典に大きさの無い臓器（胃・腸・結腸）と、中身の量は仮（PROVISIONAL）
import numpy as np, scipy.ndimage as nd, json, time, os
from scipy.spatial import cKDTree
from skimage import measure
import pyfqmr
t0=time.time()
z=np.load('organs_cav.npz'); I=z['inside']; lo=z['lo']; VOX=float(z['vox']); us=z['us']; AP=z['AP']; AV=z['AV']; AR=z['AR']; k=float(z['k'])
MM=k
J=np.load('J.npy')
SL=float(np.diff(J[3:12]).mean())/((16.7+9.1)/4.61)
U0=9.5          # 体腔の頭の端: 関節窩（肩）の体軸の位置（肋骨の籠の中で、いちばん前に心臓。Melero 2023）
UHIP=107.5      # 股関節の体軸の位置（展示の姿勢）
WALL=1.0        # 体の壁（膜の内側から）[mm]。仮
print('sL',round(SL,3))
# 体の座標
idx=np.argwhere(I); X=lo+idx*VOX
kt=cKDTree(AP); d_,ai=kt.query(X,workers=-1)
u=us[ai]; q=X-AP[ai]; vv=(q*AV[ai]).sum(1)/MM; rr=(q*AR[ai]).sum(1)/MM
depth_in=nd.distance_transform_edt(I)*0.25           # 膜からの深さ [mm]
din=depth_in[tuple(idx.T)]
# 手足を外す: 手足の骨の線から 3 mm 以内（肢帯は外さない）
P=np.load('pose_jar.npz'); bn=[str(x) for x in P['names']]; Mp=P['M']; H=P['head']; Tl=P['tail']
segs=[]
for n in bn:
    if n[:2] in ('fL','fR','hL','hR') and not n.endswith('girdle'):
        i=bn.index(n); a=H[i]@Mp[i][:3,:3].T+Mp[i][:3,3]; b=Tl[i]@Mp[i][:3,:3].T+Mp[i][:3,3]; segs.append((a,b))
limbd=np.full(len(X),1e9)
for a,b in segs:
    ab=b-a; t=np.clip(((X-a)@ab)/(ab@ab),0,1); limbd=np.minimum(limbd,np.linalg.norm(X-(a+t[:,None]*ab),axis=1)/MM)
cav=(din>WALL)&(vv>1.0)&(u>=U0)&(u<=UHIP+4)&(limbd>3.0)&(np.abs(rr)<12)
print('cavity voxels',int(cav.sum()),'volume mm3',round(cav.sum()*0.25**3,1), f'{time.time()-t0:.0f}s',flush=True)
# 輪切りごとの体腔の左右の中心（体軸の線は、膜の左右の中心から 1〜3 mm 左へずれている）と、腹の壁 Vw(u)
bins=np.arange(U0,UHIP+5,0.5); bi=np.digitize(u,bins)
def profile(fn, sig):
    out=np.full(len(bins)+1,np.nan)
    for j in np.unique(bi[cav]):
        m=cav&(bi==j)
        if m.sum()>50: out[j]=fn(m)
    ok=~np.isnan(out); out=np.interp(np.arange(len(out)),np.where(ok)[0],out[ok])
    return nd.gaussian_filter1d(nd.median_filter(out,9),sig)
Cc=profile(lambda m: 0.5*(np.percentile(rr[m],2)+np.percentile(rr[m],98)),4)
Ccu=lambda uu: np.interp(uu,bins,Cc[1:])
rr_axis=rr.copy()                              # 体軸（脊椎）からの左右
rr=rr-Ccu(u)                                   # ここから rr は体腔の左右の中心から
Vw=profile(lambda m: np.percentile(vv[m&(np.abs(rr)<3)],99) if (m&(np.abs(rr)<3)).sum()>20 else np.nan,4)
Wd=profile(lambda m: np.percentile(rr[m],98)-np.percentile(rr[m],2),4)
Vwu=lambda uu: np.interp(uu,bins,Vw[1:])
frac=(vv-1.0)/np.maximum(Vwu(u)-1.0,1e-6)      # 0 = 背（体軸の 1 mm 腹側）、1 = 腹の壁
for uu in (15,30,45,60,75,90,105): print('u',uu,'ventral wall vv %.1f'%Vwu(uu),'width %.1f'%np.interp(uu,bins,Wd[1:]),'centre %.1f'%Ccu(uu))
# 臓器（u, vv, rr は mm。大きさは論文の値 × sL）
s=SL
heart_end=U0+16.7*s
liver_end=heart_end+27.0*s
fat_end=liver_end+26.5*s
kid_end=UHIP+3.0
ORG={}
def ell(uc,vc,rc,L,Hh,W):
    return ((u-uc)/(L/2))**2+((vv-vc)/(Hh/2))**2+((rr-rc)/(W/2))**2
def ventral(uc,Hh): return Vwu(uc)-Hh/2
F={}
# 心臓: 体腔のいちばん前、肋骨の籠の中、胸骨に接する。長軸 16.7、短軸 9.1 mm（Table 3）。横断は丸い
F['heart']=ell(U0+16.7*s/2, ventral(U0+16.7*s/2,9.1*s), 0.0, 16.7*s, 9.1*s, 9.1*s)
# 肝臓: 頭側に心尖、背側に肺、尾側に腸と脂肪体、腹側は体腔の腹の壁に接する。右葉が大きい（Table 1: 右 27.0×10.4×9.9、左 19.9×7.8×7.4）
#   左右の葉の中心の横のずれ（±2.5 mm）は仮
F['liver_r']=ell(heart_end+27.0*s/2, ventral(heart_end+27.0*s/2,9.9*s), +2.5, 27.0*s, 9.9*s, 10.4*s)
F['liver_l']=ell(heart_end+19.9*s/2, ventral(heart_end+19.9*s/2,7.4*s), -2.5, 19.9*s, 7.4*s, 7.8*s)
# 胆嚢: 肝臓の尾腹側の縁、両葉の間、体腔の中ほどの腹側、やや右（7.2×5.5×4.0）。尾側の位置（右葉の 3/4）は仮
ug=heart_end+0.75*27.0*s; F['gallbladder']=ell(ug, ventral(ug,4.0*s), +1.0, 7.2*s, 4.0*s, 5.5*s)
# 脂肪体: 尾腹側、頭側に肝臓と肺、尾背側に腎臓と骨盤。左右一対の紡錘形で、腹側が広い三角の断面（右 26.5×6.4×6.1、左 25.3×6.3×6.2）
def fat(Lm,Wm,Hm,side):
    uc=liver_end+Lm*s/2; Lh=Lm*s/2; Hh=Hm*s; Wh=Wm*s/2
    along=np.clip(1-((u-uc)/Lh)**2,0,None)
    h=(Vwu(u)-vv)/Hh                                     # 0 = 腹の壁、1 = 頂
    width=Wh*(1-h)*np.sqrt(along)*1.5                    # 三角（底の幅 = Wm × 1.5 で、断面積は Wm×Hm の楕円に近い）
    return np.where((h>=0)&(h<=1)&(along>0), (np.abs(rr-side*(Wh+0.3))/np.maximum(width,1e-6))**2, 9.0)
F['fat_r']=fat(26.5,6.4,6.1,+1); F['fat_l']=fat(25.3,6.3,6.2,-1)
# 腎臓: 尾背側、背は脊椎、腹側に腸、頭側に生殖腺、尾側の極は骨盤の中（右 31.7×3.5×4.6、左 30.3×3.8×4.5）。尾の端（股関節 + 3 mm）は仮
# 左右は脊椎から（背は脊椎に接する）
def ell_ax(uc,vc,rc,L,Hh,W):
    return ((u-uc)/(L/2))**2+((vv-vc)/(Hh/2))**2+((rr_axis-rc)/(W/2))**2
F['kidney_r']=ell_ax(kid_end-31.7*s/2, 1.0+4.6*s/2, +(3.5*s/2+0.3), 31.7*s, 4.6*s, 3.5*s)
F['kidney_l']=ell_ax(kid_end-30.3*s/2, 1.0+4.5*s/2, -(3.8*s/2+0.3), 30.3*s, 4.5*s, 3.8*s)
# 管: 胃（頭背側、肝臓の背側、細長い管）・腸（尾腹側）・結腸（骨盤へ）。太さと道筋は仮（出典に大きさが無い）
def tube(path, rad):
    path=np.asarray(path,float); kd=cKDTree(path); dd,_=kd.query(np.stack([u,vv,rr],1),workers=-1); return (dd/rad)**2
def pts(fu,fv,fr,n=400):
    t=np.linspace(0,1,n); return np.stack([fu(t),fv(t),fr(t)],1)
st0=heart_end-1; st1=liver_end-2
# 標本では肺が縮む（Klaver 1973, Beaufortia 20: 164–169）。胃は肝臓の背側の、縮んだ肺のすぐ腹側（深さ 0.2、仮。参考写真の塊の背の縁が脊椎に接する）
F['stomach']=tube(pts(lambda t: st0+(st1-st0)*t, lambda t: 1.0+0.2*(Vwu(st0+(st1-st0)*t)-1.0), lambda t: -1.0+0*t), 2.0)
# 腸: 尾腹側の、肝臓（頭側）・肺（頭背側）・腎臓と骨盤（尾背側）の間（Melero 2023）。腸の区分は CT でも分けられない（同）。
#   標本では肺が縮み（Klaver 1973）、参考写真 5 枚（docs/chameleon_ct_body/organs_ref_compare の出典）の塊は
#   肩→股の t 0.20〜0.95、背→腹の深さ 0〜0.86（中央値）。腸はその範囲の、肝臓の後ろから腎臓の手前までを
#   曲がりくねる管（太さ 1.3 mm、仮）で埋める
i0=liver_end-3; i1=kid_end-10
# うねりは決まった種のなめらかな乱数（規則正しい波だと作り物に見える）。振れ幅と細かさは仮
rng_i=np.random.default_rng(2023)
def wander(n, amp, corr):
    w=nd.gaussian_filter1d(rng_i.standard_normal(n),corr,mode='nearest'); return amp*w/np.abs(w).max()
# 腸のうねり（2026-10-14 の 2 回目）: 体軸に沿う 16 本の管は、画面で規則正しい縞に見えた（写真 01 はまだらの塊）。
#   腸は曲がりくねる管なので、前後・背腹・左右の 3 つの向きに周期の違う波（リサージュ）で折り返す 6 本の管にする。
#   周期・振れ幅・本数は仮（出典に腸の道筋は無い）
paths=[]
for k_ in range(8):
    n=3000; s_=np.linspace(0,1,n); ph=rng_i.uniform(0,2*np.pi,3)
    fu_,fv_,fr_=rng_i.uniform(2.5,4.0), rng_i.uniform(7,11), rng_i.uniform(5,9)
    # 管ごとに範囲を少しずつ変える（同じ箱を埋めると、塊の縁が四角くなった）
    uc_=rng_i.uniform(0.40,0.60); ua_=rng_i.uniform(0.25,0.45); vc_=rng_i.uniform(0.28,0.50); va_=rng_i.uniform(0.12,0.30); ra_=rng_i.uniform(2.5,4.8)
    uu_=i0+(i1-i0)*(uc_+ua_*np.sin(2*np.pi*fu_*s_+ph[0])+wander(n,0.05,60))
    fvv=vc_+va_*np.sin(2*np.pi*fv_*s_+ph[1])+wander(n,0.05,40)
    rr_=ra_*np.sin(2*np.pi*fr_*s_+ph[2])+wander(n,0.6,40)
    paths.append(np.stack([uu_, 1.0+fvv*(Vwu(uu_)-1.0), rr_],1))
F['intestine']=np.minimum.reduce([tube(p_,1.3) for p_ in paths])
F['intestine']=np.where((frac>=0.03)&(frac<=0.88),F['intestine'],9.0)
# 結腸: 腸の尾端から骨盤（総排泄腔）へ。結腸は中身があると見分けられる（Melero 2023）。太さ 2 mm と道筋は仮
c0=i1-2; c1=kid_end
F['colon']=tube(pts(lambda t: c0+(c1-c0)*t, lambda t: (Vwu(c0)-3.5)*(1-t)+(4.5)*t, lambda t: 0*t), 2.0)
PRI=['heart','kidney_r','kidney_l','gallbladder','liver_r','liver_l','fat_r','fat_l','stomach','colon','intestine']
lab=np.zeros(len(X),np.int16)
for j,n in enumerate(PRI,1):
    m=cav&(lab==0)&(F[n]<=1.0); lab[m]=j
# 中身（消化管の中の内容物）: 管の芯に近い所の、ゆっくり変わる値（決まった種）が閾より上。量は仮
rng=np.random.default_rng(1013)
noise=nd.gaussian_filter(rng.standard_normal(I.shape).astype(np.float32),5)
noise/=noise.std()
nz=noise[tuple(idx.T)]
gut=np.isin(lab,[PRI.index(n)+1 for n in ('stomach','intestine','colon')])
core=np.zeros(len(X),bool)
for n in ('stomach','intestine','colon'): core|=(lab==PRI.index(n)+1)&(F[n]<=0.55)
content=gut&core&(nz>0.0)
names=PRI+['contents']
lab[content]=len(names)
for j,n in enumerate(names,1): print(n,'voxels',int((lab==j).sum()),'mm3',round((lab==j).sum()*0.25**3,1))
lung=cav&(lab==0)
print('rest of the cavity (lungs and air sacs, not drawn) mm3',round(lung.sum()*0.25**3,1),'share of cavity',round(lung.sum()/cav.sum(),2))
L3=np.zeros(I.shape,np.int16); L3[tuple(idx.T)]=lab
np.savez_compressed('organs_lab.npz',lab=L3,names=np.array(names),lo=lo,vox=VOX,lung=np.packbits(np.zeros(1,bool)))
Lg=np.zeros(I.shape,bool); Lg[tuple(idx[lung].T)]=True; np.save('organs_lung.npy',Lg)
print('done',f'{time.time()-t0:.0f}s')

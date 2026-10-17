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
# 2026-10-16（プロデューサー「胴の表面に不自然な凹凸があったり、波打ったりしています。そんなサメいないですよね。もう一度自己検証して修正方針を立てて」→「進めて」）:
#  HH_SHELL_FIT=smooth で、120〜720 mm の断面を、上の「60° の中央値で切る」代わりに、なめらかな閉じた曲線で当てる（計画書 第 9 節「胴の表面の凹凸の自己検証」）。
#  中央値で切ると、背骨から遠い腹（CT で 76〜79 mm）が横の値まで削られ（54〜58 mm）、切り口が約 57 mm おきに波打っていた。
#   - 断面ごとに、左右対称の項（1, sinθ, cos2θ, sin3θ, cos4θ, sin5θ, cos6θ。θ は横 0°・腹 90°）を当てる。曲線より 2.5 mm より外に出た所
#     （背びれ・臀びれ・腹びれの肉）は重みを 0.05 にして当て直す（5 回）
#   - 胸びれの肉が垂れた区間（CT の 205〜290 mm、腹が 107〜115 mm に飛ぶ）は、前後の断面の係数を直線でつなぐ
#   - 係数を体軸方向に σ 20 mm（HH_SHELL_SIGMA）でならす。115〜135 mm と 690〜720 mm で前のやり方と混ぜる
import os as _os2
if _os2.environ.get('HH_SHELL_FIT')=='smooth':
    _A=np.stack([np.ones(NT),np.sin(TH),np.cos(2*TH),np.sin(3*TH),np.cos(4*TH),np.sin(5*TH),np.cos(6*TH)],1)
    _C=np.zeros((len(zs),_A.shape[1]))
    for i in range(len(zs)):
        r=(R[i]+R[i][mirror])/2; w=(r>0).astype(float)
        if w.sum()<20: continue
        for _ in range(5):
            c=np.linalg.lstsq(_A*w[:,None],r*w,rcond=None)[0]; res=r-_A@c
            w=np.where(r<=0,0,np.where(res>2.5,0.05,1.0))
        _C[i]=c
    _a,_b=np.searchsorted(zmm,205),np.searchsorted(zmm,290)
    for j in range(_C.shape[1]): _C[_a:_b,j]=np.interp(zmm[_a:_b],[zmm[_a-1],zmm[_b]],[_C[_a-1,j],_C[_b,j]])
    _Cs=ndi.gaussian_filter1d(_C,float(_os2.environ.get('HH_SHELL_SIGMA',20))/(STEP*VX),axis=0,mode='nearest')   # HH_SHELL_SIGMA mm（既定 20。10 では 90 mm おきの ±1.5 mm の波が残った）
    _Rf=np.maximum(_Cs@_A.T,0.5)
    _t=np.clip((zmm-115)/20,0,1)*(1-np.clip((zmm-690)/30,0,1))
    Rs=(1-_t[:,None])*Rs+_t[:,None]*_Rf

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
# 2026-10-16 案（プロデューサー「胴の幅（第 1 背びれのあたりを一番太く）と後ろ半分の長さの案…を作って」）: HH_TRUNK_PROFILE=photo で、
#  上から見た胴の幅（ひれの膜なし）を、いただいた背中からの写真を目で読んだ全長比の幅（計画書 第 9 節「胴の形と長さ…の検証」、
#  a9_body_shape_check.jpg の青の点）に合わせる: 0.19 で 0.111、0.33 で 0.130（第 1 背びれのすぐ後ろでいちばん広い）、0.42 で 0.112、
#  0.56 で 0.092、0.65 で 0.057（ここはいまのモデルとほぼ同じ）。間は単調な 3 次（PCHIP）でつなぐ。
#  全長比は縮めた後の全長（hh_warp.py の HH_BODY_SHRINK）で数える。頭のすぐ後ろ 125 mm はいまの幅（102 mm）から始め、0.65 より後ろは前の倍率へ 30 mm で戻す
_old=_K.copy()
if _os.environ.get('HH_TRUNK_PROFILE')=='photo':
    import hh_warp
    from scipy.interpolate import PchipInterpolator
    TLf=hh_warp.TL; _zf=hh_warp.warp_mm(_zk)
    _fr=np.array([0.19,0.33,0.42,0.56,0.65]); _wf=np.array([0.111,0.130,0.112,0.092,0.057])
    _W=PchipInterpolator(np.r_[125.0,_fr*TLf],np.r_[TW,_wf*TLf])(np.clip(_zf,125.0,0.65*TLf))
    _kp=np.clip(_W/np.maximum(np.interp(_zk,zmm,ct_w),1),0.7,2.4)
    _zE=float(hh_warp.unwarp_mm(0.65*TLf))
    _a=np.clip((_zk-115)/10,0,1); _b=np.clip((_zk-_zE)/30,0,1)
    _K=np.where(_zk<125,(1-_a)+_a*_kp,np.where(_zk<_zE,_kp,(1-_b)*_kp+_b*_old))
    _K=np.where(_zk<115,_old,ndi.gaussian_filter1d(_K,3))
    if STAGE=='2':
        _w=np.interp(_zk,zmm,ct_w)
        json.dump(dict(z_mm=_zk[::5].tolist(),width_old_mm=np.round((_w*_old)[::5],2).tolist(),width_new_mm=np.round((_w*_K)[::5],2).tolist(),
                       tl_mm=TLf,source='photo profile (a9_body_shape_check)'),open('a5_trunk_width.json','w'))
# 2026-10-16 案（プロデューサー「胴の形状がまだ違います。画像や文献からあなた自身で調査し相違点を説明して」→ 説明に「了承します」）:
#  HH_TRUNK_PROFILE=ref で、胴の幅と高さを参考の図に合わせる（計画書 第 9 節「胴の形の相違点の調査」、a9_body_shape_refs.jpg）。
#   幅（上から、全長比）: FMIB 51331 の図（パブリックドメイン）。0.14 で 0.063、0.20 で 0.079、0.36 で 0.103、0.42 で 0.092、0.46 で 0.084、
#    0.50 で 0.073、0.56 で 0.058、0.60 で 0.047、0.66 で 0.035、0.70 で 0.025。首（0.16 より前）は CT の幅より細くしない（顎・舌の弓・エラの骨を膜の中に残す）、
#    尾柄は CT の 0.85 倍まで
#   高さ（横から、全長比）: Duane Raver の図（パブリックドメイン）。0.13 で 0.091、0.15 で 0.098、0.17 で 0.094、0.20 で 0.100、0.27 で 0.123、
#    0.38 で 0.112、0.42 で 0.102、0.45 で 0.090、0.50 で 0.080、0.55 で 0.067、0.60 で 0.059、0.68 で 0.037。
#    0.25〜0.45 は背の側だけを足す（参考の図では腹の線はモデルとほぼ同じで、背が背びれへ上がる）。ほかは背と腹を同じ割合で
#   尾びれの下の葉: 腹の側を 720〜820 mm で最大 HH_TRUNK_LOBE 倍（既定 1.35、760 mm で最大）。Raver の図の下の葉は全長比 0.085 まで下がる（モデル 0.06）
#  HH_TRUNK_MIX（既定 1）: 0.5 でいまの形との中間
_KD=np.ones_like(_zk); _KB=np.ones_like(_zk)
if _os.environ.get('HH_TRUNK_PROFILE')=='ref':
    import hh_warp
    from scipy.interpolate import PchipInterpolator
    MIX=float(_os.environ.get('HH_TRUNK_MIX',1.0)); TLf=hh_warp.TL; _f=hh_warp.warp_mm(_zk)/TLf
    _fw=np.array([0.14,0.20,0.36,0.42,0.46,0.50,0.56,0.60,0.66,0.70]); _ww=np.array([0.063,0.079,0.103,0.092,0.084,0.073,0.058,0.047,0.035,0.025])
    _Wt=PchipInterpolator(_fw,_ww)(np.clip(_f,_fw[0],_fw[-1]))*TLf
    _cw=np.maximum(np.interp(_zk,zmm,ct_w),1)
    _kr=_Wt/_cw; _kr=np.maximum(_kr,np.where(_f<0.16,1.0,0.85))
    _a=(np.clip((_zk-115)/60,0,1) if _os.environ.get('HH_SHELL_FIT')=='smooth' else np.clip((_zk-125)/15,0,1))*(1-np.clip((_f-0.70)/0.04,0,1))   # smooth: 115〜175 mm でゆっくり（首の段を作らない）
    _K=_old+MIX*_a*(_kr-_old)
    _K=np.where(_zk<115,_old,ndi.gaussian_filter1d(_K,3))
    # 高さ
    _ang=np.degrees(TH)
    _Dd=np.array([(-Rs[i]*np.sin(TH)).max() for i in range(len(zs))]); _Db=np.array([(Rs[i]*np.sin(TH)).max() for i in range(len(zs))])
    Dd=np.maximum(np.interp(_zk,zmm,_Dd),1); Db=np.maximum(np.interp(_zk,zmm,_Db),1)
    _fd=np.array([0.13,0.15,0.17,0.20,0.27,0.38,0.42,0.45,0.50,0.55,0.60,0.68]); _dd=np.array([0.091,0.098,0.094,0.100,0.123,0.112,0.102,0.090,0.080,0.067,0.059,0.037])
    _Dt=PchipInterpolator(_fd,_dd)(np.clip(_f,_fd[0],_fd[-1]))*TLf
    kboth=_Dt/(Dd+Db); kback=(_Dt-Db)/Dd
    wb=np.clip((_f-0.22)/0.06,0,1)*(1-np.clip((_f-0.42)/0.06,0,1))
    kd=(1-wb)*kboth+wb*kback; kb=(1-wb)*kboth+wb*1.0
    _g=(np.clip((_zk-110)/80,0,1) if _os.environ.get('HH_SHELL_FIT')=='smooth' else np.clip((_zk-120)/15,0,1))*(1-np.clip((_f-0.68)/0.03,0,1))
    kd=1+_g*(np.clip(kd,0.8,2.0)-1); kb=1+_g*(np.clip(kb,0.8,2.0)-1)
    LOBE=float(_os.environ.get('HH_TRUNK_LOBE',1.35))
    kb=kb*(1+(LOBE-1)*np.interp(_zk,[705,770,840] if _os.environ.get('HH_SIDE_SMOOTH') else [720,760,820],[0,1,0]))   # 案 2: 尾柄の下の段（波 6）を作らないよう、立ち上がりをゆっくり
    _KD=ndi.gaussian_filter1d(1+MIX*(kd-1),4); _KB=ndi.gaussian_filter1d(1+MIX*(kb-1),4)
    if STAGE=='2':
        _w=np.interp(_zk,zmm,ct_w)
        json.dump(dict(z_mm=_zk[::5].tolist(),width_old_mm=np.round((_w*_old)[::5],2).tolist(),width_new_mm=np.round((_w*_K)[::5],2).tolist(),
                       dtop_mm=np.round((Dd*(_KD-1))[::5],2).tolist(),dbot_mm=np.round((Db*(_KB-1))[::5],2).tolist(),
                       tl_mm=TLf,mix=MIX,source='ref profile (FMIB 51331 width, Duane Raver depth)'),open('a5_trunk_width.json','w'))
def kdv(z): return float(np.interp(z,_zk,_KD)), float(np.interp(z,_zk,_KB))
def kfac(z): return float(np.interp(z,_zk,_K))
# 2026-10-16 案 2（プロデューサー「真横から見た時に背中側もお腹側も体がまだまだボコボコと波打っていますよ…本ものはもっと流線的です」→「案２」）:
#  HH_SIDE_SMOOTH=背,腹（mm、例 40,90）で、横から見た背の線（断面のいちばん上）と腹の線（いちばん下）を、体軸方向にその長さでならした線にそろえる。
#  断面ごとに、背骨の高さより上を背の線まで、下を腹の線まで伸び縮みさせる（向きでなめらかに混ぜる）。120〜150 mm と 690〜720 mm で効き目を 0 へ
SIDE=_os.environ.get('HH_SIDE_SMOOTH')
_SIDEF={}
def _trunk_poly(z,kx,kd_,kb_):
    r=np.array([np.interp(z,zmm,Rs[:,j]) for j in range(NT)]); vc=vc_of(z)
    pu=r*np.cos(TH)*kx; pv=r*np.sin(TH)*((kd_+kb_)/2+(kb_-kd_)/2*np.sin(TH) if _os.environ.get('HH_SHELL_FIT')=='smooth' else np.where(np.sin(TH)<0,kd_,kb_))+vc
    if _os.environ.get('HH_SHELL_FIT')=='smooth' and 120<=z<700:
        from scipy.spatial import ConvexHull
        _h=ConvexHull(np.c_[pu,pv]).vertices; pu,pv=pu[_h],pv[_h]
    return pu,pv,vc
def _side_fit(z,pu,pv,vc):
    f=_SIDEF.get(int(round(z/VX)))
    if f is None: return pv
    sd,sb=f; d=pv-vc; sn=d/np.maximum(np.hypot(pu,d),1e-6)
    return vc+d*((sd+sb)/2+(sb-sd)/2*sn)
if SIDE and STAGE=='2':
    _sb_,_sv_=[float(x) for x in SIDE.split(',')]
    _ks=np.arange(int(120/VX),int(720/VX)); _tp=[];_bt=[];_vc=[]
    for k in _ks:
        z=k*VX; _kd,_kb=kdv(z); pu,pv,vc=_trunk_poly(z,kfac(z),_kd,_kb); _tp.append(pv.min()); _bt.append(pv.max()); _vc.append(vc)
    _tp=np.array(_tp); _bt=np.array(_bt); _vc=np.array(_vc)
    _Tt=ndi.gaussian_filter1d(_tp,_sb_/VX,mode='nearest'); _Tb=ndi.gaussian_filter1d(_bt,_sv_/VX,mode='nearest')
    _zk2=_ks*VX; _w=np.clip((_zk2-120)/30,0,1)*np.clip((720-_zk2)/30,0,1)
    _sd=1+_w*((_vc-_Tt)/np.maximum(_vc-_tp,1)-1); _sbb=1+_w*((_Tb-_vc)/np.maximum(_bt-_vc,1)-1)
    _SIDEF={int(k):(float(a),float(b)) for k,a,b in zip(_ks,_sd,_sbb)}
    json.dump(dict(z_mm=_zk2[::4].round(2).tolist(),top_mm=_tp[::4].round(2).tolist(),top_target_mm=_Tt[::4].round(2).tolist(),bot_mm=_bt[::4].round(2).tolist(),bot_target_mm=_Tb[::4].round(2).tolist(),sigma_mm=[_sb_,_sv_]),open('a5_side_fit.json','w'))
    print('side fit: max move top %.1f bottom %.1f mm'%(np.abs(_w*(_Tt-_tp)).max(),np.abs(_w*(_Tb-_bt)).max()))
if STAGE=='2':
    S=np.lib.format.open_memmap('a5_S.npy',mode='w+',dtype=np.bool_,shape=(NZ,NV,NU))
    S0=np.lib.format.open_memmap('a5_S0.npy',mode='w+',dtype=np.bool_,shape=(NZ,NV,NU))
    for k in range(NZ):
        z=k*VX
        NB0,NB1=(100.0,140.0) if _os.environ.get('HH_SHELL_FIT')=='smooth' else (115.0,115.0)
        if z<NB1:
            # 頭: 翼の後ろの端は断面で左右の離れた島になるので、最大の塊だけでなく 30 ボクセル以上の塊をすべて残す
            m=ndi.binary_fill_holes(np.asarray(F[k])>-400); lab,n=ndi.label(m)
            if n:
                sz=ndi.sum(m,lab,range(1,n+1)); m=np.isin(lab,1+np.nonzero(sz>=30)[0]); m=m|m[:,::-1]
            if z<NB0: S[k]=m; S0[k]=m; continue
            # 口の中の空洞は 142 mm まで外へ開いていて、142.6 mm で閉じる。穴を埋める前に小さな口を閉じないと、そこで断面が 5 割増しに跳び、輪の線になった
            #  → 体の正中に近い塊（重心が正中から 50 mm 以内）をまとめて外形で包む（翼の端の離れた島はそのまま）
            from skimage.morphology import convex_hull_image
            _lb,_n=ndi.label(m)
            if _n:
                _cu=np.array(ndi.center_of_mass(m,_lb,range(1,_n+1)))[:,1]*VX+U0
                _mid=np.isin(_lb,1+np.nonzero(np.abs(_cu)<50)[0])
                if _mid.any(): mh=(m&~_mid)|convex_hull_image(_mid)
                else: mh=m
            else: mh=m
            # 2026-10-16 HH_SHELL_FIT=smooth: 100〜140 mm で（CT の頭の断面は 142.6 mm で横へ ±41 → ±64 mm に跳ぶので、その前で胴へ移り終える）、頭の断面（CT）と胴の曲線を符号つき距離で少しずつ混ぜる（115 mm の段をなくす）
            r=np.array([np.interp(z,zmm,Rs[:,j]) for j in range(NT)]); kk=kfac(z); vc=vc_of(z); _kd,_kb=kdv(z)
            tr=np.zeros((NV,NU),bool)
            pu=r*np.cos(TH)*kk; pv=r*np.sin(TH)*((_kd+_kb)/2+(_kb-_kd)/2*np.sin(TH))+vc
            if z>=120:
                from scipy.spatial import ConvexHull
                _h=ConvexHull(np.c_[pu,pv]).vertices; pu,pv=pu[_h],pv[_h]
            pv=_side_fit(z,pu,pv,vc)
            rr,cc=skpoly((pv-V0)/VX,(pu-U0)/VX,shape=(NV,NU)); tr[rr,cc]=True
            sd=lambda a: ndi.distance_transform_edt(~a)-ndi.distance_transform_edt(a)
            t=(z-NB0)/(NB1-NB0); t=t*t*(3-2*t)
            mm=((1-t)*((1-t)*sd(m)+t*sd(mh))+t*sd(tr))<0   # 100 mm では CT の頭の断面そのもの → 包んだ形 → 胴の曲線
            S[k]=mm; S0[k]=mm; continue
        r=np.array([np.interp(z,zmm,Rs[:,j]) for j in range(NT)]); kk=kfac(z); vc=vc_of(z)
        if r.max()<1: continue
        _kd,_kb=kdv(z)
        for arr,kx,kd_,kb_ in ((S0,1.0,1.0,1.0),(S,kk,_kd,_kb)):
            pu,pv,_=_trunk_poly(z,kx,kd_,kb_)   # 胴の断面は外へ膨らんだ形（ひれは別に足す）。くびれを残さず外形で包む（HH_SHELL_FIT=smooth）
            if arr is S: pv=_side_fit(z,pu,pv,vc)
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
        if name=='dfin1' and _os.environ.get('HH_FIN_PLATE')=='1': continue   # 第 1 背びれは板の面に置き換える（a6a_export_gltf.py）
        d=np.load(f'a5_fin_{name}.npz'); M=d['mask']; lo=d['origin']
        # 背と腹を足した案（HH_TRUNK_PROFILE=ref）: 背びれの膜は背の上がった分だけ上へ、臀びれの膜は腹の下がった分だけ下へ動かす（体軸の断面ごと）
        if _os.path.exists('a5_trunk_width.json') and 'dtop_mm' in json.load(open('a5_trunk_width.json')):
            _T=json.load(open('a5_trunk_width.json')); PAD=60
            M2=np.zeros((M.shape[0],M.shape[1]+2*PAD,M.shape[2]),bool)
            for j in range(M.shape[0]):
                zz=(lo[0]+j)*VX
                dv=-np.interp(zz,_T['z_mm'],_T['dtop_mm']) if name!='anal' else np.interp(zz,_T['z_mm'],_T['dbot_mm'])
                sh=int(round(dv/VX)); M2[j,PAD+sh:PAD+sh+M.shape[1]]=M[j]
            M=M2; lo=lo-np.array([0,PAD,0])
        # 案 2: 背びれ・臀びれの膜は正中から ±HH_FIN_HALF mm（例 3）の板にする。付け根の厚い肉が、横から見ると背びれの前後の盛り上がり（波 2・3）になっていた
        if _os.environ.get('HH_FIN_HALF'):
            _uu=U0+(lo[2]+np.arange(M.shape[2]))*VX; M=M&(np.abs(_uu)<=float(_os.environ['HH_FIN_HALF']))[None,None,:]
        hi=lo+np.array(M.shape)
        lo2=np.maximum(lo,0); hi2=np.minimum(hi,[NZ,NV,NU])
        sub=np.asarray(S[lo2[0]:hi2[0],lo2[1]:hi2[1],lo2[2]:hi2[2]])
        sub|=M[lo2[0]-lo[0]:hi2[0]-lo[0],lo2[1]-lo[1]:hi2[1]-lo[1],lo2[2]-lo[2]:hi2[2]-lo[2]]
        S[lo2[0]:hi2[0],lo2[1]:hi2[1],lo2[2]:hi2[2]]=sub
    # 2026-10-17 案（プロデューサー「第 1 背びれ・第 2 背びれ・胸びれ・腹びれ・臀びれの 5 つとも、直し案を作ってブラウザで並べて見せてください」）:
    #  HH_FIN_REF=1 で、背びれ 2 つと臀びれの膜を、横からの参考の図 2 枚（Duane Raver、FMIB 45527、パブリックドメイン）の外形の大きさで足す。
    #  CT の膜はひれの根元しか写っていなかった（横から見て体の線から出る高さ: 第 1 背びれ 0.070・第 2 背びれ 0.006・臀びれ 0.006、参考 0.119〜0.129・0.018〜0.023・0.029〜0.034、全長比）。
    #  外形は、付け根（前の端 o〜後ろの端 i、全長比）で割った s と、高さ H（全長比）で割った値の多角形。付け根の位置は CT のひれの軟骨と参考の図から:
    #   第 1 背びれ: o 0.261・i 0.380（CT の軟骨）、H 0.124（参考の平均）。鎌形（前の縁は丸く立ち上がり、頂点は後ろ寄り、後ろの縁は切れ込み、細い後端が 1.33 まで）
    #   第 2 背びれ: o 0.605・i 0.645（参考の起点、CT の軟骨の後ろの端）、H 0.020。低く、後端が長い（1.8 まで。参考 2 枚とも 0.67〜0.68 まで伸びる）
    #   臀びれ: o 0.595・i 0.635、H 0.031。後ろの縁は深く切れ込む（ICCAT・FAO の記述）
    #  膜は正中の板（半分の厚さ 3 mm から先へ 1.6 mm まで細る。1.1 mm では面を作るときのぼかしで先が削れ、第 1 背びれが 0.104 にしかならなかった）で、横から見た背と腹の線（a5_side_fit.json）から 4 mm 体の中から立てる
    if _os.environ.get('HH_FIN_REF')=='1' and _os.path.exists('a5_side_fit.json'):
        from matplotlib.path import Path as _Path
        _SF=json.load(open('a5_side_fit.json')); TLm=1024.0
        import hh_fins; FINS={k:v for k,v in hh_fins.FINS.items() if not (k=='dfin1' and _os.environ.get('HH_FIN_PLATE')=='1')}   # 外形は hh_fins.py。第 1 背びれは体積の格子（正中から上へ 150 mm まで）から出るので、HH_FIN_PLATE=1 では a6a_export_gltf.py で板の面にする
        uu=U0+np.arange(NU)*VX; added=0
        for name,fd in FINS.items():
            pth=_Path(fd['poly']+[(0,0)]); Lb=(fd['i']-fd['o'])*TLm; Hm=fd['H']*TLm; smax=max(p_[0] for p_ in fd['poly'])
            hs=np.arange(-4.0,Hm+0.5,0.35)
            for k in range(int(fd['o']*TLm/VX),int((fd['o']*TLm+smax*Lb)/VX)+2):
                z=k*VX; sv=(z-fd['o']*TLm)/Lb
                line=np.interp(z,_SF['z_mm'],_SF['top_target_mm'] if fd['side']<0 else _SF['bot_target_mm'])
                inside=pth.contains_points(np.c_[np.full(len(hs),sv),np.maximum(hs,0)/Hm])|((hs<=0)&(sv>=0)&(sv<=1))
                if not inside.any(): continue
                sl=np.asarray(S[k]).copy()
                for h in hs[inside]:
                    t=max(1.6,3.0*(1-0.6*max(h,0)/Hm)); iv=int(round((line+fd['side']*h-V0)/VX))
                    if 0<=iv<NV: sl[iv,np.abs(uu)<=t]=True
                S[k]=sl; added+=1
            print('fin ref',name,'slices',added)
    for k in range(NZ): S[k]=ndi.binary_fill_holes(S[k])
    S.flush()
    out=0; tot=0
    for k in range(0,NZ,50):
        b=np.asarray(F[k:k+50])>250; s=np.asarray(S[k:k+50]); out+=int((b&~s).sum()); tot+=int(b.sum())
    print('bone voxels',tot,'outside shell',out,round(out/tot*100,2),'%')

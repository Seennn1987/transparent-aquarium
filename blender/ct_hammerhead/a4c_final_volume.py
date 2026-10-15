# A4: A3 の直しをすべて重ねた「最終の座標」で、骨の体積を 0.735 mm の格子に作り直す
#  最終の座標の 1 点 (z, u, v) [mm] から、A3 の直しを逆にたどって元の CT（zyg_clean）の点を求め、
#  CT の値（線形補間）と骨の塊の番号（最も近い点）を取る。
#  逆にたどる順: 頭の鏡映 → 頭〜胸の倒れ（neck_roll） → 頭の横向き（head_yaw） → 尾の反り（tail_bend）
#              → 尾の背腹のずれ（tail_keep） → 体を起こす（derolled2：倒れ tilt_sym と背骨の線 spine_line）
#  骨にしない塊: 表面の線（2670, 3867, 784, 827）、姿勢を決め直したひれの元（833, 1341, 3064, 3149, 3077, 3067）、
#               100 ボクセル未満の小さな塊。ひれは決定後の点（pect_posed, pelvic_posed）から別の体積にする
import hh_paths, os; hh_paths.cd_work()
import numpy as np, json, sys, time
from scipy.ndimage import map_coordinates, binary_dilation, gaussian_filter
VX=0.735; Z0,Z1=0.0,1046.0; U0,U1=-180.0,180.0; V0,V1=-150.0,120.0
NZ=int((Z1-Z0)/VX); NU=int((U1-U0)/VX); NV=int((V1-V0)/VX)
C=np.load('zyg_clean.npy'); L=np.load('skel_lab.npy',mmap_mode='r')
cxs,cys=np.load('spine_line.npy'); tilt=np.load('tilt_sym.npy'); keep=np.load('tail_keep_v.npy')
off=np.load('tail_bend_offset_mm.npy'); roll=np.load('neck_roll_deg.npy'); hy=json.load(open('head_yaw.json'))
sizes=np.load('skel_sizes.npy')
DROP={2670,3867,784,827,833,1341,3064,3149,3077,3067,1546,4513,4302}   # 1546・4513・4302 は a4_median_fins.py で立て直したものを別に使う
okl=np.zeros(len(sizes)+1,bool); okl[1:]=sizes>=100
for d in DROP: okl[d]=False
# 元の CT で、骨にしない塊のボクセルを先に消しておく（補間で縁が残らないように 1 ボクセル広げて消す）
from scipy.ndimage import binary_dilation as _bd
for z0 in range(0,C.shape[0],200):
    Lb=np.asarray(L[max(z0-1,0):z0+201]); bad=(Lb>0)&(~okl[Lb]); bad=_bd(bad)
    sl=slice(max(z0-1,0),z0+201); cb=C[sl]; cb[bad&(cb>-200)]=-200; C[sl]=cb
HEAD_SCALE=float(os.environ.get("HH_HEAD_MM",340.0))/340.0   # 2026-10-15 プロデューサー決定「３３％、青緑」: 頭の幅は全長の 33%（CT の個体のまま、340 mm。前は 2026-10-14 決定の 26%＝266 mm）。頭（〜130 mm）の左右だけを縮め、130〜160 mm でなめらかにつなぐ。HH_HEAD_MM で案（2026-10-15、プロデューサー「頭の大きさが体のサイズに比べて小さくないでしょうか？」）
# 2026-10-14 直し: 頭の幅の決定は翼のこと。正中から 45 mm までの中央（頭骨の中央・顎・歯）は縮めず、
#  45〜60 mm で縮め方をなめらかに変え、その外の翼だけを縮める（片側 170 → 133 mm は前と同じ）。前は顎も 26% 細くなっていた
HS_A,HS_B,HS_HALF=45.0,15.0,170.0
HS_K=(HS_HALF*HEAD_SCALE-HS_A-HS_B/2)/(HS_HALF-HS_A-HS_B/2)
_hs_u=np.linspace(0,400,4001)
_hs_d=np.where(_hs_u<HS_A,1.0,np.where(_hs_u<HS_A+HS_B,1-(1-HS_K)*(_hs_u-HS_A)/HS_B,HS_K))
_hs_f=np.r_[0,np.cumsum((_hs_d[1:]+_hs_d[:-1])/2*np.diff(_hs_u))]   # 縮めたあとの |u|（元の |u| の関数）
def head_unscale(z,u):
    w=np.clip((z-130)/30,0,1); w=w*w*(3-2*w)
    a=np.abs(u); src=np.interp(a,_hs_f,_hs_u)        # 頭（w=0）での元の |u|
    return np.sign(u)*((1-w)*src+w*a)
def inv(z,u,v):
    u=head_unscale(z,u)
    # 頭の鏡映は呼び出し側で（鏡映した点と、しない点の両方を引いて混ぜる）
    a=np.radians(np.interp(z,np.arange(len(roll)),roll)); ca,sa=np.cos(a),np.sin(a)
    u,v=u*ca-v*sa, u*sa+v*ca                                                    # 倒れを戻した分を逆に
    w=np.where(z<=130,1.0,np.clip(1-(z-130)/40,0,1)); w=w*w*(3-2*w)
    th=np.radians(hy['yaw_deg'])*w; pu=hy['offset_u_mm']*w; dz=z-hy['pivot_z_mm']
    z,u=hy['pivot_z_mm']+dz*np.cos(th)-u*np.sin(th), dz*np.sin(th)+u*np.cos(th)+pu   # 頭の横向き
    v=v+np.interp(z,np.arange(len(off)),off)                                    # 尾の反り
    zr=np.clip(z*2,0,len(cxs)-1)
    v=v-np.interp(zr,np.arange(len(keep)),keep)                                 # 尾の背腹のずれ
    t=np.radians(np.interp(zr,np.arange(len(tilt)),tilt)); c,s=np.cos(t),np.sin(t)
    x=(u*c-v*s)/0.735+np.interp(zr,np.arange(len(cxs)),cxs); y=(u*s+v*c)/0.735+np.interp(zr,np.arange(len(cys)),cys)
    return zr,y,x
# 2026-10-14 A6: 椎骨の列（a2b_split_head_spine.py の m_spine。背骨の線から 13 px 以内の軸の塊）を別の体積にする
#  Eames et al. 2007 の胚では椎骨が強く石灰化してアリザリンで赤く、ほかの軟骨はアルシアンで青い（計画書 第 8.3 節）
MS=np.unpackbits(np.load('m_spine.npy'))[:C.size].reshape(C.shape).astype(bool)
C_sp=np.where(MS,C,np.int16(-1000)).astype(np.int16); C[MS&(C>-200)]=-200
del MS
_mode='r+' if (len(sys.argv)>3 and sys.argv[3]=='keep') else 'w+'   # 'keep': 既存の体積の一部の断面だけ作り直す
out=np.lib.format.open_memmap('a4_skel_field.npy',mode=_mode,dtype=np.int16,shape=(NZ,NV,NU))
out_sp=np.lib.format.open_memmap('a4_spine_field.npy',mode=_mode,dtype=np.int16,shape=(NZ,NV,NU))
vv,uu=np.meshgrid(V0+np.arange(NV)*VX,U0+np.arange(NU)*VX,indexing='ij')
CH=24; t0=time.time(); start=int(sys.argv[1]) if len(sys.argv)>1 else 0; stop=int(sys.argv[2]) if len(sys.argv)>2 else NZ
for k0 in range(start,stop,CH):
    k1=min(k0+CH,stop); zz=(Z0+np.arange(k0,k1)*VX)[:,None,None]*np.ones((1,NV,NU))
    U=np.broadcast_to(uu,zz.shape); V=np.broadcast_to(vv,zz.shape)
    Z_,U_,V_=zz.ravel(),U.ravel(),V.ravel()
    zr,y,x=inv(Z_,U_,V_)
    val=map_coordinates(C,[zr,y,x],order=1,cval=-1000,prefilter=False)
    vsp=map_coordinates(C_sp,[zr,y,x],order=1,cval=-1000,prefilter=False)
    # 頭の鏡映（右の半分を左にも）: 頭骨の後ろの端 137 mm・顎の軟骨 144 mm の手前（z<142）で、u<0 の側。
    # 正中のまわり（u -6〜-18 mm）は鏡映と元をなめらかに混ぜる（いちばん前の椎骨 101〜141 mm が正中のやや左にあり、
    # 全部を鏡映すると消えるため。境目の段も出さないため）
    hm=(Z_<142)&(U_<-6)
    if hm.any():
        zr2,y2,x2=inv(Z_[hm],-U_[hm],V_[hm])
        vm=map_coordinates(C,[zr2,y2,x2],order=1,cval=-1000,prefilter=False)
        w=np.clip((-U_[hm]-6)/12,0,1); w=w*w*(3-2*w)
        val[hm]=w*vm+(1-w)*val[hm]
        vsm=map_coordinates(C_sp,[zr2,y2,x2],order=1,cval=-1000,prefilter=False); vsp[hm]=w*vsm+(1-w)*vsp[hm]
    out[k0:k1]=val.reshape(k1-k0,NV,NU).astype(np.int16); out_sp[k0:k1]=vsp.reshape(k1-k0,NV,NU).astype(np.int16)
out.flush(); out_sp.flush(); print('done',start,stop,round(time.time()-t0,1),'s', (NZ,NV,NU))

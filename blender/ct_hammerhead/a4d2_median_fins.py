# A4: 正中のひれ（第1背びれ 1546、第2背びれ 4513、臀びれ 4302）を、背骨の真上・真下に立て直す
#  CT（A3 の後）では、第1背びれの付け根が正中から左右へ約 15 mm ずれ、先へ向かって約 20° 傾いていた。
#  ひれの点を最終の座標へ移し（この範囲 266〜660 mm は derolled2 と同じ変換）、
#  付け根の近く（体から 12 mm 以内）の点の左右の中央を正中（u=0）へ動かし、u と v の一次の当てはめの傾きを 0 に回す（z 軸のまわり、付け根を中心）
import numpy as np, json
from scipy.ndimage import binary_closing, gaussian_filter
VX=0.735; U0,V0=-180.0,-150.0
L=np.load('skel_lab.npy',mmap_mode='r'); cxs,cys=np.load('spine_line.npy'); t=np.load('tilt_sym.npy'); info=json.load(open('comps_info.json'))
rep={}
for lab,name,side in ((1546,'dfin1',-1),(4513,'dfin2',-1),(4302,'anal',1)):
    z0,z1=info[str(lab)]['z']; sub=np.asarray(L[z0:z1+1]); zz,yy,xx=np.nonzero(sub==lab); z=zz+z0
    c=np.cos(np.radians(t[z])); s=np.sin(np.radians(t[z])); dx=xx-cxs[z]; dy=yy-cys[z]
    u=(c*dx+s*dy)*0.735; v=(-s*dx+c*dy)*0.735; zm=z*0.5
    av=np.abs(v); base=av<=av.min()+12
    ub,vb=float(np.median(u[base])),float(np.median(v[base]))
    b=np.polyfit(v,u,1)[0]; ang=np.arctan(b)                    # u = a + b v の傾き
    # z 軸まわりに -ang 回す（付け根中心）: 点 (u-ub, v-vb) を回して u 成分の v 依存を消す
    du,dv=u-ub,v-vb; ca,sa=np.cos(ang),np.sin(ang)
    u2=du*ca-dv*sa; v2=du*sa+dv*ca+vb
    # 先へ向かう曲がりも消す: 高さ（v）2 mm ごとの u の中央を 0 にそろえる（ひれを平らな縦の板にする）
    hb=np.round(v2/2).astype(int); med={k:np.median(u2[hb==k]) for k in np.unique(hb)}
    u2=u2-np.array([med[k] for k in hb])*np.clip(np.abs(v2-vb)/10,0,1)   # 付け根の近くは動かさない
    b2=np.polyfit(v2,u2,1)[0]
    np.savez(f'a4_{name}_xform.npz',ub=ub,vb=vb,ang=ang,band_keys=np.array(sorted(med)),band_med=np.array([med[k] for k in sorted(med)]))
    rep[name]={'label':lab,'n':int(len(u)),'base_u_mm':round(ub,1),'base_v_mm':round(vb,1),'lean_deg':round(float(np.degrees(ang)),1),'lean_after_deg':round(float(np.degrees(np.arctan(b2))),2)}
    P=np.stack([u2,zm,v2],1)
    iz=np.round(P[:,1]/VX).astype(int); iv=np.round((P[:,2]-V0)/VX).astype(int); iu=np.round((P[:,0]-U0)/VX).astype(int)
    lo=np.array([iz.min(),iv.min(),iu.min()])-4; hi=np.array([iz.max(),iv.max(),iu.max()])+5
    B=np.zeros(hi-lo,bool); B[iz-lo[0],iv-lo[1],iu-lo[2]]=True; B=binary_closing(B,iterations=1)
    np.savez_compressed(f'a4_{name}.npz',field=gaussian_filter(B.astype(np.float32),0.7),origin=lo)
json.dump(rep,open('a4_median_fins.json','w'),ensure_ascii=False,indent=1); print(json.dumps(rep,ensure_ascii=False))

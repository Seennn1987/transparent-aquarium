# A3 尾の上への反りを残す（2026-10-14）
#  derolled2 は背骨の中心線を一直線にそろえたため、尾びれへ上がる背骨の曲がりも消えた。
#  尾びれの起点の手前（700 mm）から後ろだけ、背骨の背腹方向のずれ（胴の直線から測る）を残し、左右のずれだけ消す。
#  700 mm より前は derolled2 と同じ（ひれの座標 c833_uvz などはそのまま使える）
import numpy as np, json
from scipy.ndimage import map_coordinates, gaussian_filter1d
C=np.load('zyg_clean.npy',mmap_mode='r'); cxs,cys=np.load('spine_line.npy'); t=np.load('tilt_sym.npy')
z=np.arange(len(cxs)); sel=(z>=400)&(z<=1600)                       # 胴（200〜800 mm）の直線
lx=np.polyval(np.polyfit(z[sel],cxs[sel],1),z); ly=np.polyval(np.polyfit(z[sel],cys[sel],1),z)
c=np.cos(np.radians(t)); s=np.sin(np.radians(t))
v=(-s*(cxs-lx)+c*(cys-ly))*0.735                                    # 背骨の背腹のずれ mm（負=背側）
ZR=1400                                                             # 700 mm
vs=gaussian_filter1d(v,40)                                          # 20 mm で平滑（胴の小さな波を消す）
ramp=np.clip((z-ZR)/120,0,1); ramp=ramp*ramp*(3-2*ramp)             # 700→760 mm でなめらかに 0→1
keep=(vs-vs[ZR])*ramp                                               # 残す背腹のずれ mm
np.save('tail_keep_v.npy',keep)
D2=np.load('derolled2.npy',mmap_mode='r'); out=np.array(D2)         # (1046,300,300)
N=300; cc=N/2; uu,vv=np.meshgrid(np.arange(N)-cc,np.arange(N)-cc)
for i in range(ZR//2,out.shape[0]):
    zz=2*i; sl=np.asarray(C[zz:zz+2]).astype(np.float32).max(0)
    sl=sl[:sl.shape[0]//2*2,:sl.shape[1]//2*2].reshape(sl.shape[0]//2,2,sl.shape[1]//2,2).max((1,3))
    k=keep[zz]/1.47                                                 # 半分の解像度の画素
    cx=cxs[zz]/2+s[zz]*k; cy=cys[zz]/2-c[zz]*k                      # 中心 = 背骨 − keep × 背腹の向き
    x=uu*c[zz]-vv*s[zz]+cx; y=uu*s[zz]+vv*c[zz]+cy
    out[i]=map_coordinates(sl,[y,x],order=1,cval=-1000).astype(np.int16)
np.save('derolled3.npy',out); np.save('derolled3_mips.npy',np.stack([out.max(1),out.max(2)]))
rep={int(mm):round(float(keep[mm*2]),1) for mm in range(700,1041,40)}
dz=np.gradient(gaussian_filter1d(keep,20))/0.5
ang={int(mm):round(float(np.degrees(np.arctan(-dz[mm*2]))),1) for mm in range(700,1041,40)}
json.dump({'keep_v_mm':rep,'local_upturn_deg':ang},open('tail_upturn.json','w'),indent=1); print(rep); print(ang)

# A3 頭の向きを胴にそろえる（横向きの首振り）
#  derolled4 の上から見た外形の鏡映で探した頭の正中線: u = -7.0 + tan(11°)(z-70) mm（重なり 0.89）。
#  胴（背骨, z>=140 mm）は u=0 で z に平行。頭は胴に対して約 11° 横を向き、z=140 mm で 6.6 mm ずれている。
#  z<=130 mm は頭を剛体として回して正中線を u=0 にそろえ、130〜170 mm で回す角度とずらしをなめらかに 0 へ移す
import hh_paths; hh_paths.cd_work()
import numpy as np, json
from scipy.ndimage import map_coordinates
D=np.load('derolled4.npy'); ZB=260
A=D[:ZB].astype(np.float32)
TH=np.radians(11.0); PZ=140.0; PU=-7.0+np.tan(TH)*(PZ-70)
N=300; cc=N/2; vv,uu=np.meshgrid(np.arange(N)-cc,np.arange(N)-cc,indexing='ij')   # (v,u) px
for zo in range(0,200):
    w=1.0 if zo<=130 else max(0.0,1-(zo-130)/40); w=w*w*(3-2*w)
    if w==0: continue
    th=TH*w; pu=PU*w
    uq=uu*1.47; dz=zo-PZ                                     # 出力の点 q=(z,u) mm
    zi=PZ+dz*np.cos(th)-uq*np.sin(th)                        # p = R(th)(q-P') + P
    ui=dz*np.sin(th)+uq*np.cos(th)+pu
    D[zo]=map_coordinates(A,[zi,vv+cc,ui/1.47+cc],order=1,cval=-1000).astype(np.int16)
np.save('derolled5.npy',D); json.dump({'yaw_deg':11.0,'pivot_z_mm':PZ,'offset_u_mm':round(float(PU),1),'blend_mm':[130,170]},open('head_yaw.json','w'))
print('ok',round(PU,1))

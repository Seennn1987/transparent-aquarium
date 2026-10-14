# A3 頭〜胸の所の倒れの残りを戻す（derolled5 → derolled6）
#  断面の外形の左右対称（neck_roll2.json, ±30° を 2° 刻み）で、175〜200 mm は +16°、205〜250 mm は +4〜+10°、260 mm 以降は 0〜−4°。
#  150〜160 mm は答えが探す範囲の端（±30°）に張り付き、決まらない（頭の平たい断面から胴の縦長の断面へ移る所）。
#  戻す量: 145 mm まで 0、170 mm で 16° まで上げ、200 mm まで 16°、そこから測った値に沿って 260 mm で 0。5 mm で平滑
import numpy as np, json
from scipy import ndimage as ndi
from scipy.ndimage import gaussian_filter1d
meas=dict((z,a) for z,a,_,_ in json.load(open('neck_roll2.json')))
z=np.arange(1046,dtype=float); r=np.zeros_like(z)
for zz in range(145,171): r[zz]=16*(zz-145)/25
r[170:201]=16
pts=[(200,16)]+[(k,meas[k]) for k in range(205,256,5)]+[(260,0)]
r[200:261]=np.interp(np.arange(200,261),[p[0] for p in pts],[p[1] for p in pts])
r=gaussian_filter1d(r,5); r[:135]=0; r[275:]=0
np.save('neck_roll_deg.npy',r)
D=np.load('derolled5.npy')
for zz in range(135,275):
    if abs(r[zz])<0.2: continue
    D[zz]=ndi.rotate(D[zz].astype(np.float32),r[zz],reshape=False,order=1,cval=-1000).astype(np.int16)
np.save('derolled6.npy',D); np.save('derolled6_mips.npy',np.stack([D.max(1),D.max(2)]))
# 肩帯・胸びれの塊（c833）の点も同じだけ回す（頭の向きの直し 130〜170 mm は肩帯の前端 161 mm にわずかにかかるが、ここでは扱わない）
zm,u,v=np.load('c833_uvz.npy'); a=np.radians(r[np.clip(np.round(zm).astype(int),0,1045)])
u2=u*np.cos(a)+v*np.sin(a); v2=-u*np.sin(a)+v*np.cos(a)
np.save('c833_uvz_r.npy',np.stack([zm,u2,v2]))
print({int(k):round(float(r[k]),1) for k in range(140,281,10)})

# A3 尾の反りを決定の角度にする（2026-10-14 プロデューサー決定「③ 約 20°」）
#  derolled3（CT の反り約 4° を残した体積）の 750 mm より後ろを、案の図（a3h_tail_options.py の③）と同じ式で背へずらす。
#  断面ごとに背腹へずらす（せん断）。曲げた区間の長さは 1/cos(16°)≈1.04 倍に伸びるので、
#  骨をメッシュにする段（A4）では椎骨ごとに回して長さを保つ。ここでは位置と角度の目安を作る
import numpy as np, json
from scipy.ndimage import shift as ndshift
keep=np.load('tail_keep_v.npy'); zz=np.arange(760,1011)
ct_deg=float(np.degrees(np.arctan(-np.polyfit(zz,keep[zz*2],1)[0])))
TARGET=20.0; EXTRA=TARGET-ct_deg; HINGE=750
D=np.load('derolled3.npy'); off=np.zeros(D.shape[0])
for mm in range(HINGE,D.shape[0]):
    r=np.clip((mm-HINGE)/30,0,1); d=np.tan(np.radians(EXTRA))*max(mm-HINGE-15*r,0)*r
    off[mm]=d; D[mm]=ndshift(D[mm].astype(np.float32),(-d/1.47,0),order=1,cval=-1000).astype(np.int16)
np.save('derolled4.npy',D); np.save('derolled4_mips.npy',np.stack([D.max(1),D.max(2)])); np.save('tail_bend_offset_mm.npy',off)
sp=keep[::2][:len(off)]+off*-1                      # 背骨の背腹の位置（mm、負=背）
z2=np.arange(760,1011); ang=float(np.degrees(np.arctan(-np.polyfit(z2,sp[z2],1)[0])))
json.dump({'ct_deg':round(ct_deg,1),'target_deg':TARGET,'extra_deg':round(EXTRA,1),'hinge_mm':HINGE,
           'spine_v_mm':{int(m):round(float(sp[m]),1) for m in range(700,1041,40)},'check_upper_lobe_deg':round(ang,1)},
          open('tail_bend.json','w'),ensure_ascii=False,indent=1)
print(open('tail_bend.json').read())

# A3 頭の翼をそろえる（2026-10-14 プロデューサー決定「②」: 画面の右の半分（u>0）を左右に使う）
#  derolled6 の u<0 の半分を、z 0〜110 mm は u>0 の半分の鏡映に置き換え、110〜135 mm は鏡映と元の CT を
#  なめらかに混ぜる（境目の段を消すため）。翼の後ろの端は 115 mm まで。135 mm より後ろは CT のまま
#  鏡の軸は u=0（直した後の頭の正中線 u≈-1 mm の 0.7 mm 手前）
import numpy as np, json
D=np.load('derolled6.npy'); Z0,Z1=110,135
M=D[:Z1,:,::-1].astype(np.float32); O=D[:Z1].astype(np.float32)
w=np.ones(Z1,np.float32); t=np.clip((np.arange(Z1)-Z0)/(Z1-Z0),0,1); w=1-t*t*(3-2*t)   # 鏡映の重み
mix=w[:,None,None]*M+(1-w[:,None,None])*O
D[:Z1,:,:150]=mix[:,:,:150].astype(np.int16)
np.save('derolled7.npy',D); np.save('derolled7_mips.npy',np.stack([D.max(1),D.max(2)]))
json.dump({'mirrored':'u>0 half to u<0','full_mm':[0,Z0],'blend_mm':[Z0,Z1]},open('head_mirror.json','w')); print('ok')

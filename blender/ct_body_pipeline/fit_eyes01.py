# 目（眼球・レンズ）の色を写真 01 の目に合わせる（2026-10-14）
#   写真 01 の目（中心 x 243, y 368 px、1 辺 447 px）: 輪 r 7〜10 px と中 r < 4 px の、液（224）で割った吸光度の中央値
#   画面（cal01.npz、色 01）: 眼球だけを通る画素（レンズを通らない）と、レンズを通る画素。膜の層・膜・骨の分（色 01）を引いて、
#   眼球・レンズの通り道の中央値で割る。画面の目は 2 つ（左右）が重なる所もあるので、通り道は左右の和
import numpy as np, sys
from PIL import Image
p=np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float); A=-np.log(np.clip(p/224.0,1e-3,1))
yy,xx=np.mgrid[0:p.shape[0],0:p.shape[1]]; r=np.hypot(xx-243,yy-368)
A_ring=np.median(A[(r>=7)&(r<=10)],0); A_mid=np.median(A[r<4],0)
cal=np.load('web/cal01.npz'); paths=np.maximum(cal['paths'],0); film=np.maximum(cal['film'][...,0],0)
G={'film':np.array([0.1173,0.0751,0.0484]),'skin':np.array([0,0.0606,0.1031]),'bone':np.array([14.79,30.86,24.66])}
t0=0.042; F=t0*(1-np.exp(-paths[...,0]/t0))
base=film[...,None]*G['film']+paths[...,2][...,None]*G['skin']+F[...,None]*G['bone']
eye=np.maximum(cal['org_eye_l'],0)+np.maximum(cal['org_eye_r'],0); lens=np.maximum(cal['org_lens_l'],0)+np.maximum(cal['org_lens_r'],0)
me=(eye>1e-4)&(lens<1e-5); ml=lens>1e-4
print('screen pixels: eye only %d, lens %d'%(me.sum(),ml.sum()))
k_eye=np.maximum(np.median((A_ring[None]-base[me])/eye[me][:,None],0),0)
k_lens=np.maximum(np.median((A_mid[None]-base[ml]-eye[ml][:,None]*k_eye[None])/lens[ml][:,None],0),0)
print('photo ring',A_ring.round(3),'centre',A_mid.round(3))
print('screen base eye-only',np.median(base[me],0).round(3),'eye path',np.median(eye[me]).round(4),'lens path',np.median(lens[ml]).round(4))
print('eye per unit',k_eye.round(2),'lens per unit',k_lens.round(2))

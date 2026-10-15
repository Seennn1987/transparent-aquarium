# 舌内突起（舌の芯）の中心線を CT で追う（2026-10-15）。基舌骨のあたりから前後へ 0.5 mm ずつ、軸に直角な面で濃さ 36〜80 の輪の重心を取る
#   出力: ento_line.npy（CT の mm）。追えた長さ 23.6 mm、外径 約 0.8 mm の薄い殻の管（ほぼ軟骨で一部石灰化: Herrel et al. 2001）
import numpy as np, scipy.ndimage as nd
V=np.load('ct_ms50726_vol4max.npz')['v'].astype(np.float32); s=0.104
p=np.array([51.0,36.6,13.4]); t=np.array([58.1,34.1,16.2])-np.array([47.6,38.3,12.1]); t/=np.linalg.norm(t)
g=np.linspace(-1.2,1.2,25); G1,G2=np.meshgrid(g,g,indexing='ij')
def step(p,t,sign):
    pts=[]
    for k in range(80):
        e1=np.cross(t,[0,0,1.0]); e1/=np.linalg.norm(e1); e2=np.cross(t,e1)
        X=p+G1[...,None]*e1+G2[...,None]*e2
        im=nd.map_coordinates(V,(X/s).transpose(2,0,1),order=1)
        m=(im>36)&(im<80)
        if m.sum()<6: break
        # 輪の中心: 重み付き重心
        w=np.where(m,im-30,0); c=np.array([(w*G1).sum(),(w*G2).sum()])/w.sum()
        if np.hypot(*c)>0.8: break
        q=p+c[0]*e1+c[1]*e2; pts.append((q,float(im[m].mean()),int(m.sum()), float(im.max())))
        if len(pts)>=3: tn=pts[-1][0]-pts[-3][0]; tn/=np.linalg.norm(tn); t=0.7*t+0.3*sign*tn; t/=np.linalg.norm(t)
        p=q+sign*0.5*t
    return pts
fw=step(p,t,1); bw=step(p,-t,1)
for q,mi,n,mx in bw[::-1]+fw: print(q.round(2),'mean %.0f n %d max %.0f'%(mi,n,mx))
P=np.array([q for q,*_ in bw[::-1]+fw]); np.save('ento_line.npy',P)
print('length %.1f mm'%np.linalg.norm(np.diff(P,axis=0),axis=1).sum())

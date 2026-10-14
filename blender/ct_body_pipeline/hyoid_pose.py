# 舌骨の姿勢: 前の端（舌骨の頭、あごの下）は頭骨について動き（FOLLOW_HEAD）、後ろへ伸びる角は CT の静止の形での胴との位置を保つように、
# 舌骨の頭のまわりに回す。回転 = 角の点（舌骨の頭から 8 mm より後ろ）を「胴について動かした位置」に最小二乗で合わせる（Kabsch）
#   出力: pose_jar_v4.npz（hyoid の行列だけ変える）、hyoid_pose.json（回転、モデル座標）
import numpy as np, json
from scipy.spatial import cKDTree
exec(open('diag_profile.py').read().split("z=np.load('diag_inside.npz')")[0])
d=np.load('chameleon_body_ct.npz')
i=bn.index('hyoid'); Mh=Mof('hyoid'); Mhead=Mof('head')
h0=P['head'][i]; ax_=P['tail'][i]-h0; ax_/=np.linalg.norm(ax_)
x=ct2m(d['hyoid__v']); s=(x-h0)@ax_
anchor=x[:0]; anc=h0@Mh[:3,:3].T+Mh[:3,3]
# 胴について動かした位置（静止の体軸で最も近い点の椎骨の変形を混ぜる。skinloft3 と同じ混ぜ方）
kd=cKDTree(C); j=kd.query(x)[1]
tgt=np.einsum('nij,nj->ni',Mst[j][:,:3,:3],x)+Mst[j][:,:3,3]
cur=x@Mh[:3,:3].T+Mh[:3,3]
m=s>8*MM
A=cur[m]-anc; B=tgt[m]-anc
U,S_,Vt=np.linalg.svd(A.T@B); Dg=np.diag([1,1,np.sign(np.linalg.det(Vt.T@U.T))]); Rx=Vt.T@Dg@U.T
ang=np.degrees(np.arccos(np.clip((np.trace(Rx)-1)/2,-1,1)))
new=(cur-anc)@Rx.T+anc
print('extra rotation %.1f deg; horn rms to trunk-follow target: before %.2f mm, after %.2f mm'%(ang,np.sqrt(((cur[m]-tgt[m])**2).sum(1).mean())/MM,np.sqrt(((new[m]-tgt[m])**2).sum(1).mean())/MM))
Mn=Mh.copy(); Mn[:3,:3]=Rx@Mh[:3,:3]; Mn[:3,3]=Rx@(Mh[:3,3]-anc)+anc
Mall=P['M'].copy(); Mall[i]=Mn
np.savez('pose_jar_v4.npz',names=P['names'],M=Mall,head=P['head'],tail=P['tail'],k=P['k'])
json.dump({'R_extra_model':Rx.tolist(),'angle_deg':ang,'anchor_model':anc.tolist()},open('hyoid_pose.json','w'),indent=1)
# 確かめ: 角の腹への深さ（姿勢の体軸の枠）
kp=cKDTree(Cp)
for nm,X in (('before',cur),('after',new)):
    jj=kp.query(X)[1]; q=X-Cp[jj]; vd=-(q*Dp[jj]).sum(1)/MM; u=arc[jj]
    print(nm,' '.join('u%d-%d: %.1f'%(a,a+10,vd[(u>=a)&(u<a+10)].max()) for a in (10,20,30,40,50) if ((u>=a)&(u<a+10)).any()))

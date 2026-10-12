# 前肢 B: 肘の位置を直したので、上腕(21)と前腕(22)を関節を結ぶ線分に近い方で分け直す。
# どの線分（肢帯・上腕・前腕・手）からも 40 ボクセル（約 4 mm）より遠い前肢 B の塊は舌骨（ラベル 2）へ移す（舌骨のかけら）
import numpy as np, scipy.ndimage as nd, sys, json
src,dst=sys.argv[1],sys.argv[2]
B=np.load(src); J={k:np.array(v,float) for k,v in json.load(open('joints.json')).items()}
def segdist(P,a,b):
    ab=b-a; t=np.clip(((P-a)@ab)/(ab@ab),0,1); return np.linalg.norm(P-(a+t[:,None]*ab),axis=1)
ks=['fB_scap0','fB_shoulder','fB_elbow','fB_wrist','fB_tip']
V=np.argwhere(np.isin(B,(20,21,22,23))); Vf=V.astype(float)
D=np.stack([segdist(Vf,J[a],J[b]) for a,b in zip(ks,ks[1:])],1)
lab=B[tuple(V.T)].copy()
arm=np.isin(lab,(21,22)); lab[arm]=np.where(D[arm,1]<=D[arm,2],21,22)
far=D.min(1)>40
print('resplit 21->22',int(((B[tuple(V.T)]==21)&(lab==22)).sum()),'22->21',int(((B[tuple(V.T)]==22)&(lab==21)).sum()),'far->hyoid',int(far.sum()))
lab[far]=2
B[tuple(V.T)]=lab; np.save(dst,B)

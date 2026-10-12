# 関節の位置を直した肢で、隣り合う 2 本の骨のラベルを、関節を結ぶ線分に近い方で分け直す
#   python3 resplit.py 入力 出力 肢 骨A 骨B   例: fB 21 22（上腕/前腕）、hB 40 41（大腿/下腿）
import numpy as np, sys, json
src,dst,c,la,lb=sys.argv[1],sys.argv[2],sys.argv[3],int(sys.argv[4]),int(sys.argv[5])
B=np.load(src); J={k:np.array(v,float) for k,v in json.load(open('joints.json')).items()}
CH={'fA':['fA_shoulder','fA_elbow','fA_wrist'],'fB':['fB_shoulder','fB_elbow','fB_wrist'],
    'hA':['hA_hip','hA_knee','hA_ankle'],'hB':['hB_hip','hB_knee','hB_ankle']}[c]
def segdist(P,a,b):
    ab=b-a; t=np.clip(((P-a)@ab)/(ab@ab),0,1); return np.linalg.norm(P-(a+t[:,None]*ab),axis=1)
V=np.argwhere(np.isin(B,(la,lb))); Vf=V.astype(float)
da=segdist(Vf,J[CH[0]],J[CH[1]]); db=segdist(Vf,J[CH[1]],J[CH[2]])
old=B[tuple(V.T)]; new=np.where(da<=db,la,lb).astype(B.dtype)
print(c,'changed',int((old!=new).sum()),'of',len(V)); B[tuple(V.T)]=new; np.save(dst,B)

# 後肢の大腿・下腿のラベルから、四肢の骨より細い棒を外す（作り方は hyoid5.py と同じ）。
# 太さの判定: 骨は中空の殻なので、先に閉じる（半径 3）＋断面ごとに穴を埋めてから σ=3 ボクセルでぼかし、0.5 で切る。
# 消えた部分（細い）のうち、手（手首→指先の線から 30 ボクセル以内）を除いた、外接の対角 40 ボクセル以上の塊を棒とする。
# 長い棒（舌骨の角鰓骨）は頭へ。短い棒は接している骨（肋骨の椎骨など）へ。どこにも接していなければ頭へ。
import numpy as np, scipy.ndimage as nd, sys, json
from skimage.morphology import ball
src,dst=sys.argv[1],sys.argv[2]
B=np.load(src); J={k:np.array(v,float) for k,v in json.load(open('joints.json')).items()}
def segdist(P,a,b):
    ab=b-a; t=np.clip(((P-a)@ab)/(ab@ab),0,1); return np.linalg.norm(P-(a+t[:,None]*ab),axis=1)
tot=0
for c,labs in (('hA',(31,32)),('hB',(40,41))):
    m=np.isin(B,labs); P=np.argwhere(m); lo=np.maximum(P.min(0)-10,0); hi=P.max(0)+11
    sl=tuple(slice(a,b) for a,b in zip(lo,hi)); sub=B[sl]; mm=np.isin(sub,labs)
    C=nd.binary_closing(np.pad(mm,6),ball(3))[6:-6,6:-6,6:-6]
    for ax in range(3):
        C=np.moveaxis(np.stack([nd.binary_fill_holes(x) for x in np.moveaxis(C,ax,0)],0),0,ax)
    G=nd.gaussian_filter(C.astype(np.float32),3.0)>0.5
    thin=mm&~nd.binary_dilation(G,iterations=2)
    q=np.argwhere(thin); dh=segdist((q+lo).astype(float),J[c+'_ankle'],J[c+'_tip'])
    thin[tuple(q[dh<30].T)]=False
    lab,n=nd.label(thin,np.ones((3,3,3)))
    for i,s in enumerate(nd.find_objects(lab),1):
        if s is None: continue
        ext=float(np.linalg.norm([x.stop-x.start for x in s]))
        cm=lab==i
        if ext<40 or cm.sum()<150: continue
        ring=nd.binary_dilation(cm,np.ones((3,3,3)),iterations=2)&~cm; nb=sub[ring]; nb=nb[(nb>0)&~np.isin(nb,labs)&~((nb>=10)&(nb<50))]
        # 長い棒（外接の対角 150 以上 = 約 16 mm）は左右一対の角鰓骨とみて頭へ。短いものは接している骨へ
        tgt=int(np.bincount(nb).argmax()) if len(nb) else 30   # 何にも接していない細い棒は腰帯に付ける（正体不明。骨盤の近くで静止しているもの）
        sub[cm]=tgt; tot+=int(cm.sum())
        print(c,'rod',int(cm.sum()),'ext',int(ext),'center',(np.argwhere(cm).mean(0)+lo).round(),'->',tgt, dict(zip(*[x.tolist() for x in np.unique(nb,return_counts=True)])) if len(nb) else {})
    B[sl]=sub
np.save(dst,B); print('moved',tot)

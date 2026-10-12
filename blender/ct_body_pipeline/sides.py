# 四肢の左右を決める。R = 前（尾→頭）× 背 の向きに、肢帯と近位の骨（上腕・大腿）が体軸からどちらへ出ているかで見る。
# 前肢 A と後肢 B が +R、前肢 B と後肢 A が -R に出る（中央値で 9〜64 ボクセル、0.9〜6.7 mm）。
# 注意: R が動物の右になるのは、CT の (断面, 行, 列) の並びが右手系のとき。断面の並びの向きはデータに書かれていないので、
#       鏡像の可能性は残る。左右対称の骨格なので、見た目は変わらない。
import numpy as np, sys, json
from scipy.spatial import cKDTree
B=np.load(sys.argv[1]); C=np.load('axis5_s.npy')*2+0.5; T=np.load('axis5_t.npy'); D=np.load('frame_D.npy'); tr=cKDTree(C)
side={}
for c,labs in (('fA',(10,11)),('fB',(20,21)),('hA',(30,31)),('hB',(40,))):
    P=np.argwhere(np.isin(B,labs)).astype(float); d,i=tr.query(P); R=np.cross(-T[i],D[i]); r=float(np.median(((P-C[i])*R).sum(1)))
    side[c]=('R' if r>0 else 'L'); print(c,round(r,1),side[c])
assert side['fA']!=side['fB'] and side['hA']!=side['hB']
json.dump({c:c[0]+s for c,s in side.items()},open('sides.json','w'),indent=1); print(open('sides.json').read())

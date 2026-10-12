# 肋骨の途切れ（骨の濃さで写らない隙間）を、軟骨の短い棒でつなぐ位置を求める。
#   各肋骨ラベルの、本体（最大の塊）と離れた塊について、いちばん近い 2 点（本体側・塊側）を隙間の両端とする。
#   隙間の濃さ（vol4max）が骨（48 以上）より低く、長さ 2 mm 以下の所だけ。太さはその肋骨の太さ（内側からの距離）
#   両端は ribrestore で復元した位置にする。出力: cart_gaps.json（CT の mm）
import numpy as np, scipy.ndimage as nd, json
from scipy.spatial import cKDTree
import ribrestore
B=np.load('B_h10.npy'); X=np.load('ct_ms50726_vol4max.npz')['v']
out=[]
objs=nd.find_objects(B)
for l in range(160,202):
    if l-1>=len(objs) or objs[l-1] is None: continue
    sl=tuple(slice(max(0,a.start-3),min(n,a.stop+3)) for a,n in zip(objs[l-1],B.shape))
    m=B[sl]==l; lab,n=nd.label(m,np.ones((3,3,3)))
    if n<2: continue
    sz=np.bincount(lab.ravel()); sz[0]=0; main=sz.argmax()
    E=nd.distance_transform_edt(m)
    off=np.array([a.start for a in sl])
    mp=np.argwhere(lab==main); mt=cKDTree(mp)
    for c in range(1,n+1):
        if c==main or sz[c]<40: continue
        cp=np.argwhere(lab==c); d,j=mt.query(cp); i=np.argmin(d)
        a=cp[i]; b=mp[j[i]]; L=d[i]*0.104
        if L>2.0 or L<0.15: continue
        line=np.linspace(a,b,max(2,int(d[i])+1)).round().astype(int)+off
        mn=int(X[tuple(line.T)].min())
        if mn>=48: continue
        # 太さ: この肋骨の、内側からの距離の大きい方 10% の中央値（端の点はどちらも表面なので使えない）
        r=float(np.median(E[m][E[m]>=np.percentile(E[m],90)]))*0.104
        A,Bp=ribrestore.restore(np.array([a+off,b+off],float),np.array([l,l]))
        out.append({'label':l,'a':(A*0.104).tolist(),'b':(Bp*0.104).tolist(),'len_mm':round(float(L),2),'radius_mm':round(float(max(r,0.08)),3),'gap_min_density':mn,'piece_voxels':int(sz[c])})
json.dump(out,open('cart_gaps.json','w'),indent=0)
print(len(out)); [print(o['label'],o['len_mm'],o['radius_mm'],o['gap_min_density'],o['piece_voxels']) for o in out]

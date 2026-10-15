# 写真（NOAA、背中から）の右の個体の胸びれの外形を取り出す
import hh_paths; hh_paths.cd_work()
import numpy as np, json
from scipy import ndimage as ndi
runs=open(hh_paths.REF+'/noaa_compare_right_runs.txt').read().strip().split(';')
M=np.zeros((366,590),bool)
for k,r in enumerate(runs):
    for seg in filter(None,r.split(',')):
        a,b=map(int,seg.split('-')); M[30+k,a:b+1]=True
lab,n=ndi.label(M); sz=ndi.sum(M,lab,range(1,n+1)); M=lab==(1+int(np.argmax(sz))); M=ndi.binary_fill_holes(ndi.binary_closing(M,iterations=2))
cx=446
edges={}
for y in range(120,366):
    xs=np.nonzero(M[y])[0]
    if len(xs)==0: continue
    # 中心を含む連続区間
    row=M[y]; l=cx; r=cx
    if not row[cx]: continue
    while l>0 and row[l-1]: l-=1
    while r<589 and row[r+1]: r+=1
    edges[y]=(l,r)
ys=sorted(edges)
pre=[y for y in ys if 185<=y<=200]; post=[y for y in ys if 295<=y<=310]
for y in ys:
    if 200<=y<=300: print(y,edges[y]) if y%10==0 else None
L0=np.median([edges[y][0] for y in pre]); R0=np.median([edges[y][1] for y in pre]); L1=np.median([edges[y][0] for y in post]); R1=np.median([edges[y][1] for y in post])
print('trunk edges before',L0,R0,'after',L1,R1)
fin={'L':np.zeros_like(M),'R':np.zeros_like(M)}
for y in range(195,305):
    a=(y-195)/110; bl=L0*(1-a)+L1*a; br=R0*(1-a)+R1*a
    xs=np.nonzero(M[y])[0]
    fin['R'][y,xs[xs>br+1]]=True; fin['L'][y,xs[xs<bl-1]]=True
for k in fin:
    lab,n=ndi.label(fin[k]); 
    if n: sz=ndi.sum(fin[k],lab,range(1,n+1)); fin[k]=lab==(1+int(np.argmax(sz)))
    print(k,'area px',int(fin[k].sum()))
np.savez('photo_pect.npz',L=fin['L'],R=fin['R'],trunk=np.array([L0,R0,L1,R1]))

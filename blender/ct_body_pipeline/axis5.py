import numpy as np, scipy.ndimage as nd
from skimage.graph import MCP_Geometric
from PIL import Image, ImageDraw
W=np.load('W2.0.npy'); D=np.load('D2.npy')
spinebits=[7,10,14,20,21,37,39,49,61,71,72,82,90,95,99]
A=np.isin(W,[5]+spinebits)
# neck: contact of 5 with 81
c=nd.binary_dilation(W==81,iterations=2)&A; start=np.argwhere(c).mean(0).round().astype(int)
pts=np.argwhere(c); start=pts[np.argmin(np.linalg.norm(pts-pts.mean(0),axis=1))]
cost=np.where(A,1.0/(0.5+D),np.inf)   # prefer thick (vertebral body) centers
m=MCP_Geometric(cost); acc,_=m.find_costs([tuple(start)])
geo=np.where(A,acc,-1); geo[np.isinf(geo)]=-1
end=np.unravel_index(np.argmax(geo),geo.shape); print('start',start,'end',end,'cost',geo[end])
path=np.array(m.traceback(end)); np.save('axis5.npy',path)
Vv=np.load('ct_ms50726_vol4.npz')['v']
for nm,axis,(i,j) in (('lat',2,(1,0)),('top',0,(2,1))):
    mm=Vv.max(axis=axis); im=Image.fromarray(np.clip(mm.astype(int)*2,0,255).astype(np.uint8)).convert('RGB'); dr=ImageDraw.Draw(im)
    Q=path*2
    for k in range(len(Q)-1): dr.line([(Q[k][i],Q[k][j]),(Q[k+1][i],Q[k+1][j])],fill=(255,int(255*k/len(Q)),0),width=3)
    im.save(f'axis5_{nm}.png')
print(len(path))

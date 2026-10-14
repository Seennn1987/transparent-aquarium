# 体の膜の胴の幅の案（見本）: CT の断面の外形を、背骨の中心から左右方向だけ広げる
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',15)
D=np.load('derolled7.npy',mmap_mode='r')
opts=[(1.0,'① CT のまま（幅÷高さ≈0.6）'),(1.5,'② 1.5 倍（≈0.9）'),(2.0,'③ 2 倍＝写真の幅（≈1.2）')]
tiles=[]
for k,lab in opts:
    row=[]
    for z in (200,300,450):
        s=np.asarray(D[z]).astype(float); m=ndi.binary_fill_holes(s>-400)
        sc=ndi.zoom(m.astype(float),(1,k),order=1)>0.5; w=sc.shape[1]; c0=int(150*k)
        out=np.zeros((300,300),bool); a=max(0,c0-150); b=min(w,c0+150); out[:,150-(c0-a):150+(b-c0)]=sc[:,a:b]
        bone=np.zeros((300,300),bool); bs=ndi.zoom((s>250).astype(float),(1,k),order=0)>0.5; bone[:,150-(c0-a):150+(b-c0)]=bs[:,a:b]
        img=np.full((300,300,3),255,np.uint8); img[out]=(205,205,215); img[bone]=(60,60,60)
        im=Image.fromarray(img[70:250,40:260]).resize((330,270),Image.NEAREST)
        ImageDraw.Draw(im).text((4,4),f'z={z} mm',fill=(0,0,0),font=F); row.append(im)
    T=Image.new('RGB',(3*335,300),(255,255,255)); ImageDraw.Draw(T).text((4,4),lab,fill=(0,0,0),font=F)
    for i,r in enumerate(row): T.paste(r,(i*335,26))
    tiles.append(T)
S=Image.new('RGB',(3*335,len(tiles)*305+30),(255,255,255))
for i,t in enumerate(tiles): S.paste(t,(0,i*305))
ImageDraw.Draw(S).text((4,S.height-24),'体の断面（前から、上が背）。灰=体、黒=骨（骨は見本のため一緒に広げた。実際の膜では骨は広げない）',fill=(60,60,60),font=F)
S.save('trunk_options.png'); print(S.size)

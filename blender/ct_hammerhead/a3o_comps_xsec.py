# 名前の決まらない塊の断面（全身 CT の元の断面、塊を赤で囲う）
import numpy as np, json
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi
F=ImageFont.truetype('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',14)
L=np.load('skel_lab.npy',mmap_mode='r'); C=np.load('zyg_clean.npy',mmap_mode='r'); info=json.load(open('comps_info.json'))
cxs,cys=np.load('spine_line.npy')
tiles=[]
for i,fr in ((2670,(0.3,0.7)),(3867,(0.3,0.7)),(1341,(0.3,0.7)),(2990,(0.5,)),(1,(0.5,)),(197,(0.5,))):
    z0,z1=info[str(i)]['z']
    for f in fr:
        z=int(z0+(z1-z0)*f); c=np.asarray(C[z]).astype(float); l=np.asarray(L[z])==i
        g=np.clip((c+300)/1000,0,1); rgb=np.stack([g,g,g],-1)*255
        edge=l&~ndi.binary_erosion(l); rgb[ndi.binary_dilation(edge,iterations=1)]=[255,40,40]
        sy,sx=int(cys[z]),int(cxs[z]); rgb[max(sy-1,0):sy+2,max(sx-1,0):sx+2]=[40,200,255]
        im=Image.fromarray(rgb.astype(np.uint8)).resize((430*2,108*2),Image.NEAREST)
        ImageDraw.Draw(im).text((4,2),f'塊 {i}  z={z/2:.0f} mm（水色の点=背骨の中心線）',fill=(255,255,0),font=F); tiles.append(im)
S=Image.new('RGB',(860,len(tiles)*220),(0,0,0))
for k,t in enumerate(tiles): S.paste(t,(0,k*220))
S.save('comps_xsec.png'); print(S.size)

# A3 頭の翼の左右差の案（derolled6、z 0〜139 mm。頭の片側の半分を鏡映して反対側に使う。正中は上から見た外形の鏡映で u≈-1 mm、0° に直してある）
#  測った左右差: 翼の前後の幅（|u|=100 mm）は左 51 mm・右 70 mm。右の翼の先は腹側へ約 15 mm 下がる（z=100 mm、|u|=150 mm で左 v 7〜13、右 25〜32 mm）
import hh_paths; hh_paths.cd_work()
import numpy as np
from PIL import Image, ImageDraw, ImageFont
F=hh_paths.font(15)
D=np.load('derolled6.npy',mmap_mode='r'); H=np.asarray(D[0:140]).copy()     # (z, v, u)
cols=np.arange(300); wingL=cols<150; wingR=cols>=150
def variant(k):
    V=H.copy(); M=H[:,:,::-1]
    if k=='R': V[:,:,wingL]=M[:,:,wingL]          # 右の翼を鏡映して左にも使う
    if k=='L': V[:,:,wingR]=M[:,:,wingR]
    return V
def pic(V):
    top=V.max(1).astype(float); front=V[20:130].max(0).astype(float)          # top (z,u), front (v,u)
    g=lambda m:(255-np.clip((m+600)/1100,0,1)*225).astype(np.uint8)
    t=Image.fromarray(g(top)).resize((300*2,int(140*2/1.47)),Image.BILINEAR)   # 縦 z 1mm, 横 u 1.47mm → mm をそろえる
    f=Image.fromarray(g(front)[110:190]).resize((600,80*2),Image.BILINEAR)
    return t,f
labs=[('CT','① CT のまま'),('R','② 画面の右の半分を左右に使う'),('L','③ 画面の左の半分を左右に使う')]
tiles=[(pic(variant(k)),lab) for k,lab in labs]
W=600*3+40; H_=tiles[0][0][0].height+tiles[0][0][1].height+90
S=Image.new('RGB',(W,H_),(255,255,255)); d=ImageDraw.Draw(S); x=0
for (t,f),lab in tiles:
    d.text((x+4,4),lab,fill=(0,0,0),font=F); S.paste(t,(x,28)); d.text((x+4,t.height+32),'前から（上が背）',fill=(80,80,80),font=F); S.paste(f,(x,t.height+52)); x+=620
d.text((4,H_-24),'上段=背中から（上が吻）。②③は頭（吻端〜140 mm）の片側の半分を鏡映。体の左右のどちらが画面の右かは未確認',fill=(60,60,60),font=F)
S.save('head_options.png'); print(S.size)

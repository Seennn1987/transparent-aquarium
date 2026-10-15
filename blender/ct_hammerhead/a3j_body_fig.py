# 確認図: A3 で起こした体（derolled4）の全身を横と背中から。ひれの決定後の位置を重ねる
import hh_paths; hh_paths.cd_work()
import numpy as np
from PIL import Image, ImageDraw, ImageFont
F=hh_paths.font(15)
M=np.load('derolled7_mips.npy'); pe=np.load('pect_posed.npz'); pv=np.load('pelvic_posed.npz')
def im(m,rows):
    g=np.clip((m.astype(float)+600)/1100,0,1); a=(255-g*225).astype(np.uint8).T[rows[0]:rows[1]]
    return Image.fromarray(a).convert('RGB')
def paint(img,pts,col,ax_v,row0):
    a=np.asarray(img).copy(); i=pts[:,1].astype(int); j=(pts[:,ax_v]/1.47+150-row0).astype(int)
    ok=(i>=0)&(i<a.shape[1])&(j>=0)&(j<a.shape[0]); a[j[ok],i[ok]]=col; return Image.fromarray(a)
side=im(M[1],(60,240)); top=im(M[0],(40,260))
# ひれは決定後の形を重ねる（横: v、背中: u）
for k,col in (('left',(220,60,60)),('right',(40,110,220))):
    side=paint(side,pe[k],col,2,60); top=paint(top,pe[k],col,0,40)
    side=paint(side,pv[k],col,2,60); top=paint(top,pv[k],col,0,40)
def fix(img): return img.resize((img.width,int(img.height*1.47)),Image.BILINEAR)   # 縦横の mm をそろえる
side=fix(side); top=fix(top)
S=Image.new('RGB',(side.width+10,side.height+top.height+130),(255,255,255)); d=ImageDraw.Draw(S)
d.text((4,4),'横から（上が背、左が吻）',fill=(0,0,0),font=F); S.paste(side,(0,26))
d.text((4,side.height+40),'背中から',fill=(0,0,0),font=F); S.paste(top,(0,side.height+62))
for mm in range(0,1046,100):
    d.line((mm,26,mm,34),fill=(220,0,0)); d.text((mm+2,26),str(mm),fill=(200,0,0),font=F)
d.text((4,S.height-24),'A3 の決定をすべて入れた体（尾の反り約20°、頭の向き・頭〜胸の倒れ・頭の翼を直した後）。赤・青=決定後の胸びれと腹びれ（左・右）。数字は吻端からの mm',fill=(60,60,60),font=F); d.text((4,S.height-46),'灰の体積には CT の元のひれ（垂れた胸びれなど）もまだ写っている。メッシュにする段（A4）で決定後のひれに置き換える',fill=(60,60,60),font=F)
S.save('body_a3.png'); print(S.size)

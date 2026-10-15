import hh_paths; hh_paths.cd_work()
import numpy as np
from PIL import Image, ImageDraw, ImageFont
F=hh_paths.font(15)
A=np.load('derolled_mips.npy'); B=np.load('derolled3_mips.npy')
def im(m,lo=-600,hi=500):
    g=np.clip((m[600:1046].astype(float)-lo)/(hi-lo),0,1)          # z 600..1045 mm, 縦=v（または u）
    a=(255-g*225).astype(np.uint8).T[60:240]                      # 縦 ±88 mm
    return Image.fromarray(a).resize((a.shape[1]*2,a.shape[0]*2),Image.NEAREST)
rows=[('前（derolled2）: 横から — 背骨を一直線にしたため尾の反りが消えている',im(A[1])),
      ('後（derolled3）: 横から — 700 mm より後ろは背骨の背腹のずれを残した',im(B[1])),
      ('後（derolled3）: 背中から — 左右の曲がりは消したまま',im(B[0]))]
W=rows[0][1].width+20; H=sum(r[1].height+30 for r in rows)+40
S=Image.new('RGB',(W,H),(255,255,255)); d=ImageDraw.Draw(S); y=0
for title,img in rows:
    d.text((4,y+4),title,fill=(0,0,0),font=F); S.paste(img,(0,y+26))
    for mm in range(650,1046,50):
        x=(mm-600)*2; d.line((x,y+26,x,y+34),fill=(220,0,0)); d.text((x+2,y+26),str(mm),fill=(200,0,0),font=F)
    y+=img.height+30
d.text((4,H-26),'上が背、左が吻。数字は吻端からの mm。灰の濃さ=CT の値（骨ほど濃い）',fill=(60,60,60),font=F)
S.save('tail_upturn.png'); print(S.size)

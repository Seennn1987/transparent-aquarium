"""形の物差し（記録 136）: shape_score.py <shape.py の json>。成体の資料と比べる。長さは S（肩関節–股関節）か SVL で割る"""
import json,sys,numpy as np
d=json.load(open(sys.argv[1])); B={k:np.array(v) for k,v in d['B'].items()}
V=np.array([x[:5] for x in d['verts']],float); top=[x[5] for x in d['verts']]
F=np.array([0,-1,0.]); U=np.array([-1,0,0.]); Lt=np.array([0,0,1.])
sh=(B['fL_upper']+B['fR_upper'])/2; hp=(B['hL_upper']+B['hR_upper'])/2
sp=np.array([p for n,p in d['spine']])
seg=np.linalg.norm(np.diff(sp,axis=0),axis=1)
names=[n for n,p in d['spine']]
# S は背骨に沿って測る（記録 102 の「体軸に沿った S」。AMNH の骨格はまっすぐ組まれ、直線と背骨に沿った長さが同じ）
arc=np.r_[0,np.cumsum(seg)]
def onspine(p):
    i=np.argmin(np.linalg.norm(sp-p,axis=1)); return arc[i]
S=onspine(hp)-onspine(sh); S_line=np.linalg.norm(sh-hp)
head=V[(V[:,4]>0.5)]
sn=head[np.argmax(head[:,:3]@F)][:3]
# SVL: 吻端→後頭（v01）の直線＋背骨に沿って総排泄口（股関節の後ろ、腰帯の後ろの端。ここでは v24 の位置）まで
svl=np.linalg.norm(sn-sp[0])+seg[:names.index('v24')].sum()
tail=seg[names.index('v24'):].sum()
# 頭: 頭の骨（head）の重みの頂点で。兜の高さは出典（Bauerová 2020）の頭長が吻端–顎関節で、モデルに顎関節の目印が無いので比べない。
# 頭の重みの頂点で、吻端から最も遠い点（兜の後ろの先）までを HL、上下の幅を HCH
far=head[np.argmax(np.linalg.norm(head[:,:3]-sn,axis=1))][:3]; HL=np.linalg.norm(far-sn)
hu=head[:,:3]@U; HCH=hu.max()-hu.min()
# 胴の輪切り（手足の重み 0.2 未満）: 肩–股の t の位置で、深さ（上下）と幅（左右）
body=V[V[:,3]<0.2]
ax=(hp-sh)/S
def cut(t):
    c=sh+(hp-sh)*t; dd=(body[:,:3]-c)@((hp-sh)/np.linalg.norm(hp-sh)); sl=body[np.abs(dd)<1.0][:,:3]
    if len(sl)<10: return None,None
    return (sl@U).max()-(sl@U).min(), (sl@Lt).max()-(sl@Lt).min()
L=lambda a,b: np.linalg.norm(B[a]-B[b])
m={'S_mm':S,'S（直線）_mm':S_line,'SVL_mm':svl,
 'S÷SVL':S/svl,'尾÷SVL':tail/svl,'HL÷SVL':HL/svl,
 '上腕骨÷S':L('fL_upper','fL_lower')/S,'前腕÷S':L('fL_lower','fL_hand')/S,'大腿骨÷S':L('hL_upper','hL_lower')/S,'脛骨÷S':L('hL_lower','hL_foot')/S,
 '左右の肩関節÷S':L('fL_upper','fR_upper')/S,'左右の股関節÷S':L('hL_upper','hR_upper')/S}
for t in (0.1,0.5,0.45,0.9):
    a,b=cut(t)
    if a: m[f'胴の深さ t{t}÷S']=a/S; m[f'胴の幅 t{t}÷S']=b/S
# 実物（範囲）と出典
R={'S÷SVL':(0.75,0.76,'Luger 2021 雄 0.756・雌 0.753'),
 '尾÷SVL':(1.07,1.24,'Luger 2021 雌 1.07・雄 1.24'),
 'HL÷SVL':(0.33,0.40,'Drown 2022 成体雄 0.404、SVL 9–13 cm 0.33–0.40'),
 '上腕骨÷S':(0.238,0.242,'AMNH 0.242・X 線雄 0.238'),
 '前腕÷S':(0.203,0.221,'X 線雄 0.203・AMNH 0.221'),
 '大腿骨÷S':(0.219,0.240,'AMNH 0.224・X 線 0.219–0.240'),
 '脛骨÷S':(0.162,0.190,'AMNH 0.162（下限）・X 線雄 0.190'),
 '左右の肩関節÷S':(0.20,0.20,'背腹 X 線 2 枚 0.203・0.202'),
 '左右の股関節÷S':(0.12,0.17,'背腹 X 線 0.122・0.167'),
 '胴の深さ t0.5÷S':(0.34,0.60,'側面 X 線 背の皮–腹 雌 0.341・雄 0.601'),
 '胴の幅 t0.5÷S':(0.34,0.39,'背腹 X 線 中ほど 0.338・0.385（腹ばいで広く出る）'),
 '胴の幅 t0.1÷S':(0.26,0.29,'背腹 X 線 肩のすぐ後ろ 0.258・0.289')}
# 記録 138: 胴の幅の並び（いちばん広い所との比）は、腹ばいで押された X 線でなく、上から写した生きた個体（YouTube z3M1RsEmY1Y 3.3 秒、若い個体、ヤシの葉の上）で比べる。合格は ±0.05
LIVE={0.06:0.78,0.30:0.90,0.48:1.00,0.61:0.98,0.76:0.92,0.91:0.82,1.00:0.61}
tol=0.05
ok=0;n=0
ws={}
for t in LIVE:
    a,b=cut(t)
    if b: ws[t]=b
mx=max(ws.values())
for t,r in LIVE.items():
    if t in ws:
        v=ws[t]/mx; good=abs(v-r)<=0.05; ok+=good; n+=1
        print(f"{'○' if good else '×'} 胴の幅の並び t{t:.2f}  モデル {v:.2f}  実物 {r:.2f}  （上から写した生きた個体、いちばん広い所との比）")
for k,v in m.items():
    if k in R:
        lo,hi,src=R[k]; good=lo*(1-tol)<=v<=hi*(1+tol); ok+=good; n+=1
        print(f"{'○' if good else '×'} {k:16s} モデル {v:.3f}  実物 {lo:.3f}〜{hi:.3f}  （{src}）")
    else: print(f"  {k:16s} モデル {v:.3f}")
print(f'合格 {ok}/{n}（実物の幅 ±5%）')

import numpy as np, matplotlib, glob; matplotlib.use('Agg')
import matplotlib.pyplot as plt, matplotlib.patches as pa
from PIL import Image
plt.rcParams['font.family']=['Noto Sans CJK JP','DejaVu Sans']
TR='/root/.claude/projects/-home-claude/1d1858a9-9367-5399-8183-e4b2d1185ae5/tool-results/'
fs=sorted(sum([glob.glob(TR+'*blob-1791886%d*'%d) for d in (5,6,7,8)],[]))
S=[(13,(187,287,237,387),'写真01\nCreema 17230557',(0.20,0.95),(0.0,0.60),(150,230,400,480)),
   (19,(55,40,145,200),'標本2\nCreema 17230551',(0.26,1.00),(0.0,1.00),None),
   (22,(30,100,175,290),'標本4\n楽天 透明屋パク',(0.23,0.89),(0.03,0.86),None),
   (27,(200,70,290,260),'ma-paku 出品\nフリル 1991114482',(0.15,0.85),(0.0,0.52),None),
   (8,(110,60,290,115),'角のあるカメレオン\n（別種・種名不明）',(0.12,1.00),(0.25,0.94),None)]
fig=plt.figure(figsize=(22,6.2))
def occ(ax,fn,title):
    z=np.load(fn); t=z['t']; f=z['frac']; lab=z['lab']
    H,_,_=np.histogram2d(np.clip(f[lab>0],0,1),np.clip(t[lab>0],0,1),bins=[30,50],range=[[0,1],[0,1]])
    Hc,_,_=np.histogram2d(np.clip(f,0,1),np.clip(t,0,1),bins=[30,50],range=[[0,1],[0,1]])
    ax.imshow(np.where(Hc>0,H/np.maximum(Hc,1),np.nan),extent=[0,1,1,0],cmap='YlOrBr',vmin=0,vmax=1,aspect='auto')
    ax.set_xlabel('肩 → 股（t）'); ax.set_ylabel('背（脊椎）→ 腹'); ax.set_title(title,fontsize=11)
    cols=['red','blue','green','purple','gray']
    for k,(i,r,name,tt,dd,crop) in enumerate(S):
        ax.add_patch(pa.Rectangle((tt[0],dd[0]),tt[1]-tt[0],dd[1]-dd[0],fill=False,ec=cols[k],lw=1.8,ls='--',label=name.split('\n')[0]))
ax=fig.add_axes([0.04,0.1,0.29,0.75]); occ(ax,'r/ms/cmp_coords.npz','② 前の版（色 = 臓器の割合）と参考写真の塊（破線、目測）'); ax.legend(fontsize=8,loc='center left',framealpha=0.9)
ax=fig.add_axes([0.37,0.1,0.29,0.75]); occ(ax,'r/ms/cmp_coords2.npz','③ 直した版')
ax=fig.add_axes([0.70,0.1,0.29,0.75]); ax.set_xlim(0,1); ax.set_ylim(1,0)
ax.set_xlabel('肩 → 股（t）'); ax.set_ylabel('背（脊椎）→ 腹'); ax.set_title('④ 直した配置の考え方（模式図・仮）',fontsize=11)
B=[('縮んだ肺\n（描かない）',0.0,0.15,0.0,0.6,'#eeeeee'),('心臓',0.02,0.13,0.62,0.95,'#d98'),('肝臓（右・左）',0.17,0.40,0.30,0.95,'#a86'),
   ('胃',0.15,0.40,0.05,0.30,'#cb9'),('腸と中身\n（塊の主体）',0.40,0.81,0.05,0.80,'#986'),('脂肪体',0.40,0.60,0.80,1.0,'#ee9'),
   ('腎臓',0.81,1.0,0.0,0.28,'#c88'),('結腸',0.81,1.0,0.30,0.65,'#875')]
for n,a,b,c,d,col in B:
    ax.add_patch(pa.Rectangle((a,c),b-a,d-c,fc=col,ec='k',lw=0.8)); ax.text((a+b)/2,(c+d)/2,n,ha='center',va='center',fontsize=9)
ax.add_patch(pa.Rectangle((0.2,0.0),0.75,0.86,fill=False,ec='red',lw=2,ls='--'))
ax.text(0.99,0.97,'赤破線: 写真 5 枚の中央値 t 0.20〜0.95・深さ 0〜0.86',color='red',ha='right',va='bottom',fontsize=9)
fig.text(0.01,0.95,'②〜④ は胴を「肩→股」×「背→腹」の 0〜1 に引き伸ばした座標（個体と写真の大きさの違いを消すため）。臓器の割合: 前の版 体腔の 17%（残り 83% は「肺」として空けていた）→ 直した版 33%',fontsize=10)
fig.savefig('organs_ref_layout.png',dpi=110)

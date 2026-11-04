"""運ぶ間の通り道の物差し（記録 140）: score_swing.py <_joints.json>
実物: Wimberly ら 2021 の床の歩き（手前の後ろ脚の足首 305.3→306.9 秒・股から、手前の前脚の手首 307.7→309.1 秒・肩から、0.1 秒ごと）。
運ぶ間を 0.1 ごとに 10 に分け、足首（手首）の前後と上下（股・肩から、÷ 吻端–股関節）を比べる。合格の幅 0.05 L"""
import json,sys,numpy as np
D='/Users/shoui/transparent-aquarium/画像サンプル収集/エボシカメレオン/収集_2026-10-26/関節の動き/場面1_ZA_304-310s.json'
C=json.load(open(D))['コマ']; L=123.3
def real(limb,root,pt,t0,t1):
    xs=[];F=[];U=[]
    for x in C:
        t=x['時刻_秒']
        if t0-0.05<=t<=t1+0.05 and x[limb].get(pt) and x.get(root):
            a=x[limb][pt];h=x[root];l=x['計算']['尺度_px']; xs.append((t-t0)/(t1-t0)); F.append(-(a[0]-h[0])/l); U.append(-(a[1]-h[1])/l)
    return np.array(xs),np.array(F),np.array(U)
R={'hR':real('手前後脚','股関節','足首',305.3,306.9),'fR':real('手前前脚','肩','手首',307.7,309.1)}
rows=json.load(open(sys.argv[1])); ok=n=0
for k,nm in [('hR','後ろ脚 足首'),('fR','前脚 手首')]:
    st=[x[k]['st'] for x in rows]; offs=[i for i in range(1,len(rows)) if not st[i] and st[i-1]]
    i0=offs[0]; i1=[i for i in range(i0,len(rows)) if st[i]][0]
    ms=np.array([(rows[i]['t']-rows[i0-1]['t'])/(rows[i1]['t']-rows[i0-1]['t']) for i in range(i0-1,i1+1)])
    mF=np.array([rows[i][k]['ankle'][0]/L for i in range(i0-1,i1+1)]); mU=np.array([rows[i][k]['ankle'][1]/L for i in range(i0-1,i1+1)])
    rs,rF,rU=R[k]
    for q in np.arange(0.1,0.95,0.1):
        rf,ru=np.interp(q,rs,rF),np.interp(q,rs,rU); mf,mu=np.interp(q,ms,mF),np.interp(q,ms,mU)
        for lab,a,b in [('前後',mf,rf),('上下',mu,ru)]:
            g=abs(a-b)<=0.05; ok+=g; n+=1
            if '-v' in sys.argv or not g: print(f"{'○' if g else '×'} {nm} {q:.1f} {lab} モデル {a:+.3f} 実物 {b:+.3f}")
print(f'合格 {ok}/{n}')

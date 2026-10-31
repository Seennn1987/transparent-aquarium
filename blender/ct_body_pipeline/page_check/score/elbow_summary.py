import json,sys,numpy as np
d=json.load(open(sys.argv[1]))
R=[]
for r in d:
    f=r['fL']
    if not f['st']: continue
    sh,el,wr=map(np.array,(f['sh'],f['el'],f['wr']))
    R.append((el[2]-r['wall'][0], sh[1]-el[1], sh[0]-el[0], np.linalg.norm(el-sh)))
R=np.array(R)
print(f"着いている間 肘の皮の外への出 {R[:,0].mean():+.1f} mm（{R[:,0].min():+.1f}〜{R[:,0].max():+.1f}）  肘の肩からの下がり {R[:,1].mean():.1f} mm  後ろ {R[:,2].mean():+.1f} mm")

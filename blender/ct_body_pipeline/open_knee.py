"""展示の姿勢の左膝を開いた姿勢を作る（記録 144）: open_knee.py <元の pose_jar> <出力> <膝の角（度）>
膜は姿勢によらず静止の骨に戻して付けるので、膜を作るときだけ使う。左のすねから先（hL_lower・hL_foot・指）を、大腿とすねの面に直角で膝を通る軸のまわりに回す"""
import numpy as np,sys
from scipy.spatial.transform import Rotation as R
P=dict(np.load(sys.argv[1])); bn=[str(x) for x in P['names']]; M=P['M'].copy(); H=P['head'].copy(); T=P['tail'].copy()
want=float(sys.argv[3])
i=lambda n:bn.index(n)
a=H[i('hL_upper')]; b=H[i('hL_lower')]; c=H[i('hL_foot')]
u=a-b; v=c-b; cur=np.degrees(np.arccos(u@v/np.linalg.norm(u)/np.linalg.norm(v)))
ax=np.cross(v,u); ax/=np.linalg.norm(ax)
rot=R.from_rotvec(-ax*np.radians(want-cur)).as_matrix()   # v を u から遠ざける向き
chain=[n for n in bn if n.startswith('hL_') and n not in ('hL_upper','hL_girdle')]
G=np.eye(4); G[:3,:3]=rot; G[:3,3]=b-rot@b
for n in chain:
    M[i(n)]=G@M[i(n)]; H[i(n)]=rot@H[i(n)]+G[:3,3]; T[i(n)]=rot@T[i(n)]+G[:3,3]
v2=H[i('hL_foot')]-b; new=np.degrees(np.arccos(u@v2/np.linalg.norm(u)/np.linalg.norm(v2)))
if abs(new-want)>1: raise SystemExit(f'向きが逆: {new:.0f}°')
P['M']=M; P['head']=H; P['tail']=T; np.savez(sys.argv[2],**P); print(f'左膝 {cur:.0f}° → {new:.0f}°、回した骨 {len(chain)}')

"""glb の読み書き（記録 143）"""
import json,struct,numpy as np
CT={5126:np.float32,5123:np.uint16,5121:np.uint8,5125:np.uint32}; NC={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}
class GLB:
    def __init__(s,path):
        raw=open(path,'rb').read(); jl=struct.unpack('<I',raw[12:16])[0]; s.J=json.loads(raw[20:20+jl]); bo=20+jl; bl=struct.unpack('<I',raw[bo:bo+4])[0]; s.BIN=bytearray(raw[bo+8:bo+8+bl])
    def acc(s,i):
        a=s.J['accessors'][i]; v=s.J['bufferViews'][a['bufferView']]; n=NC[a['type']]; dt=CT[a['componentType']]
        st=v.get('byteStride'); off=v.get('byteOffset',0)+a.get('byteOffset',0)
        if st and st!=n*np.dtype(dt).itemsize: raise ValueError('stride')
        return np.frombuffer(s.BIN,dt,a['count']*n,off).reshape(a['count'],n).copy(), off, dt
    def put(s,i,arr):
        a,off,dt=s.acc(i); arr=np.ascontiguousarray(arr.astype(dt)); assert arr.shape==a.shape; s.BIN[off:off+arr.nbytes]=arr.tobytes()
        if s.J['accessors'][i].get('min') is not None: s.J['accessors'][i]['min']=arr.min(0).tolist(); s.J['accessors'][i]['max']=arr.max(0).tolist()
    def node(s,name): return next(n for n in s.J['nodes'] if n.get('name')==name)
    def save(s,path):
        j=json.dumps(s.J,separators=(',',':')).encode(); j+=b' '*((4-len(j)%4)%4); b=bytes(s.BIN); b+=b'\0'*((4-len(b)%4)%4)
        out=b'glTF'+struct.pack('<II',2,12+8+len(j)+8+len(b))+struct.pack('<I',len(j))+b'JSON'+j+struct.pack('<I',len(b))+b'BIN\0'+b
        open(path,'wb').write(out)
def skin_data(g,mesh_node='CH_Skin'):
    nd=g.node(mesh_node); pr=g.J['meshes'][nd['mesh']]['primitives'][0]; sk=g.J['skins'][nd['skin']]
    P=g.acc(pr['attributes']['POSITION'])[0]; Jt=g.acc(pr['attributes']['JOINTS_0'])[0]; W=g.acc(pr['attributes']['WEIGHTS_0'])[0]
    IBM=g.acc(sk['inverseBindMatrices'])[0].reshape(-1,4,4).transpose(0,2,1)
    names=[g.J['nodes'][j]['name'] for j in sk['joints']]
    bindpos=np.array([np.linalg.inv(m)[:3,3] for m in IBM])
    return dict(P=P,J=Jt,W=W,names=names,bind=bindpos,prim=pr,skin=sk)

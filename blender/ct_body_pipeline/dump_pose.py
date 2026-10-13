# 展示の姿勢（POSE_JAR）での骨ごとの変形行列（静止 → 展示、モデル座標）と、静止の骨の位置を書き出す
import runpy, os, sys, numpy as np, bpy
HERE=os.path.dirname(os.path.abspath(__file__))
r=runpy.run_path(os.path.join(HERE,'rig_chameleon_ct.py'),run_name='y')
g=runpy.run_path(r['GEN'],run_name='x')
coll,rigob,skel,rig=g['build'](); d,_,k=g['load']()
r['build_pose'](rigob,d,k,r['POSE_JAR']); bpy.context.view_layer.update()
W=rigob.matrix_world; Wi=W.inverted()
names=[]; M=[]; H=[]; T=[]
for b in rigob.data.bones:
    pb=rigob.pose.bones[b.name]
    names.append(b.name); M.append(np.array(W@pb.matrix@b.matrix_local.inverted()@Wi))
    H.append(np.array(W@b.head_local)); T.append(np.array(W@b.tail_local))
np.savez(sys.argv[-1], names=np.array(names), M=np.array(M), head=np.array(H), tail=np.array(T), k=np.array(k))
print('dumped', len(names))

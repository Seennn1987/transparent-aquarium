"""足だけの膜（feet_skin.py）を体の膜（skinbody.py の skin_posed.npz）につなぐ（記録 31 の案。2026-10-18）。画面なしの Blender で動かす。

  cd <案の作業フォルダ> && Blender -b -P merge_feet.py -- <体の skin_posed.npz> <feet_posed.npz> <出力 merged_posed.npz> [足の面の数=40000]

・足ごとに、足首（骨組みの足の付け根）から下腿の向きへ CUT_MM（1.0 mm）上の平面より先を、足の骨の範囲 + 3 mm の箱で体の膜から切り取る
  （Boolean の差、EXACT）
・足の膜は Decimate で足 1 つ FEET_FACES 面に減らしてから、体の膜と Boolean の和（EXACT）でつなぐ。足の膜は下腿の足首側 3 mm を含むので、
  切り口と重なる
・面の向き: Blender の中では外向きにそろえ、書き出しでは skin_posed.npz と同じ内向きに戻す。閉じていない辺の数を出す
"""
import os
import sys
import numpy as np
import bpy
import bmesh
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
body_p, feet_p, out_p = argv[:3]; FEET_FACES = int(argv[3]) if len(argv) > 3 else 40000
CUT_MM = float(os.environ.get('CUT_MM', '1.0')); TOTAL_FACES = int(os.environ.get('TOTAL_FACES', '149000'))
P = np.load('pose_jar.npz'); bn = [str(x) for x in P['names']]; k = float(P['k']); MM = k
def ct2m(p): p = np.asarray(p, float); return np.stack([p[..., 1], -p[..., 2], -p[..., 0]], -1) * k
def posed(n, x): M = P['M'][bn.index(n)]; return ct2m(x) @ M[:3, :3].T + M[:3, 3]
d = np.load('chameleon_body_ct.npz'); rn = [str(s) for s in d['rig__names']]

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
def mesh(name, v, f):
    me = bpy.data.meshes.new(name); me.from_pydata(np.asarray(v, float).tolist(), [], np.asarray(f).tolist()); me.update()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); return ob
def outward(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()
def report(ob, tag):
    bm = bmesh.new(); bm.from_mesh(ob.data)
    nm = sum(1 for e in bm.edges if not e.is_manifold); vol = bm.calc_volume(signed=True); bm.free()
    print(f'{tag}: 面 {len(ob.data.polygons)}、閉じていない辺 {nm}、体積 {vol / MM ** 3:.1f} mm3', flush=True)
def apply_bool(ob, other, op):
    m = ob.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.solver = 'EXACT'; m.object = other
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier=m.name)

B = np.load(body_p); body = mesh('body', B['v'], B['f']); outward(body); report(body, '体の膜')
Fz = np.load(feet_p); feet = mesh('feet', Fz['v'], Fz['f']); outward(feet); report(feet, '足の膜（細かい）')
dm = feet.modifiers.new('d', 'DECIMATE'); dm.ratio = min(1.0, 2 * FEET_FACES / len(feet.data.polygons))
bpy.context.view_layer.objects.active = feet; bpy.ops.object.modifier_apply(modifier=dm.name); outward(feet); report(feet, '足の膜（減らした）')
LIMBS = os.environ.get('LIMBS', 'hL_foot,hR_foot').split(',')            # 手は LIMBS=fL_hand,fR_hand（記録 33）
for n in LIMBS:
    ankle = posed(n, d['rig__head'][rn.index(n)][None])[0]
    lo_n = n.split('_')[0] + '_lower'
    knee = posed(lo_n, d['rig__head'][rn.index(lo_n)][None])[0]
    ax = ankle - knee; ax /= np.linalg.norm(ax)
    plane = ankle - ax * CUT_MM * MM
    x = posed(n, d[n + '__v'])
    e1 = np.cross(ax, [0, 0, 1.0]); e1 = e1 / np.linalg.norm(e1) if np.linalg.norm(e1) > 1e-6 else np.array([1.0, 0, 0]); e2 = np.cross(ax, e1)
    R = np.c_[e1, e2, ax]; q = (x - plane) @ R
    lo = q.min(0) - 3 * MM; hi = q.max(0) + 3 * MM; lo[2] = 0.0
    corners = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
    cv = plane + corners @ R.T
    faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    box = mesh('cut_' + n, cv, faces); outward(box)
    apply_bool(body, box, 'DIFFERENCE'); bpy.data.objects.remove(box)
    report(body, f'体の膜（{n} を切った）')
apply_bool(body, feet, 'UNION'); outward(body); report(body, 'つないだ膜')
# 書き出し（generate_chameleon_ct_body.py）は膜が CH_SKIN_FACES（15 万）面を超えると静止の形で間引き、重みを近い頂点から写すので、
#   静止の形で重なる手足と体の頂点が混ざって三角形が伸びた（記録 31）。展示の姿勢のここで 15 万面以下にしておく
if len(body.data.polygons) > TOTAL_FACES:
    dm = body.modifiers.new('d', 'DECIMATE'); dm.ratio = TOTAL_FACES / len(body.data.polygons) * 0.995
    bpy.context.view_layer.objects.active = body; bpy.ops.object.modifier_apply(modifier=dm.name); outward(body); report(body, 'つないだ膜（減らした）')
me = body.data; v = np.array([p.co[:] for p in me.vertices])
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
f = np.array([p.vertices[:] for p in me.polygons]); f = f[:, ::-1]                    # skin_posed.npz と同じ内向き
v = np.array([p.co[:] for p in me.vertices])
np.savez_compressed(out_p, v=v.astype(np.float32), f=f.astype(np.int32)); print('saved', out_p, len(v), len(f))

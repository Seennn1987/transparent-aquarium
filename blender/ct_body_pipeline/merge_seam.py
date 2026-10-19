"""seam_patch.py のパッチで、膜をつないだ所を差し替える（記録 36 の案。2026-10-19）。画面なしの Blender で動かす。

  cd <案の作業フォルダ> && Blender -b -P merge_seam.py -- <膜 skin_posed.npz> <seam_patch.npz> <出力 merged_posed.npz>

膜から手足ごとの切る箱を引き（Boolean の差、EXACT）、パッチを足す（和）。展示の姿勢のまま TOTAL_FACES（14.9 万）面以下に減らす。
面の向きは merge_feet.py と同じ（中では外向き、書き出しは内向き）。
"""
import os
import sys
import numpy as np
import bpy
import bmesh

argv = sys.argv[sys.argv.index('--') + 1:]
skin_p, patch_p, out_p = argv[:3]
TOTAL_FACES = int(os.environ.get('TOTAL_FACES', '149000')); PATCH_FACES = int(os.environ.get('PATCH_FACES', '15000'))
k = float(np.load('pose_jar.npz')['k']); MM = k
bpy.ops.wm.read_factory_settings(use_empty=True); sc = bpy.context.scene
def mesh(name, v, f):
    me = bpy.data.meshes.new(name); me.from_pydata(np.asarray(v, float).tolist(), [], np.asarray(f).tolist()); me.update()
    ob = bpy.data.objects.new(name, me); sc.collection.objects.link(ob); return ob
def outward(ob):
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()
def report(ob, tag):
    bm = bmesh.new(); bm.from_mesh(ob.data); nm = sum(1 for e in bm.edges if not e.is_manifold); vol = bm.calc_volume(signed=True); bm.free()
    print(f'{tag}: 面 {len(ob.data.polygons)}、閉じていない辺 {nm}、体積 {vol / MM ** 3:.1f} mm3', flush=True)
def apply_bool(ob, other, op):
    m = ob.modifiers.new('b', 'BOOLEAN'); m.operation = op; m.solver = 'EXACT'; m.object = other
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.modifier_apply(modifier=m.name)
B = np.load(skin_p); body = mesh('body', B['v'], B['f']); outward(body); report(body, '膜')
Z = np.load(patch_p); limbs = sorted({k_[4:] for k_ in Z.files if k_.startswith('cut_')})
faces = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
for n in limbs:
    box = mesh('cut_' + n, Z['cut_' + n], faces); outward(box); report(box, f'切る箱 {n}'); apply_bool(body, box, 'DIFFERENCE'); bpy.data.objects.remove(box); report(body, f'切った膜（{n}）')
    pt = mesh('patch_' + n, Z['patch_' + n + '__v'], Z['patch_' + n + '__f']); outward(pt)
    dm = pt.modifiers.new('d', 'DECIMATE'); dm.ratio = min(1.0, PATCH_FACES / len(pt.data.polygons))   # 細かいままだとブール演算で穴が開いた
    bpy.context.view_layer.objects.active = pt; bpy.ops.object.modifier_apply(modifier=dm.name); outward(pt); report(pt, f'パッチ {n}')
    apply_bool(body, pt, 'UNION'); bpy.data.objects.remove(pt); outward(body); report(body, f'差し替えた膜（{n}）')
if len(body.data.polygons) > TOTAL_FACES:
    dm = body.modifiers.new('d', 'DECIMATE'); dm.ratio = TOTAL_FACES / len(body.data.polygons) * 0.995
    bpy.context.view_layer.objects.active = body; bpy.ops.object.modifier_apply(modifier=dm.name); outward(body); report(body, '差し替えた膜（減らした）')
me = body.data
bm = bmesh.new(); bm.from_mesh(me); bmesh.ops.triangulate(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
v = np.array([p.co[:] for p in me.vertices]); f = np.array([p.vertices[:] for p in me.polygons])[:, ::-1]
np.savez_compressed(out_p, v=v.astype(np.float32), f=f.astype(np.int32)); print('saved', out_p, len(v), len(f))

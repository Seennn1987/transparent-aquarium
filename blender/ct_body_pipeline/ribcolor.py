# 展示の姿勢で、肋骨を 1 本ずつ色分けして描く（膜なし）
import sys, os, runpy, numpy as np, bpy
out=sys.argv[sys.argv.index('--')+1]
r=runpy.run_path(os.path.abspath('ctb/rig_chameleon_ct.py'),run_name='y')
g=runpy.run_path(r['GEN'],run_name='x')
coll,rigob,skel,rig=g['build'](); d,_,k=g['load']()
r['build_pose'](rigob,d,k,r['POSE_JAR'])
sk=bpy.data.objects.get('CH_Skin'); sk.hide_render=True
me=skel.data; gi={vg.index:vg.name for vg in skel.vertex_groups}
col=me.color_attributes.new('C','FLOAT_COLOR','POINT')
rng=np.random.default_rng(3); pal={}
for i,v in enumerate(me.vertices):
    n=gi[max(v.groups,key=lambda x:x.weight).group] if len(v.groups) else ''
    if n.startswith('rib'):
        if n not in pal: pal[n]=list(rng.uniform(0.15,1.0,3))+[1.0]
        c=pal[n]
    else: c=[0.35,0.35,0.35,1.0]
    col.data[i].color=c
mat=skel.data.materials[0]; nt=mat.node_tree
bsdf=next(n for n in nt.nodes if n.type=='BSDF_PRINCIPLED'); at=nt.nodes.new('ShaderNodeAttribute'); at.attribute_name='C'
nt.links.new(at.outputs['Color'],bsdf.inputs['Base Color'])
r['render'](coll,skel,out)
# 色の凡例
import json; json.dump({k_:[round(x,2) for x in v[:3]] for k_,v in pal.items()},open(out.replace('.png','.json'),'w'))

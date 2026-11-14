#!/usr/bin/env python3
"""Export authentic *rest-pose* exterior A1/B1 skin geometry from AB's embedded ABP2 assets.

Read-only: does not touch the original HTML. The resulting GLBs are visual-only,
not rigged and not equivalent to the live runtime's pose/facial/physiology state.
"""
from __future__ import annotations
import argparse, base64, gzip, hashlib, json, re, struct
from pathlib import Path
import numpy as np
import trimesh

PACK = re.compile(r"ABAssetPack\.load\('data:application/octet-stream;base64,([A-Za-z0-9+/=]+)'\)")
TARGET_HEIGHT={'a1':1.78,'b1':1.65}
SKIN={'a1':[.64,.43,.34,1.0],'b1':[.71,.48,.39,1.0]}

def read_embedded_pack(html:Path):
    match=PACK.search(html.read_text(encoding='utf-8'))
    if not match:raise ValueError('No embedded ABAssetPack data found')
    payload=gzip.decompress(base64.b64decode(match.group(1),validate=True))
    if payload[:4]!=b'ABP2':raise ValueError('Unexpected asset signature')
    size=int.from_bytes(payload[4:8], 'little')
    doc=json.loads(payload[8:8+size])
    if doc.get('schema')!='AB.offline-assets.2':raise ValueError('Unexpected schema')
    return doc

def align4(n):return (n+3)&~3

def build_glb(name, p, f, color, out):
    # Source has explicit indexed face topology. Keep original winding and vertex identity.
    mesh=trimesh.Trimesh(vertices=p,faces=f,process=False,validate=False)
    normals=np.asarray(mesh.vertex_normals,dtype='<f4')
    if not np.isfinite(normals).all():raise ValueError('Nonfinite normal')
    pos=np.asarray(p,dtype='<f4').tobytes()
    nor=normals.tobytes()
    inds=np.asarray(f.reshape(-1),dtype='<u4').tobytes()
    col=np.asarray(color,dtype=np.uint8).tobytes()
    data=bytearray()
    views=[]
    for chunk,target in [(inds,34963),(pos,34962),(nor,34962),(col,34962)]:
        off=align4(len(data));data.extend(b'\0'*(off-len(data)))
        views.append({'buffer':0,'byteOffset':off,'byteLength':len(chunk),'target':target})
        data.extend(chunk)
    mins=p.min(axis=0).tolist();maxs=p.max(axis=0).tolist()
    accessors=[
        {'bufferView':0,'componentType':5125,'count':len(inds)//4,'type':'SCALAR'},
        {'bufferView':1,'componentType':5126,'count':len(p),'type':'VEC3','min':mins,'max':maxs},
        {'bufferView':2,'componentType':5126,'count':len(p),'type':'VEC3'},
        {'bufferView':3,'componentType':5121,'count':len(p),'type':'VEC3','normalized':True},
    ]
    doc={
        'asset':{'version':'2.0','generator':'AB authentic external rest mesh export 2026-11-14'},
        'scene':0,'scenes':[{'nodes':[0]}],
        'nodes':[{'name':name+'_OriginalABSkin','mesh':0}],
        'meshes':[{'name':name+'_ExteriorSkin','primitives':[{'attributes':{'POSITION':1,'NORMAL':2,'COLOR_0':3},'indices':0,'material':0,'mode':4}]}],
        'materials':[{'name':'AB rest-surface neutral skin PBR (approximate)','doubleSided':True,
             'pbrMetallicRoughness':{'baseColorFactor':SKIN[name.lower()],'metallicFactor':0.0,'roughnessFactor':0.81}}],
        'buffers':[{'byteLength':align4(len(data))}],
        'bufferViews':views,'accessors':accessors,
        'extras':{'source':'AB_CUTANEOUS_B64 original CC0 retopology, not current posed runtime snapshot',
                  'limitations':'External skin only; no eyes/hair/internal-specialist meshes, native rig or deformers included'}
    }
    js=json.dumps(doc,separators=(',',':')).encode();jlen=align4(len(js));blen=align4(len(data))
    outbytes=bytearray(12+8+jlen+8+blen)
    struct.pack_into('<III',outbytes,0,0x46546C67,2,len(outbytes))
    struct.pack_into('<II',outbytes,12,jlen,0x4E4F534A)
    outbytes[20:20+jlen]=js+b' '*(jlen-len(js))
    offset=20+jlen
    struct.pack_into('<II',outbytes,offset,blen,0x004E4942)
    outbytes[offset+8:offset+8+len(data)]=data
    out.write_bytes(outbytes)
    # Verify our result reopens independently.
    loaded=trimesh.load(out,force='scene')
    if not loaded.geometry:raise RuntimeError('Generated GLB could not be reopened')
    return {'bytes':len(outbytes),'sha256':hashlib.sha256(outbytes).hexdigest(),
            'vertices':len(p),'triangles':len(f),'boundsM':[mins,maxs],
            'watertightOriginal':bool(mesh.is_watertight),
            'windingConsistentOriginal':bool(mesh.is_winding_consistent)}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('source',type=Path)
    parser.add_argument('--out',type=Path,default=Path('native_glb'))
    args=parser.parse_args()
    root=read_embedded_pack(args.source)
    assets=root['assets']['AB_CUTANEOUS_B64']['models']
    args.out.mkdir(parents=True,exist_ok=True)
    result={'source':str(args.source),'sourceSha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),
            'models':{},'status':'Rest-pose external-skin export complete; live rig/pose and visual acceptance pending'}
    for key in ('a1','b1'):
        asset=assets[key]
        p=np.frombuffer(base64.b64decode(asset['positions']),dtype='<f4').copy().reshape(-1,3)
        faces=np.frombuffer(base64.b64decode(asset['indices']),dtype='<u4').copy().reshape(-1,3)
        col=np.frombuffer(base64.b64decode(asset['color']),dtype=np.uint8).copy().reshape(-1,3)
        if not (len(p)==len(col) and faces.max()<len(p) and np.isfinite(p).all()):raise ValueError('Invalid geometry '+key)
        native_height=float(np.ptp(p[:,1]));factor=TARGET_HEIGHT[key]/native_height
        p*=factor
        minY=float(p[:,1].min());p[:,1]-=minY
        for axis in (0,2):p[:,axis]-=(p[:,axis].min()+p[:,axis].max())*.5
        target=args.out/(key.upper()+'_AB_NativeExterior_Rest.glb')
        stats=build_glb(key,p,faces,col,target)
        result['models'][key.upper()]={'filename':target.name,'sourceNativeHeight':native_height,
               'heightMeters':TARGET_HEIGHT[key],'nativeToMeters':factor,**stats}
        print(key.upper(),stats)
    (args.out/'manifest.json').write_text(json.dumps(result,indent=2))
    print('Finished:',args.out)
if __name__=='__main__':main()

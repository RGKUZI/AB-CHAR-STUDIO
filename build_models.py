"""Generate two static GLB character prototypes for the browser studio."""
import trimesh
import numpy as np
from pathlib import Path
OUT=Path(__file__).resolve().parent/"assets"
OUT.mkdir(exist_ok=True)
def ball(scene,name,center,scale,color):
    m=trimesh.creation.icosphere(subdivisions=2,radius=1)
    m.apply_scale(scale);m.apply_translation(center)
    m.visual.vertex_colors=np.tile(np.array(color,dtype=np.uint8),(len(m.vertices),1))
    scene.add_geometry(m,geom_name=name)
def link(scene,name,a,b,r0,r1,color):
    a=np.array(a);b=np.array(b)
    m=trimesh.creation.cylinder(radius=(r0+r1)/2,height=np.linalg.norm(b-a),sections=18)
    m.apply_transform(trimesh.geometry.align_vectors([0,0,1],b-a))
    m.apply_translation((a+b)/2)
    m.visual.vertex_colors=np.tile(np.array(color,dtype=np.uint8),(len(m.vertices),1))
    scene.add_geometry(m,geom_name=name)
def make(which):
    female=which=="B1";k=1.65/1.78 if female else 1
    scene=trimesh.Scene()
    skin=[177,116,88,255] if not female else [190,132,107,255]
    suit=[44,46,52,255] if not female else [115,100,101,255]
    hair=[33,23,20,255] if not female else [58,35,28,255]
    eye=[242,228,212,255];iris=[55,35,26,255];lip=[156,84,80,255]
    def b(n,p,s,c):ball(scene,n,np.array(p)*k,np.array(s)*k,c)
    def l(n,a,c,r,rr,col):link(scene,n,np.array(a)*k,np.array(c)*k,r*k,rr*k,col)
    b('body_torso',(0,0,1.20),(.172 if female else .190,.105,.318),suit)
    b('pelvis',(0,0,.92),(.17,.11,.135),suit)
    b('neck',(0,.01,1.515),(.054,.052,.090),skin)
    b('head',(0,0,1.645),(.092,.086,.125),skin)
    b('nose',(0,-.090,1.615),(.022,.029,.042),skin)
    b('upper_lip',(0,-.09,1.57),(.039,.008,.010),lip)
    b('lower_lip',(0,-.09,1.557),(.038,.009,.009),lip)
    b('hair_cap',(0,.022,1.737),(.100,.092,.064),hair)
    for s,lr in [(-1,'R'),(1,'L')]:
        b('eye_white_'+lr,(s*.037,-.079,1.661),(.026,.011,.014),eye)
        b('iris_'+lr,(s*.037,-.09,1.661),(.011,.004,.011),iris)
        b('brow_'+lr,(s*.038,-.079,1.693),(.032,.008,.007),hair)
        b('ear_'+lr,(s*.093,.008,1.632),(.017,.021,.033),skin)
        b('deltoid_'+lr,(s*.224,0,1.387),(.071,.077,.089),skin)
        l('upper_arm_'+lr,(s*.25,0,1.38),(s*.28,0,1.165),.065,.046,skin)
        b('elbow_'+lr,(s*.28,0,1.16),(.047,.047,.05),skin)
        l('forearm_'+lr,(s*.28,0,1.15),(s*.305,-.016,.95),.046,.032,skin)
        b('hand_'+lr,(s*.308,-.025,.899),(.036,.024,.072),skin)
        for i in range(4):
            x=s*(.283+.016*i)
            l('finger_'+lr+str(i),(x,-.032,.857),(x,-.043,.779+abs(i-1.5)*.006),.008,.006,skin)
        l('thumb_'+lr,(s*.29,-.045,.916),(s*.27,-.061,.855),.012,.008,skin)
        b('upper_thigh_'+lr,(s*.125,0,.77),(.087,.086,.19),skin)
        b(('brief_' if female else 'short_')+lr,(s*.122,0,.84 if female else .81),(.095,.100,.098) if female else (.096,.097,.143),suit)
        l('leg_thigh_'+lr,(s*.126,0,.74),(s*.14,0,.52),.077,.060,skin)
        b('knee_'+lr,(s*.14,0,.505),(.06,.06,.072),skin)
        l('calf_'+lr,(s*.14,0,.48),(s*.14,.005,.12),.060,.041,skin)
        b('foot_'+lr,(s*.14,-.075,.071),(.061,.138,.054),skin)
        for i in range(5):
            b('toe_'+lr+str(i),(s*.14+(i-2)*.022,-.200,.038),(.012,.030,.017),skin)
    rng=np.random.default_rng(16 if female else 7)
    for i in range(24 if female else 36):
        angle=2*np.pi*i/(24 if female else 36)
        x=.087*np.cos(angle);y=.066*np.sin(angle)+.013
        if female:
            height=rng.uniform(1.32,1.46)
            l('hair_strand_'+str(i),(x,y,1.75),(x*1.2,y+.03,height),.016,.011,hair)
            b('hair_tip_'+str(i),(x*1.2,y+.03,height),(.018,.018,.035),hair)
        else:
            b('hair_curl_'+str(i),(x,y,1.762+rng.uniform(-.015,.01)),(.025,.026,.026),hair)
    (OUT/(which+'_Nomad_Static.glb')).write_bytes(scene.export(file_type='glb'))
if __name__=='__main__':
    make('A1');make('B1')
    print('Created A1 and B1 static GLB prototypes')

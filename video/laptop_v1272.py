"""Darkline V12.7.2: true mesh-based laptop, VTK PBR studio rendering.
No external assets, no network, no TTS. Full viewport is projected onto display.
The phone, captions, robot and original audio are retained by the compositor.
"""
import math, os, time
from collections import defaultdict
import cv2
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

# mm. Generic 14-inch 16:10 notebook, no real brand or logo.
WIDTH=321.; DEPTH=221.; LID_H=205.; TILT=math.radians(13.)
# Local lid coordinates x, height, thickness; front faces toward the viewer.
LID=np.array([[1,0,0],[0,math.sin(TILT),-math.cos(TILT)],[0,math.cos(TILT),math.sin(TILT)]])
HINGE=np.array([0,99,13.]); SCREEN_W=305.; SCREEN_H=SCREEN_W/1.6; SCREEN_Y=105.; SCREEN_Z=3.0

# A rounded cuboid is constructed from six subdivided faces, with analytical
# bevel normals. Face vertices share smooth normals across corners.
def rounded_box(size,rad,center=(0,0,0),transform=None):
    half=np.asarray(size,dtype=float)*.5; core=np.maximum(half-rad,0.)
    pts=[]; norms=[]; polys=[]
    for ax in range(3):
        u,v=(ax+1)%3,(ax+2)%3
        def coords(k):
            c=core[k]; h=half[k]
            return np.unique(np.r_[np.linspace(-h,-c,5),[-c,c],np.linspace(c,h,5)])
        uu,vv=coords(u),coords(v)
        for side in (-1,1):
            start=len(pts)
            for i,a in enumerate(uu):
                for j,b in enumerate(vv):
                    q=np.zeros(3);q[ax]=side*half[ax];q[u]=a;q[v]=b
                    cl=np.clip(q,-core,core);n=q-cl;n=n/max(1e-12,np.linalg.norm(n));p=cl+rad*n+center
                    if transform is not None:p,n=transform(p,n)
                    pts.append(p);norms.append(n)
            for i in range(len(uu)-1):
                for j in range(len(vv)-1):
                    p=start+i*len(vv)+j
                    f=[p,p+len(vv),p+len(vv)+1,p+1]
                    if side<0:f=f[::-1]
                    polys.append(f)
    points=vtk.vtkPoints();points.SetData(numpy_to_vtk(np.asarray(pts,np.float32),deep=True));a=vtk.vtkCellArray()
    for f in polys:a.InsertNextCell(4);[a.InsertCellPoint(x) for x in f]
    mesh=vtk.vtkPolyData();mesh.SetPoints(points);mesh.SetPolys(a)
    n=numpy_to_vtk(np.asarray(norms,np.float32),deep=True);n.SetName('Normals');mesh.GetPointData().SetNormals(n)
    return mesh

def lid_transform(p,n):return LID@p+HINGE,LID@n

def studio_texture():
    # Procedural HDR-ish studio environment: rectangular large light sources,
    # dark lower hemisphere, broad neutral gradients and small blue rim light.
    w,h=512,256;yy,xx=np.mgrid[0:h,0:w];u=xx/w;v=yy/h
    base=.10+.22*np.exp(-((v-.30)/.26)**2)
    env=np.repeat(base[:,:,None],3,axis=2)
    for cx,cy,sx,sy,amp,col in [(.22,.31,.095,.15,1.8,[1,.96,.91]),(.69,.34,.075,.22,1.3,[.75,.85,1]),(.94,.49,.055,.18,.9,[1,.98,.94]),(.48,.13,.20,.085,1.2,[1,1,1])]:
        z=np.exp(-((u-cx)/sx)**8-((v-cy)/sy)**8)*amp;env+=z[:,:,None]*np.array(col)
    # VTK environment expects an unsigned-byte sRGB texture with interpolation.
    env=np.clip(env/(1+env*.75),0,1)**(1/2.2);arr=(env*255).astype(np.uint8)
    image=vtk.vtkImageData();image.SetDimensions(w,h,1);sc=numpy_to_vtk(np.ascontiguousarray(arr[::-1]).reshape(-1,3),deep=True,array_type=vtk.VTK_UNSIGNED_CHAR);image.GetPointData().SetScalars(sc)
    tex=vtk.vtkTexture();tex.SetInputData(image);tex.InterpolateOn();tex.MipmapOn();tex.UseSRGBColorSpaceOn();return tex

class Laptop:
    def __init__(self,width=1350,height=1250):
        self.width,self.height=width,height;self.groups=defaultdict(list);self.actors=[]
        r=self.r=vtk.vtkRenderer();w=self.win=vtk.vtkRenderWindow();w.SetOffScreenRendering(1);w.SetSize(width,height);w.SetAlphaBitPlanes(1);w.SetMultiSamples(0);w.AddRenderer(r);r.SetBackground(0,0,0);r.SetBackgroundAlpha(0)
        r.UseImageBasedLightingOn();self.env=studio_texture();r.SetEnvironmentTexture(self.env,False);r.AutomaticLightCreationOff()
        # Broad environment lights plus restrained rim and key. PBR BRDF is VTK's.
        for pos,color,intensity in [((-320,-280,530),(1,.96,.91),1.6),((400,-130,330),(.78,.87,1),.85),((100,450,400),(1,.97,.94),1.05)]:
            l=vtk.vtkLight();l.SetLightTypeToSceneLight();l.SetPosition(*pos);l.SetFocalPoint(0,0,80);l.SetColor(*color);l.SetIntensity(intensity);r.AddLight(l)
        self.build()
        # material name: sRGB appearance, metallic, roughness
        materials={'base':((.39,.41,.45),.84,.40),'edge':((.48,.50,.53),.9,.32),'lid':((.30,.32,.36),.79,.31),'black':((.021,.025,.033),.08,.44),'glass':((.013,.018,.024),.12,.18),'keys':((.016,.019,.025),.0,.52),'pad':((.32,.34,.38),.52,.48),'rubber':((.017,.020,.023),0,.8),'lens':((.025,.06,.10),.3,.16),'legend':((.72,.75,.80),0,.7)}
        for key,meshes in self.groups.items():
            app=vtk.vtkAppendPolyData();[app.AddInputData(m) for m in meshes];app.Update();mp=vtk.vtkPolyDataMapper();mp.SetInputConnection(app.GetOutputPort());a=vtk.vtkActor();a.SetMapper(mp);p=a.GetProperty();p.SetInterpolationToPBR();col,metal,rough=materials[key];p.SetColor(*col);p.SetMetallic(metal);p.SetRoughness(rough);r.AddActor(a);self.actors.append((a,app,mp))
        self.cam=r.GetActiveCamera();self.cam.SetViewUp(0,0,1);self.cam.SetViewAngle(13.65);self.cam.SetClippingRange(5,4000)
        self.window=vtk.vtkWindowToImageFilter();self.window.SetInput(w);self.window.SetInputBufferTypeToRGBA();self.window.ReadFrontBufferOff();self.window.ShouldRerenderOff()
    def box(self,mat,size,rad,center,tf=None):self.groups[mat].append(rounded_box(size,rad,center,tf))
    def build(self):
        # Separate milled lower shell, chamfer, upper palm rest and recessed keyboard well.
        self.box('base',(WIDTH,DEPTH,10),3.7,(0,0,5.8));self.box('edge',(WIDTH-.6,DEPTH-.6,2.4),1.15,(0,0,10.5));self.box('base',(WIDTH-1.6,DEPTH-1.6,1.8),.88,(0,0,12.0));self.box('black',(282,105,1.3),.60,(0,36,13.0))
        # Hinge integrated into the rear wall, under the black display chin.
        self.box('black',(284,12,10),4,(0,98,12));self.box('lid',(270,8,7),3,(0,98,16));
        # Display's closed back, machined bezel, front glass and actual screen plane.
        self.box('lid',(WIDTH,LID_H,5.1),2.5,(0,LID_H/2,-.25),lid_transform)
        self.box('black',(WIDTH-2,LID_H-2,1.5),.72,(0,LID_H/2,2.5),lid_transform)
        self.box('glass',(SCREEN_W+.7,SCREEN_H+.7,.35),.17,(0,SCREEN_Y,3.0),lid_transform)
        # Webcam and light dot in top bezel, outside real content.
        self.box('black',(12,3,.4),.18,(0,200.5,3.29),lid_transform);self.box('lens',(2.5,2.5,.4),.19,(0,200.5,3.5),lid_transform);self.box('legend',(1.0,1.0,.3),.14,(4,200.5,3.5),lid_transform)
        # Keyboard rows with proper physical pitch and individually beveled keycaps.
        rows=[['esc','F1','F2','F3','F4','F5','F6','F7','F8','F9','F10','F11','F12','power'],list('1234567890')+['-','=','back'],['tab']+list('QWERTYUIOP')+['[',']','\\'],['caps']+list('ASDFGHJKL')+[';',"'",'enter'],['shift']+list('ZXCVBNM')+[',','.','/','shift'],['fn','ctrl','alt','cmd','space','cmd','alt','left','up','right']]
        for i,row in enumerate(rows):
            y=81-i*17.4;kh=12 if i==0 else 15.1
            wt=[5.0 if k=='space' else 1.65 if k in ('tab','caps','enter','back') else 2.05 if k=='shift' else 1 for k in row];total=sum(wt);x=-136.
            for k,weight in zip(row,wt):
                kw=(272-(len(row)-1)*2.1)*weight/total;cx=x+kw/2
                self.box('keys',(kw,kh,2.1),.85,(cx,y,14.2))
                # Small low-profile glyph strokes, physically sitting on the key top.
                if k not in ('space',):
                    if len(k)==1:
                        # Make readable legends from vector font; merge into one actor.
                        txt=vtk.vtkVectorText();txt.SetText(k.upper());txt.Update();p=txt.GetOutput();bounds=p.GetBounds();scale=2.8/max(.1,bounds[3]-bounds[2]);tr=vtk.vtkTransform();tr.PostMultiply();tr.Translate(-(bounds[0]+bounds[1])/2,-(bounds[2]+bounds[3])/2,0);tr.Scale(scale,scale,1);tr.Translate(cx,y,15.28);f=vtk.vtkTransformPolyDataFilter();f.SetTransform(tr);f.SetInputData(p);f.Update();m=vtk.vtkPolyData();m.DeepCopy(f.GetOutput());self.groups['legend'].append(m)
                    else:self.box('legend',(min(kw*.40,5),.52,.06),.028,(cx,y+1.3,15.29))
                x+=kw+2.1
        # Precision touchpad, recessed dark outline, palm rest, speakers and ports.
        self.box('black',(122,77,.55),.26,(0,-58,13.0));self.box('pad',(120.4,75.4,.58),.28,(0,-58,13.1))
        for sign in (-1,1):
            for i in range(3):
                for j in range(24):self.box('black',(1.0,1.0,.16),.075,(sign*(146+i*2.7),78-j*3.3,13.02))
            for y in (-40,-11,19):self.box('black',(.35,11,3.5),.16,(sign*(WIDTH/2-.17),y,6.7))
        self.box('rubber',(50,6,1.2),.55,(0,-DEPTH/2+.5,1.0))
    def render(self,t,opening=False):
        # Mild real orbit. Camera remains aimed above the keyboard so text stays large.
        yaw=.09+.055*math.sin(t*1.6);dist=1450.;pos=(math.sin(yaw)*dist,-math.cos(yaw)*dist,450+15*math.cos(t*1.4))
        self.cam.SetPosition(*pos);self.cam.SetFocalPoint(0,15,101);self.win.Render();self.window.Modified();self.window.Update()
        out=self.window.GetOutput();a=vtk_to_numpy(out.GetPointData().GetScalars()).reshape(self.height,self.width,4)[::-1].copy()
        # Map every browser corner to true display surface using the same camera.
        q=[]
        for x,y in [(-SCREEN_W/2,SCREEN_Y+SCREEN_H/2),(SCREEN_W/2,SCREEN_Y+SCREEN_H/2),(SCREEN_W/2,SCREEN_Y-SCREEN_H/2),(-SCREEN_W/2,SCREEN_Y-SCREEN_H/2)]:
            p=LID@np.array([x,y,3.23])+HINGE;self.r.SetWorldPoint(*p,1);self.r.WorldToDisplay();X,Y,_=self.r.GetDisplayPoint();q.append([X,self.height-1-Y])
        return a,np.asarray(q,np.float32)

if __name__=='__main__':
    from pathlib import Path
    l=Laptop();t=time.monotonic();a,q=l.render(0);print('render',time.monotonic()-t,'q',q,'alpha',a[:,:,3].min(),a[:,:,3].max(),flush=True)
    cv2.imwrite('mesh-test.png',cv2.cvtColor(a,cv2.COLOR_RGBA2BGRA));t=time.monotonic();l.render(.5);print('second',time.monotonic()-t,flush=True)

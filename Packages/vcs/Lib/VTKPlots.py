import animate_helper
import warnings
import vtk
import vcs
import vcs2vtk
import numpy
from vtk.util import numpy_support as VN
import meshfill,boxfill,isofill,isoline
import os, traceback
import cdms2
import DV3D
import MV2
   
def smooth(x,beta,window_len=11):
   """ kaiser window smoothing """
   # extending the data at beginning and at the end
   # to apply the window at the borders
   s = numpy.r_[x[window_len-1:0:-1],x,x[-1:-window_len:-1]]
   w = numpy.kaiser(window_len,beta)
   y = numpy.convolve(w/w.sum(),s,mode='valid')
   return y[(window_len/2):-(window_len/2)]

class VCSInteractorStyle(vtk.vtkInteractorStyleUser):
    
  def __init__(self,parent):
      self.AddObserver("LeftButtonPressEvent", parent.leftButtonPressEvent )
      self.AddObserver("LeftButtonReleaseEvent", parent.leftButtonReleaseEvent )
      self.AddObserver( "ModifiedEvent", parent.configureEvent )
      self.AddObserver( "ConfigureEvent", parent.configureEvent )
      
class VTKVCSBackend(object):
  def __init__(self,canvas,renWin=None, debug=False,bg=None):
    self._lastSize = None
    self.canvas = canvas
    self.renWin = renWin
    self.debug = debug
    self.bg = bg
    self.type = "vtk"
    self.plotApps = {}
    self.plotRenderers = set()
    self.renderer = None
    self._plot_keywords = ['renderer',]
    self.numberOfPlotCalls = 0 
    if renWin is not None:
      self.renWin = renWin
      if renWin.GetInteractor() is None and self.bg is False:
        self.createDefaultInteractor()
        
#   def applicationFocusChanged(self):
#       for plotApp in self.plotApps.values():
#           if hasattr(plotApp, 'refresh'): plotApp.refresh()

  def setAnimationStepper( self, stepper ):
      for plot in self.plotApps.values():
        plot.setAnimationStepper( stepper )
        
  def interact(self,*args,**kargs):
      warnings.warn("Press 'Q' to exit interactive mode and continue script execution")
      interactor = self.renWin.GetInteractor()
      istyle = interactor.GetInteractorStyle()     
      interactor.Start()

  def leftButtonPressEvent(self,obj,event):
    xy = self.renWin.GetInteractor().GetEventPosition()
    sz = self.renWin.GetSize()
    x = float(xy[0])/sz[0]
    y = float(xy[1])/sz[1]
    st = ""
    for dnm in self.canvas.display_names:
      d=vcs.elements["display"][dnm]
      if d.array[0] is None:
        continue
      t=vcs.elements["template"][d.template]
      gm = vcs.elements[d.g_type][d.g_name]
      if t.data.x1<=x<=t.data.x2 and t.data.y1<=y<=t.data.y2:
        ## Ok we clicked within template
        if numpy.allclose(gm.datawc_x1,1.e20):
          x1 = d.array[0].getAxis(-1)[0]
        else:
          x1 = gm.datawc_x1
        if numpy.allclose(gm.datawc_x2,1.e20):
          x2 = d.array[0].getAxis(-1)[-1]
        else:
          x2 = gm.datawc_x2
        if numpy.allclose(gm.datawc_y1,1.e20):
          y1 = d.array[0].getAxis(-2)[0]
        else:
          y1 = gm.datawc_y1
        if numpy.allclose(gm.datawc_y2,1.e20):
          y2 = d.array[0].getAxis(-2)[-1]
        else:
          y2 = gm.datawc_y2

        X = (x-t.data.x1)/(t.data.x2-t.data.x1)*(x2-x1)+x1
        Y = (y-t.data.y1)/(t.data.y2-t.data.y1)*(y2-y1)+y1
        # Ok we now have the X/Y values we need to figure out the indices
        try:
            I = d.array[0].getAxis(-1).mapInterval((X,X,'cob'))[0]
            try:
                J = d.array[0].getAxis(-2).mapInterval((Y,Y,'cob'))[0]
                # Values at that point
                V = d.array[0][...,J,I]
            except:
                V = d.array[0][...,I]
            if isinstance(V,numpy.ndarray):
              V=V.flat[0]
            try:
                st+="Var: %s\nX[%i] = %g\nY[%i] = %g\nValue: %g" % (d.array[0].id,I,X,J,Y,V)
            except:
                st+="Var: %s\nX = %g\nY[%i] = %g\nValue: %g" % (d.array[0].id,X,I,Y,V)
        except:
            st+="Var: %s\nX=%g\nY=%g\nValue = N/A" % (d.array[0].id,X,Y)
    ren = vtk.vtkRenderer()
    ren.SetBackground(.96,.96,.86)
    ren.SetViewport(x,y,min(x+.2,1.),min(y+.2,1))
    ren.SetLayer(self.renWin.GetNumberOfLayers()-1)
    a=vtk.vtkTextActor()
    a.SetInput(st)
    p=a.GetProperty()
    p.SetColor(0,0,0)
    bb = [0,0,0,0]
    a.GetBoundingBox(ren,bb)
    ps=vtk.vtkPlaneSource()
    ps.SetCenter(bb[0],bb[2],0.)
    ps.SetPoint1(bb[1],bb[2],0.)
    ps.SetPoint2(bb[0],bb[3],0.)
    ps.Update()
    m2d=vtk.vtkPolyDataMapper2D()
    m2d.SetInputConnection(ps.GetOutputPort())
    a2d=vtk.vtkActor2D()
    a2d.SetMapper(m2d)
    a2d.GetProperty().SetColor(.93,.91,.67)
    ren.AddActor(a2d)
    ren.AddActor(a)
    ren.ResetCamera()
    self.clickRenderer= ren
    self.renWin.AddRenderer(ren)
    self.renWin.Render()
      
  def leftButtonReleaseEvent(self,obj,event):
    self.clickRenderer.RemoveAllViewProps()
    self.clickRenderer.Render()
    self.renWin.RemoveRenderer(self.clickRenderer)
    self.renWin.Render()

  def configureEvent(self,obj,ev):
    sz = self.renWin.GetSize()
    if self._lastSize == sz: # or (self._lastSize is None and hasattr(self,"fromVistrails")):
      # We really only care about resize event
      # this is mainly to avoid segfault vwith Vistraisl which does
      # not catch configure Events but only modifiedEvents....
      return
    self._lastSize = sz
    plots_args = []
    key_args =[]
    for dnm in self.canvas.display_names:
      d=vcs.elements["display"][dnm]
      parg = []
      for a in d.array:
        if a is not None:
          parg.append(a)
      parg.append(d._template_origin)
      parg.append(d.g_type)
      parg.append(d.g_name)
      plots_args.append(parg)
      if d.ratio is not None:
          key_args.append({"ratio":d.ratio})
      else:
          key_args.append({})
    self.canvas.clear()
    for i, pargs in enumerate(plots_args):
      self.canvas.plot(*pargs,**key_args[i])

  def clear(self):
    if self.renWin is None: #Nothing to clear
          return
    renderers = self.renWin.GetRenderers()
#    plot_renderers = [ id(g.plot.renderer) for g in self.plotApps.values() ]
#    print " ------------------------------------ ------------------------------------  CLEAR: %s  ------------------------------------ ------------------------------------ " % str( plot_renderers )
    renderers.InitTraversal()
    ren = renderers.GetNextItem()
    while ren is not None:
        if not ren in self.plotRenderers:
            ren.RemoveAllViewProps()
              #ren.Clear()
            if not ren.GetLayer()==0:
              self.renWin.RemoveRenderer(ren)
        ren = renderers.GetNextItem()
    #self.renWin.Render()
    self.numberOfPlotCalls = 0 

  def createDefaultInteractor( self, ren=None ):
    defaultInteractor = self.renWin.GetInteractor()
    if defaultInteractor is None:
      #defaultInteractor = vtk.vtkGenericRenderWindowInteractor()
      defaultInteractor = vtk.vtkRenderWindowInteractor()
    self.vcsInteractorStyle = VCSInteractorStyle(self)
    if ren: self.vcsInteractorStyle.SetCurrentRenderer( ren )
    defaultInteractor.SetInteractorStyle( self.vcsInteractorStyle )
    defaultInteractor.SetRenderWindow(self.renWin)
    self.vcsInteractorStyle.On()

  def createRenWin(self,*args,**kargs):   
    if self.renWin is None:
      # Create the usual rendering stuff.
      self.renWin = vtk.vtkRenderWindow()
      self.renWin.SetWindowName("VCS Canvas %i" % self.canvas._canvas_id)
      self.renWin.SetAlphaBitPlanes(1)
      ## turning off antialiasing by default
      ## mostly so that pngs are same accross platforms
      self.renWin.SetMultiSamples(0)
      self.renderer = vtk.vtkRenderer()
      r,g,b = self.canvas.backgroundcolor
      self.renderer.SetBackground(r/255.,g/255.,b/255.)
      if self.bg is False:
          self.createDefaultInteractor(self.renderer) 
      self.renWin.AddRenderer(self.renderer)
      return True
    else:
      return False
      
  def update(self, *args, **kargs):
    if self.renWin is not None:
      #self.renWin.Render()
      pass

  def canvasinfo(self):
    if self.renWin is None:
      mapstate = False
      height = self.canvas.bgX
      width = self.canvas.bgY
      depth = None
      x=0
      y=0
    else:
      try: #mac but not linux
        mapstate = self.renWin.GetWindowCreated()
      except:
        mapstate = True
      width, height = self.renWin.GetSize()
      depth=self.renWin.GetDepthBufferSize()
      try: #mac not linux
        x,y = self.renWin.GetPosition()
      except:
        x,y = 0,0
    info = {
        "mapstate":mapstate,
        "height":height,
        "width":width,
        "depth":depth,
        "x":x,
        "y":y,
        }
    return info

  def orientation(self,*args,**kargs):
    if self.renWin is None:
      return "landscape"
    w,h = self.renWin.GetSize()
    if w>h:
      return "landscape"
    else:
      return "portrait"

  def portrait(self,W,H,x,y,clear):
      if clear:
          self.clear()
      if self.renWin is None:
          if W!=-99:
              self.canvas.bgX = W
              self.canvas.bgY = H
          else:
              W = self.canvas.bgX
              self.canvas.bgX = self.canvas.bgY
              self.canvas.bgY = W
      else:
          self.renWin.SetSize(W,H)

  def initialSize(self):
      #screenSize = self.renWin.GetScreenSize()
      self.renWin.SetSize(self.canvas.bgX,self.canvas.bgY)

  def open(self):
    if self.createRenWin():
      self.initialSize()
    #self.renWin.Render()

  def close(self):
    if self.renWin is None:
      return
    self.renWin.Finalize()

  def geometry(self,x,y,*args):
      #screenSize = self.renWin.GetScreenSize()
      self.renWin.SetSize(x,y)

  def flush(self):
      if self.renWin is not None:
          self.renWin.Render()

  def plot(self,data1,data2,template,gtype,gname,bg,*args,**kargs):
    self.numberOfPlotCalls+=1
    if self.bg is None:
      if bg:
        self.bg= True
      else:
        self.bg= False
    created = self.createRenWin(**kargs)
    if created:
        self.initialSize()
    if self.bg:
        self.renWin.SetOffScreenRendering(True)
        self.renWin.SetSize(self.canvas.bgX,self.canvas.bgY)
    self.cell_coordinates=kargs.get( 'cell_coordinates', None )
    #self.renWin.Render()
    #screenSize = self.renWin.GetScreenSize()
    if gtype in ["boxfill","meshfill","isoline","isofill","vector"]:
      data1 = self.trimData2D(data1) # Ok get only the last 2 dims
      if gtype!="meshfill":
        data2 = self.trimData2D(data2)
    #elif vcs.isgraphicsmethod(vcs.elements[gtype][gname]):
      ## oneD
    #  data1 = self.trimData1D(data1)
    #  data2 = self.trimData1D(data2)
    if gtype == "text":
      tt,to = gname.split(":::")
      tt = vcs.elements["texttable"][tt]
      to = vcs.elements["textorientation"][to]
      gm=tt
    else:
      gm = vcs.elements[gtype][gname]
    tpl = vcs.elements["template"][template]

    if kargs.get("renderer",None) is None:
        if ( gtype in ["3d_scalar", "3d_vector"] ) and (self.renderer <> None):
            ren = self.renderer
        else:
            ren = vtk.vtkRenderer()
            r,g,b = self.canvas.backgroundcolor
            ren.SetBackground(r/255.,g/255.,b/255.)
            if not (vcs.issecondaryobject(gm) and gm.priority==0):
                self.renderer = ren
                self.renWin.AddRenderer(ren)
        #ren.SetPreserveDepthBuffer(True)
    else:
      ren = kargs["renderer"]

    if gtype in ["boxfill","meshfill","isofill","isoline"]:      
      self.plot2D(data1,data2,tpl,gm)
    elif gtype in ["3d_scalar", "3d_vector"]:
      cdms_file = kargs.get( 'cdmsfile', None )
      cdms_var = kargs.get( 'cdmsvar', None )
      if not cdms_var is None:
          raise Exception()
      if not cdms_file is None:
          gm.addPlotAttribute( 'file', cdms_file )
          gm.addPlotAttribute( 'filename', cdms_file )
          gm.addPlotAttribute( 'url', cdms_file )
      self.plot3D(data1,data2,tpl,gm,ren,**kargs)
    elif gtype in ["text"]:
      if tt.priority!=0:
        self.renWin.AddRenderer(ren)
        self.setLayer(ren,tt.priority)
        vcs2vtk.genTextActor(ren,to=to,tt=tt)
    elif gtype=="line":
      if gm.priority!=0:
        self.renWin.AddRenderer(ren)
        self.setLayer(ren,gm.priority)
        vcs2vtk.prepLine(self.renWin,ren,gm)
    elif gtype=="marker":
      if gm.priority!=0:
        self.renWin.AddRenderer(ren)
        self.setLayer(ren,gm.priority)
        vcs2vtk.prepMarker(self.renWin,ren,gm)
    elif gtype=="fillarea":
      if gm.priority!=0:
        self.renWin.AddRenderer(ren)
        self.setLayer(ren,gm.priority)
        vcs2vtk.prepFillarea(self.renWin,ren,gm)
    elif gtype=="oned":
      self.renWin.AddRenderer(ren)
      self.plot1D(data1,data2,tpl,gm,ren)
    elif gtype=="vector":
      self.plotVector(data1,data2,tpl,gm)
    else:
      raise Exception,"Graphic type: '%s' not re-implemented yet" % gtype
    if not kargs.get("donotstoredisplay",False): 
      self.renWin.Render()


  def plot1D(self,data1,data2,tmpl,gm,ren):
    self.setLayer(ren,tmpl.data.priority)
    Y = data1
    if data2 is None:
      X=Y.getAxis(0)[:]
    else:
      X=data2

    if gm.flip:
      tmp = Y
      Y = X
      X = tmp

    if gm.smooth is not None:
        Y = smooth(Y,gm.smooth)
    l = self.canvas.createline()
    Xs = X.tolist()
    Ys = Y.tolist()
    xs = []
    ys = []
    prev = None
    for i,v in enumerate(Ys):
        if v is not None and Xs[i] is not None: # Valid data
            if prev is None:
                prev=[]
                prev2 = []
            prev.append(Xs[i])
            prev2.append(v)
        else:
            if prev is not None:
                xs.append(prev)
                ys.append(prev2)
                prev = None
    if prev is not None:
        xs.append(prev)
        ys.append(prev2)
    l.x = xs
    l.y = ys 
    l.color=gm.linecolor
    if gm.linewidth>0:
        l.width = gm.linewidth
    else:
        l.priority=0
    l.type = gm.line
    l.viewport = [tmpl.data.x1,tmpl.data.x2,tmpl.data.y1,tmpl.data.y2]
    # Also need to make sure it fills the whole space
    if not numpy.allclose([gm.datawc_x1,gm.datawc_x2],1.e20):
      x1,x2 = gm.datawc_x1,gm.datawc_x2
    else:
      x1,x2 = X.min(),X.max()
    if not numpy.allclose([gm.datawc_y1,gm.datawc_y2],1.e20):
      y1,y2 = gm.datawc_y1,gm.datawc_y2
    else:
      y1,y2 = Y.min(),Y.max()
    l.worldcoordinate = [x1,x2,y1,y2]
    m=self.canvas.createmarker()
    m.type = gm.marker
    m.color = gm.markercolor
    if gm.markersize>0:
        m.size = gm.markersize
    else:
        m.priority=0
    m.x = l.x
    m.y=l.y
    m.viewport=l.viewport
    m.worldcoordinate = l.worldcoordinate
    
    if not (Y.min()>max(y1,y2) or Y.max()<min(y1,y2) or X.min()>max(x1,x2) or X.max()<min(x1,x2)):
    	if l.priority>0:
        	self.canvas.plot(l,renderer=ren,donotstoredisplay=True)
    	if m.priority>0:
        	self.canvas.plot(m,renderer=ren,donotstoredisplay=True)
    ren2 = vtk.vtkRenderer()
    self.renWin.AddRenderer(ren2)
    tmpl.plot(self.canvas,data1,gm,bg=self.bg,renderer=ren2,X=X,Y=Y)
    
    if tmpl.legend.priority>0:
        ren2 = vtk.vtkRenderer()
        self.renWin.AddRenderer(ren2)
        self.setLayer(ren2,tmpl.legend.priority)
        legd = self.canvas.createline()
        legd.x = [tmpl.legend.x1, tmpl.legend.x2]
        legd.y = [tmpl.legend.y1, tmpl.legend.y1]
        legd.color = l.color
        legd.width = l.width
        legd.type  = l.type
        t=self.canvas.createtext(To_source=tmpl.legend.textorientation,Tt_source=tmpl.legend.texttable)
        t.x=tmpl.legend.x2
        t.y=tmpl.legend.y2
        t.string=data1.id
        self.canvas.plot(t,renderer=ren2,donotstoredisplay=True)
        self.canvas.plot(legd,renderer=ren2,donotstoredisplay=True)
  
  def setLayer(self,renderer,priority):
    n = self.numberOfPlotCalls + (priority-1)*10000 
    nMax = max(self.renWin.GetNumberOfLayers(),n+1)
    self.renWin.SetNumberOfLayers(nMax)
    renderer.SetLayer(n)
    pass

  

  def plot3D(self,data1,data2,tmpl,gm,ren,**kargs):
      from DV3D.Application import DV3DApp
      requiresFileVariable = True
      if ( data1 is None ) or ( requiresFileVariable and not ( isinstance(data1, cdms2.fvariable.FileVariable ) or isinstance(data1, cdms2.tvariable.TransientVariable ) ) ):
          traceback.print_stack()
          raise Exception, "Error, must pass a cdms2 variable object as the first input to the dv3d gm ( found '%s')" % ( data1.__class__.__name__ )
      g = self.plotApps.get( gm, None )
      if g == None:
          g = DV3DApp( self.canvas, self.cell_coordinates ) 
          n_overview_points = 500000
          grid_coords = ( None, None, None, None )
          var_proc_op = None
          interface = None
          roi = None # ( 0, 0, 50, 50 )
          g.gminit( data1, data2, roi=roi, axes=gm.axes, n_overview_points=n_overview_points, n_cores=gm.NumCores, renwin=ren.GetRenderWindow(), plot_attributes=gm.getPlotAttributes(), gmname=gm.g_name, cm=gm.cfgManager, **kargs  ) #, plot_type = PlotType.List  ) 
          self.plotApps[ gm ] = g
          self.plotRenderers.add( g.plot.renderer )
      else:
          g.update( tmpl )
           
  def plotVector(self,data1,data2,tmpl,gm):
    ug,xm,xM,ym,yM,continents,wrap,geo,cellData = vcs2vtk.genGrid(data1,data2,gm)
    if cellData:
        c2p = vtk.vtkCellDataToPointData()
        c2p.SetInputData(ug)
        c2p.Update()
        #For contouring duplicate points seem to confuse it
        if ug.IsA("vtkUnstructuredGrid"):
            cln = vtk.vtkCleanUnstructuredGrid()
            cln.SetInputConnection(c2p.GetOutputPort())

    missingMapper = vcs2vtk.putMaskOnVTKGrid(data1,ug,None,cellData)

    u=numpy.ma.ravel(data1)
    v=numpy.ma.ravel(data2)
    sh = list(u.shape)
    sh.append(1)
    u = numpy.reshape(u,sh)
    v = numpy.reshape(v,sh)
    z = numpy.zeros(u.shape)
    w = numpy.concatenate((u,v),axis=1)
    w = numpy.concatenate((w,z),axis=1)
    w = VN.numpy_to_vtk(w,deep=True)
    w.SetName("vectors")
    ug.GetPointData().AddArray(w)
    ## Vector attempt
    arrow = vtk.vtkArrowSource()
    l = gm.line
    if l is None:
        l = "default"
    try:
      l = vcs.getline(l)
      lwidth = l.width[0]
      lcolor = l.color[0]
      lstyle = l.type[0]
    except:
      lstyle = "solid"
      lwidth = 1.
      lcolor = 0
    if gm.linewidth is not None:
        lwidth = gm.linewidth
    if gm.linecolor is not None:
        lcolor = gm.linecolor


    arrow.SetTipRadius(.1*lwidth)
    arrow.SetShaftRadius(.03*lwidth)
    arrow.Update()
    glyphFilter = vtk.vtkGlyph2D()
    glyphFilter.SetSourceConnection(arrow.GetOutputPort())
    glyphFilter.OrientOn()
    glyphFilter.SetVectorModeToUseVector()
    glyphFilter.SetInputArrayToProcess(1,0,0,0,"vectors")
    glyphFilter.SetScaleFactor(2.*gm.scale)
    if cellData:
        if ug.IsA("vtkUnstructuredGrid"):
            glyphFilter.SetInputConnection(cln.GetOutputPort())
        else:
            glyphFilter.SetInputConnection(c2p.GetOutputPort())
    else:
        glyphFilter.SetInputData(ug)

    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(glyphFilter.GetOutputPort())
    act = vtk.vtkActor()
    act.SetMapper(mapper)
    try:
      cmap = vcs.elements["colormap"][cmap]
    except:
      cmap = vcs.elements["colormap"][self.canvas.getcolormapname()]
    r,g,b = cmap.index[lcolor]
    act.GetProperty().SetColor(r/100.,g/100.,b/100.)
    x1,x2,y1,y2 = vcs2vtk.getRange(gm,xm,xM,ym,yM)
    act = vcs2vtk.doWrap(act,[x1,x2,y1,y2],wrap)
    ren=vtk.vtkRenderer()
    self.renWin.AddRenderer(ren)
    self.setLayer(ren,tmpl.data.priority)
    vcs2vtk.fitToViewport(act,ren,[tmpl.data.x1,tmpl.data.x2,tmpl.data.y1,tmpl.data.y2],[x1,x2,y1,y2])
    if tmpl.data.priority!=0:
        ren.AddActor(act)
    self.renderTemplate(tmpl,data1,gm)
    if self.canvas._continents is None:
      continents = False
    if continents:
        projection = vcs.elements["projection"][gm.projection]
        self.plotContinents(x1,x2,y1,y2,projection,wrap,tmpl)

  def plot2D(self,data1,data2,tmpl,gm):
    ug,xm,xM,ym,yM,continents,wrap,geo,cellData = vcs2vtk.genGrid(data1,data2,gm)
    #Now applies the actual data on each cell
    if isinstance(gm,boxfill.Gfb) and gm.boxfill_type=="log10":
        data1=numpy.ma.log10(data1)
    data = VN.numpy_to_vtk(data1.filled(0.).flat,deep=True)
    if cellData:
        ug.GetCellData().SetScalars(data)
    else:
        ug.GetPointData().SetScalars(data)
    
    try:
      cmap = vcs.elements["colormap"][cmap]
    except:
      cmap = vcs.elements["colormap"][self.canvas.getcolormapname()]

    color = getattr(gm,"missing",None)
    if color is not None:
        color = cmap.index[color]
    missingMapper = vcs2vtk.putMaskOnVTKGrid(data1,ug,color,cellData)
    lut = vtk.vtkLookupTable()
    mn,mx=vcs.minmax(data1)
    #Ok now we have grid and data let's use the mapper
    mapper = vtk.vtkPolyDataMapper()
    legend = None
    if isinstance(gm,(meshfill.Gfm,boxfill.Gfb)):
      geoFilter = vtk.vtkDataSetSurfaceFilter()
      if cellData:
          p2c = vtk.vtkPointDataToCellData()
          p2c.SetInputData(ug)
          geoFilter.SetInputConnection(p2c.GetOutputPort())
      else:
        geoFilter.SetInputData(ug)
      geoFilter.Update()

    if isinstance(gm,(isofill.Gfi,isoline.Gi,meshfill.Gfm)) or \
        (isinstance(gm,boxfill.Gfb) and gm.boxfill_type=="custom"):
      
      #Now this filter seems to create the good polydata
      sFilter = vtk.vtkDataSetSurfaceFilter()
      if cellData:
          # Sets data to point instead of just cells
          c2p = vtk.vtkCellDataToPointData()
          c2p.SetInputData(ug)
          c2p.Update()
          if self.debug:
            vcs2vtk.dump2VTK(c2p)
          #For contouring duplicate points seem to confuse it
          if ug.IsA("vtkUntructuredGrid"):
              cln = vtk.vtkCleanUnstructuredGrid()
              cln.SetInputConnection(c2p.GetOutputPort())
              if self.debug:
                vcs2vtk.dump2VTK(cln)
              sFilter.SetInputConnection(cln.GetOutputPort())
          else:
              sFilter.SetInputConnection(c2p.GetOutputPort())
      else:
          sFilter.SetInputData(ug)
      sFilter.Update()
      if self.debug:
        vcs2vtk.dump2VTK(sFilter)
      if isinstance(gm,isoline.Gi):
        cot = vtk.vtkContourFilter()
        if cellData:
          cot.SetInputData(sFilter.GetOutput())
        else:
          cot.SetInputData(ug)


      levs = gm.levels
      if (isinstance(gm,isoline.Gi) and numpy.allclose( levs[0],[0.,1.e20])) or numpy.allclose(levs,1.e20):
        levs = vcs.mkscale(mn,mx)
        Ncolors = len(levs)
        if isinstance(gm,(isofill.Gfi,meshfill.Gfm)):
          levs2 = vcs.mkscale(mn,mx)
          levs=[]
          for i in range(len(levs2)-1):
            levs.append([levs2[i],levs2[i+1]])
      else:
        if isinstance(gm.levels[0],(list,tuple)):
          if isinstance(gm,isoline.Gi):
            levs = [x[0] for x in gm.levels]
          else:
            levs = gm.levels
        else:
          levs = [] 
          levs2=gm.levels
          if numpy.allclose(levs2[0],1.e20):
            levs2[0]=-1.e20
          for i in range(len(levs2)-1):
            levs.append([levs2[i],levs2[i+1]])
          if isinstance(gm,isoline.Gi):
            levs = levs2
      Nlevs=len(levs)
      Ncolors = Nlevs
      ## Figure out colors
      if isinstance(gm,boxfill.Gfb):
        cols = gm.fillareacolors 
        if cols is None:
          cols = vcs.getcolors(levs2,split=0)
      elif isinstance(gm,(isofill.Gfi,meshfill.Gfm)):
        cols = gm.fillareacolors
        if cols==[1,]:
          cols = vcs.getcolors(levs2,split=0)
      elif isinstance(gm,isoline.Gi):
        cols = gm.linecolors

      if isinstance(gm,isoline.Gi):
        cot.SetNumberOfContours(Nlevs)
        if levs[0]==1.e20:
          levs[0]=-1.e20
        for i in range(Nlevs):
          cot.SetValue(i,levs[i])
        cot.SetValue(Nlevs,levs[-1])
        cot.Update()
        mapper.SetInputConnection(cot.GetOutputPort())
        mappers = []
      else:
        mappers = []
        LEVS = []
        INDX = []
        COLS = []
        indices = gm.fillareaindices
        if indices is None:
            indices=[1,]
        while len(indices)<len(cols):
            indices.append(indices[-1])
        for i,l in enumerate(levs):
            if i==0:
                C = [cols[i],]
                if numpy.allclose(levs[0][0],-1.e20):
                    ## ok it's an extension arrow
                    L=[mn-1.,levs[0][1]]
                else: 
                    L = levs[i]
                I = [indices[i],]
            else:
                if l[0] == L[-1] and I[-1]==indices[i]:
                    # Ok same type lets keep going
                    if numpy.allclose(l[1],1.e20):
                        L.append(mx+1.)
                    else:
                        L.append(l[1])
                    C.append(cols[i])
                else: # ok we need new contouring
                    LEVS.append(L)
                    COLS.append(C)
                    INDX.append(I)
                    C = [cols[i],]
                    L = levs[i]
                    I = [indices[i],]
        LEVS.append(L)
        COLS.append(C)
        INDX.append(I)

        
        for i,l in enumerate(LEVS):
          # Ok here we are trying to group together levels can be, a join will happen if:
          # next set of levels contnues where one left off AND pattern is identical
           
          if isinstance(gm,isofill.Gfi):
              mapper = vtk.vtkPolyDataMapper()
              lut = vtk.vtkLookupTable()
              cot = vtk.vtkBandedPolyDataContourFilter()
              cot.ClippingOn()
              cot.SetInputData(sFilter.GetOutput())
              cot.SetNumberOfContours(len(l))
              for j,v in enumerate(l):
                  cot.SetValue(j,v)
              #cot.SetScalarModeToIndex()
              cot.Update()
              mapper.SetInputConnection(cot.GetOutputPort())
              lut.SetNumberOfTableValues(len(COLS[i]))
              for j,color in enumerate(COLS[i]):
                  r,g,b = cmap.index[color]      
                  lut.SetTableValue(j,r/100.,g/100.,b/100.)
                  #print l[j],vcs.colors.rgb2str(r*2.55,g*2.55,b*2.55),l[j+1]
              mapper.SetLookupTable(lut)
              mapper.SetScalarRange(0,len(l)-1)
              mapper.SetScalarModeToUseCellData()
          else:
              for j,color in enumerate(COLS[i]):
                  mapper = vtk.vtkPolyDataMapper()
                  lut = vtk.vtkLookupTable()
                  th = vtk.vtkThreshold()
                  th.ThresholdBetween(l[j],l[j+1])
                  th.SetInputConnection(geoFilter.GetOutputPort())
                  geoFilter2 = vtk.vtkDataSetSurfaceFilter()
                  geoFilter2.SetInputConnection(th.GetOutputPort())
                  mapper.SetInputConnection(geoFilter2.GetOutputPort())
                  lut.SetNumberOfTableValues(1)
                  r,g,b = cmap.index[color]      
                  lut.SetTableValue(0,r/100.,g/100.,b/100.)
                  mapper.SetLookupTable(lut)
                  mapper.SetScalarRange(l[j],l[j+1])
                  mappers.append([mapper,])

          #png = vtk.vtkPNGReader()
          #png.SetFileName("/git/uvcdat/Packages/vcs/Share/uvcdat_texture.png")
          #T=vtk.vtkTexture()
          #T.SetInputConnection(png.GetOutputPort())
          if isinstance(gm,isofill.Gfi):
              mappers.append([mapper,])

    else: #Boxfill (non custom)/Meshfill
      if isinstance(gm,boxfill.Gfb):
        if numpy.allclose(gm.level_1,1.e20) or numpy.allclose(gm.level_2,1.e20):
          levs = vcs.mkscale(mn,mx)
          legend = vcs.mklabels(levs)
          dx = (levs[-1]-levs[0])/(gm.color_2-gm.color_1+1)
          levs = numpy.arange(levs[0],levs[-1]+dx,dx)
        else:
          if gm.boxfill_type=="log10":
              levs = vcs.mkscale(numpy.ma.log10(gm.level_1),numpy.ma.log10(gm.level_2))
          else:
              levs = vcs.mkscale(gm.level_1,gm.level_2)
          legend = vcs.mklabels(levs)
          if gm.boxfill_type=="log10":
              for k in legend.keys():
                  legend[float(numpy.ma.log10(legend[k]))] = legend[k]
                  del(legend[k])
          dx = (levs[-1]-levs[0])/(gm.color_2-gm.color_1+1)
          levs = numpy.arange(levs[0],levs[-1]+dx,dx)

        cols = range(gm.color_1,gm.color_2+1)
      else:
        if numpy.allclose(gm.levels,1.e20):
          levs = vcs.mkscale(mn,mx)
        else:
          levs = gm.levels
          if numpy.allclose(levs[0],1.e20):
            levs[0]=-1.e20
        cols = gm.fillareacolors
        if cols==[1,]:
          cols = vcs.getcolors(levs)
      Nlevs = len(levs)
      Ncolors = Nlevs-1
      #Prep mapper
      mappers=[]
      mapper = vtk.vtkPolyDataMapper()
      thr = vtk.vtkThreshold()
      thr.SetInputConnection(geoFilter.GetOutputPort())
      if not gm.ext_1 in ["y",1,True]  and not gm.ext_2 in ["y",1,True] :
          thr.ThresholdBetween(levs[0],levs[-1])
      elif gm.ext_1 in ["y",1,True]  and not gm.ext_2 in ["y",1,True] :
          thr.ThresholdByLower(levs[-1])
      elif not gm.ext_1 in ["y",1,True]  and gm.ext_2 in ["y",1,True] :
          thr.ThresholdByUpper(levs[0])
      thr.Update()
      geoFilter2 = vtk.vtkDataSetSurfaceFilter()
      geoFilter2.SetInputConnection(thr.GetOutputPort())
      if gm.ext_1 in ["y",1,True]  and gm.ext_2 in ["y",1,True] :
          mapper.SetInputConnection(geoFilter.GetOutputPort())
      else:
          mapper.SetInputConnection(geoFilter2.GetOutputPort())

    if mappers == []: # ok didn't need to have special banded contours
      mappers=[mapper,]
      ## Colortable bit
      # make sure length match
      while len(cols)<Ncolors:
        cols.append(cols[-1])
      
      lut.SetNumberOfTableValues(Ncolors)
      for i in range(Ncolors):
        r,g,b = cmap.index[cols[i]]
        lut.SetTableValue(i,r/100.,g/100.,b/100.)

      mapper.SetLookupTable(lut)
      if numpy.allclose(levs[0],-1.e20):
        lmn = mn-1.
      else:
        lmn= levs[0]
      if numpy.allclose(levs[-1],1.e20):
        lmx = mx+1.
      else:
        lmx= levs[-1]
      mapper.SetScalarRange(lmn,lmx)

    if missingMapper is not None:
        mappers.insert(0,missingMapper)

    x1,x2,y1,y2 = vcs2vtk.getRange(gm,xm,xM,ym,yM)

    if tmpl.data.priority != 0:
      # And now we need actors to actually render this thing
      for mapper in mappers:
        act = vtk.vtkActor()
        if isinstance(mapper,list):
          act.SetMapper(mapper[0])
        else:
          mapper.Update()
          act.SetMapper(mapper)
        if geo is None:
          act = vcs2vtk.doWrap(act,[x1,x2,y1,y2],wrap)
        if isinstance(mapper,list):
          #act.GetMapper().ScalarVisibilityOff()
          #act.SetTexture(mapper[1])
          pass
        # create a new renderer for this mapper (we need one for each mapper because of cmaera flips)
        ren = vtk.vtkRenderer()
        self.renWin.AddRenderer(ren)
        self.setLayer(ren,tmpl.data.priority)
        ren.AddActor(act)
        vcs2vtk.fitToViewport(act,ren,[tmpl.data.x1,tmpl.data.x2,tmpl.data.y1,tmpl.data.y2],wc=[x1,x2,y1,y2],geo=geo)

    if isinstance(gm,meshfill.Gfm):
      tmpl.plot(self.canvas,data1,gm,bg=self.bg,X=numpy.arange(xm,xM*1.1,(xM-xm)/10.),Y=numpy.arange(ym,yM*1.1,(yM-ym)/10.))
    else:
      self.renderTemplate(tmpl,data1,gm)
    if isinstance(gm,(isofill.Gfi,meshfill.Gfm,boxfill.Gfb)):
      if getattr(gm,"legend",None) is not None:
        legend = gm.legend
      if gm.ext_1 in ["y",1,True] and not numpy.allclose(levs[0],1.e20):
          if isinstance(levs,numpy.ndarray):
              levs=levs.tolist()
          levs.insert(0,-1.e20)
      if gm.ext_2 in ["y",1,True] and not numpy.allclose(levs[0],1.e20):
          if isinstance(levs,numpy.ndarray):
              levs=levs.tolist()
          levs.append(1.e20)

      self.renderColorBar(tmpl,levs,cols,legend,cmap)
    if self.canvas._continents is None:
      continents = False
    if continents:
        projection = vcs.elements["projection"][gm.projection]
        self.plotContinents(x1,x2,y1,y2,projection,wrap,tmpl)

  def plotContinents(self,x1,x2,y1,y2,projection,wrap,tmpl):
      contData = vcs2vtk.prepContinents(self.canvas._continents)
      contMapper = vtk.vtkPolyDataMapper()
      contMapper.SetInputData(contData)
      contActor = vtk.vtkActor()
      contActor.SetMapper(contMapper)
      contActor.GetProperty().SetColor(0.,0.,0.)
      contActor = vcs2vtk.doWrap(contActor,[x1,x2,y1,y2],wrap)
      if projection.type!="linear":
          contData=contActor.GetMapper().GetInput()
          cpts = contData.GetPoints()
          geo, gcpts = vcs2vtk.project(cpts,projection,[x1,x2,y1,y2])
          contData.SetPoints(gcpts)
          contMapper = vtk.vtkPolyDataMapper()
          contMapper.SetInputData(contData)
          contActor = vtk.vtkActor()
          contActor.SetMapper(contMapper)
          contActor.GetProperty().SetColor(0.,0.,0.)
      else:
          geo=None
      ren = vtk.vtkRenderer()
      self.renWin.AddRenderer(ren)
      self.setLayer(ren,tmpl.data.priority)
      vcs2vtk.fitToViewport(contActor,ren,[tmpl.data.x1,tmpl.data.x2,tmpl.data.y1,tmpl.data.y2],wc=[x1,x2,y1,y2],geo=geo)
      if tmpl.data.priority!=0:
        ren.AddActor(contActor)

  def renderTemplate(self,tmpl,data,gm):
    tmpl.plot(self.canvas,data,gm,bg=self.bg)

  def renderColorBar(self,tmpl,levels,colors,legend,cmap):
    if tmpl.legend.priority>0:
      tmpl.drawColorBar(colors,levels,x=self.canvas,legend=legend,cmap=cmap)

  def cleanupData(self,data):
      data[:] = numpy.ma.masked_invalid(data,numpy.nan)
      return data

  def trimData1D(self,data):
    if data is None:
      return None
    while len(data.shape)>1:
      data = data[0]
    return self.cleanupData(data)

  #ok now trying to figure the actual data to plot
  def trimData2D(self,data):
    if data is None:
      return None
    try:
      g=data.getGrid()
      gaxes=list(g.getAxisList())
      daxes=list(data.getAxisList())
      if daxes[len(daxes)-len(gaxes):] == gaxes:
        # Ok it is gridded and the grid axes are last
        return self.cleanupData(data(*(slice(0,1),)*(len(daxes)-len(gaxes)),squeeze=1))
      else:
        # Ok just return the last two dims
        return self.cleanupData(data(*(slice(0,1),)*(len(daxes)-2),squeeze=1))
    except Exception,err: # ok no grid info
      daxes=list(data.getAxisList())
      if cdms2.isVariable(data):
        return self.cleanupData( data(*(slice(0,1),)*(len(daxes)-2)))
      else: #numpy arrays are not callable
        op = ()
        for i in range(numpy.rank(data)-2):
          op.append(slice(0,1))
        return self.cleanupData(data[op])

  def put_png_on_canvas(self,filename,zoom=1,xOffset=0,yOffset=0,*args,**kargs):
      return self.put_img_on_canvas(filename,zoom,xOffset,yOffset,*args,**kargs)
  def put_img_on_canvas(self,filename,zoom=1,xOffset=0,yOffset=0,*args,**kargs):
    readerFactory = vtk.vtkImageReader2Factory()
    reader = readerFactory.CreateImageReader2(filename)
    reader.SetFileName(filename)
    reader.Update()
    imageData = reader.GetOutput()
    a = vtk.vtkImageActor()
    a.GetMapper().SetInputConnection(reader.GetOutputPort())
    origin = imageData.GetOrigin()
    spc = imageData.GetSpacing()
    ext = imageData.GetExtent()
    ren = vtk.vtkRenderer()
    r,g,b = self.canvas.backgroundcolor
    ren.SetBackground(r/255.0, g/255.0, b/255.0)
    cam = ren.GetActiveCamera()
    cam.ParallelProjectionOn()
    width = (ext[1]-ext[0])*spc[0]
    height = (ext[3]-ext[2])*spc[1]
    xoff = width*xOffset/zoom/200.
    yoff = height*yOffset/zoom/200.
    xc  = origin[0] + .5*(ext[0]+ext[1])*spc[0]
    yc  = origin[1] + .5*(ext[2]+ext[3])*spc[1]
    yd = (ext[3]-ext[2])*spc[1]
    d = cam.GetDistance()
    cam.SetParallelScale(.5*yd/zoom)
    cam.SetFocalPoint(xc+xoff,yc+yoff,0.)
    cam.SetPosition(xc+xoff,yc+yoff,d)
    ren.AddActor(a)
    self.renWin.AddRenderer(ren)
    self.renWin.Render()
    return

  def vectorGraphics(self, output_type, file, width=None, height=None, units=None):
    if self.renWin is None:
      raise Exception("Nothing on Canvas to dump to file")

    gl  = vtk.vtkGL2PSExporter()
    gl.SetInput(self.renWin)
    gl.SetCompress(0) # Do not compress
    gl.SetFilePrefix(".".join(file.split(".")[:-1]))
    if output_type=="svg":
        gl.SetFileFormatToSVG()
    elif output_type == "ps":
        gl.SetFileFormatToPS()
    elif output_type=="pdf":
        gl.SetFileFormatToPDF()
    else:
        raise Exception("Unknown format: %s" % output_type)
    gl.Write()

  def postscript(self, file, width=None, height=None, units=None,left=None,right=None,top=None,bottom=None):
      if right is not None:
          warnings.warn("the right_margin keyword for postscript has been deprecated in 2.0 and is being ignored")
      if left is not None:
          warnings.warn("the left_margin keyword for postscript has been deprecated in 2.0 and is being ignored")
      if top is not None:
          warnings.warn("the top_margin keyword for postscript has been deprecated in 2.0 and is being ignored")
      if bottom is not None:
          warnings.warn("the bottom_margin keyword for postscript has been deprecated in 2.0 and is being ignored")

      return self.vectorGraphics("ps", file, width, height, units)

  def pdf(self, file, width=None, height=None, units=None):
      return self.vectorGraphics("pdf", file, width, height, units)

  def svg(self, file, width=None, height=None, units=None):
      return self.vectorGraphics("svg", file, width, height, units)

  def png(self, file, width=None,height=None,units=None,draw_white_background = 0):
        
        if self.renWin is None:
          raise Exception,"Nothing to dump aborting"
            
        if not file.split('.')[-1].lower() in ['png']:
            file+='.png'

        try:
          os.remove(file)
        except:
          pass

        #if width is not None and height is not None:
        #  self.renWin.SetSize(width,height)
          #self.renWin.Render()
        imgfiltr = vtk.vtkWindowToImageFilter()
        imgfiltr.SetInput(self.renWin)
#        imgfiltr.SetMagnification(3)
        imgfiltr.SetInputBufferTypeToRGBA()
        imgfiltr.Update()
        writer = vtk.vtkPNGWriter()
        writer.SetInputConnection(imgfiltr.GetOutputPort())
        writer.SetFileName(file)
        writer.Write()

  def cgm(self,file):
        if self.renWin is None:
          raise Exception,"Nothing to dump aborting"
            
        if not file.split('.')[-1].lower() in ['cgm']:
            file+='.cgm'

        try:
          os.remove(file)
        except:
          pass

        writer = vtk.vtkIOCGM.vtkCGMWriter()
        writer.SetFileName(file)
        R = self.renWin.GetRenderers()
        r=R.GetFirstRenderer()
        A = r.GetActors()
        A.InitTraversal()
        a = A.GetNextActor()
        while a is not None:
          m = a.GetMapper()
          m.Update()
          writer.SetInputData(m.GetInput())
          writer.Write()
          a=A.GetNextActor()
  def Animate(self,*args,**kargs):
    return VTKAnimate(*args,**kargs)

  def gettextextent(self,textorientation,texttable):
      warnings.warn("Please implement gettextextent for VTK Backend")
  
  def getantialiasing(self):
    if self.renWin is None:
      return 0
    else:
      return self.renWin.GetMultiSamples()

  def setantialiasing(self,antialiasing):
    if self.renWin is None:
      warnings.warn("no RenderWindow ready, skipping setantialiasing call, please reissue at a later time")
    else:
      self.renWin.SetMultiSamples(antialiasing)

class VTKAnimate(animate_helper.AnimationController):
   pass

# class VTKAnimate(animate_helper.animate_obj):
#   def __init__(self,*args,**kargs):
#     animate_helper.animate_obj.__init__(self,*args,**kargs)
#     self._initial_blink_done = False
#   def draw2(self,frame):
#     if self.create_flg == 1:
#         self.current_frame = frame
#         kargs = {}
#         if self._initial_blink_done:
#           kargs["noblink"]=True
#         else:
#           self._initial_blink_done = True
#         self.vcs_self.backend.clear()
#         self.vcs_self.put_png_on_canvas(self.animation_files[frame],
#                 self.zoom_factor, self.vertical_factor, self.horizontal_factor,**kargs)
#         if animate_helper.hasPyQt:
#           self.signals.drew.emit()


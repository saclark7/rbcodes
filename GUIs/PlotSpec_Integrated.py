import numpy as np
from IGM import compute_EW
from IGM import rb_setline as line       
import pdb
import sys
import os
from pathlib import Path
from utils import rb_utility as rt
import matplotlib as mpl
mpl.use('Qt5Agg')
mpl.rcParams['lines.linewidth'] = .9
clr=rt.rb_set_color()
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QComboBox,QHBoxLayout,QFileDialog,
    QLineEdit, QInputDialog,QListWidget, QVBoxLayout, QListWidgetItem,QLabel,QTableWidget,QGridLayout,QMessageBox,QBoxLayout,QDesktopWidget)

from PyQt5.QtGui import QPalette, QColor
from pkg_resources import resource_filename
import pandas as pd
import matplotlib.pyplot as plt 
from astropy.convolution import convolve, Box1DKernel
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg,
    NavigationToolbar2QT as NavigationToolbar,
)
from matplotlib.figure import Figure
from GUIs import guess_abs_line_vel_gui as g
from GUIs.abstools import Absorber as A
 



HELP = '''
        MAIN GUI HELP:
        Left Widget is the absorber manager. Here you can add known absorbers, guess absorbers
        and plot or hide the transition lines. If an absorber is determined to be incorrect, removing 
        the abosrber will delete it from the manager and it will not exist in the output csv file once saving
        
        The main canvas is where all following keyboard events are tied to. If interacting with another 
        widget outside of the canvas, must reclick within the canvas to enable the keyboard events
        
        The active zabs manager (below canvas) will display what redshift is currently being used
        for identifying matching transitions. The Catalog button will automatically add this transition 
        to the absorber manager
        
        --------------Keyboard Events----------
        
        'r':   resets/clears the axes and replots the spectra
        'R':   Keeps the spectra active and will remove all lines/text from the canvas
        't':   Will restrict the ymax of the canvas to the users current mouse height
        'b':   Restricts ymin of the canvas to current mouse height
        'S':   Smoothes the spectra
        'U':   Unsmooth spectra
        'x':   Sets left x limit (xmin)
        'X':   Sets right x limit (xmax)
        ']':   Shifts canvas to the right
        '[':   Shifts canvas to the left
        'Y':   User can input their own y limits
        'H':   Help Window
        'v':   Opens Separate Vstack GUI for the user to identify detected transitions
               Vstack commands will be discussed below
        
        'j':   Designed to be used by zooming into a small region of the spectra,
               finding an absortion region, put mouse in the middle of that region.
               'j' then opens a transition list window for the user to select which
               ion they believe the abosrber is located. Once a transition is clicked,
               the active zabs will display what the redshift should be based on the 
               mouse x location
               
        'F':   Zooms out to show the full spectra.
        
        
        --------Vstack GUI Keyboard Events--------
        Upon pressing 'v' in main canvas, a separate window will pop up
        
        '>':   Shifts page right (if more than one page)
        '<':   Shifts page left 
        'w':   Will change the transition flag between detection and Non-detection
        
        
        ------Notes-------
        Upon hitting 'v', the transition list will be saved. If redoing an analysis to correct
        or check transitions, it will identify user that the transition list has already been
        analyzed for the absorber. If continuing it will overwrite the previous results
        PLEASE NOTE, it will overwrite, not update the previous results.
        
        Save: Saving will generate its own file tree for files. Can rename a folder, but
            do not rename the files otherwise they will not load. Saving can be done without 
            evaluate linelists for each absorber or with partially evaluated line lists.
            Saving will access the current working directory, but can change the filepath to any 
            desired folder.
            
            The absorber manager will be saved as a .csv and the linelists saved as a .txt
            
        Load: To load, only give the parent folder, which has contents of the .csv and .txt files
              Loading will repopulate the previously confirmed absorber redshifts, colors, and linelist 
              used and will plot the detected absorbers as identified during the VStack GUI.
               
        

        '''

class mainWindow(QtWidgets.QMainWindow):#QtWidgets.QMainWindow
    
    def __init__(self,wave,flux,error,zabs=0,parent=None):
        
        #Action identifiers and initializing storing containers
        self.zabs_list = pd.DataFrame(data=None,columns = ['Zabs','list','color'])
        self.line_list = pd.DataFrame(data=None,columns = ['Name','Wave_obs','Zabs'])
        self.zabs_line_plot = []
        self.z_list = []
        self.text = []
        self.linelist = []
        self.hide = False
        self.row = None
        self.row_remove = False
        self.identified_line_active = False
        self.identified_lines = []
        self.identified_text = []
        self.wave=wave
        self.flux=flux
        self.smoothed_spectrum=flux
        self.error=error
        self.zabs=zabs
        self.label='None' # Initializing a label
        
        #make longer color list
        clrlist=list(clr.keys())  

        self.combo_options =clrlist[1:]# ['yellow','orange','red','green','white']
        self.line_options = ['LLS','LLS Small','DLA','None']
        
        #---------------Initial page setup------------------# 
        super(mainWindow,self).__init__(parent)
        self.setWindowTitle('Absorber Idenificaation')
        
        #Main canvas widgets
        main_layout = QHBoxLayout()
        self.spectrum = Figure()
        self.ax = self.spectrum.add_subplot(111)
        self.ax.step(self.wave, self.flux, '-',lw=1,color=clr['teal'])
        self.init_xlims = [min(self.wave),max(self.wave)]
        self.canvas = FigureCanvasQTAgg(self.spectrum)
        toolbar = NavigationToolbar(self.canvas, self)
        
        #Zabs Manager Widgets
        self.abs_plot = manage_identified_absorbers(self)
        self.abs_plot.table.cellChanged.connect(self.cellchanged)
        
        self.manage_save = QPushButton("Save",self)
        self.manage_save.clicked.connect(lambda: self.saveCatalog_fn(self))
        
        self.manage_load = QPushButton("Load",self)
        self.manage_load.clicked.connect(lambda: self.LoadCatalog_fn(self))
        
        self.Identified_line_plot = QPushButton("Plot Identified Lines", self)
        self.Identified_line_plot.clicked.connect(lambda: Identified_plotter(self))
        #save layout (bottom of left panel)
        save_layout = QHBoxLayout()
        save_layout.addWidget(self.manage_save)
        save_layout.addWidget(self.manage_load)
        
        
        #left panel Main layout
        manage_layout = QVBoxLayout()
        manage_layout.addWidget(self.abs_plot.table)
        manage_layout.addLayout(save_layout)
        manage_layout.addWidget(self.Identified_line_plot)
        
        #canvas layout
        plot_layout = QtWidgets.QVBoxLayout()
        plot_layout.addWidget(toolbar,stretch=1)
        plot_layout.addWidget(self.canvas,stretch=5)
        self.plot_layout = plot_layout
        
        # active values widgets (bottom of main panel)
        self.active_zabs = QLineEdit(self)
        self.active_zabs.setText(str(self.zabs))
        self.active_zabs.textChanged[str].connect(lambda: self.zabs_changed())
        self.zabs_label = QLabel("Active Redshift",self)
        self.line_label = QLabel("Active LineList",self)
        self.combo_lines = QComboBox()
        for items in self.line_options:
            self.combo_lines.addItem(items)
        self.main_linelist = self.combo_lines.currentText()
        
        # Shows the active redshift and transition
        self.combo_color_main = QComboBox()
        for items in self.combo_options:
            self.combo_color_main.addItem(items)
        self.color = self.combo_color_main.currentText()
        color_label = QLabel('Color',self)
        
        #active values layout (bottom of canvas layout)
        active_elem_layout = QtWidgets.QFormLayout()
        active_elem_layout.addRow(self.zabs_label,self.active_zabs)
        active_elem_layout.addRow(self.line_label,self.combo_lines)
        active_elem_layout.addRow(color_label,self.combo_color_main)
        
        #Catalog to connect Guessed line to the zabs manager:
        catalog = QPushButton("Catalog",self)
        catalog.clicked.connect(lambda: self.update_manager())#Catalog(self))
        plot = QPushButton("Plot",self)
        plot.clicked.connect(lambda: Redshift_Guess(self))
        refresh = QPushButton("Refresh",self)
        refresh.clicked.connect(lambda: self.Refreshed(self))
        #Spacer is to reduce the size of Active redshift and transition
        spacer = QHBoxLayout()
        plot_cat = QVBoxLayout()
        
        spacerItem = QtWidgets.QSpacerItem(100, 20, QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum)
        spacer.addItem(spacerItem)
#         spacer.addWidget(plot)
        spacer.addLayout(active_elem_layout)
        plot_cat.addWidget(plot)
        plot_cat.addWidget(catalog)
        plot_cat.addWidget(refresh)
        spacer.addLayout(plot_cat)
#         spacer.addWidget(catalog)
        spacer.addItem(spacerItem)
        plot_layout.addLayout(spacer,stretch=1)

        
        main_layout.addLayout(manage_layout,28)
        main_layout.addLayout(plot_layout,80)

        # Create a placeholder widget to hold our toolbar and canvas.
        widget = QtWidgets.QWidget()
        widget.setLayout(main_layout)
        self.setCentralWidget(widget)
        self.show()
        #--------------------------end of layouts/widgets initialization------------#
        
        #Plot spectra
        self.ax.set_xlabel('Wavelength')
        self.ax.set_ylabel('Flux')
        xr=[min(self.wave),max(self.wave)]
        yr=[0.,np.median(flux)*2.5]
        self.ax.set_ylim(yr)
        self.ax.set_xlim(xr)
        #---------------------------------------------------
#         self.ax=ax
        self.vel=np.array([1.])
        self.lam_lim=[]
        self.lam_ylim=[]
        self.FXval=[]
        self.FYval=[]


        
        #connect
        self.setParent(parent)
        self.spectrum.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.spectrum.canvas.setFocus()
        self.cid = self.spectrum.canvas.mpl_connect('key_press_event',self.ontype)
        
        try:
            self.abs_plot.table.cellChanged.connect(self.cellchanged)
        except:
            pass
        
    def ontype(self,event):
        zabs=np.double(0.)
        # when the user hits 'r': clear the axes and plot the original spectrum
        if event.key=='r':
            self.ax.cla()
            self.ax.step(self.wave,self.flux,'-',linewidth=1,color=clr['teal'])
            self.ax.set_xlabel('Wavelength')
            self.ax.set_ylabel('Flux')
            xr=[np.min(self.wave),np.max(self.wave)]
            yr=[np.min(self.flux),np.max(self.flux)]
            self.ax.set_ylim([yr[0],yr[1]])
            self.ax.set_xlim([xr[0], xr[1]])
            self.spectrum.canvas.draw()
        #another refresh to keep the current flux values but remove the plotted lines
        elif event.key == 'R':
            del self.ax.lines[1:]
            for ii in self.text[-1]:
                ii.remove()
            self.spectrum.canvas.draw()
#         # Set top y max
        elif event.key=='t':
            xlim=self.ax.get_xlim()
            ylim=self.ax.get_ylim()
            self.ax.set_ylim([ylim[0],event.ydata])
            self.ax.set_xlim(xlim)
            self.spectrum.canvas.draw() 
#         # Set top y min
        elif event.key=='b':
            xlim=self.ax.get_xlim()
            ylim=self.ax.get_ylim()
            self.ax.set_ylim([event.ydata,ylim[1]])
            self.ax.set_xlim(xlim)
            self.spectrum.canvas.draw() 
#         # Smooth spectrum
        elif event.key=='S':
            self.vel[0] += 2
            Filter_size=np.int(self.vel[0]) 
            self.smoothed_spectrum =convolve(self.flux, Box1DKernel(Filter_size))#medfilt(flux,np.int(Filter_size))
            self.specplot()
            self.spectrum.canvas.draw()  
#         #Unsmooth Spectrum
        elif event.key=='U':
            self.vel[0] -= 2
            if self.vel[0] <= 0:
                self.vel[0]=1;
            Filter_size=np.int(self.vel[0]) 
            self.smoothed_spectrum =convolve(self.flux, Box1DKernel(Filter_size))#medfilt(flux,np.int(Filter_size))
            self.specplot()
    
        # Set X max
        elif event.key=='X':
            xlim=self.ax.get_xlim()
            ylim=self.ax.get_ylim()
            self.ax.set_xlim([xlim[0],event.xdata])
            self.ax.set_ylim(ylim)
            self.spectrum.canvas.draw() 
        # Set x min
        elif event.key=='x':
            xlim=self.ax.get_xlim()
            ylim=self.ax.get_ylim()
            self.ax.set_xlim([event.xdata,xlim[1]])
            self.ax.set_ylim(ylim)
            self.spectrum.canvas.draw() 

        # Set pan spectrum
        elif event.key==']':
            xlim=self.ax.get_xlim()
            ylim=self.ax.get_ylim()
            delx=(xlim[1]-xlim[0])
            self.ax.set_xlim([xlim[1],xlim[1]+delx])
            self.ax.set_ylim(ylim)
            self.spectrum.canvas.draw() 
        # Set pan spectrum
        elif event.key=='[':
            xlim=self.ax.get_xlim()
            ylim=self.ax.get_ylim()
            delx=(xlim[1]-xlim[0])
            self.ax.set_xlim([xlim[0]-delx,xlim[0]])
            self.ax.set_ylim(ylim)
            self.spectrum.canvas.draw() 

        elif event.key == 'Y':
            Windowname='Manual y-Limits'
            instruction='Input range (e.g. 0.,2.)'
            ylim, ok = QInputDialog.getText(self,Windowname,instruction)
            if ok:
                ylimit = ylim.split(',')
                ylimit = np.array(ylimit).astype('float32')
                self.ax.set_ylim(ylimit)
                self.spectrum.canvas.draw()
        elif ((event.key == 'h') or (event.key =='H')):
            self.help = HelpWindow()
            self.help.show()
            
        elif event.key =='v':
            #first check if absorber linelist has already been catologed.
            if self.zabs in self.line_list.Zabs.tolist():
                
                #if so, ask user if they would like to re-eval the results
                buttonReply = QMessageBox.question(self,"Reevaluate" ,"Current Zabs LineList already evaluated: Reevaluate and overwrite?",
                                                   QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
                if buttonReply == QMessageBox.Yes:
                    self.ion_selection = vStack(self,self.wave,self.flux,self.error,'LLS',zabs=self.zabs)
                    
            #otherwise, proceed without manual consent
            else:
                self.ion_selection = vStack(self,self.wave,self.flux,self.error,'LLS',zabs=self.zabs)

        elif event.key =='j':
            self.xdata = event.xdata
            self.manT = Manual_Transition(self)
            self.manT.show()
            
        #Zoom out to FULL spectrum
        elif event.key == 'F':
            self.ax.set_xlim(self.init_xlims)
            self.spectrum.canvas.draw()
            
    #Update manager brings items from the active zabs layout (below canvas) to an entry in the zabs_manager
    def update_manager(self):
        self.color = self.combo_color_main.currentText()
        try: linelist = self.manT.combo_ll.currentText()
        except: linelist =self.combo_lines.currentText() 
        new_row = pd.Series(data = {'Zabs': self.zabs, 'list': linelist, 'color': self.color})
        self.zabs_list=self.zabs_list.append(new_row,ignore_index=True)
        
        self.zabs_line_plot.append(self.temp_plots)
        self.text.append(self.tt_temp)
        
        #if you're filling a final slot within the zabs manager, create another slot
        if self.abs_plot.table.rowCount() == self.zabs_list.shape[0]:
            iterations = self.abs_plot.table.rowCount()
            for ii in range(iterations):
                if self.abs_plot.table.item(ii,1) == None:
                    #set z
                    self.abs_plot.table.setItem(ii,1,QtWidgets.QTableWidgetItem(str(np.round(self.zabs,4))))
                    #set linelist
                    self.abs_plot.table.cellWidget(ii,0).setCurrentIndex(self.combo_lines.currentIndex())
                    #set color
                    self.abs_plot.table.cellWidget(ii,2).setCurrentIndex(self.combo_color_main.currentIndex())
            Catalog(self)
            try: self.manT.close()
            except: pass
#             self.active_ion.setText(' ')
            self.spectrum.canvas.draw()

        #else populate the first empty slot without creating a new
        else:
            iterations = self.abs_plot.table.rowCount()
            for ii in range(iterations):
                if self.abs_plot.table.item(ii,1) == None:
                    self.abs_plot.table.setItem(ii,1,QtWidgets.QTableWidgetItem(str(np.round(self.zabs,4))))
                    #set linelist
                    self.abs_plot.table.cellWidget(ii,0).setCurrentIndex(self.combo_lines.currentIndex())
                    #set color
                    self.abs_plot.table.cellWidget(ii,2).setCurrentIndex(self.combo_color_main.currentIndex())
                    self.abs_plot.table.resizeColumnsToContents()
                    try: self.manT.close()
                    except: pass
#                     self.active_ion.setText(' ')

                    self.spectrum.canvas.draw()
                    break
                    
    def Refreshed(self,parent):
        if len(self.ax.lines)>1:
            del self.ax.lines[1:]
            self.ax.texts = []
            try:
                for ii in self.text[-1]:
                    ii.remove()
            except:
                pass
            self.spectrum.canvas.draw()
        
    
    def cellchanged(self):
        col = self.abs_plot.table.currentColumn()
        row = self.abs_plot.table.currentRow()
        try: text = self.abs_plot.table.currentItem().text()
        except: pass
        try: self.abs_plot.table.cellWidget(row,col).setText(text)
        except: pass
        try: self.active_zabs.setText(text); self.zabs = np.double(text)
        except: pass
    def zabs_changed(self):
        try: self.zabs = np.double(self.active_zabs.text())
        except: self.active_zabs.setText("Please input numerical redshift")
            
    def saveCatalog_fn(self,parent):
        self.saving = SaveCatalog(parent)
        if self.saving.continueSaving == True:
            self.saving.show()
        else:
            self.saving.close()
            
    def LoadCatalog_fn(self,parent):
        self.loading = LoadCatalog(parent)
        self.loading.show()
        

    def specplot(self):
        ax=self.spectrum.gca()
        xlim=ax.get_xlim()
        ylim=ax.get_ylim()
        replace = ax.step(self.wave,self.smoothed_spectrum,'-',lw=1,label='smooth',color=clr['teal'])
        self.ax.lines[0] = replace[0]
        del self.ax.lines[-1]
        self.spectrum.canvas.draw() 
        

    # Read and draw linelist    
    def DrawLineList(self,label,color='white',remove = False,hide =False,Man_Transition = False):
        self.active_zabs.setText(str(self.zabs))
        self.throw_away = False
        
        #this is for 'Z' functionality deletes all lines and plots a new line
        if ((remove == True) & (self.row_remove == False) & (self.hide == False)):
            del self.ax.lines[1:len(self.ax.lines)]
            self.ax.texts = []
            self.throw_away = True
            
        #HIDE PROCEDURE
        if ((remove == True) & (self.hide == True)):
            for ii in self.text[self.row][:]:
                ii.remove()
            for ii in self.zabs_line_plot[self.row][:]:
                ii.remove()
            
            self.zabs_line_plot[self.row] = []
            self.text[self.row] = []
            self.spectrum.canvas.draw()
            return
        
        # REMOVE PROCEDURE
        elif ((remove == True) & (self.row_remove == True)):
            #remove lines from canvas
            for ii in self.text[self.row][:]:
                try: ii.remove()
                except: pass

            for ii in self.zabs_line_plot[self.row][:]:
                try: ii.remove()
                except: pass
                
            #delete line identifiers
            if len(self.text)>0:
                del self.text[self.row]
            try: 
                del self.z_list[self.row]
            except:
                if len(self.z_list) < 1:
                    pass
                else:
                    print('copy error and cntrl f!')
            del self.zabs_line_plot[self.row]
            self.spectrum.canvas.draw()
            return
        
        #PLOT PROCEDURE (otherwise continue plotting)
        else:
            self.label=label
            linecolor=clr[color]
            data=line.read_line_list(label)
            xlim=self.ax.get_xlim()
            ylim=self.ax.get_ylim()
            
            tt_temp = []
            temp_plots = []
            for i in range(0, len(data)):
                if ((data[i]['wrest']*(1.+self.zabs) >= np.double(xlim[0])) & (data[i]['wrest']*(1.+self.zabs) <= np.double(xlim[1]))):
                    xdata=[data[i]['wrest']*(1.+self.zabs),data[i]['wrest']*(1.+self.zabs)]
                    ss=self.ax.transData.transform((0, .9))
                    ydata=[0,ylim[1]]
                    lineplot,=self.ax.plot(xdata,ydata,'--',color=linecolor)                    
                    tt=self.ax.text(xdata[0],0.75*ylim[1],data[i]['ion']+' '+ np.str(self.zabs),rotation=90)
                    
                    #append text and plot artist objects
                    tt_temp.append(tt)
                    temp_plots.append(lineplot)


            self.tt_temp = tt_temp
            self.temp_lines = len(tt_temp)#uneccessary do use additional id
            self.temp_plots = temp_plots
            #if first zabs or new zabs

            if ((self.zabs not in self.z_list or len(self.zabs_line_plot)<1) and (self.throw_away == False) and (Man_Transition == False)):
                self.zabs_line_plot.append(temp_plots)
                self.text.append(tt_temp)
                self.z_list.append(self.zabs)
            
            #if replotting a zabs, then reindex its lines
            elif ((self.zabs in self.z_list) and (self.throw_away == False) and (Man_Transition == False)): #maybe need the zabs update option to make sure nothing happens in the 'Z' event
                self.zabs_line_plot[self.row] = temp_plots
                self.text[self.row] = tt_temp
            #need to store new text objects     
            if self.hide == True:
                self.text[self.row] = tt_temp
                self.zabs_line_plot[self.row] = temp_plots
        self.spectrum.canvas.draw()


    def get_linelist(self):
        items = ( "LLS", "LLS Small", "DLA","None")

        item, ok = QInputDialog.getItem(self, "Select Linelist", 
            "Line Lists", items, 0, False)            
        
        if ok and item:
            self.label=item


class Redshift_Guess:
    def __init__(self,parent):
        parent.zabs = np.double(parent.active_zabs.text())
        color = parent.combo_color_main.currentText()
        label = parent.combo_lines.currentText()
        parent.DrawLineList(label,color=color,remove = True,hide =False)

        
class manage_identified_absorbers(QWidget):
    def __init__(self,parent):
        super().__init__()
        self.resize(300,250)
        self.layout = QHBoxLayout()
        self.table = QTableWidget()
        self.setWindowTitle('Zabs Manager')
        
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(('Line Lists','z','Color','Plot','Remove','Hide'))
        self.table.setRowCount(2)
        #make longer color list
        clrlist=list(clr.keys()) 
        self.combo_options = clrlist[1:]#['yellow','orange','red','green','white']
        self.line_options = ['LLS','LLS Small','DLA','None']
        
        for i in range(2):
            combo = QComboBox()
            for items in self.combo_options:
                combo.addItem(items)
            self.table.setCellWidget(i,2,combo)
        for i in range(2):
            combo = QComboBox()
            self.plotbut = QPushButton("Plot",self)
            self.plotbut.clicked.connect(lambda: self.plot(parent))
            
            self.removebut = QPushButton("Remove",self)
            #overwrites objectName
            self.removebut.setObjectName(str(i))
            self.removebut.clicked.connect(lambda: self.remove(parent))
            
            self.hidebut = QPushButton("Hide",self)
            self.hidebut.clicked.connect(lambda: self.hide(parent))
            
            for items in self.line_options:
                combo.addItem(items)
            self.table.setCellWidget(i,0,combo)
            self.table.setCellWidget(i,3,self.plotbut)
            self.table.setCellWidget(i,4,self.removebut)
            self.table.setCellWidget(i,5,self.hidebut)

        self.table.cellChanged.connect(self.cellchanged)
        self.layout.addWidget(self.table)
        self.setLayout(self.layout)
        self.identified_line=None
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.table.resizeColumnsToContents()

    def plot(self,parent):
        row,column = self.get_index(self)
        parent.row = row
        linelist = parent.abs_plot.table.cellWidget(row,0).currentText()
        z = np.double(parent.abs_plot.table.item(row,1).text())
        parent.zabs = z
        color = parent.abs_plot.table.cellWidget(row,2).currentText()

        new_row = pd.Series(data = {'Zabs': z, 'list': linelist, 'color': color})
        if parent.zabs_list.shape[0]< 1:
            parent.zabs_list=parent.zabs_list.append(new_row,ignore_index=True)
    
        elif parent.zabs not in parent.zabs_list.Zabs.to_numpy():
            parent.zabs_list=parent.zabs_list.append(new_row,ignore_index=True)
#         elif parent.zabs in parent.zabs_list.Zabs.to_numpy():

        parent.hide = True #update text objects for removal/hiding
        parent.DrawLineList(linelist,color,remove = False)
        parent.hide = False
        
        #ensure entered redshift is visible
        self.table.resizeColumnsToContents()
        
        #if the user has hidden the plot, turn hide background back to gray
        self.table.cellWidget(row,5).setStyleSheet('background-color : QColor(53, 53, 53)')
        #need to write a function for making the table entries the below code is redundant
        if self.table.rowCount() == parent.zabs_list.shape[0]:
            new_row = self.table.rowCount()
            self.table.setRowCount(self.table.rowCount()+1)
            #self.table.insertRow(self.table.rowCount())
            
            combo_color = QComboBox()
            for items in self.combo_options:
                combo_color.addItem(items)
            self.table.setCellWidget(new_row,2,combo_color)
            
            self.plotbut = QPushButton("Plot",self)
            self.plotbut.clicked.connect(lambda: self.plot(parent))
            
            self.removebut = QPushButton("Remove",self)

#             self.removebut.setObjectName(str(i))
            self.removebut.clicked.connect(lambda: self.remove(parent))
            
            self.hidebut = QPushButton("Hide",self)
            self.hidebut.clicked.connect(lambda: self.hide(parent))
            combo = QComboBox()
            for items in self.line_options:
                combo.addItem(items)
            self.table.setCellWidget(new_row,0,combo)
            self.table.setCellWidget(new_row,3,self.plotbut)
            self.table.setCellWidget(new_row,4,self.removebut)
            self.table.setCellWidget(new_row,5,self.hidebut)
            self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
            
            
    
            
    def hide(self,parent):
        row,column = self.get_index(self)#parent.abs_plot.table.currentRow()
        parent.row = row
        linelist = parent.abs_plot.table.cellWidget(row,0).currentText()
        color = parent.abs_plot.table.cellWidget(row,2).currentText()
        parent.hide = True
        parent.DrawLineList(linelist,color,remove = True)
        parent.hide = False
        parent.abs_plot.table.cellWidget(row,5).setStyleSheet('background-color : green')
        
    def remove(self,parent):
        #get row of deleted zabs values
        row,column = self.get_index(self)
        parent.row = row
        
        #need to remove the objects stored in canvas for plot/hide functionality with condition row_remove==True
        parent.row_remove = True
        color = parent.abs_plot.table.cellWidget(row,2).currentText()
        parent.DrawLineList('label',color,remove = True)
        parent.row_remove = False
        
        #remove from the line_list manager if user has stored
        zabs = float(parent.abs_plot.table.item(row,1).text())
        if zabs in parent.line_list.Zabs.tolist():
            index = parent.line_list[parent.line_list['Zabs'] == zabs].index
            parent.line_list = parent.line_list.drop(index,inplace=False)

        #remove from the table widget
        self.table.removeRow(row)
        
        #remove from the zabs_manager
        parent.zabs_list = parent.zabs_list.drop(parent.zabs_list.index[row])
        

    def cellchanged(self):
        col = self.table.currentColumn()
        row = self.table.currentRow()
        try: text = self.table.currentItem().text()
        except: pass
    def get_index(self,parent):
        button = QtWidgets.QApplication.focusWidget()
        index = self.table.indexAt(button.pos())
        if index.isValid():
            row = index.row()
            column = index.column()
        return row,column
    
        



class Manual_Transition(QWidget):
    def __init__(self,parent):
        super().__init__()
        self.resize(200,900)
        self.layout = QVBoxLayout()
        self.line_options = ['LLS','LLS Small','DLA','None']
        self.combo_ll = QComboBox()
        for items in self.line_options:
            self.combo_ll.addItem(items)
        self.layout.addWidget(self.combo_ll)
        self.layout.setAlignment(QtCore.Qt.AlignTop)
        self.setLayout(self.layout)
        self.combo_ll.currentIndexChanged.connect(lambda: self.line_change(parent))
    
        
        #Obtain Absorber
        self.Transitions = QListWidget()
        data = line.read_line_list('LLS')
        self.wavelist = []
        for ii in range(len(data)):
            self.Transitions.addItem(data[ii]['ion'])
            self.wavelist.append(data[ii]['wrest'])
        self.Transitions.itemClicked.connect(lambda: self.transition_change(parent))
            
        self.layout.addWidget(self.Transitions)
        
        #Need to obtain linelist
    def line_change(self,parent):
        parent.label = self.combo_ll.currentText()
        data = line.read_line_list(self.combo_ll.currentText())
        self.Transitions.clear()
        
        for ii in range(len(data)):
            self.Transitions.addItem(data[ii]['ion'])
            
    def transition_change(self,parent):
        
        del parent.ax.lines[1:]
        parent.ax.texts = []
        
        parent.label = self.combo_ll.currentText()
#         parent.active_ion.setText(self.Transitions.currentItem().text())
        lambda_rest = self.wavelist[self.Transitions.currentRow()]
        parent.lambda_rest = lambda_rest
        
        parent.zabs= np.round((parent.xdata -lambda_rest)/lambda_rest,4)
        parent.active_zabs.setText(str(parent.zabs))
        parent.DrawLineList(parent.label,color=parent.combo_color_main.currentText(),remove=False,Man_Transition=True)


        
class Catalog:
    def __init__(self,parent):
        try:self.table = parent.abs_plot.table
        except: self.table=parent.table
        new_row = self.table.rowCount()
        self.table.setRowCount(self.table.rowCount()+1)


        combo_color = QComboBox()
        for items in parent.combo_options:
            combo_color.addItem(items)
        self.table.setCellWidget(new_row,2,combo_color)

        self.plotbut = QPushButton("Plot",self.table)
        self.plotbut.clicked.connect(lambda: manage_identified_absorbers.plot(parent.abs_plot,parent))

        self.removebut = QPushButton("Remove",self.table)

        self.removebut.clicked.connect(lambda: manage_identified_absorbers.remove(parent.abs_plot,parent))

        self.hidebut = QPushButton("Hide",self.table)
        self.hidebut.clicked.connect(lambda: manage_identified_absorbers.hide(parent.abs_plot,parent))
        combo = QComboBox()
        for items in parent.line_options:
            combo.addItem(items)
        self.table.setCellWidget(new_row,0,combo)
        self.table.setCellWidget(new_row,3,self.plotbut)
        self.table.setCellWidget(new_row,4,self.removebut)
        self.table.setCellWidget(new_row,5,self.hidebut)
        self.table.setSizeAdjustPolicy(QtWidgets.QAbstractScrollArea.AdjustToContents)
        self.table.resizeColumnsToContents()
        parent.spectrum.canvas.focusWidget()
        try:parent.manT.close()
        except: pass

        
class SaveCatalog(QWidget):
    def __init__(self,parent):
        super().__init__()
        self.resize(700,200)
        
        #set a timer after setting background green. Then close save window
        def onsave(self,parent,method):
            if method == 0:
                file = self.line.text()
                parent_dir = Path(file).parent
                if parent_dir.is_dir() == False:
                    parent_dir.mkdir(exist_ok=True)
                parent.zabs_list.to_csv(file)
                self.savebut.setStyleSheet('background-color : green')
            elif method == 1:
                file = self.line1.text()
                parent_dir = Path(file).parent
                if parent_dir.is_dir() == False:
                    parent_dir.mkdir(exist_ok=True)
                parent.line_list.to_csv(file, sep=' ')
                self.savebut1.setStyleSheet('background-color : green')
            else:
                directory = Path(self.line2.text())
                if directory.is_dir() == False:
                    directory.mkdir(exist_ok=True)

                if ((self.LineLists == 'All') or (self.LineLists == 'Partial')):
                    parent.line_list.to_csv(str((directory/'LineList_Identified.txt').resolve()), sep=' ')


                file = directory / 'Absorber_Catalog.csv'
                parent.zabs_list.to_csv(str(file.resolve()))
                self.savebut2.setStyleSheet('background-color : green')
                
        self.continueSaving = True
#         layout = QHBoxLayout()
        
        #if no linelists have been identified
        if parent.line_list.shape[0] == 0:
            buttonReply = QMessageBox.question(self,"Missing Linelist" ,"No Linelists have been obtained: Proceed?",QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if buttonReply == QMessageBox.Yes:
                self.LineLists = 'None' 
            else: self.continueSaving = False
        
        #if more absorbers in zabs manager than unique zabs in linelist manager
        if (parent.zabs_list.shape[0] != len(np.unique(parent.line_list.Zabs.tolist()))) and (self.continueSaving==True) and (parent.line_list.shape[0] != 0):
            buttonReply = QMessageBox.question(self,"Missing Linelist" ,"Missing linelists for the cataloged absorbers, continue?",QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
            if buttonReply == QMessageBox.Yes:
                self.LineLists = 'Partial'
            else: self.continueSaving = False
        else:
            self.LineLists = 'All'
            
        if self.continueSaving == True:
            directory = Path.cwd()
            directory = directory /'SpecPlot_Projects'
            
            #layouts
            main = QVBoxLayout()
            layout = QHBoxLayout()
            layout1 = QHBoxLayout()
            layout2 = QHBoxLayout()
            layouts = [layout,layout1,layout2]
            
            #labels
            label = QLabel('Absorber Catolog Save (formats accepted: .csv)')
            label1 = QLabel('Linelist Save (formats accepted: .txt, .log)')
            label2 = QLabel('Directory Save (enter parent folder, filename defaults: Absorber_Catolog.csv, Identified_Linelist.txt)')
            labels = [label,label1,label2]
            
            #line edits
            self.line = QLineEdit(self)
            self.line1 = QLineEdit(self)
            self.line2 = QLineEdit(self)
            self.line.setText(str((directory / 'Absorber_Catalog.csv').resolve()))
            self.line1.setText(str((directory / 'Identified_Linelist.txt').resolve()))
            self.line2.setText(str(directory.resolve()))
            lines = [self.line,self.line1,self.line2]
            
            #save buttons
            self.savebut = QPushButton("Save",self)
            self.savebut.clicked.connect(lambda: onsave(self,parent,0))
            self.savebut1 = QPushButton("Save",self)
            self.savebut1.clicked.connect(lambda: onsave(self,parent,1))
            self.savebut2 = QPushButton("Save",self)
            self.savebut2.clicked.connect(lambda: onsave(self,parent,2))
            savebuts = [self.savebut,self.savebut1,self.savebut2]
            
            #create layout
            for ii in range(3):
                main.addWidget(labels[ii])
                layouts[ii].addWidget(lines[ii])
                layouts[ii].addWidget(savebuts[ii])
                main.addLayout(layouts[ii])
                

            
            self.setLayout(main)
            
        #Tell user which absorbers dont have a linelist by marking the comboboxes in red background and close save window
        elif self.continueSaving == False: #and ((self.LineLists == 'Partial') or (self.LineLists == 'None')):
            line_zabs = np.unique(parent.line_list.Zabs.tolist())
            manager_zabs = parent.zabs_list.Zabs.tolist()
            
            # for zabs in zabs manager that arent in line_list
            if len(line_zabs>0):
                for z in manager_zabs:
                    if z in line_zabs:
                        pass
                    else:
                        index = parent.zabs_list.Zabs[parent.zabs_list.Zabs == z].index[0]
                        parent.abs_plot.table.cellWidget(index,0).setStyleSheet('background-color : red')
                        parent.abs_plot.table.cellWidget(index,2).setStyleSheet('background-color : red')
    
                    #setcellWidgetbackground color
                self.close()
            else:
                index = parent.zabs_list.Zabs[parent.zabs_list.Zabs == parent.zabs_list.Zabs.tolist()[0]].index[0]
                parent.abs_plot.table.cellWidget(index,0).setStyleSheet('background-color : red')
                parent.abs_plot.table.cellWidget(index,2).setStyleSheet('background-color : red')
                self.close()
        #else close save window
        else:
            self.close()

class LoadCatalog(QWidget):
    def __init__(self,parent):
        super().__init__()
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        #lay1= absorbercat.csv load; lay2= linelist.txt load; lay3=directory containing both load
        layout = QHBoxLayout(self)
        layout1 = QHBoxLayout(self)
        layout2 = QHBoxLayout(self)
        
        self.label = QLabel("Enter Zabs Manager dir+file (AbsorberCatalog.csv is default)")
        self.entry = QLineEdit(self)
        self.browse = QPushButton("Browse")
        self.browse.clicked.connect(lambda: self.browsefiles(parent,0))
        
        self.label1 = QLabel("Enter Linelist dir+file (Identified_Linelist.txt is default)")
        self.entry1 = QLineEdit(self)
        self.browse1 = QPushButton("Browse")
        self.browse1.clicked.connect(lambda: self.browsefiles(parent,1))
        
        self.label2 = QLabel("Enter Directory containing both")
        self.entry2 = QLineEdit(self)
        self.browse2 = QPushButton("Browse")
        self.browse2.clicked.connect(lambda: self.browsefiles(parent,2))
        
        #Add widgets to layout
        labs = [self.label,self.label1,self.label2]
        entrys = [self.entry,self.entry1,self.entry2]
        browses = [self.browse,self.browse1,self.browse2]
        lays = [layout,layout1,layout2]
        for ii in range(len(labs)):
            main_layout.addWidget(labs[ii])
            lays[ii].addWidget(entrys[ii])
#             lays[ii].addWidget(buttons[ii])
            lays[ii].addWidget(browses[ii])
            main_layout.addLayout(lays[ii])
        
        
        
        #setAutoDefault registers 'enter' to "load" function
        #this should correspond to which of the boxes are filled
        #self.button.setAutoDefault(True)
#         self.entry.returnPressed.connect(self.button.click)
                                
    def browsefiles(self,parent,method):
        if method == 0: # get csv
            fname,_ = QFileDialog.getOpenFileName(self, 'Open file', os.getcwd(),"CSV files (*csv)")
            parent.zabs_list = pd.read_csv(fname)
            parent.zabs_list = parent.zabs_list[parent.zabs_list.keys()[1:]]
            #Populate zabs list and hide plots
            self.populate_zabs_manager(parent)
            
            
        elif method == 1: #get txt
            fname,_ = QFileDialog.getOpenFileName(self, 'Open file', os.getcwd(),"Text files (*txt *.log)")
            parent.line_list = pd.read_csv(fname,sep=' ')
            parent.line_list = parent.line_list[parent.line_list.keys()[1:]]
            self.plot_identified_lines(parent)
            
        else:
            dirs = QFileDialog.getExistingDirectory(self,"Open a folder",os.getenv("HOME"),QFileDialog.ShowDirsOnly)
            for files in os.listdir(dirs):
            #read in zabs manager
                if files.endswith('.csv'):
                    parent.zabs_list = pd.read_csv(files)
                    parent.zabs_list = parent.zabs_list[parent.zabs_list.keys()[1:]]
                    self.populate_zabs_manager(parent)
                #read in linelist manager
                elif files.endswith('.txt'):
                    parent.line_list = pd.read_csv(files,sep=' ')
                    parent.line_list = parent.line_list[parent.line_list.keys()[1:]]
                    self.plot_identified_lines(parent)

            self.close()
    def populate_zabs_manager(self,parent):
        zabs = parent.zabs_list['Zabs'].values.tolist()
        self.green_index = []
        for ii in range(parent.zabs_list.shape[0]):       
            if ii >= parent.abs_plot.table.rowCount():
                #Catalog class create the new zabs_manager rows
                Catalog(parent)
                
            #Fill the newly created rows with saved values
            parent.row = ii
            parent.zabs = zabs[ii]
            parent.abs_plot.table.setItem(ii,1,QtWidgets.QTableWidgetItem(str(zabs[ii])))
            parent.abs_plot.table.cellWidget(ii,2).setCurrentText(parent.zabs_list['color'].iloc[ii])
            parent.abs_plot.table.cellWidget(ii,0).setCurrentText(parent.zabs_list['list'].iloc[ii])
            parent.DrawLineList(parent.zabs_list['list'].iloc[ii],color = parent.zabs_list['color'].iloc[ii])
            if ii > 0:
                parent.hide = True
                parent.DrawLineList(parent.zabs_list['list'].iloc[ii],parent.zabs_list['color'].iloc[ii],remove = True)
                parent.hide = False
                parent.abs_plot.table.cellWidget(ii,5).setStyleSheet('background-color : green')
                self.green_index.append(ii)
        Catalog(parent)
    
    def plot_identified_lines(self,parent):
        #if zabs_manager already loaded
        if parent.zabs_list.shape[0]>0:
            # clear plotted lines/text from zabs_manager such that the new lines for plot/remove/hide are same color as linelist
            del parent.ax.lines[1:]; parent.zabs_line_plot = []
            parent.ax.texts = []; parent.texts = []

            for z in parent.zabs_list.Zabs.tolist():
                index = parent.line_list[parent.line_list['Zabs'] == z].index
                color = parent.zabs_list.color[parent.zabs_list.Zabs == z].values[0]
                ylim=parent.ax.get_ylim()
                #for all lines at that redshift
                for i in index:
                    xdata = [parent.line_list.loc[i].Wave_obs,parent.line_list.loc[i].Wave_obs]
                    ylow = np.interp(xdata[0],parent.wave,parent.flux)+.75
                    lineplot,=parent.ax.plot(xdata,[ylow,0.75*ylim[1]],'-',color=color)
                    tt = parent.ax.text(xdata[0],0.75*ylim[1],parent.line_list.loc[i].Name+' '+ np.str(parent.line_list.loc[i].Zabs),rotation=90)
                    parent.identified_lines.append(lineplot)
                    parent.identified_text.append(tt)
                parent.text = [[]]*len(parent.zabs_list.Zabs.tolist())
                parent.zabs_line_plot = [[]]*len(parent.zabs_list.Zabs.tolist())
                
            #if linelist has absorbers that are not cataloged
            if len(np.unique(parent.line_list.Zabs.tolist())) > len(parent.zabs_list.Zabs.tolist()):
                zabs_list = parent.zabs_list.Zabs.tolist()
                line_list_zabs = np.unique(parent.line_list.Zabs.tolist())
                for z in line_list_zabs:
                    if z not in zabs_list:
                        index = parent.line_list[parent.line_list['Zabs'] == z].index
                        ylim=parent.ax.get_ylim()
                        for i in index:
                            xdata = [parent.line_list.loc[i].Wave_obs,parent.line_list.loc[i].Wave_obs]
                            ylow = np.interp(xdata[0],parent.wave,parent.flux)+.75
                            lineplot,=parent.ax.plot(xdata,[ylow,0.75*ylim[1]],'-',color='white')
                            tt = parent.ax.text(xdata[0],0.75*ylim[1],parent.line_list.loc[i].Name+' '+ np.str(parent.line_list.loc[i].Zabs),rotation=90)
                            parent.identified_lines.append(lineplot)
                            parent.identified_text.append(tt)

        else:

            tt_all = []
            temp_plot = []
            ylim=parent.ax.get_ylim()
            for i in range(parent.line_list.shape[0]):
                xdata = [parent.line_list.loc[i].Wave_obs,parent.line_list.loc[i].Wave_obs]
                ylow = np.interp(xdata[0],parent.wave,parent.flux)+.75
                lineplot,=parent.ax.plot(xdata,[ylow,0.75*ylim[1]],'-',color='white')
                tt = parent.ax.text(xdata[0],0.75*ylim[1],parent.line_list.loc[i].Name+' '+ np.str(parent.line_list.loc[i].Zabs),rotation=90)
                parent.identified_lines.append(lineplot)
                parent.identified_text.append(tt)
                
        try:
            for ii in self.green_index:
                parent.abs_plot.table.cellWidget(ii,5).setStyleSheet('background-color : QColor(53, 53, 53)')
        except:
            pass
        
        parent.Identified_line_plot.setStyleSheet('background-color : green')
        parent.identified_line_active = True
        parent.spectrum.canvas.draw()
   
                
class HelpWindow(QtWidgets.QWidget):
    def __init__(self,parent=None):
        super(HelpWindow, self).__init__(parent)
        self.resize(500,850)
        label = QtWidgets.QLabel(HELP,self)
        
        
class Identified_plotter:
    def __init__(self,parent):
        if parent.line_list.shape[0]==0:
            parent.Identified_line_plot.setStyleSheet('background-color : red')
        else:
            #if active remove plots and set indicator back to gray
            if parent.identified_line_active == True:
                for ii in parent.identified_lines:
                    ii.remove()
                for ii in parent.identified_text:
                    ii.remove()
                parent.identified_text = []; parent.identified_lines = []
                parent.Identified_line_plot.setStyleSheet('background-color : QColor(53, 53, 53)')
                parent.identified_line_active = False
            #else 
            else:
                parent.identified_line_active = True
                if parent.zabs_list.shape[0]>0:
                    for z in parent.zabs_list.Zabs.tolist():
                        index = parent.line_list[parent.line_list['Zabs'] == z].index
                        color = parent.zabs_list.color[parent.zabs_list.Zabs == z].values[0]
                        ylim=parent.ax.get_ylim()
                        for i in index:
                            xdata = [parent.line_list.loc[i].Wave_obs,parent.line_list.loc[i].Wave_obs]
                            ylow = np.interp(xdata[0],parent.wave,parent.flux)+.75
                            lineplot,=parent.ax.plot(xdata,[ylow,0.75*ylim[1]],'-',color=color)
                            tt = parent.ax.text(xdata[0],0.75*ylim[1],parent.line_list.loc[i].Name+' '+ np.str(parent.line_list.loc[i].Zabs),rotation=90)
                            parent.identified_lines.append(lineplot)
                            parent.identified_text.append(tt)

                
                    #if linelist has absorbers that are not cataloged
                    if len(np.unique(parent.line_list.Zabs.tolist())) > len(parent.zabs_list.Zabs.tolist()):
                        zabs_list = parent.zabs_list.Zabs.tolist()
                        line_list_zabs = np.unique(parent.line_list.Zabs.tolist())
                        for z in line_list_zabs:
                            if z not in zabs_list:
                                index = parent.line_list[parent.line_list['Zabs'] == z].index
                                ylim=parent.ax.get_ylim()
                                for i in index:
                                    xdata = [parent.line_list.loc[i].Wave_obs,parent.line_list.loc[i].Wave_obs]
                                    ylow = np.interp(xdata[0],parent.wave,parent.flux)+.75
                                    lineplot,=parent.ax.plot(xdata,[ylow,0.75*ylim[1]],'-',color='white')
                                    tt = parent.ax.text(xdata[0],0.75*ylim[1],parent.line_list.loc[i].Name+' '+ np.str(parent.line_list.loc[i].Zabs),rotation=90)
                                    parent.identified_lines.append(lineplot)
                                    parent.identified_text.append(tt)
                else:
                    ylim=parent.ax.get_ylim()
                    for i in range(parent.line_list.shape[0]):
                        xdata = [parent.line_list.loc[i].Wave_obs,parent.line_list.loc[i].Wave_obs]
                        ylow = np.interp(xdata[0],parent.wave,parent.flux)+.75
                        lineplot,=parent.ax.plot(xdata,[ylow,0.75*ylim[1]],'-',color='white')
                        tt = parent.ax.text(xdata[0],0.75*ylim[1],parent.line_list.loc[i].Name+' '+ np.str(parent.line_list.loc[i].Zabs),rotation=90)
                        parent.identified_lines.append(lineplot)
                        parent.identified_text.append(tt)
                                    
                parent.Identified_line_plot.setStyleSheet('background-color : green')        
            parent.spectrum.canvas.draw()
                
                
                
#---------------for Vstack---------------------#

def prepare_absorber_object(z_abs,wave,flux,error,line_flg='LLS',vlim=[-1000,1000]):
    
    # Read the full linelist
    data=line.read_line_list(line_flg)
    wavelist=[]
    for i in range(0,len(data)):
        wavelist.append(data[i]['wrest'])
        
        
    wavelist=np.array(wavelist)

    
    # select the lines within the wavelength range only
    q= np.where((wavelist > np.min(wave)/(1.+z_abs)) &  (wavelist < (np.max(wave)/(1.+z_abs))));
    
    # Total transitions visible within the wavelength window
    nTot= len(q[0]);
    
    wavelist_selected=wavelist[q]
    
    absys=A.Absorber(z_abs,wave,flux,error,list(wavelist_selected),window_lim=vlim,nofrills=True)   
    
    return absys.ions
    

class vStack:
    def __init__(self,parent,wave,flux,error,line_flg,zabs=0,vlim=[-1000.,1000.]):  
        self.parent = parent
        self.parent_canvas = parent.canvas
        self.zabs=zabs
        self.vlim=vlim
        self.ions=prepare_absorber_object(zabs,wave,flux,error,line_flg='LLS')
        #-----full spectra properties---------#
        self.z = self.ions['Target']['z']; self.flux = self.ions['Target']['flux']
        self.wave = self.ions['Target']['wave']; self.error = self.ions['Target']['error']
        
               
        self.keys = list(self.ions.keys())[:-1] # last item is the full target spectrum
        
        self.nions = np.int(len(self.keys))
        #Flag to know if it is a detection or not
        #Set everything by default to non-detection
        for i in (self.keys):
            self.ions[i]['flag']=0
        
        
        #-----Sorting out how many pages are needed---------#

        
        self.page=1
        self.plotppage=12
        self.nrow=int(self.plotppage/3)
        self.ncol=int((self.plotppage)/self.nrow)
        self.npages=int((self.nions/self.plotppage))
        
        
        fig= Figure()#figure(figsize=(12,8))
        self.fig=fig
        self.axes=list(range(self.plotppage))
        for i in range(self.plotppage):
            self.axes[i]=self.fig.add_subplot(self.nrow,self.ncol,i+1)
        self.axes=np.array(self.axes)
        self.vPlot()
        self.fig.subplots_adjust(hspace=0)

        self.canvas = FigureCanvasQTAgg(self.fig)
        
        self.fig.canvas.setFocusPolicy( QtCore.Qt.ClickFocus )
        self.fig.canvas.setFocus()
        self.cid = self.fig.canvas.mpl_connect('key_press_event',self.onkb)
        
        parent.plot_layout.removeWidget(parent.canvas)
        plt.close(self.parent.spectrum)
        parent.plot_layout.insertWidget(1,self.canvas)#FigureCanvasQTAgg(self.fig))


    def onkb(self,event):
        #set up custom y-limit
        if event.key=='Y':
            if event.inaxes in self.axes:
                i=np.where(event.inaxes==self.axes)[0][0]+self.plotppage*(self.page-1)
                Windowname='Manual y-Limits'
                instruction_text='Input range (e.g. 0.,2.)'
                temp=input_txt_dlg(Windowname,instruction_text)
                yrangetext=temp.filename

                yrange = yrangetext.split(',')
                yrange = np.array(yrange).astype('float32')
                self.vPlot(ploti=i,yrange=[yrange[0],yrange[1]])
                
        #page right
        elif event.key=='>':
            self.page+=1
            if self.page>self.npages: 
                self.page=1
            self.vPlot()
        #page left
        elif event.key=='<':
            self.page-=1
            if self.page<1: 
                self.page=self.npages
            self.vPlot()
            
        #Toggle between detection-non-detection or blended    
        elif event.key =='w': #Detected,non-detected, blended-detection 
            if event.inaxes in self.axes:
                i=np.where(event.inaxes==self.axes)[0][0]+self.plotppage*(self.page-1)
                #set up a dumb toggling cycle
                temp_flag=self.ions[self.keys[i]]['flag']+1

                if temp_flag==0:
                    temp_flag =1
                elif temp_flag==1:
                    temp_flag==2
                else:
                    temp_flag=0
                self.ions[self.keys[i]]['flag']= temp_flag#
                self.vPlot(ploti=i,comment=False)
                
        #save linelist
        elif event.key=='S':
            #reinsert the primary spectrum canvas to the mainlayout for keyboard functionality
            self.parent.plot_layout.removeWidget(self.canvas)
            self.parent.plot_layout.insertWidget(1,self.parent.canvas)
            
            #Need to check if it is reevaluating a linelist, if so delete all lines with same 'zabs' value
            if self.parent.line_list.shape[0] > 0:
                zabs_list = self.parent.line_list.Zabs.tolist()
                if self.parent.zabs in zabs_list:
                    index = self.parent.line_list[self.parent.line_list['Zabs'] == self.parent.zabs].index
                    self.parent.line_list = self.parent.line_list.drop(index,inplace=False)

            keys = list(self.ions.keys())
            # based on line evaluation, add lines to the overall zabs manager linelist ('flag=1' is detected lines to add)
            for key in keys[:-1]:
                if self.ions[key]['flag'] == 1:
                    wave_obs = self.ions[key]['lam_0_z']
                    name = self.ions[key]['name']
                    zabs = self.ions['Target']['z']
                    new_row = pd.Series(data = {'Name': name, 'Wave_obs': wave_obs, 'Zabs': zabs})
                    self.parent.line_list=self.parent.line_list.append(new_row,ignore_index=True)
                    
            #lets keep zabs_list sorted by ascending zabs
            self.parent.line_list = self.parent.line_list.sort_values(by='Zabs')
            
            #close to canvas so spectrum canvas is again visible
            self.canvas.close()
            
            #after quitting save function, lineList and color will be red for unsaved lines, check and replace if saving a missing linelist
            
            #first need to find row
            row = self.parent.zabs_list.Zabs[self.parent.zabs_list.Zabs == self.parent.zabs].index[0]
            
            # red is #ff0000, if not red it will have no palette so this will need to be a try/pass
            try:
                if self.parent.abs_plot.table.cellWidget(row,0).palette().color(QtGui.QPalette.Background).name() == '#ff0000':
                    self.parent.abs_plot.table.cellWidget(row,0).setStyleSheet('background-color : QColor(53, 53, 53)')
                    self.parent.abs_plot.table.cellWidget(row,2).setStyleSheet('background-color : QColor(53, 53, 53)')
            except:
                pass
    def vPlot(self,ploti=None,comment=False,yrange=None):#spec,i=0):
        # global axesR
        if ploti is None:
            ploti=np.arange(self.plotppage*(self.page-1),min(self.plotppage*self.page,self.nions))
        else:
            ploti=[ploti]

        for i in ploti:
            self.plotstuff(i,comment=comment,yrange=yrange)
        self.fig.canvas.draw()

        
    def plotstuff(self,i,comment=False,yrange=False):
        ax=self.axes[i % self.plotppage]
        #---------------Define variables for readability--------------#
        vel = self.ions[self.keys[i]]['vel']
        wave = self.ions[self.keys[i]]['wave']
        error = self.ions[self.keys[i]]['error']
        flux = self.ions[self.keys[i]]['flux']
        name = self.ions[self.keys[i]]['name']
        window_lim = self.ions[self.keys[i]]['window_lim']
        flag=self.ions[self.keys[i]]['flag']
        f0 = self.ions[self.keys[i]]['f']

        ax.clear()
        
        # Set a title giving the page number
        if i % self.plotppage ==0:
            ax.set_title('Page '+ str(self.page)+' of ' + str(self.npages),color=clr['teal'])


        ax.step(vel,flux/np.nanmean(flux),where='mid',color=clr['teal'])
        ax.step(vel,error/np.nanmean(flux),where='mid',color=clr['orange2'])
        
        ax.axhline(1,color=clr['light_gray'],linestyle='dotted')
        ax.axvline(0,color=clr['light_gray'],linestyle='dotted')
        ax.text(x=0.05, y=0.815, s=name, fontsize=10, transform=ax.transAxes,color=clr['red'])
        ax.text(x=0.75, y=0.815, s='f0: '+str(f0), fontsize=10, transform=ax.transAxes,color=clr['red'])
        
        if comment != False:
            ax.text(x=0.85, y=0.815, s=comment, fontsize=12, transform=ax.transAxes,color=clr['teal'])
        if yrange != False:
            ax.set_ylim(yrange)

        
        if flag is not None: #Display some measurement
            textout=self.plotText(flag=flag)
            if flag==1:
                textcolor=clr['yellow']
            else:
                textcolor=clr['light_gray']
            ax.text(x=0.05, y=0.01, s=textout, fontsize=12, transform=ax.transAxes,color=textcolor)
    
    def plotText(self,flag=1):
        if flag==1:
            text='Detection'       
        elif flag==0:
            text='Non-Detection'      
        elif flag==2:
            text ='Blended-detection'
        return text

#Initial inputs and callable class to run proram        
class input_txt_dlg:
    def __init__(self,Windowname,instruction,default_text='test'):
        app = QApplication(sys.argv)
        main = popup_windows(Windowname,instruction,default_text=default_text)
        self.filename=main.filename
        main.show()
        sys.exit(app.exec_())        
        
        
     
        
#--------------------initialization of Application-----------------
class rb_plotspec():
    
    def __init__(self,wave,flux,error,zabs=0.):


        if not QtWidgets.QApplication.instance():
            app = QtWidgets.QApplication(sys.argv)
            app.setStyle("Fusion")

            # Now use a palette to switch to dark colors:
            palette = QPalette()
            palette.setColor(QPalette.Window, QColor(53, 53, 53))
            palette.setColor(QPalette.WindowText, QtCore.Qt.white)        
            palette.setColor(QPalette.Base, QColor(25, 25, 25))
            palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
            palette.setColor(QPalette.Button, QColor(53, 53, 53))
            palette.setColor(QPalette.ButtonText, QtCore.Qt.white)
            palette.setColor(QPalette.BrightText, QtCore.Qt.red)
            palette.setColor(QPalette.Link, QColor(42, 130, 218))
            palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
            palette.setColor(QPalette.Text, QtCore.Qt.white)
    
            app.setPalette(palette)

        else:
            app = QtWidgets.QApplication.instance() 



        #app = QtWidgets.QApplication(sys.argv)
         # Force the style to be the same on all OSs:
        main = mainWindow(wave,flux,error)
        main.resize(1700,900)
        
        #Center app on initialization
        qr = main.frameGeometry()
        cp = QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        main.move(qr.topLeft())
        
        main.show()
        QtWidgets.QApplication.setQuitOnLastWindowClosed(True)
        app.exec_()
        app.quit()


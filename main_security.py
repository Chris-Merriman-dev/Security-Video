'''
Created By : Christian Merriman

Date : 1/22/2024

Purpose : Use to familiarize myself with Python and make a Facial Recognition application. It will let you select an device camera to use and track 
for faces. You can add peoples faces to a database using pandas. It will store a face image of them and other personal information. If it recognizes 
someone that is in the database, it will store when they were there. It will keep track of everytime they were seen.

This uses face_recognition for detecting faces. It will use multiprocessing (multiple cpu cores), for handling the information. I do this so there is 
no slowdown, while it detects faces. A separate core will be send the face information and process it there.

Files Needed :

face_data.py

'''
import face_recognition
from PIL import Image, ImageTk
import os
import shutil
import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog as fd
from threading import Lock
import copy
import time
import multiprocessing
import tkinter.ttk as ttk
from pygrabber.dshow_graph import FilterGraph
import face_data
from datetime import datetime
import datetime
import pandas as pd
import gc

#Globals
ENCODING_DIRECTORY = "Face Data" #directory used for data on people and their faces
REMOVE_FACE_TIME = 1 * 60 # minutes x 60 seconds (mins in seconds)

#use directory like this, because saving to cvs with pandas has issues when i used os
PANDAS_FILENAME1 = "db_data/data1.cvs" #stores details on people
PANDAS_FILENAME2 = "db_data/data2.cvs" #stores the ID of person and date/times they were seen

#use files seperate from directory to use os, to delete files if needed
PANDAS_REAL_FILE1 = "data1.cvs" #stores details on people
PANDAS_REAL_FILE2 = "data2.cvs" #stores the ID of person and date/times they were seen
PANDAS_DIRECT = "db_data" #directory for these files

#apps background color
BACKGROUND_COLOR = "FloralWhite"

#directory and images used for our help section
HELP_IMAGES_DIRECTORY = "Help Images"
HELP_IMAGES = ["Page0.png",
               "Page1.png",
               "Page2.png",
               "Page3.png",
               "Page4.png",
               "Page5.png",
               "Page6.png",
               "Page7.png",
               "Page8.png",
               "Page9.png",
               "Page10.png",
               "Page11.png"]

#Class that runs our application
class VideoRecorder:

    def __init__(self) -> None:
        #value used for showing camera view
        self.show_cam = True

        #init our GUI with TTK
        self.init_GUI_TTK()

        #init to -1, so we know no device to use yet (0 and up good)
        self.device_num = -1

        #init our known facial data
        self.init_Known_Facial_Data(ENCODING_DIRECTORY, True)

    '''
        init_GUI_TTK :
        inits the GUI for our main window frame
    '''
    def init_GUI_TTK(self) -> None:
        #lets us know if our inits valid, to start app
        self.valid_init = True

        #get screen resolution
        self.screen_resolution = self.get_monitor_resolution()        
        
        #set dimensions and positions
        #set to middle of screen
        root_width = 1400
        root_height = 700
        width = self.screen_resolution[0]
        height = self.screen_resolution[1]

        x_pos, y_pos = self.get_Window_Center_Pos(self.screen_resolution[0], self.screen_resolution[1], root_width, root_height)

        #check screen size, to see if it fits into screen res
        if(width < root_width or height < root_height):
            #doesnt fit, so set init to False and return
            messagebox.showerror('Bad Screen Resoultion','Screen Resolution is too small. Need at least, 1920 x 1080.')
            self.valid_init = False
            return

        #create main window frame
        self.root_window = tk.Tk()

        #set our window geometry and settings
        self.root_window.geometry(str(root_width) + 'x' + str(root_height) + '+' + str(x_pos) + '+' + str(y_pos))
        self.root_window.title('Video Security')
        self.root_window.resizable(width=False, height=False)
        self.root_window.configure(bg=BACKGROUND_COLOR)

        #create our window style
        self.style = ttk.Style()

        #set our windows theme
        if 'winnative' in self.style.theme_names():
            self.theme = 'winnative'
        else:
            self.theme = 'default'

        self.style.theme_use(self.theme)

        #setup 4 columns
        for i in range(4):
            self.root_window.columnconfigure(index=i, minsize=root_width/4, weight=1)

        #setup 12 rows
        for i in range(12):
            self.root_window.rowconfigure(index=i, minsize=root_height/12, weight=1)

        #init our gui video
        self.init_GUI_TTK_Video(self.root_window)

        #init our gui data
        self.init_GUI_TTK_Data(self.root_window, self.style)

        #init our gui listbox
        self.init_GUI_Listbox(self.root_window)

        #init our gui buttons
        self.init_GUI_TTK_Buttons(self.root_window, self.style)

        #init our apps root menu
        self.init_GUI_Menu(self.root_window, self.style)

        #set window to top most window and the focus
        self.root_window.attributes('-topmost', True)
        self.root_window.update()
        self.root_window.attributes('-topmost', False)
        self.root_window.update()

        #method to call on windows close
        self.root_window.protocol("WM_DELETE_WINDOW", self.exit)

    '''
        get_Window_Center_Pos :
        Gets our screens center position
    '''
    def get_Window_Center_Pos(self, screenwidth, screenheight, windowwidth, windowheight) -> tuple:
        #set dimensions and positions
        #set to middle of screen
        x_pos = int((screenwidth - windowwidth) / 2)
        y_pos = int((screenheight - windowheight) / 2)

        return (x_pos, y_pos)

    '''
        inits the label for our video
    '''
    def init_GUI_TTK_Video(self, root) -> None:
        #webcam
        self.webcam_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.webcam_label.grid(row=0, column=0, rowspan=10, columnspan=2, sticky= tk.NSEW)

    '''
        check_Input_Devices :
        Uses filtergraph, to see what input video devices are available
    '''
    def check_Input_Devices(self) -> list:
        graph = FilterGraph()
        return graph.get_input_devices()

    '''
        init_WebCam_Device :
        Will init a video device, if we can. It will then stream it, to our label sent in.

    '''
    def init_WebCam_Device(self, label):
        
        #makes sure we do not already have a capture device
        if 'cap' not in self.__dict__:
            #update label to let us know we are loading video
            self.webcam_label.config(text='Loading video from ' + self.check_Input_Devices()[self.device_num] + '...', anchor='center')
            self.root_run_menu.entryconfig('Load Video Device', state='disabled')
            self.root_run_menu.entryconfig('Stop Video Device', state='normal')            
            self.root_window.update()

            #load capture device and set initialized to true
            self.cap = cv2.VideoCapture(self.device_num)            
            self.backSub = cv2.createBackgroundSubtractorMOG2()

            #lets us know if webcam is processing
            self.webcam_processing = False

            #lets us know to stop processing webcam
            self.webcam_processing_stop = False       

            #enable face detection
            self.root_run_menu.entryconfig('Start Face Detection' , state='normal')

            #set a ref to the label
            self._label = label

            #lets us know we dont need to start device
            self.start_device = False

            #update button
            self.start_device_button_main_root.config(text='Stop Video Device')

            #update show face detect button
            self.start_facedetect = True
            self.start_facedetect_button_main_root.config(text='Start Face Detection')
            self.start_facedetect_button_main_root.grid(row=10, column=1, sticky=tk.NSEW)
            self.start_facedetect_button_main_root['state'] = 'normal'

            #check to see if we need to enable hide button
            if not self.show_cam:
                self.hide()

        #reset device num
        self.device_num = -1

        #if we have a capture device and it did not open
        if 'cap' not in self.__dict__ or not self.cap.isOpened():
            
            #remove cap device
            if 'cap' in self.__dict__ :
                self.cap.release()
                del self.__dict__['cap']

            #check to see if we need to enable hide button
            if self.show_cam:
                self.hide()

            #lets us know we need to start device
            self.start_device = True

            #update button
            self.start_device_button_main_root.config(text='Load Video Device')

            #update start face detect button
            self.start_facedetect_button_main_root.grid_forget()

            #update labels
            self.webcam_label.config(text='', anchor='center', image='')
            self.root_run_menu.entryconfig('Stop Video Device', state='disabled')
            self.root_run_menu.entryconfig('Load Video Device', state='normal')
            self.root_run_menu.entryconfig('Start Face Detection' , state='disabled')
            self.root_run_menu.entryconfig('Stop Face Detection' , state='disabled')
            self.root_window.update()

            #show error messages
            messagebox.showerror('No Capture Device', 'Error : No capture device found! Make sure your webcam is plugged in and enabled.')
            #print('ERROR NO VIDEO')
            self.valid_init = False
            return
        

        self.process_Webcam_Device()
    
    '''
        process_Webcam_Device : 
        Will process data, captured from the input video device. It will take that data and do a check for faces, if enabled.
        It will then draw needed information, to our webcam label
    '''
    def process_Webcam_Device(self):
        
        #if we need to stop processing webcam, then just return
        if self.webcam_processing_stop:
            return

        #turn on webcam process flag
        self.webcam_processing = True

        ret, frame = self.cap.read()

        #found video device
        if ret:

            #make sure we are doing multithread
            if 'app_loop_face' in self.__dict__ :
                #turn on face check run
                self.face_check_run = True

                #check for faces and return the locations and names for each face
                locations = self.face_check(frame)

                #update current face listbox
                self.check_names_listbox_remove(REMOVE_FACE_TIME)

                #turn off face check run
                self.face_check_run = False


                if len(locations) == 0:
                    #self.name_label.config(text='No one detected.')
                    pass
                else:
                    for (top, right, bottom, left) in locations:
                    # Scale back up face locations since the frame we detected in was scaled to 1/4 size
                        top *= 2
                        right *= 2
                        bottom *= 2
                        left *= 2

                        # Draw a box around the face
                        cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)

            self.most_recent_capture_arr = frame
            img_ = cv2.cvtColor(self.most_recent_capture_arr, cv2.COLOR_BGR2RGB)
            self.most_recent_capture_pil = Image.fromarray(img_)
            imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)

            #check for hiding or showing webcam
            if self.show_cam :
                self._label.imgtk = imgtk
                self._label.configure(image=imgtk)
            else:
                #self._label.imgtk = None
                self._label.config(text='', anchor='center', image='')

            self._label.after(15, self.process_Webcam_Device)

        #video device error
        else:
            messagebox.showerror('No Video Device Found!', 'Input video device cannot be found! Please check connections.')
            #turn off webcam process flag
            self.webcam_processing = False
            self.stop_Webcam_Device()

        #turn off webcam process flag
        self.webcam_processing = False

    '''
        stop_Webcam_Device:
        If we have a current video device, capturing data, this will stop it.
    '''
    def stop_Webcam_Device(self) -> None:

        #set flag to stop processing webcam
        self.webcam_processing_stop = True

        #loop until we are done processing our webcam
        while self.webcam_processing:
            pass

        #if caps in our dictionary and its open, then release it and delete it from dictionary
        if 'cap' in self.__dict__  and self.cap.isOpened():
            
            #stop face detection if needed
            if 'app_loop_face' in self.__dict__ : 
                self.stop_Facial_Recognition(False)

            self.cap.release()
            del self.__dict__['cap']

            #lets us know we need to start device
            self.start_device = True

            #update button
            self.start_device_button_main_root.config(text='Load Video Device')

            #update face detect button
            self.start_facedetect = True
            self.start_facedetect_button_main_root.config(text='Start Face Detection')
            self.start_facedetect_button_main_root.grid_forget()

            self.webcam_label.config(text='', anchor='center', image='')
            self.root_run_menu.entryconfig('Stop Video Device', state='disabled')
            self.root_run_menu.entryconfig('Load Video Device', state='normal')
            self.root_run_menu.entryconfig('Start Face Detection' , state='disabled')
            self.root_run_menu.entryconfig('Stop Face Detection' , state='disabled')
            #self._label.imgtk = None
            self.root_window.update()

    '''
        init_GUI_Menu :
        This will init our main windows GUI Menu (File, Run, Help).
    '''
    def init_GUI_Menu(self,root, style) -> None:
        
        #turns off dashed line at top of menu
        root.option_add('*tearOff', False)

        #create the roots menu
        self.root_menu = tk.Menu(root)
        root.config(menu=self.root_menu)

        #add our menu drop downs
        #file
        self.root_file_menu = tk.Menu(self.root_menu)
        self.root_menu.add_cascade(label='File', menu=self.root_file_menu, underline=0)# accelerator='Control+F')
        self.root_file_menu.add_separator()
        self.root_file_menu.add_command(label='Exit', command=self.exit, underline=1)

        #run
        self.root_run_menu = tk.Menu(self.root_menu)
        self.root_menu.add_cascade(label='Run', menu=self.root_run_menu, underline=0)
        self.root_run_menu.add_command(label='Load Video Device', underline=0, command= lambda: self.init_VideoDevice_Dialog(root, style, False) )
        self.root_run_menu.add_command(label='Stop Video Device', underline=3, command= self.stop_Webcam_Device, state='disabled')
        self.root_run_menu.add_separator()
        self.root_run_menu.add_command(label='Start Face Detection', command=self.start_Facial_Recognition, underline=0, state='disabled')
        self.root_run_menu.add_command(label='Stop Face Detection', command= lambda: self.stop_Facial_Recognition(True), underline=1, state='disabled')

        #help
        self.root_about_menu = tk.Menu(self.root_menu)
        self.root_menu.add_cascade(label='Help', menu=self.root_about_menu, underline=0)
        self.root_about_menu.add_command(label='Help Documentation', command=self.init_help_documentation_dialog, underline=0)
        self.root_about_menu.add_separator()
        self.root_about_menu.add_command(label='About', command=self.init_help_about_dialog, underline=0)

    '''
        init_GUI_TTK_Data :
        Inits our main windows GUI, to display data, of a selected person.
    '''
    def init_GUI_TTK_Data(self, root, style) -> None:

        #create image label
        self.image_face_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.image_face_label.grid(row=0, column=2, rowspan=4, columnspan=1, sticky=tk.NSEW)
        self.image_face_label.config(text='', anchor='center')

        #create name label
        self.image_name_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.image_name_label.grid(row=0, column=3, sticky=tk.W)
        self.image_name_label.config(text='', anchor='center')

        #create description label
        self.image_description_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.image_description_label.grid(row=1, column=3, sticky=tk.W)
        self.image_description_label.config(text='', anchor='center')

        #create first seen label
        self.image_first_seen_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.image_first_seen_label.grid(row=2, column=3, sticky=tk.W)
        self.image_first_seen_label.config(text='', anchor='center')

        #create last seen label
        self.image_last_seen_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.image_last_seen_label.grid(row=3, column=3, sticky=tk.W)
        self.image_last_seen_label.config(text='', anchor='center')

        #create unique id label
        self.image_uid_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.image_uid_label.grid(row=4, column=2, columnspan=2, sticky=tk.W)
        self.image_uid_label.config(text='', anchor='center')

        #create datetime table label
        self.image_datetime_table_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.image_datetime_table_label.grid(row=5, column=2, columnspan=2, sticky=tk.NSEW)
        self.image_datetime_table_label.config(text='Dates and Times Person Was Here :', anchor='center')

        #create label for names_listbox
        self.names_listbox_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.names_listbox_label.grid(row=8, column=2, columnspan=1, sticky=tk.S)
        self.names_listbox_label.config(text='Current Visitors', anchor='center')

        #create label for all_names_listbox
        self.all_names_listbox_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.all_names_listbox_label.grid(row=8, column=3, columnspan=1, sticky=tk.S)
        self.all_names_listbox_label.config(text='Known People', anchor='center')

        #init our table
        self.init_GUI_TTK_Data_Table(root, style)

    '''
        init_GUI_TTK_Data_Table :
        Inits the main windows GUI for a person selected. It will create a table, that is used to display the dates and times,
        they were last seen.
    '''
    def init_GUI_TTK_Data_Table(self, root, style) -> None:
        #create table
        self.image_datetime_table = ttk.Treeview(root)

        #create scrollbars
        #Y
        self.image_datetime_table_scrollbarY = tk.Scrollbar(self.image_datetime_table, orient=tk.VERTICAL, bg=BACKGROUND_COLOR)
        self.image_datetime_table.config(yscrollcommand=self.image_datetime_table_scrollbarY.set)
        self.image_datetime_table_scrollbarY.config(command=self.image_datetime_table.yview)

        #X
        self.image_datetime_table_scrollbarX = tk.Scrollbar(self.image_datetime_table, orient=tk.HORIZONTAL, bg=BACKGROUND_COLOR)
        self.image_datetime_table.config(xscrollcommand=self.image_datetime_table_scrollbarX.set)
        self.image_datetime_table_scrollbarX.config(command=self.image_datetime_table.xview)

        #set positions
        self.image_datetime_table.grid(row=6, column=2, columnspan=2, rowspan=2, sticky=tk.NSEW)
        self.image_datetime_table_scrollbarY.pack(side=tk.RIGHT, fill=tk.Y)
        self.image_datetime_table_scrollbarX.pack(side=tk.BOTTOM, fill=tk.X)

        #create columns
        self.image_datetime_table['columns'] = ('Date', 'Start Time', 'End Time', 'Total Time')
        self.image_datetime_table.column("#0", width=0,  stretch=tk.NO)
        self.image_datetime_table.column('Date', anchor=tk.CENTER, width=75)
        self.image_datetime_table.column('Start Time', anchor=tk.CENTER, width=75)
        self.image_datetime_table.column('End Time', anchor=tk.CENTER, width=75)
        self.image_datetime_table.column('Total Time', anchor=tk.CENTER, width=75)

        #create headings
        self.image_datetime_table.heading("#0", text='',  anchor=tk.CENTER)
        self.image_datetime_table.heading("Date", text='Date',  anchor=tk.CENTER)
        self.image_datetime_table.heading("Start Time", text='Start Time',  anchor=tk.CENTER)
        self.image_datetime_table.heading("End Time", text='End Time',  anchor=tk.CENTER)
        self.image_datetime_table.heading("Total Time", text='Total Time',  anchor=tk.CENTER)
        
    '''
        init_GUI_Listbox:
        This will create 2 different listboxes, for our stored people.
        self.names_listbox : This is for the active people, that are seen now (with face detection).
        self.all_names_listbox  : This is for all people, we have in our pandas database (even if not seen).

    '''
    def init_GUI_Listbox(self, root) -> None:
        
        #create listbox to display active people (those seen now)
        self.names_listbox = tk.Listbox(root, height=5, selectmode=tk.SINGLE)
        self.names_listbox.bind('<<ListboxSelect>>', self.names_listbox_select)
        
        self.names_listbox_scrollbar = tk.Scrollbar(self.names_listbox, orient=tk.VERTICAL, bg=BACKGROUND_COLOR)  
        self.names_listbox.config(yscrollcommand=self.names_listbox_scrollbar.set)
        self.names_listbox_scrollbar.config(command=self.names_listbox.yview)

        self.names_listbox.grid(padx=5, pady=5, row=9, column=2, rowspan=2, columnspan=1, sticky=tk.NSEW)
        self.names_listbox_scrollbar.pack(side=tk.RIGHT, fill= tk.Y)

        #second listbox for all people in our pandas dataframe
        self.all_names_listbox = tk.Listbox(root, height=5, selectmode=tk.SINGLE)
        self.all_names_listbox.bind('<<ListboxSelect>>', self.all_names_listbox_select)
        
        self.all_names_listbox_scrollbar = tk.Scrollbar(self.all_names_listbox, orient=tk.VERTICAL, bg=BACKGROUND_COLOR)  
        self.all_names_listbox.config(yscrollcommand=self.all_names_listbox_scrollbar.set)
        self.all_names_listbox_scrollbar.config(command=self.all_names_listbox.yview)

        self.all_names_listbox.grid(padx=5, pady=5, row=9, column=3, rowspan=2, columnspan=1, sticky=tk.NSEW)
        self.all_names_listbox_scrollbar.pack(side=tk.RIGHT, fill= tk.Y)

    '''
        init_GUI_TTK_Buttons :
        Inits our main windows buttons to be used.
    '''
    def init_GUI_TTK_Buttons(self, root, style) -> None:
        
        #configure our buttons fonts
        style.configure("ButtonDesign1.Toolbutton", font="Helvetica 20 bold", anchor="center")

        #map the styles for buttons, for each action
        style.map("ButtonDesign1.Toolbutton",   
                    background=[('active', 'AntiqueWhite2'), 
                                ('pressed', 'white'),
                                ('disabled', 'AntiqueWhite'),
                                ('!disabled', "AntiqueWhite")],
                    foreground=[('active', 'RoyalBlue4'),
                                ('pressed', 'black'),
                                ('disabled', 'AntiqueWhite2'),
                                ('!disabled', 'RoyalBlue2')]) #NavajoWhite4


        #hide and show camera button
        self.hide_button_main_root = ttk.Button(
                        root,
                        text="Hide Camera",
                        command=self.hide,
                        padding=(0,2),
                        width=20,
                        style="ButtonDesign1.Toolbutton"
                    )
        
        self.hide_button_main_root.grid(row=11, column=0, sticky=tk.NSEW)

        #exit app button
        self.exit_button_main_root = ttk.Button(
                        root,
                        text="Exit",
                        command=self.exit,
                        padding=(0,2),
                        width=20,
                        style="ButtonDesign1.Toolbutton"
                    )
        
        self.exit_button_main_root.grid(row=11, column=1, sticky=tk.NSEW)

        #select all_names_listbox button
        self.add_person_button = ttk.Button(
                        root,
                        text="Add Person",
                        command=self.add_person_to_facedata1,
                        padding=(0,2),
                        width=20,
                        style="ButtonDesign1.Toolbutton"
                    )
        
        self.add_person_button.grid(row=11, column=2, sticky=tk.NSEW)

        #select all_names_listbox button
        self.remove_person_button = ttk.Button(
                        root,
                        text="Remove Person",
                        command=lambda: self.remove_person_from_facedata(ENCODING_DIRECTORY),
                        padding=(0,2),
                        width=20,
                        style="ButtonDesign1.Toolbutton"
                    )
        
        self.remove_person_button.grid(row=11, column=3, sticky=tk.NSEW)

        #start stop video device
        #lets us know state of button
        self.start_device = True
        self.start_device_button_main_root = ttk.Button(
                        root,
                        text="Load Video Device",
                        command=lambda: self.init_stop_VideoDevice_button(self.start_device),
                        padding=(0,2),
                        width=20,
                        style="ButtonDesign1.Toolbutton"
                    )
        
        self.start_device_button_main_root.grid(row=10, column=0, sticky=tk.NSEW)
        
        #start face rec button
        #lets us know state of button
        self.start_facedetect = True
        self.start_facedetect_button_main_root = ttk.Button(
                        root,
                        text="Start Face Detection",
                        command=lambda: self.init_stop_facedetection_button(self.start_facedetect),
                        padding=(0,2),
                        width=20,
                        style="ButtonDesign1.Toolbutton"
                    )
        
        #hidden so not placed now
        #self.start_facedetect_button_main_root.grid(row=10, column=1, sticky=tk.NSEW)

    '''
        init_help_documentation_dialog :
        Inits our help document pop up dialog and shows how the app works.
    '''
    def init_help_documentation_dialog(self) -> None:
        self.help_documentation_page_num = 0

        #create dialog
        self.help_documentation_dialog = tk.Toplevel()
        self.help_documentation_dialog.title('Help Documentation : Help about application.')
        self.help_documentation_dialog.resizable(width=False, height=False)
        self.help_documentation_dialog.configure(bg=BACKGROUND_COLOR)

        #windows size
        dialog_width = 1400
        dialog_height = 700

        #get our centered position
        x_pos, y_pos = self.get_Window_Center_Pos(self.screen_resolution[0], self.screen_resolution[1], dialog_width, dialog_height)
        self.help_documentation_dialog.geometry(str(dialog_width) + 'x' + str(dialog_height) + '+' + str(x_pos) + '+' + str(y_pos))

        #configure columns and rows
        #setup 14 columns
        for i in range(14):
            self.help_documentation_dialog.columnconfigure(index=i, minsize=dialog_width/14, weight=1)

        #setup 10 rows
        for i in range(10):
            self.help_documentation_dialog.rowconfigure(index=i, minsize=dialog_height/10, weight=1)

        #init GUI
        self.init_help_documentation_dialog_GUI(self.help_documentation_dialog, self.style)

        #load our first page
        self.load_help_documentation_page(self.help_documentation_dialog, self.style, self.help_documentation_page_num)

        #disables root window and puts this dialog to top view
        self.root_window.attributes('-disabled', True)
        self.help_documentation_dialog.focus_set()
        self.help_documentation_dialog.attributes('-topmost', True)
        self.help_documentation_dialog.update()
        self.help_documentation_dialog.attributes('-topmost', False)
        self.help_documentation_dialog.update()

        #capture close event
        self.help_documentation_dialog.protocol("WM_DELETE_WINDOW", self.exit_help_documentation_dialog)

    '''
        init_help_documentation_dialog_GUI :
        Inits the GUI for help documentaion dialog
    '''
    def init_help_documentation_dialog_GUI(self, root, style) -> None:
        #image label
        self.dialog_helpdoc_image_label = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_helpdoc_image_label.grid(row=0, column=0, rowspan=5, columnspan=14, sticky=tk.NSEW)#, rowspan=6, sticky= tk.N)
        self.dialog_helpdoc_image_label.config(text='', anchor='center')

        #RIGHT LABELS
        #label1 right
        self.dialog_helpdoc_right_label1 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_helpdoc_right_label1.grid(row=5, column=7, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        self.dialog_helpdoc_right_label1.config(text='1.', anchor='center')

        #label2 right
        self.dialog_helpdoc_right_label2 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_helpdoc_right_label2.grid(row=6, column=7, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        self.dialog_helpdoc_right_label2.config(text='2', anchor='center')

        #label3 right
        self.dialog_helpdoc_right_label3 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_helpdoc_right_label3.grid(row=7, column=7, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        self.dialog_helpdoc_right_label3.config(text='3', anchor='center')

        #label4 right
        self.dialog_helpdoc_right_label4 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_helpdoc_right_label4.grid(row=8, column=7, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        self.dialog_helpdoc_right_label4.config(text='4', anchor='center')

        #BOTTOM LABELS
        #label1 bottom
        self.dialog_helpdoc_bottom_label1 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_helpdoc_bottom_label1.grid(row=5, column=1, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        self.dialog_helpdoc_bottom_label1.config(text='B1', anchor='center')

        #label2 bottom
        self.dialog_helpdoc_bottom_label2 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_helpdoc_bottom_label2.grid(row=6, column=1, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        self.dialog_helpdoc_bottom_label2.config(text='B2', anchor='center')

        #label3 bottom
        self.dialog_helpdoc_bottom_label3 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_helpdoc_bottom_label3.grid(row=7, column=1, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        self.dialog_helpdoc_bottom_label3.config(text='B3', anchor='center')

        #label4 bottom
        self.dialog_helpdoc_bottom_label4 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_helpdoc_bottom_label4.grid(row=8, column=1, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        self.dialog_helpdoc_bottom_label4.config(text='B4', anchor='center')

        #BUTTONS
        #back button
        self.helpdoc_back_button = ttk.Button(root, text="Back", padding=(0,2), command=self.back_button_help_documentation_page, style="ButtonDesign1.Toolbutton")
        self.helpdoc_back_button.grid(row=9, column=0, rowspan=1, columnspan=2, sticky=tk.NSEW)

        #create our next Button
        self.helpdoc_next_button  = ttk.Button(root, text="Next", padding=(0,2), command=self.next_button_help_documentation_page, style="ButtonDesign1.Toolbutton")
        self.helpdoc_next_button.grid(row=9, column=2, rowspan=1, columnspan=2, sticky=tk.NSEW)

        #create our done Button
        done_button = ttk.Button(root, text="Done", padding=(0,2), command=self.exit_help_documentation_dialog, style="ButtonDesign1.Toolbutton")
        done_button.grid(row=9, column=8, rowspan=1, columnspan=2, sticky=tk.NSEW)
    '''
        back_button_help_documentation_page :
        Used to go back a page (help doc pages) on help doc dialog
    '''
    def back_button_help_documentation_page(self) -> None:
        #make sure we can go back a page and then load it
        if self.help_documentation_page_num > 0:
            self.help_documentation_page_num -=1
            self.load_help_documentation_page(self.help_documentation_dialog, self.style, self.help_documentation_page_num)

    '''
        next_button_help_documentation_page :
        Use to go to the next page (help doc pages) on help doc dialog
    '''
    def next_button_help_documentation_page(self) -> None:
        #make sure we can go ahead a page and then load it
        if self.help_documentation_page_num < 10:
            self.help_documentation_page_num += 1
            self.load_help_documentation_page(self.help_documentation_dialog, self.style, self.help_documentation_page_num)

    '''
        load_help_documentation_page :
        Send in the page number and it will load the details of that page. Will not go under 0 or over the max pages.
        Uses directory HELP_IMAGES_DIRECTORY and images HELP_IMAGES[page number here (page_num)]
    '''
    def load_help_documentation_page(self, root, style, page_num) -> None:
        
        #First page
        if page_num == 0:
            #hide back button
            self.helpdoc_back_button.grid_forget()

            #now load our page0 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 600)

            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='Upper right area, is for data of a person selected.', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='Dates and Times : Shows when they were seen.', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='Current Visitors : Shows known people currently seen, by camera.', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='Known People : Shows a list of current known people to track.', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='Load Video Device : Will let you choose an input video device (camera).', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='Hide Camera : Will switch between hiding and showing active camera.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='Exit : Will close the application', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='Add Person : Will add a new person to track. Remove Person : Will remove a known person from tracking.', anchor='center')

        elif page_num == 1:
            #show back button
            self.helpdoc_back_button .grid(row=9, column=0, rowspan=1, columnspan=2, sticky=tk.NSEW)

            #now load our page1 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 600)

            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='ID : Their identification number.', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='Dates and Times : Shows a list of the dates, times and total time there in minutes.', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='Upper right area shows the person selecteds information.', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='Name : Who they are.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='Info : A brief description about them.', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='The last time they were seens starting date time and ending date time.', anchor='center')
        elif page_num == 2:
            #now load our page2 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 600)
            
            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='Run : Start Face Detection : Usable when camera is on. Detects faces and alerts known people.', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='Run : Stop Face Detection : Will stop detecting faces.', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='Help : Help Documentation : Help documentation, you are currently reading.', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='Help : About : Information about this application.', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='File : Exit : Will exit the application.', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='Run : Load Video Device : Will let you choose an input video device (camera).', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='Run : Stop Video Device : Will stop video from the camera and close Face Detection (if running).', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='', anchor='center')

        elif page_num == 3:
            #now load our page3 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 550)
            
            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='Select the input video device : Input video devices (cameras) currently available.', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='It will refresh and check for any new devices you connect.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='Select the device and press Okay or press Cancel to back out.', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='', anchor='center')
        elif page_num == 4:
            #now load our page4 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 600)

            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='Black Box : This is where your input video will be showing.', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='Stop Video Device (Button or File Menu) : Will stop your input video AND face detection, if it is running.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='Start Face Detection (Button or Run Menu): You may now start detecting faces.', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='', anchor='center')
        elif page_num == 5:
            #now load our page5 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 600)
            
            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='Current Visitors : These are the current known people who the face detection has seen recently.', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='Clicking on a current visitor, will show information about this current visit.', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='Face Detection is currently running and looking for faces and known people.', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='Stop Face Detection (Button or Run Menu) : Will stop detecting faces.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='', anchor='center')
        elif page_num == 6:
            #now load our page6 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 600)
            
            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='Note : There must be 1 and only 1 face in the file or camera.', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='If there is no face or more than 1 face, you will receive an error.', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='Also, when using a file, you must use an image file or receive an error.', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='Select how you wish to add a new person.', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='Face from file : Will open file select.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='Face from camera : Will open an option to select an input video device to use.', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='Select Okay when an option is choosen or Cancel to leave.', anchor='center')
        elif page_num == 7:
            #now load our page7 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 375)
            
            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='Select the input video device : Input video devices (cameras) currently available.', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='It will refresh and check for any new devices you connect.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='Select the device and press Okay or press Back to go back to File or Camera selection.', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='', anchor='center')
        elif page_num == 8:
            #now load our page8 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 300)

            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='Okay : Once a valid face is taken, it will be enabled. Press it to move on.', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='Cancel : Closes out everything and goes back to the main application screen.', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='This will record from your input video device (camera).', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='Start : Starts a countdown, to take a picture of a face. Must be 1 face only.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='Back : Will go back to the input video device selection.', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='', anchor='center')
        elif page_num == 9:
            #show button
            self.helpdoc_next_button.grid(row=9, column=2, rowspan=1, columnspan=2, sticky=tk.NSEW)

            #now load our page9 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 300)
            
            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='Okay : Press the Okay button, when you are satisfied with the picture results.', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='This will move onto entering details about this person.', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='This shows what the countdown will look like, once Start is pressed.', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='Please make sure to have one face and only one face in the screen.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='If you do not, it will not work and give you an error.', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='', anchor='center')
        elif page_num == 10:
            #hide button
            self.helpdoc_next_button.grid_forget()

            #now load our page10 image
            img_file = os.path.join(HELP_IMAGES_DIRECTORY, HELP_IMAGES[page_num])
            #load image
            img = cv2.imread(img_file)            
            self.update_image_person_profile_dialog_frame(img, self.dialog_helpdoc_image_label, 300)
            
            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='Black Box : Will be the picture of the person, you choose (from file or camera).', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='Okay : Press, once you have entered all information. It will then add this person.', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='Cancel : Will close out everything. You will need to start over, if you choose this.', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='Enter the details about the person.', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='Name : Enter a name, up to 100 characters long.', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='Description : Enter a brief description, up to 50 characters long.', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='ID : This is a unique id and is automatically generated, for every person created.', anchor='center')
        #left here, incase need extra page
        elif page_num == 11:
            #hide button
            self.helpdoc_next_button.grid_forget()

            #update labels
            #RIGHT
            self.dialog_helpdoc_right_label1.config(text='', anchor='center')
            self.dialog_helpdoc_right_label2.config(text='', anchor='center')
            self.dialog_helpdoc_right_label3.config(text='', anchor='center')
            self.dialog_helpdoc_right_label4.config(text='', anchor='center')

            #BOTTOM
            self.dialog_helpdoc_bottom_label1.config(text='', anchor='center')
            self.dialog_helpdoc_bottom_label2.config(text='', anchor='center')
            self.dialog_helpdoc_bottom_label3.config(text='', anchor='center')
            self.dialog_helpdoc_bottom_label4.config(text='', anchor='center')

    '''
        exit_help_documentation_dialog :
        Used to exit the help doc dialog
    '''
    def exit_help_documentation_dialog(self) -> None:
        #re-enable the main window
        self.root_window.attributes('-disabled', False)

        #destroy this window
        self.help_documentation_dialog.destroy()

        #set window to top most window and the focus
        self.root_window.attributes('-topmost', True)
        self.root_window.update()
        self.root_window.attributes('-topmost', False)
        self.root_window.update()

    '''
        init_help_about_dialog :
        Used to init our about dialog
    '''
    def init_help_about_dialog(self) -> None:
        #create dialog
        self.help_about_dialog = tk.Toplevel()

        self.help_about_dialog.title('About App')
        self.help_about_dialog.attributes('-toolwindow', 1)
        self.help_about_dialog.resizable(width=False, height=False)
        self.help_about_dialog.configure(bg=BACKGROUND_COLOR)

        #windows size
        dialog_width = 400
        dialog_height = 300

        #get our centered position
        x_pos, y_pos = self.get_Window_Center_Pos(self.screen_resolution[0], self.screen_resolution[1], dialog_width, dialog_height)
        self.help_about_dialog.geometry(str(dialog_width) + 'x' + str(dialog_height) + '+' + str(x_pos) + '+' + str(y_pos))

        #configure columns and rows
        #setup 8 columns
        for i in range(8):
            self.help_about_dialog.columnconfigure(index=i, minsize=dialog_width/8, weight=1)

        #setup 5 rows
        for i in range(5):
            self.help_about_dialog.rowconfigure(index=i, minsize=dialog_height/5, weight=1)

        self.init_help_about_dialog_GUI(self.help_about_dialog, self.style)

        #capture close event
        self.help_about_dialog.protocol("WM_DELETE_WINDOW", self.okay_help_about_dialog)

        #disables root window and puts to top about dialog
        self.root_window.attributes('-disabled', True)
        self.help_about_dialog.focus_set()
        self.help_about_dialog.attributes('-topmost', True)
        self.help_about_dialog.update()
        self.help_about_dialog.attributes('-topmost', False)
        self.help_about_dialog.update()

    '''
        init_help_about_dialog_GUI :
        Used to init help about dialogs GUI
    '''
    def init_help_about_dialog_GUI(self, root, style) -> None:
        #label1 description
        dialog_description_label1 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        dialog_description_label1.grid(row=1, column=1, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        dialog_description_label1.config(text='Beta App Version : ...', anchor='center')

        #label2 description
        dialog_description_label2 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        dialog_description_label2.grid(row=2, column=1, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        dialog_description_label2.config(text='Date Created : 2/2024', anchor='center')

        #label3 description
        dialog_description_label3 = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        dialog_description_label3.grid(row=3, column=1, rowspan=1, columnspan=6, sticky=tk.W)#, rowspan=6, sticky= tk.N)
        dialog_description_label3.config(text='Created by : Christian Merriman', anchor='center')

        #create our Okay Button
        okay_button = ttk.Button(root, text="Okay", padding=(0,2), command=self.okay_help_about_dialog, style="ButtonDesign1.Toolbutton")
        okay_button.grid(row=4, column=6, rowspan=1, columnspan=2, sticky=tk.NSEW)

    '''
        okay_help_about_dialog :
        This will close the about dialog, when pressed. Goes back to root window.
    '''
    def okay_help_about_dialog(self) -> None:
        #re-enable the main window
        self.root_window.attributes('-disabled', False)

        #destroy this window
        self.help_about_dialog.destroy()

        #set window to top most window and the focus
        self.root_window.attributes('-topmost', True)
        self.root_window.update()
        self.root_window.attributes('-topmost', False)
        self.root_window.update()

    '''
        init_stop_VideoDevice_button :
        Used for initializing the video device and stop and closing it.
    '''
    def init_stop_VideoDevice_button(self, startDevice) -> None:
        #lets us know if we are starting or stopping device
        if startDevice:
            self.init_VideoDevice_Dialog(self.root_window, self.style, False)
        else:
            self.stop_Webcam_Device()

    '''
        init_stop_facedetection_button :
        Used for starting and stopping facial detection.
    '''
    def init_stop_facedetection_button(self, startDetect) -> None:
        if startDetect:
            self.start_Facial_Recognition()
        else:
            self.stop_Facial_Recognition(True)

    '''
        init_VideoDevice_Dialog :
        Creates the dialog that will let you choose the video input option.
    '''
    def init_VideoDevice_Dialog(self, root, style, addPerson) -> None:
        self.addPerson_Device = addPerson

        self.videoDevice_Dialog = tk.Toplevel()

        self.videoDevice_Dialog.title('Video Device Loader')
        self.videoDevice_Dialog.resizable(width=False, height=False)
        self.videoDevice_Dialog.configure(bg=BACKGROUND_COLOR)

        #windows size
        dialog_width = 400
        dialog_height = 300

        #get our centered position
        x_pos, y_pos = self.get_Window_Center_Pos(self.screen_resolution[0], self.screen_resolution[1], dialog_width, dialog_height)

        self.videoDevice_Dialog.geometry(str(dialog_width) + 'x' + str(dialog_height) + '+' + str(x_pos) + '+' + str(y_pos))

        #configure columns and rows
        #setup 2 columns
        for i in range(2):
            self.videoDevice_Dialog.columnconfigure(index=i, minsize=dialog_width/2, weight=1)

        #setup 5 rows
        for i in range(5):
            self.videoDevice_Dialog.rowconfigure(index=i, minsize=dialog_height/5, weight=1)

        #create the GUI
        self.init_VideoDevice_Dialog_GUI(self.videoDevice_Dialog, style, root)
        


        self.videoDevice_Dialog.focus_set()
        if not self.addPerson_Device:
            root.attributes('-disabled', True)
        self.videoDevice_Dialog.attributes('-topmost', True)
        self.videoDevice_Dialog.update()
        self.videoDevice_Dialog.attributes('-topmost', False)
        self.videoDevice_Dialog.update()

        #label = tk.Label(self.videoDevice_Dialog, text="Hello World!")
        #label.pack(fill='x', padx=50, pady=5)

        #button_close = tk.Button(self.videoDevice_Dialog, text="Close", command=self.videoDevice_Dialog.destroy)
        #button_close = tk.Button(self.videoDevice_Dialog, text="Close", command=self.exit_VideoDevice_Dialog)
        #button_close.pack(fill='x')

        #capture close event
        self.videoDevice_Dialog.protocol("WM_DELETE_WINDOW", lambda: self.exit_VideoDevice_Dialog(mainRoot=root))

        self.videoDevice_Dialog_Active = True

        self.videoDevice_Dialog.after(1000, self.refresh_VideoDevice_listbox)

    '''
        init_VideoDevice_Dialog_GUI :
        Setup GUI for dialog.
    '''
    def init_VideoDevice_Dialog_GUI(self, root, style, mainRoot) -> None:

        #label description
        self.dialog_description_label = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_description_label.grid(row=0, column=0, rowspan=1, columnspan=2, sticky=tk.NSEW)#, rowspan=6, sticky= tk.N)
        self.dialog_description_label.config(text='Select the input video device, you wish to use :', anchor='center')

        #create our listbox
        self.device_input_list = self.check_Input_Devices()
        #self.names_listbox = tk.Listbox(self.main_window, height=5, listvariable=tk.Variable(value=tmplist), selectmode=tk.SINGLE)
        self.dialog_devicelist_listbox = tk.Listbox(root, height=3, selectmode=tk.SINGLE, listvariable=tk.Variable(value=self.device_input_list))
        #self.names_listbox.place(x=750,y=115, width=250, height=50)
        self.dialog_devicelist_listbox.bind('<<ListboxSelect>>', self.videoDevice_Listbox_Selectlist)
        
        self.dialog_devicelist_listbox_scrollbar = tk.Scrollbar(self.dialog_devicelist_listbox, orient=tk.VERTICAL, bg=BACKGROUND_COLOR)  
        self.dialog_devicelist_listbox.config(yscrollcommand=self.dialog_devicelist_listbox_scrollbar.set)
        self.dialog_devicelist_listbox_scrollbar.config(command=self.dialog_devicelist_listbox.yview)

        self.dialog_devicelist_listbox.grid(padx=5, pady=5, row=1, column=0, rowspan=3, columnspan=2, sticky=tk.NSEW)
        #self.names_listbox_scrollbar.grid(row=3, column=1, sticky=tk.W)
        self.dialog_devicelist_listbox_scrollbar.pack(side=tk.RIGHT, fill= tk.Y)

        #create our Okay Button
        okay_button = ttk.Button(root, text="Okay", padding=(0,2), command=lambda: self.okay_VideoDevice_Dialog(mainRoot=mainRoot), style="ButtonDesign1.Toolbutton")
        okay_button.grid(row=4, column=0, rowspan=1, columnspan=1, sticky=tk.NSEW)

        #create our Cancel button
        if self.addPerson_Device:
            cancel = "Back"
        else:
            cancel = "Cancel"
        button_cancel = ttk.Button(root, text=cancel, padding=(0,2), command=lambda: self.exit_VideoDevice_Dialog(mainRoot=mainRoot), style="ButtonDesign1.Toolbutton")
        button_cancel.grid(row=4, column=1, rowspan=1, columnspan=1, sticky=tk.NSEW)

    '''
        init_Known_Facial_Data :
        Loads a database of known faces, with pandas.
    '''
    def init_Known_Facial_Data(self, data_dir, createFile2) -> None:
        #load facial data here
        #array that stores current known faces
        self.current_faces = []
        self.current_faces_lock = Lock()
        

        # Get known faces image and labels, descriptions and unique ids
        self.images, self.labels, self.descriptions, self.unique_ids = face_data.load_face_data(data_dir)

        self.df1, self.df2 = face_data.load_update_pandas_db(PANDAS_FILENAME1, PANDAS_FILENAME2, self.labels, self.descriptions, self.unique_ids, createFile2)
        
        #update list
        self.update_all_names_listbox()

        print(self.df1)
        print(self.df2)

        #encode our known people
        self.face_encodings, self.face_names = face_data.encode_known_people(self.images, self.labels)

    '''
        release_Known_Facial_Data :
        Closes the face pandas dbs.
    '''
    def release_Known_Facial_Data(self) -> None:
        #close dataframes
        if 'df1' in self.__dict__:
            del self.__dict__['df1']
            #clear mem
            gc.collect()

        if 'df2' in self.__dict__:
            del self.__dict__['df2']
            #clear mem
            gc.collect()

        #remove data on known people
        if 'images' in self.__dict__:
            del self.__dict__['images']

        if 'labels' in self.__dict__:
            del self.__dict__['labels']

        if 'descriptions' in self.__dict__:
            del self.__dict__['descriptions']

        if 'unique_ids' in self.__dict__:
            del self.__dict__['unique_ids']

        #clear listbox
        self.all_names_listbox.delete(0, tk.END)
        self.root_window.update()

    '''
        update_panda_dataframe2 :
        Updates our pandas database for the face we have seen. It will calculate the total time they were seen for, by when we first to last saw them.
    '''
    def update_panda_dataframe2(self, dataframe, id, start_time, end_time, filename) -> None:
        
        #calculate total time in seconds
        totaltime = end_time - start_time

        #create dataframe and concat to current (Total time stored in seconds. Will be convertable later)
        df = pd.DataFrame(list(zip([id], [start_time], [end_time], [totaltime.seconds])), columns=['UUID', 'Arrival Time', 'Departure Time', 'Total Time'] ) 
        df.set_index(['UUID'], inplace=True)
        self.df2 = pd.concat([dataframe, df])

        #update file
        self.df2.to_csv(filename)

    '''
        update_all_names_listbox :
        Updates the known facial names, to be displayed on our listbox.
    '''
    def update_all_names_listbox(self) -> None:
        #check for current selection
        #get selected listbox item
        index = self.all_names_listbox.curselection()

        value = None

        if index:
            # get the value at the selected index
            value = self.all_names_listbox.get(index[0])

        #clear listbox
        self.all_names_listbox.delete(0, tk.END)

        #update listbox with dataframe1
        self.update_all_names_listbox_with_df1()

        #select item
        if value:
            self.all_names_listbox.select_set(index)

    '''
        update_all_names_listbox_with_df1 :
        Will get the names from df1 and insert to listbox.
    '''
    def update_all_names_listbox_with_df1(self) -> None:
        #get all of our df1 names to a list
        names = self.df1['Name'].to_list()

        #go through names and add to listbox
        for name in names:
            self.all_names_listbox.insert(tk.END, name)

    '''
        update_all_names_listbox_with_df2 :
        Old function for updating listbox.
    '''
    def update_all_names_listbox_with_df2(self) -> None:
        ids = self.df2.index.to_list()
        arrival = self.df2['Arrival Time'].to_list()

        #go through are variables to add to listbox
        for id, arrive in zip(ids, arrival):
            #get name and create a string to display name and arrival time
            index = self.unique_ids.index(id)            
            name = ''

            if index >= 0:
                name = self.labels[index]

            text = name + ' & Time : ' + str(arrive)
            self.all_names_listbox.insert(tk.END, text)
        

    '''
        start_Facial_Recognition :
        Used to start the multiprocessing for detecting faces. Uses multiprocessing, so the video capturing does not slow down and it can detect whose face it is, on the other core.
    '''
    def start_Facial_Recognition(self) -> None:

        #disable menu start
        self.root_run_menu.entryconfig('Start Face Detection' , state='disabled')
        self.start_facedetect_button_main_root['state'] = 'disabled'
        

        self.face_check_run = False

        self.last_face_count = 0
        self.time_check = -1
        self.time_seconds_check = 1

        #create 2 queues for sending data in and out of our class and then init loop facecheck class
        self.data_in_queue = multiprocessing.Queue()
        self.data_out_queue = multiprocessing.Queue()
        self.app_loop_face = face_data.AppLoopFaceCheck(self.data_in_queue, self.data_out_queue, 
                                                        self.face_encodings, self.face_names, 
                                                        self.images, self.descriptions, 
                                                        self.unique_ids)
        
        #now start it
        self.app_loop_face.start()

        #change button to stop
        self.start_facedetect = False
        self.start_facedetect_button_main_root.config(text='Stop Face Detection')
        self.start_facedetect_button_main_root['state'] = 'normal'
        

        #enable menu stop
        self.root_run_menu.entryconfig('Stop Face Detection' , state='normal')

    '''
        stop_Facial_Recognition :
        Will stop facial recognition, by making sure we close our multiprocesses as well.
    '''
    #send in True or False to let us know if we should enable Start menu
    def stop_Facial_Recognition(self, enableStart) -> None:

        #disable menu stop
        self.root_run_menu.entryconfig('Stop Face Detection' , state='disabled')
        
        #make sure we arent checking for faces
        while self.face_check_run:
            pass

        #stop it and remove it
        if 'app_loop_face' in self.__dict__ :            
            self.app_loop_face.stop()
            del self.__dict__['app_loop_face']

        #sleep to make sure app_loop_face is closed before we do rest of closing
        time.sleep(.01)

        #make sure we arent checking for faces again
        while self.face_check_run:
            pass

        #stop out queue and remove it
        if 'data_out_queue' in self.__dict__ :
            #empty queue
            while not self.data_out_queue.empty():
                garb = self.data_out_queue.get()
            
            #close and delete from dict
            self.data_out_queue.close()
            del self.__dict__['data_out_queue']

        #stop in queue and remove it
        if 'data_in_queue' in self.__dict__ :  
            #empty queue
            while not self.data_in_queue.empty():
                garb = self.data_in_queue.get()
            
            #close and delete from dict
            self.data_in_queue.close()
            del self.__dict__['data_in_queue']

        #clear current faces list
        with self.current_faces_lock:
            self.current_faces.clear()

        #clear the listbox and data labels
        self.names_listbox.delete(0, tk.END)
        self.clear_data_labels()

        #enable menu start
        if enableStart:
            #update button
            self.start_facedetect = True
            self.start_facedetect_button_main_root.config(text='Start Face Detection')


            self.root_run_menu.entryconfig('Start Face Detection' , state='normal')
            

    '''
        refresh_VideoDevice_listbox :
        Reloads GUIs listbox.
    '''
    def refresh_VideoDevice_listbox(self) -> None:
            
            #make sure this dialog is active
            if self.videoDevice_Dialog_Active:

                #get video inputs
                input_list = self.check_Input_Devices()

                #make sure its different
                if self.device_input_list != input_list:

                    #get selected listbox item
                    index = self.dialog_devicelist_listbox.curselection()

                    value = None

                    if index:
                        # get the value at the selected index
                        value = self.dialog_devicelist_listbox.get(index)
                    
                    #clear current list and then update it
                    self.device_input_list.clear()
                    self.device_input_list = input_list.copy()

                    #clear listbox
                    self.dialog_devicelist_listbox.delete(0, tk.END)

                    #repopulate listbox
                    for input in input_list:
                        self.dialog_devicelist_listbox.insert(tk.END, input)

                    #now reselect old selected value, if needed
                    if value:
                        #if values in list, get index and select in listbox
                        if value in self.device_input_list:
                            val_index = self.device_input_list.index(value)
                            self.dialog_devicelist_listbox.select_set(val_index)

                #check again in a certain time
                self.videoDevice_Dialog.after(1000, self.refresh_VideoDevice_listbox)

    '''
        videoDevice_Listbox_Selectlist :
        Used for testing selection.
    '''
    def videoDevice_Listbox_Selectlist(self, event) -> None:
        selection = event.widget.curselection()
        if selection:
            index = int(selection[0])
            value = event.widget.get(index)
            print('Value')
            print(value)

    '''
        okay_VideoDevice_Dialog :
        Used for testing selection of input video device.
    '''
    def okay_VideoDevice_Dialog(self, mainRoot, event=None) -> None:
        
        #get selected listbox item
        index = self.dialog_devicelist_listbox.curselection()

        #if we have a selection
        if index:
            # get the value at the selected index
            value = self.dialog_devicelist_listbox.get(index[0])
            print(value)
            if not self.addPerson_Device :
                self.device_num = index[0]
            else:
                self.device_num_addPerson = index[0]

            self.exit_VideoDevice_Dialog(mainRoot=mainRoot)
        #nothing selected, so let user know to select a device and press okay and then reset focus to dialog
        else:
            print('Nothing Selected!')
            messagebox.showwarning('No Device Selected!', 'Please select a device and then press the Okay button.')
            
            #reset the focus to video device dialog, after the messagebox is done
            self.videoDevice_Dialog.focus_set()
            self.videoDevice_Dialog.attributes('-topmost', True)
            self.videoDevice_Dialog.update()
            self.videoDevice_Dialog.attributes('-topmost', False)
            self.videoDevice_Dialog.update()
        
    '''
        exit_VideoDevice_Dialog :
        Checks for type of exit from device selection. Options noted below.
    '''
    def exit_VideoDevice_Dialog(self, mainRoot, event=None) -> None:
        #disable
        self.videoDevice_Dialog_Active = False
        #re-enable the main window
        if not self.addPerson_Device:
            mainRoot.attributes('-disabled', False)
        #self.root_window.attributes('-disabled', False)
        #destroy this window
        self.videoDevice_Dialog.destroy()

        #set window to top most window and the focus
        if not self.addPerson_Device:
            mainRoot.attributes('-topmost', True)
            mainRoot.update()
            mainRoot.attributes('-topmost', False)
            mainRoot.update()

        #self.root_window.attributes('-topmost', True)
        #self.root_window.update()
        #self.root_window.attributes('-topmost', False)
        #self.root_window.update()

        #if we have a device, lets load our video
        if not self.addPerson_Device and self.device_num >= 0:
            self.init_WebCam_Device(self.webcam_label)
        #if we have a device and we are adding a person, lets go and load it
        elif self.addPerson_Device and self.device_num_addPerson >= 0:
            #load the camera face capture dialog
            self.init_camera_face_capture_dialog(self.root_window, self.style, self.device_num_addPerson)
        #if we did not have a device and are on adding a person, that means we hit cancel, to go back
        elif self.addPerson_Device:
            #load addPerson dialog
            self.init_addperson_to_facedata1(self.root_window, self.style)

    '''
        init_camera_face_capture_dialog :
        Used to capture the face of a person, we wish to learn for our db.
    '''
    def init_camera_face_capture_dialog(self, root, style, deviceNum) -> None:

        self.camera_face_cap_Dialog = tk.Toplevel()

        self.camera_face_cap_Dialog.title('Camera Face Capture')
        self.camera_face_cap_Dialog.resizable(width=False, height=False)
        self.camera_face_cap_Dialog.configure(bg=BACKGROUND_COLOR)

        #windows size
        dialog_width = 800
        dialog_height = 800

        #get our centered position
        x_pos, y_pos = self.get_Window_Center_Pos(self.screen_resolution[0], self.screen_resolution[1], dialog_width, dialog_height)

        self.camera_face_cap_Dialog.geometry(str(dialog_width) + 'x' + str(dialog_height) + '+' + str(x_pos) + '+' + str(y_pos))

        #configure columns and rows
        #setup 6 columns
        for i in range(6):
            self.camera_face_cap_Dialog.columnconfigure(index=i, minsize=dialog_width/6, weight=1)

        #setup 10 rows
        for i in range(10):
            self.camera_face_cap_Dialog.rowconfigure(index=i, minsize=dialog_height/10, weight=1)

        #create the GUI
        self.init_camera_face_capture_dialog_GUI(self.camera_face_cap_Dialog, style)       

        self.camera_face_cap_Dialog.focus_set()
        self.camera_face_cap_Dialog.attributes('-topmost', True)
        self.camera_face_cap_Dialog.update()
        self.camera_face_cap_Dialog.attributes('-topmost', False)
        self.camera_face_cap_Dialog.update()


        #capture close event
        self.camera_face_cap_Dialog.protocol("WM_DELETE_WINDOW", self.exit_camera_face_capture_dialog)

        #init webcam
        if self.init_camera_face_capture_webcam(self.camera_face_cap_Dialog, self.faceCapture_webcam_label):
            #process webcam
            self.process_camera_face_capture_webcam(self.faceCapture_webcam_label)

            #enable start button
            self.cam_start_button['state'] = 'normal'

    '''
        init_camera_face_capture_dialog_GUI :
        Inits GUI for init_camera_face_capture_dialog.
    '''
    def init_camera_face_capture_dialog_GUI(self, root, style) -> None:
        #label description
        self.dialog_description_label = ttk.Label(root, background=BACKGROUND_COLOR)#, style="design.TLabel")
        self.dialog_description_label.grid(row=0, column=0, rowspan=1, columnspan=6, sticky=tk.NSEW)#, rowspan=6, sticky= tk.N)
        self.dialog_description_label.config(text='Line your face up in the view and press start.', anchor='center')
        
        #label for webcam
        self.faceCapture_webcam_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.faceCapture_webcam_label.grid(row=1, column=1, rowspan=5, columnspan=4, sticky= tk.NSEW)

        #create our Start Button
        self.cam_start_button = ttk.Button(root, text="Start", padding=(0,2), command= self.startCapture_camera_face_capture_dialog, style="ButtonDesign1.Toolbutton")
        self.cam_start_button.grid(row=7, column=2, rowspan=1, columnspan=2, sticky=tk.NSEW)
        self.cam_start_button['state'] = 'disable'

        #create our Back Button
        back_button = ttk.Button(root, text="Back", padding=(0,2), command= self.back_camera_face_capture_dialog, style="ButtonDesign1.Toolbutton")
        back_button.grid(row=9, column=0, rowspan=1, columnspan=1, sticky=tk.NSEW)

        #create our Okay Button
        self.camera_okay_button = ttk.Button(root, text="Okay", padding=(0,2), command= self.okay_camera_face_capture_dialog, style="ButtonDesign1.Toolbutton")
        self.camera_okay_button.grid(row=9, column=4, rowspan=1, columnspan=1, sticky=tk.NSEW)
        self.camera_okay_button['state'] = 'disabled'

        #create our Cancel button
        button_cancel = ttk.Button(root, text='Cancel', padding=(0,2), command=lambda: self.cancel_camera_face_capture_dialog(False), style="ButtonDesign1.Toolbutton")
        button_cancel.grid(row=9, column=5, rowspan=1, columnspan=1, sticky=tk.NSEW)
    
    '''
        init_camera_face_capture_webcam :
        Loads input video device to be used for capturing.
    '''
    def init_camera_face_capture_webcam(self, root, label) -> bool:
        #get our capture devices
        print(self.check_Input_Devices())# list of camera device

        if 'face_cap' not in self.__dict__:
            #update label to let us know we are loading video
            label.config(text='Loading video from ' + self.check_Input_Devices()[self.device_num_addPerson] + '...', anchor='center')      
            root.update()

            #load capture device and set initialized to true
            self.face_cap = cv2.VideoCapture(self.device_num_addPerson)

            #lets us know if webcam is processing
            self.face_webcam_processing = False

            #lets us know to stop processing webcam
            self.face_webcam_processing_stop = False       

        if 'face_cap' not in self.__dict__ or not self.face_cap.isOpened():
            #close and remove var
            if 'face_cap' in self.__dict__ :
                self.face_cap.release()
                del self.__dict__['face_cap']

            #update label
            label.config(text='', anchor='center', image='')
            root.update()

            #show error
            messagebox.showerror('No Capture Device', 'Error : No capture device found! Make sure your webcam is plugged in and enabled. Please try again.')
            print('ERROR NO VIDEO')

            #close out dialog, so send in True
            self.exit_camera_face_capture_dialog()

            return False
        
        #set countdown for start button, to take picture of face
        self.camera_countdown = False

        return True

    '''
        process_camera_face_capture_webcam :
        Will process the data from input device. There is a countdown for when it will capture the face. Follow comments for more info.
    '''
    def process_camera_face_capture_webcam(self, label) -> None:
        #if we need to stop processing webcam, then just return
        if self.face_webcam_processing_stop:
            return

        #turn on webcam process flag
        self.face_webcam_processing = True

        ret, frame = self.face_cap.read()
        
        #found video device
        if ret:
            height, width = frame.shape[:2]
            #if we are counting down
            if self.camera_countdown:
                #check to see if 1 second has passed
                if not self.check_time_diff_less(self.camera_countdown_timer, datetime.datetime.now(), 1):
                    #update timer
                    self.camera_countdown_timer = datetime.datetime.now()
                    #update count
                    self.camera_countdown_timer_count -= 1

                if self.camera_countdown_timer_count == 4:
                    font = cv2.FONT_HERSHEY_DUPLEX
                    h = int(height/2)
                    w = int(width/4)
                    #h = 200
                    w = 13
                    cv2.putText(img=frame, text='Starting Countdown For Picture', org=(w, h), fontFace=font, fontScale=1.0, color=(0, 0, 255), thickness=1)
                elif self.camera_countdown_timer_count == 3:
                    font = cv2.FONT_HERSHEY_DUPLEX
                    h = int(height/2)
                    w = int(width/2 - 68)
                    #h = 200
                    #w = 200
                    cv2.putText(img=frame, text='3', org=(w, h), fontFace=font, fontScale=1.0, color=(0, 0, 255), thickness=1)
                elif self.camera_countdown_timer_count == 2:
                    font = cv2.FONT_HERSHEY_DUPLEX
                    h = int(height/2)
                    w = int(width/2 - 68)
                    cv2.putText(img=frame, text='2', org=(w, h), fontFace=font, fontScale=1.0, color=(0, 0, 255), thickness=1)
                elif self.camera_countdown_timer_count == 1:
                    font = cv2.FONT_HERSHEY_DUPLEX
                    h = int(height/2)
                    w = int(width/2 - 68)
                    cv2.putText(img=frame, text='1', org=(w, h), fontFace=font, fontScale=1.0, color=(0, 0, 255), thickness=1)
                elif self.camera_countdown_timer_count <= 0:
                    #check to see if we have an encoded face
                    results = self.check_image_camera_face_capture_dialog(frame)

                    #only 1 face found
                    if results == 1:
                        print('face encoded')
                        self.camera_face_image = copy.deepcopy(frame)
                        self.camera_okay_button['state'] = 'normal'
                    else:
                        print('no face encoded')
                        #disable dialog
                        self.camera_face_cap_Dialog.attributes('-disabled', True)
                        
                        text = tuple()
                        if results == 0:
                            text = ('No Face Detected!', 'Please make sure one face is inside the video screen and try again.')
                        elif results == 2:
                            text = ('Too Many Faces Detected!', 'Please make sure one and only one face is inside the video screen and try again.')
                        elif results == 3:
                            text = ('Face Already Known!', 'This face is of a known person. Please use someone else.')

                        messagebox.showerror(text[0], text[1])

                        #enable dialog
                        self.camera_face_cap_Dialog.attributes('-disabled', False)
                        self.camera_face_cap_Dialog.focus_set()
                        self.camera_face_cap_Dialog.attributes('-topmost', True)
                        self.camera_face_cap_Dialog.update()
                        self.camera_face_cap_Dialog.attributes('-topmost', False)
                        self.camera_face_cap_Dialog.update()

                    #end countdown
                    self.camera_countdown = False
                    self.cam_start_button['state'] = 'normal'

            if 'camera_face_image' in self.__dict__ :
                self.most_recent_capture_arr = self.camera_face_image
                img_ = cv2.cvtColor(self.most_recent_capture_arr, cv2.COLOR_BGR2RGB)
                self.most_recent_capture_pil = Image.fromarray(img_)
                imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
                label.imgtk = imgtk
                label.configure(image=imgtk)
            else:            
                self.most_recent_capture_arr = frame
                img_ = cv2.cvtColor(self.most_recent_capture_arr, cv2.COLOR_BGR2RGB)
                self.most_recent_capture_pil = Image.fromarray(img_)
                imgtk = ImageTk.PhotoImage(image=self.most_recent_capture_pil)
                label.imgtk = imgtk
                label.configure(image=imgtk)

            label.after(15, lambda: self.process_camera_face_capture_webcam(label))

        #video device error
        else:
            messagebox.showerror('No Video Device Found!', 'Input video device cannot be found! Please check connections. Closing out.')
            #turn off webcam process flag
            self.face_webcam_processing = False
            self.exit_camera_face_capture_dialog()

        #turn off webcam process flag
        self.face_webcam_processing = False

    #will return an int about what results are.
    #int :
    #0 : Means no face found. (FAIL)
    #1 : Means 1 face found and good. (SUCCESS)
    #2 : Means more than 1 face found. (FAIL)
    #3 : Means this face is already in our encoded faces. (FAIL)
    def check_image_camera_face_capture_dialog(self, image) -> int:
        small_frame = cv2.resize(image, (0, 0), fx=0.5, fy=0.5)
        #check to see if image has 1 face
        face = face_recognition.face_encodings(cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB))

        #if we have no faces
        if len(face) == 0:
            return 0
        #if we have more than 1 face
        elif len(face) > 1:
            return 2

        #make sure we have encodings to check
        if len(self.face_encodings) > 0:
            #now check to see if face is currently in encoded faces
            results = face_recognition.compare_faces(self.face_encodings, face[0])
            face_distances = face_recognition.face_distance(self.face_encodings, face[0])
            best_match_index = np.argmin(face_distances)

            #face found, already in encoded faces
            if results[best_match_index]:
                return 3
        
        #have an encoded face
        return 1
    
    '''
        startCapture_camera_face_capture_dialog :
        Starts the facial capturing.
    '''
    def startCapture_camera_face_capture_dialog(self) -> None:
        self.cam_start_button['state'] = 'disable'
        self.camera_okay_button['state'] = 'disabled'

        #delete our image
        if 'camera_face_image' in self.__dict__ :
            del self.__dict__['camera_face_image']

        #turn on our timer
        self.camera_countdown = True

        #get start time
        self.camera_countdown_timer = datetime.datetime.now()

        #how many seconds we will countdown (start message is first second)
        self.camera_countdown_timer_count = 4
    
    '''
        okay_camera_face_capture_dialog :
        GUI okay button, for when we have captured our face.
    '''
    def okay_camera_face_capture_dialog(self) -> None:
        #close webcam if needed
        if 'face_cap' in self.__dict__ and self.face_cap.isOpened():
            self.face_cap.release()
            del self.__dict__['face_cap']
        #destroy this window
        self.camera_face_cap_Dialog.destroy()
        
        #init new profile and send in copy of image       
        self.init_person_profile_dialog(self.camera_face_image)

    '''
        back_camera_face_capture_dialog :
        GUI back button, if we want to go back to selecting a new input device.
    '''
    def back_camera_face_capture_dialog(self) -> None:
        #close webcam if needed
        if 'face_cap' in self.__dict__ and self.face_cap.isOpened():
            self.face_cap.release()
            del self.__dict__['face_cap']

        #delete our image
        if 'camera_face_image' in self.__dict__ :
            del self.__dict__['camera_face_image']
        
        #destroy this window
        self.camera_face_cap_Dialog.destroy()
        #set our device num to no device as default (-1)
        self.device_num_addPerson = -1
        #load the device dialog, addPerson is True, since we are adding
        self.init_VideoDevice_Dialog(None, self.style, True)

    '''
        cancel_camera_face_capture_dialog :
        GUI cancel button, will take us back to our main dialog.
    '''
    def cancel_camera_face_capture_dialog(self, closeOut) -> None:
        #Make sure we wish to cancel
        if not closeOut and messagebox.askokcancel("Do you wish to cancel?", "If you cancel, you will have to start over again. Are you sure?"):
            self.exit_camera_face_capture_dialog()
        else:
            self.camera_face_cap_Dialog.focus_set()
            self.camera_face_cap_Dialog.attributes('-topmost', True)
            self.camera_face_cap_Dialog.update()
            self.camera_face_cap_Dialog.attributes('-topmost', False)
            self.camera_face_cap_Dialog.update()

    '''
        exit_camera_face_capture_dialog :
        exit event to handle if they close the dialog for capturing the face.
    '''
    def exit_camera_face_capture_dialog(self) -> None:
        #close webcam if needed
        if 'face_cap' in self.__dict__ and self.face_cap.isOpened():
            self.face_cap.release()
            del self.__dict__['face_cap']

        #delete our image
        if 'camera_face_image' in self.__dict__ :
            del self.__dict__['camera_face_image']
        
        #re-enable the main window
        self.root_window.attributes('-disabled', False)
        #destroy this window
        self.camera_face_cap_Dialog.destroy()

        #set window to top most window and the focus
        self.root_window.attributes('-topmost', True)
        self.root_window.update()
        self.root_window.attributes('-topmost', False)
        self.root_window.update()

    '''
        start :
        This will start to run out apps main loop.
    '''
    def start(self) -> None:
        self.webcam_label.config(text='', anchor='center')
        self.root_window.mainloop()

    '''
        hide :
        Hides and shows camera view.
    '''
    def hide(self) -> None:        
        #will hide or show webcam
        if self.show_cam:
            self.show_cam = False
            self.hide_button_main_root.config(text='Show Camera')            
        else:
            self.show_cam = True
            self.hide_button_main_root.config(text='Hide Camera')            

    '''
        exit :
        Handles closing our app.
    '''
    def exit(self) -> None:
        if 'cap' in self.__dict__ and self.cap.isOpened():
            self.cap.release()

        #make sure we save anything thats left in listbox for current visitors
        self.check_names_listbox_remove(0)

        cv2.destroyAllWindows()
        self.root_window.destroy()

    '''
        names_listbox_select :
        Fills the list box with active people that have recently been seen.
    '''
    def names_listbox_select(self, event):
        #selection = event.widget.curselection()
        selection = self.names_listbox.curselection()
        if selection:
            index = int(selection[0])
            #value = event.widget.get(index)
            value = self.names_listbox.get(index)
            print('Value')
            print(value)

            #find the string
            i = self.labels.index(value)

            #now get indexes for our list of people
            indexes = self.df1.index.to_list()
            #now use the index of UUID (person.name. DONT BE CONFUSED. the .name is part of pandas for index key) 
            #and then get the 'Name' of the person
            pos = indexes.index(self.unique_ids[i])
            person = self.df1.iloc[pos]

            #make sure its in the range of our image array and then update frame with image
            if i in range(len(self.images)):
                self.fill_image_datetime_table(self.unique_ids[i])
                self.update_image_frame(self.images[i][0], value)
                self.image_uid_label.config(text='ID : ' + str(self.unique_ids[i]))
                #self.image_description_label.config(text='Info : ' + self.descriptions[i])

                #had to use dataframe or it moves it into different position on label
                self.image_description_label.config(text='Info : ' + person['Description'])
                firsttime, lasttime = self.get_first_last_seen(self.unique_ids[i])
                seen_text = "First Seen : " + str(firsttime)
                seen_text = seen_text[:seen_text.index('.')]
                self.image_first_seen_label.config(text=seen_text)
                seen_text = "Last Seen : " + str(lasttime)
                seen_text = seen_text[:seen_text.index('.')]
                self.image_last_seen_label.config(text=seen_text)

    '''
        get_first_last_seen :
        Gets when seen first and last time.
    '''
    def get_first_last_seen(self, id):
        first = None
        last = None
        with self.current_faces_lock:
            for face in self.current_faces:
                if face.id == id:
                    first = face.date_time_first
                    last = face.date_time_last

        return first, last
    
    '''
        remove_person_from_facedata :
        Removes them from out database.
    '''
    def remove_person_from_facedata(self, data_dir) -> None:

        if 'app_loop_face' in self.__dict__:
            if messagebox.askyesno('Facial Recognition Running', 'You need to stop running facial recognition. Do you wish to continue?'):
                #if we need to stop face detection
                self.stop_Facial_Recognition(True)
            #they said no, so exit out
            else:
                #set window to top most window and the focus
                self.root_window.attributes('-topmost', True)
                self.root_window.update()
                self.root_window.attributes('-topmost', False)
                self.root_window.update()
                return

        #get current selected person
        index = self.all_names_listbox.curselection()

        #make sure they have someone selected
        if not index:
            messagebox.showwarning('No Person Selected!', 'You must select a person, from our Known People list box.')      
        
        #someone is selected, so make sure they wish to delete this person
        elif messagebox.askyesno('PERSON DELETION WARNING!!!', 'Are you sure, that you wish to delete this person?'):

            #get the person at this location
            person = self.df1.iloc[index[0]]

            #now get indexes for our list of people
            #indexes = self.df1.index.to_list()

            #now use the index of UUID (person.name. DONT BE CONFUSED. the .name is part of pandas for index key) 
            uid = str(person.name)

            #now delete this uid from dataFrames
            #make sure index is in df2
            indexes = self.df2.index.to_list()
            indexes = set(indexes)

            #if id is in df2, then remove it
            if uid in indexes:
                self.df2.drop(index=[uid], inplace=True)   
                     
            self.df1.drop(index=[uid], inplace=True)

            #update files
            self.df1.to_csv(PANDAS_FILENAME1)
            self.df2.to_csv(PANDAS_FILENAME2)            

            if self.delete_person_dir(data_dir, uid):
                #if we need to stop face detection
                if 'app_loop_face' in self.__dict__ :
                    self.stop_Facial_Recognition(True)

                #close facial data
                self.release_Known_Facial_Data()

                #reload facial data
                self.init_Known_Facial_Data(ENCODING_DIRECTORY, False)

                #clear data shown
                self.clear_data_labels()

                messagebox.showinfo('Person Deleted.', 'The person has been deleted.')
            else:
                messagebox.showerror("Error: Could Not Delete!", "Could not delete. Please delete the directory, on your own.")

        #set window to top most window and the focus
        self.root_window.attributes('-topmost', True)
        self.root_window.update()
        self.root_window.attributes('-topmost', False)
        self.root_window.update()
            

    '''
        delete_person_dir :
        Removes the directory their information is stored in.
    '''                              
    def delete_person_dir(self, data_dir, uid) -> bool:
        #now find the directory for this one
        #get all of our directories to be used
        directories = []
        for filename in os.listdir(data_dir):
            if os.path.isdir(os.path.join(data_dir, filename)):
                directories.append(os.path.join(data_dir, filename))

        deleted_dir = False

        for directory in directories:
        #get our first directory
            if deleted_dir:
                break

            #now open the files in this directory
            for filename in os.listdir(directory):
                if deleted_dir:
                    break
                if os.path.join(directory, filename) == os.path.join(directory, 'Name'):

                    #get our directory and then get our text file (will always be name.txt)
                    name_direct = os.path.join(directory, filename)

                    #make sure txt file is there
                    for nameDirectFile in os.listdir(name_direct):
                        
                        #get the name of the file we are looking for and see if it exists
                        file_direct = os.path.join(name_direct, 'name.txt')
                        if os.path.join(name_direct, nameDirectFile) == file_direct:
                            #data we read in
                            read_Data = []

                            #open the file and read in the name
                            with open(file_direct) as name_file:
                                #create our list of data and append to all data
                                data = [line for line in name_file.readlines()]
                                read_Data.append(data)

                            #see if this is the directory, that we need to delete
                            if len(read_Data[0]) == 3:
                                #strip return char
                                data = read_Data[0][2].rstrip()

                                #if we found our directory, delete it and then end the loop
                                if data == uid:
                                    # Try to remove the tree; if it fails, throw an error using try...except.
                                    try:
                                        shutil.rmtree(directory)
                                    except OSError as e:
                                        print("Error: %s - %s." % (e.filename, e.strerror))
                                        messagebox.showerror("Error: %s - %s." % (e.filename, e.strerror), 'Could not delete. Please delete the directory, on your own. ' + directory)
                                        return False
                                    
                                    deleted_dir = True
                                    return deleted_dir
                                    #break

        return deleted_dir
            
    
    '''
        add_person_to_facedata1 :
        Adds person to database.
    '''     
    def add_person_to_facedata1(self) -> None:
        #check to see if current stream already going. Must close it first
        if 'cap' in self.__dict__ :
            if messagebox.askyesno('Must close current video stream!', 'You must close your current video stream, if you wish to add a person. Do you wish to continue?'):
                self.stop_Webcam_Device()
                self.init_addperson_to_facedata1(self.root_window, self.style)
        #no stream, so add person
        else:
            self.init_addperson_to_facedata1(self.root_window, self.style)
        
        

    '''
        init_addperson_to_facedata1 :
        Loads the adding them to database GUI.
    ''' 
    def init_addperson_to_facedata1(self, root, style) -> None:
        self.addperson_Dialog = tk.Toplevel()

        self.addperson_Dialog.title('Select an Option')
        self.addperson_Dialog.resizable(width=False, height=False)
        self.addperson_Dialog.configure(bg=BACKGROUND_COLOR)

        #windows size
        dialog_width = 400
        dialog_height = 300

        #get our centered position
        x_pos, y_pos = self.get_Window_Center_Pos(self.screen_resolution[0], self.screen_resolution[1], dialog_width, dialog_height)

        self.addperson_Dialog.geometry(str(dialog_width) + 'x' + str(dialog_height) + '+' + str(x_pos) + '+' + str(y_pos))

        #configure columns and rows
        #setup 5 columns
        for i in range(5):
            self.addperson_Dialog.columnconfigure(index=i, minsize=dialog_width/5, weight=1)

        #setup 5 rows
        for i in range(5):
            self.addperson_Dialog.rowconfigure(index=i, minsize=dialog_height/5, weight=1)

        #now init GUI
        self.init_addperson_to_facedata1_GUI(self.addperson_Dialog, self.style)

        #set our device num to no device as default (-1)
        self.device_num_addPerson = -1

        self.addperson_Dialog.focus_set()
        root.attributes('-disabled', True)
        self.addperson_Dialog.attributes('-topmost', True)
        self.addperson_Dialog.update()
        self.addperson_Dialog.attributes('-topmost', False)
        self.addperson_Dialog.update()

        #capture close event
        self.addperson_Dialog.protocol("WM_DELETE_WINDOW", self.exit_addperson_to_facedata1)

    '''
        init_addperson_to_facedata1_GUI :
        Initializes the GUI for adding them to database.
    ''' 
    def init_addperson_to_facedata1_GUI(self, root, style) -> None:
        #label description
        self.dialog_description_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.dialog_description_label.grid(row=0, column=0, rowspan=2, columnspan=5, sticky=tk.NSEW)#, rowspan=6, sticky= tk.N)
        self.dialog_description_label.config(text='Please select how you wish to create a new face.\nEither from a file or camera.', anchor='center')
        
        #init radio buttons
        #create style for BACKGROUND_COLOR
        radio_style = ttk.Style()
        
        radio_style.map("FaceData1.TRadiobutton",   
                    background=[('active', BACKGROUND_COLOR), 
                                #('pressed', 'white'),
                                ('pressed', BACKGROUND_COLOR),
                                ('disabled', BACKGROUND_COLOR),
                                ('!disabled', BACKGROUND_COLOR)])#,
                    #foreground=[('active', 'RoyalBlue4'), 
                    #            #('pressed', 'black'),
                    #            ('pressed', 'black'),
                    #            ('disabled', 'AntiqueWhite2'),
                    #            ('!disabled', 'RoyalBlue2')]) #NavajoWhite4

        self.face1_radio = tk.IntVar()
        self.face1_radio.set(0)
        self.file_radio_button = ttk.Radiobutton(root, text="Face from file.", variable=self.face1_radio, value=1, command=self.facedata1_radiobutton_selected, style="FaceData1.TRadiobutton")
        self.camera_radio_button = ttk.Radiobutton(root, text="Face from camera.", variable=self.face1_radio, value=2, command=self.facedata1_radiobutton_selected, style="FaceData1.TRadiobutton")
        self.file_radio_button.grid(row=2, column=1, rowspan=1, columnspan=3, sticky=tk.NSEW)
        self.camera_radio_button.grid(row=3, column=1, rowspan=1, columnspan=3, sticky=tk.NSEW)

        #create our Okay Button
        okay_button = ttk.Button(root, text="Okay", padding=(0,2), command=lambda: self.okay_addperson_to_facedata1(self.face1_radio.get()), style="ButtonDesign1.Toolbutton")
        okay_button.grid(row=4, column=0, rowspan=1, columnspan=2, sticky=tk.NSEW)

        #create our Cancel button
        button_cancel = ttk.Button(root, text="Cancel", padding=(0,2), command=self.exit_addperson_to_facedata1, style="ButtonDesign1.Toolbutton")
        button_cancel.grid(row=4, column=3, rowspan=1, columnspan=2, sticky=tk.NSEW)

    '''
        exit_addperson_to_facedata1 :
        Exits the window for adding to database.
    ''' 
    def exit_addperson_to_facedata1(self) -> None:
        
        #re-enable the main window
        self.root_window.attributes('-disabled', False)

        #destroy this window
        self.file_radio_button.selection_clear()
        self.camera_radio_button.selection_clear()
        self.file_radio_button.destroy()
        self.camera_radio_button.destroy()
        self.addperson_Dialog.destroy()

        #set window to top most window and the focus
        self.root_window.attributes('-topmost', True)
        self.root_window.update()
        self.root_window.attributes('-topmost', False)
        self.root_window.update()

    '''
        okay_addperson_to_facedata1 :
        Handles when trying to add person. It will make sure they can actual add them to database.
    ''' 
    def okay_addperson_to_facedata1(self, radioButton) -> None:
        #check to see which radio button was selected
        if radioButton == 0:
            #disable dialog
            self.addperson_Dialog.attributes('-disabled', True)
            messagebox.showwarning('No Option Selected', 'Please select an option and then click the Okay button.')
            #enable dialog
            self.addperson_Dialog.attributes('-disabled', False)
            self.addperson_Dialog.focus_set()
            self.addperson_Dialog.attributes('-topmost', True)
            self.addperson_Dialog.update()
            self.addperson_Dialog.attributes('-topmost', False)
            self.addperson_Dialog.update()
        #open a file
        elif radioButton == 1:
            #disable dialog
            self.addperson_Dialog.attributes('-disabled', True)
            file = fd.askopenfile(
                title="Open an Image File",
                initialdir=os.getcwd(),
                filetypes=[ ("Jpeg files",('*.jpeg;*.jpg')), 
                            ("Png file",('*.png')),
                            ("Gif file",('*.gif')) ])

            if file:
                #try and open the file
                try:
                    img = cv2.imread(filename=file.name)
                except:
                    messagebox.showerror("Open File Error!", "Error opening file! Please try again or another file.")
                    #enable dialog
                    self.addperson_Dialog.attributes('-disabled', False)
                    self.addperson_Dialog.focus_set()
                    self.addperson_Dialog.attributes('-topmost', True)
                    self.addperson_Dialog.update()
                    self.addperson_Dialog.attributes('-topmost', False)
                    self.addperson_Dialog.update()
                    return

                print(type(img))

                #if type(img) == 'NoneType':
                if isinstance(img, (type(None))):
                    messagebox.showerror("Open File Error!", "Error opening file! Please try again or another file.")
                    #enable dialog
                    self.addperson_Dialog.attributes('-disabled', False)
                    self.addperson_Dialog.focus_set()
                    self.addperson_Dialog.attributes('-topmost', True)
                    self.addperson_Dialog.update()
                    self.addperson_Dialog.attributes('-topmost', False)
                    self.addperson_Dialog.update()
                    return
                #check to see if we have an encoded face
                results = self.check_image_camera_face_capture_dialog(img)

                #we have an image with face
                if results == 1:
                    print('face encoded')

                    #now check to see if the face is currently in encoded faces

                    #copy image
                    self.camera_face_image = copy.deepcopy(img)

                    #destroy this window
                    #self.file_radio_button.selection_clear()
                    #self.camera_radio_button.selection_clear()
                    #self.file_radio_button.destroy()
                    #self.camera_radio_button.destroy()
                    self.addperson_Dialog.destroy()

                    #load profile dialog
                    self.init_person_profile_dialog(self.camera_face_image)
                #image with no face
                else:
                    print('face not encoded')
                    text = tuple()
                    if results == 0:
                        text = ('No Face Detected!', 'Please make sure one face is inside the video screen and try again.')
                    elif results == 2:
                        text = ('Too Many Faces Detected!', 'Please make sure one and only one face is inside the video screen and try again.')
                    elif results == 3:
                        text = ('Face Already Known!', 'This face is of a known person. Please use someone else.')

                    messagebox.showerror(text[0], text[1])

                    #enable dialog
                    self.addperson_Dialog.attributes('-disabled', False)
                    self.addperson_Dialog.focus_set()
                    self.addperson_Dialog.attributes('-topmost', True)
                    self.addperson_Dialog.update()
                    self.addperson_Dialog.attributes('-topmost', False)
                    self.addperson_Dialog.update()
                    return
                    
                
                
            #No file selected. Re-enable dialog
            else:
                #enable dialog
                self.addperson_Dialog.attributes('-disabled', False)
                self.addperson_Dialog.focus_set()
                self.addperson_Dialog.attributes('-topmost', True)
                self.addperson_Dialog.update()
                self.addperson_Dialog.attributes('-topmost', False)
                self.addperson_Dialog.update()       
                                  
        elif radioButton == 2:
            #destroy this window
            self.file_radio_button.selection_clear()
            self.camera_radio_button.selection_clear()
            self.file_radio_button.destroy()
            self.camera_radio_button.destroy()
            self.addperson_Dialog.destroy()

            #load the device dialog, addPerson is True, since we are adding
            self.init_VideoDevice_Dialog(None, self.style, True)


    '''
        facedata1_radiobutton_selected :
        Radio button options.
    ''' 
    def facedata1_radiobutton_selected(self) -> None:
        if self.face1_radio.get() == 1:
            print('file')
        elif self.face1_radio.get() == 2:
            print('camera')

    '''
        all_names_button_select :
        Old code, no longer used for selecting names on list.
    ''' 
    def all_names_button_select(self):

        #get current selection
        index = self.all_names_listbox.curselection()

        #if we have a selection
        if index:
            #get the person at this location
            person = self.df2.iloc[index[0]]

            #now get indexes for our list of people
            indexes = self.df1.index.to_list()

            #now use the index of UUID (person.name. DONT BE CONFUSED. the .name is part of pandas for index key) 
            #and then get the 'Name' of the person
            pos = indexes.index(person.name)
            name = self.df1.iloc[pos]['Name']

            print('*******************************************')
            print(name)
            print(person.name)
            print(person['Arrival Time'])
            print(person['Departure Time'])
            print(person['Total Time'])

    '''
        all_names_listbox_select :
        Used to populate listbox with names from pandas dataframe.
    ''' 
    def all_names_listbox_select(self, event) -> None:
        #get current selection
        #index = event.widget.curselection()
        index = self.all_names_listbox.curselection()

        #if we have a selection
        if index:
            #get the person at this location
            person = self.df1.iloc[index[0]]

            #now get indexes for our list of people
            indexes = self.df1.index.to_list()

            #now use the index of UUID (person.name. DONT BE CONFUSED. the .name is part of pandas for index key) 
            #and then get the 'Name' of the person
            pos = indexes.index(person.name)
            name = self.df1.iloc[pos]['Name']

            print('*******************************************')
            print(name)
            print(person.name)
            print(person['Description'])
            #print(person['Arrival Time'])
            #print(person['Departure Time'])
            #print(person['Total Time'])


            #make sure its in the range of our image array and then update frame with image
            if index[0] in range(len(self.images)):
                self.update_image_frame(self.images[index[0]][0], name)
                self.image_uid_label.config(text='ID : ' + str(person.name))
                self.image_description_label.config(text='Info : ' + person['Description'])

                self.fill_image_datetime_table(person.name)
                
                #firsttime, lasttime = self.get_first_last_seen(self.unique_ids[index])
                #seen_text = "First Seen : " + str(firsttime)
                #self.image_first_seen_label.config(text=seen_text)
                #seen_text = "Last Seen : " + str(lasttime)
                #self.image_last_seen_label.config(text=seen_text)

    '''
        fill_image_datetime_table :
        Displays the persons data on the window interface.
    ''' 
    def fill_image_datetime_table(self, id) -> None:
        #clear treeview
        for i in self.image_datetime_table.get_children():
            self.image_datetime_table.delete(i)

        #find the data for this id
        df = self.df2.loc[self.df2.index== id]

        last_date1 = None
        last_string_date1 = None
        last_date2 = None
        last_string_date2 = None

        #now fill the table
        for i in range(df.shape[0]):
            #get our data
            arrival_string = str(df.iloc[i]['Arrival Time'])
            depart_string = str(df.iloc[i]['Departure Time'])
            total_time = float(df.iloc[i]['Total Time'])

            #remove microseconds
            arrival = arrival_string[:arrival_string.index('.')]
            depart = depart_string[:depart_string.index('.')]

            #format string to datetime
            arrival = datetime.datetime.strptime(arrival, '%Y-%m-%d %H:%M:%S')
            depart = datetime.datetime.strptime(depart, '%Y-%m-%d %H:%M:%S')                
            
            #format arrival to month and time string
            arrival_date = str(arrival.month) + '-' + str(arrival.day) + '-' + str(arrival.year)
            arrival_time = str(arrival.hour) + ':' + str(arrival.minute) + ':' + str(arrival.second)

            #format depart to month and time string
            depart_date = str(depart.month) + '-' + str(depart.day) + '-' + str(depart.year)
            depart_time = str(depart.hour) + ':' + str(depart.minute) + ':' + str(depart.second)

            #check to see if we have latest date and time
            if last_date1 == None:
                last_date1 = arrival
                last_date2 = depart

                #check to see if the dates are different.
                #get our dates as month, day, year
                arr = datetime.datetime(arrival.year, arrival.month, arrival.day)
                dep = datetime.datetime(depart.year, depart.month, depart.day)
                #if first day is less than last day
                if arr < dep:
                    last_string_date1 = arrival_string
                    last_string_date2 = depart_string

                    #dates different, so put both dates in our string
                    arrival_date = arrival_date + ' & ' + depart_date

                else: 
                    last_string_date1 = arrival_string
                    last_string_date2 = depart_string   

            elif last_date1 < arrival:
                last_date1 = arrival
                last_date2 = depart

                #check to see if the dates are different.
                #get our dates as month, day, year
                arr = datetime.datetime(arrival.year, arrival.month, arrival.day)
                dep = datetime.datetime(depart.year, depart.month, depart.day)
                #if first day is less than last day
                if arr < dep:
                    last_string_date1 = arrival_string
                    last_string_date2 = depart_string

                    #dates different, so put both dates in our string
                    arrival_date = arrival_date + ' & ' + depart_date
                else:
                    last_string_date1 = arrival_string
                    last_string_date2 = depart_string  
            
            #format time in minutes
            total_time = total_time / 60.0

            total_time = str(format(total_time, '.2f')) + ' minutes.'

            #fill in table data            
            self.image_datetime_table.insert(parent='', index=i, iid=i, text='', 
                                             values=(arrival_date, arrival_time, depart_time, total_time))

        #now update the latest date and time
        #make sure we have dates to use
        if isinstance(last_string_date1, (type(None))):
            seen_text = "First Seen : "
            self.image_first_seen_label.config(text=seen_text)
        else:
            seen_text = "First Seen : " + last_string_date1
            seen_text = seen_text[:seen_text.index('.')]
            self.image_first_seen_label.config(text=seen_text)

        if isinstance(last_string_date2, (type(None))):
            seen_text = "Last Seen : "
            self.image_last_seen_label.config(text=seen_text)
        else:
            seen_text = "Last Seen : " + last_string_date2
            seen_text = seen_text[:seen_text.index('.')]
            self.image_last_seen_label.config(text=seen_text)


        #seen_text = "First Seen : " + last_string_date1
        #seen_text = seen_text[:seen_text.index('.')]
        #self.image_first_seen_label.config(text=seen_text)

        #seen_text = "Last Seen : " + last_string_date2
        #seen_text = seen_text[:seen_text.index('.')]
        #self.image_last_seen_label.config(text=seen_text)

    '''
        update_image_frame :
        Gets the correct person image to display.
    ''' 
    def update_image_frame(self, in_image, name):
        image = in_image.copy()
        #image = Image.open(image).resize((200, 150))

        #resize our image
        max_width = 200
        scale_percent = max_width / image.shape[1]
        w = int(image.shape[1] * scale_percent)
        h = int(image.shape[0] * scale_percent)
        dim = (w,h)
        image = cv2.resize(image, dim, interpolation = cv2.INTER_AREA)

        #now make sure height is under our max size
        if image.shape[0] > 200:
            max_height = 200
            scale_percent = max_height / image.shape[0]
            w = int(image.shape[1] * scale_percent)
            h = int(image.shape[0] * scale_percent)  

            dim = (w,h)
             
            image = cv2.resize(image, dim, interpolation = cv2.INTER_AREA)

        #now format our image and add it to label
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
        imgtk = ImageTk.PhotoImage(image=image)
        self.image_face_label.imgtk = imgtk
        self.image_face_label.configure(image=imgtk)

        #update name
        self.image_name_label.config(text='Name : ' + name)

    '''
        get_monitor_resolution :
        Does what says.
    ''' 
    def get_monitor_resolution(self) -> list:
        """
        Gets the screen resoultion for current monitor. (works with multiple monitors)

        geometry (str): The standard Tk geometry string.
            [width]x[height]+[left]+[top]

        Returns:
            (list)
            [width, heigh, left, top]
        """
        root = tk.Tk()
        root.update_idletasks()
        root.attributes('-fullscreen', True)
        root.state('iconic')
        geometry = root.winfo_geometry()
        root.destroy()

        #create a list of the attributes
        #get our index positions
        indexes = []
        indexes.append(geometry.find('x'))
        indexes.append(geometry.find('+'))
        indexes.append(geometry.find('+', indexes[1]+1))

        #now sort the data
        width = int(geometry[:indexes[0]])
        height = int(geometry[indexes[0]+1:indexes[1]])
        left = int(geometry[indexes[1]+1:indexes[2]])
        right = int(geometry[indexes[2]+1:])

        #return geometry
        return [width, height, left, right]

    '''
        face_check :
        Checks if the camera view has a detectable face.
    ''' 
    def face_check(self, frame):
        
        starttime = time.perf_counter()

        locations = []

        small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
        #get our face locations
        #cnn or hog
        #model="hog"
        #locations = face_recognition.face_locations(cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY), number_of_times_to_upsample=1)
        #locations = face_recognition.face_locations(cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY), model='hog')
        #locations = face_recognition.face_locations(cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY), model='cnn')
        locations = face_recognition.face_locations(cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY))

        #check faces if the number on screen has changed or if we have any faces, check every time_seconds_check seconds
        if len(locations) != self.last_face_count or abs(time.perf_counter() - self.time_check) >= self.time_seconds_check and len(locations) > 0:
            
            #set the new face count and update time
            self.last_face_count = len(locations)
            self.time_check = time.perf_counter()

            #make sure we are doing multithread
            if 'app_loop_face' in self.__dict__ :
                #send tuple of (locations, small_frame)
                self.data_in_queue.put((locations.copy(), small_frame.copy()))

        elif len(locations) == 0:
            #set the new face count and update time
            self.last_face_count = len(locations)

            #make sure we are doing multithread
            if 'app_loop_face' in self.__dict__ :
                #send tuple of (locations, small_frame)
                self.data_in_queue.put((locations.copy(), small_frame.copy()))

        #make sure we are doing multithread
        if 'app_loop_face' in self.__dict__ :
            #check the out queue to see if we have any data
            while not self.data_out_queue.empty():
                #make sure we are doing multithread
                if 'app_loop_face' not in self.__dict__ :
                    break
                
                #get our data and then update current faces
                faces_data = self.data_out_queue.get()                
                self.add_facedata_to_currentfaces(faces_data)

                #tk.Event()
                #update listbox selection, if selected
                self.names_listbox_select(tk.Event())
        
        #end this now if we are done with face rec
        if 'app_loop_face' not in self.__dict__ :
            return locations

        starttime = abs(time.perf_counter() - starttime)
        #print('face_check Time : ' + str(starttime))

        return locations
    
    '''
        add_facedata_to_currentfaces :
        This will add new faces to our current_faces. will check if they need to be updated or added
    ''' 
    def add_facedata_to_currentfaces(self, faces_data):        
        
        #lock data and go through to find it
        with self.current_faces_lock:
            new_faces = []

            #go through faces data sent in
            for face in faces_data:
                #make sure this face is not unknown
                if face.name != "Unknown":
                    #lets us know if face is in our current list
                    found = False

                    for current_face in self.current_faces:                    
                        #see if we found it in current
                        if current_face.id == face.id:
                            #lets us know we found it
                            found = True
                            
                            #update last time an break loop
                            current_face.date_time_last = face.date_time_first

                            break
                    
                    #not in list, so add to it
                    if not found:
                        new_faces.append(face)

            #add new faces to listbox
            self.add_facedata_to_listbox(new_faces)
            
            #add new faces to current faces
            self.current_faces.extend(new_faces)

    '''
        add_facedata_to_listbox :
        Adds face names to listbox.
    ''' 
    def add_facedata_to_listbox(self, facedata):

        #loop through and add them to listbox
        for face in facedata:
            self.names_listbox.insert(tk.END, face.name)

    '''
        init_person_profile_dialog :
        Initialize the profile window.
    ''' 
    def init_person_profile_dialog(self, image) -> None:
        self.person_profile_dialog = tk.Toplevel()

        self.person_profile_dialog.title('Person Profile')
        self.person_profile_dialog.resizable(width=False, height=False)
        self.person_profile_dialog.configure(bg=BACKGROUND_COLOR)

        #windows size
        dialog_width = 800
        dialog_height = 800

        #get our centered position
        x_pos, y_pos = self.get_Window_Center_Pos(self.screen_resolution[0], self.screen_resolution[1], dialog_width, dialog_height)

        self.person_profile_dialog.geometry(str(dialog_width) + 'x' + str(dialog_height) + '+' + str(x_pos) + '+' + str(y_pos))

        #configure columns and rows
        #setup 6 columns
        for i in range(6):
            self.person_profile_dialog.columnconfigure(index=i, minsize=dialog_width/6, weight=1)

        #setup 10 rows
        for i in range(10):
            self.person_profile_dialog.rowconfigure(index=i, minsize=dialog_height/10, weight=1)

        #create a UUID for this person
        uid = face_data.create_unique_id(self.unique_ids)

        #create the GUI
        self.init_person_profile_dialog_GUI(self.person_profile_dialog, self.style, image, uid)       

        self.person_profile_dialog.focus_set()
        self.person_profile_name_entry.focus_force()   
        self.person_profile_dialog.attributes('-topmost', True)
        self.person_profile_dialog.update()
        self.person_profile_dialog.attributes('-topmost', False)
        self.person_profile_dialog.update()

        #capture close event
        self.person_profile_dialog.protocol("WM_DELETE_WINDOW", self.exit_person_profile_dialog)


        #enable start button
        #self.cam_start_button['state'] = 'normal'

    '''
        init_person_profile_dialog_GUI :
        Setup the GUI for the dialog.
    ''' 
    def init_person_profile_dialog_GUI(self, root, style, image, uid) -> None:
        #create image label
        self.person_profile_face_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.person_profile_face_label.grid(row=0, column=1, rowspan=5, columnspan=4, sticky=tk.NSEW)
        #image2 = image
        #image2 = cv2.cvtColor(image2, cv2.COLOR_BGR2RGB)
        #image2 = Image.fromarray(image2)
        #image2 = ImageTk.PhotoImage(image=image2)
        self.person_profile_face_label.config(text='', anchor='center')#, image=image2)
        #self.person_profile_face_label.imgtk = image2
        #self.person_profile_face_label.configure(image=image2)

        self.update_image_person_profile_dialog_frame(image, self.person_profile_face_label, 375)

        #details label
        self.person_profile_title_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.person_profile_title_label.grid(row=5, column=0, columnspan=6, sticky=tk.NSEW)
        self.person_profile_title_label.config(text='Enter the details of this person below and then press Okay to add them.', anchor='center')

        #create name label
        self.person_profile_name_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.person_profile_name_label.grid(row=6, column=0, columnspan=2, sticky=tk.E)
        self.person_profile_name_label.config(text='Please enter the persons name :', anchor='center')

        #create name entry
        validate_cmd_name = (root.register(self.validate_name_length), '%P')

        self.person_profile_name_var = tk.StringVar()
        self.person_profile_name_entry = ttk.Entry(root, width=75, validate='key', validatecommand=validate_cmd_name, textvariable=self.person_profile_name_var)
        self.person_profile_name_entry.grid(row=6, column=2, columnspan=4)
        

        #create description label
        self.person_profile_description_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.person_profile_description_label.grid(row=7, column=0, columnspan=2, sticky=tk.E)
        self.person_profile_description_label.config(text='Enter a description, under 50 characters :', anchor='center')

        #create description entry
        validate_cmd_description = (root.register(self.validate_description_length), '%P')

        self.person_profile_description_var = tk.StringVar()
        self.person_profile_description_entry = ttk.Entry(root, width=75, validate='key', validatecommand=validate_cmd_description, textvariable=self.person_profile_description_var)
        self.person_profile_description_entry.grid(row=7, column=2, columnspan=4)

        #create unique id label
        self.person_profile_uid_label = ttk.Label(root, background=BACKGROUND_COLOR)
        self.person_profile_uid_label.grid(row=8, column=0, columnspan=6, sticky=tk.NSEW)
        self.person_profile_uid_label.config(text='ID : ' + str(uid), anchor='center')

        #init buttons
        self.init_person_profile_dialog_buttons(root, style)

    '''
        update_image_person_profile_dialog_frame :
        Will resize the persons image to fit the window.
    ''' 
    def update_image_person_profile_dialog_frame(self, in_image, label, size):
        image = in_image.copy()
        #image = Image.open(image).resize((200, 150))

        #resize our image
        max_width = size
        scale_percent = max_width / image.shape[1]
        w = int(image.shape[1] * scale_percent)
        h = int(image.shape[0] * scale_percent)     

        dim = (w,h)

        image = cv2.resize(image, dim, interpolation = cv2.INTER_AREA)

        #now make sure height is under our max size
        if image.shape[0] > size:
            max_height = size
            scale_percent = max_height / image.shape[0]
            w = int(image.shape[1] * scale_percent)
            h = int(image.shape[0] * scale_percent)  

            dim = (w,h)

            image = cv2.resize(image, dim, interpolation = cv2.INTER_AREA) 

        #now format our image and add it to label
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = Image.fromarray(image)
        imgtk = ImageTk.PhotoImage(image=image)
        label.imgtk = imgtk
        label.configure(image=imgtk)

    '''
        init_person_profile_dialog_buttons :
        Setup the buttons for this dialog.
    ''' 
    def init_person_profile_dialog_buttons(self, root, style) -> None:
        #create our Back Button
        #back_button = ttk.Button(root, text="Back", padding=(0,2), command= self.back_camera_face_capture_dialog)
        #back_button.grid(row=9, column=0, rowspan=1, columnspan=1, sticky=tk.NSEW)
        
        #create our Okay Button
        okay_button = ttk.Button(root, text="Okay", padding=(0,2), command=self.okay_person_profile_dialog, style="ButtonDesign1.Toolbutton")
        okay_button.grid(row=9, column=4, rowspan=1, columnspan=1, sticky=tk.NSEW)

        #create our Cancel button
        button_cancel = ttk.Button(root, text="Cancel", padding=(0,2), command=self.cancel_person_profile_dialog, style="ButtonDesign1.Toolbutton")
        button_cancel.grid(row=9, column=5, rowspan=1, columnspan=1, sticky=tk.NSEW)

    '''
        validate_name_length :
        Used to limit name length to 100 or less.
    ''' 
    def validate_name_length(self, new_text):
        #valid = len(new_text) <= 10
        #self.person_profile_name_entry.config(bg='green' if valid else 'red', fg='white')
        #return valid

        #strip returns
        #if new_text.find('\n') >= 0:
        #    self.person_profile_name_var.set(self.person_profile_name_var.get().rstrip())
        
        #make sure len under size
        #if len(new_text) > 100:
        #    self.person_profile_name_var.set(self.person_profile_name_var.get()[:100])

        #return self.person_profile_name_var.get()

        valid = len(new_text) <= 100
        return valid

    '''
        validate_description_length :
        Used to limit description length to 50 or less.
    ''' 
    def validate_description_length(self, new_text):
        #valid = len(new_text) <= 10
        #self.person_profile_name_entry.config(bg='green' if valid else 'red', fg='white')
        #print(valid)
        #strip returns
        #if new_text.find('\n') >= 0:
        #    self.person_profile_description_var.set(self.person_profile_description_var.get().rstrip())
        
        #make sure len under size
        #if len(new_text) > 50:
        #    self.person_profile_description_var.set(self.person_profile_description_var.get()[:50])

        #return self.person_profile_description_var.get()

        valid = len(new_text) <= 50
        return valid

    #Unused
    def back_person_profile_dialog(self) -> None:
        pass
    
    '''
        okay_person_profile_dialog :
        Will make sure we have the correct information for this person.
    ''' 
    def okay_person_profile_dialog(self) -> None:
        #get our entry name and description
        name = self.person_profile_name_entry.get().rstrip()
        description = self.person_profile_description_entry.get().rstrip()

        if len(name) == 0 :
            messagebox.showwarning('No Name Entered!', 'Please enter a name.')
            self.person_profile_dialog.focus_set()
            self.person_profile_dialog.attributes('-topmost', True)
            self.person_profile_dialog.update()
            self.person_profile_dialog.attributes('-topmost', False)
            self.person_profile_dialog.update()
        elif len(description) == 0 :
            messagebox.showwarning('No Description Entered!', 'Please enter a description.')
            self.person_profile_dialog.focus_set()
            self.person_profile_dialog.attributes('-topmost', True)
            self.person_profile_dialog.update()
            self.person_profile_dialog.attributes('-topmost', False)
            self.person_profile_dialog.update()
        else:
            text = 'Are you sure you wish to add ' + name + '? Yes to continue. No to edit information.'
            if messagebox.askyesno('Add Person?', text):
                print(name)
                print(description)

                #get our id (need to get rid of "ID : ")
                uid = self.person_profile_uid_label['text'][5:]
                print(uid)

                #if we add person successfully
                if self.add_person_profile_dialog(name, description, self.camera_face_image, uid):
                    #need to reload data
                    print('Person added')

                    #release all known people
                    self.release_Known_Facial_Data()

                    #now delete file1
                    result = self.delete_pandas_file1(os.path.join(PANDAS_DIRECT, PANDAS_REAL_FILE1))                 
                    
                    #reload all known people
                    self.init_Known_Facial_Data(ENCODING_DIRECTORY, False)

                    #exit dialog and go back to main
                    self.exit_person_profile_dialog()

                #error adding person
                else:
                    print("error adding person")



                #delete our image
                #if 'camera_face_image' in self.__dict__ :
                #    del self.__dict__['camera_face_image']
            else:
                self.person_profile_dialog.focus_set()
                self.person_profile_dialog.attributes('-topmost', True)
                self.person_profile_dialog.update()
                self.person_profile_dialog.attributes('-topmost', False)
                self.person_profile_dialog.update()

    '''
        delete_pandas_file1 :
        Quick fix to delete pandas file.
    ''' 
    def delete_pandas_file1(self, filename) -> bool:
        deleted = False
        #direct = os.path.join(directory, filename)
        #check to see if we have a file to delete
        if os.path.isfile(filename):

            # Try to delete the file.
            try:
                os.remove(filename)
                deleted = True
            except OSError as e:
                # If it fails, inform the user.
                print("Error: %s - %s." % (e.filename, e.strerror))
                return False

        return deleted

    '''
        add_person_profile_dialog :
        Will add a person to our database. Returns True if success and False if not.
    ''' 
    def add_person_profile_dialog(self, name, description, image, uid) -> bool:
        #ENCODING_DIRECTORY
        #get all of our directories to be used
        directories1 = []
        directories2 = []
        count = 0
        for filename in os.listdir(ENCODING_DIRECTORY):
            if os.path.isdir(os.path.join(ENCODING_DIRECTORY, filename)):
                directories1.append(os.path.join(ENCODING_DIRECTORY, filename))
                directories2.append(filename)
                count+=1

        #i = 5
        # 0, 1, 3, 4, 5

        #i = 2
        # 0 2

        direct_num = count

        for i in range(count):
            if str(i) not in directories2:
                direct_num = i
                break


        #i=0

        #keep checking, until we can make a new directory and then break loop
        #while True:
        #    if not os.path.exists(os.path.join(ENCODING_DIRECTORY, str(i))):
        #        os.makedirs(os.path.join(ENCODING_DIRECTORY, str(i)))
        #        break
        #    else:
        #        i+=1

        #keep checking, until we can make a new directory and then break loop
        while True:
            if not os.path.exists(os.path.join(ENCODING_DIRECTORY, str(direct_num))):
                os.makedirs(os.path.join(ENCODING_DIRECTORY, str(direct_num)))
                break
            else:
                direct_num+=1
        
        #create directory
        directory = os.path.join(ENCODING_DIRECTORY, str(direct_num))

        #save image
        filesaved = cv2.imwrite(os.path.join(directory, name + '.png'),image)

        #error saving file. Remove directory and return False
        if not filesaved:
            # Try to remove the tree; if it fails, throw an error using try...except.
            try:
                shutil.rmtree(directory)
            except OSError as e:
                print("Error: %s - %s." % (e.filename, e.strerror))

            return False
        
        #create Name directory and set
        os.makedirs(os.path.join(directory, 'Name'))
        directory = os.path.join(directory, 'Name')

        #now create name.txt and write to it
        direct_file = os.path.join(directory, 'name.txt')

        #try to write to file name.txt
        try:
            with open(direct_file, 'w') as file:
                # Write content to the file
                file.write(name + '\n')
                file.write(description + '\n')
                file.write(uid)
        except Exception as error:
            print("Error saving name.txt")
            filesaved = False

        #error saving file. Remove directory and return False
        if not filesaved:
            # Try to remove the tree; if it fails, throw an error using try...except.
            try:
                directory = os.path.join(ENCODING_DIRECTORY, str(i))
                shutil.rmtree(directory)
            except OSError as e:
                print("Error: %s - %s." % (e.filename, e.strerror))

            return False
        
        #should return True
        return filesaved
        
    '''
        cancel_person_profile_dialog :
        Just cancels adding them.
    ''' 
    def cancel_person_profile_dialog(self) -> None:
        #Make sure we wish to cancel
        if messagebox.askokcancel("Do you wish to cancel?", "If you cancel, you will have to start over again. Are you sure?"):
            self.exit_person_profile_dialog()
        else:
            self.person_profile_dialog.focus_set()
            self.person_profile_dialog.attributes('-topmost', True)
            self.person_profile_dialog.update()
            self.person_profile_dialog.attributes('-topmost', False)
            self.person_profile_dialog.update()

    '''
        exit_person_profile_dialog :
        Handles window being closed and exited.
    ''' 
    def exit_person_profile_dialog(self) -> None:
        #re-enable the main window
        self.root_window.attributes('-disabled', False)
        #destroy this window
        self.person_profile_dialog.destroy()

        #delete our image
        if 'camera_face_image' in self.__dict__ :
            del self.__dict__['camera_face_image']

        #set window to top most window and the focus
        self.root_window.attributes('-topmost', True)
        self.root_window.update()
        self.root_window.attributes('-topmost', False)
        self.root_window.update()
    
    '''
        check_face_times :
        Unused here.
    ''' 
    def check_face_times(self, face_data):
        #go through face data to see if we need to add to this
        for data in face_data:

            #keep track if we found data
            found = False

            #go through all current faces stored
            for current_face in self.current_faces:
                if data.id == current_face.id:
                    pass
    '''
        check_time_diff_less :
        This is used to check to see if we need to remove them from being currently active. We have a time we want to check. So example, the persons face has not been seen for 5 minutes, 
        we will then remove them from being active. Will return True if they are under and False if equal or over.
    ''' 
    #checks to see if the time is less 
    def check_time_diff_less(self, start_time, end_time, diff) -> bool:
        
        datetime.datetime.now()
        timediff = end_time - start_time

        if timediff.seconds < diff:
            return True
        else:
            return False

    '''
        check_names_listbox_remove :
        Updates our listbox for names to display.
    ''' 
    def check_names_listbox_remove(self, removal_time):

        #lock data and go through to find it
        with self.current_faces_lock:
            #list of faces to remove
            removed_faces = []

            #go through current faces
            for current_face in self.current_faces:
                #check to see if its not less than our removal time
                if not self.check_time_diff_less(current_face.date_time_last, datetime.datetime.now(), removal_time):
                    #remove it from the list and update our listbox
                    removed_faces.append(current_face)

            #go through faces to remove and update pandas df2 and file2
            for removed_face in removed_faces:
                self.remove_facedata_from_listbox(removed_face)
                self.update_panda_dataframe2(self.df2, 
                                             removed_face.id, 
                                             removed_face.date_time_first, 
                                             removed_face.date_time_last, 
                                             PANDAS_FILENAME2)
                
                #update list
                self.update_all_names_listbox()

            #if we removed a face, check to see if we have one selected on person list and update table
            if removed_faces:
                self.all_names_listbox_select(None)


    '''
        remove_facedata_from_listbox :
        Will remove the person from the listbox.
    '''   
    def remove_facedata_from_listbox(self, facedata):
        #get selected listbox item
        index = self.names_listbox.curselection()
        value = None

        if index:
            # get the value at the selected index
            selected_face = self.current_faces[index[0]]

            #see if selected is one we will delete
            if selected_face.id != facedata.id:
                value = selected_face.id
            #we will delete it, so clear our labels
            #else:
            #    self.clear_data_labels()

        #find item and delete it
        for face in self.current_faces:
            #if we found our item, remove it and break loop
            if face.id == facedata.id:
                self.current_faces.remove(face)
                break   

        #clear listbox
        self.names_listbox.delete(0, tk.END)

        #repopulate listbox
        i = 0
        for face in self.current_faces:
            self.names_listbox.insert(tk.END, face.name)

            #if we have a value, and we found it in our list, select it
            if value and face.id == value:
                self.names_listbox.select_set(i)

            i+=1

    '''
        clear_data_labels :
        Clears all data for a person.
    '''   
    def clear_data_labels(self) -> None:
        self.image_face_label.config(image='')
        self.image_name_label.config(text='')
        self.image_uid_label.config(text='')
        self.image_description_label.config(text='')
        self.image_first_seen_label.config(text='')
        self.image_last_seen_label.config(text='')
        #clear treeview
        for i in self.image_datetime_table.get_children():
            self.image_datetime_table.delete(i)
    
    '''
        add_names_to_listbox :
        No longer used.
    '''  
    #add name to listbox, if its not in it already
    def add_names_to_listbox(self, names, confidences):
        
        #go through all names
        for name, confidence in zip(names, confidences):
            #dont use Unknown name
            if name != 'Unknown':
                #get listbox size and names from it
                size = self.names_listbox.size()
                box_names = []
                for i in range(0,size):
                    box_names.append(self.names_listbox.get(i))
                
                #if names not in the listbox, then add to end
                if name not in box_names:
                    self.names_listbox.insert(tk.END, name)


if __name__ == "__main__":
    multiprocessing.freeze_support()
    app = VideoRecorder()
    if(app.valid_init):
        app.start()
    else:
        app.exit()

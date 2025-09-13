'''
Created By : Christian Merriman

Date : 1/22/2024

Purpose : Used to handle facial recognition. This is used with multiprocessing, for handling the data we capture on video.
Follow the functions below for flow.

'''
import time
import os
from os.path import exists as file_exists
import cv2
import face_recognition
import multiprocessing
import uuid
import numpy as np
import math
import pandas as pd
import copy
from datetime import datetime
import datetime

MAX_LINE_SIZE = 3

'''
    class FaceData :
    Will store information on the person face.
'''  
class FaceData:
    def __init__(self, id = None, image = None, encoder = None, name = "Unknown", description = None, location = None, frame = None, confidence = None, date_time = None):
        self.id = id
        self.image = image
        self.encoder = encoder
        self.name = name
        self.description = description
        self.location = location
        self.frame = frame
        self.confidence = confidence
        self.date_time_first = date_time    #first seen
        self.date_time_last = date_time     #last seen
        self.first_Visible_perf = 0
        self.first_Visible_time = 0
        self.last_Visible_perf = 0
        self.last_Visible_time = 0
        self.TIME_INACTIVE = 2 * 60 #minutes * seconds for time away and inactive
        
    '''
        set_TimeVisible :
        It will keep track of time the person has been active (seen).
    '''  
    def set_TimeVisible(self):
        #if no time set, init first and last
        if self.first_Visible_time == 0:
            self.last_Visible_perf = self.first_Visible_perf = time.perf_counter()
            self.last_Visible_time = self.first_Visible_time = time.gmtime()
        #if not first time and its less than or equal our inactive time, then set next time
        elif abs(time.perf_counter() - self.last_Visible_perf) <= self.TIME_INACTIVE:
            self.last_Visible_perf = time.perf_counter()
            self.last_Visible_time = time.gmtime()
        #if not first time and its greater than our inactive time, then...
        #FOR NOW : just start time keepers at start
        elif abs(time.perf_counter() - self.last_Visible_perf) > self.TIME_INACTIVE:
            #figure out code here. We see them again for first time.
            self.last_Visible_perf = self.first_Visible_perf = time.perf_counter()
            self.last_Visible_time = self.first_Visible_time = time.gmtime()
    '''
        set_Confidence :
        This will set the face confidence. How likely the face we are looking at, is the one we know.
    '''  
    def set_Confidence(self, new_Confidence, name, frame, location):
        if new_Confidence > self.confidence:
            self.confidence = new_Confidence
            self.name = name
            self.frame = frame
            self.location = location

'''
    class AppLoopFaceCheck :
    This is used for our multiprocessing, to handle all face data.
'''  
class AppLoopFaceCheck:

    def __init__(self, in_queue, out_queue, faceencodings, facenames, faceimages, facedescriptions, uids):
        self.cpu_cores = multiprocessing.cpu_count() #number of cpus to use
        self.app_timer = time.perf_counter() #checks our time
        self.run_app = True #lets us know to run main loop
        self.data_in_queue = in_queue #data coming in to process
        self.data_out_queue = out_queue #data we processed and send out
        self.app_loop_process = multiprocessing.Process(target=self.app_loop) #main loop for facial rec
        self.face_encodings = faceencodings #known face encodings
        self.face_names = facenames #encoding names
        self.face_images = faceimages
        self.face_descriptions = facedescriptions
        self.unique_ids = uids
        self.current_face_locations = 0 #set default to 0
        #self.current_face_names = [] #our current face names detected
        self.last_time_check = time.perf_counter() #keeps track of the last time we checked face matches
        self.LAST_TIME_CHECK_RECHECK = 3 #we will recheck our time every this many seconds, no matter what
        self.current_faces_data = [] #list of all current FaceData we have
        self.previous_faces_data = []
        


    '''
        find_faces_data_name :
        returns True if we find name or False if we do not find it
    '''  
    def find_faces_data_name(self, name):
        
        for face_data in self.current_faces_data:
            if face_data.name == name:
                return True
        
        return False

    '''
        get_unique_id :
        Create our unique id for this name
    '''  
    def get_unique_id(self, name):
        #if name Unknown
        if name == 'Unknown':
            return self.create_unique_uuid4(name)
        
        #get our id and return it
        index = self.face_names.index(name)

        return self.unique_ids[index]

    '''
        create_unique_uuid4 :
        returns a unique uuid.uuid4 ID
    '''  
    def create_unique_uuid4(self, name):
        #setup vars needed
        needID = True
        id = None
        while needID:
            #create id and set needID to false, since we have one
            id = uuid.uuid4()
            needID = False

            #go through faces to make sure this ID is unique
            for face in self.current_faces_data:
                #if we found the id, set needID to True and break the for loop
                if face.id == id:
                    needID = True
                    break

        return id   

    '''
        app_loop :
        The main loop of the multiprocess.
    '''  
    def app_loop(self):
        #run while app active
        while self.run_app:
            #go through data for in queue if any available
            while not self.data_in_queue.empty():

                starttime = time.perf_counter()

                #get our tuple data of (locations, small_frame)
                locations, small_frame = self.data_in_queue.get()

                #make sure we have locations to use, else skip to next iteration of the while queue loop
                if(len(locations) == 0):
                    self.current_face_locations = len(locations)
                    continue

                #if we have no face encodings, just continue to next loop
                if len(self.face_encodings) == 0:
                    continue
                
                find = lambda searchList, elem: [i for i, x in enumerate(searchList) if x in elem]

                #if we have the same locations and our current face names are all known
                #and we havent exceeded our check time variable, then skip this loop with continue
                #if(len(locations) == self.current_face_locations and len(find(self.current_face_names, 'Unknown'))  == 0 and abs(time.perf_counter() - self.last_time_check) < self.LAST_TIME_CHECK_RECHECK):
                if(len(locations) == self.current_face_locations and self.find_faces_data_name('Unknown') and abs(time.perf_counter() - self.last_time_check) < self.LAST_TIME_CHECK_RECHECK):
                    #if we have same face count, all names are known and we arent over our time check amount, then just continue in loop
                    continue

                
                #print('app_loop checking faces')
                #update variables
                self.current_face_locations = len(locations)
                self.last_time_check = time.perf_counter()

                encodings = face_recognition.face_encodings(cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB), locations)

                #encodings = face_recognition.face_encodings(cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB), face_locations)

                ##face_encodings = copy.deepcopy(encodings)

                #names = []
                #confidences = []
                new_faces_data = []

                #go through each face encoding to see if we have a match
                for encoding in encodings:
                    results = face_recognition.compare_faces(self.face_encodings, encoding)
                    #results = face_recognition.compare_faces(self.face_encodings, encoding, tolerance=0.4)
                    name = "Unknown"
                    confidence = 'Not Known'
                    image = None
                    description = ''

                    #best_match_index = np.argmin(results)

                    face_distances = face_recognition.face_distance(self.face_encodings, encoding)
                    best_match_index = np.argmin(face_distances)

                    #if best_match_index >=0 and best_match_index < len(self.face_names):
                    if results[best_match_index]:
                        name = self.face_names[best_match_index]
                        #name + ' ' + self.face_confidence(face_distances[best_match_index])
                        confidence = self.face_confidence(face_distances[best_match_index])
                        image = self.face_images[best_match_index]
                        description = self.face_descriptions[best_match_index]

                    #lets get our unique ID
                    id = self.get_unique_id(name)

                    #get datetime
                    current_time = datetime.datetime.now()                   

                    #create our FaceData
                    fd = FaceData(id=id, name=name, description=description, date_time = current_time, image=image, confidence=confidence, encoder=encoding, frame=small_frame)                    

                    new_faces_data.append(fd)
                    #names.append(name)
                    #confidences.append(confidence)
                    
                    #names.append(f'{name} ({confidence})')

                #send out our new face data
                self.data_out_queue.put(new_faces_data)
                #send our list of names to out queue
                #self.data_out_queue.put((names, confidences))

                #set our new faces_data
                self.current_faces_data.clear()
                self.current_faces_data = new_faces_data.copy()

                #set our new names
                #self.current_face_names.clear()
                #self.current_face_names = names.copy()

                #starttime = abs(time.perf_counter() - starttime)
                #print('app_loop Time : ' + str(starttime))

    # https://www.youtube.com/watch?v=tl2eEBFEHqM
    '''
        face_confidence :
        Calculates the confidence this is the face we want.

        https://www.youtube.com/watch?v=tl2eEBFEHqM
    '''  
    def face_confidence(self, face_distance, face_match_threshold = 0.6):
        range = (1.0 - face_match_threshold)
        linear_val = (1.0 - face_distance) / (range * 2.0)

        if face_distance > face_match_threshold:
            return str(round(linear_val * 100, 2)) + '%'
        else:
            value = (linear_val + ((1.0 - linear_val) * math.pow((linear_val - 0.5) * 2, 0.2))) * 100
            return str(round(value, 2)) + '%'

    '''
        start :
        Starts main loop.
    '''  
    def start(self):
        self.app_loop_process.start()

    '''
        stop :
        Terminates the multiproccess.
    '''  
    def stop(self):
        #end our app loop and close it.
        #need to terminate, join (waits for it to end) and then close
        self.run_app = False
        self.app_loop_process.terminate()
        self.app_loop_process.join()
        self.app_loop_process.close()

'''
    check_face_data :
    check our face data and make sure there are no UUIDs to update
'''  
def check_face_data(data_dir):
    #load data
    in_data = load_Data(data_dir)
    out_data = copy.deepcopy(in_data)

    #create list for ids
    ids=[data[MAX_LINE_SIZE-1] for data in in_data if len(data) == MAX_LINE_SIZE]

    #now loop through all our data and create new UUIDS needed
    for i in range(len(out_data)):
        #see if we need an UUID
        if len(out_data[i]) < MAX_LINE_SIZE:
            #create UUID
            out_data[i].append(create_unique_id(ids))

            #now add this UUID to current ids
            ids.append(out_data[i][MAX_LINE_SIZE-1])

    #now rewrite to files
    write_Data(data_dir, in_data, out_data)

'''
    load_Data :
    Loads are face data array.
''' 
def load_Data(data_dir):
    #return data
    #data we are reading from files
    read_Data = []

    print('LOADING SAMPLE DATA FILES : ')

    #get all of our directories to be used
    directories = []
    for filename in os.listdir(data_dir):
        if os.path.isdir(os.path.join(data_dir, filename)):
            directories.append(os.path.join(data_dir, filename))

    for directory in directories:
        #get our first directory

        #now open the files in this directory
        for filename in os.listdir(directory):
            if os.path.join(directory, filename) == os.path.join(directory, 'Name'):

                #get our directory and then get our text file (will always be name.txt)
                name_direct = os.path.join(directory, filename)

                #make sure txt file is there
                for nameDirectFile in os.listdir(name_direct):
                    
                    #get the name of the file we are looking for and see if it exists
                    file_direct = os.path.join(name_direct, 'name.txt')
                    if os.path.join(name_direct, nameDirectFile) == file_direct:

                        #open the file and read in the name
                        with open(file_direct) as name_file:
                            #create our list of data and append to all data
                            data = [line for line in name_file.readlines()]
                            read_Data.append(data)
                            
    return read_Data

'''
    write_Data :
    Writes to the face data.
''' 
def write_Data(data_dir, in_data, out_data):

    print('WRITING SAMPLE DATA FILES : ')

    #get all of our directories to be used
    directories = []
    for filename in os.listdir(data_dir):
        if os.path.isdir(os.path.join(data_dir, filename)):
            directories.append(os.path.join(data_dir, filename))
    
    #used to go through our data. init to 0
    i = 0

    for directory in directories:

        #if we do not need to alter this file, then continue to next one
        if len(in_data[i]) == MAX_LINE_SIZE:
            #inc i
            i += 1

            continue

        #now open the files in this directory
        for filename in os.listdir(directory):

            if os.path.join(directory, filename) == os.path.join(directory, 'Name'):

                #get our directory and then get our text file (will always be name.txt)
                name_direct = os.path.join(directory, filename)

                #make sure txt file is there
                for nameDirectFile in os.listdir(name_direct):
                    
                    #get the name of the file we are looking for and see if it exists
                    file_direct = os.path.join(name_direct, 'name.txt')
                    if os.path.join(name_direct, nameDirectFile) == file_direct:

                        #open the file and append the UUID to end
                        with open(file_direct, 'a') as name_file:
                            name_file.writelines("\n" + str(out_data[i][MAX_LINE_SIZE-1]))                        

        #inc i
        i += 1

'''
    create_unique_id :
    create a new unique id thats not in our id list sent in
''' 
def create_unique_id(ids):
    #setup vars needed
    needID = True
    uid = None
    while needID:
        #create id and set needID to false, since we have one
        uid = uuid.uuid4()
        needID = False

        #go through ids sent in and if we find our uid in there, then set needID = True and break
        for id in ids:
            if id == uid:
                needID = True
                break

    return uid

'''
    load_face_data :
    Load all of our data and return it (see top and end of function)
''' 
def load_face_data(data_dir):

    #first check our face data and make sure there are no UUIDs to update
    check_face_data(data_dir)

    #return data
    images = []
    labels = []
    descriptions = []
    ids = []

    print('LOADING FACE DATA FILES : ')

    #get all of our directories to be used
    directories = []
    for filename in os.listdir(data_dir):
        if os.path.isdir(os.path.join(data_dir, filename)):
            directories.append(os.path.join(data_dir, filename))

    for directory in directories:
        #get our first directory
        #directory = os.path.join(data_dir, str(i))
        print(directory)
        temp_images = []

        #now open the files in this directory
        for filename in os.listdir(directory):
            if not os.path.isdir(os.path.join(directory, filename)):
                #temp_image = face_recognition.load_image_file(os.path.join(directory, filename))
                #temp_images.append(temp_image)

                temp_image = cv2.imread(os.path.join(directory, filename))

                #resize our image
                scale_percent = 50
                w = int(temp_image.shape[1] * scale_percent / 100)
                h = int(temp_image.shape[0] * scale_percent / 100)
                dim = (w,h)
                temp_image = cv2.resize(temp_image, dim, interpolation = cv2.INTER_AREA)

                temp_images.append(temp_image)
                #image = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
                

                #print(os.path.join(directory, filename))
            elif os.path.join(directory, filename) == os.path.join(directory, 'Name'):
                #print('NAME DIRECT')
                #print(os.path.join(directory, filename))

                #get our directory and then get our text file (will always be name.txt)
                name_direct = os.path.join(directory, filename)
                name_exists = False

                #make sure txt file is there
                for nameDirectFile in os.listdir(name_direct):
                    
                    #get the name of the file we are looking for and see if it exists
                    file_direct = os.path.join(name_direct, 'name.txt')
                    if os.path.join(name_direct, nameDirectFile) == file_direct:

                        #open the file and read in the name
                        with open(file_direct) as name_file:
                            data = [line for line in name_file.readlines()]                            

                            #name
                            labels.append(data[0])
                            name_exists = True
                            print('label added : ' + data[0])

                            #description
                            descriptions.append(data[1])

                            #UUID
                            ids.append(data[2])

                        break
                
                #if their name file doesnt exist, they are an unknown person
                if not name_exists:
                    labels.append('unknown person')

        #directory = os.path.join(directory, 'Name')
        #print(directory)

        images.append(temp_images)    

    #print('images ' + str(len(images)) + ', labels ' + str(len(labels)))

    for label in labels:
        index = labels.index(label)
        labels[index] = label.rstrip()

    return images, labels, descriptions, ids

'''
    load_update_pandas_db :
    This will load and update our database.
''' 
def load_update_pandas_db(filename1, filename2, labels, descriptions, ids, createFile2) -> tuple:
    
    #if no file1 or file2, then create both
    #createfile2, only if we ask for it or it does not exist
    if not file_exists(filename1) or not file_exists(filename2):
        #if we dont want to create file 2, make sure a file2 exists already
        if not createFile2 and not file_exists(filename2):
            df, df2 = create_pandas_db(filename1, filename2, labels, descriptions, ids, True, True)
        else:
            df, df2 = create_pandas_db(filename1, filename2, labels, descriptions, ids, True, createFile2)
            #load the df2
            dftemp, df2 = load_pandas_db(filename1, filename2)

        return df, df2
    #open files
    else:
        #load the dbs
        df, df2 = load_pandas_db(filename1, filename2)

        #now update them if needed
        df = update_pandas_db(df, labels, descriptions, ids, filename1, filename2)

        return df, df2

'''
    create_pandas_db :
    Creates a pandas db if needed.
''' 
def create_pandas_db(filename1, filename2, labels, descriptions, ids, createFile1, createFile2) -> tuple:
    
    #first get rid of '\n'
    l = []
    d = []
    i = []
    for label in labels:
        label = label.rstrip()
        l.append(label)    

    for description in descriptions:
        description = description.rstrip()
        d.append(description)

    for id in ids:
        id = id.rstrip()
        i.append(id)
    
    #create dataframe
    df = pd.DataFrame(list(zip(i, l, d)), columns=['UUID', 'Name', 'Description'] ) 
    df.set_index(['UUID'], inplace=True)
    if createFile1:
        df.to_csv(filename1)

    #if we need to create file 2
    if createFile2:
        df2 = pd.DataFrame(list(zip([], [], [], [])), columns=['UUID', 'Arrival Time', 'Departure Time', 'Total Time'] ) 
        df2.set_index(['UUID'], inplace=True)
        df2.to_csv(filename2)
    else:
        df2 = None

    return df, df2

'''
    load_pandas_db :
    Loads our databases.
''' 
def load_pandas_db(filename1, filename2) -> tuple:
    df = pd.read_csv(filename1)
    df.set_index(['UUID'], inplace=True)
    df2 = pd.read_csv(filename2)
    df2.set_index(['UUID'], inplace=True)

    return df, df2

'''
    update_pandas_db :
    Updates the databases.
''' 
def update_pandas_db(df1, labels, descriptions, ids, filename1, filename2) -> pd.DataFrame:
    n_ids = []
    n_labels = []
    n_descriptions = []
    #find ids not in the DB
    i = 0
    for id in ids:
        #if its not in the dataframe, then add it
        #if any(df1.UUID != id):
        if id not in df1.index:
            n_ids.append(id)
            n_labels.append(labels[i])
            n_descriptions.append(descriptions[i])
        i+=1

    #create a new dataframe from our new data
    #n_df = pd.DataFrame(list(zip(n_ids, n_labels, n_descriptions)), columns=['UUID', 'Name', 'Description'] )
    #n_df.set_index(['UUID'], inplace=True)
    
    #create if needed
    if(len(n_ids) > 0):
        n_df1, n_df2 = create_pandas_db(filename1, filename2,n_labels, n_descriptions, n_ids, True, False)    
        df1 = pd.concat([df1, n_df1])
        df1.to_csv(filename1)

    return df1

'''
    encode_known_people :
    This will send in our data and encode them with face_recognition. It will return encodings and labels.
''' 
def encode_known_people(images, labels):
    face_encodings = []
    face_names = []

    #loop through our images list    
    for image, label in zip(images, labels):
        encoding = face_recognition.face_encodings(cv2.cvtColor(image[0], cv2.COLOR_BGR2RGB))[0]
        face_encodings.append(encoding)
        face_names.append(label)

    return face_encodings, face_names
    
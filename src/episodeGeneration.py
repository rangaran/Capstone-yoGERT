# @file createEpisode.ipynb
# @author Team GIS Gang
# @brief This notebook aims to generate Trip Episodes based on the given datasets of points

import csv
import os
from csv import writer
import geopy as gp
import pandas as pd
import glob

#os.chdir("../src/")
path = os.path.dirname(os.path.abspath(__file__))
os.chdir(path) 







class EpisodeGeneration():
    # @param csv_path:
    # @param title:
    # @return an .csv file that consists of points
    def createTrace(self,csv_path, tracefolder_fullpath):

        #Create a trace folder

        try: 
            os.mkdir(tracefolder_fullpath)
            print("Trace folder created ") 

        except FileExistsError:
            print("Trace folder already exists")

        #Reads csv and store in data frame
        df = pd.read_csv(csv_path)
        df = df[["lat","long","time"]]
        df['time']= pd.to_datetime(df['time'])



        #Calculate stepsize using start and end time of dataset
        starttime = pd.to_datetime(df['time'].iloc[0])
        endtime = pd.to_datetime(df['time'].iloc[-1])
        totaltime = pd.Timedelta(endtime - starttime).seconds 

        if(totaltime == 0):
            stepsize = 1
        else:
            stepsize = (round(len(df)/totaltime)) 

        #Trim points based on step size
        if(stepsize != 0):
            df = df.drop(df[df.index%stepsize !=0].index)
            df = df.reset_index()
            df = df[["lat","long","time"]]
        
        df.reset_index()
        df['id'] = df.index

        #Saves trip points to csv file 
        df.to_csv(tracefolder_fullpath+"/trace.csv", index=False)


    #INPUT Trace.CSV
    #OUTPUT Segments.CSV
    def createSegments(self,tracefolder_fullpath):
        
        #Join the points cvs file by index n and n+1
        df = pd.read_csv(tracefolder_fullpath+"/trace.csv")
        df2= df.iloc[:-1 , :]
        df1 = df.tail(-1)
        df1 = df1.reset_index()


        velocities = pd.DataFrame(columns= ["start_lat","start_long","end_lat","end_long","start_time","end_time","total_time","total_distance","velocity","start_index","end_index"])
        velocities["start_lat"] = df1["lat"]
        velocities["start_long"] = df1["long"]
        velocities["end_lat"] = df2["lat"]
        velocities["end_long"] = df2["long"]
        velocities["start_time"] = pd.to_datetime(df1['time'])
        velocities["end_time"] =  pd.to_datetime(df2['time'])
        velocities["total_time"] = (velocities["end_time"] - velocities["start_time"]).dt.total_seconds().abs()
        velocities['total_distance'] = velocities.apply(lambda x: gp.distance.distance((x[0], x[1]), (x[2], x[3])).m, axis=1)
        velocities["start_index"] = df2['id']
        velocities["end_index"] =  df1['id']
        velocities['velocity'] = velocities['total_distance'] / (velocities['total_time'])

        #Saves trip segement to csv file
        velocities.to_csv(tracefolder_fullpath+"/segments.csv", index=False)



    #INPUT VELOCITY.CSV
    #OUTPUT EPISODE.CSV
    def findStops(self,tracefolder_fullpath):

        from enum import Enum
        class mode(Enum):
            STOP = 0
            WALK = 1.7
            DRIVE = 12
            MOVING = 99


        df = pd.read_csv(tracefolder_fullpath+"/segments.csv") 
        episode= pd.DataFrame(columns= ["start_lat","start_long","end_lat","end_long","start_time","end_time","start_index","end_index","mode"])



        #get starting mode 
        startVel = df['velocity'].iloc[0] 

        startIndex = 0
        currMode = mode.STOP
        if( startVel < mode.WALK.value):
            currMode = mode.STOP
        else:
            currMode = mode.MOVING



        for index in range(1,len(df)):

            endIndex = index - 1
            endVel =  df['velocity'].iloc[endIndex]

            if( endVel < mode.WALK.value):
                endMode = mode.STOP
            else:
                endMode = mode.MOVING

    
            if(currMode != endMode):
        
                new_row = [df['start_lat'].iloc[startIndex] ,
                    df['start_long'].iloc[startIndex] ,
                    df['end_lat'].iloc[endIndex] ,
                    df['end_long'].iloc[endIndex] ,
                    df['start_time'].iloc[startIndex],
                    df['end_time'].iloc[endIndex],
                    df['start_index'].iloc[startIndex],
                    df['end_index'].iloc[endIndex],
                    currMode]    
                episode.loc[len(episode)] = new_row
                currMode = endMode
                startIndex =index


        episode = episode.loc[(episode['mode'] == mode.STOP)]
        episode['middle_point'] = (episode['start_index'] + episode['end_index'])/2
        try: 
                os.mkdir(tracefolder_fullpath+"/stop")
                print("Trace folder created ") 

        except FileExistsError:
                print("Trace folder already exists")

        episode.to_csv(tracefolder_fullpath+"/stop/stops.csv", index=False)




    def cleanStops(self,tracefolder_fullpath, timetol, distol):
        stops= pd.read_csv(tracefolder_fullpath+"/stop/stops.csv") 
        droplist = []


        for index in range(len(stops)):
            starttime = pd.to_datetime(stops['start_time'].iloc[index]) 
            endtime = pd.to_datetime(stops['end_time'].iloc[index])
            timePassed = pd.Timedelta(endtime - starttime).seconds 
            if(timePassed > timetol and index < len(stops)-1):
                droplist.append(index)
            


        stops = stops.drop(droplist)


        stops.to_csv(tracefolder_fullpath+"/stop/stops.csv", index=False)


    ###
    def createEpisodes(self,tracefolder_fullpath):

        from enum import Enum
        class mode(Enum):
            STOP = 0
            WALK = 1.7
            DRIVE = 12
            MOVING = 99

        stops= pd.read_csv(tracefolder_fullpath+"/stop/stops.csv") 
        trace= pd.read_csv(tracefolder_fullpath+"/trace.csv") 
        segments = pd.read_csv(tracefolder_fullpath+"/segments.csv") 
        
        startindex = 0
        endindex = 0
        eid = 0

        try: 
                os.mkdir(str(tracefolder_fullpath+"/episode"))
                print("Trace folder created ") 

        except FileExistsError:
                print("Trace folder already exists")

        for index, row in stops.iterrows():
            endindex = row['start_index']
            if (row['start_index'] == 0):
                
                newepisode = trace.loc[row['start_index']:row['end_index']].copy()
                newepisode["mode"] = mode.STOP
                newepisode.to_csv(tracefolder_fullpath+"/episode/"+str(eid)+"_episode.csv", index=False)
                eid+=1
                startindex = row['end_index'] + 1



            else:
                newepisode = trace.loc[startindex:endindex-1].copy()
                

                medvelocity = segments.loc[(segments["start_index"] > startindex) & (segments["start_index"] < endindex),['velocity']].copy()
    
                medvelocity = medvelocity["velocity"].median()
        
                if( medvelocity < mode.DRIVE.value):
                    finalmode = mode.WALK
                else:
                    finalmode = mode.DRIVE

                newepisode["mode"] = finalmode
                newepisode.to_csv(tracefolder_fullpath+"/episode/"+str(eid)+"_episode.csv", index=False)
                startindex = row['end_index'] + 1
                eid+=1

                
                newepisode = trace.loc[ row['start_index']: row['end_index']].copy()
                newepisode["mode"] = mode.STOP
                newepisode.to_csv(tracefolder_fullpath+"/episode/"+str(eid)+"_episode.csv", index=False)
                eid+=1
        

        if (startindex == endindex == 1):
            endindex = len(trace)
            newepisode = trace.loc[startindex:endindex]
            

            medvelocity = segments.loc[(segments["start_index"] > startindex) & (segments["start_index"] < endindex),['velocity']]
    
            medvelocity = medvelocity["velocity"].median()

            if( medvelocity < mode.DRIVE.value):
                finalmode = mode.WALK
            else:
                finalmode = mode.DRIVE

            newepisode["mode"] = finalmode
            newepisode.to_csv(tracefolder_fullpath+"/episode/"+str(eid)+"_episode.csv", index=False)
            startindex = row['end_index'] + 1   
            eid+=1    

        elif(endindex != len(trace)):
            endindex = len(trace)
            newepisode = trace.loc[startindex:endindex]
            

            medvelocity = segments.loc[(segments["start_index"] > startindex) & (segments["start_index"] < endindex),['velocity']]

            medvelocity = medvelocity["velocity"].median()

            if( medvelocity < mode.DRIVE.value):
                finalmode = mode.WALK
            else:
                finalmode = mode.DRIVE

            newepisode["mode"] = finalmode
            newepisode.to_csv(tracefolder_fullpath+"/episode/"+str(eid)+"_episode.csv", index=False)
            startindex = row['end_index'] + 1   
            eid+=1         
                    

    def episodeGenerator(self,csv_path,tracefolder_path,title):
        tracefolder_fullpath = tracefolder_path+title
 
        self.createTrace(csv_path,tracefolder_fullpath)

        self.createSegments(tracefolder_fullpath)
        self.findStops(tracefolder_fullpath)
        self.cleanStops(tracefolder_fullpath,60,60)
        self.createEpisodes(tracefolder_fullpath)


    def summarymode(self,tracefilepath):
        from enum import Enum
        class mode(Enum):
            STOP = 0
            WALK = 1.7
            DRIVE = 12
            MOVING = 99
        modes = []


        
        files = glob.glob(os.path.dirname(tracefilepath)+'/episode'+ "/*.csv")
        print(files)
        
        for f in files:
            data = csv.reader(open(f))
            c = 0
            
            for line in data:
                
                if c>0: 
                    
                    modes.append(line[4])
                    
                    break
                
                c = c+1
        
        stats=os.path.dirname(tracefilepath)+'/summarymode.csv'
        with open(stats, 'w') as f1:
            writer_object = writer(f1)
            writer_object.writerow(['Summary Mode'])
            writer_object.writerow([str(mode(modes)) ])


# createVelocities("./Segment/trace1")
# generateEpisodes("./Segment/trace1")
# cleanEpisode("./Segment/trace1")

# createSegments("../src/exampleDataset/trace_2.csv","trace2")
# createVelocities("./Segment/trace2")
# generateEpisodes("./Segment/trace2")
# cleanEpisode("./Segment/trace2")

# createSegments("../src/exampleDataset/trace_3.csv","trace3")
# createSegments("./exampleDataset/trace_3.csv","trace3") 
# createVelocities("./Segment/trace3")
# generateEpisodes("./Segment/trace3")
# cleanEpisode("./Segment/trace3")
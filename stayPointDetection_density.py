# -*- coding: utf-8 -*-
# @Author  : zhang35
# @Time    : 2020/09/16 18:00
# @Function: extract stay points from a GPS log file (implementation of algorithm in [2])

# References:
# [1] Q. Li, Y. Zheng, X. Xie, Y. Chen, W. Liu, and W.-Y. Ma, "Mining user similarity based on location history", in Proceedings of the 16th ACM SIGSPATIAL international conference on Advances in geographic information systems, New York, NY, USA, 2008, pp. 34:1--34:10.
# [2] Jing Yuan, Yu Zheng, Liuhang Zhang, XIng Xie, and Guangzhong Sun. 2011. Where to find my next passenger. In Proceedings of the 13th international conference on Ubiquitous computing (UbiComp '11). Association for Computing Machinery, New York, NY, USA, 109–118.

# test data could be downloaded from: https://www.microsoft.com/en-us/download/confirmation.aspx?id=52367

import time
import os
import sys
from math import radians, cos, sin, asin, sqrt
import folium
import webbrowser

time_format = '%Y-%m-%d,%H:%M:%S'

# structure of point
class Point:
    def __init__(self, latitude, longitude, dateTime, arriveTime, leaveTime):
        self.latitude = latitude
        self.longitude = longitude
        self.dateTime = dateTime
        self.arriveTime = arriveTime
        self.leaveTime = leaveTime

# calculate distance between two points from their coordinate
def getDistanceOfPoints(pi, pj):
    lat1, lon1, lat2, lon2 = list(map(radians, [float(pi.latitude), float(pi.longitude), 
                                                float(pj.latitude), float(pj.longitude)]))
    dlon = lon2 - lon1 
    dlat = lat2 - lat1 
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a)) 
    m = 6371000 * c
    return m

# calculate time interval between two points
def getTimeIntervalOfPoints(pi, pj):
    t_i = time.mktime(time.strptime(pi.dateTime, time_format))
    t_j = time.mktime(time.strptime(pj.dateTime, time_format))
    return t_j - t_i

# compute mean coordinates of a group of points
def computMeanCoord(gpsPoints):
    lat = 0.0
    lon = 0.0
    for point in gpsPoints:
        lat += float(point.latitude)
        lon += float(point.longitude)
    return (lat/len(gpsPoints), lon/len(gpsPoints))

# extract stay points from a GPS log file
# input:
#        file: the name of a GPS log file
#        distThres: distance threshold
#        timeThres: time span threshold
# default values of distThres and timeThres are 200 m and 30 min respectively, according to [1]
def stayPointExtraction(points, distThres = 200, timeThres = 30*60):
    stayPointCenterList= []
    stayPointList = []
    pointNum = len(points)
    i = 0
    while i < pointNum - 1: 
        # j: index of the last point within distTres
        j = i + 1
        flag = False
        while j < pointNum:
            if getDistanceOfPoints(points[i], points[j]) < distThres:
                j += 1
            else:
                break

        j -= 1
        # at least one point found within distThres
        if j > i:
            # candidate cluster found
            if getTimeIntervalOfPoints(points[i], points[j]) > timeThres: 
                nexti = i + 1
                j += 1
                while j < pointNum:
                    if getDistanceOfPoints(points[nexti], points[j]) < distThres and \
                        getTimeIntervalOfPoints(points[nexti], points[j]) > timeThres: 
                        nexti += 1
                        j += 1
                    else:
                        break
                j -= 1
                latitude, longitude = computMeanCoord(points[i : j+1])
                arriveTime = time.mktime(time.strptime(points[i].dateTime, time_format))
                leaveTime = time.mktime(time.strptime(points[j].dateTime, time_format))
                dateTime = time.strftime(time_format, time.localtime(arriveTime)), time.strftime(time_format, time.localtime(leaveTime))
                stayPointCenterList.append(Point(latitude, longitude, dateTime, arriveTime, leaveTime))
                stayPointList.extend(points[i : j+1])
        i = j + 1
    return stayPointCenterList, stayPointList

# add points into mapDots (type: folium.map.FeatureGroup())
def addPoints(mapDots, points, color):
    for p in points:
        mapDots.add_child(folium.CircleMarker(
            [p.latitude, p.longitude], 
            radius=4,
            tooltip=p.dateTime,
            color=color
            ))

# parse lines into points
def parseGeoTxt(lines):
    points = []
    for line in lines:
        field_pointi = line.rstrip().split(',')
        latitude = float(field_pointi[0])
        longitude = float(field_pointi[1])
        dateTime = field_pointi[-2]+','+field_pointi[-1]
        points.append(Point(latitude, longitude, dateTime, 0, 0))
    return points

def main():
    m = folium.Map(location=[40.007814,116.319764])
    mapDots = folium.map.FeatureGroup()

    count = 0
    for dirname, dirnames, filenames in os.walk(sys.path[0] + '/Data'):
        filenum = len(filenames)
        print(filenum , "files found")
        for filename in filenames:
            if  filename.endswith('plt'):
                gpsfile = os.path.join(dirname, filename)
                print("processing:" ,  gpsfile) 
                log = open(gpsfile, 'r')
                lines = log.readlines()[6:] # first 6 lines are useless
                points = parseGeoTxt(lines)
                stayPointCenter, stayPoint = stayPointExtraction(points)
                addPoints(mapDots, points, "yellow")

                if len(stayPointCenter) > 0:
                    # add pionts to a group to be shown on map
                    addPoints(mapDots, stayPoint, "blue")
                    addPoints(mapDots, stayPointCenter, "red")

                    # writen into file ./StayPoint/*.plt
                    spfile = gpsfile.replace('Data', 'StayPoint').replace('.plt', '_density.plt')
                    if not os.path.exists(os.path.dirname(spfile)):
                        os.makedirs(os.path.dirname(spfile))
                    spfile_handle = open(spfile, 'w+')
                    print('Extracted stay points:\nlaltitude\tlongitude\tarriving time\tleaving time', file=spfile_handle)
                    for sp in stayPointCenter:
                        print(sp.latitude, sp.longitude, time.strftime(time_format, time.localtime(sp.arriveTime)), time.strftime(time_format, time.localtime(sp.leaveTime)), file=spfile_handle)
                    spfile_handle.close()

                    print("writen into:" ,  spfile) 
                    count += 1
                else:
                    print(gpsfile , "has no stay point")
        print(count, "out of" , filenum , "files contain stay points")

    # show stay points on map
    m.add_child(mapDots)
    m.save(sys.path[0] + "/index2.html")
    webbrowser.open(sys.path[0] + "/index2.html")
if __name__ == '__main__':
    main()
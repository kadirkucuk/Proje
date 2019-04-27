import numpy as np
import math
import arcpy
import os
from arcpy import env
from time import strftime
# ------------------------------------------------------------------------------------------------
Input2 = arcpy.GetParameterAsText(0)
Input1 = arcpy.GetParameterAsText(1)
directory = arcpy.GetParameterAsText(2) # Projenin olduğu dosya
Choice = arcpy.GetParameterAsText(3)
# ------------------------------------------------------------------------------------------------
field = "hausdorff" # Hausdorff Uzaklıklarının Olduğu Sütun
field2 = "TOPODETAYA"
field3 = "name"
new_shapefile = "Hausdorff_Analysis.shp" # Kesişen poligonların veri seti
new_shapefile2 ="Non_Overlaps.shp"
field_type = "Double"
field_type2 = "String"
feature_type = "POLYGON"
overlapping_features = os.path.join(directory,new_shapefile) # Veri setinin dosya Konumu
Non_Overlap = os.path.join(directory,new_shapefile2)
# ------------------------------------------------------------------------------------------------
# Test to see if the output feature class already exists
if arcpy.Exists(overlapping_features):
   # Delete it if it does
   arcpy.Delete_management(overlapping_features)
if arcpy.Exists(Non_Overlap):
    arcpy.Delete_management(Non_Overlap)
# ------------------------------------------------------------------------------------------------
arcpy.CreateFeatureclass_management(directory, new_shapefile, feature_type) # Yeni layer oluşturur
arcpy.CreateFeatureclass_management(directory, new_shapefile2, feature_type)
arcpy.AddField_management(overlapping_features, field, field_type) # Öznitelik tablosuna yeni sütun ekler
arcpy.AddField_management(overlapping_features, field2, field_type2)
arcpy.AddField_management(overlapping_features, field3, field_type2)
arcpy.AddField_management(Non_Overlap, field3, field_type2)
# ------------------------------------------------------------------------------------------------
# Hausdorff uzaklığını hesaplar
def Hausdorff_dist(poly_a,poly_b):
    dist_lst = []
    for i in range(len(poly_a)):
        dist_min = 1000.0
        for j in range(len(poly_b)):
            dist = math.sqrt((poly_a[i].X - poly_b[j].X)**2+(poly_a[i].Y - poly_b[j].Y)**2)
            if dist_min > dist:
                dist_min = dist
        dist_lst.append(dist_min)
    hausdorff = np.max(dist_lst)
    return hausdorff
# ------------------------------------------------------------------------------------------------
# Köşe noktalarını hesaplar
def polygon_vertices(p1):
    for points1 in p1:
        return points1
# ------------------------------------------------------------------------------------------------
# Poligonu veri setine ekler
def insert_cursor(base_polygon,insert_polygon):
    cursor = arcpy.da.InsertCursor(base_polygon, ['SHAPE@'])
    cursor.insertRow([insert_polygon])
# ------------------------------------------------------------------------------------------------
# Listedeki hausdorff uzaklıklarını öznitelik tablosuna ekler
def update_cursor(base_polygon,polygon_field,list):
    pointer = 0
    with arcpy.da.UpdateCursor(base_polygon, polygon_field) as cursor4:
        for a in cursor4:
            a[0] = list[pointer]
            pointer += 1
            cursor4.updateRow(a)

# ------------------------------------------------------------------------------------------------
def Hausdorff_Analysis_Centroid(Input1,Input2):
    cursors1 = []
    cursors3 = []
    fields_OSM = ["OID@", "SHAPE@", "SHAPE@TRUECENTROID","name"]
    with arcpy.da.SearchCursor(Input1, fields_OSM) as cursor:
        for row in cursor:
            cursors1.append(row)
            cursors3.append(row)
    cursors2 = []
    fields_reference = ["OID@", "SHAPE@","TOPODETAYA"]
    with arcpy.da.SearchCursor(Input2,fields_reference ) as cursor2:
        for rows in cursor2:
            cursors2.append(rows)
    errors = 0
    hausdorff_list = []
    TOPODETAY_list = []
    OSM_list = []
    Non_Overlap_OSM_Attribute = []
    for row in cursors1:
        try:
            distance = 10000000
            polygon1 = row[1]
            o = row[2][0]
            k = row[2][1]
            point = arcpy.Point(o, k)
            Matching = False
            for rows in cursors2:
                polygon2 = rows[1]
                if polygon2.contains(point):
                    Matching = True
                    result = Hausdorff_dist(polygon_vertices(row[1]), polygon_vertices(rows[1]))
                    if distance > result:
                        distance = result
                        topodetay = rows[2]
                        osm_name = row[3]
                    break
            if Matching is True:
                hausdorff_list.append(distance)
                insert_cursor(overlapping_features,polygon1)
                TOPODETAY_list.append(topodetay)
                OSM_list.append(osm_name)
                cursors3.remove(row)
        except:
            errors +=1
    update_cursor(overlapping_features, field, hausdorff_list)
    update_cursor(overlapping_features, field2, TOPODETAY_list)
    update_cursor(overlapping_features, field3, OSM_list)
    for i in cursors3:
        try:
            insert_cursor(Non_Overlap,i[1])
            Non_Overlap_OSM_Attribute.append(i[3])
        except:
            errors +=1
    update_cursor(Non_Overlap, field3, Non_Overlap_OSM_Attribute)
# ------------------------------------------------------------------------------------------------
def Hausdorff_Analysis_Overlap(Input1,Input2):
    cursors1 = []
    cursors3 = []
    field_OSM = ["OID@", "SHAPE@","name"]
    with arcpy.da.SearchCursor(Input1, field_OSM) as cursor:
        for row in cursor:
            cursors1.append(row)
            cursors3.append(row)
    cursors2 = []
    field_reference = ["OID@", "SHAPE@","TOPODETAYA"]
    with arcpy.da.SearchCursor(Input2, field_reference) as cursor2:
        for rows in cursor2:
            cursors2.append(rows)
    errors = 0
    hausdorff_list = []
    TOPODETAY_list = []
    OSM_list = []
    Non_Overlap_OSM_Attribute = []
    for row in cursors1:
        try:
            distance = 1000000
            polygon1 = row[1]
            Matching = False
            for rows in cursors2:
                polygon2 = rows[1]
                if polygon1.overlaps(polygon2):
                    Matching = True
                    result = Hausdorff_dist(polygon_vertices(row[1]), polygon_vertices(rows[1]))
                    if distance > result:
                        distance = result
                        topodetay = rows[2]
                        osm_name = row[2]
            if Matching is True:
                hausdorff_list.append(distance)
                insert_cursor(overlapping_features, polygon1)
                TOPODETAY_list.append(topodetay)
                OSM_list.append(osm_name)
                cursors3.remove(row)
        except:
            errors +=1
        del row
    update_cursor(overlapping_features, field, hausdorff_list)
    update_cursor(overlapping_features, field2, TOPODETAY_list)
    update_cursor(overlapping_features, field3, OSM_list)
    for i in cursors3:
        try:
            insert_cursor(Non_Overlap,i[1])
            Non_Overlap_OSM_Attribute.append(i[2])
        except:
            errors +=1
    update_cursor(Non_Overlap, field3, Non_Overlap_OSM_Attribute)
# Poligon kesişimlerini kontrol eden ve kesişim varsa gerekli fonksiyonların çalışmasını sağlar
# ------------------------------------------------------------------------------------------------
if Choice == "Hausdorff Analysis With Centroid Method":
    Hausdorff_Analysis_Centroid(Input1, Input2)
elif Choice == "Hausdorff Analysis With Overlap Method":
    Hausdorff_Analysis_Overlap(Input1,Input2)
# ------------------------------------------------------------------------------------------------
# get the map document
mxd = arcpy.mapping.MapDocument("CURRENT")

# get the data frame
df = arcpy.mapping.ListDataFrames(mxd,"*")[0]

# create a new layer
newlayer = arcpy.mapping.Layer(overlapping_features)
newlayer2 = arcpy.mapping.Layer(Non_Overlap)
# add the layer to the map at the bottom of the TOC in data frame 0
arcpy.mapping.AddLayer(df, newlayer,"BOTTOM")
arcpy.mapping.AddLayer(df, newlayer2,"BOTTOM")

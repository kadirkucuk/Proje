import numpy as np
import math
import arcpy
import os
arcpy.env.overwriteOutput = True
# ------------------------------------------------------------------------------------------------
Input1 = arcpy.GetParameterAsText(0)
Input2 = arcpy.GetParameterAsText(1)
directory = arcpy.GetParameterAsText(2)
Choice = arcpy.GetParameterAsText(3)
Threshold = arcpy.GetParameterAsText(4)
dsc_topovt = arcpy.Describe(Input1)
coord_sys_topovt = dsc_topovt.spatialReference
# ------------------------------------------------------------------------------------------------
field = "hausdorff"  # Hausdorff distance field
field2 = "TOPODETAYA"
field3 = "name"
new_shapefile = "Hausdorff_Analysis.shp"  # Overlapping features
new_shapefile2 = "Non_Overlaps.shp"
new_shapefile3 = "KUCUKBINA_Analysis.shp"
new_shapefile4 = "KUCUKBINA_Non_Overlaps.shp"
field_type = "Double"
field_type2 = "String"
feature_type = "POLYGON"
overlapping_features = os.path.join(directory,new_shapefile) # Veri setinin dosya Konumu
Non_Overlap = os.path.join(directory,new_shapefile2)
KUCUKBINA = os.path.join(directory,new_shapefile3)
KUCUKBINA_Non_Overlaps = os.path.join(directory,new_shapefile4)
# ------------------------------------------------------------------------------------------------
# Calculates Hausdorff distance
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
# Gets vertices
def polygon_vertices(p1):
    for points1 in p1:
        return points1
# ------------------------------------------------------------------------------------------------
# Poligonu veri setine ekler
def insert_cursor(base_polygon,polygon):
    cursor = arcpy.da.InsertCursor(base_polygon, ['SHAPE@'])
    for i in polygon:
        cursor.insertRow([i])
# ------------------------------------------------------------------------------------------------
# Listedeki hausdorff uzaklıklarını öznitelik tablosuna ekler
def update_cursor(base_polygon,polygon_field,list):
    pointer = 0
    with arcpy.da.UpdateCursor(base_polygon, polygon_field) as cursor:
        for a in cursor:
            a[0] = list[pointer]
            pointer += 1
            cursor.updateRow(a)
# ------------------------------------------------------------------------------------------------
def KUCUKBINA_Analysis(Input1,Input2,Threshold):
    fields_OSM = ["OID@", "SHAPE@",  "name","SHAPE@TRUECENTROID"]
    cursor_osm = [ cursor for cursor in arcpy.da.SearchCursor(Input2, fields_OSM)]
    fields_reference = ["OID@", "SHAPE@", "TOPODETAYA","SHAPE@TRUECENTROID"]
    cursor_topovt = [cursor for cursor in arcpy.da.SearchCursor(Input1,fields_reference )]
    errors = 0
    # ----------------------------------------------------------
    poly_list = []
    Point_TOPODETAY = []
    Point_TOPODETAY2 = []
    Point_name = []
    Point_name2 = []
    for topovt in cursor_topovt:
        try:
            poly_list2 = []
            count = 0
            Matching = False
            point = arcpy.Point(topovt[3][0], topovt[3][1])
            for osm in cursor_osm:
                dist = math.sqrt((topovt[3][0] - osm[3][0]) ** 2 + (topovt[3][1] - osm[3][1]) ** 2)
                if dist < int(Threshold):
                    if osm[1].contains(point):
                        Matching = True
                        Point_TOPODETAY2 = topovt[2]
                        Point_name2 = osm[2]
                        poly_list2 = osm[1]
                        count = count+1
                        cursor_osm.remove(osm)
            if Matching is True:
                if count == 1:
                    Point_TOPODETAY.append(Point_TOPODETAY2)
                    poly_list.append(poly_list2)
                    Point_name.append(Point_name2)
        except:
            errors = +1
    insert_cursor(KUCUKBINA, poly_list)
    update_cursor(KUCUKBINA, field2, Point_TOPODETAY)
    update_cursor(KUCUKBINA, field3, Point_name)

    Non_Overlap_OSM_Attribute = []
    Non_Overlap_list = []

    for i in cursor_osm:
        try:
            Non_Overlap_list.append(i[1])
            Non_Overlap_OSM_Attribute.append(i[2])
        except:
            errors +=1
    insert_cursor(KUCUKBINA_Non_Overlaps, Non_Overlap_list)
    update_cursor(KUCUKBINA_Non_Overlaps, field3, Non_Overlap_OSM_Attribute)
# ------------------------------------------------------------------------------------------------
def Hausdorff_Analysis_Centroid(Input1,Input2,Threshold):
    fields_OSM = ["OID@","SHAPE@", "SHAPE@TRUECENTROID", "name"]
    cursors1 = [cursor for cursor in arcpy.da.SearchCursor(Input2, fields_OSM)]
    fields_reference = ["OID@","SHAPE@", "TOPODETAYA","SHAPE@TRUECENTROID"]
    cursors2 = [cursor for cursor in arcpy.da.SearchCursor(Input1,fields_reference )]
    errors = 0
    hausdorff_list = []
    TOPODETAY_list = []
    OSM_list = []
    Non_Overlap_OSM_Attribute = []
    polygon_list = []
    Non_Overlap_list = []
    for topovt in cursors2:
        try:
            for osm in cursors1:
                dist = math.sqrt((topovt[3][0] - osm[2][0]) ** 2 + (topovt[3][1] - osm[2][1]) ** 2)
                if dist < int(Threshold):
                    point = arcpy.Point(osm[2][0], osm[2][1])
                    if topovt[1].contains(point):
                        result = Hausdorff_dist(polygon_vertices(osm[1]), polygon_vertices(topovt[1]))
                        hausdorff_list.append(result)
                        TOPODETAY_list.append(topovt[2])
                        OSM_list.append(osm[3])
                        polygon_list.append(osm[1])
                        cursors1.remove(osm)
                        break
        except:
            errors +=1
    insert_cursor(overlapping_features, polygon_list)
    update_cursor(overlapping_features, field, hausdorff_list)
    update_cursor(overlapping_features, field2, TOPODETAY_list)
    update_cursor(overlapping_features, field3, OSM_list)

    for i in cursors1:
        try:
            Non_Overlap_list.append(i[1])
            Non_Overlap_OSM_Attribute.append(i[3])
        except:
            errors +=1
    insert_cursor(Non_Overlap, Non_Overlap_list)
    update_cursor(Non_Overlap, field3, Non_Overlap_OSM_Attribute)

# ------------------------------------------------------------------------------------------------
def Hausdorff_Analysis_Overlap(Input1,Input2,Threshold):
    fields_OSM = ["OID@", "SHAPE@",  "name","SHAPE@TRUECENTROID"]
    cursors1 = [ cursor for cursor in arcpy.da.SearchCursor(Input2, fields_OSM)]
    fields_reference = ["OID@", "SHAPE@", "TOPODETAYA","SHAPE@TRUECENTROID"]
    cursors2 = [cursor for cursor in arcpy.da.SearchCursor(Input1,fields_reference )]
    errors = 0
    # ----------------------------------------------------------
    hausdorff_list = []
    TOPODETAY_list = []
    OSM_list = []
    Non_Overlap_OSM_Attribute = []
    Non_Overlap_list = []
    polygon_list = []
    for topovt in cursors2:
        try:
            distance = 1000000
            Matching = False
            for osm in cursors1:
                dist = math.sqrt((osm[3][0] - topovt[3][0]) ** 2 + (osm[3][1] - topovt[3][1]) ** 2)
                if dist < int(Threshold):
                    if osm[1].overlaps(topovt[1]):
                        Matching = True
                        result = Hausdorff_dist(polygon_vertices(osm[1]), polygon_vertices(topovt[1]))
                        if distance > result:
                            distance = result
                            topodetay = topovt[2]
                            osm_name = osm[2]
                            cursors1.remove(osm)
            if Matching is True:
                hausdorff_list.append(distance)
                polygon_list.append(topovt[1])
                TOPODETAY_list.append(topodetay)
                OSM_list.append(osm_name)
        except:
            errors +=1

    insert_cursor(overlapping_features, polygon_list)
    update_cursor(overlapping_features, field, hausdorff_list)
    update_cursor(overlapping_features, field2, TOPODETAY_list)
    update_cursor(overlapping_features, field3, OSM_list)
    for i in cursors1:
        try:
            Non_Overlap_list.append(i[1])
            Non_Overlap_OSM_Attribute.append(i[2])
        except:
            errors +=1
    insert_cursor(Non_Overlap, Non_Overlap_list)
    update_cursor(Non_Overlap, field3, Non_Overlap_OSM_Attribute)
# Poligon kesişimlerini kontrol eden ve kesişim varsa gerekli fonksiyonların çalışmasını sağlar
# ------------------------------------------------------------------------------------------------
if Choice == "Hausdorff Analysis With Centroid Method":
    arcpy.CreateFeatureclass_management(directory, new_shapefile, feature_type)
    arcpy.CreateFeatureclass_management(directory, new_shapefile2, feature_type)
    arcpy.AddField_management(overlapping_features, field, field_type)
    arcpy.AddField_management(overlapping_features, field2, field_type2)
    arcpy.AddField_management(overlapping_features, field3, field_type2)
    arcpy.AddField_management(Non_Overlap, field3, field_type2)
    arcpy.DefineProjection_management(overlapping_features, coord_sys_topovt)
    arcpy.DefineProjection_management(Non_Overlap, coord_sys_topovt)
    Hausdorff_Analysis_Centroid(Input1, Input2,Threshold)
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd, "*")[0]
    newlayer = arcpy.mapping.Layer(overlapping_features)
    newlayer2 = arcpy.mapping.Layer(Non_Overlap)
    arcpy.mapping.AddLayer(df, newlayer, "BOTTOM")
    arcpy.mapping.AddLayer(df, newlayer2, "BOTTOM")
elif Choice == "Hausdorff Analysis With Overlap Method":
    arcpy.CreateFeatureclass_management(directory, new_shapefile, feature_type)
    arcpy.CreateFeatureclass_management(directory, new_shapefile2, feature_type)
    arcpy.AddField_management(overlapping_features, field, field_type)
    arcpy.AddField_management(overlapping_features, field2, field_type2)
    arcpy.AddField_management(overlapping_features, field3, field_type2)
    arcpy.AddField_management(Non_Overlap, field3, field_type2)
    arcpy.DefineProjection_management(overlapping_features, coord_sys_topovt)
    arcpy.DefineProjection_management(Non_Overlap, coord_sys_topovt)
    Hausdorff_Analysis_Overlap(Input1,Input2,Threshold)
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd, "*")[0]
    newlayer = arcpy.mapping.Layer(overlapping_features)
    newlayer2 = arcpy.mapping.Layer(Non_Overlap)
    arcpy.mapping.AddLayer(df, newlayer, "BOTTOM")
    arcpy.mapping.AddLayer(df, newlayer2, "BOTTOM")
elif Choice == "KUCUKBINA Analizi":
    arcpy.CreateFeatureclass_management(directory, new_shapefile3, feature_type)
    arcpy.CreateFeatureclass_management(directory, new_shapefile4, feature_type)
    arcpy.AddField_management(KUCUKBINA, field2, field_type2)
    arcpy.AddField_management(KUCUKBINA, field3, field_type2)
    arcpy.AddField_management(KUCUKBINA_Non_Overlaps, field3, field_type2)
    arcpy.DefineProjection_management(KUCUKBINA, coord_sys_topovt)
    arcpy.DefineProjection_management(KUCUKBINA_Non_Overlaps, coord_sys_topovt)
    KUCUKBINA_Analysis(Input1,Input2,Threshold)
    mxd = arcpy.mapping.MapDocument("CURRENT")
    df = arcpy.mapping.ListDataFrames(mxd,"*")[0]
    newlayer3 = arcpy.mapping.Layer(KUCUKBINA)
    newlayer2 = arcpy.mapping.Layer(KUCUKBINA_Non_Overlaps)
    arcpy.mapping.AddLayer(df, newlayer2, "BOTTOM")
    arcpy.mapping.AddLayer(df, newlayer3,"BOTTOM")
# ------------------------------------------------------------------------------------------------
import numpy as np
import math
import arcpy
import os
from arcpy import env
from time import strftime
# ------------------------------------------------------------------------------------------------
Input1 = arcpy.GetParameterAsText(0) # Load the First Feature Layer
Input2 = arcpy.GetParameterAsText(1) #  Load the Second Feature Layer
directory = arcpy.GetParameterAsText(2) # Set the File Location
Choice = arcpy.GetParameterAsText(3)# Select the Method
# ------------------------------------------------------------------------------------------------
field = "hausdorff" #Field Name
new_shapefile = "Hausdorff_Analysis.shp" #Layer name
field_type = "Double" # Field Type
feature_type = "POLYGON" # Layer Type
overlapping_features = os.path.join(directory,new_shapefile) # File location of the layer to add a matching polygon
Non_Overlap = os.path.join(directory,new_shapefile2) # File location of the Non overlapping polygons
# ------------------------------------------------------------------------------------------------
# Test to see if the output feature class already exists
if arcpy.Exists(overlapping_features):
   # Delete it if it does
   arcpy.Delete_management(overlapping_features)
# Test to see if the output feature class already exists
if arcpy.Exists(Non_Overlap):
    # Delete it if it does
    arcpy.Delete_management(Non_Overlap)
# ------------------------------------------------------------------------------------------------
arcpy.CreateFeatureclass_management(directory, new_shapefile, feature_type) # Create new layer
arcpy.CreateFeatureclass_management(directory, new_shapefile2, feature_type)# Create new layer
arcpy.AddField_management(overlapping_features, field, field_type) # Adds new column to attribute table
# ------------------------------------------------------------------------------------------------
#Calculates Hausdorff distance
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
#Finds coordinates of vertices
def polygon_vertices(p1):
    for points1 in p1:
        return points1
# ------------------------------------------------------------------------------------------------
# Adds the polygon to the layer
def insert_cursor(base_polygon,insert_polygon):
    cursor = arcpy.da.InsertCursor(base_polygon, ['SHAPE@'])
    cursor.insertRow([insert_polygon])
# ------------------------------------------------------------------------------------------------
# Adds the hausdorff distances found in the attribute table
def update_cursor(base_polygon,polygon_field,list):
    pointer = 0
    with arcpy.da.UpdateCursor(base_polygon, polygon_field) as cursor4:
        for a in cursor4:
            a[0] = list[pointer]
            pointer += 1
            cursor4.updateRow(a)

# ------------------------------------------------------------------------------------------------
# It checks the match according to the Centroid Method and adds polygons to a new layer if there is a match.
def Hausdorff_Analysis_Centroid(Input1,Input2):
    cursors1 = []
    with arcpy.da.SearchCursor(Input1, ["OID@", "SHAPE@"]) as cursor:
        for row in cursor:
            cursors1.append(row)
    cursors2 = []
    with arcpy.da.SearchCursor(Input2, ["OID@", "SHAPE@", "SHAPE@TRUECENTROID"]) as cursor2:
        for rows in cursor2:
            cursors2.append(rows)
    hausdorff_list = []
    errors = 0
    for row in cursors1:
        try:
            polygon1 = arcpy.Polygon(polygon_vertices(row[1]))
            overlaps = False
            hausdorff_list2 = []
            for rows in cursors2:
                o = rows[2][0]
                k = rows[2][1]
                point = arcpy.Point(o, k)
                if polygon1.contains(point):
                    overlaps = True
                    result = Hausdorff_dist(polygon_vertices(row[1]), polygon_vertices(rows[1]))
                    hausdorff_list2.append(result)
                    cursors2.remove(rows)
            if overlaps is True:
                insert_cursor(overlapping_features,polygon1)
                result2 = min(hausdorff_list2)
                hausdorff_list.append(result2)
        except:
            errors +=1
        del row
    update_cursor(overlapping_features, field, hausdorff_list)
    for i in cursors2:
        polygon = arcpy.Polygon(polygon_vertices(i[1]))
        insert_cursor(Non_Overlap,polygon)
# ------------------------------------------------------------------------------------------------
# It checks the match according to the Overlap Method and adds polygons to a new layer if there is a match.
def Hausdorff_Analysis_Overlap(Input1,Input2):
    cursors1 = []
    with arcpy.da.SearchCursor(Input1, ["OID@", "SHAPE@"]) as cursor:
        for row in cursor:
            cursors1.append(row)
    cursors2 = []
    with arcpy.da.SearchCursor(Input2, ["OID@", "SHAPE@", "SHAPE@TRUECENTROID"]) as cursor2:
        for rows in cursor2:
            cursors2.append(rows)
    hausdorff_list = []
    errors = 0
    for row in cursors1:
        try:
            polygon1 = arcpy.Polygon(polygon_vertices(row[1]))
            overlaps = False
            hausdorff_list2 = []
            for rows in cursors2:
                polygon2 = arcpy.Polygon(polygon_vertices(rows[1]))
                if polygon1.overlaps(polygon2):
                    overlaps = True
                    result = Hausdorff_dist(polygon_vertices(row[1]), polygon_vertices(rows[1]))
                    hausdorff_list2.append(result)
                    cursors2.remove(rows)
            if overlaps is True:
                insert_cursor(overlapping_features,polygon1)
                result2 = min(hausdorff_list2)
                hausdorff_list.append(result2)
        except:
            errors +=1
        del row
    update_cursor(overlapping_features, field, hausdorff_list)
    for i in cursors2:
        polygon = arcpy.Polygon(polygon_vertices(i[1]))
        insert_cursor(Non_Overlap,polygon)

# ------------------------------------------------------------------------------------------------
# Choose one of the methods

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

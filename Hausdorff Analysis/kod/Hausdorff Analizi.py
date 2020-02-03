import numpy as np
import math
import arcpy
import os
arcpy.env.overwriteOutput = True
# ------------------------------------------------------------------------------------------------
TOPOVT_BUYUKBINA_Verisi = arcpy.GetParameterAsText(0) #TOPOVT BUYUKBINA katmanı
TOPOVT_KUCUKBINA_Verisi = arcpy.GetParameterAsText(1) #TOPOVT KUCUKBINA katmanı
OSM_Verisi = arcpy.GetParameterAsText(2) #OSM bina katmanı
Konum = arcpy.GetParameterAsText(3) # Çıktıların kaydedileceği dosya konumu
Yontem = arcpy.GetParameterAsText(4) # Kullanılacak Yöntem
Esik_Deger_KUCUKBINA = arcpy.GetParameterAsText(5) # KUCUKBINA Eşik Değeri
Esik_Deger_Opsiyonel = arcpy.GetParameterAsText(6) # BUYUKBINA Eşik Değeri
dsc_topovt = arcpy.Describe(TOPOVT_BUYUKBINA_Verisi) # TOPOVT'nin koordinat sistemini tanımlama
coordinat_sistem_topovt = dsc_topovt.spatialReference 
# ------------------------------------------------------------------------------------------------
if Esik_Deger_Opsiyonel: # Eğer büyük bina analizi için ayrıca bir eşik değeri verilirse kullan
    Esik_Deger_BUYUKBINA = Esik_Deger_Opsiyonel
else: # Eğer büyük bina analizi için ayrıca bir eşik değeri verilmezse küçük bina analizinin eşik değerini kullan
    Esik_Deger_BUYUKBINA = Esik_Deger_KUCUKBINA

# ------------------------------------------------------------------------------------------------
# Burada katmanların ve özniteliklerin ve veri tiplerinin adları tanımlanır
Hausdorff_mesafesi = "hausdorff" 
topodetaya = "TOPODETAYA"
isim = "name"
m_uzaklik = "Mesafe"
ortusme_orani = "Ortusme"
field_type = "Double"
field_type2 = "String"
feature_type = "POLYGON"
Eslesen_Binalar = os.path.join(Konum,"Eslesen_Binalar.shp")
Eslesmeyen_Binalar = os.path.join(Konum,"Eslesmeyen_Binalar.shp")
KUCUKBINA_Eslesenler = os.path.join(Konum,"KUCUKBINA_Eslesenler.shp")
KUCUKBINA_Eslesmeyenler = os.path.join(Konum,"KUCUKBINA_Eslesmeyenler.shp")
# ------------------------------------------------------------------------------------------------
# Bu fonksiyon Hausdorff mesafesini hesaplar
def Hausdorff_dist(poly_a,poly_b):
    mesafe_listesi = [] # Boş bir liste açılır
    mesafe_listesi_a = []
    mesafe_listesi_b = []
    for i in range(len(poly_a)): # a poligonunun her bir köşesinden
        minimum_mesafe = 1000.0 # Başlangıç olarak belirlenen minimum mesafe.
        for j in range(len(poly_b)): # b poligonunun her bir köşesine
            mesafe = math.sqrt((poly_a[i].X - poly_b[j].X)**2+(poly_a[i].Y - poly_b[j].Y)**2) # Köşeler arasındaki mesafe hesaplanır
            if minimum_mesafe > mesafe: # Eğer hesaplanan mesafe minimum mesafeden büyükse
                minimum_mesafe = mesafe # minimum mesafe hesaplanan mesafe olur
        mesafe_listesi_a.append(minimum_mesafe) # a Poligonunun bir köşe noktasının b poligonundaki en yakın köşe noktasının arasındaki mesafe listeye eklenir
    mesafe_listesi.append(np.max(mesafe_listesi_a)) # En küçük uzaklıklar arasındaki en büyük değer Hausdorff mesafesi olur
    for k in range(len(poly_b)): # a poligonunun her bir köşesinden
        minimum_mesafe = 1000.0 # Başlangıç olarak belirlenen minimum mesafe.
        for l in range(len(poly_a)): # b poligonunun her bir köşesine
            mesafe = math.sqrt((poly_a[l].X - poly_b[k].X)**2+(poly_a[l].Y - poly_b[k].Y)**2) # Köşeler arasındaki mesafe hesaplanır
            if minimum_mesafe > mesafe: # Eğer hesaplanan mesafe minimum mesafeden büyükse
                minimum_mesafe = mesafe # minimum mesafe hesaplanan mesafe olur
        mesafe_listesi_b.append(minimum_mesafe) # a Poligonunun bir köşe noktasının b poligonundaki en yakın köşe noktasının arasındaki mesafe listeye eklenir
    mesafe_listesi.append(np.max(mesafe_listesi_b)) # En küçük uzaklıklar arasındaki en büyük değer Hausdorff mesafesi olur
    return (np.min(mesafe_listesi))
# ------------------------------------------------------------------------------------------------
# Bu fonksiyon köşe noktalarını bulur
def polygon_vertices(p1):
    for nokta in p1:
        return nokta
# ------------------------------------------------------------------------------------------------
def ortusme(poligon1, poligon2):
    ortusen_alan = poligon1.intersect(poligon2, 4)
    toplam_alan = poligon1.area + poligon2.area - ortusen_alan.area
    oran = ortusen_alan.area/toplam_alan
    return (oran*100)
# Bu fonksiyon poligonları katmana ekler
def insert_cursor(base_polygon,polygon):
    cursor = arcpy.da.InsertCursor(base_polygon, ['SHAPE@'])
    for i in polygon:
        cursor.insertRow([i])
# ------------------------------------------------------------------------------------------------
# Bu fonksiyon öznitelikleri katmandaki öznitelik tablosuna ekler
def update_cursor(base_polygon,polygon_field,list):
    pointer = 0
    with arcpy.da.UpdateCursor(base_polygon, polygon_field) as cursor:
        for a in cursor:
            a[0] = list[pointer]
            pointer += 1
            cursor.updateRow(a)
# ------------------------------------------------------------------------------------------------
# Bu fonksiyon KUCUKBINA analizini yapar
def KUCUKBINA_Analizi(Girdi1,Girdi2,Esik_Deger):
    OSM_sutunlari = ["OID@", "SHAPE@",  "name","SHAPE@TRUECENTROID"] # Analizde kullanılacak özelliklerin listesi
    cursor_osm = [ cursor for cursor in arcpy.da.SearchCursor(Girdi2, OSM_sutunlari)] # OSM verisinin özelliklerini sorgular
    cursor_osm2 = cursor_osm[:]
    TOPOVT_sutunlari = ["OID@", "SHAPE@", "TOPODETAYA","SHAPE@TRUECENTROID"] # Analizde kullanılacak özelliklerin listesi
    cursor_topovt = [cursor for cursor in arcpy.da.SearchCursor(Girdi1,TOPOVT_sutunlari )] # TOPOVT verisinin özelliklerini sorgular
    hatalar = 0
    # ----------------------------------------------------------
    # Boş listeler açılır
    poly_list = []
    Nokta_TOPODETAY = []
    Nokta_TOPODETAY2 = []
    Nokta_adi = []
    Nokta_adi2 = []
    mesafe_listesi = []
    for topovt in cursor_topovt: # Her bir TOPOVT binasından
        try:
            poly_list2 = []
            eslesme_sayisi = 0
            Eslesme = False
            for osm in cursor_osm: # Her bir OSM binasına
                mesafe = math.sqrt((topovt[3][0] - osm[3][0]) ** 2 + (topovt[3][1] - osm[3][1]) ** 2) # Binaların merkezleri arasındaki mesafe
                if mesafe < int(Esik_Deger): # Eşik değerden büyükse
                    Eslesme = True # Eşleşme vardır
                    merkezler_arasi_mesafe = mesafe
                    Nokta_TOPODETAY2 = topovt[2] # Topodetay numarası
                    Nokta_adi2 = osm[2] # OSM poligonunun adı
                    poly_list2 = osm[1] # Eşleşen OSM poligonu
                    eslesme_sayisi = eslesme_sayisi+1 # Eşleşme sayısını 1 arttır
                    cursor_osm2.remove(osm) # Eşleşen OSM poligonunu ekle
            if Eslesme is True:
                if eslesme_sayisi == 1: # Eğer TOPOVT poligonu sadece 1 OSM poligonu ile eşleşiyorsa
                    mesafe_listesi.append(merkezler_arasi_mesafe)
                    Nokta_TOPODETAY.append(Nokta_TOPODETAY2) # Topodetay numarasını listeye ekle
                    poly_list.append(poly_list2) # OSM poligonunu listeye ekle 
                    Nokta_adi.append(Nokta_adi2) # OSM poligonun adını listeye ekle
        except:
            hatalar = +1
    insert_cursor(KUCUKBINA_Eslesenler, poly_list) # Eşleşen OSM poligonunu katmana ekle
    update_cursor(KUCUKBINA_Eslesenler, topodetaya, Nokta_TOPODETAY) # Topodetay numarasını ekle
    update_cursor(KUCUKBINA_Eslesenler, isim, Nokta_adi) # OSM poligonunun ismini öznitelik tablosuna ekle
    update_cursor(KUCUKBINA_Eslesenler, m_uzaklik, mesafe_listesi)
    Eslesmeyen_Oznitelik = []
    Eslesmeyen_Binalar = []

    for i in cursor_osm2: # Kalan OSM poligonlarını Eşleşmeyen binalara ekle
        try:
            Eslesmeyen_Binalar.append(i[1])
            Eslesmeyen_Oznitelik.append(i[2])
        except:
            hatalar +=1
    insert_cursor(KUCUKBINA_Eslesmeyenler, Eslesmeyen_Binalar) # Eşleşmeyen OSM poligonunu katmana ekle
    update_cursor(KUCUKBINA_Eslesmeyenler, isim, Eslesmeyen_Oznitelik) # OSM poligonunun ismini öznitelik tablosuna ekle
# ------------------------------------------------------------------------------------------------
# Bu fonksiyon eşik değer yöntemine göre Hausdorff analizini yapar
def Esik_Deger_Yontemi(Girdi1,Girdi2,Esik_Deger):
    OSM_oznitelik = ["OID@", "SHAPE@",  "name","SHAPE@TRUECENTROID"] # Analizde kullanılacak özelliklerin listesi
    cursors1 = [ cursor for cursor in arcpy.da.SearchCursor(Girdi2, OSM_oznitelik)] # OSM verisinin özelliklerini sorgular
    cursors3 = cursors1[:]
    TOPOVT_oznitelik = ["OID@", "SHAPE@", "TOPODETAYA","SHAPE@TRUECENTROID"] # Analizde kullanılacak özelliklerin listesi
    cursors2 = [cursor for cursor in arcpy.da.SearchCursor(Girdi1,TOPOVT_oznitelik )] # TOPOVT verisinin özelliklerini sorgular
    errors = 0
    # ----------------------------------------------------------
    # Boş listeler açılır
    hausdorff_listesi = []
    TOPODETAY_listesi = []
    OSM_listesi = []
    Eslesmeyen_oznitelik = []
    Eslesmeyenler_listesi = []
    poligon_listesi = []
    ortusme_orani_listesi = []
    for topovt in cursors2: # Her bir TOPOVT poligonundan
        try:
            eslesme_sayisi = 0
            Eslesme = False
            for osm in cursors1: # Her bir OSM poligonuna
                mesafe = math.sqrt((osm[3][0] - topovt[3][0]) ** 2 + (osm[3][1] - topovt[3][1]) ** 2) # Binaların merkezleri arasındaki mesafe
                if mesafe < int(Esik_Deger): # Merkezler arasındaki mesafe eşik değerden küçükse
                    Eslesme = True # Eşleşme vardır
                    ortusme_yuzdesi = ortusme(topovt[1], osm[1])
                    Hausdorff = Hausdorff_dist(polygon_vertices(osm[1]), polygon_vertices(topovt[1])) # Hausdorff mesafesini hesapla
                    topodetay = topovt[2] # Topodetay numarası
                    osm_isim = osm[2] # OSM poligonun adı
                    eslesme_sayisi = eslesme_sayisi + 1 # Eşleşme sayısını 1 arttır
                    cursors3.remove(osm) # OSM poligonunu kaldır
            if Eslesme is True:
                if eslesme_sayisi == 1: # Yalnızca 1-1 eşleşme varsa
                    ortusme_orani_listesi.append(ortusme_yuzdesi)
                    hausdorff_listesi.append(Hausdorff) # Hausdorff mesafesini listeye ekle
                    poligon_listesi.append(topovt[1]) # TOPOVT poligonunu listeye ekle
                    TOPODETAY_listesi.append(topodetay) # Topodetay numarasını listeye ekle
                    OSM_listesi.append(osm_isim) # OSM poligonunun adını listeye ekle
        except:
            errors += 1
    insert_cursor(Eslesen_Binalar, poligon_listesi) # Eşleşen TOPOVT poligonlarını Eslesen_Binalar katmanına ekle
    update_cursor(Eslesen_Binalar, Hausdorff_mesafesi, hausdorff_listesi) # Listedeki Hausdorff mesafelerini Eslesen_Binalar katmanının öznitelik tablosuna ekle
    update_cursor(Eslesen_Binalar, topodetaya, TOPODETAY_listesi) # Listedeki topodetay numaralarını Eslesen_Binalar katmanının öznitelik tablosuna ekle
    update_cursor(Eslesen_Binalar, isim, OSM_listesi) # Listedeki OSM poligonlarının isimleri Eslesen_Binalar katmanının öznitelik tablosuna ekle
    update_cursor(Eslesen_Binalar, ortusme_orani, ortusme_orani_listesi)
    for i in cursors3:
        try:
            Eslesmeyenler_listesi.append(i[1]) # Eslesmeyen OSM poligonunu listeye ekle
            Eslesmeyen_oznitelik.append(i[2]) # Eslesmeyen OSM poligonunun adını listeye ekle
        except:
            errors +=1
    insert_cursor(Eslesmeyen_Binalar, Eslesmeyenler_listesi) # Eslesmeyen OSM poligonlarını Eslesmeyen_Binalar katmanına ekle
    update_cursor(Eslesmeyen_Binalar, isim, Eslesmeyen_oznitelik) # Eslesmeyen OSM poligonlarının adlarını Eslesmeyen_Binalar katmanının öznitelik tablosuna ekle
# ------------------------------------------------------------------------------------------------
# Bu fonksiyon merkez tabanlı yönteme göre Hausdorff analizi yapar
def Merkez_Tabanli_Yontem(Girdi1,Girdi2):
    OSM_Oznitelik = ["OID@","SHAPE@", "SHAPE@TRUECENTROID", "name"] # Analizde kullanılacak özellikler
    cursors1 = [cursor for cursor in arcpy.da.SearchCursor(Girdi2, OSM_Oznitelik)] # OSM katmanının özelliklerini sorgula
    TOPOVT_Oznitelik = ["OID@","SHAPE@", "TOPODETAYA","SHAPE@TRUECENTROID"] # Analizde kullanılacak özellikler
    cursors2 = [cursor for cursor in arcpy.da.SearchCursor(Girdi1,TOPOVT_Oznitelik )] # TOPOVT katmanının özelliklerini sorgula
    hatalar = 0
    # Boş listeler açılır
    hausdorff_listesi = []
    TOPODETAY_listesi = []
    OSM_listesi = []
    Eslesmeyen_OSM_oznitelik = []
    poligon_listesi = []
    Eslesmeyenler_listesi = []
    ortusme_orani_listesi = []
    for topovt in cursors2: # Her bir TOPOVT poligonundan
        for osm in cursors1: # Her bir OSM poligonuna
            try:
                OSM_nokta = arcpy.Point(osm[2][0], osm[2][1]) # OSM poligonunun merkezini tanımla
                if topovt[1].contains(OSM_nokta): # OSM poligonunun merkezi TOPOVT poligonun içerisindeyse eşleşme vardır
                    Hausdorff = Hausdorff_dist(polygon_vertices(osm[1]), polygon_vertices(topovt[1])) # Hausdorff mesafesini hesapla
                    ortusme_orani_yuzdesi = ortusme(topovt[1],osm[1])
                    ortusme_orani_listesi.append(ortusme_orani_yuzdesi)
                    hausdorff_listesi.append(Hausdorff) # Hausdorff mesafesini listeye ekle
                    TOPODETAY_listesi.append(topovt[2]) # Topodetay numarasını listeye ekle
                    OSM_listesi.append(osm[3]) # OSM poligonunun adını listeye ekle
                    poligon_listesi.append(topovt[1]) # Eşleşen TOPOVT poligonunu listeye ekle 
                    cursors1.remove(osm) # Eşleşen OSM poligonunu kaldır
                    break
            except:
                hatalar +=1
    insert_cursor(Eslesen_Binalar, poligon_listesi) # Listedeki TOPOVT poligonlarını Eslesen_Binalar katmanına ekle
    update_cursor(Eslesen_Binalar, Hausdorff_mesafesi, hausdorff_listesi) # Listedeki Hausdorff mesafelerini Eslesen_Binalar katmanının öznitelik tablosuna ekle
    update_cursor(Eslesen_Binalar, topodetaya, TOPODETAY_listesi) # Listedeki topodetay numaralarını Eslesen_Binalar katmanının öznitelik tablosuna ekle
    update_cursor(Eslesen_Binalar, isim, OSM_listesi) # Listedeki OSM poligonlarının adlarını Eslesen_Binalar katmanına ekle
    update_cursor(Eslesen_Binalar, ortusme_orani, ortusme_orani_listesi)
    for i in cursors1:
        try:
            Eslesmeyenler_listesi.append(i[1]) # Eşleşmeyen OSM poligonlarını listeye ekle
            Eslesmeyen_OSM_oznitelik.append(i[3]) # Eşleşmeyen OSM poligonlarının adlarını listeye ekle
        except:
            hatalar +=1
    insert_cursor(Eslesmeyen_Binalar, Eslesmeyenler_listesi) # Listedeki poligonları Eslesmeyen_Binalar katmanına ekle
    update_cursor(Eslesmeyen_Binalar, isim, Eslesmeyen_OSM_oznitelik) # Listedeki OSM poligonlarının adlarını Eslesmeyen_Binalar katmanının öznitelik tablosuna ekle

# ------------------------------------------------------------------------------------------------
# Bu fonksiyon örtüşme yöntemine göre Hausdorff analizi yapar
def Ortusme_Yontemi(Girdi1,Girdi2):
    OSM_Oznitelik = ["OID@", "SHAPE@",  "name","SHAPE@TRUECENTROID"] # Analizde kullanılacak özellikler
    cursors1 = [ cursor for cursor in arcpy.da.SearchCursor(Girdi2, OSM_Oznitelik)] # OSM katmanının özelliklerini sorgula
    TOPOVT_Oznitelik = ["OID@", "SHAPE@", "TOPODETAYA","SHAPE@TRUECENTROID"] # Analizde kullanılacak özellikler
    cursors2 = [cursor for cursor in arcpy.da.SearchCursor(Girdi1,TOPOVT_Oznitelik)] # TOPOVT katmanının özelliklerini sorgula
    hatalar = 0
    # Boş listeler açılır
    hausdorff_listesi = []
    TOPODETAY_listesi = []
    OSM_listesi = []
    Eslesmeyen_OSM_oznitelik = []
    Eslesmeyenler_listesi = []
    poligon_listesi = []
    ortusme_orani_listesi = []
    for topovt in cursors2: # Her bir TOPOVT poligonundan
        try:
            eslesme_sayisi = 0
            Eslesme = False
            for osm in cursors1: # Her bir OSM poligonuna
                if osm[1].overlaps(topovt[1]): # Eğer TOPOVT ve OSM poligonları örtüşüyor ise
                    Eslesme = True # Eşleşme vardır
                    mesafe = Hausdorff_dist(polygon_vertices(osm[1]), polygon_vertices(topovt[1])) # Hausdorff mesafesini hesapla
                    Hausdorff = mesafe
                    ortusme_orani_yuzdesi = ortusme(topovt[1],osm[1])
                    topodetay = topovt[2] # Topodetay numarası
                    osm_isim = osm[2] # OSM poligonun adı
                    eslesme_sayisi = eslesme_sayisi + 1  # Eşleşme sayısını 1 arttır
                    cursors1.remove(osm) # Eşleşen OSM poligonunu kaldır
            if Eslesme is True:
                if eslesme_sayisi == 1: # Eğer sadece 1-1 eşleşme varsa
                    ortusme_orani_listesi.append(ortusme_orani_yuzdesi)
                    hausdorff_listesi.append(Hausdorff) # Hausdorff mesafesini listeye ekle
                    poligon_listesi.append(topovt[1]) # TOPOVT poligonunu listeye ekle
                    TOPODETAY_listesi.append(topodetay) # Topodetay numarasını listeye ekle
                    OSM_listesi.append(osm_isim) # OSM poligonunun adını listeye ekle
        except:
            hatalar +=1
    insert_cursor(Eslesen_Binalar, poligon_listesi) # Listedeki poligonları Eslesen_Binalar katmanına ekle
    update_cursor(Eslesen_Binalar, Hausdorff_mesafesi, hausdorff_listesi) # Listedeki Hausdorff mesafelerini Eslesen_Binalar katmanının öznitelik tablosuna ekle
    update_cursor(Eslesen_Binalar, topodetaya, TOPODETAY_listesi) # Listedeki topodetay numaralarını Eslesen_Binalar katmanının öznitelik tablosuna ekle
    update_cursor(Eslesen_Binalar, isim, OSM_listesi) # Listedeki OSM poligonlarının adlarını Eslesen_Binlar katmanının öznitelik tablosuna ekle
    update_cursor(Eslesen_Binalar, ortusme_orani, ortusme_orani_listesi)
    for i in cursors1:
        try:
            Eslesmeyenler_listesi.append(i[1]) # Eslesmeyen OSM poligonlarını listeye ekle
            Eslesmeyen_OSM_oznitelik.append(i[2]) # Eslesmeyen OSM poligonlarının adlarını listeye ekle
        except:
            hatalar +=1
    insert_cursor(Eslesmeyen_Binalar, Eslesmeyenler_listesi) # Listedeki poligonları Eslesmeyen_Binalar katmanına ekle
    update_cursor(Eslesmeyen_Binalar, isim, Eslesmeyen_OSM_oznitelik) # Listedeki OSM poligonlarının adlarını Eslesmeyen_Binalar katmanının öznitelik tablosuna ekle
# ------------------------------------------------------------------------------------------------
if Yontem == "Esik Deger Yontemi": # Eğer eşik değer yöntemi seçilirse
    arcpy.CreateFeatureclass_management(Konum, "KUCUKBINA_Eslesenler.shp", feature_type) # KUCUKBINA_Eslesenler.shp dosyasını oluştur
    arcpy.CreateFeatureclass_management(Konum, "KUCUKBINA_Eslesmeyenler.shp", feature_type) # KUCUKBINA_Eslesmeyenler.shp dosyasını oluştur
    arcpy.AddField_management(KUCUKBINA_Eslesenler, topodetaya, field_type2) # KUCUKBINA_Eslesenler katmanının öznitelik tablosuna topodetaya sütununu ekle
    arcpy.AddField_management(KUCUKBINA_Eslesenler, isim, field_type2) # KUCUKBINA_Eslesenler katmanının öznitelik tablosuna isim sütununu ekle
    arcpy.AddField_management(KUCUKBINA_Eslesenler, m_uzaklik, field_type)
    arcpy.AddField_management(KUCUKBINA_Eslesmeyenler, isim, field_type2) # KUCUKBINA_Eslesmeyenler katmanının öznitelik tablosuna isim sütununu ekle
    KUCUKBINA_Analizi(TOPOVT_KUCUKBINA_Verisi,OSM_Verisi,Esik_Deger_KUCUKBINA) # Küçükbina analizini yap
    arcpy.CreateFeatureclass_management(Konum, "Eslesen_Binalar.shp", feature_type) # Eslesen_Binalar.shp dosyasını oluştur
    arcpy.CreateFeatureclass_management(Konum, "Eslesmeyen_Binalar.shp", feature_type) # Eslesmeyen_Binalar.shp dosyasını oluştur
    arcpy.AddField_management(Eslesen_Binalar, Hausdorff_mesafesi, field_type) # Eslesen_Binalar katmanının öznitelik tablosuna Hausdorff sütununu ekle
    arcpy.AddField_management(Eslesen_Binalar, topodetaya, field_type2) # Eslesen_Binalar katmanının öznitelik tablosuna topodetaya sütununu ekle
    arcpy.AddField_management(Eslesen_Binalar, isim, field_type2) # Eslesen_Binalar katmanının öznitelik tablosuna isim sütununu ekle
    arcpy.AddField_management(Eslesen_Binalar, ortusme_orani, field_type)
    arcpy.AddField_management(Eslesmeyen_Binalar, isim, field_type2) # Eslesmeyen_Binalar katmanının öznitelik tablosuna isim sütununu ekle
    # Sonraki 4 satır koordinat sistemlerini tanımlar
    arcpy.DefineProjection_management(KUCUKBINA_Eslesenler, coordinat_sistem_topovt)
    arcpy.DefineProjection_management(KUCUKBINA_Eslesmeyenler, coordinat_sistem_topovt)
    arcpy.DefineProjection_management(Eslesen_Binalar, coordinat_sistem_topovt)
    arcpy.DefineProjection_management(Eslesmeyen_Binalar, coordinat_sistem_topovt)
    Esik_Deger_Yontemi(TOPOVT_BUYUKBINA_Verisi,KUCUKBINA_Eslesmeyenler,Esik_Deger_BUYUKBINA) # Eşik değer yönteminin fonksiyonunu çalıştır
elif Yontem == "Ortusme Yontemi":
    arcpy.CreateFeatureclass_management(Konum, "KUCUKBINA_Eslesenler.shp", feature_type) # KUCUKBINA_Eslesenler.shp dosyasını oluştur
    arcpy.CreateFeatureclass_management(Konum, "KUCUKBINA_Eslesmeyenler.shp", feature_type) # KUCUKBINA_Eslesmeyenler.shp dosyasını oluştur
    arcpy.AddField_management(KUCUKBINA_Eslesenler, topodetaya, field_type2) # KUCUKBINA_Eslesenler katmanının öznitelik tablosuna topodetaya sütununu ekle
    arcpy.AddField_management(KUCUKBINA_Eslesenler, isim, field_type2) # KUCUKBINA_Eslesenler katmanının öznitelik tablosuna isim sütununu ekle
    arcpy.AddField_management(KUCUKBINA_Eslesenler, m_uzaklik, field_type)
    arcpy.AddField_management(KUCUKBINA_Eslesmeyenler, isim, field_type2) # KUCUKBINA_Eslesmeyenler katmanının öznitelik tablosuna isim sütununu ekle
    KUCUKBINA_Analizi(TOPOVT_KUCUKBINA_Verisi,OSM_Verisi,Esik_Deger_KUCUKBINA) # Küçükbina analizini yap
    arcpy.CreateFeatureclass_management(Konum, "Eslesen_Binalar.shp", feature_type) # Eslesen_Binalar.shp dosyasını oluştur
    arcpy.CreateFeatureclass_management(Konum, "Eslesmeyen_Binalar.shp", feature_type) # Eslesmeyen_Binalar.shp dosyasını oluştur
    arcpy.AddField_management(Eslesen_Binalar, Hausdorff_mesafesi, field_type) # Eslesen_Binalar katmanının öznitelik tablosuna Hausdorff sütununu ekle
    arcpy.AddField_management(Eslesen_Binalar, topodetaya, field_type2) # Eslesen_Binalar katmanının öznitelik tablosuna topodetaya sütununu ekle
    arcpy.AddField_management(Eslesen_Binalar, isim, field_type2) # Eslesen_Binalar katmanının öznitelik tablosuna isim sütununu ekle
    arcpy.AddField_management(Eslesen_Binalar, ortusme_orani, field_type)
    arcpy.AddField_management(Eslesmeyen_Binalar, isim, field_type2) # Eslesmeyen_Binalar katmanının öznitelik tablosuna isim sütununu ekle
    # Sonraki 4 satır koordinat sistemlerini tanımlar
    arcpy.DefineProjection_management(KUCUKBINA_Eslesenler, coordinat_sistem_topovt)
    arcpy.DefineProjection_management(KUCUKBINA_Eslesmeyenler, coordinat_sistem_topovt)
    arcpy.DefineProjection_management(Eslesen_Binalar, coordinat_sistem_topovt)
    arcpy.DefineProjection_management(Eslesmeyen_Binalar, coordinat_sistem_topovt)
    Ortusme_Yontemi(TOPOVT_BUYUKBINA_Verisi,KUCUKBINA_Eslesmeyenler) # Örtüşme yönteminin fonksiyonunu çalıştır
elif Yontem == "Merkez Tabanli Yontem":
    arcpy.CreateFeatureclass_management(Konum, "KUCUKBINA_Eslesenler.shp", feature_type) # KUCUKBINA_Eslesenler.shp dosyasını oluştur
    arcpy.CreateFeatureclass_management(Konum, "KUCUKBINA_Eslesmeyenler.shp", feature_type) # KUCUKBINA_Eslesmeyenler.shp dosyasını oluştur
    arcpy.AddField_management(KUCUKBINA_Eslesenler, topodetaya, field_type2) # KUCUKBINA_Eslesenler katmanının öznitelik tablosuna topodetaya sütununu ekle
    arcpy.AddField_management(KUCUKBINA_Eslesenler, isim, field_type2) # KUCUKBINA_Eslesenler katmanının öznitelik tablosuna isim sütununu ekle
    arcpy.AddField_management(KUCUKBINA_Eslesenler, m_uzaklik, field_type)
    arcpy.AddField_management(KUCUKBINA_Eslesmeyenler, isim, field_type2) # KUCUKBINA_Eslesmeyenler katmanının öznitelik tablosuna isim sütununu ekle
    KUCUKBINA_Analizi(TOPOVT_KUCUKBINA_Verisi,OSM_Verisi,Esik_Deger_KUCUKBINA) # Küçükbina analizini yap
    arcpy.CreateFeatureclass_management(Konum, "Eslesen_Binalar.shp", feature_type) # Eslesen_Binalar.shp dosyasını oluştur
    arcpy.CreateFeatureclass_management(Konum, "Eslesmeyen_Binalar.shp", feature_type) # Eslesmeyen_Binalar.shp dosyasını oluştur
    arcpy.AddField_management(Eslesen_Binalar, Hausdorff_mesafesi, field_type) # Eslesen_Binalar katmanının öznitelik tablosuna Hausdorff sütununu ekle
    arcpy.AddField_management(Eslesen_Binalar, topodetaya, field_type2) # Eslesen_Binalar katmanının öznitelik tablosuna topodetaya sütununu ekle
    arcpy.AddField_management(Eslesen_Binalar, isim, field_type2) # Eslesen_Binalar katmanının öznitelik tablosuna isim sütununu ekle
    arcpy.AddField_management(Eslesen_Binalar, ortusme_orani, field_type)
    arcpy.AddField_management(Eslesmeyen_Binalar, isim, field_type2) # Eslesmeyen_Binalar katmanının öznitelik tablosuna isim sütununu ekle
    # Sonraki 4 satır koordinat sistemlerini tanımlar
    arcpy.DefineProjection_management(KUCUKBINA_Eslesenler, coordinat_sistem_topovt)
    arcpy.DefineProjection_management(KUCUKBINA_Eslesmeyenler, coordinat_sistem_topovt)
    arcpy.DefineProjection_management(Eslesen_Binalar, coordinat_sistem_topovt)
    arcpy.DefineProjection_management(Eslesmeyen_Binalar, coordinat_sistem_topovt)
    Merkez_Tabanli_Yontem(TOPOVT_BUYUKBINA_Verisi,KUCUKBINA_Eslesmeyenler) # Merkez tabanlı yöntemin fonksiyonunu çalıştır
# Aşağıdaki satırlar katmanların ArcMap yazılımında gösterilmesini sağlar
mxd = arcpy.mapping.MapDocument("CURRENT")
df = arcpy.mapping.ListDataFrames(mxd, "*")[0]
newlayer1 = arcpy.mapping.Layer(KUCUKBINA_Eslesenler)
newlayer2 = arcpy.mapping.Layer(KUCUKBINA_Eslesmeyenler)
newlayer3 = arcpy.mapping.Layer(Eslesen_Binalar)
newlayer4 = arcpy.mapping.Layer(Eslesmeyen_Binalar)
arcpy.mapping.AddLayer(df, newlayer1, "BOTTOM")
arcpy.mapping.AddLayer(df, newlayer2,"BOTTOM")
arcpy.mapping.AddLayer(df, newlayer3, "BOTTOM")
arcpy.mapping.AddLayer(df, newlayer4, "BOTTOM")
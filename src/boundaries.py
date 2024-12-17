import geopandas as gpd
import pandas as pd
from unidecode import unidecode

"""
While analyzing all datasets, I found some issues in the boundaries provided by GADM:
- most polygons are not well defined - when visualized, they don't cover the whole neighborhood, like can cut residence areas or streets
- the administratives are not updated, i.e. old names, old governing territory, etc.

In an effort of looking for well refined boundaries, I found an public project City Scope which supported HCMC's city planning.
I haven't found any source for other cities yet.
For now, I'll replace the GADM's HCMC boundaries with CityScope's 
"""
title_dict = {
    'tp.': 'Thành Phố',
    't.': 'Tỉnh',
    'q.': 'Quận',
    'tx.': 'ThịXã',
    'h.': 'Huyện',
    'p.': 'Phường',
    'tt.': 'ThịTrấn',
    'x.': 'Xã',
    'thành phố': 'ThànhPhố',
    'thànhphố': 'ThànhPhố',
    'tỉnh': 'Tỉnh',
    'quận': 'Quận',
    'thị xã': 'ThịXã',
    'thịxã': 'ThịXã',
    'huyện': 'Huyện',
    'phường': 'Phường',
    'thị trấn': 'ThịTrấn',
    'thịtrấn': 'ThịTrấn',
    'xã': 'Xã',
    'trungtâmhuấnluyện': 'TTHL',
    'đảo': 'Huyện'
}

title_en_list = ['thanhpho','tinh','quan','thixa','huyen','phuong','thitran','xa','trungtamhuanluyen','dao']

def remove_title(name, title_list):
    for title in title_list:
        if name.lower().startswith(title):
            return name[len(title):].strip()
    return name

def correct_title(title):
    for old, new in title_dict.items():
        if title.lower().startswith(old):
            return new
    return title    

def convert_en(name):
    name_en = unidecode(name).lower().replace(" ", "")
    return name_en

def read_gadm(level, cols):
    gdf = gpd.read_file(r"data\gadm41_VNM_"+level+".json")
    gdf = gdf[gdf.columns[cols]]
    
    # STEP 1: Some admin names have titles to differentiate with other similar names, e.g. "CaoLãnh(Thànhphố)", "ThànhPhốBắcKạn" -> Remove these titles since there's a admin title column already
    # Remove the title in brackets
    gdf["NAME_"+level] = gdf["NAME_"+level].apply(lambda x: x.split("(")[0] if "(" in x else x)
    # Remove the title as an initial word
    gdf["NAME_"+level] = gdf["NAME_"+level].apply(lambda x: remove_title(x,title_dict))

    # STEP 2: Fix admin names
    if level=="2":
        gdf["NAME_"+level] = gdf["NAME_"+level].replace({"QuiNhơn":"QuyNhơn","TânThành":"PhúMỹ"})
    else:
        gdf["NAME_"+level] = gdf["NAME_"+level].replace({"ViệtKhái":"NguyễnViệtKhái","TrựcPhú":"NinhCường","ChươngDươngĐộ":"ChươngDương",
                                                         "PhiêngCôn":"PhiêngKôn","CưYang":"CưJang","Cầukho":"CầuKho","MườngChanh":"MươngChanh"})
        gdf.loc[gdf[gdf.GID_3=="VNM.39.1.15_1"].index, "NAME_"+level] = "ThanhPhú"

    # STEP 3: Correct titles
    gdf["TYPE_"+level] = gdf["TYPE_"+level].apply(correct_title)
    
    # To match with CityScope
    gdf["NAME_"+level+"_en"] = gdf["NAME_"+level].apply(convert_en)
    gdf["TYPE_"+level+"_en"] = gdf["TYPE_"+level].apply(convert_en)
        
    return gdf[gdf.columns[[0,1,2,3,5,6,4]]]

def read_csp(filepath, cols):
    gdf = gpd.read_file(filepath)
    gdf = gpd.GeoDataFrame(gdf, crs=32648)
    gdf = gdf.to_crs(4326)
    gdf = gdf[gdf.columns[cols]]
    # To match with GADM
    gdf["Dist_Name"] = gdf["Dist_Name"].apply(lambda x: x.replace("District","Quan").lower().replace(" ",""))
    gdf["Dist_Name"] = gdf["Dist_Name"].apply(lambda x: remove_title(x,title_en_list))
    if "Com_Name" in gdf.columns:
        gdf["Com_Name"] = gdf["Com_Name"].apply(lambda x: x.replace("Ward","Phuong").lower().replace(" ",""))
        gdf["Com_Name"] = gdf["Com_Name"].apply(lambda x: remove_title(x,title_en_list))
    return gdf

def join_gadm_cityscope(level, gdf_gadm):
    cols=[0,1,25]
    newcols = ["dist_en","cityscope_id","geometry"]
    if level=="Ward":
        cols=[0,1,2,11]
        newcols.insert(0,"ward_en")
    
    gdf_cityscope = read_csp(filepath=r"data\CityScope_HCMC\Population_"+level+"_Level.shp", cols=cols)
    gdf_cityscope.columns = newcols

    ## Merge 2 boundaries
    gdf_gadm_hcmc = gdf_gadm[gdf_gadm.city=="HồChíMinh"].drop(["geometry"], axis=1)
    gdf_hcmc = pd.merge(gdf_gadm_hcmc, gdf_cityscope, how="inner")
    gdf_hcmc = gpd.GeoDataFrame(gdf_hcmc.drop(["cityscope_id"], axis=1))
    
    # Append modified HCMC boundaries to GADM
    boundaries = pd.concat([gdf_gadm[gdf_gadm.city!="HồChíMinh"], gdf_hcmc])
    boundaries = gpd.GeoDataFrame(boundaries)

    # Export GeoJSON file
    boundaries.to_file(r"VN_Boundaries_"+level+".json", driver='GeoJSON', encoding='utf-8')
    return boundaries

# Source: https://gadm.org/download_country.html (level 2 = district, level 3 = Ward)
# Note: GADM administrative names don't have spaces
gadm_dist = read_gadm(level="2", cols=[4,0,6,9,13])
gadm_dist["NAME_1_en"] = gadm_dist["NAME_1"].apply(convert_en)
gadm_dist.insert(1, "NAME_1_en", gadm_dist.pop("NAME_1_en"))

gadm_ward = read_gadm(level="3", cols=[6,0,9,12,16])
gadm_ward = pd.merge(gadm_dist[gadm_dist.columns[range(7)]], gadm_ward, how="inner")

gadm_dist.columns = ["city","city_en","dist_id","district","dist_title","dist_en","dist_title_en","geometry"]
gadm_ward.columns = ["city","city_en","dist_id","district","dist_title","dist_en","dist_title_en","ward_id","ward","ward_title","ward_en","ward_title_en","geometry"]

# Source: https://github.com/CityScope/CSL_HCMC/tree/main/Data/GIS/Population/population_HCMC/population_shapefile
dist_boundaries = join_gadm_cityscope("District", gadm_dist)
ward_boundaries = join_gadm_cityscope("Ward", gadm_ward)
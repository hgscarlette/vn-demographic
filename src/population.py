import pandas as pd
from src.boundaries import title_dict, remove_title, correct_title, convert_en
import geopandas as gpd
import duckdb

"""
Source of population data: http://portal.thongke.gov.vn/khodulieudanso2019/Default.aspx
Note: the administrative may not be updated as in 2019, for example, Thị xã Đồng Xoài was already
upgraded to a city in 10/2018 but the population data still keeps it as Thị xã Đồng Xoài
"""

query_init = f"""
INSTALL spatial; 
LOAD spatial;
"""
duckdb.default_connection.sql(query_init)

def read_excel_pivot(path, row_to_skip, row_header, cols_remove_agg, row_agg):
    df = pd.read_excel(path, skiprows=row_to_skip, header=row_header)
    # Fill up empty Group by level rows
    cols=df.columns[[0,1]]
    df.loc[:,cols] = df.loc[:,cols].ffill()
    # Remove all aggregated rows
    for col in df.columns[cols_remove_agg]:
        df = df[~df[col].str.contains(row_agg, na=False)]
    df.reset_index(drop=True, inplace=True)
    return df

def process_admin(df):
    # Correct ward names
    df["city"] = df["city"].apply(lambda x: x.replace("Thanh Hoá","Thanh Hóa").replace("Khánh Hoà","Khánh Hòa"))

    # Add administrative IDs to process data
    df["dist_id_pop"] = df.groupby(["city","district"]).ngroup()
    admin_cols = ["city","district"]
    if "ward" in df.columns:
        # Correct ward names
        df["ward"] = df["ward"].apply(lambda x: x.replace("Qui Hướng","Quy Hướng").replace("Mương Tranh","Mương Chanh")
                                    .replace("Xốp Cộp","Sốp Cộp").replace("La Tơi","Ia Tơi").replace("La Dom","Ia Dom")
                                    .replace("La Dal","Ia Dal").replace("La Rong","Ia Rong").replace("La Pal","Ia Pal")
                                    .replace("Nà Ơt","Nà Ớt").replace("Hòa Tú II","Hòa Tú 2")
                                    .replace("trấn Phước Cát","trấn Phước Cát 1").replace("Phường Phường Đúc","Phường Đúc")
                                   )
        df["ward_id_pop"] = df.groupby(["city","district","ward"]).ngroup()
        admin_cols.insert(2,"ward")
    
    # To match with Boundaries
    for col in admin_cols:
        # Remove space and generate title columns
        df[col] = df[col].apply(lambda x: x.replace(" ",""))
        df[col[:4]+"_title"] = df[col]
        # Remove the title as an initial word
        df[col] = df[col].apply(lambda x: remove_title(x,title_dict))
        df[col] = df[col].apply(lambda x: str(int(x)) if x.isnumeric() else x)
        # Correct titles
        df[col[:4]+"_title"] = df[col[:4]+"_title"].apply(correct_title)
        # Add en versions
        df[col[:4]+"_title_en"] = df[col[:4]+"_title"].apply(convert_en)
        df[col[:4]+"_en"] = df[col].apply(convert_en)
        
    return df

def parse_population(population_size):
    # Population by Ward and Urban/Rural
    df_allpop = read_excel_pivot(path=r"data\Population data\Population by Urban (Ward).xlsx",
                                 row_to_skip=2, row_header=0,
                                 cols_remove_agg=[0,1], row_agg="Tổng số"
                                 )
    
    df_allpop.columns = ["city","district","ward","total","urban","rural"]
    allpop_ward = process_admin(df_allpop)
    
    # Population by Age and Urban/Rural
    df_popage = read_excel_pivot(path=r"data\Population data\Population by Age & Urban (District).xlsx",
                                 row_to_skip=2, row_header=[0,1],
                                 cols_remove_agg=[0], row_agg="Tổng số"
                                 )
    
    df_popage["urban_15_34"] = df_popage['1. Thành thị'][df_popage['1. Thành thị'].columns[3:7]].sum(axis=1)
    df_popage["rural_15_34"] = df_popage['2. Nông thôn'][df_popage['2. Nông thôn'].columns[3:7]].sum(axis=1)
    df_popage["total_15_34"] = df_popage["urban_15_34"] + df_popage["rural_15_34"]

    youngpop_dist = df_popage[df_popage.columns[[0,1,41,42,43]]]
    youngpop_dist.columns = ["city","district","urban_15_34","rural_15_34","total_15_34"]
    youngpop_dist = process_admin(youngpop_dist)
    
    # Household number by Size and Urban/Rural
    df_household = read_excel_pivot(path=r"data\Population data\Population by Household Size (Ward).xlsx",
                                    row_to_skip=2, row_header=[0,1],
                                    cols_remove_agg=[0,1], row_agg="Tổng số"
                                    )

    df_household["urban_5+"] = df_household['1. Thành thị'][df_household['1. Thành thị'].columns[4:]].sum(axis=1)
    df_household["rural_1_2"] = df_household['2. Nông thôn'][df_household['2. Nông thôn'].columns[0:2]].sum(axis=1)
    df_household["rural_5+"] = df_household['2. Nông thôn'][df_household['2. Nông thôn'].columns[4:]].sum(axis=1)

    household_ward = df_household[df_household.columns[[0,1,2,5,6,7,8,20,21,15,16,22]]]
    household_ward.columns = ["city","district","ward","urban_1","urban_2","urban_3","urban_4","urban_5","rural_1_2","rural_3","rural_4","rural_5"]
    household_ward = process_admin(household_ward)
    
    return allpop_ward if population_size=="all" else (youngpop_dist if population_size=="young" else household_ward)

def measure_area(gdf):
    # Convert CRS to equal-area projection -> the length unit is now `meter`
    gdf = gdf.to_crs(epsg=6933)
    gdf["area_sqm"] = gdf.area.values #/10e6 for sqKm
    gdf.insert(len(gdf.columns)-2, "area_sqm", gdf.pop("area_sqm"))
    gdf = gdf.to_crs(epsg=4326)
    return gdf

def get_GADM_ID(df_population, level):
    # Measure boundary's area for population density later
    gdf = gpd.read_file("VN_Boundaries_"+level+".json")
    gdf = measure_area(gdf)
    boundary = gdf.drop(["geometry"], axis=1)

    # Assign GADM's IDs to each Population's administrative
    level_query = level.lower()[:4]

    x = 2 if level == "District" else 3
    # Administrative columns to query
    admin_cols = list(df_population.columns[:x])
    admin_with_title = [col[:4] + "_title" for col in admin_cols]
    admin_cols.extend(admin_with_title)
    admin_main_cols = ', pop.'.join(admin_cols)
    # Mectric columns to query
    metric_cols = df_population.columns[x:1-x*4]
    metric_cols_query = ', pop.'.join(metric_cols)

    query = f"""
    SELECT DISTINCT
        IFNULL(IFNULL(IFNULL(gadm_full.{level_query}_id, gadm_full_en.{level_query}_id), gadm.{level_query}_id), gadm_en.{level_query}_id) AS {level_query}_id,
        pop.{admin_main_cols},
        IFNULL(IFNULL(IFNULL(gadm_full.area_sqm, gadm_full_en.area_sqm), gadm.area_sqm), gadm_en.area_sqm) AS area_sqm,
        pop.{metric_cols_query}
    FROM df_population pop
    LEFT JOIN boundary gadm_full
    ON pop.city = gadm_full.city AND pop.district = gadm_full.district AND pop.{level.lower()} = gadm_full.{level.lower()} AND pop.dist_title = gadm_full.dist_title AND pop.{level_query}_title = gadm_full.{level_query}_title
    LEFT JOIN boundary gadm_full_en
    ON pop.city_en = gadm_full_en.city_en AND pop.dist_en = gadm_full_en.dist_en AND pop.{level_query}_en = gadm_full_en.{level_query}_en AND pop.dist_title_en = gadm_full_en.dist_title_en AND pop.{level_query}_title_en = gadm_full_en.{level_query}_title_en
    LEFT JOIN boundary gadm
    ON pop.city = gadm.city AND pop.district = gadm.district AND pop.{level.lower()} = gadm.{level.lower()}
    LEFT JOIN boundary gadm_en
    ON pop.city_en = gadm_en.city_en AND pop.dist_en = gadm_en.dist_en AND pop.{level_query}_en = gadm_en.{level_query}_en
    """

    df_population_with_id = duckdb.default_connection.sql(query).df()
    return df_population_with_id


population_ward = parse_population("all")
population_ward_withID = get_GADM_ID(population_ward, level="Ward")
population_ward_withID["pop_density"] = round(population_ward_withID["total"] / population_ward_withID["area_sqm"] * 1e6)
population_ward_withID.to_csv("VN_Population_ward.csv", index=False)

youngpop_dist = parse_population("young")
youngpop_dist_withID = get_GADM_ID(youngpop_dist, level="District")
youngpop_dist_withID["dense_15_34"] = round(youngpop_dist_withID["total_15_34"] / youngpop_dist_withID["area_sqm"] * 1e6)
youngpop_dist_withID.to_csv("VN_YoungPop_dist.csv", index=False)

household_ward = parse_population("household")
household_ward_withID = get_GADM_ID(household_ward, level="Ward")
household_ward_withID.to_csv("VN_HouseholdPop_ward.csv", index=False)
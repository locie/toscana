from toscana import *
from pathlib import Path
from toscana.data_pre_processing import reproject_shapefiles_2154_to_IGNF, obtain_municipality_buildings, check_validity
import os, sys
import pandas as pd

# os.environ["PATH"] += r";C:\Users\riedelb\AppData\Local\anaconda3\envs\toscana_env\Library\bin"
### DEFINE A WORKING DIRECTORY ! 
working_directory = Path("/home/ferryap/Documents/Apolline/Projet_AVENIR")
if not working_directory: 
    raise NameError("A working directory must be entered before starting the test!")

working_directory.mkdir(exist_ok=True)

path_municipality_footprint = Path("/home/ferryap/Documents/Apolline/Projet_AVENIR/zones_valides.shp")

fn_results_folder =f"AVENIR_zones_valides/"
path_results_folder = working_directory / fn_results_folder
path_results_folder.mkdir(exist_ok=True)

download_BDTOPO = False
download_DEM = True
download = download_BDTOPO | download_DEM

def create_folder_tree(path_results_folder, download) :
    path_temp_folder = path_results_folder / "temp_folder"
    path_temp_folder.mkdir(exist_ok=True)
    path_shapefiles = path_temp_folder / "shapefiles"
    path_shapefiles.mkdir(exist_ok=True)
    path_raster_files = path_temp_folder / "raster_files"
    path_raster_files.mkdir(exist_ok=True)
    path_final_output_folder = path_results_folder / "final_output_files"
    path_final_output_folder.mkdir(exist_ok=True)

    path_meteorological_folder = path_temp_folder / "meteorological_files"
    path_meteorological_folder.mkdir(exist_ok=True)

    path_clip_files = path_temp_folder / "clip_files"
    path_clip_files.mkdir(exist_ok=True)  

    path_csv_files = path_temp_folder / "csv_files"
    path_csv_files.mkdir(exist_ok=True)  

    if download : 
        path_raw_data_folder = path_results_folder/"raw_data_folder"
        path_raw_data_folder.mkdir(exist_ok = True)
        return path_temp_folder, path_shapefiles, path_raster_files, path_final_output_folder, path_meteorological_folder, path_clip_files, path_csv_files, path_raw_data_folder
    else : 
        return path_temp_folder, path_shapefiles, path_raster_files, path_final_output_folder, path_meteorological_folder, path_clip_files, path_csv_files



### create some folder to store the results and organize them in different subfolder: see the folder tree below 
if download : 
    path_temp_folder, path_shapefiles, path_raster_files, path_final_output_folder, path_meteorological_folder, path_clip_files, path_csv_files, path_raw_data_folder=create_folder_tree(path_results_folder, download)
else : 
    path_temp_folder, path_shapefiles, path_raster_files, path_final_output_folder, path_meteorological_folder, path_clip_files, path_csv_files =create_folder_tree(path_results_folder, download)

import geopandas as gpd 


### download the BDTOPO database for the selected departement (15-12-2023 version)
if download_BDTOPO : 
    path_municipalities_dep, path_buildings_dep = download_and_extract_BDTOPO_data(73, path_raw_data_folder)



# path_municipality_footprint = path_shapefiles / "municipality_footprint.shp"

path_reproject_municipality_footprint = path_shapefiles / "municipality_footprint_reproject.shp"
reproject_shapefiles_2154_to_IGNF(path_municipality_footprint, path_reproject_municipality_footprint)
path_municipality_buildings = path_shapefiles / "municipality_buildings.shp"
#obtain_municipality_buildings(path_buildings_dep, path_municipality_footprint, path_municipality_buildings)
path_municipality_buildings_reproject = path_shapefiles / "municipality_buildings_reproject.shp"
reproject_shapefiles_2154_to_IGNF(path_municipality_buildings,path_municipality_buildings_reproject)
path_municipality_buildings_reproject_valid = path_shapefiles / "municipality_buildings_reproject_valid.shp"
check_validity(path_municipality_buildings_reproject, path_municipality_buildings_reproject_valid)

# ### create the grid used for the analysis
grid_gpd = obtain_grid(path_shapefiles) 
path_grid = path_shapefiles / "municipality_grid.shp"

# grid_gpd = gpd.read_file(str(path_grid))

### download the DEM file from OpenDEM website
if download_DEM : 
     path_DEM = download_extract_and_merge_DEM_from_OpenDEM(path_raw_data_folder, path_shapefiles)

### pre process raster file : creation of DHM, DSM 
preprocess_raster_file(path_raster_files, path_shapefiles, path_DEM, height_column="HAUTEUR",pixel_resolution=10) 

# ### download the meteorological files
# save_temp_meteorological_file = False  
# average_meteorological_file = True
# bool_global = True
# obtain_meteorological_files(path_meteorological_folder, path_shapefiles, save_temp_file= save_temp_meteorological_file, average=average_meteorological_file)

# path_gdf_centroid =  path_meteorological_folder / "centroid_grid.shp"
# day_nbr = 20
# month_number = 4
# list_days = list(transform_days_into_period(day_nbr, month_number, day_nbr, month_number))
# name_folder_period = f"{day_nbr}_{month_number}"

#  ## download weather forecast
# import datetime as dt 
# from meteole import AromeForecast

# # Configure the logger to provide information on data recovery: recovery status, default settings, etc.
# import logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger("meteole")

# # Initialize the AROME forecast client
# # Find your APPLICATION_ID by following these guidelines: https://maif.github.io/meteole/how_to/?h=application_id#get-a-token-an-api-key-or-an-application-id
# APPLICATION_ID = UUNZRW5HZUhfbDZLTW1xOG9LaGJyem9DVXRzYToydG5rWTdJN3NkT195d21sYjlwZnVMMjJLZzRh
# arome_client = AromeForecast(application_id = APPLICATION_ID)

# # Check indicators available
# print(arome_client.INDICATORS)

# # Fetch weather data
# df_arome = arome_client.get_coverage(
#     indicator="V_COMPONENT_OF_WIND_GUST__SPECIFIC_HEIGHT_LEVEL_ABOVE_GROUND",  # Optional: if not, you have to fill coverage_id
#     run="2025-01-10T00.00.00Z",                                                # Optional: forecast start time
#     forecast_horizons=[                                                       # Optional: prediction times (in hours)
#       dt.timedelta(hours=1),
#       dt.timedelta(hours=2),
#     ],  
#     heights=[10],                                                              # Optional: height above ground level
#     pressures=None,                                                            # Optional: pressure level
#     long = (-5.1413, 9.5602),                                                  # Optional: longitude
#     lat = (41.33356, 51.0889),                                                 # Optional: latitude
#     coverage_id=None,                                                          # Optional: an alternative to indicator/run/interval
#     temp_dir=None,                                                             # Optional: Directory to store the temporary file
# )

from meteofetch import Arome001
import xarray as xr

# Récupération du dernier run AROME avec la variable 'ssrd'
ds = Arome001.get_latest_forecast(paquet='SP1', variables=('ssrd',))

# Aperçu des données disponibles
print(ds)

lat_min, lat_max = 45.5, 46.0
lon_min, lon_max = 4.5, 5.2

# Extraction de la sous-zone
sub_ds = ds.sel(latitude=slice(lat_max, lat_min), longitude=slice(lon_min, lon_max))  # latitudes inversées

# Transformation en DataFrame pour traitement
df = point.to_dataframe().reset_index()

# Conversion J/m² en W/m² (irradiance moyenne horaire)
df['ssrd_Wm2'] = df['ssrd'] / 3600  # 1h = 3600 s

print(df[['time', 'ssrd_Wm2']].head())

## create hourly weather folders
path_hourly_weather_folder = path_meteorological_folder / "hourly_files"
path_hourly_weather_folder.mkdir(exist_ok=True)
path_meteorological_folder_period = create_period_weather_file(name_folder_period,path_meteorological_folder,path_gdf_centroid, list_days, average=average_meteorological_file)

path_hourly_weather_folder_period = path_hourly_weather_folder/name_folder_period
path_hourly_weather_folder_period.mkdir(exist_ok=True)


# if average : 
#             path_folder_month_average = path_folder_month / "average_files"
#             path_folder_month_average.mkdir(exist_ok=True)        

#             path_average_folder = path_meteorological_folder / "average_files"
# else : 
#             path_folder_month_txt = path_folder_month / "txt_files"
#             path_folder_month_txt.mkdir(exist_ok=True)
  
#             path_txt_folder = path_meteorological_folder / "txt_files"



if average_meteorological_file :
    path_meteorological_folder_period_average = path_meteorological_folder_period/"average_files"
   
    # path_hourly_weather_folder_period_average = path_hourly_weather_folder_period/"average_files"
    # path_hourly_weather_folder_period_average.mkdir(exist_ok=True)

    path_final_output_folder_period = path_final_output_folder/name_folder_period
    path_final_output_folder_period.mkdir(exist_ok=True)



for file in os.listdir(path_meteorological_folder_period_average):  # discrétisation spatiale
    df1 = pd.read_csv(path_meteorological_folder_period_average/file, sep= ' ')
    for i in range(1,25,1) : # discrétisation temporelle heure par heure
        df = df1[df1['it'] == i]
        name_folder_hours = f"heure_{i}"
        # path_final_output_folder_hours = path_final_output_folder/name_folder_period/name_folder_hours
        # path_final_output_folder_hours.mkdir(exist_ok=True)
        # path_final_output_folder = path_final_output_folder/name_folder_period
        # path_final_output_folder.mkdir(exist_ok=True)
        path_hourly_weather_folder_period_hours = path_hourly_weather_folder_period/name_folder_hours
        path_hourly_weather_folder_period_hours.mkdir(exist_ok=True)
        if average_meteorological_file :
            path_hourly_weather_folder_period_hours_average = path_hourly_weather_folder_period_hours/"average_files"
            path_hourly_weather_folder_period_hours_average.mkdir(exist_ok=True)
            df.to_csv(path_hourly_weather_folder_period_hours_average/ file, index=False, sep=' ')


# heure par heure sur une journée 
for i in range(1,25,1) : 
    name_folder_hours = f"heure_{i}"
    path_final_output_folder_period_hours = path_final_output_folder_period/name_folder_hours
    path_final_output_folder_period_hours.mkdir(exist_ok=True)
    path_hourly_weather_folder_period_hours = path_hourly_weather_folder_period/name_folder_hours
    ## run the solar simulation for each grid tiles for the period
    iterate_on_grid(grid_gpd, path_final_output_folder_period_hours, path_clip_files, path_raster_files, path_meteorological_folder , path_csv_files, path_meteorological_subfolder=path_hourly_weather_folder_period_hours,average = average_meteorological_file, restart_tile=1, bool_global=bool_global, albedo=0.8)
    post_process(path_final_output_folder_period_hours, grid_gpd, path_shapefiles, path_csv_files, column_prefix="sol_", average=average_meteorological_file, bool_global= bool_global, distance= -1.5)
    # display_results(path_raster_files, path_final_output_folder_period, column_prefix="sol_", name_plot="Distribution_irradiation.pdf")




# for i in range(1,32,1) : 
#     list_days = list(transform_days_into_period(i, 1, i+1, 1))
#     name_folder_period = f"{i}_1"
#     path_meteorological_folder_period = create_period_weather_file(name_folder_period,path_meteorological_folder, path_gdf_centroid, list_days, average=average_meteorological_file)
#     path_final_output_folder_period = path_final_output_folder/f"{i}_1"
#     path_final_output_folder_period.mkdir(exist_ok=True)
#     ## run the solar simulation for each grid tiles for the period
#     iterate_on_grid(grid_gpd, path_final_output_folder_period, path_clip_files, path_raster_files, path_meteorological_folder , path_csv_files, path_meteorological_subfolder=path_meteorological_folder_period,average = average_meteorological_file, restart_tile=1, bool_global=bool_global, albedo = 0.8)
#     post_process(path_final_output_folder_period, grid_gpd, path_shapefiles, path_csv_files, column_prefix="sol_", average=average_meteorological_file, bool_global= bool_global, distance= -1.5)
#     # display_results(path_raster_files, path_final_output_folder_period, column_prefix="sol_", name_plot="Distribution_irradiation.pdf")


# for i in range(1,29,1) : 
#     list_days = list(transform_days_into_period(i, 2, i+1, 2))
#     name_folder_period = f"{i}_2"
#     path_meteorological_folder_period = create_period_weather_file(name_folder_period,path_meteorological_folder, path_gdf_centroid, list_days, average=average_meteorological_file)
#     path_final_output_folder_period = path_final_output_folder/f"{i}_2"
#     path_final_output_folder_period.mkdir(exist_ok=True)
#     ## run the solar simulation for each grid tiles for the period
#     iterate_on_grid(grid_gpd, path_final_output_folder_period, path_clip_files, path_raster_files, path_meteorological_folder , path_csv_files, path_meteorological_subfolder=path_meteorological_folder_period,average = average_meteorological_file, restart_tile=1, bool_global=bool_global, albedo=0.8)
#     post_process(path_final_output_folder_period, grid_gpd, path_shapefiles, path_csv_files, column_prefix="sol_", average=average_meteorological_file, bool_global= bool_global, distance= -1.5)
#     # display_results(path_raster_files, path_final_output_folder_period, column_prefix="sol_", name_plot="Distribution_irradiation.pdf")

# for i in range(1,32,1) : 
#     list_days = list(transform_days_into_period(i, 3, i+1, 3))
#     name_folder_period = f"{i}_3"
#     path_meteorological_folder_period = create_period_weather_file(name_folder_period,path_meteorological_folder, path_gdf_centroid, list_days, average=average_meteorological_file)
#     path_final_output_folder_period = path_final_output_folder/f"{i}_3"
#     path_final_output_folder_period.mkdir(exist_ok=True)
#     ## run the solar simulation for each grid tiles for the period
#     iterate_on_grid(grid_gpd, path_final_output_folder_period, path_clip_files, path_raster_files, path_meteorological_folder , path_csv_files, path_meteorological_subfolder=path_meteorological_folder_period,average = average_meteorological_file, restart_tile=1, bool_global=bool_global, albedo=0.8)
#     post_process(path_final_output_folder_period, grid_gpd, path_shapefiles, path_csv_files, column_prefix="sol_", average=average_meteorological_file, bool_global= bool_global, distance= -1.5)
#     # display_results(path_raster_files, path_final_output_folder_period, column_prefix="sol_", name_plot="Distribution_irradiation.pdf")



# for i in range(1,31,1) : 
#     list_days = list(transform_days_into_period(i, 4, i+1, 4))
#     name_folder_period = f"{i}_4"
#     path_meteorological_folder_period = create_period_weather_file(name_folder_period,path_meteorological_folder, path_gdf_centroid, list_days, average=average_meteorological_file)
#     path_final_output_folder_period = path_final_output_folder/f"{i}_4"
#     path_final_output_folder_period.mkdir(exist_ok=True)
#     ## run the solar simulation for each grid tiles for the period
#     iterate_on_grid(grid_gpd, path_final_output_folder_period, path_clip_files, path_raster_files, path_meteorological_folder , path_csv_files, path_meteorological_subfolder=path_meteorological_folder_period,average = average_meteorological_file, restart_tile=1, bool_global=bool_global, albedo=0.8)
#     post_process(path_final_output_folder_period, grid_gpd, path_shapefiles, path_csv_files, column_prefix="sol_", average=average_meteorological_file, bool_global= bool_global, distance= -1.5)
#     # display_results(path_raster_files, path_final_output_folder_period, column_prefix="sol_", name_plot="Distribution_irradiation.pdf")


# for i in range(1,32,1) : 
#     list_days = list(transform_days_into_period(i, 5, i+1, 5))
#     name_folder_period = f"{i}_5"
#     path_meteorological_folder_period = create_period_weather_file(name_folder_period,path_meteorological_folder, path_gdf_centroid, list_days, average=average_meteorological_file)
#     path_final_output_folder_period = path_final_output_folder/f"{i}_5"
#     path_final_output_folder_period.mkdir(exist_ok=True)
#     ## run the solar simulation for each grid tiles for the period
#     iterate_on_grid(grid_gpd, path_final_output_folder_period, path_clip_files, path_raster_files, path_meteorological_folder , path_csv_files, path_meteorological_subfolder=path_meteorological_folder_period,average = average_meteorological_file, restart_tile=1, bool_global=bool_global, albedo=0.8)
#     post_process(path_final_output_folder_period, grid_gpd, path_shapefiles, path_csv_files, column_prefix="sol_", average=average_meteorological_file, bool_global= bool_global, distance= -1.5)
#     # display_results(path_raster_files, path_final_output_folder_period, column_prefix="sol_", name_plot="Distribution_irradiation.pdf")

# for i in range(1,31,1) : 
#     list_days = list(transform_days_into_period(i, 11, i+1, 11))
#     name_folder_period = f"{i}_11"
#     path_meteorological_folder_period = create_period_weather_file(name_folder_period,path_meteorological_folder, path_gdf_centroid, list_days, average=average_meteorological_file)
#     path_final_output_folder_period = path_final_output_folder/f"{i}_11"
#     path_final_output_folder_period.mkdir(exist_ok=True)
#     ## run the solar simulation for each grid tiles for the period
#     iterate_on_grid(grid_gpd, path_final_output_folder_period, path_clip_files, path_raster_files, path_meteorological_folder , path_csv_files, path_meteorological_subfolder=path_meteorological_folder_period,average = average_meteorological_file, restart_tile=1, bool_global=bool_global, albedo=0.8)
#     post_process(path_final_output_folder_period, grid_gpd, path_shapefiles, path_csv_files, column_prefix="sol_", average=average_meteorological_file, bool_global= bool_global, distance= -1.5)
#     # display_results(path_raster_files, path_final_output_folder_period, column_prefix="sol_", name_plot="Distribution_irradiation.pdf")

# for i in range(1,32,1) : 
#     list_days = list(transform_days_into_period(i, 12, i+1, 12))
#     name_folder_period = f"{i}_12"
#     path_meteorological_folder_period = create_period_weather_file(name_folder_period,path_meteorological_folder, path_gdf_centroid, list_days, average=average_meteorological_file)
#     path_final_output_folder_period = path_final_output_folder/f"{i}_12"
#     path_final_output_folder_period.mkdir(exist_ok=True)
#     ## run the solar simulation for each grid tiles for the period
#     iterate_on_grid(grid_gpd, path_final_output_folder_period, path_clip_files, path_raster_files, path_meteorological_folder , path_csv_files, path_meteorological_subfolder=path_meteorological_folder_period,average = average_meteorological_file, restart_tile=1, bool_global=bool_global, albedo=0.8)
#     post_process(path_final_output_folder_period, grid_gpd, path_shapefiles, path_csv_files, column_prefix="sol_", average=average_meteorological_file, bool_global= bool_global, distance= -1.5)
#     # display_results(path_raster_files, path_final_output_folder_period, column_prefix="sol_", name_plot="Distribution_irradiation.pdf")


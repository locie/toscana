from toscana import *
from pathlib import Path

### INPUT ### 
""" SELECTION OF THE VILLAGE """
village_name = "La Croix-de-la-Rochette" 
village_INSEE_code ="73095"
village_departement = "73" 

""""""""""""""""""""""""""""""""""""""""""""""""
""" DEFINE THE FOLDER CONTAINING THE INPUT """
# input_folder = Path("input_folder/") ##### create a folder and place all the input inside 
# path_DEM = input_folder / "DEM.tif" #### name of your DEM that should cover an area larger than the investigated village / supposed to have a IGNF ETRS89 LAEA projection 
### use IGN data, folder download directly from IGN for the departement of your village
# path_IGN_folder = input_folder / "BDTOPO/BDTOPO_3-0_TOUSTHEMES_SHP_LAMB93_D074_2022-09-15/BDTOPO_3-0_TOUSTHEMES_SHP_LAMB93_D074_2022-09-15/BDTOPO/1_DONNEES_LIVRAISON_2022-09-00418/BDT_3-0_SHP_LAMB93_D074-ED2022-09-15"
# path_municipalities_dep = path_IGN_folder/("ADMINISTRATIF/COMMUNE.shp")
# path_buildings_dep = path_IGN_folder/("BATI/BATIMENT.shp")
# """"""""""""""""""""""""""""""""""""""""""""""""

""" DEFINE THE LOCATION OF THE FOLDER WITH THE RESULTS """
# parent_folder = "" # put the name of your parent folder, where you want to place your output
# fn_results_folder = parent_folder + f"Solar_cadastre_{village_name}/" ### name chosen for the folder with all the results 
""""""""""""""""""""""""""""""""""""""""""""""""

### DEFINE A WORKING DIRECTORY ! 
working_directory = ""
if not working_directory: 
    raise NameError("A working directory must be entered before starting the test!")

working_directory.mkdir(exist_ok=True)
(working_directory / 'DATA').mkdir(exist_ok=True)

### DEM DOWNLOAD FROM OPENDEM, ONLY THE TILE CORRESPONDING TO THE REGION OF INTEREST : TILES N245E400 --> https://www.opendem.info/opendemeu_download_highres.html
path_DEM = working_directory /"DATA/N245E400.tif" 
## SHAPEFILE FROM IGN, COMING FROM THE FOLDER OF THE BDTOPO DOWNLOAD FROM THE DEPARTEMENT OF INTEREST :D073, LAYER COMMUNE FOR THE MUNICIPALITIES AND LAYER BATIMENT FOR THE BUILDINGS --> https://geoservices.ign.fr/bdtopo#telechargementshpdep2023 
path_municipalities_dep = working_directory/ "DATA/COMMUNE.shp"
path_buildings_dep = working_directory / "DATA/BATIMENT.shp"


### CREATION OF A FOLDER TO CONTAIN ALL THE RESULTS 
fn_results_folder =f"Solar_cadastre_{village_name}/"
path_results_folder = working_directory / fn_results_folder
path_results_folder.mkdir(exist_ok=True)

download_BDTOPO = True #False
download_DEM = True # False
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

### download the BDTOPO database for the selected departement (15-12-2023 version)
if download_BDTOPO : 
    path_municipalities_dep, path_buildings_dep = download_and_extract_BDTOPO_data(village_departement, path_raw_data_folder)

### pre process shapefiles from IGN to keep only data for the municipality
preprocess_municipality_buildings(path_shapefiles, path_municipalities_dep, village_INSEE_code, path_buildings_dep)

### create the grid used for the analysis
grid_gpd = obtain_grid(path_shapefiles) 

### download the DEM file from OpenDEM website
if download_DEM : 
    path_DEM = download_extract_and_merge_DEM_from_OpenDEM(path_raw_data_folder, path_shapefiles)

### pre process raster file : creation of DHM, DSM 
preprocess_raster_file(path_raster_files, path_shapefiles, path_DEM, height_column="HAUTEUR") 

### download the meteorological files
save_temp_meteorological_file = False  
average_meteorological_file = True
bool_global = True
obtain_meteorological_files(path_meteorological_folder, path_shapefiles, save_temp_file= save_temp_meteorological_file, average=average_meteorological_file)

## run the solar simulation for each grid tiles
iterate_on_grid(grid_gpd, path_final_output_folder, path_clip_files, path_raster_files, path_meteorological_folder , path_csv_files, average = average_meteorological_file, restart_tile=1, bool_global=bool_global)

## post process the results to get the usefull information
post_process(path_final_output_folder, grid_gpd, path_shapefiles, path_csv_files, column_prefix="sol_", average=average_meteorological_file, bool_global= bool_global, distance= -1.5)

## make some vizualisation of the results
display_results(path_raster_files, path_final_output_folder, column_prefix="sol_")

### store the usefull information into a dataframe/csv file 
df_results = calculate_village_distribution_characteristics(path_csv_files, path_raster_files, path_final_output_folder, path_shapefiles,grid_gpd, path_meteorological_folder,village_name, village_INSEE_code, village_departement, average = average_meteorological_file)


"""
Structure of the output folder 
--> Solar_cadastre_nom_village
    --> raw_data_folder (optional)
        --> BDTOPO_D0{departement}_2023-12-15 (optional)
            --> BDTOPO_3-3_TOUSTHEMES_SHP_LAMB93_D0{departement}_2023-12-15
                --> BDTOPO
                    --> 1_DONNEES_LIVRAISON_2023-12-00099
                        --> BDT_3-3_SHP_LAMB93_D0{departement}-ED2023-12-15
                            --> ADMINISTRATIF
                                - COMMUNE
                            --> BATI
                                - BATIMENT
        --> N{a}E{b} (N245E400 for example) (optional)
            - N{a}E{b} (N245E400 for example)
        - grid_download_DEM_Open_DEM (optional)
        - raw_merge_DEM (optional)
    --> temp_folder
        --> csv_folder
            - centroid_municipality_coordinates
            - centroid_buildings_buffer_coordinates
            - list_incorrect_tiles
        --> clip_files 
            --> DSM_clip
                - DSM_clip_temp_
            --> DHM_clip
                - DHM_clip_temp_
            --> wallheight_clip
                - wallheight_clip_temp_
            --> wallaspect_clip
                - wallaspect_clip_temp_
            --> grid_clip
                -grid_temp_
        --> raster_files
            - DEM_clip_large
            - DEM_resample
            - DHM
            - DSM
            - DHM_temp_1
            - DHM_temp_2
            - DSM_temp
        --> shapefiles
            - municipality_footprint
            - municipality_footprint_reproject
            - municipality_buildings
            - municipality_buildings_reproject
            - municipality_buildings_reproject_valid
            - municipality_buildings_reproject_valid_sup_0
            - municipality_extent
            - municipality_grid
            - grid_extent
            - buffer_buildings
            - buffer_buildings_zonal_stats_solar
            - municipality_area_and_perimeter
            - municipality_zonal_stats_altitude
            - centroid_municipality
            - centroid_municipality_coordinates
            - centroid_buildings_buffer
            - centroid_buildings_buffer_coordinates
            - valid_departement_buildings (in some cases)
        --> meteorogical_files
            - centroid_grid
            - centroid_grid_modified (optional)
            - centroid_grid_modified_coordinates (optional)
            - centroid_grid_modified_csv (optional)
            - centroid_grid_csv (optional)
            - list_incorrect_tiles_meteorological
            --> epw_files (optional)
                - epw_files_center_grid_
            --> txt_files (optional)
                - txt_files_center_grid_
            --> average_files (optional)
                - txt_average_files_center_grid_

    --> final result   
        - merge_annual_solar_energy
        - merge_annual_solar_energy_clip_municipality_extent
        - buildings_zonal_stats_solar
        - irradiation_csv
        - Distribution_irradiation
        - municipality_and_solar_distribution_characteristics
        --> SEBE_simulation
            --> SEBE_
                - roof_irradiance_
                - sky_irradiance_
                - dsm
                - Energyyearroof
                - Energyyearwall
                - RunInfoSEBE
"""

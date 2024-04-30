import sys

from ..utils import processing

from tqdm import tqdm
from ..utils import clip_raster
from pathlib import Path
from pandas import DataFrame, read_csv

from qgis.core import QgsProcessingException

""" ITERATE ON GRID AND RUN SEBE SIMUALTION """

def _clip_grid(grid_gpd, j, path_clip_grid): 
    """Clip one tile of the grid based on the name of its id (j). 

    Parameters
    ----------
    grid_gpd : GeoDataFrame
        geopandas file with grid (obtained in define_grid)
    j : int
        name of the id of the tile to be clipped
    path_clip_grid : path-like
        path where to save the layer (grid tile shapefile)
    """
    grid_gpd_temp = grid_gpd[grid_gpd['id']==j]
    grid_gpd_temp.to_file(str(path_clip_grid))  

def calculate_wallheight_wallaspect(path_DHM_clip, path_wallheight_clip, path_wallaspect_clip, wall_limit=0.1): 
    """Calculate wallheight and wallaspect rasters from DHM (or with DSM, both are possible), defining a limit of height to consider wall (0.1m by default (for DHM) (around 3m for DSM)).

    Parameters
    ----------
    path_DHM_clip : path-like
        path of the clip raster (DHM or DSM) (path_clip_raster from `clip_raster`)
    path_wallheight_clip : path-like
        path where to save the layer (wallheight raster clip files)
    path_wallaspect_clip : path-like
        path where to save the layer (wallaspect raster clip files)
    wall_limit : float, optional
        minimum difference of height to consider a pixel as a wall, by default 0.1

    Raises
    ------
    AssertionError
        wall_limit must be greater than 0
    """
    if wall_limit<=0 : 
        raise AssertionError('Wall limit must be greater than 0 ! ')
    
    processing.run("umep:Urban Geometry: Wall Height and Aspect",\
    {'INPUT':str(path_DHM_clip),\
    'INPUT_LIMIT':wall_limit,\
    'OUTPUT_HEIGHT':str(path_wallheight_clip),'OUTPUT_ASPECT':str(path_wallaspect_clip)})

def run_SEBE_simulation(path_DSM_clip, path_wallheight_clip, path_wallaspect_clip, path_average_meteorological_file, path_output_SEBE_temp_folder, path_sky_irradiance, path_roof_irradiance, bool_global= True, utc=1, bool_save_sky_irradiance = True, albedo = 0.15 ):
    """Launch the SEBE algorithm to calculate irradiation on surfaces, precising an average ``albedo`` value of surfaces (default : 0.15), the time zone (default :1), calculating direct and diffuse irradiance from global irradiance if necessary (default: True) and saving the sky irradiance distribution (distribution of irradiance components) (default : True). 
    
    Parameters
    ----------
    path_DSM_clip : path-like
        path of the DSM clip raster (path_output from `clip_raster`)
    path_wallheight_clip : path-like
        path of the clip wallheight (from `calculate_wallheight_wall_aspect`)
    path_wallaspect_clip : path-like
        path of the clip wallaspect (from `calculate_wallheight_wall_aspect`)
    path_average_meteorological_file : path-like
        path of the average txt meteorological file (obtained in `obtain_average_meteorological_files`)
    path_output_SEBE_temp_folder : path-like
        path of the folder to save output of the calculation 
    path_sky_irradiance : path-like
        path where to save the sky irradiance distribution
    path_roof_irradiance : path-like
        path where to save the roof irradiance raster
    bool_global : bool, optional
        boolean value to calculate or not the diffuse and direct irradiance value from global irradiance value, by default True
    utc : int, optional
        value of utc time, by default 1
        from -12 to 12, see umep:Solar Radiation: Solar Energy of Builing Envelopes (SEBE) documentation
    bool_save_sky_irradiance : bool, optional
        boolean to save or not the sky irradiance data, by default True
    albedo : float, optional
        value of the albedo, by default 0.15
        from 0 to 1, see umep:Solar Radiation: Solar Energy of Builing Envelopes (SEBE) documentation

    Raises
    ------
    AssertionError
        albedo must be between 0 and 1
    AssertionError
        utc must be between -12 and 12   
    """
    if albedo <0 or albedo >1 : 
        raise AssertionError('Albedo must be between 0 and 1!')
    if utc<-12 or utc > 12: 
        raise AssertionError('UTC must be between -12 and 12!')

    processing.run("umep:Solar Radiation: Solar Energy of Builing Envelopes (SEBE)",\
    {'INPUT_DSM':str(path_DSM_clip),\
    'INPUT_CDSM':None,\
    'TRANS_VEG':3,\
    'INPUT_TDSM':None,\
    'INPUT_THEIGHT':25,\
    'INPUT_HEIGHT':str(path_wallheight_clip),\
    'INPUT_ASPECT':str(path_wallaspect_clip),\
    'ALBEDO':albedo,\
    'INPUTMET':str(path_average_meteorological_file),\
    'ONLYGLOBAL':bool_global,\
    'UTC':utc,\
    'SAVESKYIRR':bool_save_sky_irradiance,\
    'IRR_FILE':str(path_sky_irradiance),\
    'OUTPUT_DIR':str(path_output_SEBE_temp_folder),\
    'OUTPUT_ROOF':str(path_roof_irradiance)})

def _create_clip_folder(path_clip_files): 
    """Create subfolders to store temporary clip files. 

    Parameters
    ----------
    path_clip_files : path-like
        path of the folder with temporary clip files (define in main function)

    Returns
    -------
    path_clip_DSM : path-like
        path of the folder created in order to store the clipped raster DSM
    path_clip_grid : path-like
        path of the folder created in order to store the clipped shapefile grid tile
    path_clip_DHM : path-like
        path of the folder created in order to store the clipped raster DHM 
    path_clip_wallheight : path-like    
        path of the folder created in order to store the clipped raster wallheight
    path_clip_wallaspect : path-like
        path of the folder created in order to store the clipped raster wallaspect 
    """
    path_clip_DSM = path_clip_files / "DSM_clip"
    path_clip_DSM.mkdir(exist_ok=True)

    path_clip_grid= path_clip_files / "grid_clip"
    path_clip_grid.mkdir(exist_ok=True)

    path_clip_DHM=path_clip_files/  "DHM_clip"
    path_clip_DHM.mkdir(exist_ok=True)

    path_clip_wallheight =path_clip_files/ "wallheight_clip"
    path_clip_wallheight.mkdir(exist_ok=True)

    path_clip_wallaspect= path_clip_files/  "wallaspect_clip"
    path_clip_wallaspect.mkdir(exist_ok=True)

    return path_clip_DSM, path_clip_grid, path_clip_DHM, path_clip_wallheight, path_clip_wallaspect


def _create_SEBE_folder(path_final_output_folder, j): 
    """Create SEBE folders, where will be stored the results. A main folder is created and one folder to store the simulation of each grid tile is created. 

    Parameters
    ----------
    path_final_output_folder : path-like
        path of the folder where to save the final results (define in main function)
    j : int
        name of the id of the tile to be simulated

    Returns
    -------
    path_SEBE_temp : path-like
        path of the subfolder with the SEBE simulation results of the simulated tile
    """
    fn_main_SEBE_folder = "SEBE_simulation/"
    fn_SEBE_temp ="SEBE_"

    path_main_SEBE_folder = path_final_output_folder / fn_main_SEBE_folder
    path_main_SEBE_folder.mkdir(exist_ok = True)

    path_SEBE_temp = path_main_SEBE_folder / (fn_SEBE_temp + str(j) +"/")
    path_SEBE_temp.mkdir(exist_ok = True)

    return path_SEBE_temp


def iterate_on_grid(grid_gpd, path_final_output_folder, path_clip_files, path_raster_files, path_meteorological_folder,path_csv_folder,  wall_limit=0.1, bool_global= True, utc=1, bool_save_sky_irradiance = True, albedo = 0.15, restart_tile = 1 , average = True):  
    """Function used to iterate on the grid (run simulation for each grid tile) : the DSM, DHM and grid are clipped at the extent of one tile, wall aspects and wall heights are calculated and then SEBE simulation are run.
    
    SEBE calculation are not done for the tiles for which the meteorological files could not have been downloaded. 
    The iteration starts with the first tile (by default) but can be changed by changing restart_tile. 
    Exceptions are included to consider if SEBE calculation could not be run : problem when calculating the sky irradiance distribution (if direct and diffuse component are derived from global, error could appear when reprojecting the component on each patch of the sky vault) or if some wrong values are present in meteorological data (averaged or not).
    The list of the tiles for which the SEBE calculation could not have been done (due to a missing meteorological files, to an error in the calculation of the diffuse and direct component from the global, or due to an other error) are saved in a csv files with the corresponding error. 

    Parameters
    ----------
    grid_gpd : GeoDataFrame
        geopandas grid file
    path_final_output_folder : path-like
        path of the folder where to save the final results (define in main function)
    path_clip_files : path-like
        path of the folder with temporary clip files (define in main function)
    path_raster_files : path-like
        path of the folder with temporary raster files (define in main function)
    path_meteorological_folder : path-like
        path of the folder where are saved all the meteorological files
    path_csv_folder : path-like
        path of the folder with temporary csv files (define in main function)
    wall_limit : float, optional
        minimum difference of height to consider a pixel as a wall, by default 0.1
    bool_global : bool, optional
        boolean value to calculate or not the diffuse and direct irradiance values from global irradiance values, by default True
    utc : int, optional
        value of utc time, by default 1
        from -12 to 12, see umep:Solar Radiation: Solar Energy of Builing Envelopes (SEBE) documentation
    bool_save_sky_irradiance : bool, optional
        boolean to save or not the sky irradiance data, by default True
    albedo : float, optional
        value of the albedo, by default 0.15
        from 0 to 1, see umep:Solar Radiation: Solar Energy of Builing Envelopes (SEBE) documentation
    restart_tile : int, optional
        number of the first tile on which to run SEBE simulation (to change to start not from the beginning), by default 1
    average : bool, optional
        boolean value to indicate if an average of the meteorological files was done or not, by default True

    Raises
    ------
    AssertionError
        restart_tile must be smaller than the number of grid tiles and higher than 1 (first tile)        
    """
    path_list_tiles = path_meteorological_folder / "list_incorrect_tiles_meteorological.csv"
    df_list_tiles = read_csv(str(path_list_tiles))
    list_incorrect_meteorological_tiles = df_list_tiles['tile_number'].tolist()
    list_error = []

    fc = len(grid_gpd)
    if restart_tile<1 or restart_tile >fc:
        raise AssertionError(f'Restart tile must be between 1 and {fc} (number of tiles in the grid)!')

    path_DSM = path_raster_files/ "DSM.tif"
    path_DHM = path_raster_files/ "DHM.tif"

    if average : 
        path_average_folder = path_meteorological_folder/"average_files"
        fn_average_files = "average_txt_files_center_grid_"
    else : 
        path_average_folder = path_meteorological_folder/"txt_files"
        fn_average_files = "txt_files_center_grid_"


    starting_tile = restart_tile-1
    list_incorrect_tiles = []
    for i in tqdm(range(starting_tile,fc)):
        j=i+1
        path_clip_DSM, path_clip_grid, path_clip_DHM, path_clip_wallheight, path_clip_wallaspect = _create_clip_folder(path_clip_files)
        path_clip_grid_temp = path_clip_grid / ("grid_temp"+str(j)+".shp")
        _clip_grid(grid_gpd, j, path_clip_grid_temp)
        path_DSM_clip_temp = path_clip_DSM / ("DSM_clip_temp"+str(j)+".tif")
        clip_raster(path_clip_grid_temp, path_DSM, path_DSM_clip_temp)
        path_DHM_clip_temp = path_clip_DHM / ("DHM_clip_temp"+str(j)+".tif")
        clip_raster(path_clip_grid_temp, path_DHM, path_DHM_clip_temp)
        path_wallheight_clip_temp = path_clip_wallheight / ("wallheight_clip_temp"+str(j)+".tif")
        path_wallaspect_clip_temp = path_clip_wallaspect / ("wallaspect_clip_temp"+str(j)+".tif")
        calculate_wallheight_wallaspect(path_DHM_clip_temp, path_wallheight_clip_temp, path_wallaspect_clip_temp,wall_limit=wall_limit)
        path_average_meteorological_file = path_average_folder / (fn_average_files + str(j) + ".txt")
        path_SEBE_temp_folder = _create_SEBE_folder(path_final_output_folder, j)
        path_sky_irradiance = path_SEBE_temp_folder / ("sky_irradiance_"+str(j)+".txt")
        path_roof_irradiance = path_SEBE_temp_folder / ("roof_irradiance_" +str(j)+ ".tif")
        if j not in list_incorrect_meteorological_tiles : 
            try : 
                run_SEBE_simulation(path_DSM_clip_temp, path_wallheight_clip_temp, path_wallaspect_clip_temp, path_average_meteorological_file, path_SEBE_temp_folder, path_sky_irradiance, path_roof_irradiance, bool_global= bool_global, utc=utc, bool_save_sky_irradiance = bool_save_sky_irradiance, albedo = albedo)
            except QgsProcessingException as e: 
                print(f"Problem with grid tile n°{j} : it is not possible to calculate diffuse and direct irradiance component from direct. Moving to next tile.")
                print(e)
                list_incorrect_tiles.append(j)
                list_error.append(e)
        else : 
           list_incorrect_tiles.append(j) 
           list_error.append("No valid meteorological files")
           print("No valid meteorological files")

        df_list_tiles = DataFrame({'tile_number': list_incorrect_tiles, 'error': list_error})
        path_list_tiles = path_csv_folder / "list_incorrect_tiles.csv"
        df_list_tiles.to_csv(str(path_list_tiles), index=False)


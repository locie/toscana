from ..utils import processing
from pandas import read_csv
from geopandas import read_file
from ..solar_simulation._sebe_simulation import _create_SEBE_folder
from ..utils import clip_raster, zonal_statistics
from rasterio import open

""" POST PROCESSING """
def _verify_SEBE_results(path_merge_SEBE_raster, average = True, bool_global = True):
    """Verify the validity of a raster obtained from SEBE calculation.

    It verifies if there are negative values that would correspond to outlier values because the received irradiation must be above zero.
    Negative values could be obtainted when doing SEBE calculation with average meteorological files and when not estimating diffuse and direct components from global.

    Parameters
    ----------
    path_merge_SEBE_raster : pathlib.Path
        path of the SEBE raster (with SEBE results) to verify (path_merge_SEBE_raster obtained in `merge_SEBE_raster` for example)
    average : bool, optional
        boolean value to indicate if an average of the meteorological files was done or not, by default True
    bool_global : bool, optional
        boolean value to indicate if the diffuse and direct irradiance values were estimated or not from global irradiance values, by default True
    
    Returns
    -------
    has_negative_values : bool
        boolean value to indicate or not if the raster contains negative value
    """
    with open(str(path_merge_SEBE_raster)) as src:
        raster_data = src.read(1)
        has_negative_values = (raster_data < 0).any()

        if has_negative_values:
            if average == True and bool_global == False: 
                print('Negative irradiation values, it is physically not possible. It is possibly due to the averaging of meteorological data and a bad redistribution of diffuse and direct component inot pacthes of similar solid angles throughout the sky vault.')
            else : 
                print('Negative irradiation values ! It is physically not possible! There should have an error in the input settings!')
    
    return has_negative_values

def merge_raster(list, path_merge_raster):
    """Merge several raster files.

    Parameters
    ----------
    list : list 
        list of the path of the raster files to merge
    path_merge_raster : pathlib.Path
        path where to save the merge raster layer
    """
    processing.run("gdal:merge",\
    {'INPUT':list,\
    'PCT':False,\
    'SEPARATE':False,\
    'NODATA_INPUT':None,\
    'NODATA_OUTPUT':None,\
    'OPTIONS':'',\
    'EXTRA':'',\
    'DATA_TYPE':5,\
    'OUTPUT':str(path_merge_raster)})

def merge_SEBE_raster(grid_gdp, path_merge_SEBE_raster, path_final_output_folder, path_csv_folder, average = True, bool_global = True): 
    """Merge the raster files obtained from the SEBE simulation.

    The function take the raster files in the different subfolders (one for each grid tile).
    Only the rasters obtained from the tile where the SEBE calculation could be done are merged.
    A verification on each raster files and on the merge raster is done to be sure that there is only values above zero in the merge raster.

    Parameters
    ----------
    grid_gdp : GeoDataFrame
        geopandas grid file (from `define_grid`)
    path_merge_SEBE_raster : pathlib.Path
        path where to save the merge raster file with SEBE results
    path_final_output_folder : pathlib.Path
        path of the folder with the final results
    path_csv_folder : pathlib.Path
        path of the folder with temporary csv files (define in main function)
    average : bool, optional
        boolean value to indicate if an average of the meteorological files was done or not, by default True
    bool_global : bool, optional
        boolean value to indicate if the diffuse and direct irradiance values were estimated or not from global irradiance values, by default True
    """
    path_list_tiles = path_csv_folder / "list_incorrect_tiles.csv"
    df_list_tiles = read_csv(str(path_list_tiles))
    list_incorrect_tiles = df_list_tiles['tile_number'].tolist()
    fc =len(grid_gdp)
    list_SEBE_raster = []
    for i in range(0, fc): 
        j= i +1
        path_SEBE_temp_folder = _create_SEBE_folder(path_final_output_folder, j)
        path_SEBE_raster = path_SEBE_temp_folder / "Energyyearroof.tif"
        if j not in list_incorrect_tiles:
            if path_SEBE_raster.exists() :
                has_negative_value = _verify_SEBE_results(path_SEBE_raster, average = average, bool_global= bool_global)
                if has_negative_value : 
                    print(f"Check the settings of tile n°{j} where there are negative values!") 
                list_SEBE_raster.append(str(path_SEBE_raster))
            else : 
                print(f"The tile n°{j} has not been simulated. The irradiation map of this tile is not added to the merge irradiation map.")
    merge_raster(list_SEBE_raster, path_merge_SEBE_raster)
    has_negative_value = _verify_SEBE_results(path_merge_SEBE_raster, average = average, bool_global= bool_global)

def create_buffer(path_buildings, path_buildings_buffer, distance = -1.5): 
    """Create a (negative) buffer for building footprints (towards the center).

    It is done in order to not consider the edges of the buildings (for zonal statistics). The default ``distance`` of the buffer : -1.5m.

    Parameters
    ----------
    path_buildings : pathlib.Path
        path of the shapefile with buildings, to which are applied the buffer (for example path_municipality_buildings_reproject_valid_sup_0 obtained in select_buildings_height_sup_0)
    path_buildings_buffer : pathlib.Path
        path to save the layer (buildings with buffer)
    distance : float, optional
        Size of the buffer (distance from the original edge to the final edge. Negative : remove size of the shapefile), by default -1.5
    """
    if distance > 0 : 
        print('Distance should be below zero to be coherent with the methodology. The buffer is created to not include values at the edge of buildings ! The negative values mean that the building footprints with buffer are smaller than the original ones.')
        
    processing.run("native:buffer",\
    {'INPUT':str(path_buildings),\
    'DISTANCE':distance,\
    'SEGMENTS':5,\
    'END_CAP_STYLE':0,\
    'JOIN_STYLE':0,\
    'MITER_LIMIT':1,\
    'DISSOLVE':False,\
    'SEPARATE_DISJOINT':False,\
    'OUTPUT':str(path_buildings_buffer)})


def _post_process_buffer_zonal_stat(path_buildings_buffer_zonal_stat, path_buildings_buffer_zonal_stat_post_process, column_prefix = '_', statistics = 'mean'): 
    """Remove buildings that does not exist anymore with the applied buffer (remove the na value in zonal statistics applied to buildings with buffer)
    
    If the name of the column (``column_prefix`` + ``statistics``) is not found, other name of column are tried because the name could be shortened when the shapefile is saved.

    Parameters
    ----------
    path_buildings_buffer_zonal_stat : pathlib.Path
        path of the shapefile with buidings with buffer (from path_zonal_statistics obtain in zonal_statistics for example)
    path_buildings_buffer_zonal_stat_post_process : pathlib.Path
        path want to save the layer (buildings with zonal statistics and with no na value)
    column_prefix : str, optional
        prefix of the column that have been chosen to create the statistics, by default '_'
    statistics : str, optional
        name of the suffix of the column where to verify that there is no nan value, by default 'mean'

    Raises
    ------
    AttributeError
        name of the column (column_prefix + statistics) not found in the dataframe
        if column name is too long (>10 characters), the name was probably shortened before saving
        if statistics different from mean, count, sum : statistics has probably not been computed 
    """
    subset = column_prefix + statistics
    buildings_buffer = read_file(str(path_buildings_buffer_zonal_stat))

    list_stats = ['mean', 'count', 'sum']

    if subset not in buildings_buffer.columns:
        print(f"No column named {subset} found in the dataframe. Trying to find the right name.")
        try : 
            subset = column_prefix[:5] + statistics
            if subset in buildings_buffer.columns:
                print(f"column_prefix was shortened before, the actual column_prefix is {column_prefix[:5]}.")
            else: 
                raise AttributeError(f"column_prefix was not shortened before. Tring to find the right name.")
        except : 
            try : 
                subset = column_prefix + statistics
                subset = subset[:10]
                if subset in buildings_buffer.columns:
                    print(f"column name was shortened before, the actual columne name is {subset}.")
                else : 
                    raise AttributeError(f"column name was not shortened before. Trying to find the right name.")
            except : 
                subset = column_prefix + statistics
                if statistics not in list_stats: 
                    raise AttributeError('Statistics not in the list, should be either mean, count or sum.')
                elif len(subset)>10 : 
                    if len(column_prefix) > 5 : 
                        raise AttributeError('Name too long and has probably been shortened before saving the shapefile. Column prefix is long, could have been shortened before.')
                    else:
                        raise AttributeError('Name too long and has probably been shortened before saving the shapefile.')                
                else : 
                    raise AttributeError(f"No column named '{subset}' found in the dataframe.")
    
    buildings_buffer = buildings_buffer.dropna(subset=[subset])
    buildings_buffer = buildings_buffer.reset_index(drop=True)
    if len(buildings_buffer) ==0 : 
        raise ValueError( "No buildings left, the distance set in the creation of the buffer is probably too high ! ")
    buildings_buffer.to_file(str(path_buildings_buffer_zonal_stat_post_process))

def post_process(path_final_output_folder, grid_gpd, path_shapefiles, path_csv_folder, distance =-1.5, column_prefix = 'sol_',statistics = 'mean', bool_count = True, bool_sum = True, bool_mean = True, average = True, bool_global = True):  
    """Function to post process the results from iteration on the grid with the SEBE simulation.
    
    The clip SEBE rasters are merged in one raster, this raster is clipped at the municipality extent
    Buffers are created for buildings (to not consider edges values when doing zonal statistics). 
    Then zonal statistics are done to obtain an average annual irradiation value per building.
    The buildings shapefile with zonal statistics is post processed to remove the na values.

    Parameters
    ----------
    path_final_output_folder : pathlib.Path
        path of the folder with the final results (define in main function)
    grid_gpd : GeoDataFrame
        geopandas grid file (from define_grid)
    path_shapefiles : pathlib.Path
        path of the folder with temporary shapefiles (define in main function)
    path_csv_folder : pathlib.Path
        path of the folder with temporary csv files (define in main function)
    distance : float, optional
        Size of the buffer (distance from the original edge to the final edge (Negative : remove size of the shapefile), by default -1.5
    column_prefix : str, optional
        prefix of the column that have been chosen to create the statistics, by default 'sol\_'
    statistics : str, optional
        name of the suffix of the column where to verify that there is no nan value, by default 'mean'
    bool_count : bool, optional
        boolean value to obtain or not the number of pixel inside each shape in zonal statistics of merge SEBE raster, by default True
    bool_sum : bool, optional
        boolean value to obtain or not the sum of the pixel values inside each shape in zonal statistics of merge SEBE raster, by default True
    bool_mean : bool, optional
        boolean value to obtain or not the average of the pixel values inside each shape in zonal statistics of merge SEBE raster, by default True
    average : bool, optional
        boolean value to indicate if an average of the meteorological files was done or not, by default True
    bool_global : bool, optional
        boolean value to indicate if the diffuse and direct irradiance values were estimated or not from global irradiance values, by default True
    """

    if len(column_prefix)>5 : 
        column_prefix = column_prefix[:5]
        print(f'Prefix name too long, the name of the column could not be saved entirely, column_prefix has been shorten to :{column_prefix}') 

    path_reproject_municipality_footprint = path_shapefiles / "municipality_footprint_reproject.shp"
    path_municipality_buildings_reproject_valid_sup_0 = path_shapefiles / "municipality_buildings_reproject_valid_sup_0.shp"

    path_merge_SEBE_raster = path_final_output_folder / "merge_annual_solar_energy.tif"
    merge_SEBE_raster(grid_gpd, path_merge_SEBE_raster, path_final_output_folder, path_csv_folder, average = average, bool_global=bool_global)
    path_clip_raster_municipality = path_final_output_folder / "merge_annual_solar_energy_clip_municipality_extent.tif"
    clip_raster(path_reproject_municipality_footprint, path_merge_SEBE_raster, path_clip_raster_municipality)
    path_buffer_buildings = path_shapefiles / "buffer_buildings.shp"
    create_buffer(path_municipality_buildings_reproject_valid_sup_0, path_buffer_buildings, distance=distance)
    path_buffer_buildings_zonal_stats = path_shapefiles / "buffer_buildings_zonal_stats_solar.shp"
    solar_prefix = zonal_statistics(path_buffer_buildings, path_merge_SEBE_raster, path_buffer_buildings_zonal_stats, column_prefix = column_prefix, bool_count = bool_count, bool_sum = bool_sum, bool_mean = bool_mean)
    path_buildings_buffer_zonal_stat_post_process = path_final_output_folder / "buildings_zonal_stats_solar.shp"
    _post_process_buffer_zonal_stat(path_buffer_buildings_zonal_stats, path_buildings_buffer_zonal_stat_post_process, column_prefix = solar_prefix , statistics = statistics)


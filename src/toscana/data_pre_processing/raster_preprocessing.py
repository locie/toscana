import sys
from osgeo import gdal

from ..utils import processing

from geopandas import read_file
from numpy import nan
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsCoordinateReferenceSystem
from requests import get
from zipfile import ZipFile
from ..data_post_processing import merge_raster



""" PRE PROCESS RASTER FILES """
def _create_grid_download_dem(path_raw_data_folder, bool_France = True):
    """Create the grid (for France (default) or for Europe) with the name and URL of the DEM raster tile available on OpenDEM website.

    Parameters
    ----------
    path_raw_data_folder : pathlib.Path
        path of the folder with raw data (downloaded) files (define in main function)
    bool_France : bool, optional
        boolean value to indicate or not if the territory of interest is located in France or not, by default True

    Returns
    -------
    grid_dem : GeoDataFrame
        geopandas grid file used to download the DEM raster tile
    """
    if bool_France :
        extent ='3200000.000000000,4300000.000000000,2000000.000000000,3150000.000000000 [IGNF:ETRS89LAEA]' 
    else :  
        extent = '2600000.000000000,7400000.000000000,1350000.000000000,5450000.000000000 [IGNF:ETRS89LAEA]'
    
    path_grid_dem = path_raw_data_folder / 'grid_download_DEM_Open_DEM.shp'

    processing.run("native:creategrid",\
    {'TYPE':2,\
    'EXTENT':extent,\
    'HSPACING':50000,\
    'VSPACING':50000,\
    'HOVERLAY':0,\
    'VOVERLAY':0,\
    'CRS':QgsCoordinateReferenceSystem('IGNF:ETRS89LAEA'),\
    'OUTPUT':str(path_grid_dem)})

    grid_dem= read_file(str(path_grid_dem))
    for i in range(0, len(grid_dem)): 
        grid_dem.loc[i,'dem_tile'] = "N"+str(grid_dem.loc[i,"bottom"])[:3]+"E"+str(grid_dem.loc[i,"left"])[:3]
        grid_dem.loc[i,'url_dem'] ="https://opendemdata.info/data/europe_laea/"+grid_dem.loc[i,'dem_tile'] +".zip"
    grid_dem.to_file(str(path_grid_dem))
    return grid_dem

def _download_and_extract_data_DEM(link, dem_tile, path_raw_data_folder): 
    """Download a DEM raster tile from OpenDEM website giving a link and the name of the time.

    A packed folder is downloaded and then extracted.

    Parameters
    ----------
    link : str
        link used to download the DEM raster tile 
    dem_tile : str
        _name of the DEM raster tile
    path_raw_data_folder : pathlib.Path
        path of the folder with raw data (downloaded) files (define in main function)
    """     
    fn_packed_download_folder = dem_tile + ".zip"
    path_packed_download_folder = path_raw_data_folder / fn_packed_download_folder

    print(f"Download from : {link}")
    response = get(link)
    
    with open(str(path_packed_download_folder), 'wb') as f:
        f.write(response.content)
    print("Download completed.")
    with ZipFile(path_packed_download_folder, 'r') as zip_ref:
        zip_ref.extractall(path_raw_data_folder)
    print("Extraction completed.")

def download_extract_and_merge_DEM_from_OpenDEM(path_raw_data_folder,path_shapefiles, bool_France = True, threshold = 100): 
    """Download and extract the DEM raster tile from the OpenDEM website according to the municipality footprint extent.

    The raster tiles are then merged together to have a unique merge DEM. 
    First, the edge tile are obtained. If the municipality footprint extent is close to the border of the tile, the neighbouring tile is also download. 
    All the tiles that overlap with the extent of municipality footprint are downloaded and then merge together. 
    If the studied territory is not located in France, ``bool_France`` should be set to False. 
    
    Parameters
    ----------
    path_raw_data_folder : pathlib.Path
        path of the folder with raw data (downloaded) files (define in main function)
    path_shapefiles : pathlib.Path
        path of the folder with temporary shapefiles (define in main function)
    bool_France : bool, optional
        boolean value to indicate or not if the territory of interest is located in France or not, by default True
    threshold : int, optional
        minimal value (in meters) of the difference between the municipality extent and the border of the raster tile, by default 100

    Returns
    -------
    path_merge_dem : pathlib.Path
        path where is saved the merged DEM
    """    
    path_municipality_extent = path_shapefiles / "municipality_extent.shp"

    grid_dem = _create_grid_download_dem(path_raw_data_folder, bool_France = bool_France)
    extent_municipality = read_file(str(path_municipality_extent))

    list_a = []
    list_b = []

    #Top left point
    X_top_left = extent_municipality.loc[0, 'MINX']
    Y_top_left =extent_municipality.loc[0,'MAXY']
    for i in range(0,len(grid_dem)): 
        tile = grid_dem.loc[i]
        if tile["left"] < X_top_left and X_top_left < tile["right"] and tile["bottom"] < Y_top_left and Y_top_left < tile["top"] : 
            dem_tile_top_left = tile["dem_tile"]
            break

    list_a.append(int(dem_tile_top_left[1:4]))
    list_b.append(int(dem_tile_top_left[5:8]))
    if abs(X_top_left -tile["left"]) <threshold : 
        b_top_left = int(dem_tile_top_left[5:8])-5
        list_b.append(b_top_left)
    if abs(Y_top_left - tile["top"]) < threshold : 
        a_top_left = int(dem_tile_top_left[1:4])+ 5
        list_a.append(a_top_left)

    #Top right point
    X_top_right = extent_municipality.loc[0, 'MAXX']
    Y_top_right =extent_municipality.loc[0,'MAXY']
    for i in range(0,len(grid_dem)): 
        tile = grid_dem.loc[i]
        if tile["left"] < X_top_right and X_top_right < tile["right"] and tile["bottom"] < Y_top_right and Y_top_right < tile["top"] : 
            dem_tile_top_right= tile["dem_tile"]
            break

    if int(dem_tile_top_right[1:4]) not in list_a : 
        list_a.append(int(dem_tile_top_right[1:4]))
    if int(dem_tile_top_right[5:8]) not in list_b :
        list_b.append(int(dem_tile_top_right[5:8]))
    if abs(X_top_right -tile["right"]) <threshold : 
        b_top_right = int(dem_tile_top_right[5:8])+5
        if b_top_right not in list_b:
            list_b.append(b_top_right)
    if abs(Y_top_right - tile["top"]) < threshold : 
        a_top_right = int(dem_tile_top_right[1:4])+5
        if a_top_right not in list_a : 
            list_a.append(a_top_right)

    #Bottom left point
    X_bottom_left = extent_municipality.loc[0, 'MINX']
    Y_bottom_left =extent_municipality.loc[0,'MINY']
    for i in range(0,len(grid_dem)): 
        tile = grid_dem.loc[i]
        if tile["left"] < X_bottom_left and X_bottom_left < tile["right"] and tile["bottom"] < Y_bottom_left and Y_bottom_left < tile["top"] : 
            dem_tile_bottom_left = tile["dem_tile"]
            break

    if int(dem_tile_bottom_left[1:4]) not in list_a : 
        list_a.append(int(dem_tile_bottom_left[1:4]))
    if int(dem_tile_bottom_left[5:8]) not in list_b :
        list_b.append(int(dem_tile_bottom_left[5:8]))
    if abs(X_bottom_left -tile["left"]) <threshold : 
        b_bottom_left = int(dem_tile_bottom_left[5:8])-5
        if b_bottom_left not in list_b : 
            list_b.append(b_bottom_left)
    if abs(Y_bottom_left - tile["bottom"]) < threshold : 
        a_bottom_left = int(dem_tile_bottom_left[1:4])- 5
        if a_bottom_left not in list_a : 
            list_a.append(a_bottom_left)

    #Bottom right point
    X_bottom_right = extent_municipality.loc[0, 'MAXX']
    Y_bottom_right =extent_municipality.loc[0,'MINY']
    for i in range(0,len(grid_dem)): 
        tile = grid_dem.loc[i]
        if tile["left"] < X_bottom_right and X_bottom_right < tile["right"] and tile["bottom"] < Y_bottom_right and Y_bottom_right < tile["top"] : 
            dem_tile_bottom_right= tile["dem_tile"]
            break

    if int(dem_tile_bottom_right[1:4]) not in list_a : 
        list_a.append(int(dem_tile_bottom_right[1:4]))
    if int(dem_tile_bottom_right[5:8]) not in list_b :
        list_b.append(int(dem_tile_bottom_right[5:8]))
    if abs(X_bottom_right -tile["right"]) <threshold : 
        b_bottom_right = int(dem_tile_bottom_right[5:8])+5
        if b_bottom_right not in list_b : 
            list_b.append(b_bottom_right)
    if abs(Y_bottom_right - tile["bottom"]) < threshold : 
        a_bottom_right = int(dem_tile_bottom_right[1:4])-5
        if a_bottom_right not in list_a : 
            list_a.append(a_bottom_right)

    max_a = max(list_a)
    min_a = min(list_a)
    max_b = max(list_b)
    min_b = min(list_b)

    list_dem = []
    for a in range(min_a, max_a+5, 5): 
        for b in range(min_b, max_b+5, 5): 
            dem_tile= "N"+str(a) +"E" + str(b)
            url_dem = grid_dem[grid_dem["dem_tile"]==dem_tile]["url_dem"].values[0]
            path_dem_temp = path_raw_data_folder / f"{dem_tile}/{dem_tile}.tif"
            if path_dem_temp.exists() == False : 
                try : 
                    _download_and_extract_data_DEM(url_dem, dem_tile, path_raw_data_folder)
                    list_dem.append(str(path_dem_temp))
                except : 
                    print(f"It is not possible to download the DEM tile ({dem_tile}) from OpenDEM website.")
            else : 
                list_dem.append(str(path_dem_temp))

    path_merge_dem = path_raw_data_folder /"raw_merge_DEM.tif"
    merge_raster(list_dem, path_merge_dem)
    
    return path_merge_dem


def _obtain_large_grid_extent(path_grid, path_extent_grid,  projection = 'IGNF:ETRS89LAEA', extra_size = 1000):
    """Obtain the extent of the grid and large extent of the grid (necessary for next step).

    Parameters
    ----------
    path_grid : pathlib.Path
        path of the shapefile with the grid (path_grid from define_grid)
    path_extent_grid : pathlib.Path
        path where to save the shapefile with the (large) extent of the grid
    projection : str, optional
        name of the reference system of the grid, by default "IGNF:ETRS89LAEA"
    extra_size : int, optional
        extra width and height to add to the extent of the grid, by default 1000

    Returns
    -------
    large_extent_grid : str
        string with the large extent points of the grid extent(larger to enable a correct resampling of the DEM) (format needed for qgis simulation)
    """
    processing.run("native:polygonfromlayerextent",\
    {'INPUT':str(path_grid),'ROUND_TO':0,'OUTPUT':str(path_extent_grid)})
    extent_grid=QgsVectorLayer(str(path_extent_grid), '', 'ogr')
    for feat in extent_grid.getFeatures():
        x_min=feat['MINX']
        y_min=feat['MINY']
        x_max=feat['MAXX']
        y_max=feat['MAXY']
    extent_grid =f"{x_min}, {x_max}, {y_min}, {y_max} [{projection}]"
    x_min-=extra_size
    y_min-=extra_size
    x_max+=extra_size
    y_max+=extra_size
    large_extent_grid =f"{x_min}, {x_max}, {y_min}, {y_max} [{projection}]"
    return large_extent_grid

def _clip_DEM_large(path_intput_DEM, large_extent_grid, path_clip_large_DEM):
    """Clip the original DEM at the large extent of the grid (reduce computational time for next step)

    Parameters
    ----------
    path_intput_DEM : pathlib.Path
        path with the original DEM
    large_extent_grid : str
        string with the large extent of the grid (from obtain_large_grid_extent)
    path_clip_large_DEM : pathlib.Path
        path where to save the layer with the clipped DEM
    """
    processing.run("gdal:cliprasterbyextent",\
    {'INPUT':str(path_intput_DEM),\
    'PROJWIN':large_extent_grid,\
    'OVERCRS':False,\
    'NODATA':None,\
    'OPTIONS':'',\
    'DATA_TYPE':0,\
    'EXTRA':'',\
    'OUTPUT':str(path_clip_large_DEM)})

def resample_DEM(path_clip_large_DEM, path_resample_DEM, large_extent_grid, resample_method=1, resample_resolution=1): 
    """Resample the original DEM to obtain a DEM of 1m resolution (default), default option is bilinear resample.

    Parameters
    ----------
    path_clip_large_DEM : pathlib.Path
        path with the DEM to resample (path_output from clip_DEM_large)
    path_resample_DEM : pathlib.Path
        path where to save the layer with the resampled DEM
    large_extent_grid : str
        string with the large extent of the grid, from obtain_large_grid_extent
    resample_method : int, optional
        Select the resampling method (1= bilinear) , by default 1
        from 0 to 11, see gdal:warpreproject documentation
    resample_resolution : int, optional
        Select the resampling resolution, by default 1

    Raises
    ------
    AssertionError
        resample_method must be between 0 and 11 (available resampling method)
    """    
    if resample_method < 0 or resample_method >11: 
        raise AssertionError('This resampling method does not exist! resample_method should be between 0 and 11.')

    processing.run("gdal:warpreproject",\
    {'INPUT':str(path_clip_large_DEM),\
    'SOURCE_CRS':None,\
    'TARGET_CRS':None,\
    'RESAMPLING':resample_method,\
    'NODATA':None,\
    'TARGET_RESOLUTION':resample_resolution,\
    'OPTIONS':'',\
    'DATA_TYPE':0,\
    'TARGET_EXTENT':large_extent_grid,\
    'TARGET_EXTENT_CRS':None,\
    'MULTITHREADING':False,\
    'EXTRA':'',\
    'OUTPUT':str(path_resample_DEM)})

def select_buildings_height_sup_0(path_reproject_municipality_buildings, path_buildings_sup_0, height_column = "HAUTEUR"): 
    """Select only buildings with a height above 0 (necessary to create DSM).

    By default, the column name with the height of buildings is "HAUTEUR" (name of the column in BDTOPO database).

    Parameters
    ----------
    path_reproject_municipality_buildings : pathlib.Path
        path of the shapefile layer with the buildings (path_reproject_municipality_buildings from reproject buildings/check validity)
    path_buildings_sup_0 : pathlib.Path
        path where to save the layer with the shapefile with only buildings with a height above 0
    height_column : str, optional
        column name with the height of buildings, by default "HAUTEUR"
    """
    processing.run("native:extractbyexpression",\
    {'INPUT':str(path_reproject_municipality_buildings),\
    'EXPRESSION':f' "{height_column}" >0',\
    'OUTPUT':str(path_buildings_sup_0)})

def _fill_nodata(path_raster_with_nodata, path_filled_raster, value = 0.0 ): 
    """Fill raster with no data with a defined ``value`` (default is 0).

    Parameters
    ----------
    path_raster_with_nodata : pathlib.Path
        path of the raster with nodata values
    path_filled_raster : pathlib.Path
        path where to save the raster with a wanted value instead of the nodata values
    value : float, optional
        value by which are replaed the nodata values, by default 0.0
    """        
    processing.run("native:fillnodata", \
    {'INPUT':str(path_raster_with_nodata),\
    'BAND':1,\
    'FILL_VALUE':value,\
    'OUTPUT':str(path_filled_raster)})

def create_DSM(path_resample_DEM, path_buildings_sup_0, large_extent_grid, path_DSM, path_DSM_temp, pixel_resolution=1, height_column = "HAUTEUR"): 
    """Create the DSM from the DEM (resample at 1m resolution (default)).

    By default, the column name with the height of buildings is "HAUTEUR" (name of the column in BDTOPO database).
    The nodata values of the DSM are replaced by 0. 

    Parameters
    ----------
    path_resample_DEM : pathlib.Path
        path of the DEM (path_resample_DEM from resample_DEM)
    path_buildings_sup_0 : pathlib.Path
        path of the shapefile with buildings (and heights) (path_buildings_sup_0 from select_buildings_height_sup_0)
    large_extent_grid : str
        string with the large extent of the grid (from obtain_large_grid_extent)
    path_DSM : pathlib.Path
        path where to save the layer with the created DSM
    path_DSM_temp : pathlib.Path
        path where to save a temporary layer used to create the final DSM
    pixel_resolution : int, optional
        Resolution of the DSM, by default 1
    height_column : str, optional
        column name with the height of buildings, by default "HAUTEUR"
    """
    processing.run("umep:Spatial Data: DSM Generator", \
    {'INPUT_DEM':str(path_resample_DEM),\
    'INPUT_POLYGONLAYER':str(path_buildings_sup_0),\
    'INPUT_FIELD':height_column,\
    'USE_OSM':False,\
    'BUILDING_LEVEL':3.1,\
    'EXTENT':large_extent_grid,\
    'PIXEL_RESOLUTION':pixel_resolution,\
    'OUTPUT_DSM':str(path_DSM_temp)})

    _fill_nodata(path_DSM_temp, path_DSM)

def create_DHM(path_resample_DEM, path_buildings_sup_0, large_extent_grid, path_DHM_temp_1, path_DHM_temp_2, path_DHM, pixel_resolution=1, height_column = "HAUTEUR"): 
    """Create the DHM (only building height above ground level) with a resolution of 1m (default).
    
    First step : create a raster with zero value at the same size/extent than the DSM.
    Second step : create the DHM by adding building height. By default, the column name with the height of buildings is "HAUTEUR" (name of the column in BDTOPO database).
    Third step : replace the nodata values of the DHM by 0.

    Parameters
    ----------
    path_resample_DEM : pathlib.Path
        path of the DEM (path_resample_DEM from resample_DEM)
    path_buildings_sup_0 : pathlib.Path
        path of the shapefile with buildings (and heights) (path_buildings_sup_0 from select_buildings_height_sup_0)
    large_extent_grid : str
        string with the large extent of the grid (from obtain_large_grid_extent) 
    path_DHM_temp_1 : pathlib.Path
        path where to save a temporary layer used to create the final DHM
    path_DHM_temp_2 : pathlib.Path
        path where to save a second temporary layer used to create the final DHM
    path_DHM : pathlib.Path
        path where to save the created DHM
    pixel_resolution : int, optional
        Resolution of the DHM, by default 1
    height_column : str, optional
        column name with the height of buildings, by default "HAUTEUR"
    """
    processing.run("gdal:rastercalculator",\
    {'INPUT_A':str(path_resample_DEM),\
    'BAND_A':1,\
    'FORMULA':'A*0.0',\
    'NO_DATA':None,\
    'EXTENT_OPT':0,\
    'PROJWIN':None,\
    'RTYPE':5,\
    'OPTIONS':'',\
    'EXTRA':'',\
    'OUTPUT':str(path_DHM_temp_1)})

    processing.run("umep:Spatial Data: DSM Generator", \
    {'INPUT_DEM':str(path_DHM_temp_1),\
    'INPUT_POLYGONLAYER':str(path_buildings_sup_0),\
    'INPUT_FIELD':height_column,\
    'USE_OSM':False,\
    'BUILDING_LEVEL':0.1,\
    'EXTENT':large_extent_grid,\
    'PIXEL_RESOLUTION':pixel_resolution,\
    'OUTPUT_DSM':str(path_DHM_temp_2)})
    
    _fill_nodata(path_DHM_temp_2, path_DHM)

def preprocess_raster_file(path_raster_files, path_shapefiles, path_DEM, projection = 'IGNF:ETRS89LAEA',extra_size = 1000, resample_method=1,height_column = "HAUTEUR",  pixel_resolution=1): 
    """Preprocess and create the raster files that are needed for the SEBE simulation.

    A larger DEM than the grid extent is needed because of the resampling. 
    The DEM is resampled in order to have a resolution of 1m. 
    This resolution is needed to add the height of building to create the DSM. 
    Only buildings with height above zero are kept for the analysis. 
    A DHM is also created for the calculation of wall height and wall aspect.

    Parameters
    ----------
    path_raster_files : pathlib.Path
        path of the folder with temporary raster files (define in main function)
    path_shapefiles : pathlib.Path
        path of the folder with temporary shapefiles (define in main function)
    path_DEM : pathlib.Path
        path of the raw input DEM, it is supposed to have 25m resolution and IGNF ETRS89LAEA projection
    projection : str, optional
        name of the reference system of the grid, by default "IGNF:ETRS89LAEA"
    extra_size : int, optional
        extra width and height to add to the extent of the grid, by default 1000
    resample_method : int, optional
        Select the resampling method (1 = bilinear), by default 1
        from 0 to 11, see gdal:warpreproject documentation
    height_column : str, optional
        column name with the height of buildings, by default "HAUTEUR"
    pixel_resolution : int, optional
        Select the resolution of the rasters, by default 1

    Raises
    ------
    AssertionError
        extra_size should be high enough to enable the resampling (extra_size < 4*resolution_x or extra_size <4*resolution_y)
    AttributeError
        height_column not in the dataframe
    AttributeError
        height_column must contain numbers (int or float)
    """
    layer = QgsRasterLayer(str(path_DEM), "")
    transform = layer.rasterUnitsPerPixelX()  
    resolution_x = transform if transform else 0
    transform = layer.rasterUnitsPerPixelY() 
    resolution_y = transform if transform else 0
    if extra_size <4*resolution_x or extra_size <4*resolution_y : 
        raise AssertionError('Extra size too small : resampling could failed')

    path_municipality_grid = path_shapefiles / "municipality_grid.shp"
    path_municipality_buildings_reproject_valid = path_shapefiles / "municipality_buildings_reproject_valid.shp"

    buildings = read_file(str(path_municipality_buildings_reproject_valid))
    if height_column  not in buildings.columns:
        raise AttributeError(f"No column named '{height_column}' found in the dataframe.")
    
    
    def convert_to_float(value):
        """Convert the values contains in a column of a dataframe to float if there are nummbers in string format.

   

        Parameters
        ----------
        value : str
            string to convert to float if possible

        Returns
        -------
        string_value : float
            float value of the string if possible

        Raises
        ------
        AttributeError
            String value must be a number
        """        
        try:
            string_value = float(value)
            return string_value
        except ValueError:
            raise AttributeError('The height column does not contain numbers!')
        
    dtype = buildings[height_column].dtype

    if dtype != 'float64' and dtype !="int":
        buildings[height_column].fillna("0", inplace=True)
        buildings[height_column] = buildings[height_column].apply(convert_to_float)
        print("The column contains string that can be converted to numbers")

    path_grid_extent = path_shapefiles / "grid_extent.shp"
    large_extent_grid = _obtain_large_grid_extent(path_municipality_grid, path_grid_extent, projection=projection, extra_size=extra_size)

    path_clip_DEM_large = path_raster_files / "DEM_clip_large.tif"
    _clip_DEM_large(path_DEM, large_extent_grid, path_clip_DEM_large)
    path_DEM_resample =  path_raster_files / "DEM_resample.tif"
    resample_DEM(path_clip_DEM_large, path_DEM_resample, large_extent_grid, resample_method=resample_method, resample_resolution=pixel_resolution)
    path_municipality_buildings_reproject_valid_sup_0 = path_shapefiles / "municipality_buildings_reproject_valid_sup_0.shp"
    select_buildings_height_sup_0(path_municipality_buildings_reproject_valid, path_municipality_buildings_reproject_valid_sup_0, height_column=height_column)
    path_DSM_temp = path_raster_files/"DSM_temp.tif"
    path_DSM = path_raster_files / "DSM.tif"
    create_DSM(path_DEM_resample, path_municipality_buildings_reproject_valid_sup_0, large_extent_grid, path_DSM, path_DSM_temp, pixel_resolution=pixel_resolution, height_column=height_column)
    path_DHM_temp_1 = path_raster_files / "DHM_temp_1.tif"
    path_DHM_temp_2 = path_raster_files / "DHM_temp_2.tif"
    path_DHM = path_raster_files / "DHM.tif"
    create_DHM(path_DEM_resample, path_municipality_buildings_reproject_valid_sup_0, large_extent_grid, path_DHM_temp_1, path_DHM_temp_2, path_DHM, pixel_resolution=pixel_resolution, height_column=height_column)

 


from qgis.core import QgsApplication

qgs = QgsApplication([], False)
qgs.initQgis()

import processing
from processing.core.Processing import Processing
Processing.initialize()
import sys


# import of 'umep_processing'
from os import environ
from platform import system

HOME = environ['HOME']
system_ = system()
file_exists = False
try:
    with open(f'{HOME}/.toscana_config.txt', 'r') as f:
        plugin_path = f.readline().rstrip()
except BaseException as e:
    if system_ == 'Windows':
        plugin_path = rf'{HOME}\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins'
    elif system_ == 'Darwin':
        plugin_path = rf'{HOME}/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins'
    else: # Linux-like
        plugin_path = rf'{HOME}/.local/share/QGIS/QGIS3/profiles/default/python/plugins'
    with open(f'{HOME}/.toscana_config.txt', 'w') as f:
        f.write(plugin_path)

sys.path.append(plugin_path)
try:
    from processing_umep.processing_umep_provider import ProcessingUMEPProvider ## this line display Warnings ##
except ModuleNotFoundError as e:
    raise ModuleNotFoundError(f"""Qgis plugin 'processing_umep' could not be found.
          1. Make sure to install it using the plugin manager from Qgis. The installation directory can be found using the
             Qgis interface: Settings -> User profiles -> Open active profile folder, then "python/plugins" should contain processing_UMEP.
          2. If it installed in a non standard directory, please specify the full absolute plugin path in file "{HOME}/.toscana_config.txt".
             Current path is "{plugin_path}".""")



umep_provider = ProcessingUMEPProvider()

qgs.processingRegistry().addProvider(umep_provider)


from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsVectorLayer
from qgis.core import edit


from geopandas import read_file 
from pandas import DataFrame ,read_csv 
from scipy.stats import johnsonsu
from numpy import min, max, array, append, histogram
from sklearn.metrics import r2_score


def create_centroid(path_shapefile, path_centroid):
    """Create centroids of a shapefile (grid, municipality footprint for example).

    Parameters
    ----------
    path_shapefile : pathlib.Path
        path of the shapefile for which the centroids are wanted (for example path_grid obtained in `define_grid`, or path_reproject_municipality_footprint obtained in `reproject_municipality_footprint`)
    path_centroid : pathlib.Path
        path where to save the created shapefile with the centroids

    Returns
    -------
    gdf_centroid : GeoDataFrame
        geopandas file with the centroids
    """
    processing.run("native:centroids",\
    {'INPUT':str(path_shapefile),\
    'ALL_PARTS':False,\
    'OUTPUT':str(path_centroid)})
    gdf_centroid = read_file(str(path_centroid))
    return  gdf_centroid

def create_csv_coordinates(path_shapefile, path_shapefile_coordinates, path_csv_file):
    """Obtain the coordinates (longitude, latitude) of some points (centroids for example) in a shapefile and transform it into a csv file. 

    Parameters
    ----------
    path_shapefile : pathlib.Path
        path of the shapefile with the points for which the coordinates are wanted
    path_shapefile_coordinates : pathlib.Path
        path where to save the shapefile with the coordinates of the points
    path_csv_file : pathlib.Path
        path where to save the csv file with the coordinates of the points

    Returns
    -------
    df_points : DataFrame
        dataframe with coordinates of the points. 
    """
    processing.run("native:addxyfields",\
    {'INPUT':str(path_shapefile),\
    'CRS':QgsCoordinateReferenceSystem('EPSG:4326'),\
    'PREFIX':'',\
    'OUTPUT':str(path_shapefile_coordinates)})

    layer = QgsVectorLayer(str(path_shapefile_coordinates), '', 'ogr')
    for field in layer.fields():
        print(field.name())
        if field.name() == 'x':
            with edit(layer):
                idx = layer.fields().indexFromName(field.name())
                layer.renameAttribute(idx, 'longitude')
        if field.name() == 'y':
            with edit(layer):
                idx = layer.fields().indexFromName(field.name())
                layer.renameAttribute(idx, 'latitude')

    processing.run("native:savefeatures", \
    {'INPUT':str(path_shapefile_coordinates),\
    'OUTPUT':str(path_csv_file),\
    'LAYER_NAME':'',\
    'DATASOURCE_OPTIONS':'',\
    'LAYER_OPTIONS':''})

    df_points = read_csv(str(path_csv_file))
    return df_points

def clip_raster(path_mask_shapefiles, path_input_raster, path_clip_raster):
    """Clip a raster based on a shapefile mask layer (a grid tile for example).

    Parameters
    ----------
    path_mask_shapefiles : pathlib.Path
        path of the shapefile used as mask (clip to the shapefile extent) (for example path_clip_grid obtained in `clip_grid` or path_reproject_municipality_footprint obtained in `reproject_municipality_footprint`)
    path_input_raster : pathlib.Path
        path of the raster that need to be clipped (for example DSM, DHM)
    path_clip_raster : pathlib.Path
        path where to save the clip raster layer (raster tiles for example)
    """
    processing.run("gdal:cliprasterbymasklayer",\
    {'INPUT':str(path_input_raster),\
    'MASK':str(path_mask_shapefiles),\
    'SOURCE_CRS':None,\
    'TARGET_CRS':None,\
    'NODATA':None,\
    'ALPHA_BAND':False,\
    'CROP_TO_CUTLINE':True,\
    'KEEP_RESOLUTION':False,\
    'SET_RESOLUTION':False,\
    'X_RESOLUTION':None,\
    'Y_RESOLUTION':None,\
    'MULTITHREADING':False,\
    'OPTIONS':'',\
    'DATA_TYPE':0,\
    'EXTRA':'',\
    'OUTPUT':str(path_clip_raster)})

def zonal_statistics(path_shapefile, path_raster, path_zonal_statistics, bool_count = True, bool_sum = True, bool_mean = True, column_prefix = '_'):
    """Obtain statistics for each shape of a shapefile according to a raster file (count the number of pixel (default :True), sum the pixel values (default : True), average of the pixel values (default : True)). ``column_prefix`` could be used to define the name of the column where will be stored the statistics (linked with the raster data that are used to calculate the statistics for example).

    Parameters
    ----------
    path_shapefile : pathlib.Path
        path of the shapefile containing the shapes for which statistics are wanted (path_buildings_buffer obtained in `create_buffer` for example)
    path_raster : pathlib.Path
        path of the raster containing the value on which statistics will be calculated (path_merge_SEBE_raster obtained in `merge_SEBE_raster` for example)
    path_zonal_statistics : pathlib.Path
        path where to save the layer with zonal statistics
    bool_count : bool, optional
        boolean value to obtain or not the number of pixel inside each shape, by default True
    bool_sum : bool, optional
        boolean value to obtain or not the sum of the pixel values inside each shape, by default True
    bool_mean : bool, optional
        boolean value to obtain or not the average of the pixel values inside each shape, by default True
    column_prefix : str, optional
        prefix name of the columns that will be created to store the different statistics, by default '_'

    Returns
    -------
    column_prefix : str
        prefix name of the columns that are created to store the different statistics
    """
    if len(column_prefix)>5 : 
        column_prefix = column_prefix[:5]
        print(f'Prefix name too long, the name of the column could not be saved entirely, column_prefix has been shorten to :{column_prefix}') 

    list_stat= []
    if bool_count == True:
        list_stat.append(0)
    if bool_sum == True :
        list_stat.append(1)
    if bool_mean == True :
        list_stat.append(2)

    processing.run("native:zonalstatisticsfb",\
    {'INPUT':str(path_shapefile),\
    'INPUT_RASTER':str(path_raster),\
    'RASTER_BAND':1,\
    'COLUMN_PREFIX':column_prefix,\
    'STATISTICS':list_stat,\
    'OUTPUT':str(path_zonal_statistics)})
    return column_prefix

def calculate_r2_johnsonsu(fitting_parameters, x_obs, y_obs):
    """Calculate the R2 coefficient between the real distribution (``x_obs`` and ``y_obs``) and the Johnson's SU distribution from `fitting_parameters`` a,b,c,d.

    Parameters
    ----------
    fitting_parameters : tuple
        float tuple with the fitting parameters of the Johnson's SU distribution (a,b,c,d), c is the location parameter and d is the scale parameter
    x_obs : list
        list of x value of the real distribution (irradiation)
    y_obs : list
        list of y value of the real distribution (probability)

    Returns
    -------
    r2_johnsonsu : float
        R2 coefficient calculated between real distribution and Johnson's SU distribution.
    """
    a,b,c,d = fitting_parameters
    y_pred =  johnsonsu.pdf(x_obs, a, b, c, d)
    return r2_score(y_obs, y_pred)

def calculate_histogram_and_johnsonsu_fit(path_irradiation_csv, bool_buffer =True): 
    """Calculate the histogram/distribution from a csv file and calculate the fitted Johnson's SU distribution. 
    
    It is especially made to calculate the histogram for the distribution of the average annual irradiation received by building rooftops, with x value representing irradiation values and y value representing probability values.
    Two methods are tested to fit the Johnson's SU distribution : a classic method (init) and a method by setting floc = xmax (xmax, setting the location parameter to the maximum value of x value of the real distribution). 
    The fitting parameters (a,b,c,d) with the best R2 coefficient value are kept.

    Parameters
    ----------
    path_irradiation_csv : pathlib.Path
        path of the csv file with irradiation value (path_irradiation_csv obtained in generate_irradiation_csv_file)
    bool_buffer : bool, optional
        boolean value to specify or not if the shapefile with building footprints used to obtain the irradiation value has a buffer and then na value need to be removed, by default True

    Returns
    -------
    data : DataFrame
        dataframe with irradiation values
    nb_bins : int
        number of bins in the histogram
    fitting_parameters : tuple
        float tuple with the fitting parameters of the Johnson's SU distribution (a,b,c,d), c is the location parameter and d is the scale parameter
    x : list     
        x values used to calculate the histogram (middle value of the bar), with two more values added (that will be used for the display of Johnson's SU fit)
    R2 : float    
        best R2 coefficient calculated between the real distribution and the fitted Johnson's SU distribution between the two methods (classic (init) or floc=xmax(xmax))
    R2_init : float    
        R2 coefficient calculated between the real distribution and the fitted Johnson's SU distribution with classic method
    R2_xmax : float
        R2 coefficient calculated between the real distribution and the fitted Johnson's SU distribution by setting floc = xmax (maximum value of the x value of the real distribution)
    method : str
        name of the method with the best R2 coefficient between the classic method or by setting floc = xmax (maximum value of the x value of the real distribution) (init for initial, or xmax for floc =xmax)
    """
    try : 
        data = read_csv(str(path_irradiation_csv), usecols=range(1,2))
        data = data.squeeze()
        if bool_buffer== True : 
            data=data.loc[data!=0.0].dropna()
        min_data = min(data)
        max_data = max(data)
        nb_bins = int((max_data-min_data)/5)
        hist, bins = histogram(data, bins = nb_bins, density= True)
        x = (bins[:-1]+bins[1:])/2
        df_proba = DataFrame({'x':x, 'Probability' : hist})
        y_obs = array(df_proba['Probability'])
        x_obs = array(df_proba['x'])
        xmax = x_obs.max()

        params_est = johnsonsu.fit(data)
        a = params_est[0]
        b = params_est[1]
        c = params_est[2]
        d = params_est[3]
        R2_init = calculate_r2_johnsonsu((a,b,c,d), x_obs, y_obs)
        R2 = R2_init
        method = "init"
        param_est_xmax = johnsonsu.fit(data, floc = xmax)
        a_xmax = param_est_xmax[0]
        b_xmax = param_est_xmax[1]
        c_xmax = param_est_xmax[2]
        d_xmax = param_est_xmax[3]
        R2_xmax = calculate_r2_johnsonsu((a_xmax,b_xmax,c_xmax,d_xmax), x_obs, y_obs)
        if R2_xmax >R2_init : 
            a = a_xmax
            b =b_xmax
            c=c_xmax
            d=d_xmax
            R2 = R2_xmax
            method = "xmax"
        last_bin_width = x[-1] - x[-2]
        x = append(x, x[-1]+last_bin_width)
        x = append(x, x[-1]+last_bin_width)
        fitting_parameters = (a,b,c,d)
        return data, nb_bins, fitting_parameters,x, R2, R2_init, R2_xmax, method
    except ValueError as e: 
        if "cannot convert float NaN to integer" in str(e) :   
            print("It is possible that the distance of the buffer is too high, no buildings left, histogram can not be calculated and displayed.")
 
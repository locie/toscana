# import numpy as np
from scipy.stats import johnsonsu
from geopandas import read_file 
from socket import setdefaulttimeout
from urllib.request import urlopen, Request 
from io import StringIO 
from numpy import cos, sin, pi, nan, exp, sinh, cosh, linspace, sqrt, std, mean, median, quantile
from shapely.geometry import Polygon
from tqdm import tqdm
from pandas import DataFrame, Series, read_csv, concat
from urllib.error import HTTPError
from requests.exceptions import HTTPError as exceptionsHTTPError, ReadTimeout as exceptionsReadTimeout
from ..utils import processing

from ..utils import zonal_statistics, create_centroid, create_csv_coordinates, calculate_histogram_and_johnsonsu_fit

"""" CHARACTERISTICS OF THE MUNICIPALITY AND THE SOLAR DISTRIBUTION """
def johnsonsu_mean(fitting_parameters): 
    """Calculate the mean value of a Johnson's SU distribution from fitting parameters a,b,c,d.

    Parameters
    ----------
    fitting_parameters : tuple
        float tuple with the fitting parameters of the Johnson's SU distribution (a,b,c,d), c is the location parameter and d is the scale parameter

    Returns
    -------
    mean : float
        mean value of the Johnson's SU distribution
    """
    a,b,c,d = fitting_parameters
    mean = c-d*exp((b**(-2))/2)*sinh(a/b)
    return mean

def johnsonsu_median(fitting_parameters):
    """Calculate the median value of a Johnson's SU distribution from fitting parameters a,b,c,d.

    Parameters
    ----------
    fitting_parameters : tuple
        float tuple with the fitting parameters of the Johnson's SU distribution (a,b,c,d), c is the location parameter and d is the scale parameter

    Returns
    -------
    median : float
        median value of the Johnson's SU distribution
    """
    a,b,c,d = fitting_parameters
    median = c+d*sinh(-a/b)
    return median

def johnsonsu_variance(fitting_parameters):
    """Calculate the variance value of a Johnson's SU distribution from fitting parameters a,b,d.

    Parameters
    ----------
    fitting_parameters : tuple
        float tuple with the fitting parameters of the Johnson's SU distribution (a,b,d), d is the scale parameter

    Returns
    -------
    variance : float
        variance value of the Johnson's SU distribution
    """
    a,b,d = fitting_parameters
    variance = ((d**2)/2)*(exp(b**(-2))-1)*(exp(b**(-2))*cosh(2*a/b)+1)
    return variance

def johnsonsu_mode(fitting_parameters):   
    """Calculate the mode value of a Johnson's SU distribution from fitting parameters a,b,c,d.

    Parameters
    ----------
    fitting_parameters : tuple
        float tuple with the fitting parameters of the Johnson's SU distribution (a,b,c,d), c is the location parameter and d is the scale parameter

    Returns
    -------
    mode : float
        mode value of the Johnson's SU distribution
    p_mode : float
        probability value at mode's value of the Johnson's SU distribution
    """
    a,b,c,d = fitting_parameters
    median = johnsonsu_median(fitting_parameters)
    x =  linspace(0, median*2, 1000)
    mode = 0
    p_mode =0
    for i in range(0, len(x)): 
        if johnsonsu.pdf(x[i],a,b,c,d)> p_mode:
            mode = x[i]
            p_mode= johnsonsu.pdf(x[i],a,b,c,d)
    return mode, p_mode 

def johnsonsu_std(fitting_parameters):
    """Calculate the standard deviation value of a Johnson's SU distribution from fitting parameters a,b,d.

    Parameters
    ----------
    fitting_parameters : tuple
        float tuple with the fitting parameters of the Johnson's SU distribution (a,b,d), d is the scale parameter

    Returns
    -------
    std : float
        standard deviation value of the Johnson's SU distribution
    """
    a,b,d = fitting_parameters
    variance = johnsonsu_variance((a, b,d))
    std = sqrt(variance)
    return std

def johnsonsu_width(fitting_parameters, divide):
    """Calculate the spread of a Johnson's SU distribution at a certain percentage of the maximum value (probability value of the mode) from fitting parameters a,b,c,d.
    It looks for the two x values for which the probability value is equal to 1/``divide`` of the probability value of the mode, and then calculate the difference between these two values.
    It is made to calculte the spread at one-third maximum (``divide`` = 3). 

    Parameters
    ----------
    fitting_parameters : tuple
        float tuple with the fitting parameters of the Johnson's SU distribution (a,b,c,d), c is the location parameter and d is the scale parameter
    divide : float
        value used to divide the probability maximum value and obtain a probability height at which the spread of the distribution is wanted. This value is used to search for the x values corresponding of this probability value in the Johnson's SU distribution from fitting parameters a,b,c,d

    Returns
    -------
    values_below_mode : float
        x value with probability equal to 1/divide of the probability value of the mode, x value smaller than the mode value
    values_above_mode : float
        x value with probability equal to 1/divide of the probability value of the mode, x value higher than the mode value
    spread : float
        spread of the distribution at 1/divide maximum
    """
    a,b,c,d = fitting_parameters
    mode, pdf_mode = johnsonsu_mode(fitting_parameters)
    threshold = pdf_mode / divide
    values_below_mode = 0
    values_above_mode = 0

    x = mode
    while True:
        pdf_value = johnsonsu.pdf(x, a, b,c,d)
        if pdf_value < threshold:
            values_below_mode=x
            break
        x -= 0.01

    x = mode
    while True:
        pdf_value = johnsonsu.pdf(x, a, b,c,d)
        if pdf_value < threshold:
            values_above_mode=x
            break
        x += 0.01

    spread = values_above_mode - values_below_mode
    return values_below_mode,values_above_mode, spread

def calculate_area_and_perimeter(path_shapefile, path_shapefile_perimeter_and_area) : 
    """Calcualte the area and perimeter of a shapefile.

    Parameters
    ----------
    path_shapefile : pathlib.Path
        path of the shapefile for which the perimeter and area are wanted
    path_shapefile_perimeter_and_area : pathlib.Path
        path where to save the shapefile layer with perimeter and area values
    """
    processing.run("qgis:exportaddgeometrycolumns", \
    {'INPUT':str(path_shapefile),\
    'CALC_METHOD':0,\
    'OUTPUT':str(path_shapefile_perimeter_and_area)})

def calculate_village_characteristics(path_shapefiles, path_csv_folder, path_reproject_municipality_footprint, path_DEM_resample, population_column = "POPULATION"): 
    """Calculate the area, the perimeter, the mean altitude of a municipality footprint, as well as the longitude and the latitude of the center of the village. 
    
    Zonal statistics with the resample DEM and the municipality footprint is used to obtain the mean altitude. 
    The centroid of the municipality footprint is obtained to then obtain the coordinates of this centroid.  
    Get the number of inhabitants of the municipality in the column ``population_column`` (default : "POPULATION")  and return a nan if not available. 

    Parameters
    ----------
    path_shapefiles : pathlib.Path
        path of the folder with temporary shapefiles (define in main function)
    path_csv_folder : pathlib.Path
        path of the folder with temporary csv files (define in main function)
    path_reproject_municipality_footprint : pathlib.Path
        path of the municipality footprint shapefile reproject in the IGNF ETRS89LAEA reference system (for example path_reproject_municipality_footprint from reproject_municipality_footprint)
    path_DEM_resample : pathlib.Path
        path of the resampled DEM raster file (for example path_resample_DEM obtained in resample_DEM)
    population_column : str, optional
        name of the column with number of inhabitants of the studied municipality in the municipality footprint shapefile, by default "POPULATION"

    Returns
    -------
    area : float
        area of the municipality footprint
    perimeter : float
        perimeter of the municipality footprint
    mean_altitude : float
        mean altitude value of the municipality footprint
    latitude_center : float
        latitude of the center of the municipality
    longitude_center : float
        longitude of the center of the municipality
    population : int
        population of the municipality (informed by IGN)
    """ 
    path_perimeter_and_area_municipality = path_shapefiles / "municipality_area_and_perimeter.shp"
    calculate_area_and_perimeter(path_reproject_municipality_footprint, path_perimeter_and_area_municipality)
    area_and_perimeter = read_file(str(path_perimeter_and_area_municipality))
    area = area_and_perimeter.loc[0, "area"]/ 1000000
    perimeter = area_and_perimeter.loc[0, "perimeter"]/ 1000
    try : 
        population  = area_and_perimeter.loc[0, population_column]
    except : 
        population = nan
    path_zonal_statistics_altitude_municipality = path_shapefiles  / "municipality_zonal_stats_altitude.shp"
    prefix = zonal_statistics(path_reproject_municipality_footprint, path_DEM_resample, path_zonal_statistics_altitude_municipality, column_prefix = 'alt_')
    zonal_stats_municipality = read_file(str(path_zonal_statistics_altitude_municipality))
    col_name = prefix +'mean'
    mean_altitude = zonal_stats_municipality.loc[0, col_name]
    path_centroid_municipality = path_shapefiles / "centroid_municipality.shp"
    gdf_centroid = create_centroid(path_reproject_municipality_footprint, path_centroid_municipality)
    path_centroid_municipality_coordinates = path_shapefiles / "centroid_municipality_coordinates.shp"
    path_centroid_municipality_csv = path_csv_folder / "centroid_municipality_coordinates.csv"
    df_centroid =  create_csv_coordinates(path_centroid_municipality, path_centroid_municipality_coordinates, path_centroid_municipality_csv)
    latitude_center = df_centroid.loc[0, "latitude"]
    longitude_center = df_centroid.loc[0, "longitude"]
    return area, perimeter, mean_altitude, latitude_center, longitude_center, population

""" CALCULATION OF SVI AND DFI """
def calculate_SVI(path_buildings_buffer_zonal_stat_post_process, path_shapefiles, path_csv_folder, nb_tests = 5): 
    """Calculate the Sky View Index (SVI).

    First, the centroid of buildings are obtained with their coordinates. 
    It uses the centroid of buildings and horizon files from PVGIS API 
    Then, these coordinates are used in the PVGIS API to obtain horizon files. 
    The horizon files are then used to obtain the horizon profile at a specified place considering local surrounding topography and compared it with the horizon profile of a flat region (no surrounding topography).
    These horizon profiles are used to calculate the area of visible sky in both case. The ratio is obtained for all the considered buildings of the municipality. 
    The average ratio over all the considered building is the SVI. 
    If horizon profile is not available for one building, it moves to the next one, and the average is done only one the valid buildings. 
    It saves in a csv file the SVI for each building or the error if the horizon profile was not available for this building.

    Parameters
    ----------
    path_buildings_buffer_zonal_stat_post_process : pathlib.Path
        path of shapefile with building footprints for which the SVI is wanted (path_buildings_buffer_zonal_stat_post_process from _post_process_buffer_zonal_stat for example)
    path_shapefiles : pathlib.Path
        path of the folder with temporary shapefiles (define in main function)
    path_csv_folder : pathlib.Path
        path of the folder with temporary csv files (define in main function)
    nb_tests : int, optional
        number of time to test downloading the horizon file if there is a connection problem, by default 5

    Returns
    -------
    SVI : float
        Sky View Index (SVI) calculated for the municipality
    """
    path_centroid_buildings_buffer = path_shapefiles/ "centroid_buildings_buffer.shp"
    gdf_centroid_buildings = create_centroid(path_buildings_buffer_zonal_stat_post_process, path_centroid_buildings_buffer)
    path_centroid_buildings_buffer_coordinates = path_shapefiles/ "centroid_buildings_buffer_coordinates.shp"
    path_centroid_buildings_buffer_coordinates_csv = path_csv_folder/ "centroid_buildings_buffer_coordinates.csv"
    df_centroid_buildings = create_csv_coordinates(path_centroid_buildings_buffer, path_centroid_buildings_buffer_coordinates, path_centroid_buildings_buffer_coordinates_csv)
    df_centroid_buildings["error"] = ""
    number_error_building = 0

    list_remaining_buildings = []

    for test in range(0, nb_tests): 
        if test > 0  and len(list_remaining_buildings) >0 : 
            print("Horizon profile for some buildings were not available due to a ReadTimeout Error. Let's try another time! ")
            print(list_remaining_buildings)
        if (len(list_remaining_buildings) != 0) or test ==0  :
            list_copy_remaining_buildings = list_remaining_buildings.copy()  
            list_remaining_buildings = []    
            for i_building in tqdm(range(0, len(df_centroid_buildings))): 
                if (i_building in list_copy_remaining_buildings and test > 0) or test == 0 : 
                    lat = str(df_centroid_buildings.loc[i_building, 'latitude'])
                    long = str(df_centroid_buildings.loc[i_building, 'longitude'])
                    url_horizon = "https://re.jrc.ec.europa.eu/api/printhorizon?lat="+lat+"&lon="+long+"&outputformat=csv"
                    timeout = 200
                    setdefaulttimeout(timeout)
                    try : 
                        data = urlopen(Request(url_horizon)).read()
                        text = data.decode('utf-8')
                        s=StringIO(text)
                        df=read_csv(s, skiprows=3,delimiter=r"\t+",nrows=50, engine='python')
                        df['A_rad']=df['A']*pi/180
                        columns = ['A_x_polar','A_y_polar','horizon_x_polar', 'horizon_y_polar']
                        for col in columns :
                            df[col]=Series(dtype=float)
                        for i in range(0, len(df)):
                            df['A_x_polar'][i]=90*cos(df['A_rad'][i])
                            df['A_y_polar'][i]=90*sin(df['A_rad'][i])
                            df['horizon_x_polar'][i]=(90-df['H_hor'][i])*cos(df['A_rad'][i])
                            df['horizon_y_polar'][i]=(90-df['H_hor'][i])*sin(df['A_rad'][i])
                        points_outline = []
                        points_horizon =[]
                        for i in range(0, len(df)):
                            couple_outline = (df['A_x_polar'][i], df['A_y_polar'][i])
                            points_outline.append(couple_outline)
                            couple_horizon = (df['horizon_x_polar'][i], df['horizon_y_polar'][i])
                            points_horizon.append(couple_horizon)
                        poly_outline = Polygon(points_outline)
                        poly_horizon = Polygon(points_horizon)
                        area_outline = poly_outline.area
                        area_horizon = poly_horizon.area
                        mask = area_horizon/area_outline
                        df_centroid_buildings.loc[i_building, "mask"] = mask

                    except (exceptionsHTTPError, HTTPError)  as e: 
                        if ("Network is unreachable" in str(e)) or ("Connection reset by peer" in str(e)) or ("timed out" in str(e)) or ("Time-out" in str(e)) : 
                            if i_building not in list_remaining_buildings : 
                                list_remaining_buildings.append(i_building)
                            if test == (nb_tests-1) :
                                number_error_building = number_error_building + 1
                                df_centroid_buildings.loc[i_building, "error"] = str(e)
                        else : 
                            number_error_building = number_error_building + 1
                            df_centroid_buildings.loc[i_building, "error"] = str(e)
                            if "Location over the sea" in str(e):
                                print(f"Problem with building n°{i_building} : It is not possible to access the horizon profile, the centroid of the building is located over the sea.")
                            elif "Internal Server Error" in str(e): 
                                print(f"Problem with building n°{i_building} : It is not possible to access the horizon profile, there is an internal servor error (often due to centroid of the building located too close to the sea).")
                            else : 
                                print(f"Problem with building n°{i_building} : It is not possible to access the horizon profile.")
                                print(e)
                    except (TimeoutError, exceptionsReadTimeout, OSError) as e : 
                        if i_building not in list_remaining_buildings : 
                            list_remaining_buildings.append(i_building)
                        if "Network is unreachable" in str(e) : 
                            print(f"Problem with building n°{i_building} : It is not possible to access the horizon profile because the network is unreachable!")
                        elif "Connection reset by peer" in str(e) : 
                            print(f"Problem with building n°{i_building} : It is not possible to access the horizon profile because the connection was reset by peer!")
                        else :
                            print(f"Problem with building n°{i_building} : It is not possible to access the horizon profile due to ReadTimeout error!")
                        if test == (nb_tests -1) : 
                            number_error_building = number_error_building + 1
                            df_centroid_buildings.loc[i_building, "error"] = str(e)     

    if number_error_building > 0 : 
        print(f"It is not possible to access the horizon profile for {number_error_building} buildings")
    df_centroid_buildings.to_csv(str(path_centroid_buildings_buffer_coordinates_csv))
    df_centroid_buildings_no_error = df_centroid_buildings[df_centroid_buildings['error']==""]
    try : 
        SVI = mean(df_centroid_buildings_no_error['mask'])
        return SVI
    except KeyError as e : 
        if "mask" in str(e):
            print("It is possible that the distance of the buffer is too high, no buildings left, SVI can not be calculated.")

def calculate_DFI(grid_gpd, path_average_folder, fn_average_files, path_csv_folder): 
    """Calculate the Diffuse Fraction Index (DFI).

    It is calculated using the meteorological files (average) used for the simulation. 
    For each tile of the grid, the diffuse irradiance value per hour (for hours between 10:00 and 15:00 (10 a.m. and 3 p.m.)) is summed. The same is done for the global irradiance. 
    For each tile of the grid, the ratio is obtained. The average ratio over all grid tiles is the DFI. 
    The tile of the grid for which the meteorological file could not have been downloaded are not considered in the calculation of the DFI.

    Parameters
    ----------
    grid_gpd : GeoDataFrame
        geopandas grid file
    path_average_folder : pathlib.Path
        path of the folder where are saved the meteorological txt files (average txt files for example)
    fn_average_files : str
        prefix name given to the txt files (average txt files for example)
    path_csv_folder : pathlib.Path
        path of the folder with temporary csv files (define in main function)

    Returns
    -------
    DFI : float
        Diffuse Fraction Index (DFI) calculated for the municipality
    """
    
    path_list_tiles = path_csv_folder / "list_incorrect_tiles.csv"
    df_list_tiles = read_csv(str(path_list_tiles))
    list_incorrect_tiles = df_list_tiles['tile_number'].tolist()

    dhi_index_village=0 
    for i in range(0,len(grid_gpd)):
        if i+1 not in list_incorrect_tiles : 
            path_average_txt_files = path_average_folder / (fn_average_files+str(i+1)+".txt")
            tmy = read_csv(str(path_average_txt_files), sep = " ")
            somme_ghi_grid= 0
            somme_dhi_grid=0
            dhi_index_grid = 0
            for j in range(0,365):
                for k in range(0,6):
                    ligne = j *24 +k+9
                    ghi_grid = tmy.loc[ligne, 'Kdn']
                    dhi_grid = tmy.loc[ligne, 'Kdiff']
                    somme_ghi_grid += ghi_grid
                    somme_dhi_grid +=dhi_grid
            dhi_index_grid = (somme_dhi_grid/somme_ghi_grid)
            dhi_index_village += dhi_index_grid
    DFI = dhi_index_village/(len(grid_gpd)-len(list_incorrect_tiles))
    return DFI


def calculate_village_distribution_characteristics(path_csv_folder, path_raster_files, path_final_output_folder, path_shapefiles,grid_gpd, path_meteorological_folder, village_name , village_INSEE_code=None, village_departement=None,average = True, population_column = "POPULATION", nb_tests = 5):
    """Calculate and gather in a dataframe the village characteristics and distribution characteristics.

    The village characteristics include geographical data of the village (area, perimeter, coordinates) with administratives information (population, department). 
    ``departement`` and ``INSEE_code`` are set to None by default to include the case of a territory studied that do not correspond to a french municipality. 
    ``village_name`` could correspond to the name of territory studied if it is not a municipality.
    Then, results from SEBE simulation are used to obtain the distribution of the average annual irradiation and the associated fitted Johnson's SU distribution. 
    Statistical indicators to describe the distribution and the fitted Johnson's SU are obtained, as well as two indicators, SVI and DFI, to describe the far mask (topography) and the meteorologial situation of the municipality.
    The dataframe is then exported in a csv file.
    
    Parameters
    ----------
    path_csv_folder : pathlib.Path
        path of the folder with temporary csv files (define in main function)
    path_raster_files : pathlib.Path
        path of the folder with temporary raster files (define in main function)
    path_final_output_folder : pathlib.Path
        path of the folder with the final results (define in main function)
    path_shapefiles : pathlib.Path
        path of the folder with temporary shapefiles (define in main function)
    grid_gpd : GeoDataFrame
        geopandas grid file
    path_meteorological_folder : pathlib.Path
        path of the folder where are saved all the meteorological files
    village_name : str
        municipality name
    village_INSEE_code : str, optional
        INSEE code of the municipality, by default None
    village_departement : str, optional
        departement the municipality, by default None
    average : bool, optional
        boolean value to indicate if an average of the meteorological files was done or not, by default True
    population_column : str, optional
        name of the column with number of inhabitants of the studied municipality in the municipality footprint shapefile, by default "POPULATION"
    nb_tests : int, optional
        number of time to test downloading the horizon file if there is a connection problem, by default 5

    Returns
    -------
    df : Dataframe
        dataframe with all the characteristics of the village and of the solar distribution
    """
    
    path_reproject_municipality_footprint = path_shapefiles / "municipality_footprint_reproject.shp"
    path_DEM_resample = path_raster_files / "DEM_resample.tif"
    path_buildings_buffer_zonal_stat_post_process = path_final_output_folder / "buildings_zonal_stats_solar.shp"
    path_irradiation_csv = path_final_output_folder / "irradiation_csv.csv"
    bool_buffer = True

    if average : 
        path_average_folder = path_meteorological_folder/"average_files"
        fn_average_files = "average_txt_files_center_grid_"
    else : 
        path_average_folder = path_meteorological_folder/"txt_files"
        fn_average_files = "txt_files_center_grid_"

    area, perimeter, mean_altitude, latitude_center, longitude_center, population= calculate_village_characteristics(path_shapefiles, path_csv_folder, path_reproject_municipality_footprint, path_DEM_resample, population_column=population_column)
    SVI = calculate_SVI(path_buildings_buffer_zonal_stat_post_process, path_shapefiles, path_csv_folder, nb_tests=nb_tests)
    DFI = calculate_DFI(grid_gpd, path_average_folder, fn_average_files, path_csv_folder)

    column  = ["village_name", "village_INSEE_code", "village_departement"]
    # df_1 = DataFrame(columns=column) ## to remove
    df = DataFrame(columns=column) ## to remove
    column = ["population","surface_km2", "perimeter_km", "mean_altitude","latitude_center", "longitude_center","number_of_buildings", "latitude_center", "longitude_center", "average_raw_data", "standard_deviation_raw_data", "median_raw_data", "first_quartile_raw_data", "second_quartile_raw_data", "third_quartile_raw_data","interquartile_range_raw_data", "a_johnsonsu", "b_johnsonsu","c_johnsonsu","d_johnsonsu",  "average_johnsonsu", "standard_deviation_johnsonsu", "median_johnsonsu", "mode_johnsonsu", "xmin_one_third_mode_johnsonsu", "xmax_one_third_mode_johnsonsu", "spread_one_third_maximum_mode_johnsonsu","probability_mode_johnsonsu", "R2_johnsonsu", "R2_johnsonsu_init", "R2_johnsonsu_xmax", "method_johnsonsu", "DFI", "SVI" ]
    for col in column :
        df[col]=Series(dtype=float)
        # df_1[col]=Series(dtype=float)

    data = read_csv(str(path_irradiation_csv), usecols=range(1,2))
    data = data.squeeze()
    if bool_buffer== True : 
        data=data.loc[data!=0.0].dropna()
    data= data.sort_values()
    data.reset_index(drop=True, inplace=True)

    data, nb_bins, fitting_parameters,x, R2, R2_init, R2_xmax, method = calculate_histogram_and_johnsonsu_fit(path_irradiation_csv, bool_buffer =True)
    a,b,c,d = fitting_parameters
    mode_johnsonsu, proba_mode_johnsonsu = johnsonsu_mode(fitting_parameters)
    xmin_one_third_mode_johnsonsu,xmax_one_third_mode_johnsonsu,spread_one_third_maximum_mode_johnsonsu = johnsonsu_width(fitting_parameters,3)

    q1 = quantile(data, 0.25) 
    q2= quantile(data, 0.5)
    q3 = quantile(data, 0.75)

    values = {
    "village_name": village_name,
    "village_INSEE_code": village_INSEE_code,
    "village_departement": village_departement,
    "population" : population,
    "surface_km2": area,
    "perimeter_km" : perimeter,
    "mean_altitude": mean_altitude,
    "latitude_center" : latitude_center,
    "longitude_center" : longitude_center, 
    "number_of_buildings" : int(len(data)), 
    "average_raw_data" : mean(data), 
    "standard_deviation_raw_data" : std(data),
    "first_quartile_raw_data" : q1,
    "second_quartile_raw_data" : q2,
    "third_quartile_raw_data" :q3,
    "interquartile_range_raw_data" :q3 -q1,
    "median_raw_data" : median(data),
    "a_johnsonsu" : a, 
    "b_johnsonsu" :b, 
    "c_johnsonsu" : c, 
    "d_johnsonsu" : d, 
    "average_johnsonsu" : johnsonsu_mean(fitting_parameters), 
    "standard_deviation_johnsonsu" : johnsonsu_std((a,b,d)), 
    "median_johnsonsu" : johnsonsu_median(fitting_parameters), 
    "mode_johnsonsu": mode_johnsonsu,
    "xmin_one_third_mode_johnsonsu" : xmin_one_third_mode_johnsonsu,
    "xmax_one_third_mode_johnsonsu" : xmax_one_third_mode_johnsonsu,
    "spread_one_third_maximum_mode_johnsonsu" : spread_one_third_maximum_mode_johnsonsu,
    "probability_mode_johnsonsu" : proba_mode_johnsonsu,
    "R2_johnsonsu": R2, 
    "R2_johnsonsu_init" :R2_init, 
    "R2_johnsonsu_xmax" : R2_xmax, 
    "method_johnsonsu": method , 
    "DFI" : DFI,
    "SVI" : SVI
    }

    data_list = [values]
    df = concat([df, DataFrame(data_list)], ignore_index=True)

    # df_1= df_1.append(values, ignore_index=True) ## to remove
    # print(df_1.equals(df)) ## to remove
    path_distribution_characteristics = path_final_output_folder / "municipality_and_solar_distribution_characteristics.csv"
    df.to_csv(str(path_distribution_characteristics))
    return df



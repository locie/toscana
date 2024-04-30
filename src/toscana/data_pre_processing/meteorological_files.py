from ..utils import processing



from pandas import read_csv, DataFrame, concat
from geopandas import GeoDataFrame
from pvlib.iotools import get_pvgis_tmy

from numpy import sqrt, pi, exp, max, sum, array
from tqdm import tqdm
from shapely.geometry import Point
from urllib.error import HTTPError
from requests.exceptions import HTTPError as exceptionsHTTPError, ReadTimeout as exceptionsReadTimeout

from ..utils import create_centroid, create_csv_coordinates

""" OBTAIN METEOROLOGICAL FILES """
def _normal_distribution(x):
    """Define the normal distribution

    Parameters
    ----------
    x : float
        value to which is applied the normal distribution

    Returns
    -------
    normal : float
        value of the normal distribution
    """
    normal = 1 / sqrt(2 * pi) * exp(-0.5 * x**2)
    return normal

def _create_folder_meteorological_files(path_meteorological_folder, temp = True, average = True):    
    """Create subfolders for meteorological files and store the data.

    Parameters
    ----------
    path_meteorological_folder : pathlib.Path
        path of the folder where to save all the meteorological files
    temp : bool, optional
        boolean value to save or not temporary meteorological files, by default True
    average : bool, optional
        boolean value to do or not an average of the meteorological files, by default True

    Returns
    -------
    path_epw_folder : pathlib.Path
        path of the folder created in order to store the epw files, returned only if temp = True
    path_txt_folder
        path of the folder created in order to store the txt files, returned only if temp = True and average = True or if average = False
    path_average_folder
        path of the folder created in order to store the averaged txt files, returned only if average = True
    """
    fn_epw_folder ="epw_files"
    fn_txt_folder = "txt_files"
    fn_average_folder = "average_files"

    if temp: 
        path_epw_folder = path_meteorological_folder/ fn_epw_folder
        path_epw_folder.mkdir(exist_ok=True)
        
        path_txt_folder = path_meteorological_folder/ fn_txt_folder
        path_txt_folder.mkdir(exist_ok=True)

        if average: 
            path_average_folder = path_meteorological_folder/ fn_average_folder
            path_average_folder.mkdir(exist_ok=True)
            return path_epw_folder, path_txt_folder, path_average_folder
        else : 
            return path_epw_folder, path_txt_folder
    else : 
        if average : 
            path_average_folder = path_meteorological_folder/ fn_average_folder
            path_average_folder.mkdir(exist_ok=True)
            return path_average_folder
        else : 
            path_txt_folder = path_meteorological_folder/ fn_txt_folder
            path_txt_folder.mkdir(exist_ok=True)
            return path_txt_folder

def _create_modified_grid_centroid(gdf_centroid_grid, path_centroid_grid_modified, path_centroid_grid_modified_coordinates, path_centroid_grid_modified_csv, projection = "IGNF:ETRS89LAEA"): 
    """Create a modified grid centroids : centroids of the neighboring tiles are created and stored in a new dataframe. 
    
    The centroids of the 12 closest tiles of each tile of the actual grid are stored. 
    The coordinates (latitude and longitude) of the 12 centroids are obtained and will be used to obtain the meteorological files.
    The function will work for the reference system IGNF:ETRS89LAEA, but could work for other projection system where coordinates are in meters (Projected coordinate reference systems). 

    Parameters
    ----------
    gdf_centroid_grid : GeoDataframe
        geopandas file with the centroid of the actual grid (obtained in `create_centroid`)
    path_centroid_grid_modified : pathlib.Path
        path to save the shapefile with the modified grid centroids
    path_centroid_grid_modified_coordinates : pathlib.Path
        path where to save the shapefile with the modified grid centroids with their latitude and longitude
    path_centroid_grid_modified_csv : pathlib.Path
        path where to save the csv file with the coordinates of the modified grid centroids
    projection : str, optional
        name of the reference system of the grid, by default "IGNF:ETRS89LAEA"

    Returns
    -------
    df_centroid_modified : DataFrame
        dataframe with the coordinates of the modified grid centroids
    """
    fc = len(gdf_centroid_grid)
    ids = list(range(1, fc + 1))
    colonnes_vides = {'X': None, 'Y': None, 'Center': None,  'X1': None, 'Y1' : None, 'Point_1':None, 'X2':None, 'Y2':None, 'Point_2':None, 'X3':None, 'Y3':None,'Point_3':None, 'X4':None, 'Y4':None,'Point_4':None, 'X5':None, 'Y5':None, 'Point_5':None,'X6':None, 'Y6':None, 'Point_6':None, 'X7':None, 'Y7':None, 'Point_7':None, 'X8':None, 'Y8':None, 'Point_8':None, 'X9':None, 'Y9':None, 'Point_9':None,'X10':None, 'Y10':None,'Point_10':None, 'X11':None, 'Y11':None, 'Point_11':None,'X12':None, 'Y12':None, 'Point_12':None } 
    gdf_1 = GeoDataFrame({'ID': ids, **colonnes_vides})
    
    for i in tqdm(range(0,fc)): 
        point = gdf_centroid_grid['geometry'].iloc[i]
        gdf_1.loc[i, 'X'] = point.x
        gdf_1.loc[i, 'Y'] = point.y
        gdf_1.loc[i, 'Center'] = Point(point.x, point.y)

        gdf_1.loc[i, 'X1'] = point.x
        gdf_1.loc[i, 'Y1'] = point.y+1000
        gdf_1.loc[i, 'Point_1'] = Point(point.x, point.y+1000)

        gdf_1.loc[i, 'X2'] = point.x+1000
        gdf_1.loc[i, 'Y2'] = point.y
        gdf_1.loc[i, 'Point_2'] = Point(point.x+1000, point.y)

        gdf_1.loc[i, 'X3'] = point.x
        gdf_1.loc[i, 'Y3'] = point.y-1000
        gdf_1.loc[i, 'Point_3'] = Point(point.x, point.y-1000)

        gdf_1.loc[i, 'X4'] = point.x-1000
        gdf_1.loc[i, 'Y4'] = point.y
        gdf_1.loc[i, 'Point_4'] = Point(point.x-1000, point.y)

        gdf_1.loc[i, 'X5'] = point.x+1000
        gdf_1.loc[i, 'Y5'] = point.y+1000
        gdf_1.loc[i, 'Point_5'] = Point(point.x+1000, point.y+1000)

        gdf_1.loc[i, 'X6'] = point.x+1000
        gdf_1.loc[i, 'Y6'] = point.y-1000
        gdf_1.loc[i, 'Point_6'] = Point(point.x+1000, point.y-1000)

        gdf_1.loc[i, 'X7'] = point.x-1000
        gdf_1.loc[i, 'Y7'] = point.y-1000
        gdf_1.loc[i, 'Point_7'] = Point(point.x-1000, point.y-1000)

        gdf_1.loc[i, 'X8'] = point.x-1000
        gdf_1.loc[i, 'Y8'] = point.y+1000
        gdf_1.loc[i, 'Point_8'] = Point(point.x-1000, point.y+1000)

        gdf_1.loc[i, 'X9'] = point.x
        gdf_1.loc[i, 'Y9'] = point.y+2000
        gdf_1.loc[i, 'Point_9'] = Point(point.x, point.y+2000)

        gdf_1.loc[i, 'X10'] = point.x+2000
        gdf_1.loc[i, 'Y10'] = point.y
        gdf_1.loc[i, 'Point_10'] = Point(point.x+2000, point.y)

        gdf_1.loc[i, 'X11'] = point.x
        gdf_1.loc[i, 'Y11'] = point.y-2000
        gdf_1.loc[i, 'Point_11'] = Point(point.x, point.y-2000)

        gdf_1.loc[i, 'X12'] = point.x-2000
        gdf_1.loc[i, 'Y12'] = point.y
        gdf_1.loc[i, 'Point_12'] = Point(point.x-2000, point.y)
    
    gdf_1= gdf_1.set_geometry('Center', crs =projection)
    liste_Center = gdf_1['Center'].tolist()
    liste_other_point = []
    gdf_2 = gdf_1[['ID', 'Center']]
    gdf_3 = GeoDataFrame(gdf_2.copy(), geometry='Center', crs= projection)
    gdf_3.rename(columns={'Center': 'geometry'}, inplace=True)
    gdf_3= gdf_3.set_geometry('geometry', crs =projection)

    long = len(gdf_3)
    to_append = []
    for i in range(1, 13):
        name_point = 'Point_' + str(i)
        for j in range(0, fc):
            if (gdf_1.loc[j, name_point] not in liste_Center) and (gdf_1.loc[j, name_point] not in liste_other_point):
                liste_other_point.append(gdf_1.loc[j,name_point])
                new_row = {'ID': long+1, 'geometry': gdf_1.loc[j, name_point]}
                to_append.append(new_row)
                long = long +1
    gdf_to_append = GeoDataFrame(to_append, geometry='geometry', crs=projection)
    gdf_3 = concat([gdf_3, gdf_to_append], ignore_index=True)

    for i in range(0, fc) : 
        gdf_3.loc[i, "ID_1"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_1']].values
        gdf_3.loc[i, "ID_2"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_2']].values
        gdf_3.loc[i, "ID_3"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_3']].values
        gdf_3.loc[i, "ID_4"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_4']].values
        gdf_3.loc[i, "ID_5"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_5']].values
        gdf_3.loc[i, "ID_6"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_6']].values
        gdf_3.loc[i, "ID_7"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_7']].values
        gdf_3.loc[i, "ID_8"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_8']].values
        gdf_3.loc[i, "ID_9"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_9']].values
        gdf_3.loc[i, "ID_10"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_10']].values
        gdf_3.loc[i, "ID_11"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_11']].values
        gdf_3.loc[i, "ID_12"] = gdf_3['ID'].loc[gdf_3['geometry'] == gdf_1.loc[i, 'Point_12']].values

    gdf_3= gdf_3.set_geometry('geometry', crs =projection)
    gdf_3.to_file(str(path_centroid_grid_modified), driver='ESRI Shapefile', crs=projection)
    df_centroid_modified = create_csv_coordinates(path_centroid_grid_modified, path_centroid_grid_modified_coordinates, path_centroid_grid_modified_csv )
    return df_centroid_modified

def _obtain_epw_meteorological_files(df_centroid_modified, gdf_centroid_grid ,  path_epw_folder, path_meteorological_folder, nb_tests = 5): 
    """Download the meteorological files from PVGIS for all the grid tiles centers.

    Exceptions are included to consider if meteorological files could not be downloaded. 
    It could happen if the grid tile centers are located over the sea or too close to the sea. 

    Parameters
    ----------
    df_centroid_modified : Dataframe
        dataframe with the modified grid centroids (from df_centroid_modified obtained in `_create_modified_grid_centroid`)
    gdf_centroid_grid : GeoDataframe
        geopandas file with the centroid of the actual grid (obtained in `create_centroid`)
    path_epw_folder : pathlib.Path
        path of the folder where to save the epw files
    path_meteorological_folder : pathlib.Path
        path of the folder where to save all the meteorological files
    nb_tests : int, optional
        number of time to test downloading the meteorological file if there is a connection problem, by default 5

    Returns
    -------
    fn_epw_files : str
        prefix name given to the download epw files 
    list_tiles_incorrect_meteorological : list
        list with the number of the tiles for which the meteorological files could not have been downloaded 
    df_centroid_modified : DataFrame
        dataframe with the coordinates of the modified grid centroids (and if there are downloading errors)
    """
    fc_original_grid = len(gdf_centroid_grid)
    list_tiles_incorrect_meteorological = []
    list_error =[]
    fn_epw_files= "epw_files_center_grid_"
    fc = len(df_centroid_modified)
    df_centroid_modified['error_meteorological_files'] = False

    list_remaining_tiles = []

    for test in range(0, nb_tests): 
        if test > 0 and len(list_remaining_tiles)>0: 
            print("Some tiles were not downloaded due to a ReadTimeout Error. Let's try another time! ")
        if len(list_remaining_tiles) != 0 or test == 0:
            list_copy_remaining_tiles = list_remaining_tiles.copy()
            list_remaining_tiles =[]
            for i in tqdm(range(0,fc)):
                if (i+1 in list_copy_remaining_tiles and test > 0) or test == 0 : 
                    latitude=df_centroid_modified['latitude'][i]
                    longitude=df_centroid_modified['longitude'][i]
                    try : 
                        tmy,a,b,c= get_pvgis_tmy(latitude=latitude, longitude=longitude, outputformat='epw', url='https://re.jrc.ec.europa.eu/api/v5_2/', timeout=200) 
                        path_epw_files = path_epw_folder / (fn_epw_files+str(i+1)+".csv")
                        tmy.to_csv(str(path_epw_files))
                    except (exceptionsHTTPError, HTTPError)  as e:
                        if ("Network is unreachable" in str(e)) or ("Connection reset by peer" in str(e)) or ("timed out" in str(e)) or ("Time-out" in str(e)) : 
                            list_remaining_tiles.append(i+1)
                            if test == (nb_tests-1) :
                                if (i+1) not in list_tiles_incorrect_meteorological : 
                                    list_error.append(e)
                                    list_tiles_incorrect_meteorological.append(i+1)           
                                    df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
                        else :
                            list_error.append(e)
                            list_tiles_incorrect_meteorological.append(i+1)
                            df_centroid_modified.loc[i,'error_meteorological_files'] = True
                            if i < fc_original_grid:
                                if "Location over the sea" in str(e):
                                    print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file, the centroid of the grid tile is located over the sea.")
                                elif "Internal Server Error" in str(e): 
                                    print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file, there is an internal servor error (often due to centroid of the grid tile located too close to the sea).")
                                else : 
                                    print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file.")
                                    print(e)
                            else : 
                                if "Location over the sea" in str(e):
                                    print(f"Problem with neighbouring grid tile n°{i+1} : It is not possible to download the meteorological file, the centroid of the grid tile is located over the sea.")
                                elif "Internal Server Error" in str(e): 
                                    print(f"Problem with neighbouring grid tile n°{i+1} : It is not possible to download the meteorological file, there is an internal servor error (often due to centroid of the grid tile located too close to the sea).")
                                else : 
                                    print(f"Problem with neighbouring grid tile n°{i+1} : It is not possible to download the meteorological file.")
                                    print(e)
                    except (TimeoutError, exceptionsReadTimeout, OSError, ConnectionResetError) as e : 
                        if i+1 not in list_remaining_tiles : 
                            list_remaining_tiles.append(i+1)
                        if i < fc_original_grid:
                            if "Network is unreachable" in str(e) : 
                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the network is unreachable!")
                            elif "Connection reset by peer" in str(e) : 
                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the connection was reset by peer!")
                            else :
                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file due to ReadTimeout error!")
                        else : 
                            if "Network is unreachable" in str(e) : 
                                print(f"Problem with neighbouring grid tile n°{i+1} : It is not possible to download the meteorological file because the network is unreachable!")
                            elif "Connection reset by peer" in str(e) : 
                                print(f"Problem with neighbouring grid tile n°{i+1} : It is not possible to download the meteorological file because the connection was reset by peer!")
                            else :
                                print(f"Problem with neighbouring grid tile n°{i+1} : It is not possible to download the meteorological file due to ReadTimeout error!")
                        if test == (nb_tests-1) :
                            if (i+1) not in list_tiles_incorrect_meteorological : 
                                list_error.append(e)
                                list_tiles_incorrect_meteorological.append(i+1)           
                                df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
                    
    df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
    path_list_tiles = path_meteorological_folder / "list_incorrect_tiles_meteorological.csv"
    df_list_tiles.to_csv(str(path_list_tiles), index=False)
    return fn_epw_files, list_tiles_incorrect_meteorological, df_centroid_modified

def _obtain_txt_meteorological_files(df_centroid_modified, path_epw_folder, path_txt_folder, fn_epw_files, list_tiles_incorrect_meteorological):    
    """Transform the epw files in txt files  : it is the format needed to run SEBE calculation. The transformation is not done for the tiles for which the meteorological files could not have been downloaded. 

    Parameters
    ----------
    df_centroid_modified : Dataframe
        dataframe with the modified grid centroids, (df_centroid_modified obtained in `_create_modified_grid_centroid`)
    path_epw_folder : pathlib.Path
        path of the folder where are saved the epw files
    path_txt_folder : pathlib.Path
        path of the folder where to save the txt files
    fn_epw_files : str
        prefix name given to the download epw files 
    list_tiles_incorrect_meteorological : list
        list with the number of the tiles for which the meteorological files could not have been downloaded

    Returns
    -------
    fn_txt_files : str
        prefix name given to the txt files 
    """
    fn_txt_files = "txt_files_center_grid_"
    fc = len(df_centroid_modified)
    columns = ['%iy','id', 'it', 'imin', 'Q*', 'QH', 'QE', 'Qs', 'Qf', 'Wind', 'RH','Td', 'press', 'rain', 'Kdn', 'snow', 'ldown', 'fcld', 'wuh', 'xsmd','lai_hr', 'Kdiff', 'Kdir', 'Wd']
    list_year = []
    for k in range(0, 8760): 
        list_year.append(2015)
    list_day=[]
    for day in range(0, 365): 
        for hour in range(0,24): 
            list_day.append(day+1)
    files_txt_temp= DataFrame({'%iy':list_year})
    for j in columns:
        files_txt_temp[j]=-999.00
    files_txt_temp=files_txt_temp.astype({'%iy':int, 'id':int, 'it':int, 'imin':int})

    for l in tqdm(range(0, fc)): 
        if l+1 not in list_tiles_incorrect_meteorological :
            path_epw_files = path_epw_folder / (fn_epw_files+str(l+1)+".csv")
            epw_files_temp = read_csv(str(path_epw_files))
            for i in range(0, len(files_txt_temp)):
                files_txt_temp.loc[i,'%iy']=2015
                files_txt_temp.loc[i,'id']=list_day[i]
            files_txt_temp['it']=epw_files_temp['hour']
            files_txt_temp['imin']=epw_files_temp['minute']
            files_txt_temp['RH']=epw_files_temp['relative_humidity']
            files_txt_temp['Td']=epw_files_temp['temp_air']
            files_txt_temp['Kdn']=epw_files_temp['ghi']
            files_txt_temp['Kdiff']=epw_files_temp['dhi']
            files_txt_temp['Kdir']=epw_files_temp['dni']
            path_txt_files = path_txt_folder / (fn_txt_files+str(l+1)+".txt")
            files_txt_temp.to_csv(str(path_txt_files), index=False, sep=' ')
    return fn_txt_files

def _obtain_average_meteorological_files(gdf_centroid, df_centroid_modified, path_txt_folder, path_average_folder, fn_txt_files, list_tiles_incorrect_meteorological, option_no_average_if_one_problem = False, option_no_average_for_the_error_tile = False):    
    """Obtain average meteorological files : an weighted average of the meteorological files from the studied tile and the 12 closest tiles is made. 
    
    The weight are determined based on a normalized distance and using the normal distribution. 
    There are several option if some meteorological could not have been downloaded : 
    - don't average any meteorological file if there is at least one file that was not downloaded (among the tiles of the grid and the neighbouring tiles) : set ``option_no_average_if_one_problem`` to True to select this option
    - don't average a meteorological file if there is at least one file that was not downloaded among the studied tile or its neighbours : set ``option_no_average_for_the_error_tile`` to True 
    - make an average of the valid meteorological files for each valid tile (the weights are normalized only by considering the valid neighbouring tiles) : it is the default option. 
    The list of the tiles for which the meteorological files could not have been downloaded are saved in a csv files with the corresponding error. 

    Parameters
    ----------
    gdf_centroid : GeoDataFrame
        geopandas file with the centroid of the actual grid (obtained in `create_centroid`)
    df_centroid_modified : DataFrame
        dataframe with the modified grid centroids, (df_centroid_modified obtained in `_create_modified_grid_centroid`)
    path_txt_folder : pathlib.Path
        path of the folder where are saved the txt files
    path_average_folder : pathlib.Path
        path of the folder where to save the average txt files
    fn_txt_files : str
        prefix name given to the txt files
    list_tiles_incorrect_meteorological : list
        list with the number of the tiles for which the meteorological files could not have been downloaded
    option_no_average_if_one_problem : bool, optional
        boolean value to don't average any meteorological file if there is one problem for one tile or one of the neighbouring tile among all the tiles, by default False
    option_no_average_for_the_error_tile : bool, optional
        boolean value to don't average the meteorological file if there is one problem for the studied tile or one of the neighbouring tile of the studied tile, by default False
    """    

    if option_no_average_for_the_error_tile == True and option_no_average_if_one_problem== True : 
        print("The two options can not be set to True at the same time, only the option option_no_average_if_one_problem will be retained!")

    fc = len(gdf_centroid)
    fn_average_files = "average_txt_files_center_grid_"
    distances = array([0.0, 1.0, 1.0, 1.0, 1.0, sqrt(2), sqrt(2), sqrt(2), sqrt(2), 2.0, 2.0, 2.0, 2.0])
    normalized_distances = distances / max(distances)
    weights_no_normalized = _normal_distribution(normalized_distances)
    weights = weights_no_normalized/ sum(weights_no_normalized)

    global_indic_error_neighbour = False
    df_centroid_modified["one_error_neighbour"]  = False
    

    if len(list_tiles_incorrect_meteorological)> 0 : # verify if meteorological files could not be downloaded for at list one tile of the modified grid
        global_indic_error_neighbour = True

    for l in tqdm(range(0, fc)): 
        if l+1 not in list_tiles_incorrect_meteorological : 
            path_txt_files = path_txt_folder / (fn_txt_files+str(l+1)+".txt")
            files_txt_temp= read_csv(str(path_txt_files), sep =' ')
            indic_error_neighbour = False
            for h in range(1,13): 
                ID = df_centroid_modified.loc[l, 'ID_'+str(h)]
                if df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['error_meteorological_files'].values[0] == True :  # verify if meteorological files could have been downloaded for neighbouring tiles 
                    indic_error_neighbour = True  # set to True if for at least one neighbouring tile the meteorological file could not be downloaded
                    df_centroid_modified.loc[l, "one_error_neighbour"] = True # set to True if for at least one neighbouring tile the meteorological file could not be downloaded
                    global_indic_error_neighbour = True 
            if indic_error_neighbour == False and option_no_average_if_one_problem == False : # if no problem found for the neighbouring tiles of the studied AND option set to False for option_no_average_if_one_problem (False = make an average if no problem found for the neighbouring tiles of the studied tile )
                files_txt_temp['RH'] = files_txt_temp['RH']*weights[0]
                files_txt_temp['Td'] = files_txt_temp['Td']*weights[0]
                files_txt_temp['Kdn'] = files_txt_temp['Kdn']*weights[0]
                files_txt_temp['Kdiff'] = files_txt_temp['Kdiff']*weights[0]
                files_txt_temp['Kdir'] = files_txt_temp['Kdir']*weights[0]
                for h in range(1,13): 
                        ID = df_centroid_modified.loc[l, 'ID_'+str(h)]
                        path_other_txt_files_temp = path_txt_folder / (fn_txt_files+str(int(ID))+".txt")
                        other_txt_files_temp = read_csv(str(path_other_txt_files_temp), sep =' ')
                        files_txt_temp['RH'] = files_txt_temp['RH'] +  other_txt_files_temp['RH']*weights[h]
                        files_txt_temp['Td'] = files_txt_temp['Td'] +  other_txt_files_temp['Td']*weights[h]
                        files_txt_temp['Kdn'] = files_txt_temp['Kdn'] +  other_txt_files_temp['Kdn']*weights[h]
                        files_txt_temp['Kdiff'] = files_txt_temp['Kdiff'] +  other_txt_files_temp['Kdiff']*weights[h]
                        files_txt_temp['Kdir'] = files_txt_temp['Kdir'] +  other_txt_files_temp['Kdir']*weights[h]
                path_average_txt_files = path_average_folder / (fn_average_files+str(l+1)+".txt")
                files_txt_temp.to_csv(str(path_average_txt_files), index=False, sep=' ')

    if global_indic_error_neighbour == True and option_no_average_if_one_problem == True : #if one error found and option_no_average_if_one_problem set to True ( True = don't average if there is at least one problem for one of the studied tile or for at least one neighbour of the studied tiles)
        print(f"No average for any tile due to at least one tile with one problem")
        for l in tqdm(range(0, fc)):
            if l+1 not in list_tiles_incorrect_meteorological : 
                path_txt_files = path_txt_folder / (fn_txt_files+str(l+1)+".txt")
                files_txt_temp= read_csv(str(path_txt_files), sep =' ')
                path_average_txt_files = path_average_folder / (fn_average_files+str(l+1)+".txt")
                files_txt_temp.to_csv(str(path_average_txt_files), index=False, sep=' ')

    if global_indic_error_neighbour == True and option_no_average_if_one_problem == False : # if one error found and option_no_average_if_one_problem set to False (False = make an average if no problem found for the neighbouring tiles of the studied tile )
        if option_no_average_for_the_error_tile == True : # for the tile with at least one problem for one of the neighbouring tile, don't make an average for this tile
            for l in tqdm(range(0, fc) ): 
                if l+1 not in list_tiles_incorrect_meteorological :  
                    path_txt_files = path_txt_folder / (fn_txt_files+str(l+1)+".txt")
                    files_txt_temp= read_csv(str(path_txt_files), sep =' ')
                    if df_centroid_modified.loc[l, "one_error_neighbour"] == True : 
                        path_average_txt_files = path_average_folder / (fn_average_files+str(l+1)+".txt")
                        files_txt_temp.to_csv(str(path_average_txt_files), index=False, sep=' ')
                        print(f"No average for tile number {l+1} due to at least one neighbouring tile with one problem")
        else : # for the tile with at least one problem for one of the neighbouring tile, make an average only with the valid neighbouring tiles
            for l in tqdm(range(0,fc)):
                if l+1 not in list_tiles_incorrect_meteorological : 
                    path_txt_files = path_txt_folder / (fn_txt_files+str(l+1)+".txt")
                    files_txt_temp= read_csv(str(path_txt_files), sep =' ')
                    if df_centroid_modified.loc[l, "one_error_neighbour"] == True : 
                        print(f"Modified average for tile number°{l+1} due to at least one neighbouring tile with one problem")
                        sum_weights = 0 
                        df_centroid_modified.loc[l, "modified_weights"] = weights_no_normalized[0]
                        sum_weights = sum_weights + weights_no_normalized[0]
                        for h in range(1,13): # calculate the weights for each neighbouring tiles
                            ID = df_centroid_modified.loc[l, 'ID_'+str(h)]
                            if df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['error_meteorological_files'].values[0] != True :
                                df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['modified_weights'].values[0] = weights_no_normalized[h]
                                sum_weights = sum_weights + weights_no_normalized[h]
                        df_centroid_modified.loc[l, "modified_weights"] = weights_no_normalized[0]/sum_weights

                        for h in range(1,13): # normalize the weights for each neighbouring tiles
                            ID = df_centroid_modified.loc[l, 'ID_'+str(h)]
                            if df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['error_meteorological_files'].values[0]!= True :
                                index = df_centroid_modified[df_centroid_modified['ID'] == int(ID)].index[0]
                                df_centroid_modified.loc[index ,'modified_weights']= weights_no_normalized[h] / sum_weights
                        files_txt_temp['RH'] = files_txt_temp['RH']*df_centroid_modified.loc[l, "modified_weights"] 
                        files_txt_temp['Td'] = files_txt_temp['Td']*df_centroid_modified.loc[l, "modified_weights"] 
                        files_txt_temp['Kdn'] = files_txt_temp['Kdn']*df_centroid_modified.loc[l, "modified_weights"] 
                        files_txt_temp['Kdiff'] = files_txt_temp['Kdiff']*df_centroid_modified.loc[l, "modified_weights"] 
                        files_txt_temp['Kdir'] = files_txt_temp['Kdir']*df_centroid_modified.loc[l, "modified_weights"] 
                        for h in range(1,13): 
                            ID = df_centroid_modified.loc[l, 'ID_'+str(h)]
                            if df_centroid_modified[df_centroid_modified['ID'] == int(ID)]["error_meteorological_files"].values[0] != True :
                                path_other_txt_files_temp = path_txt_folder / (fn_txt_files+str(int(ID))+".txt")
                                other_txt_files_temp = read_csv(str(path_other_txt_files_temp), sep =' ')
                                files_txt_temp['RH'] = files_txt_temp['RH'] +  other_txt_files_temp['RH']* df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['modified_weights'].values[0]
                                files_txt_temp['Td'] = files_txt_temp['Td'] +  other_txt_files_temp['Td']* df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['modified_weights'].values[0]
                                files_txt_temp['Kdn'] = files_txt_temp['Kdn'] +  other_txt_files_temp['Kdn']* df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['modified_weights'].values[0]
                                files_txt_temp['Kdiff'] = files_txt_temp['Kdiff'] +  other_txt_files_temp['Kdiff']* df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['modified_weights'].values[0]
                                files_txt_temp['Kdir'] = files_txt_temp['Kdir'] +  other_txt_files_temp['Kdir']* df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['modified_weights'].values[0]
                        path_average_txt_files = path_average_folder / (fn_average_files+str(l+1)+".txt")
                        files_txt_temp.to_csv(str(path_average_txt_files), index=False, sep=' ')


def obtain_meteorological_files(path_meteorological_folder, path_shapefiles, save_temp_file = True, average = True,  option_no_average_if_one_problem = False, option_no_average_for_the_error_tile = False, nb_tests = 5 ):    
    """Obtain the meteorological files needed to run the SEBE simulations.
    
    Folders to save the files are created. 
    Centroids of the grid tiles are created. 
    They are modified to include the 12 closest centroids. 
    The metorological files are obtained in epw format, and then transform in txt format, needed for the simulations. These temporary files are saved only if ``save_temp_file`` is set to True.
    An average of the meteorological file from the tile and the 12 closest tiles is done if ``average`` is set to True (default value) (due to the low resolution of the meteorological data). 
    If there is some meteorological files that could not be downloaded, the average is done only with the valid neighbouring tiles (default).
    ``option_no_average_if_one_problem`` and ``option_no_average_for_the_error_tile`` will be used only if ``average`` is set to True. 

    Parameters
    ----------
    path_meteorological_folder : pathlib.Path
        path of the folder where to save all the meteorological files
    path_shapefiles : pathlib.Path
        path of the folder with temporary shapefiles (define in main function)
    save_temp_file : bool, optional
        boolean value to save or not temporary meteorological files, by default True
    average : bool, optional
        boolean value to do or not an average of the meteorological files, by default True
    option_no_average_if_one_problem : bool, optional
        boolean value to don't average any meteorological file if there is one problem for one tile or one of the neighbouring tile among all the tiles, by default False
    option_no_average_for_the_error_tile : bool, optional
        boolean value to don't average the meteorological file if there is one problem for the studied tile or one of the neighbouring tile of the studied tile, by default False
    nb_tests : int, optional
        number of time to test downloading the meteorological file if there is a connection problem, by default 5
    """
    path_input_grid = path_shapefiles / "municipality_grid.shp"
    
    if average : 
        if save_temp_file: 
            path_epw_folder, path_txt_folder, path_average_folder = _create_folder_meteorological_files(path_meteorological_folder, average= True, temp=True)
        else : 
            path_average_folder = _create_folder_meteorological_files(path_meteorological_folder, average= True, temp=False)

        path_centroid_grid = path_meteorological_folder / "centroid_grid.shp"
        path_centroid_grid_modified = path_meteorological_folder / "centroid_grid_modified.shp"
        path_centroid_grid_modified_coordinates =  path_meteorological_folder / "centroid_grid_modified_coordinates.shp" 
        path_centroid_grid_modified_csv=  path_meteorological_folder / "centroid_grid_modified_csv.csv" 

        gdf_centroid_grid = create_centroid(path_input_grid, path_centroid_grid)

        df_centroid_modified = _create_modified_grid_centroid(gdf_centroid_grid,  path_centroid_grid_modified, path_centroid_grid_modified_coordinates, path_centroid_grid_modified_csv )
        
        if save_temp_file: 
            fn_epw_files, list_tiles_incorrect_meteorological, df_centroid_modified = _obtain_epw_meteorological_files(df_centroid_modified,gdf_centroid_grid, path_epw_folder, path_meteorological_folder, nb_tests= nb_tests)
            fn_txt_files = _obtain_txt_meteorological_files(df_centroid_modified, path_epw_folder, path_txt_folder, fn_epw_files, list_tiles_incorrect_meteorological)
            _obtain_average_meteorological_files(gdf_centroid_grid, df_centroid_modified, path_txt_folder, path_average_folder, fn_txt_files, list_tiles_incorrect_meteorological, option_no_average_if_one_problem = option_no_average_if_one_problem, option_no_average_for_the_error_tile = option_no_average_for_the_error_tile )
        else : 
            _obtain_average_meteorogical_files_no_temp(df_centroid_modified,gdf_centroid_grid,path_average_folder,path_meteorological_folder, option_no_average_if_one_problem = option_no_average_if_one_problem, option_no_average_for_the_error_tile = option_no_average_for_the_error_tile, nb_tests= nb_tests  )
    else :
        path_centroid_grid = path_meteorological_folder / "centroid_grid.shp"
        path_centroid_grid_coordinates =  path_meteorological_folder / "centroid_grid_coordinates.shp" 
        path_centroid_grid_csv=  path_meteorological_folder / "centroid_grid_csv.csv" 
        gdf_centroid_grid = create_centroid(path_input_grid, path_centroid_grid)
        df_centroid_grid= create_csv_coordinates(path_centroid_grid, path_centroid_grid_coordinates, path_centroid_grid_csv )
        if save_temp_file : 
            path_epw_folder, path_txt_folder = _create_folder_meteorological_files(path_meteorological_folder, average= False, temp=True)
            _obtain_meteorological_files_no_average(df_centroid_grid, path_txt_folder, path_meteorological_folder, path_epw_folder=path_epw_folder, temp = True, nb_tests= nb_tests)
        else : 
            path_txt_folder = _create_folder_meteorological_files(path_meteorological_folder, average= False, temp=False)
            _obtain_meteorological_files_no_average(df_centroid_grid, path_txt_folder, path_meteorological_folder,  temp = False, nb_tests= nb_tests)

def _obtain_average_meteorogical_files_no_temp(df_centroid_modified, gdf_centroid, path_average_folder, path_meteorological_folder, option_no_average_if_one_problem = False, option_no_average_for_the_error_tile = False, nb_tests = 5):
    """Download the meteorological files from PVGIS for all the grid tiles centers and average them : an weighted average of the meteorological files from the studied tile and the 12 closest tiles is made. 
    
    The weight are determined based on a normalized distance and using the normal distribution. The temporary epw meteorological files are not saved. 
    Exceptions are included to consider if meteorological files could not be downloaded. 
    It could happen if the grid tile centers are located over the sea or too close to the sea. 
    There are several option if some meteorological could not have been downloaded : 
    - don't average any meteorological file if there is at least one file that was not downloaded (among the tiles of the grid and the neighbouring tiles) : set ``option_no_average_if_one_problem`` to True to select this option
    - don't average a meteorological file if there is at least one file that was not downloaded among the studied tile or its neighbours : set ``option_no_average_for_the_error_tile`` to True 
    - make an average of the valid meteorological files for each valid tile (the weights are normalized only by considering the valid neighbouring tiles) : it is the default option. 
    The list of the tiles for which the meteorological files could not have been downloaded are saved in a csv files with the corresponding error. 

    Parameters
    ----------
    df_centroid_modified : Dataframe
        dataframe with the modified grid centroids (from df_centroid_modified obtained in `_create_modified_grid_centroid`)
    gdf_centroid : GeoDataFrame
        geopandas file with the centroid of the actual grid (obtained in `create_centroid`)
    path_average_folder : pathlib.Path
        path of the folder where to save the average txt files
    path_meteorological_folder : pathlib.Path
        path of the folder where to save all the meteorological files
    option_no_average_if_one_problem : bool, optional
        boolean value to don't average any meteorological file if there is one problem for one tile or one of the neighbouring tile among all the tiles, by default False
    option_no_average_for_the_error_tile : bool, optional
        boolean value to don't average the meteorological file if there is one problem for the studied tile or one of the neighbouring tile of the studied tile, by default False
    nb_tests : int, optional
        number of time to test downloading the meteorological file if there is a connection problem, by default 5
    """

    columns = ['%iy','id', 'it', 'imin', 'Q*', 'QH', 'QE', 'Qs', 'Qf', 'Wind', 'RH','Td', 'press', 'rain', 'Kdn', 'snow', 'ldown', 'fcld', 'wuh', 'xsmd','lai_hr', 'Kdiff', 'Kdir', 'Wd']
    list_year = []
    for k in range(0, 8760): 
        list_year.append(2015)
    list_day=[]
    for day in range(0, 365): 
        for hour in range(0,24): 
            list_day.append(day+1)
    files_txt_temp= DataFrame({'%iy':list_year})
    for j in columns:
        files_txt_temp[j]=-999.00
    files_txt_temp=files_txt_temp.astype({'%iy':int, 'id':int, 'it':int, 'imin':int})

    distances = array([0.0, 1.0, 1.0, 1.0, 1.0, sqrt(2), sqrt(2), sqrt(2), sqrt(2), 2.0, 2.0, 2.0, 2.0])
    normalized_distances= distances / max(distances)
    weights_no_normalized = _normal_distribution(normalized_distances)
    weights= weights_no_normalized/ sum(weights_no_normalized)

    fc = len(gdf_centroid)
    list_tiles_incorrect_meteorological = []
    list_error =[]
    

    global_indic_error_neighbour = False
    indic_continue = True

    list_remaining_tiles = []

    for test in range(0, nb_tests): 
        if test > 0  and len(list_remaining_tiles) >0 : 
            print("Some tiles were not downloaded due to a ReadTimeout Error. Let's try another time! ")
        if (len(list_remaining_tiles) != 0) or test ==0  :
            list_copy_remaining_tiles = list_remaining_tiles.copy()  
            list_remaining_tiles = []    
            for i in tqdm(range(0,fc)):
                if (i+1 in list_copy_remaining_tiles and test > 0) or test == 0 : 
                    if i+1 not in list_tiles_incorrect_meteorological:
                        if option_no_average_if_one_problem == True and global_indic_error_neighbour == True :
                            indic_continue = False 
                        if indic_continue == True : 
                            latitude=df_centroid_modified['latitude'][i]
                            longitude=df_centroid_modified['longitude'][i]
                            try : 
                                tmy,a,b,c= get_pvgis_tmy(latitude=latitude, longitude=longitude, outputformat='epw', url='https://re.jrc.ec.europa.eu/api/v5_2/', timeout=200) 
                                tmy = tmy.reset_index(drop=True)
                                tmy = tmy.reset_index()
                                list_weights_no_normalized = []
                                list_tile = []
                                tmy['relative_humidity'] = tmy['relative_humidity']*weights[0]
                                tmy['temp_air'] = tmy['temp_air']*weights[0]
                                tmy['ghi'] = tmy['ghi']*weights[0]
                                tmy['dhi'] = tmy['dhi']*weights[0]
                                tmy['dni'] = tmy['dni']*weights[0]
                                list_weights_no_normalized.append(weights_no_normalized[0])
                                indic_error_neighbour = False
                                indic_continue_tile = True
                                for h in range(1,13):
                                    if option_no_average_for_the_error_tile == True and indic_error_neighbour == True : 
                                        indic_continue_tile = False 
                                    if indic_continue_tile == True : 
                                        ID = df_centroid_modified.loc[i, 'ID_'+str(h)]
                                        latitude = df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['latitude'].values[0]
                                        longitude = df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['longitude'].values[0]
                                        if ID not in list_tiles_incorrect_meteorological : 
                                            try : #make an average only with the valid neighbouring tiles
                                                tmy_t, a_t, b_t, c_t = get_pvgis_tmy(latitude=latitude, longitude=longitude, outputformat='epw', url='https://re.jrc.ec.europa.eu/api/v5_2/', timeout=200)
                                                tmy_t = tmy_t.reset_index(drop=True)
                                                tmy_t = tmy_t.reset_index()
                                                tmy['ghi']= tmy['ghi'] + tmy_t['ghi']*weights[h] 
                                                tmy['dhi']= tmy['dhi'] + tmy_t['dhi']*weights[h]
                                                tmy['dni']= tmy['dni'] + tmy_t['dni']*weights[h]
                                                tmy['relative_humidity']= tmy['relative_humidity'] + tmy_t['relative_humidity']*weights[h]
                                                tmy['temp_air']= tmy['temp_air'] + tmy_t['temp_air']*weights[h]
                                                list_weights_no_normalized.append(weights_no_normalized[h])
                                                list_tile.append(ID)
                                            except (exceptionsHTTPError, HTTPError)  as e: 
                                                if ("Network is unreachable" in str(e)) or ("Connection reset by peer" in str(e)) or ("timed out" in str(e)) or ("Time-out" in str(e)): 
                                                    list_remaining_tiles.append(i+1)
                                                    if test == (nb_tests-1) :
                                                        global_indic_error_neighbour = True
                                                        indic_error_neighbour = True
                                                else :  
                                                    global_indic_error_neighbour = True
                                                    indic_error_neighbour = True # set to True if at least for at least one neighbouring tile the meteorological file could not be downloaded
                                                    list_error.append(e)
                                                    list_tiles_incorrect_meteorological.append(ID)
                                                    if "Location over the sea" in str(e):
                                                        print(f"Problem with neighbouring grid tile n°{ID} : It is not possible to download the meteorological file, the centroid of the grid tile is located over the sea.")
                                                    elif "Internal Server Error" in str(e): 
                                                        print(f"Problem with neighbouring grid tile n°{ID} : It is not possible to download the meteorological file, there is an internal servor error (often due to centroid of the grid tile located too close to the sea).")
                                                    else : 
                                                        print(f"Problem with neighbouring grid tile n°{ID} : It is not possible to download the meteorological file.")
                                                        print(e)
                                            except (TimeoutError, exceptionsReadTimeout, OSError, ConnectionResetError) as e : 
                                                if i+1 not in list_remaining_tiles : 
                                                    list_remaining_tiles.append(i+1)
                                                if "Network is unreachable" in str(e) : 
                                                    print(f"Problem with neighbouring grid tile n°{ID} : It is not possible to download the meteorological file because the network is unreachable!")
                                                elif "Connection reset by peer" in str(e) : 
                                                    print(f"Problem with neighbouring grid tile n°{ID} : It is not possible to download the meteorological file because the connection was reset by peer!")
                                                else :
                                                    print(f"Problem with neighbouring grid tile n°{ID} : It is not possible to download the meteorological file due to ReadTimeout error!")
                                                if test == (nb_tests-1) :
                                                    global_indic_error_neighbour = True
                                                    indic_error_neighbour = True
                                        else : 
                                            indic_error_neighbour = True # set to True if at least for at least one neighbouring tile the meteorological file could not be downloaded
                                            print(f"Problem with neighbouring grid tile n°{ID} : It is not possible to download the meteorological file.")
                                    else : # for the tile with at least one problem for one of the neighbouring tile, don't make an average for this tile
                                        h = 15 
                                        latitude=df_centroid_modified['latitude'][i]
                                        longitude=df_centroid_modified['longitude'][i]
                                        try : 
                                            tmy,a,b,c= get_pvgis_tmy(latitude=latitude, longitude=longitude, outputformat='epw', url='https://re.jrc.ec.europa.eu/api/v5_2/', timeout=200)
                                            tmy = tmy.reset_index(drop=True)
                                            tmy = tmy.reset_index()
                                        except (TimeoutError, exceptionsReadTimeout, OSError, ConnectionResetError) as e : 
                                            if i+1 not in list_remaining_tiles : 
                                                list_remaining_tiles.append(i+1)
                                            if "Network is unreachable" in str(e) : 
                                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the network is unreachable!")
                                            elif "Connection reset by peer" in str(e) : 
                                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the connection was reset by peer!")
                                            else :
                                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file due to ReadTimeout error!")
                                            if test == (nb_tests-1) :
                                                if (i+1) not in list_tiles_incorrect_meteorological : 
                                                    list_error.append(e)
                                                    list_tiles_incorrect_meteorological.append(i+1)           
                                                    df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
                            
                                try :
                                    if indic_continue_tile == True and indic_error_neighbour == True : # for the tile with at least one problem for one of the neighbouring tile, make an average only with the valid neighbouring tiles
                                        sum_weights_error =0 
                                        for s in range(0, len(list_weights_no_normalized)):
                                            sum_weights_error = sum_weights_error +  list_weights_no_normalized[s]
                                        list_weights_no_normalized = list_weights_no_normalized/sum_weights_error  # calculate and normalize the weights for each neighbouring tiles
                                        latitude=df_centroid_modified['latitude'][i]
                                        longitude=df_centroid_modified['longitude'][i]
                                        tmy,a,b,c= get_pvgis_tmy(latitude=latitude, longitude=longitude, outputformat='epw', url='https://re.jrc.ec.europa.eu/api/v5_2/', timeout=200) 
                                        tmy = tmy.reset_index(drop=True)
                                        tmy = tmy.reset_index()
                                        tmy['relative_humidity'] = tmy['relative_humidity']*list_weights_no_normalized[0]
                                        tmy['temp_air'] = tmy['temp_air']*list_weights_no_normalized[0]
                                        tmy['ghi'] = tmy['ghi']*list_weights_no_normalized[0]
                                        tmy['dhi'] = tmy['dhi']*list_weights_no_normalized[0]
                                        tmy['dni'] = tmy['dni']*list_weights_no_normalized[0]
                                        ss = 1
                                        for ID in list_tile : 
                                            latitude = df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['latitude'].values[0]
                                            longitude = df_centroid_modified[df_centroid_modified['ID'] == int(ID)]['longitude'].values[0]
                                            tmy_t, a_t, b_t, c_t = get_pvgis_tmy(latitude=latitude, longitude=longitude, outputformat='epw', url='https://re.jrc.ec.europa.eu/api/v5_2/', timeout=200)
                                            tmy_t = tmy_t.reset_index(drop=True)
                                            tmy_t = tmy_t.reset_index()
                                            tmy['ghi']= tmy['ghi'] + tmy_t['ghi']*list_weights_no_normalized[ss] 
                                            tmy['dhi']= tmy['dhi'] + tmy_t['dhi']*list_weights_no_normalized[ss]
                                            tmy['dni']= tmy['dni'] + tmy_t['dni']*list_weights_no_normalized[ss]
                                            tmy['relative_humidity']= tmy['relative_humidity'] + tmy_t['relative_humidity']*list_weights_no_normalized[ss]
                                            tmy['temp_air']= tmy['temp_air'] + tmy_t['temp_air']*list_weights_no_normalized[ss]
                                            ss = ss+1
                                    fn_average_files = "average_txt_files_center_grid_"
                                    for j in range(0, len(files_txt_temp)):
                                        files_txt_temp.loc[j,'%iy']=2015
                                        files_txt_temp.loc[j,'id']=list_day[j]
                                    files_txt_temp['it']=tmy['hour']
                                    files_txt_temp['imin']=tmy['minute']
                                    files_txt_temp['RH']=tmy['relative_humidity']
                                    files_txt_temp['Td']=tmy['temp_air']
                                    files_txt_temp['Kdn']=tmy['ghi']
                                    files_txt_temp['Kdiff']=tmy['dhi']
                                    files_txt_temp['Kdir']=tmy['dni']
                                    path_average_txt_files = path_average_folder / (fn_average_files+str(i+1)+".txt")
                                    files_txt_temp.to_csv(str(path_average_txt_files), index=False, sep=' ')
                                except (TimeoutError, exceptionsReadTimeout, OSError, ConnectionResetError) as e : 
                                    if i+1 not in list_remaining_tiles : 
                                        list_remaining_tiles.append(i+1)
                                    if "Network is unreachable" in str(e) : 
                                        print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the network is unreachable!")
                                    elif "Connection reset by peer" in str(e) : 
                                        print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the connection was reset by peer!")
                                    else :
                                        print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file due to ReadTimeout error!")
                                    if test == (nb_tests-1) :
                                        if (i+1) not in list_tiles_incorrect_meteorological : 
                                            list_error.append(e)
                                            list_tiles_incorrect_meteorological.append(i+1)           
                                            df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
                            except (exceptionsHTTPError, HTTPError)  as e:
                                if ("Network is unreachable" in str(e)) or ("Connection reset by peer" in str(e)) or ("timed out" in str(e)) or ("Time-out" in str(e)): 
                                    list_remaining_tiles.append(i+1)
                                    if test == (nb_tests-1) :
                                        if (i+1) not in list_tiles_incorrect_meteorological : 
                                            list_error.append(e)
                                            list_tiles_incorrect_meteorological.append(i+1)           
                                            df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
                                else :
                                    global_indic_error_neighbour = True
                                    list_error.append(e)
                                    list_tiles_incorrect_meteorological.append(i+1)
                                    if "Location over the sea" in str(e):
                                        print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file, the centroid of the grid tile is located over the sea.")
                                    elif "Internal Server Error" in str(e): 
                                        print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file, there is an internal servor error (often due to centroid of the grid tile located too close to the sea).")
                                    else : 
                                        print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file.")
                                        print(e)
                            except (TimeoutError, exceptionsReadTimeout, OSError, ConnectionResetError) as e : 
                                if i+1 not in list_remaining_tiles : 
                                    list_remaining_tiles.append(i+1)
                                if "Network is unreachable" in str(e) : 
                                    print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the network is unreachable!")
                                elif "Connection reset by peer" in str(e) : 
                                    print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the connection was reset by peer!")
                                else :
                                    print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file due to ReadTimeout error!")
                                if test == (nb_tests-1) :
                                    if (i+1) not in list_tiles_incorrect_meteorological : 
                                        list_error.append(e)
                                        list_tiles_incorrect_meteorological.append(i+1)           
                                        df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})

    if global_indic_error_neighbour == False or option_no_average_if_one_problem == False : 
        df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
        path_list_tiles = path_meteorological_folder / "list_incorrect_tiles_meteorological.csv"
        df_list_tiles.to_csv(str(path_list_tiles), index=False)

    if global_indic_error_neighbour == True and option_no_average_if_one_problem == True : #if one error found and option_no_average_if_one_problem set to True ( True = don't average if there is at least one problem for one of the studied tile or for at least one neighbour of the studied tiles)
        
        list_remaining_tiles = []
        list_tiles_incorrect_meteorological = []
        list_error =[]

        for test in range(0, nb_tests): 
            if test > 0 : 
                print("Some tiles were not downloaded due to a ReadTimeout Error. Let's try another time! ")
            if (len(list_remaining_tiles) != 0) or test ==0  :
                list_copy_remaining_tiles = list_remaining_tiles.copy()  
                list_remaining_tiles = []    
            for i in tqdm(range(0,fc)):
                if (i in list_copy_remaining_tiles and test > 0) or test == 0 : 
                    try : 
                        latitude=df_centroid_modified['latitude'][i]
                        longitude=df_centroid_modified['longitude'][i]
                        tmy,a,b,c= get_pvgis_tmy(latitude=latitude, longitude=longitude, outputformat='epw', url='https://re.jrc.ec.europa.eu/api/v5_2/', timeout=200)
                        tmy = tmy.reset_index(drop=True)
                        tmy = tmy.reset_index()
                        fn_average_files = "average_txt_files_center_grid_"
                        for j in range(0, len(files_txt_temp)):
                            files_txt_temp.loc[j,'%iy']=2015
                            files_txt_temp.loc[j,'id']=list_day[j]
                        files_txt_temp['it']=tmy['hour']
                        files_txt_temp['imin']=tmy['minute']
                        files_txt_temp['RH']=tmy['relative_humidity']
                        files_txt_temp['Td']=tmy['temp_air']
                        files_txt_temp['Kdn']=tmy['ghi']
                        files_txt_temp['Kdiff']=tmy['dhi']
                        files_txt_temp['Kdir']=tmy['dni']
                        path_average_txt_files = path_average_folder / (fn_average_files+str(i+1)+".txt")
                        files_txt_temp.to_csv(str(path_average_txt_files), index=False, sep=' ')
                    
                    
                    except (exceptionsHTTPError, HTTPError)  as e:
                        if ("Network is unreachable" in str(e)) or ("Connection reset by peer" in str(e)) or ("timed out" in str(e))  or ("Time-out" in str(e)): 
                            list_remaining_tiles.append(i+1)
                            if test == (nb_tests-1) :
                                if (i+1) not in list_tiles_incorrect_meteorological : 
                                    list_error.append(e)
                                    list_tiles_incorrect_meteorological.append(i+1)           
                                    df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
                        else :
                            list_error.append(e)
                            list_tiles_incorrect_meteorological.append(i+1)
                            if "Location over the sea" in str(e):
                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file, the centroid of the grid tile is located over the sea.")
                            elif "Internal Server Error" in str(e): 
                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file, there is an internal servor error (often due to centroid of the grid tile located too close to the sea).")
                            else : 
                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file.")
                                print(e)
                    except (TimeoutError, exceptionsReadTimeout, OSError, ConnectionResetError) as e : 
                        if i+1 not in list_remaining_tiles : 
                            list_remaining_tiles.append(i+1)
                        if "Network is unreachable" in str(e) : 
                            print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the network is unreachable!")
                        elif "Connection reset by peer" in str(e) : 
                            print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the connection was reset by peer!")
                        else :
                            print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file due to ReadTimeout error!")
                        if test == (nb_tests-1) :
                            if (i+1) not in list_tiles_incorrect_meteorological : 
                                list_error.append(e)
                                list_tiles_incorrect_meteorological.append(i+1)           
                                df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})

        df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
        path_list_tiles = path_meteorological_folder / "list_incorrect_tiles_meteorological.csv"
        df_list_tiles.to_csv(str(path_list_tiles), index=False)

def _obtain_meteorological_files_no_average(df_centroid, path_txt_folder, path_meteorological_folder,  path_epw_folder=None, temp = False, nb_tests =5):
    """ Download the meteorological files from PVGIS for all the grid tiles centers and to transform the epw files in txt files  : it is the format needed to run SEBE calculation.
    
    The epw temporary files are saved only if ``temp`` is set to True.
    Exceptions are included to consider if meteorological files could not be downloaded. 
    It could happen if the grid tile centers are located over the sea or too close to the sea. 
    The list of the tiles for which the meteorological files could not have been downloaded are saved in a csv files with the corresponding error. 

    Parameters
    ----------
    df_centroid : Dataframe
        dataframe with the grid centroids (from df_centroid obtained in `create_csv_coordinates`)
    path_txt_folder : _type_
        _description_
    path_meteorological_folder : pathlib.Path
        path of the folder where to save all the meteorological files
    path_epw_folder : pathlib.Path, optional
        path of the folder where to save the epw files if temp is set to True, by default None
    temp : bool, optional
        boolean value to save or not the temporary epw files, by default False
    nb_tests : int, optional
        number of time to test downloading the meteorological file if there is a connection problem, by default 5
    """
    list_error =[]
    list_tiles_incorrect_meteorological = [] 
    columns = ['%iy','id', 'it', 'imin', 'Q*', 'QH', 'QE', 'Qs', 'Qf', 'Wind', 'RH','Td', 'press', 'rain', 'Kdn', 'snow', 'ldown', 'fcld', 'wuh', 'xsmd','lai_hr', 'Kdiff', 'Kdir', 'Wd']
    list_year = []
    for k in range(0, 8760): 
        list_year.append(2015)
    list_day=[]
    for day in range(0, 365): 
        for hour in range(0,24): 
            list_day.append(day+1)
    files_txt_temp= DataFrame({'%iy':list_year})
    for j in columns:
        files_txt_temp[j]=-999.00
    files_txt_temp=files_txt_temp.astype({'%iy':int, 'id':int, 'it':int, 'imin':int})

    fc = len(df_centroid)

    list_remaining_tiles = []
    for test in range(0, nb_tests): 
        if test > 0 and len(list_remaining_tiles)>0: 
            print("Some tiles were not downloaded due to a ReadTimeout Error. Let's try another time! ")
        if len(list_remaining_tiles) != 0  or test == 0:
            list_copy_remaining_tiles = list_remaining_tiles.copy()
            list_remaining_tiles = [] 
            for i in tqdm(range(0,fc)):
                if (i+1 in list_copy_remaining_tiles and test > 0) or test == 0 :  
                    latitude=df_centroid['latitude'][i]
                    longitude=df_centroid['longitude'][i]
                    try : 
                        tmy,a,b,c= get_pvgis_tmy(latitude=latitude, longitude=longitude, outputformat='epw', url='https://re.jrc.ec.europa.eu/api/v5_2/', timeout=200) 
                        if temp: 
                            fn_epw_files= "epw_files_center_grid_" 
                            path_epw_files = path_epw_folder / (fn_epw_files+str(i+1)+".csv")
                            tmy.to_csv(str(path_epw_files))
                        fn_average_files = "txt_files_center_grid_"
                        for j in range(0, len(files_txt_temp)):
                            files_txt_temp.loc[j,'%iy']=2015
                            files_txt_temp.loc[j,'id']=list_day[j]

                        tmy = tmy.reset_index(drop=True)
                        tmy = tmy.reset_index()
                        files_txt_temp['it']=tmy['hour']
                        files_txt_temp['imin']=tmy['minute']
                        files_txt_temp['RH']=tmy['relative_humidity']
                        files_txt_temp['Td']=tmy['temp_air']
                        files_txt_temp['Kdn']=tmy['ghi']
                        files_txt_temp['Kdiff']=tmy['dhi']
                        files_txt_temp['Kdir']=tmy['dni']
                        path_txt_files = path_txt_folder / (fn_average_files+str(i+1)+".txt")
                        files_txt_temp.to_csv(str(path_txt_files), index=False, sep=' ')
                        df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})

                    except (exceptionsHTTPError, HTTPError)  as e:
                        if ("Network is unreachable" in str(e)) or ("Connection reset by peer" in str(e)) or ("timed out" in str(e)) or ("Time-out" in str(e)) : 
                            list_remaining_tiles.append(i+1)
                            if test == (nb_tests-1) :
                                if (i+1) not in list_tiles_incorrect_meteorological : 
                                    list_error.append(e)
                                    list_tiles_incorrect_meteorological.append(i+1)           
                                    df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
                        else :
                            list_error.append(e)
                            list_tiles_incorrect_meteorological.append(i+1)
                            df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
                            if "Location over the sea" in str(e):
                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file, the centroid of the grid tile is located over the sea.")
                            elif "Internal Server Error" in str(e): 
                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file, there is an internal servor error (often due to centroid of the grid tile located too close to the sea).")
                            else : 
                                print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file.")
                    
                    except (TimeoutError, exceptionsReadTimeout, OSError, ConnectionResetError) as e : 
                        if i+1 not in list_remaining_tiles : 
                            list_remaining_tiles.append(i+1)
                        if "Network is unreachable" in str(e) : 
                            print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the network is unreachable!")
                        elif "Connection reset by peer" in str(e) : 
                            print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file because the connection was reset by peer!")
                        else :
                            print(f"Problem with grid tile n°{i+1} : It is not possible to download the meteorological file due to ReadTimeout error!")
                        if test == (nb_tests-1) :
                            if (i+1) not in list_tiles_incorrect_meteorological : 
                                list_error.append(e)
                                list_tiles_incorrect_meteorological.append(i+1)           
                                df_list_tiles = DataFrame({'tile_number': list_tiles_incorrect_meteorological, 'error': list_error})
    path_list_tiles = path_meteorological_folder / "list_incorrect_tiles_meteorological.csv"
    df_list_tiles.to_csv(str(path_list_tiles), index=False)

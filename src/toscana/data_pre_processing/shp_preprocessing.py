"""module to pre-process shapefiles"""
from geopandas import read_file
from requests import get
from py7zr import unpack_7zarchive
from ..utils import processing
from qgis.core import QgsCoordinateReferenceSystem, QgsProcessingException

""" PRE PROCESS BUILDING AND MUNICIPALITY FOOTPRINT """

def download_and_extract_BDTOPO_data(departement, path_raw_data_folder): 
    """Download shapefiles (municipalities footprints and buildings footprints) from the BDTOPO database on the IGN website giving a the number of the ``departement``.

    A packed folder is downloaded and then extracted.
    The version downloaded is the 15-12-2023 version. 

    Parameters
    ----------
    departement : str
        departement the municipality
    path_raw_data_folder : pathlib.Path
        path of the folder with raw data (downloaded) files (define in main function)

    Returns
    -------
    path_departement_municipalities_footprint : pathlib.Path
        path of the municipalities footprints for the department of interest  
    path_input_departement_building : pathlib.Path
        path of the buildings footprints for the department of interest 
    """ 
    if departement != "2A" and departement !="2B" : 
        try :  
            string_value = int(departement)
        except: 
            raise ValueError("departement must be a string with the number of the french departement (and not the name) !")
        try : 
            if int(departement) > 95 : 
                raise ValueError
        except ValueError: 
            raise ValueError("This departement does not exist (or not available)!")
      
    link = f"https://data.geopf.fr/telechargement/download/BDTOPO/BDTOPO_3-3_TOUSTHEMES_SHP_LAMB93_D0{departement}_2023-12-15/BDTOPO_3-3_TOUSTHEMES_SHP_LAMB93_D0{departement}_2023-12-15.7z"
    path_packed_download_folder = path_raw_data_folder / f"BDTOPO_D0{departement}_2023-12-15.7z"
    print(f"Download from : {link}")
    response = get(link)
    
    with open(str(path_packed_download_folder), 'wb') as f:
        f.write(response.content)
    print("Download completed.")

    path_unpacked_download_folder = path_raw_data_folder/ f"BDTOPO_D0{departement}_2023-12-15"
    with open(str(path_packed_download_folder), 'rb') as f:
        unpack_7zarchive(f, str(path_unpacked_download_folder))
    print("Extraction completed.")

    path_departement_municipalities_footprint = path_unpacked_download_folder / f"BDTOPO_3-3_TOUSTHEMES_SHP_LAMB93_D0{departement}_2023-12-15/BDTOPO/1_DONNEES_LIVRAISON_2023-12-00099/BDT_3-3_SHP_LAMB93_D0{departement}-ED2023-12-15/ADMINISTRATIF/COMMUNE.shp"
    path_input_departement_building =  path_unpacked_download_folder / f"BDTOPO_3-3_TOUSTHEMES_SHP_LAMB93_D0{departement}_2023-12-15/BDTOPO/1_DONNEES_LIVRAISON_2023-12-00099/BDT_3-3_SHP_LAMB93_D0{departement}-ED2023-12-15/BATI/BATIMENT.shp"

    return path_departement_municipalities_footprint, path_input_departement_building

def obtain_municipality_footprint(path_departement_municipalities_footprint, path_output_municipality_footprint, INSEE_code): 
    """Obtain the municipality footprint of the selected municipality among all the municipalities of the selected departement using the ``INSEE_code``.

    Parameters
    ----------
    path_departement_municipalities_footprint : pathlib.Path
        path of the municipalities footprint for the department of interest 
    path_output_municipality_footprint : pathlib.Path
        path where to save the layer with the municipality footprint of the selected municipality
    INSEE_code : str
        INSEE code of the municipality to study
    """
    # expression  = f'"INSEE_COM"={INSEE_code}'
    expression = f'"INSEE_COM" =\'{INSEE_code}\''
    print(expression)
    processing.run("native:extractbyexpression", \
    {'INPUT':str(path_departement_municipalities_footprint),\
    'EXPRESSION':expression,\
    'OUTPUT':str(path_output_municipality_footprint)})

def reproject_shapefiles_2154_to_IGNF(path_shapefiles_2154, path_shapefiles_IGNF ): 
    """Reproject shapefiles from EPSG 2154 reference system into IGNF : ETRS89LAEA reference system.

    Parameters
    ----------
    path_shapefiles_2154 : pathlib.Path
        path of the shapefile in the reference system EPSG:2154 (path_output_municipality_footprint obtained in `obtain_municipality_footprint or path_municipality_buildings from obtain_municipality_buildings`)
    path_shapefiles_IGNF : pathlib.Path
        path where to save the layer (shapefile reproject in IGNF: ETRS89LAEA reference system)
    """
    processing.run("native:reprojectlayer",\
    {'INPUT':str(path_shapefiles_2154),\
    'TARGET_CRS':QgsCoordinateReferenceSystem('IGNF:ETRS89LAEA'),\
    'OPERATION':'+proj=pipeline +step +inv +proj=lcc +lat_0=46.5 +lon_0=3 +lat_1=49 +lat_2=44 +x_0=700000 +y_0=6600000 +ellps=GRS80 +step +proj=laea +lat_0=52 +lon_0=10 +x_0=4321000 +y_0=3210000 +ellps=GRS80',\
    'OUTPUT':str(path_shapefiles_IGNF)})

def obtain_municipality_buildings(path_input_departement_building, path_input_municipality_footprint, path_municipality_buildings): 
    """Obtain the buildings of the selected municipality from the buildings of the departement of interest.

    Parameters
    ----------
    path_input_departement_building : pathlib.Path
        path of the shapefile with buildings from the selected departement 
    path_input_municipality_footprint : pathlib.Path
        path of the municipality footprint (path_output_municipality_footprint obtained in `obtain_municipality_footprint`)
    path_municipality_buildings : pathlib.Path
        path where to save the layer with buildings of the municipality
    """
    processing.run("native:clip", \
    {'INPUT':str(path_input_departement_building),\
    'OVERLAY':str(path_input_municipality_footprint),\
    'OUTPUT':str(path_municipality_buildings)})


def check_validity(path_input_shapefiles, path_valid_shapefiles): 
    """Verify the validity of buildings footprints (remove invalid features).

    Parameters
    ----------
    path_input_shapefiles : pathlib.Path
        path of the shapefile to verify (path_reproject_municipality_buildings obtained in `reproject_buildings` for example)
    path_valid_shapefiles : pathlib.Path
        path where to save the shapefile layer with only valid features
    """
    processing.run("qgis:checkvalidity", \
    {'INPUT_LAYER':str(path_input_shapefiles),\
    'METHOD':2,\
    'IGNORE_RING_SELF_INTERSECTION':False,\
    'VALID_OUTPUT':str(path_valid_shapefiles)})

def preprocess_municipality_buildings(path_shapefiles, path_municipalities_dep, village_INSEE_code, path_buildings_dep):
    """Pre process the municipality and the building footprints.
    
    It allows to obtain the buildings and municipality footprints of the studied municiaplity and reproject them in the good geographical reference system. 
    Invalid features are also removed.  

    Parameters
    ----------
    path_shapefiles : pathlib.Path
        path of the folder with temporary shapefiles (define in main function)
    path_municipalities_dep : pathlib.Path
        path of the municipalities footprints for the department of interest 
    village_INSEE_code : str
        INSEE code of the municipality to study
    path_buildings_dep : pathlib.Path
        path of the shapefile with buildings from the selected departement 
    """
    path_municipality_footprint = path_shapefiles / "municipality_footprint.shp"
    obtain_municipality_footprint(path_municipalities_dep, path_municipality_footprint, village_INSEE_code)
    path_reproject_municipality_footprint = path_shapefiles / "municipality_footprint_reproject.shp"
    reproject_shapefiles_2154_to_IGNF(path_municipality_footprint, path_reproject_municipality_footprint)
    path_municipality_buildings = path_shapefiles / "municipality_buildings.shp"
    try : 
        obtain_municipality_buildings(path_buildings_dep, path_municipality_footprint, path_municipality_buildings)
    except QgsProcessingException as e :
        if "has invalid geometry" in str(e): 
            print("It is not possible to obtain the municipality buildings due to an error in the building footprint shapefile (invalid geometry of one building). The validity of buildings is checked for all the buildings of the departement.")
            path_buildings_dep_valid = path_shapefiles / "valid_departement_buildings.shp"
            check_validity(path_buildings_dep, path_buildings_dep_valid)
            obtain_municipality_buildings(path_buildings_dep_valid, path_municipality_footprint, path_municipality_buildings)
    path_municipality_buildings_reproject = path_shapefiles / "municipality_buildings_reproject.shp"
    reproject_shapefiles_2154_to_IGNF(path_municipality_buildings,path_municipality_buildings_reproject)
    path_municipality_buildings_reproject_valid = path_shapefiles / "municipality_buildings_reproject_valid.shp"
    check_validity(path_municipality_buildings_reproject, path_municipality_buildings_reproject_valid)



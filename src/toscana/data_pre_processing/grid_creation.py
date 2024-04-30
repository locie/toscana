"""module to create a grid"""

from ..utils import processing

from qgis.core import QgsCoordinateReferenceSystem
from qgis.core import QgsVectorLayer

from geopandas import read_file

""" CREATION OF THE GRID """

def obtain_municipality_extent(path_reproject_municipality_footprint, path_municipality_extent,  projection = 'IGNF:ETRS89LAEA' ):
    """Obtain the rectangle extent of the municipality (from the municipality footprint) and obtain extents points (in IGNF ETRS89LAEA reference system by default, modify ``projection``to change it).

    Parameters
    ----------
    path_reproject_municipality_footprint : pathlib.Path
        path of the municipality footprint shapefile reproject in the new neference system (for example path_reproject_municipality_footprint obtained in `reproject_municipality_footprint`)
    path_municipality_extent : pathlib.Path
        path where to save the layer with the municipality extent shapefile
    projection : str, optional
        name of the reference system of the grid, by default "IGNF:ETRS89LAEA"
        
    Returns
    -------
    extent_points : str
        string with the extent points of the commune extent (format needed for qgis simulation)
    """
    processing.run("native:polygonfromlayerextent", \
    {'INPUT':str(path_reproject_municipality_footprint),\
    'ROUND_TO':0,\
    'OUTPUT':str(path_municipality_extent)})

    commune_extent = QgsVectorLayer(str(path_municipality_extent), '', 'ogr')
    for feat in commune_extent.getFeatures():
        minX=feat['MINX']
        minY=feat['MINY']
        maxX=feat['MAXX']
        maxY=feat['MAXY']
    extent_points=str(minX)+','+str(maxX)+','+str(minY)+','+str(maxY)+f'[{projection}]'
    return extent_points

def define_grid(extent_points, path_grid, projection = 'IGNF:ETRS89LAEA', horizontal_spacing =1000, vertical_spacing =1000):
    """Obtain the grid that will be used for the simulation.

    It is a grid of 1000m (``horizontal_spacing``) per 1000m (``vertical_spacing``) per default.

    Parameters
    ----------
    extent_points : str
        string with the extent points of the commune extent (extents_point obtained in `obtain_municipality_extent`)
    path_grid : pathlib.Path
        path where to save the layer with the grid
    projection : str, optional
        name of the reference system of the grid, by default "IGNF:ETRS89LAEA"
    horizontal_spacing : int, optional
        horizontal size of grid tiles, by default 1000
    vertical_spacing : int, optional
        vertical size of grid tiles, by default 1000

    Returns
    -------
    grid_gpd : GeoDataFrame
        geopandas grid file

    Raises
    ------
    AssertionError
        horizontal_spacing too large (compared to horizontal length of municipality extent)
    AssertionError
        vertical_spacing too large (compared to vertical length of municipality extent)
    """ 
    minx = extent_points.split(',')[0]
    minx = float(minx)
    maxx =extent_points.split(',')[1]
    maxx = float(maxx)
    miny = extent_points.split(',')[2]
    miny = float(miny)
    maxy =extent_points.split(',')[3]
    maxy = maxy.split('[')[0]
    maxy = float(maxy)
    
    diff_x = maxx-minx
    diff_y = maxy - miny
    if horizontal_spacing > diff_x :
        raise AssertionError(f'Horizontal spacing too large for the municipality size ! Horizontal length of municipality extent : {diff_x} ')

    if vertical_spacing > diff_y :
        raise AssertionError(f'Vertical spacing too large for the municipality size ! Vertical length of municipality extent : {diff_y} ')

    crs = QgsCoordinateReferenceSystem(f'{projection}')
    processing.run("native:creategrid",\
    {'TYPE':2,\
    'EXTENT':extent_points,\
    'HSPACING':horizontal_spacing,\
    'VSPACING':vertical_spacing,\
    'HOVERLAY':0,\
    'VOVERLAY':0,\
    'CRS':crs,\
    'OUTPUT':str(path_grid)})
    grid_gpd = read_file(str(path_grid))
    return grid_gpd 

def obtain_grid(path_shapefiles, projection = "IGNF:ETRS89LAEA", horizontal_spacing = 1000, vertical_spacing =1000) : 
    """Create the grid in order to run the SEBE simulation for the studied village.

    It is a grid of 1000m (``horizontal_spacing``) per 1000m (``vertical_spacing``) per default (in IGNF ETRS89LAEA reference system by default, modify ``projection``to change it).

    Parameters
    ----------
    path_shapefiles : pathlib.Path
        path of the folder with temporary shapefiles (define in main function) 
    projection : str, optional
        name of the reference system of the grid, by default "IGNF:ETRS89LAEA"
    horizontal_spacing : int, optional
        horizontal size of grid tiles, by default 1000
    vertical_spacing : int, optional
        vertical size of grid tiles, by default 1000
    Returns
    -------
    grid_gpd : GeoDataFrame
        geopandas grid file
    """
    path_reproject_municipality_footprint = path_shapefiles /  "municipality_footprint_reproject.shp"
    path_municipality_extent = path_shapefiles / "municipality_extent.shp"
    extent_points = obtain_municipality_extent(path_reproject_municipality_footprint, path_municipality_extent, projection=projection)
    path_municipality_grid = path_shapefiles / "municipality_grid.shp"
    grid_gpd = define_grid(extent_points, path_municipality_grid,projection=projection, horizontal_spacing=horizontal_spacing, vertical_spacing=vertical_spacing)

    return grid_gpd


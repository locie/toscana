# toscana

## What does "toscana" stand for? 
"toscana" stands for TerritOrial Solar Cadastre modeling and ANAlysis. 


## Scientific description 
`toscana` is a tool aimed at obtaining a solar cadastre at the territory or municipality scale. 

It is based on the `SEBE` algorithm from `UMEP`. 
This tool facilitates simulation over large scale by gathering and consolidating all the pre-processing and post-processing tasks. Additionaly, the tool was developped with the goal of being suitable for mountainous territories by considering local and far masks. 
`toscana` has been developped to be compatible with open-access databases for the French territory, but can be adapated for other databases (after adjusting them to the required format).
The installation procedure for `toscana` is detailed in the [Installation](#installation) subsection and should be followed precisely.


## Example 

An example of usage is provided in the tests folder in `test`. 
To run the example, you need at least to specify a `working_directory` (a folder path) in the `test` file (line 26).
The example will allow you to obtain a solar cadastre for the village of *La Croix-de-la-Rochette* (INSEE code : 73095). 

There are two options to execute this test : 
- First option : set `download_BDTOPO` and `download_DEM` to True. This will utilize two functions that allow for the direct downloading of the BDTOPO (IGN) for the chosen departement and the raster files from OpenDem for the selected municipality. 
- Second option : set `download_BDTOPO` and `download_DEM` to False, and download the data from [toscana_test_data](https://github.com/locie/toscana_test_data). Then, place these downloaded data in a subfolder named **DATA** within your specified **working directory**. 
    These data can be obtained as follows : 
    - The shapefiles _BATIMENT_ and _COMMUNE_ can be found by downloading the dataset from the BDTOPO for departement 73 ([IGN database](https://geoservices.ign.fr/bdtopo)).\
        - _COMMUNE.shp_ can be found in the subfolder  : "/BDTOPO/1_DONNEES_LIVRAISON_XXXX-XX-XXXXX/BDT_X-X_SHP_LAMB93_D073-EDXXXX-XX-XX/ADMINISTRATIF/". \
        - _BATI.shp_ can be found in the subfolder : "/BDTOPO/1_DONNEES_LIVRAISON_XXXX-XX-XXXXX/BDT_X-X_SHP_LAMB93_D073-EDXXXX-XX-XX/BATI/".\
        - XXXX represents numbers that depend on the version of the dataset. \
    - The raster file _N245E400.tif_ can be downloaded from [OpenDem](https://www.opendem.info/opendemeu_download_highres.html).

If the first option is selected, the municipality can be changed by modifying `village_name`, `village_INSEE_code` and `village_departement`. 

## Databases

Three main inputs are required to use this package : one shapefile with the municipality/territory footprint, one shapefile with the building footprints and one raster file with a DEM.

### Basic databases
`toscana` was designed to utilize shapefiles from the BDTOPO database produced by IGN. Two inputs are required from the BDTOPO : _COMMUNE.shp_ and _BATIMENT.shp_.
`toscana` is configured for the use of raster in IGNF: ETRS89LAEA coordinate reference system. Such rasters can be found on the [OpenDEM portal](https://www.opendem.info/opendemeu_download_highres.html).



### Databases requirements
To utilize all functions within the package, the following input data requirements must be met:
- Building footprint : projected in EPSG:2154, with a column named "HAUTEUR" representing the maximum building height. 
- Municipality footprint : projected in EPSG:2154, with a column named "INSEE_COM" containing the INSEE code of the municipality (for France) and a column named "POPULATION" with the number of inhabitants (only used for post-processing). 
- DEM (Digital Elevation Model) : projected in IGNF:ETRS89LAEA, covering a larger extent than the municipality footprint, with a recommended resolution of 1 meter.

### Use of alternative databases

Many other databases are available and could be compatible with functions available in `toscana`. 

#### Projection of alternative databases
The raster and shapefile databases should share the same projection (preferably matching the raster's projection, as reprojecting a raster is more complex). A function is available to reproject the shapefile from BDTOPO (EPSG:2154) into the IGNF:ETRS89LAEA projection.

If the shapefile are in a different projection than EPSG:2154, they should be pre-processed using software/package like QGIS, although `toscana` does not provide such pre-processing functions.

Most of the function are designed to be used with IGNF:ETRS89LAEA projection, but for many of them, it is possible to specify the name of an alternative projection. 

For ease of use with `toscana`, a DEM projected in IGNF:ETRS89LAEA is recommended. IGNF:ETRS89LAEA is a projected coordinate reference systems with coordinates in meters. Some functions will work only with projected coordinate systems.

#### Required information in the shapefiles
In the shapefile containing building footprints, a column indicating building height should be present. By default, the column name is "HAUTEUR", but this can be changed if the shapefile is not derived from BDTOPO.

For the shapefile containing the municipality footprints, a column with the INSEE code of the studied municipality should be included (unique code). If the studied territory is not a French municipality, data should be preprocessed to obtain the footprint of the territory in a 
shapefile. Additionally, in this shapefile, the "POPULATION" column is used for post-processing results, but it is optional.

#### Other required information
Three pieces of information are needed to start the simulation : the village name, the village INSEE code and the departement. 
The village name can be replaced by the name of the territory to study. 
The INSEE code is usefull to select the territory footprint. If it's not available, the footprint needs to be obtained using another method. 
The departement and the INSEE code are also needed for post-processing but are optional for this initial step.


## Common/unsolved problems
Some comon problems have been identified and have not yet been resolved:
- Meteorological files are obtained from PVGIS. If the municipality is located close to the sea, there may be occasions where some meteorological data cannot be downloaded. If certain meteorological files cannot be downloaded, several options can be selected to average the available meteorological data.
- Erroneous meteorological files can cause the SEBE calculation to fail.
- The meteorological data are processed in SEBE : the diffuse and direct irradiation components are redistributed into sky vault patches. If meteorological files are averaged, this redistribution can result in some components becoming negative, leading to negative irradiation received by surfaces (which is physically impossible).
- To address negative results from the SEBE calculation, the direct and diffuse irradiation components could be estimated from global irradiation. However, in some cases, the sky irradiance distribution could failed if these components are estimated from global irradiation.


## Documentation

You can access the documentation in 3 ways:

- embedded help within your IDE regarding specific `toscana` functions
- the HTML version of this documentation: simply open (with your browser) the file `doc/_build/html/index.html` 
- the PDF version of this documentation: `doc/_build/toscana.pdf`

## Installation 

### Overview

`toscana` was successfully tested on the following setup:

- `conda` environment
- `qgis` installed within this environment (LTS release)
- `python=3.10`
- plugins `UMEP` and `UMEP for processing` installed through the Qgis GUI

Installation is a 2 steps process: 

1. Creation of the conda environment
2. Installation of `toscana`

The package has been tested on Linux and Windows, and is normally compatible OS X. 

### Environment set up

Below is a small code snippet that would set up a proper conda environment:

```
conda create -n toscana_env python=3.10
conda activate toscana_env
conda install -y conda-forge::qgis=3.34 conda-forge::pvlib conda-forge::matplotlib-scalebar 
conda install -y conda-forge::jaydebeapi=1.2.3 
conda install -y rasterio matplotlib tqdm scipy scikit-learn shapely geopandas pandas fiona

```

If needed, you might install the `draco` and `py7zr` libraries:

```
conda install conda-forge::gsl conda-forge::draco conda-forge::py7zr 
```

Don't forget to [install `UMEP` and `UMEP for processing` from Qgis **Plugin Manager**](https://docs.qgis.org/3.34/en/docs/training_manual/qgis_plugins/fetching_plugins.html#follow-along-installing-new-plugins)!

### `toscana` installation


#### `pip` installation (preferred way)

1. Activate your conda environment (`toscana_env`)
2. Run `pip install toscana`.

**note**: installation of packages using `pip` within a conda environment is usually depreciated, yet this one is very unlikely to break your environment.

#### Manual installation

1. Clone this repository: `git clone <Github_repo>`
2. Move to the cloned directory: `cd toscana`
3. Activate your conda environment (`toscana_env`)
4. Run `pip install .` to install the `toscana` package

You can test your installation by running `import toscana` inside a Python interpreter.

### Notes

A conda package might be available in a near future.

## Detailed description 

### Main algorithm
The solar cadastres created with `toscana` are based on calculations performed using SEBE algorithms developed in the UMEP plugin for QGIS. 

Calculations can be time-consuming if the size of the studied territory is too large. Therefore, the territory is divided into tiles, and simulations are conducted per tile. The required inputs include a DSM (Digital Surface Model), a raster file containing wall aspect data and one containing wall height data, and a meteorological file. 

A different meteorological file is used for each grid tile, allowing to consider the various far masks at different locations (especially in the mountainous territory). 


### Meteorological files 

- `toscana` allows averaging of meteorological files to address discontinuities caused by low resolution of weather data.

Meteorological files are sourced from the SARAH-2 database and downloaded from PVGIS. They are taking into account the far masks. 
However, the resolution of this dataset is only 5km, which means that two simulation tiles belonging to different parts of the SARAH-2 database can result in significantly different meteorological files.
To mitigate large differences and discontinuities in input weather data that could lead to substantial variations in calculated irradiance, `toscana` allows averaging of meteorological files. 
An average of the weather files from the studied tile and its 12 neighbouring tiles is computed, with weights depending on the distance between the center of each neighbouring tile and the studied tile, and based on the normal distribution. 

### Data preparation 
Data preparation is necessary before running the calculation to obtain the solar cadastre with `toscana`. This tool is designed to study a specific delimited territory (such as a municipality). 
The footprint of the territory must be obtained and must be in the same projection as the DEM, wich represents the elevation of the terrain. Therefore, shapefiles must be reprojected into the correct reference system. The grid is then created based on the footprint of the territory. 
The DEM may need to be resampled if its resolution is too low, especially because it will be modified to include the height of the buildings.

### Post-processing 
`toscana` was also developed to calculate irradiation on building rooftops. 
After obtaining the solar cadastre, post processing is performed to calculate the mean irradiation per building. Buffers are created to exclude the edges of the buildings because edges typically receive much lower irradiation than the rest of the rooftop.

### Visualization of the results
`toscana` allows visualization of the results including the DEM, the solar map, a map displaying the mean irradiation per building. 
Additionally, the mean irradiation per building is displayed as an histogram. The histogram often fits very well the Johnson's SU distribution for the majority of French municipalities.

Futhermore, `toscana` allows calculating severam indicators such as a Sky View Index, a Diffuse Fraction Index and also indicators related to the description of the distribution of the mean irradiation per building. 


## Author

Apolline Ferry is the author of this code, developed during her PhD thesis. You can contact her by email at : apolline.ferry@laposte.net or sending a message on GitHub. 

## Copyright
The code is distributed under an Apache-2.0 license. 
Most of the development work was conducted during a PhD thesis funded by [UNITA](https://univ-unita.eu/Sites/UNITA/en/).

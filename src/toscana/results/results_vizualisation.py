import matplotlib.pyplot as plt 
from rasterio import plot as rioplot, open as rasterio_open
import matplotlib.colors as colors

from numpy import linspace, ceil, floor, nanmin, nanmax
from matplotlib_scalebar.scalebar import ScaleBar
from geopandas import read_file
from shapely.geometry import Point
from scipy.stats import johnsonsu
import matplotlib.patches as mpatches
from ..utils import calculate_histogram_and_johnsonsu_fit

""" RESULTS DISPLAY """
def display_elevation_file(path_raster, rectangle = True, bool_title_elevation= False, title_elevation= "Map of the municipality's elevation"):  
    """Display in a figure the raster of an elevation file (DSM, DEM for example) with a grey scale.

    Parameters
    ----------
    path_raster : pathlib.Path
        path of the raster file to display (path_DSM obtained in `create_DSM` or path_DHM obtained in `create_DHM` for example)
    rectangle : bool, optional
        boolean value to display or not the borders (recommended to set to False if the raster is a raster coming from `clip_raster` function), by default True
    bool_title_elevation : bool, optional
        boolean value to display or not the title, by default False
    title_elevation : str, optional
        title of the figure, by default "Map of the municipality's elevation"
    """
    fig, ax = plt.subplots(figsize=(11, 7))
    font = {'size' : 16}
    plt.rc('font', **font)
    raster = rasterio_open(str(path_raster))
    data = raster.read(1, masked=True)
    vmin = floor(nanmin(data[data != 0]) / 10) * 10
    vmax = ceil(nanmax(data) / 10) * 10
    cmap_reversed = plt.colormaps['Greys_r']
    cmap_custom = cmap_reversed
    norm = colors.Normalize(vmin=vmin, vmax=vmax)
    rioplot.show(raster, ax=ax, cmap = cmap_custom, norm=norm)
    image = ax.get_images()[0]
    cbar = plt.colorbar(image, ax=ax, label ='Altitude (m)', shrink =1) 
    cbar.set_label('Altitude (m)', fontsize=25) 
    cbar.ax.tick_params(labelsize=25) 
    ax = plt.gca()
    ax.yaxis.set_major_formatter(plt.NullFormatter())
    ax.xaxis.set_major_formatter(plt.NullFormatter())
    plt.tick_params(axis = 'x', length = 0)
    plt.tick_params(axis = 'y', length = 0)
    if rectangle == False: 
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
    scalebar = ScaleBar(1, units='m', scale_loc='bottom', length_fraction=0.2, width_fraction=0.02, font_properties={"size": 25}) 
    ax.add_artist(scalebar)
    scalebar.font_size = 30
    scalebar.color = 'black'
    scalebar.location = 'lower left'
    if bool_title_elevation:
        plt.title(label = title_elevation, fontsize = 25)
    plt.tight_layout()
    plt.show()

def display_SEBE_raster(path_raster, rectangle = False, bool_title_SEBE = False, title_SEBE = f"Map of the municipality's average \nannual irradiation on surfaces"):  
    """Display in a figure the raster of the merge SEBE raster with a Red Yellow Blue colorscale.

    Parameters
    ----------
    path_raster : pathlib.Path
        path of the raster to display, made for the merge raster with SEBE results (path_merge_SEBE_raster obtained in `merge_SEBE_raster` or path_clip_raster obtained in `clip_raster`)
    rectangle : bool, optional
        boolean value to display or not the borders (recommended to set to False if the raster is a raster coming from `clip_raster function`), by default False
    bool_title_SEBE : bool, optional
        boolean value to display or not the title, by default False
    title_SEBE : str, optional
        title of the figure, by default f"Map of the municipality's average \nannual irradiation on surfaces"
    """
    fig, ax = plt.subplots(figsize=(11, 7))
    font = {'size':16}
    plt.rc('font', **font)
    raster = rasterio_open(str(path_raster))
    data = raster.read(1, masked=True)
    vmin = floor(nanmin(data[data != 0]) / 10) * 10
    if vmin < 0 : 
        vmin = 0
    vmax = ceil(nanmax(data) / 10) * 10
    cmap_reversed =plt.colormaps['RdYlBu_r'] 
    colors_custom = ['white'] + cmap_reversed(linspace(0, 1, cmap_reversed.N-1)).tolist() 
    cmap_custom = colors.LinearSegmentedColormap.from_list('CustomColormap', colors_custom)
    norm = colors.Normalize(vmin=vmin, vmax=vmax)
    rioplot.show(raster, ax=ax, cmap = cmap_custom, norm=norm)
    image = ax.get_images()[0]
    cbar = plt.colorbar(image, ax=ax, label ='Irradiation (kWh/m²)', shrink =1) 
    cbar.set_label('Irradiation (kWh/m²)', fontsize=25) 
    cbar.ax.tick_params(labelsize=25)
    ax = plt.gca()
    ax.yaxis.set_major_formatter(plt.NullFormatter())
    ax.xaxis.set_major_formatter(plt.NullFormatter())
    plt.tick_params(axis = 'x', length = 0)
    plt.tick_params(axis = 'y', length = 0)
    if rectangle == False : 
        ax.spines['top'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['right'].set_visible(False)
    scalebar = ScaleBar(1, units='m', scale_loc='bottom', length_fraction=0.2, width_fraction=0.02, font_properties={"size": 25})
    ax.add_artist(scalebar)
    scalebar.font_size = 30
    scalebar.color = 'black'
    scalebar.location = 'lower left'
    if bool_title_SEBE :
        plt.title(label =title_SEBE, fontsize = 25)
    plt.tight_layout()
    plt.show()

def display_zonal_stat_shapefile(path_shapefile, column_name, bool_title_stats = False, title_stats = f"Map of the municipality's average annual rooftop\nirradiation per building", label_stats = "Irradiation (kWh/m²)"):
    """Display in a figure a shapefile containing data (in the column ``column_name``) to display with a Orange Red colorscale. 

    It displays the value if the cursor is put on a shape (a building footprint for example).
    It is made to be used with a building footprints shapefile with average annual solar irradiation received by buildings (``column_name`` sol_mean for example).

    Parameters
    ----------
    path_shapefile : pathlib.Path
        path of the shapefile with the data (zonal statistics) to display (path_buildings_buffer_zonal_stat_post_process obtained in `_post_process_buffer_zonal_stat` for example)
    column_name : str
        name of the column in the shapefile containing the values to display
    bool_title_stats : bool, optional
        boolean value to display or not the title, by default False
    title_stats : _type_, optional
        title of the figure, by default f"Map of the municipality's average annual rooftop\nirradiation per building"
    label_stats : str, optional
        lalbel of the colorbar, by default "Irradiation (kWh/m²)"

    Raises
    ------
    AttributeError
        name of the column (``column_name``) not found in the dataframe
        if ``column_name`` is too long (>10 characters), the name was probably shortened before saving
    """
    try : 
        fig, ax = plt.subplots(figsize=(11, 7))
        font = {'size' : 16}
        plt.rc('font', **font)
        shapefile = read_file(path_shapefile)
        if column_name  not in shapefile.columns:
            if len(column_name)>10 : 
                raise AttributeError(f"No column named '{column_name}' found in the dataframe. Name too long and has probably been shortened before saving the shapefile") 
            else : 
                raise AttributeError(f"No column named '{column_name}' found in the dataframe.")
        cmap = plt.colormaps['OrRd']
        color = cmap(max(shapefile[column_name]))
        shapefile_plot = shapefile.plot(column=column_name, ax=ax, cmap ="OrRd")
        ax.yaxis.set_major_formatter(plt.NullFormatter())
        ax.xaxis.set_major_formatter(plt.NullFormatter())
        plt.tick_params(axis='x', length=0)
        plt.tick_params(axis='y', length=0)

        cbar = fig.colorbar(shapefile_plot.collections[0], ax=ax)
        cbar.set_label(label_stats, fontsize=16)  
        cbar.ax.tick_params(labelsize=16)  
        
        annotations = []
        
        def hover(event):
            """Display values when the cursor is put on a shape.

            Parameters
            ----------
            event : MouseEven
                the mouse event triggered by hovering over a shape
            """
            nonlocal annotations
            
            for annotation in annotations:
                annotation.remove()
            
            annotations = []
            
            if event.inaxes == ax:
                point = Point(event.xdata, event.ydata)
                for idx, row in shapefile.iterrows():
                    if row.geometry.contains(point):
                        annotation = ax.annotate(f"{row[column_name]}", (event.xdata, event.ydata), xytext=(10, 10), textcoords='offset points', fontsize=12, color='black', weight='bold')
                        annotations.append(annotation)
                        fig.canvas.draw_idle()
                        return
        fig.canvas.mpl_connect('motion_notify_event', hover)
        legend_patch = mpatches.Patch(color=color, label='Buildings' )
        if bool_title_stats :
            plt.title(label=title_stats, fontsize = 16)
        plt.legend(handles=[legend_patch], loc='best', fontsize =16)
        plt.show()
    except (AttributeError, ValueError) as e: 
        print(e)
        if "max() arg is an empty sequence" in str(e):
            print("It is possible that the distance of the buffer is too high, no buildings left and no shapefile to display. ")

def generate_irradiation_csv_file(path_buildings_zonal_stats, column_name, path_final_output_folder):     
    """Generate a csv file with data coming from a shapefile contained in a column named ``column_name``. 
    
    The na value are filled with 0.
    It is made to generate a csv file with irradiation value (annual irradiation received by building footprints).

    Parameters
    ----------
    path_buildings_zonal_stats : pathlib.Path
        path of the shapefile containing the data (zonal statistics for example) to export in a csv file (path_buildings_buffer_zonal_stat_post_process obtained in `_post_process_buffer_zonal_stat` for example)
    column_name : str
        name of the column in the shapefile containing the values to export (sol_mean for example)
    path_final_output_folder : pathlib.Path
        path of the folder where to save the final results (define in main function)

    Returns
    -------
    path_irradiation_csv : pathlib.Path
        path of the csv file with data exported from the shapefile 

    Raises
    ------
    AttributeError
        name of the column (``column_name``) not found in the dataframe
        if ``column_name`` is too long (>10 characters), the name was probably shortened before saving
    """
    buildings_zonal_stats = read_file(str(path_buildings_zonal_stats))

    if column_name not in buildings_zonal_stats.columns:
        if len(column_name)>10 : 
            raise AttributeError(f"No column named '{column_name}' found in the dataframe. Name too long and has probably been shortened before saving the shapefile") 
        else : 
            raise AttributeError(f"No column named '{column_name}' found in the dataframe.")
            

    buildings_zonal_stats[column_name].fillna(0, inplace=True)
    data = buildings_zonal_stats[column_name]
    path_irradiation_csv= path_final_output_folder / "irradiation_csv.csv"
    data.to_csv(str(path_irradiation_csv))
    return path_irradiation_csv


def display_histogram(data, nb_bins,x ,fitting_parameters,R2, path_final_output_folder, bool_johnsonsu = True, save_plot = True, name_plot = "Distribution_irradiation.png", bool_title_histo = False, title_histo = "Distribution of average annual rooftop irradiation"):    
    """Display the histogram with optionally the Johnson's SU distribution fitted to the distribution (default : True) (inputs coming from `calculate_histogram_and_johnsonsu_fit`)
    
    The figure is saved in an output folder. 

    Parameters
    ----------
    data : DataFrame
        dataframe with irradiation values
    nb_bins : int
        number of bins in the histogram
    x : list
        list of the x value used to display the Johnson's SU distribution
    fitting_parameters : tuple
        float tuple with the fitting parameters of the Johnson's SU distribution (a,b,c,d), c is the location parameter and d is the scale parameter
    R2 : float
        best R2 coefficient between classic (init) or floc=xmax (xmax) methods
    path_final_output_folder : pathlib.Path
        path of the folder where to save the final results (define in main function)
    bool_johnsonsu : bool, optional
        boolean value to display or not the Johnson's SU fitted distribution, by default True
    save_plot : bool, optional
        boolean value to save or not a figure with the distribution, by default True
    name_plot : str, optional
        name of the file saved with the figure of the distribution, by default "Distribution_irradiation.png"
    bool_title_histo : bool, optional
        boolean value to display or not the title, by default False
    title_histo : str, optional
        title of the figure, by default "Distribution of average annual rooftop irradiation"
    """    
    cmap = plt.get_cmap('tab20')
    num_colors = 20
    colors = [cmap(i) for i in linspace(0,1,num_colors)]
    fig, ax = plt.subplots(figsize=(6,5))
    font = {'size':16}
    plt.rc('font', **font)
    color = colors[1]
    label =f"Real distribution"
    plt.hist(data,bins=nb_bins,density=True, label=label, alpha=1, color=color)
    a,b,c,d = fitting_parameters
    pdf = johnsonsu.pdf(x, a,b,c,d)
    color = colors[0]
    if bool_johnsonsu == True : 
        plt.plot(x, pdf, label=f"Johnson's S$_U$ PDF-\nR²={R2:.2f}", color=color, linewidth = 2)
    ax.legend( loc='upper left')
    plt.xlabel('Irradiation (kWh/m²)', fontdict=font)
    plt.ylabel('Probability', fontdict=font)
    ax.tick_params(axis='both', labelsize=font['size'])
    plt.grid(True, linestyle=':', linewidth=0.5)
    if bool_title_histo : 
        plt.title(title_histo, fontdict = font)
    plt.tight_layout()
    path_plot_save = path_final_output_folder / name_plot
    if save_plot : 
        plt.savefig(str(path_plot_save))
    plt.show()

def display_distribution(path_buildings_zonal_stats, column_name, path_final_output_folder, bool_johnsonsu = True, save_plot = True, name_plot = "Distribution_irradiation.png",  bool_title_histo =False, title_histo = "Distribution of average annual rooftop irradiation"): 
    """Display in a figure the histogram of a feature with values included in a shapefile (in the column named ``column_name``), with optionally the Johnson's SU fitted distribution (default : True).
    
    It is made to display the average annual irradiation received per building rooftop.
    The values are first stored in a csv file, then histogram and the Johnson's SU fit are calculated. Then, the histogram is displayed.

    Parameters
    ----------
    path_buildings_zonal_stats : pathlib.Path
        path of the shapefile containing the data (zonal statistics for example) to display in a histogram (path_buildings_buffer_zonal_stat_post_process obtained in `_post_process_buffer_zonal_stat` for example)
    column_name : str
        name of the column in the shapefile containing the values to display in the histogram (sol_mean for example)
    path_final_output_folder : pathlib.Path
        path of the folder where to save the final results (define in main function)
    bool_johnsonsu : bool, optional
        boolean value to display or not the Johnson's SU fitted distribution, by default True
    save_plot : bool, optional
        boolean value to save or not a figure with the distribution, by default True
    name_plot : str, optional
        name of the file saved with the figure of the distribution, by default "Distribution_irradiation.png
    bool_title_histo : bool, optional
        boolean value to display or not the title, by default False
    title_histo : str, optional
        title of the figure, by default "Distribution of average annual rooftop irradiation"
    """
    try :  
        path_irradiation_csv= generate_irradiation_csv_file(path_buildings_zonal_stats, column_name, path_final_output_folder)
        data, nb_bins, fitting_parameters,x, R2, R2_init, R2_xmax, method = calculate_histogram_and_johnsonsu_fit(path_irradiation_csv, bool_buffer =True)
        display_histogram(data,nb_bins,x,fitting_parameters,R2, path_final_output_folder, bool_johnsonsu = bool_johnsonsu, save_plot= save_plot, name_plot=name_plot, bool_title_histo=bool_title_histo, title_histo=title_histo)

    except (AttributeError, ValueError, TypeError) as e: 
        print(e)
        if "cannot unpack non-iterable NoneType object" in str(e): 
            print("It is possible that the distance of the buffer is too high, no buildings left. The histogram can not be calculated and displayed.")

def display_results(path_raster_files, path_final_output_folder, rectangle_elevation = True, rectangle_SEBE = False, bool_johnsonsu = True, column_prefix = "sol_",
                    statistics ='mean', save_plot = True, name_plot = "Distribution_irradiation.png", bool_title_histo =False, title_histo = "Distribution of average \nannual rooftop irradiation",
                    bool_title_elevation= False, title_elevation= "Map of the municipality's elevation", bool_title_SEBE = False, title_SEBE = f"Map of the municipality's average \nannual irradiation on surfaces", 
                    bool_title_stats = False, title_stats = f"Map of the municipality's average annual rooftop\nirradiation per building", label_stats = "Irradiation (kWh/m²)"):
    """Display the results : the resample DSM of the village, the raster with SEBE results, the shapefile with building footprints (with buffer) and their average annual irradiation on rooftops and the histogram with the average annual irradiation received by rooftops and the associated Johnson's SU fitted distribution. 

    Parameters
    ----------
    path_raster_files : pathlib.Path
        path of the folder with temporary raster files (define in main function)
    path_final_output_folder : pathlib.Path
        path of the folder with the final results (define in main function)
    rectangle_elevation : bool, optional
        boolean value to display or not the borders of the elevation file (recommended to set to False if the raster is a raster coming from `clip_raster` function), by default True
    rectangle_SEBE : bool, optional
        boolean value to display or not the borders of the merge SEBE raster (recommended to set to False if the raster is a raster coming from `clip_raster` function), by default False
    bool_johnsonsu : bool, optional
        boolean value to display or not the Johnson's SU fitted distribution, by default True
    column_prefix : str, optional
        prefix of the column that have been chosen to create the statistics, by default 'sol\_'
    statistics : str, optional
        name of the suffix of the column to display, by default 'mean'
    save_plot : bool, optional
        boolean value to save or not a figure with the distribution, by default True
    name_plot : str, optional
        name of the file saved with the figure of the distribution, by default "Distribution_irradiation.png
    bool_title_histo : bool, optional
        boolean value to display or not the title, by default False
    title_histo : str, optional
        title of the figure, by default "Distribution of average annual rooftop irradiation"
    bool_title_elevation : bool, optional
        boolean value to display or not the title, by default False
    title_elevation : str, optional
        title of the figure, by default "Map of the municipality's elevation"
    bool_title_SEBE : bool, optional
        boolean value to display or not the title, by default False
    title_SEBE : _type_, optional
        title of the figure, by default f"Map of the municipality's average \nannual irradiation on surfaces"
    bool_title_stats : bool, optional
        boolean value to display or not the title, by default False
    title_stats : _type_, optional
        title of the figure, by default f"Map of the municipality's average annual rooftop\nirradiation per building"
    label_stats : str, optional
        lalbel of the colorbar, by default "Irradiation (kWh/m²)"
    """
    solar_prefix = column_prefix
    path_DSM = path_raster_files / "DSM.tif"
    path_merge_SEBE_raster= path_final_output_folder / "merge_annual_solar_energy_clip_municipality_extent.tif"
    path_buffer_buildings_zonal_stats = path_final_output_folder / "buildings_zonal_stats_solar.shp"
    display_elevation_file(path_DSM, rectangle=rectangle_elevation, bool_title_elevation=bool_title_elevation, title_elevation=title_elevation)
    display_SEBE_raster(path_merge_SEBE_raster, rectangle= rectangle_SEBE, bool_title_SEBE=bool_title_SEBE, title_SEBE=title_SEBE)
    column_name = solar_prefix + statistics
    display_zonal_stat_shapefile(path_buffer_buildings_zonal_stats, column_name, bool_title_stats=bool_title_stats, title_stats=title_stats, label_stats=label_stats)
    display_distribution(path_buffer_buildings_zonal_stats, column_name, path_final_output_folder, bool_johnsonsu= bool_johnsonsu, save_plot=save_plot, name_plot=name_plot, bool_title_histo=bool_title_histo, title_histo=title_histo)


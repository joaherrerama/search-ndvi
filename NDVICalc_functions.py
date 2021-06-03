import satsearch
import datetime as date
from dateutil.relativedelta import *
import json
import numpy as np
import rasterio as rio
import time
import intake
from pyproj import Proj, transform

def data_requesting_Element84(geojson,cloud): 
 
    """
        This function send the parametes and geomtry to the STAC API and retrieve all available datasets
        that are suitable based on the inputs (geometry,cloud) provided by the user.
    """
    now = date.datetime.now()
    last_month = now+relativedelta(months=-1)
    dates = str(last_month.strftime("%Y-%m-%d")) + '/' + str(now.strftime("%Y-%m-%d"))

    URL='https://earth-search.aws.element84.com/v0'
    results = satsearch.Search.search(url=URL,
                                    collections=['sentinel-s2-l2a-cogs'], # note collection='sentinel-s2-l2a-cogs' doesn't work
                                    datetime=dates,
                                    intersects=geojson,
                                    query={
                                        'eo:cloud_cover': {'lt': cloud},
                                        'sentinel:data_coverage':{'gt': 70}
                                    }
    )

    items = results.items()
    if(results.found() == 0):
        items = 'No Data Available'
    # Save this locally for use later
    items.save('default/temp/my-s2-l2a-cogs.json')
    return items

def load_geojson(url):
    try:
        with open(url) as f:
            features = json.load(f)['features']
            print("[INFO] The Geojson has ", len(features)," feature(s)")
            return features
    except:
        print("[ERROR] The Geojson file seems to be corrupted. Check the structure please")

def transform_geometry(geometry,crs):
    inProj = Proj('EPSG:4326')
    outProj = Proj(crs)
    print(inProj,outProj)
    g = json.dumps(geometry)
    geometry_json = json.loads(g)

    feature_out = geometry_json.copy()
    new_coords = []

    #all coordinates
    coords = feature_out['coordinates']

    #coordList is for each individual polygon
    for coordList in coords:

        #each point in list
        for coordPair in coordList:
            x1 = coordPair[1]
            y1 = coordPair[0]
            lat_grid, lon_grid = x1, y1
            #do transformation
            coordPair[0],coordPair[1] = transform(inProj,outProj,lat_grid, lon_grid)

    return feature_out

def NDVI_single_scene(items,geometry):
    """
        This function calculate NDVI statistics for a single scene
        Input:
            - items: catalog of images found on the previous step
            - geometry: Single Feature from Geojson file 
    """

    src = rio.open(items[0].asset("red")["href"]).crs
    all_bounds = transform_geometry(geometry,src)
    all_bound = [all_bounds]
    try:
        # Read and open(B4 and B8)
        with rio.open(items[0].asset("red")["href"]) as src:
            b4_cropped, b4_transform = rio.mask.mask(src,all_bound, crop=True)

        with rio.open(items[0].asset("nir")["href"]) as src:
            b8_cropped, b8_transform = rio.mask.mask(src,all_bound, crop=True)
    
        red = b4_cropped
        nir = b8_cropped

        # Calculate ndvi
        ndvi = (nir-red)/(nir+red)

        return ndvi

    except:
        print("[ERROR] Please validate that the GEOJSON is in WGS84: Coordinates must be sorted -> [Longitude, Latitude]. ")

def NDVI_multiple_scenes(items):
    """
        This function intend to  calculate NDVI statistics for time series dataset
        Input:
            - items
    """
    stats = {}
    catalog = intake.open_stac_item_collection(items)
    latest = str(list(catalog)[0])
    item = catalog[latest]

    # stack_bands() method should be identical to landsat
    bands = ['nir','red']
    stack = item.stack_bands(bands)

    # currently need to specify chunks:
    da = stack(chunks=dict(band=1, x=2048, y=2048)).to_dask()

    # Reorganize into xarray DataSet with common band names
    da['band'] = bands
    ds = da.to_dataset(dim='band')

    # Calculate NDVI
    NDVI = (ds['nir'] - ds['red']) / (ds['nir'] + ds['red'])
    print(np.nanmean(NDVI.mean(dim=['x', 'y']).values))

    return stats

def calculate_stats(stats,ndvi):
    """
        The funtion calculate the statistcs based on parameter -stat provided by the user
        options:
            - mean
            - median
            - mode
            - max
            - min
            - std
    """
    stat = {}
    for i in stats:
        #print("[INFO] Calculating", i)

        if(i == 'mean'):
            print("[INDEX] Calculating", i)
            r = np.nanmean(ndvi)
        elif(i == 'median'):
            print("[INDEX] Calculating", i)
            r = np.nanmedian(ndvi)
        elif(i == 'mode'):
            print("[INDEX] Calculating", i)
            vals,counts = np.unique(ndvi, return_counts=True)
            r = vals[np.argmax(counts)]
            #r = st.mode(ndvi,nan_policy ="omit")[0] # CHECK THE FUNCTION
        elif(i == 'max'):
            print("[INDEX] Calculating", i)
            r = np.nanmax(ndvi)
        elif(i == 'min'):
            print("[INDEX] Calculating", i)
            r = np.nanmin(ndvi)
        elif(i == 'std'):
            print("[INDEX] Calculating", i)
            r =np.nanstd(ndvi)

        stat[i] = r
    
    print(stat)
    
    return stat


def calculation(cloud,stats,path):
    """
        This function present the general workflow for all the calculation
        Geojson loading  -> data acquisition -> NDVI calculation -> Results
    """
    # Starting time (measure time performing)
    start = time.time()
    result_list = {}
    geojson = load_geojson(path)

    #  Calculating NDVI and stats for each feature from the GEOJSON
    for i in range(len(geojson)):

        print("[STEP] Data acquisition process -> feature ", i )
        
        items = data_requesting_Element84(geojson[i]['geometry'],cloud)  

        if(items != 'No Data Available'):

            print("[STEP] NDVI Calculation process -> feature ", i)
            try:
                NDVI = NDVI_single_scene(items,geojson[i]['geometry'])
            except:
                 print("[ERROR] Something went wrong, please check the messages above ")
                 break

            print("[STEP] Statistics calculation process -> feature ", i)
            
            try:
                result = calculate_stats(stats,NDVI)
            
                catalog = intake.open_stac_item_collection(items)
                latest = str(list(catalog)[0])
                result_list[i] = {latest: result}
            except:
                 print("[ERROR] Something went wrong, please check the messages above ")
                 break
        else:
            result_list[i] = {"ERROR": "NO DATA AVAILABLE"}

    print("[RESULT] The statistics calculated from NDVI Scene(s) are:")
    print(result_list)
    end = time.time()
    print("[TIME] Time of execution was (seconds): ", end - start)


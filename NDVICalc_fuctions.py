import satsearch
import datetime as date
from dateutil.relativedelta import *
import json
import numpy as np
import matplotlib.pyplot as plt
import rasterio as rio
import time
import intake
from scipy import stats as st


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

def NDVI_single_scene(items):
    """
        This fuction calculate NDVI statistics for a single scene
        Input:
            - items
    """
    # Read and open(B4 and B8)
    b4 = rio.open(items[0].asset("red")["href"])
    b8 = rio.open(items[0].asset("nir")["href"])
    red = b4.read()
    nir = b8.read()

    # Calculate ndvi
    ndvi = (nir.astype(float)-red.astype(float))/(nir+red)

    return ndvi

def NDVI_multiple_scenes(items):

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
            - mean:
            - median:
            - mode
            - max
            - min
            - std
    """
    stat = {}
    for i in stats:
        
        result = {
        'mean': np.nanmean(ndvi),
        'median': np.nanmedian(ndvi),
        'mode': st.mode(ndvi),
        'max': np.nanmax(ndvi),
        'min': np.nanmin(ndvi),
        'std': np.nanstd(ndvi)
        }[i]

        stat[i] = result
    
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
        
        print("[STEP] NDVI Calculation process -> feature ", i)

        NDVI = NDVI_single_scene(items)

        print("[STEP] Statistics calculation process -> feature ", i)

        result = calculate_stats(stats,NDVI)

        catalog = intake.open_stac_item_collection(items)
        latest = str(list(catalog)[0])
        result_list[i] = {latest: result}

    print("[RESULT] The statistics calculated from NDVI Scene(s) are:")
    print(result_list)
    end = time.time()
    print("[TIME] Time of excecution was (seconds): ", end - start)


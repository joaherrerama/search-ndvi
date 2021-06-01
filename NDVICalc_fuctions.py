import intake
import satsearch
import datetime as date 
import json
import numpy as np
import matplotlib.pyplot as plt
import rasterio as rio
from rasterio.plot import show
import time



def data_requestion_Element84(geojson):  

    now = date.datetime.now()
    print(now)
    dates = '2018-02-01/2018-12-04'


    URL='https://earth-search.aws.element84.com/v0'
    results = satsearch.Search.search(url=URL,
                                    collections=['sentinel-s2-l2a-cogs'], # note collection='sentinel-s2-l2a-cogs' doesn't work
                                    datetime=dates,
                                    intersects=geojson,
                                    query={
                                        'eo:cloud_cover': {'lt': 10},
                                        'sentinel:data_coverage':{'gt': 50}
                                    }
    )

    print('%s items' % results.found())
    items = results.items()
    # Save this locally for use later
    items.save('my-s2-l2a-cogs.json')
    return items

def load_geojson(url='default/geometry/geometry.geojson'):
    with open(url) as f:
        return json.load(f)['features'][0]['geometry']

def NDVI_single_scene(items):
    """
        This fuction calculate NDVI statistics for a single scene
        Input:
            - items
    """
    stats = {}

    # Read and open(B4 and B8)
    b4 = rio.open(items[0].asset("red")["href"])
    b8 = rio.open(items[0].asset("nir")["href"])
    red = b4.read()
    nir = b8.read()

    # Calculate ndvi
    ndvi = (nir.astype(float)-red.astype(float))/(nir+red)


    print(np.nanmean(ndvi))

    return stats

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

def calculation():
    start = time.time()

    geojson = load_geojson()

    items = data_requestion_Element84(geojson)  

    result = NDVI_single_scene(items)

    print("[INFO] The statistics calculated from NDVI Scene(s) are:")
    print(result)
    print("[INFO] Time of excecution was (seconds):")
    end = time.time()
    print(end - start)


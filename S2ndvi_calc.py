#!/usr/bin/env python
import os
import argparse
import NDVICalc_fuctions as ndvi

def main(command_line=None):
    parser = argparse.ArgumentParser('Sentinel 2: NDVI Calculation')

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print debug info'
    )

    subprasers = parser.add_subparsers(dest='command')

    # Average NDVI Calculation on latest date (Scene)

    latest = subprasers.add_parser('latest', help='calculate the average NDVI based on a latest scene available')
    latest.add_argument(
        '-cloudperc',
        help='Percentage of cloud cover in the scene (optional)',
        default= 100,
        type=int,
        nargs='?'
    )

    latest.add_argument(
        '-stats',
        help='descriptors to calculate (mean, median, mode, max, min, std) default -> [mean,mode,std] (optional)',
        default= ['mean','mode','std'],
        choices=['mean', 'median', 'mode', 'max', 'min', 'std'],
        nargs='+'
    )

    latest.add_argument(
        '-geometry',
        help='Study Area to analyse in GEOJSON format (optional)',
        type=str,
        default="./default/geometry/geometry.geojson",
        nargs='?'
    )

    # Average NDVI Calculation on user-defined dates (Scenes)
    dates = subprasers.add_parser('dates', help='calculate the average NDVI based on user-defined dates and scenes available')

    args = parser.parse_args(command_line)

    if args.debug:
        print("debug: " + str(args))
    if args.command == 'latest':

        while True:
            if(os.path.isfile(args.geometry) and args.geometry.endswith(".geojson") ):
                print("[INFO] Geojson path validated")
            else:
                print("[ERROR] Please check the path given")
                break
            
            if(args.cloudperc >= 0 and args.cloudperc <= 100):
                print("[INFO] Cloud Percentage validated")
            else:
                print("[ERROR] Cloud Percentage Parameter must be from 0 to 100")
                break
            print("[INFO] NDVI calculation running ...")
            ndvi.calculation(args.cloudperc,args.stats,args.geometry)
            break

    elif args.command == 'dates':
        print('Still on development')


if __name__ == '__main__':
    main()


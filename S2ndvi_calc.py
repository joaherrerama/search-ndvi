#!/usr/bin/env python
import argparse
import NDVICalc_fuctions as ndvi

def main(command_line=None):
    parser = argparse.ArgumentParser('NDVI Calculation')

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Print debug info'
    )

    subprasers = parser.add_subparsers(dest='command')

    # Average NDVI Calculation on latest date (Scene)

    latest = subprasers.add_parser('latest', help='calculate the average NDVI based on a latest scene available')
    latest.add_argument(
        'geometry',
        help='Study Area to analyse in GEOJSON format (optional)',
        default="Döberitzer Heide Nature Reserve",
        nargs='?'
    )
    latest.add_argument(
        'cloud-coverage',
        help='Percentage of cloud cover in the scene (optional)',
        default="100",
        nargs='?'
    )
    latest.add_argument(
        'descriptors',
        help='what to praise for (optional)',
        default="no reason",
        nargs='?'
    )

    # Average NDVI Calculation on user-defined dates (Scenes)
    dates = subprasers.add_parser('dates', help='calculate the average NDVI based on user-defined dates and scenes available')

    args = parser.parse_args(command_line)

    if args.debug:
        print("debug: " + str(args))
    if args.command == 'latest':
        ndvi.calculation()
    elif args.command == 'dates':
        print('Still in development')


if __name__ == '__main__':
    main()


import argparse
import datetime
import logging
import traceback
from multiprocessing import Process

from viscalmon.dpol_monitoring.algos import offsets, phidp0, zdr90, zdr_rain, zdr_rings
from viscalmon.general.io.radar import get_files_names, open_rainbow_xarray

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)





def job_vertical(begin : datetime.datetime, end : datetime.datetime, radar : str) -> None:
    logger.info("Vertical job.")

    logger.info("Getting file names.")
    files = get_files_names("azi:ZDR,RhoHV,dBZ", begin, end, radar)

    logger.info("Opening files.")
    data, _, _, alt = open_rainbow_xarray(files)

    if alt is None:
        logger.error("Missing altitude.")
        raise ValueError("alt is None.")
    else:
        alt = float(alt)

    zdr90(radar, begin.date(), data, alt)

    logger.info("End vertical job.")






def job_volume(begin : datetime.datetime, end : datetime.datetime, radar : str) -> None:
    logger.info("Volume job.")

    logger.info("Getting file names.")
    files = get_files_names("vol:uPhiDP,ZDR,RhoHV,dBZ", begin, end, radar)

    logger.info("Opening files.")
    data, _, _, alt = open_rainbow_xarray(files)

    if alt is None:
        logger.error("Missing altitude.")
        raise ValueError("alt is None.")
    else:
        alt = float(alt)

    
    
    # In parallel
    p_offsets = Process(target=offsets, args=(radar, begin.date(), [ file for file in files if "ZDR" in file ], [ file for file in files if "uPhiDP" in file ]))
    p_phidp0 = Process(target=phidp0, args=(radar, begin.date(), data))
    p_zdr_rain = Process(target=zdr_rain, args=(radar, begin.date(), data, alt))
    p_zdr_rings = Process(target=zdr_rings, args=(radar, begin.date(), data))

    p_offsets.start()
    p_phidp0.start()
    p_zdr_rain.start()
    p_zdr_rings.start()

    p_offsets.join()
    p_phidp0.join()
    p_zdr_rain.join()
    p_zdr_rings.join()

    logger.info("End volume job.")





def main():

    logger.info("Starting.")
    
    # Parse arguments
    parser = argparse.ArgumentParser()

    parser.add_argument("radar", choices=["jabbeke", "wideumont"], help="the radar to run the monitoring scripts on")
    parser.add_argument("begin_date", help="begin date or month concerned, format YYYYMMDD")
    parser.add_argument("end_date", help="begin date or month concerned, format YYYYMMDD", nargs="?")

    args = parser.parse_args()
    logger.debug(f"Parsed args: {args}.")
    


    # Parse dates
    begin_date = datetime.date.strptime(args.begin_date, "%Y%m%d")

    if args.end_date is None:
        end_date = begin_date
    else:
        end_date = datetime.date.strptime(args.end_date, "%Y%m%d")
        if end_date < begin_date:
            raise ValueError("end_date should be greater than begin_date.")
    
    logger.debug(f"Period : {begin_date} -> {end_date}")
    


    date = begin_date
    while date <= end_date:
        logger.info(f"Processing day {date}.")

        try:
            begin = datetime.datetime(date.year, date.month, date.day, tzinfo=datetime.timezone.utc)
            end = datetime.datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=datetime.timezone.utc)
            
            # In parallel
            p_vertical = Process(target=job_vertical, args=(begin, end, args.radar))
            p_volume = Process(target=job_volume, args=(begin, end, args.radar))
            
            p_vertical.start()
            p_volume.start()

            p_vertical.join()
            p_volume.join()
            
        except Exception:
            logger.error(f"Error in compare_r_r_daily. Skipping day {date}.\n{traceback.format_exc()}")

        date += datetime.timedelta(days=1)





if __name__=="__main__":
    main()
import datetime
import logging

from viscalmon.general.io.radar import get_files_names
from viscalmon.general.io.utils import (
    acc_time_from_product_name,
    scale_from_product_name,
    software_from_product_name,
)

# Configure logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

handler = logging.StreamHandler()
handler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(funcName)s - %(message)s')

handler.setFormatter(formatter)

logger.addHandler(handler)





def get_and_filter_files_names(product_name : str, begin_timestamp : datetime.datetime, end_timestamp : datetime.datetime, \
                                radar : str | None = None) -> list[str]:
    """
        Get radar files names for a specified product between two timestamps and filter them for removing non-necessary files:
        - for accumulation times such as 10 min / 1 hour : only keep multiples of that acccumulation time
        - for RADQPE composite 1-day accumulations : only keep 8am l.t. - 8am l.t. file

        Parameters
        ----------
        product_name : str
            See `viscalmon.general.io.radar.get_files_names`.
        
        begin_timestamp : datetime.datetime
            Begin timestamp.

        end_timestamp : datetime.datetime
            Begin timestamp.
        
        radar : str, optional
            See `viscalmon.general.io.radar.get_files_names`.
        
        Returns
        -------
        list of str
            Files names.
    """

    acc_time = acc_time_from_product_name(product_name)
    software = software_from_product_name(product_name)
    
    if acc_time == datetime.timedelta(days=1) and software == "radqpe2" and scale_from_product_name(product_name) == "composite":
        logger.debug("Identified as RADQPE2 1-day composite. Keep 8am l.t. hours.")
        return get_files_names(product_name, begin_timestamp, end_timestamp, radar, [0], [8])
    
    elif acc_time != datetime.timedelta(0) and acc_time!=datetime.timedelta(days=1):
        logger.debug("Identified as accumulation not equal to 1 day.")
        acc_time_minutes = int(acc_time.seconds / 60)
        minutes_to_keep = list(range(0, 60, acc_time_minutes))
        logger.debug(f"Keep minutes {minutes_to_keep}")
        return get_files_names(product_name, begin_timestamp, end_timestamp, radar, minutes_to_keep)
    
    else:
        logger.debug("Identified as other. Keep all.")
        return get_files_names(product_name, begin_timestamp, end_timestamp, radar)
import datetime
from typing import Literal


def acc_time_from_product_name(product_name : str) -> datetime.timedelta:
    """
        Tells the accumulation time of the product.

        Extracts and parses the last part of the name.

        Parameters
        ----------
        product_name : str
            Name of the product (internal to this app).
            See `constants.GAUGE_PRODUCTS_TYPES` and `viscalmon.general.io.constants.RADAR_PRODUCTS_TYPES`.
        
        Returns
        -------
        datetime.timedelta
            Accumulation time.
        
        Raises
        ------
        ValueError
            If the product name has the wrong format.
    """

    if product_name[:3] == "vol" or product_name[:3] == "azi":
        return datetime.timedelta()
    
    parts = product_name.split("_")

    if len(parts) < 1:
        raise ValueError("Wrong name format.")

    last_part = parts[-1]
    if last_part == "rr":
        return datetime.timedelta()
    elif last_part == "5m":
        return datetime.timedelta(minutes=5)
    elif last_part == "10m":
        return datetime.timedelta(minutes=10)
    elif last_part == "1h":
        return datetime.timedelta(hours=1)
    elif last_part == "1d":
        return datetime.timedelta(days=1)
    else:
        raise ValueError("Wrong name format.")





def scale_from_product_name(product_name : str) -> Literal["single", "composite"]:
    """
        Tells the scale of the product : single-radar or composite.

        Extracts and parses the second part of the name.

        Parameters
        ----------
        product_name : str
            Name of the product (internal to this app).
            See `constants.RADAR_PRODUCTS_TYPES`.
        
        Returns
        -------
        {'single', 'composite'}
            If the product corresponds to a single radar or to a composite.
        
        Raises
        ------
        ValueError
            If the product name has the wrong format.
    """

    if product_name[:3] == "vol" or product_name[:3] == "azi":
        return "single"
    
    parts = product_name.split("_")

    if len(parts) < 2:
        raise ValueError("Wrong name format.")

    second_part = parts[1]
    if second_part == "single":
        return "single"
    elif second_part == "comp":
        return "composite"
    else:
        raise ValueError("Wrong name format.")





def software_from_product_name(product_name : str) -> Literal["rainbow", "radqpe2"]:
    """
        Tells the software that produced the product.

        Extracts and parses the first part of the name.

        Parameters
        ----------
        product_name : str
            Name of the product (internal to this app).
            See `constants.RADAR_PRODUCTS_TYPES`.
        
        Returns
        -------
        {'rainbow', 'radqpe2'}
            Software name.
        
        Raises
        ------
        ValueError
            If the product name has the wrong format.
    """

    if product_name[:3] == "vol" or product_name[:3] == "azi":
        return "rainbow"
    
    parts = product_name.split("_")

    if len(parts) < 1:
        raise ValueError("Wrong name format.")

    second_part = parts[0]
    if second_part == "rainbow":
        return "rainbow"
    elif second_part == "radqpe2":
        return "radqpe2"
    else:
        raise ValueError("Wrong name format.")





def full_radar_name_to_short(radar : str) -> str:
    """
        Converts full radar name to short with country prefix.

        Parameters
        ----------
        radar : {'wideumont', 'jabbeke', 'helchteren', 'avesnois'}
            Full radar name.

        Returns
        -------
        str
            Short radar name.

        Raises
        ------
        ValueError
            If the radar name is unknown.

    """

    match radar:
        case "wideumont":
            return "bewid"
        case "jabbeke":
            return "bejab"
        case "helchteren":
            return "behel"
        case "avesnois":
            return "frave"
        case _:
            raise ValueError("Radar name unknown.")





def product_archive_folder(product_name : str, date : datetime.date, radar : str | None = None) -> str:
    """
        Gives the archive folder name associated to a product, a date and eventually a radar.

        Parameters
        ----------
        product_name : str
            Product name (internal to this app).
            See `constants.RADAR_PRODUCTS_TYPES`.
        
        date : datetime.date
            Date.
        
        radar : {'wideumont', 'jabbeke', 'helchteren', 'avesnois'}, optional
            Full radar name.

        Returns
        -------
        str
            Folder name.

        Raises
        ------
        ValueError
            If the product or radar name is unknown.

    """

    base_rainbow = f"/mnt/HDS_ERS/archive/{date.strftime('%Y/%m/%d')}/radar/"
    base_radqpe2 = f"/mnt/HDS_RADQPE2/RADQPE2/archive/{date.strftime('%Y/%m/%d')}/"

    if scale_from_product_name(product_name) == "single" and radar is None:
        raise ValueError("Missing radar specification.")
    if radar is None:
        radar = ""
    
    match product_name:
        case "rainbow_single_rr":
            return base_rainbow + f"single/{radar}/rate/*/bin/"
        case "rainbow_comp_beborder_rr":
            return base_rainbow + "composite/belradcomp/sri/beborder00/bin/"
        case "rainbow_comp_be_rr":
            return base_rainbow + "composite/belradcomp/sri/becomp00/bin/"
        case "rainbow_single_1h":
            return base_rainbow + f"single/{radar}/acrr/acrr_1h*/bin/"
        case "rainbow_single_1d":
            return base_rainbow + f"single/{radar}/acrr/acrr_24h*/bin/"
        case "rainbow_comp_10m":
            return base_rainbow + "composite/belradcomp/acrr/acrr_10min/bin/"
        case "rainbow_comp_1h":
            return base_rainbow + "composite/belradcomp/acrr/acrr_1hr/bin/"
        case "radqpe2_single_rr":
            return base_radqpe2 + f"{full_radar_name_to_short(radar)}/image/rate/qpe/hdf/"
        case "radqpe2_comp_rr":
            return base_radqpe2 + "best/comp/rate/qpe/hdf/"
        case "radqpe2_comp_edk_rr":
            return base_radqpe2 + "best/comp/rate/qpe_edk/hdf/"
        case "radqpe2_comp_mfb_rr":
            return base_radqpe2 + "best/comp/rate/qpe_mfb/hdf/"
        case "radqpe2_single_5m":
            return base_radqpe2 + f"{full_radar_name_to_short(radar)}/image/acrr/qpe_5m/hdf/"
        case "radqpe2_single_10m":
            return base_radqpe2 + f"{full_radar_name_to_short(radar)}/image/acrr/qpe_10m/hdf/"
        case "radqpe2_single_1h":
            return base_radqpe2 + f"{full_radar_name_to_short(radar)}/image/acrr/qpe_1h/hdf/"
        case "radqpe2_single_1d":
            return base_radqpe2 + f"{full_radar_name_to_short(radar)}/image/acrr/qpe_1d/hdf/"
        case "radqpe2_single_mfb_1d":
            return base_radqpe2 + f"{full_radar_name_to_short(radar)}/image/acrr/qpe_mfb_1d/hdf/"
        case "radqpe2_comp_5m":
            return base_radqpe2 + "best/comp/acrr/qpe_5m/hdf/"
        case "radqpe2_comp_10m":
            return base_radqpe2 + "best/comp/acrr/qpe_10m/hdf/"
        case "radqpe2_comp_1h":
            return base_radqpe2 + "best/comp/acrr/qpe_1h/hdf/"
        case "radqpe2_comp_1d":
            return base_radqpe2 + "best/comp/acrr/qpe_1d/hdf/"
        case "radqpe2_comp_edk_5m":
            return base_radqpe2 + "best/comp/acrr/qpe_edk_5m/hdf/"
        case "radqpe2_comp_edk_10m":
            return base_radqpe2 + "best/comp/acrr/qpe_edk_10m/hdf/"
        case "radqpe2_comp_edk_1h":
            return base_radqpe2 + "best/comp/acrr/qpe_edk_1h/hdf/"
        case "radqpe2_comp_edk_1d":
            return base_radqpe2 + "best/comp/acrr/qpe_edk_1d/hdf/"
        case "radqpe2_comp_mfb_5m":
            return base_radqpe2 + "best/comp/acrr/qpe_mfb_5m/hdf/"
        case "radqpe2_comp_mfb_10m":
            return base_radqpe2 + "best/comp/acrr/qpe_mfb_10m/hdf/"
        case "radqpe2_comp_mfb_1h":
            return base_radqpe2 + "best/comp/acrr/qpe_mfb_1h/hdf/"
        case "radqpe2_comp_mfb_1d":
            return base_radqpe2 + "best/comp/acrr/qpe_mfb_1d/hdf/"
        case product_name if product_name[:3] == "azi":
            match radar:
                case "wideumont" | "jabbeke":
                    return base_rainbow + f"single/{radar}/azi/*/bin/"
                case _:
                    raise ValueError("No data available for this radar.")
        case product_name if product_name[:3] == "vol":
            match radar:
                case "wideumont" | "jabbeke":
                    return base_rainbow + f"single/{radar}/vol/{full_radar_name_to_short(radar)}_scan_v3_Z/bin/"
                case _:
                    return base_rainbow + f"single/{radar}/vol/*/bin/"
        case _:
            raise ValueError("Wrong product name.")
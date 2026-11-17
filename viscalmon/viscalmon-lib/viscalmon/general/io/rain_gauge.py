import datetime

import oracledb
import pyarrow
from dateutil import tz

TABLES = {
    "aws_10m" : "AWS_10MIN",
    "aws_1h" : "AWS_1HOUR",
    "aws_clim_10m" : "AWS_CLIM_10MIN",
    "hic_5m" : "HIC_PRECIP_5MIN",
    "hic_1h" : "HIC_PRECIP_1HOUR",
    "obs_1d" : "PRECIPITATION",
    "spw_5m" : "SETHY_PRECIP_5MIN",
    "spw_1h" : "SETHY_PRECIP",
    "vmm_10m" : "VMM_PRECIP_10MIN",
    "vmm_5m" : "VMM_PRECIP_5MIN"
}

STATIONS_TABLES = {
    "aws_10m" : "AWS_STATION",
    "aws_1h" : "AWS_STATION",
    "aws_clim_10m" : "AWS_STATION",
    "hic_5m" : "HIC_STATION",
    "hic_1h" : "HIC_STATION",
    "obs_1d" : "PRECIP_STATION",
    "spw_5m" : "SETHY_STATION",
    "spw_1h" : "SETHY_STATION",
    "vmm_10m" : "VMM_STATION",
    "vmm_5m" : "VMM_STATION"
}

QUANTITY_COLUMNS = {
    "aws_10m" : "PRECIP_QUANTITY",
    "aws_1h" : "PRECIP_1HOUR",
    "aws_clim_10m" : "PRECIP_QUANTITY",
    "hic_5m" : "PRECIP_QUANTITY",
    "hic_1h" : "PRECIP_QUANTITY",
    "obs_1d" : "PRECIP_QUANTITY",
    "spw_5m" : "PRECIP_QUANTITY",
    "spw_1h" : "PRECIP_QUANTITY",
    "vmm_10m" : "PRECIP_QUANTITY",
    "vmm_5m" : "PRECIP_QUANTITY"
}

SCHEMA = pyarrow.schema({
    "timestamp" : pyarrow.timestamp("s", tz="UTC"),
    "station_id" : pyarrow.uint64(),
    "lon" : pyarrow.float32(),
    "lat" : pyarrow.float32(),
    "quantity" : pyarrow.float32(),
    "quality_flag" : pyarrow.string()
})





def get_rain_gauges_data(data_type : str,
                        start : datetime.datetime, end : datetime.datetime,
                        username : str, password : str, host : str, port : int, service : str):
    """
    Gets rain gauges data from the Oracle database.

    Parameters
    ----------
    data_type : str
        Network and time resolution to use.
        See `constants`.
    
    start : datetime.datetime
        Start timestamp (UTC).

    end : datetime.datetime
        End timestamp (UTC).

    username : str
        Username for database connection.
    
    password : str
        Password for database connection.

    host : str
        Database host.

    port : int
        Database port.

    service : str
        Database service name.

    Returns
    -------
    pd.DataFrame
        Dataframe with columns :
        - timestamp *(timestamp)* : Timestamp at the end of the validity period.
        - station_id *(int)* : Station ID.
        - lon *(float)* : Station longitude.
        - lat *(float)* : Station latitude.
        - quantity *(float)* : Precipitation quantity in mm.
        - validated *(bool)* : If the data has been validated.
        - corrected *(bool)* : If the data has been corrected.
    """

    if data_type not in ['aws_10m', 'aws_1h', 'aws_clim_10m', 'hic_5m', 'hic_1h', 'obs_1d', 'spw_5m', 'spw_1h', 'vmm_10m', 'vmm_5m']:
        raise ValueError("Wrong data type requested.")
    

    
    table = TABLES[data_type]
    station_table = STATIONS_TABLES[data_type]
    quantity_column = QUANTITY_COLUMNS[data_type]



    utc_zone = tz.gettz("UTC")
    be_zone = tz.gettz("Europe/Brussels")



    # For PRECIPITATION table, values with timestamp YYYYMMDD0000 are measured between YYYYMMDD0800 and YYYYMM(DD+1)0800
    if data_type == "obs_1d":
        start = (start.astimezone(be_zone) - datetime.timedelta(days=1, hours=8)).replace(tzinfo=utc_zone)
        end = (end.astimezone(be_zone) - datetime.timedelta(days=1, hours=8)).replace(tzinfo=utc_zone)



    # Open database connection and fetch requested data
    with oracledb.connect(user=username, password=password, host=host, port=port, service_name=service) as connection:
        odf = connection.fetch_df_all(
            statement=f"""
                SELECT
                    PRECIPS.TIMESTAMP AS timestamp,
                    STATIONS.STAT_ID AS station_id,
                    LOCATIONS.LONGITUDE AS lon,
                    LOCATIONS.LATITUDE AS lat,
                    PRECIPS.QUANTITY AS quantity,
                    QCONTROL.get_qcflag('CLIMAT', '{table}', '{quantity_column}', PRECIPS.CODE, PRECIPS.TIMESTAMP) AS quality_flag


                FROM
                    (
                        SELECT CODE, TIMESTAMP, {quantity_column} AS QUANTITY, QC_FLAGS
                        FROM {table}
                        WHERE
                            :start_timestamp <= TIMESTAMP
                            AND TIMESTAMP <= :end_timestamp
                            AND {quantity_column} IS NOT NULL
                    ) PRECIPS,
                    (
                        SELECT CODE, STAT_ID, DATE_BEGIN, DATE_END
                        FROM {station_table}
                    ) STATIONS,
                    (
                        SELECT STAT_ID, DATE_CHANGE, LONGITUDE_WGS84 AS LONGITUDE, LATITUDE_WGS84 AS LATITUDE
                        FROM LOCATION
                        WHERE
                            LONGITUDE_WGS84 IS NOT NULL
                            AND LATITUDE_WGS84 IS NOT NULL
                    ) LOCATIONS
            
                WHERE
                    PRECIPS.CODE = STATIONS.CODE
                    AND LOCATIONS.STAT_ID = STATIONS.STAT_ID
                    AND STATIONS.DATE_BEGIN < :start_timestamp
                    AND (
                        STATIONS.DATE_END > :end_timestamp
                        OR STATIONS.DATE_END IS NULL
                    )
                    AND (LOCATIONS.STAT_ID, LOCATIONS.DATE_CHANGE) IN (
                        SELECT STAT_ID, MAX(DATE_CHANGE)
                        FROM LOCATION
                        GROUP BY STAT_ID
                    )
                """,
            parameters={
                "start_timestamp":start,
                "end_timestamp":end},
            arraysize=1000,
            fetch_decimals=True,
            requested_schema=SCHEMA
        )
    
    
    
    # Convert pyarrow Dataframe to Pandas DataFrame
    df = pyarrow.table(odf).to_pandas()



    # Convert quality flag to boolean
    df["validated"] = df["quality_flag"] == "v"
    df["corrected"] = df["quality_flag"] == "c"
    df.pop("quality_flag")



    # Add one day if obs_1d
    if data_type == "obs_1d":
        df["timestamp"] = (df["timestamp"].dt.tz_localize(None).dt.tz_localize(be_zone) + datetime.timedelta(days=1, hours=8)).dt.tz_convert(utc_zone)



    return df.convert_dtypes()
CREATE TABLE public."Daily_G_R" (
    id integer NOT NULL,
    date date NOT NULL,
    product_g text NOT NULL,
    product_r text NOT NULL,
    station_id integer NOT NULL,
    station_lon real NOT NULL,
    station_lat real NOT NULL,
    radar text,
    min_availability real NOT NULL,
    min_precip_rate real NOT NULL,
    n_pixels integer NOT NULL,
    mean_error real,
    mean_abs_error real,
    rmse real,
    cov real,
    var_1 real,
    var_2 real,
    corr real,
    total_bias real,
    mean_bias real,
    median_bias real,
    weighted_bias real,
    scatter_score real,
    ratio_1_db real,
    ratio_2_db real,
    median_error real,
    weighted_error real
);


CREATE SEQUENCE public."Daily_G_R_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Daily_G_R_id_seq" OWNED BY public."Daily_G_R".id;


CREATE TABLE public."Daily_Mean_G_R" (
    id integer NOT NULL,
    date date NOT NULL,
    product_g text NOT NULL,
    product_r text NOT NULL,
    radar text,
    min_availability real NOT NULL,
    min_precip_rate real NOT NULL,
    n_pixels integer NOT NULL,
    mean_error real,
    mean_abs_error real,
    rmse real,
    cov real,
    var_1 real,
    var_2 real,
    corr real,
    total_bias real,
    mean_bias real,
    median_bias real,
    weighted_bias real,
    scatter_score real,
    ratio_1_db real,
    ratio_2_db real,
    median_error real,
    weighted_error real
);


CREATE SEQUENCE public."Daily_Mean_G_R_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Daily_Mean_G_R_id_seq" OWNED BY public."Daily_Mean_G_R".id;


CREATE TABLE public."Daily_Mean_Shift" (
    id integer NOT NULL,
    date timestamp without time zone DEFAULT now() NOT NULL,
    products_g text NOT NULL,
    product_r text NOT NULL,
    radar text,
    min_availability real NOT NULL,
    shift integer,
    n_g_nonzero integer
);


CREATE SEQUENCE public."Daily_Mean_Shift_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Daily_Mean_Shift_id_seq" OWNED BY public."Daily_Mean_Shift".id;


CREATE TABLE public."Daily_R_R" (
    id integer NOT NULL,
    date date NOT NULL,
    product_1 text NOT NULL,
    product_2 text NOT NULL,
    radar_1 text,
    radar_2 text,
    min_availability real NOT NULL,
    min_precip_rate real NOT NULL,
    n_pixels integer NOT NULL,
    mean_error real,
    mean_abs_error real,
    rmse real,
    cov real,
    var_1 real,
    var_2 real,
    corr real,
    total_bias real,
    mean_bias real,
    median_bias real,
    ratio_1_db real,
    ratio_2_db real,
    median_error real
);


CREATE TABLE public."Daily_R_R_Thresholds" (
    id integer NOT NULL,
    product_1 text NOT NULL,
    product_2 text NOT NULL,
    min_precip_rate real NOT NULL,
    min_n_pixels integer NOT NULL
);


CREATE SEQUENCE public."Daily_R_R_Thresholds_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Daily_R_R_Thresholds_id_seq" OWNED BY public."Daily_R_R_Thresholds".id;


CREATE SEQUENCE public."Daily_R_R_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Daily_R_R_id_seq" OWNED BY public."Daily_R_R".id;


CREATE TABLE public."Daily_Shift" (
    id integer NOT NULL,
    date timestamp without time zone DEFAULT now() NOT NULL,
    product_g text NOT NULL,
    product_r text NOT NULL,
    station_id integer NOT NULL,
    station_lon real NOT NULL,
    station_lat real NOT NULL,
    radar text,
    min_availability real NOT NULL,
    shift integer,
    n_g_nonzero integer
);


CREATE SEQUENCE public."Daily_Shift_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Daily_Shift_id_seq" OWNED BY public."Daily_Shift".id;


CREATE TABLE public."Monthly_G_R" (
    id integer NOT NULL,
    month date NOT NULL,
    product_g text NOT NULL,
    product_r text NOT NULL,
    station_id integer NOT NULL,
    radar text,
    min_availability real NOT NULL,
    min_precip_rate real NOT NULL,
    n_pixels integer NOT NULL,
    mean_error real,
    mean_abs_error real,
    rmse real,
    cov real,
    var_1 real,
    var_2 real,
    corr real,
    total_bias real,
    mean_bias real,
    median_bias real,
    weighted_bias real,
    scatter_score real,
    ratio_1_db real,
    ratio_2_db real,
    station_lon real NOT NULL,
    station_lat real NOT NULL,
    median_error real,
    weighted_error real
);


CREATE SEQUENCE public."Monthly_G_R_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Monthly_G_R_id_seq" OWNED BY public."Monthly_G_R".id;


CREATE TABLE public."Monthly_Mean_G_R" (
    id integer NOT NULL,
    month date NOT NULL,
    product_g text NOT NULL,
    product_r text NOT NULL,
    radar text,
    min_availability real NOT NULL,
    min_precip_rate real NOT NULL,
    n_pixels integer NOT NULL,
    mean_error real,
    mean_abs_error real,
    rmse real,
    cov real,
    var_1 real,
    var_2 real,
    corr real,
    total_bias real,
    mean_bias real,
    median_bias real,
    weighted_bias real,
    scatter_score real,
    ratio_1_db real,
    ratio_2_db real,
    median_error real,
    weighted_error real
);


CREATE SEQUENCE public."Monthly_Mean_G_R_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Monthly_Mean_G_R_id_seq" OWNED BY public."Monthly_Mean_G_R".id;


CREATE TABLE public."Monthly_R_R" (
    id integer NOT NULL,
    month date CONSTRAINT "Monthly_R_R_date_not_null" NOT NULL,
    product_1 text NOT NULL,
    product_2 text NOT NULL,
    radar_1 text,
    radar_2 text,
    min_availability real NOT NULL,
    min_precip_rate real NOT NULL,
    n_pixels integer NOT NULL,
    mean_error real,
    mean_abs_error real,
    median_error real,
    rmse real,
    cov real,
    var_1 real,
    var_2 real,
    corr real,
    total_bias real,
    mean_bias real,
    median_bias real,
    ratio_1_db real,
    ratio_2_db real
);


CREATE SEQUENCE public."Monthly_R_R_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Monthly_R_R_id_seq" OWNED BY public."Monthly_R_R".id;


CREATE TABLE public."Phidp0" (
    id integer NOT NULL,
    radar text NOT NULL,
    date date NOT NULL,
    phidp0 real,
    n_gates_ranges integer NOT NULL
);


CREATE SEQUENCE public."Phidp0_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Phidp0_id_seq" OWNED BY public."Phidp0".id;


CREATE TABLE public."RavisOffset" (
    id integer NOT NULL,
    radar text NOT NULL,
    date date NOT NULL,
    zdr_0 real,
    zdr_1 real,
    zdr_2 real,
    zdr_3 real,
    phidp_0 real,
    phidp_1 real,
    phidp_2 real,
    phidp_3 real
);


CREATE SEQUENCE public."RavisOffset_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."RavisOffset_id_seq" OWNED BY public."RavisOffset".id;


CREATE TABLE public."Zdr90" (
    id integer NOT NULL,
    radar text NOT NULL,
    date date NOT NULL,
    mean_zdr real,
    n_points integer NOT NULL,
    n_scans integer NOT NULL,
    available_rhohv boolean
);


CREATE SEQUENCE public."Zdr90_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."Zdr90_id_seq" OWNED BY public."Zdr90".id;


CREATE TABLE public."ZdrRain" (
    id integer NOT NULL,
    radar text NOT NULL,
    date date NOT NULL,
    mean_zdr real,
    n_points integer NOT NULL
);


CREATE SEQUENCE public."ZdrRain_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."ZdrRain_id_seq" OWNED BY public."ZdrRain".id;


CREATE TABLE public."ZdrRings" (
    id integer NOT NULL,
    radar text NOT NULL,
    date date NOT NULL,
    mean_zdr_1 real,
    mean_zdr_2 real,
    mean_zdr_3 real,
    mean_zdr_4 real,
    mean_zdr_5 real,
    mean_zdr_6 real,
    mean_zdr_7 real,
    mean_zdr_8 real,
    mean_zdr_9 real,
    mean_zdr_10 real,
    n_points_1 integer,
    n_points_2 integer,
    n_points_3 integer,
    n_points_4 integer,
    n_points_5 integer,
    n_points_6 integer,
    n_points_7 integer,
    n_points_8 integer,
    n_points_9 integer,
    n_points_10 integer
);


CREATE SEQUENCE public."ZdrRings_id_seq"
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public."ZdrRings_id_seq" OWNED BY public."ZdrRings".id;


ALTER TABLE ONLY public."Daily_G_R" ALTER COLUMN id SET DEFAULT nextval('public."Daily_G_R_id_seq"'::regclass);


ALTER TABLE ONLY public."Daily_Mean_G_R" ALTER COLUMN id SET DEFAULT nextval('public."Daily_Mean_G_R_id_seq"'::regclass);


ALTER TABLE ONLY public."Daily_Mean_Shift" ALTER COLUMN id SET DEFAULT nextval('public."Daily_Mean_Shift_id_seq"'::regclass);


ALTER TABLE ONLY public."Daily_R_R" ALTER COLUMN id SET DEFAULT nextval('public."Daily_R_R_id_seq"'::regclass);


ALTER TABLE ONLY public."Daily_R_R_Thresholds" ALTER COLUMN id SET DEFAULT nextval('public."Daily_R_R_Thresholds_id_seq"'::regclass);


ALTER TABLE ONLY public."Daily_Shift" ALTER COLUMN id SET DEFAULT nextval('public."Daily_Shift_id_seq"'::regclass);


ALTER TABLE ONLY public."Monthly_G_R" ALTER COLUMN id SET DEFAULT nextval('public."Monthly_G_R_id_seq"'::regclass);


ALTER TABLE ONLY public."Monthly_Mean_G_R" ALTER COLUMN id SET DEFAULT nextval('public."Monthly_Mean_G_R_id_seq"'::regclass);


ALTER TABLE ONLY public."Monthly_R_R" ALTER COLUMN id SET DEFAULT nextval('public."Monthly_R_R_id_seq"'::regclass);


ALTER TABLE ONLY public."Phidp0" ALTER COLUMN id SET DEFAULT nextval('public."Phidp0_id_seq"'::regclass);


ALTER TABLE ONLY public."RavisOffset" ALTER COLUMN id SET DEFAULT nextval('public."RavisOffset_id_seq"'::regclass);


ALTER TABLE ONLY public."Zdr90" ALTER COLUMN id SET DEFAULT nextval('public."Zdr90_id_seq"'::regclass);


ALTER TABLE ONLY public."ZdrRain" ALTER COLUMN id SET DEFAULT nextval('public."ZdrRain_id_seq"'::regclass);


ALTER TABLE ONLY public."ZdrRings" ALTER COLUMN id SET DEFAULT nextval('public."ZdrRings_id_seq"'::regclass);


ALTER TABLE ONLY public."Daily_G_R"
    ADD CONSTRAINT "Daily_G_R_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Daily_Mean_G_R"
    ADD CONSTRAINT "Daily_Mean_G_R_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Daily_Mean_Shift"
    ADD CONSTRAINT "Daily_Mean_Shift_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Daily_R_R_Thresholds"
    ADD CONSTRAINT "Daily_R_R_Thresholds_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Daily_R_R"
    ADD CONSTRAINT "Daily_R_R_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Daily_Shift"
    ADD CONSTRAINT "Daily_Shift_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Monthly_G_R"
    ADD CONSTRAINT "Monthly_G_R_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Monthly_Mean_G_R"
    ADD CONSTRAINT "Monthly_Mean_G_R_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Monthly_R_R"
    ADD CONSTRAINT "Monthly_R_R_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Phidp0"
    ADD CONSTRAINT "Phidp0_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."RavisOffset"
    ADD CONSTRAINT "RavisOffset_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Zdr90"
    ADD CONSTRAINT "Zdr90_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."ZdrRain"
    ADD CONSTRAINT "ZdrRain_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."ZdrRings"
    ADD CONSTRAINT "ZdrRings_pkey" PRIMARY KEY (id);


ALTER TABLE ONLY public."Daily_G_R"
    ADD CONSTRAINT daily_g_r_unique UNIQUE NULLS NOT DISTINCT (date, product_g, product_r, station_id, radar, min_availability, min_precip_rate);


ALTER TABLE ONLY public."Daily_Mean_G_R"
    ADD CONSTRAINT daily_mean_g_r_unique UNIQUE NULLS NOT DISTINCT (date, product_r, product_g, radar, min_availability, min_precip_rate);


ALTER TABLE ONLY public."Daily_Mean_Shift"
    ADD CONSTRAINT daily_mean_shift_unique UNIQUE NULLS NOT DISTINCT (date, products_g, product_r, radar, min_availability);


ALTER TABLE ONLY public."Daily_R_R"
    ADD CONSTRAINT daily_r_r_unique UNIQUE (date, product_1, product_2, radar_1, radar_2, min_availability, min_precip_rate);


ALTER TABLE ONLY public."Daily_Shift"
    ADD CONSTRAINT daily_shift_unique UNIQUE NULLS NOT DISTINCT (date, product_g, product_r, station_id, radar, min_availability);


ALTER TABLE ONLY public."Monthly_G_R"
    ADD CONSTRAINT monthly_gr_unique UNIQUE NULLS NOT DISTINCT (month, product_g, product_r, station_id, radar, min_availability, min_precip_rate);


ALTER TABLE ONLY public."Monthly_Mean_G_R"
    ADD CONSTRAINT monthly_mean_g_r_unique UNIQUE NULLS NOT DISTINCT (month, product_r, product_g, radar, min_availability, min_precip_rate);


ALTER TABLE ONLY public."Monthly_R_R"
    ADD CONSTRAINT monthly_r_r_unique UNIQUE NULLS NOT DISTINCT (month, product_1, product_2, radar_1, radar_2, min_availability, min_precip_rate);


ALTER TABLE ONLY public."Phidp0"
    ADD CONSTRAINT phidp0_unique UNIQUE (radar, date);


ALTER TABLE ONLY public."RavisOffset"
    ADD CONSTRAINT ravisoffset_unique UNIQUE (radar, date);


ALTER TABLE ONLY public."Zdr90"
    ADD CONSTRAINT zdr90_unique UNIQUE (radar, date);


ALTER TABLE ONLY public."ZdrRain"
    ADD CONSTRAINT zdrrain_unique UNIQUE (radar, date);


ALTER TABLE ONLY public."ZdrRings"
    ADD CONSTRAINT zdrrings_unique UNIQUE (radar, date);
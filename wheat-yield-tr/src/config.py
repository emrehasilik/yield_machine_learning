START_YEAR = 2005
END_YEAR = 2024

# Hasat yılı sezon penceresi: 1 Oct (y-1) -> 31 Jul (y)
SEASON_START_MONTH, SEASON_START_DAY = 10, 1
SEASON_END_MONTH, SEASON_END_DAY = 7, 31

NASA_POWER_VARS = [
    "T2M",            # mean temp
    "T2M_MAX",
    "T2M_MIN",
    "PRECTOTCORR",    # precip
    "ALLSKY_SFC_SW_DWN"  # solar radiation
]

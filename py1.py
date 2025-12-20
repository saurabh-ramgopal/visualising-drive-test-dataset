import pandas as pd
import numpy as np
from scipy import stats
import folium
from folium import plugins
import json
from datetime import datetime
import warnings
warnings.filterwarnings('ignore')
import h3

def assign_rat(row):
    has_5g = not (pd.isna(row['NR5G_RF_RSRP']) and pd.isna(row['NR5G_RF_SINR']) and pd.isna(row['NR5G_Throughput_PDSCH_TP']))
    has_lte = not (pd.isna(row['LTE_L1_RF_RSRP']) and pd.isna(row['LTE_L1_RF_RS_SINR']) and pd.isna(row['LTE_Data_Throughput_Downlink_All_PDSCH_PDSCH_TP_Total']))

    if has_5g and not has_lte:
        return 'NR5G'
    elif has_lte and not has_5g:
        return 'LTE'
    elif has_5g and has_lte:
        return 'NR5G' 
    else:
        return 'Unknown'


# Aggregate by RAT type
def aggregate_group(group, rat_type):
    agg_dict = {'count': len(group)}

    if rat_type == 'NR5G':
        cols_5g = ['NR5G_RF_RSRP', 'NR5G_RF_SINR', 'NR5G_Throughput_PDSCH_TP']
        for col in cols_5g:
            valid_vals = group[col].dropna()
            if len(valid_vals) > 0:
                agg_dict[f'{col}_mean'] = valid_vals.mean()
                agg_dict[f'{col}_median'] = valid_vals.median()
            else:
                agg_dict[f'{col}_mean'] = np.nan
                agg_dict[f'{col}_median'] = np.nan
    else:  # LTE
        cols_lte = ['LTE_L1_RF_RSRP', 'LTE_L1_RF_RS_SINR', 'LTE_Data_Throughput_Downlink_All_PDSCH_PDSCH_TP_Total']
        for col in cols_lte:
            valid_vals = group[col].dropna()
            if len(valid_vals) > 0:
                agg_dict[f'{col}_mean'] = valid_vals.mean()
                agg_dict[f'{col}_median'] = valid_vals.median()
            else:
                agg_dict[f'{col}_mean'] = np.nan
                agg_dict[f'{col}_median'] = np.nan

    # Keep categorical/spatial columns
    agg_dict['Lat'] = group['Lat'].iloc[0]
    agg_dict['Lon'] = group['Lon'].iloc[0]
    agg_dict['Market'] = group['MarketFileName'].iloc[0]
    agg_dict['RAT'] = rat_type

    return pd.Series(agg_dict)


df_clean = pd.read_csv('raw_data.csv')
print(f'File imported')

df_clean = df_clean.dropna(subset=['Lon', 'Lat']) 
df_clean['Time'] = pd.to_datetime(df_clean['Time'])
df_clean['TimeSec'] = df_clean['Time'].dt.floor('S')

df_clean['RAT'] = df_clean.apply(assign_rat, axis=1) # NR5G > LTE
df_clean = df_clean[df_clean['RAT'] != 'Unknown'] 

print(f'RAT assignment done')

H3_RES = 9 #street-level
df_clean['H3'] = df_clean.apply(lambda row: h3.latlng_to_cell(row['Lat'], row['Lon'], H3_RES), axis=1)

# Lat/Lon grid binning
BIN_SIZE = 0.002  # 200m
df_clean['Lat_Bin'] = (df_clean['Lat'] / BIN_SIZE).astype(int) * BIN_SIZE
df_clean['Lon_Bin'] = (df_clean['Lon'] / BIN_SIZE).astype(int) * BIN_SIZE
df_clean['Grid_ID'] = df_clean['Lat_Bin'].astype(str) + '_' + df_clean['Lon_Bin'].astype(str)

print(f'RAT aggregating....')

#5G
agg_5g = df_clean[df_clean['RAT'] == 'NR5G'].groupby(['TimeSec', 'Grid_ID']).apply(
    lambda g: aggregate_group(g, 'NR5G'), include_groups=False).reset_index()
#LTE
agg_lte = df_clean[df_clean['RAT'] == 'LTE'].groupby(['TimeSec', 'Grid_ID']).apply(
    lambda g: aggregate_group(g, 'LTE'), include_groups=False).reset_index()

df_agg = pd.concat([agg_5g, agg_lte], ignore_index=True)
df_agg = df_agg.sort_values(['TimeSec', 'Grid_ID']).reset_index(drop=True)

print(f'Converting to file....')
df_agg.to_csv('py1_result.csv', index=False)
print(f'Exported py1_result.csv with {len(df_clean)} records')
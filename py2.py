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

def calculate_perf_index(row):
    if row['RAT'] == 'NR5G':
        rsrp = row['NR5G_RF_RSRP_mean']
        sinr = row['NR5G_RF_SINR_mean']
        tp = row['NR5G_Throughput_PDSCH_TP_mean']
    else:  # LTE
        rsrp = row['LTE_L1_RF_RSRP_mean']
        sinr = row['LTE_L1_RF_RS_SINR_mean']
        tp = row['LTE_Data_Throughput_Downlink_All_PDSCH_PDSCH_TP_Total_mean']

    # drop null values
    if pd.isna(rsrp) or pd.isna(sinr) or pd.isna(tp):
        return np.nan

    rsrp_score = (rsrp + 120) / 60 
    sinr_score = sinr / 30
    tp_max = 200 
    tp_score = min(tp / tp_max, 1.0) 

    perf_index = 0.4 * rsrp_score + 0.4 * sinr_score + 0.2 * tp_score
    return np.clip(perf_index, 0, 1)  # range 0-1 

def perf_band(score):
    if pd.isna(score):
        return 'Unknown'
    elif score < 0.33:
        return 'Low'
    elif score < 0.67:
        return 'Medium'
    else:
        return 'High'


df_kpi = pd.read_csv('py1_result.csv')
df_kpi['Perf'] = df_kpi.apply(calculate_perf_index, axis=1)
df_kpi['Perf_Band'] = df_kpi['Perf'].apply(perf_band)

# KPI simplification 
df_clean_export = df_kpi[['TimeSec', 'Grid_ID', 'Lat', 'Lon', 'RAT', 'count', 'Perf', 'Perf_Band', 'Market']].copy()

df_clean_export['RSRP_mean'] = df_kpi.apply(
    lambda r: r['NR5G_RF_RSRP_mean'] if r['RAT'] == 'NR5G' else r['LTE_L1_RF_RSRP_mean'],
    axis=1
)
df_clean_export['SINR_mean'] = df_kpi.apply(
    lambda r: r['NR5G_RF_SINR_mean'] if r['RAT'] == 'NR5G' else r['LTE_L1_RF_RS_SINR_mean'],
    axis=1
)
df_clean_export['Throughput_mean'] = df_kpi.apply(
    lambda r: r['NR5G_Throughput_PDSCH_TP_mean'] if r['RAT'] == 'NR5G'
    else r['LTE_Data_Throughput_Downlink_All_PDSCH_PDSCH_TP_Total_mean'],
    axis=1
)

# Save to CSV
df_clean_export.to_csv('py2_result.csv', index=False)
print(f'Exported py2_result.csv with {len(df_clean_export)} records')
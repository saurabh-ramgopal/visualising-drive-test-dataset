import folium
from folium.plugins import MarkerCluster
from branca.colormap import LinearColormap
import pandas as pd
import h3
from shapely.geometry import Polygon

df_points = pd.read_csv('py2_result.csv')
df_points = df_points.sort_values("TimeSec")

center_lat = df_points['Lat'].mean()
center_lon = df_points['Lon'].mean()

# Color scale limits
vmin = df_points['Perf'].quantile(0.01)
vmax = df_points['Perf'].quantile(0.99)

vmin = float(vmin)
vmax = float(vmax)
if vmin == vmax:
    vmax = vmin + 1e-6

def safe_color(value, cmap, vmin, vmax):
    value = max(vmin, min(vmax, value)) 
    return cmap(value)

# colormap for Performane
cmap = LinearColormap(
    colors=['green', 'white', 'red'],
    vmin=vmin,
    vmax=vmax
)
cmap.caption = "Performance Index"

# STEP 3 — Build Map
m = folium.Map(location=[center_lat, center_lon], zoom_start=13, tiles="OpenStreetMap")

# LAYER 1 — POINT-BASED MAP
point_layer = folium.FeatureGroup(name="1-Second Points", show=True)
cluster = MarkerCluster(name="Point cluster")

for _, r in df_points.iterrows():

    color = safe_color(r['Perf'], cmap, vmin, vmax)

    popup_html = (
        f"<b>Time:</b> {r['TimeSec']}<br>"
        f"<b>Perf:</b> {r['Perf']:.3f}<br>"
        f"<b>RAT:</b> {r['RAT']}<br>"
        f"<b>RSRP:</b> {r['RSRP_mean']}<br>"
        f"<b>SINR:</b> {r['SINR_mean']}<br>"
        f"<b>TP:</b> {r['Throughput_mean']} Mbps<br>"
    )

    cluster.add_child(
        folium.CircleMarker(
            location=[r['Lat'], r['Lon']],
            radius=3,
            weight=1,
            fill=True,
            fill_opacity=0.8,
            color=color
        ).add_child(folium.Popup(popup_html))
    )

point_layer.add_child(cluster)
m.add_child(point_layer)


# LAYER 2 — Drive PATH
path_layer = folium.FeatureGroup(name="Drive Path")

df_points['next_Lat'] = df_points['Lat'].shift(-1)
df_points['next_Lon'] = df_points['Lon'].shift(-1)
df_points['next_Perf'] = df_points['Perf'].shift(-1)

for _, r in df_points[:-1].iterrows():
    color = safe_color(r['Perf'], cmap, vmin, vmax)

    folium.PolyLine(
        locations=[[r['Lat'], r['Lon']], [r['next_Lat'], r['next_Lon']]],
        weight=4,
        color=color,
        opacity=0.9
    ).add_to(path_layer)

m.add_child(path_layer)


# LAYER 3 — H3 HEXBIN MAP
df_h3 = df_points.copy()
df_h3['H3'] = df_h3.apply(lambda r: h3.latlng_to_cell(r['Lat'], r['Lon'], 9), axis=1)

# Aggregate KPIs per hex
hex_agg = df_h3.groupby('H3').agg({
    'Perf': 'mean',
    'RSRP_mean': 'mean',
    'SINR_mean': 'mean',
    'Throughput_mean': 'mean',
    'Lat': 'count'
}).rename(columns={'Lat': 'Samples'}).reset_index()

# Color scale for hex layer
h3_vmin = hex_agg['Perf'].quantile(0.01)
h3_vmax = hex_agg['Perf'].quantile(0.99)

h3_vmin = float(h3_vmin)
h3_vmax = float(h3_vmax)
if h3_vmin == h3_vmax:
    h3_vmax = h3_vmin + 1e-6

h3_cmap = LinearColormap(['green', 'white', 'red'], vmin=h3_vmin, vmax=h3_vmax)

hex_layer = folium.FeatureGroup(name="H3 Hex Aggregation")

for _, r in hex_agg.iterrows():
    boundary = h3.cell_to_boundary(r['H3'])
    poly = Polygon(boundary)

    perf = r['Perf']
    color = safe_color(perf, h3_cmap, h3_vmin, h3_vmax)

    popup = (
        f"<b>Hex:</b> {r['H3']}<br>"
        f"<b>Samples:</b> {r['Samples']}<br>"
        f"<b>Perf:</b> {r['Perf']:.3f}<br>"
        f"<b>RSRP mean:</b> {r['RSRP_mean']:.2f}<br>"
        f"<b>SINR mean:</b> {r['SINR_mean']:.2f}<br>"
        f"<b>TP mean:</b> {r['Throughput_mean']:.2f} Mbps<br>"
    )

    folium.Polygon(
        locations=[(lat, lon) for lat, lon in boundary],
        color=color,
        fill=True,
        fill_opacity=0.7,
        weight=1,
        popup=popup
    ).add_to(hex_layer)

m.add_child(hex_layer)


# generate map
m.add_child(cmap)
folium.LayerControl().add_to(m)

m.save("map_insights.html")
print("✓ Saved: map_insights.html")


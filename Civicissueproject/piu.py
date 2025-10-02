import os
import sqlite3
import folium
import geopandas as gpd
from folium.plugins import HeatMap
import matplotlib.pyplot as plt

# -------------------------
# Database Path (absolute)
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.abspath(os.path.join(BASE_DIR, "..", "civic.db"))

print("🔎 Using DB file:", DB_NAME)


# -------------------------
# District Mapping (DB → Shapefile)
# -------------------------
DISTRICT_MAP = {
    "angul": "Angul",
    "balangir": "Balangir",
    "balasore": "Baleshwar",   # shapefile uses Baleshwar
    "bargarh": "Bargarh",
    "bhadrak": "Bhadrak",
    "boudh": "Bauda",          # shapefile uses Bauda
    "cuttack": "Cuttack",
    "deogarh": "Debagarh",     # shapefile uses Debagarh
    "dhenkanal": "Dhenkanal",
    "gajapati": "Gajapati",
    "ganjam": "Ganjam",
    "jagatsinghpur": "Jagatsinghpur",
    "jajpur": "Jajapur",       # shapefile uses Jajapur
    "jharsuguda": "Jharsuguda",
    "kalahandi": "Kalahandi",
    "kandhamal": "Kandhamal",
    "kendrapara": "Kendrapara",
    "keonjhar": "Kendujhar",   # shapefile uses Kendujhar
    "khordha": "Khordha",
    "koraput": "Koraput",
    "malkangiri": "Malkangiri",
    "mayurbhanj": "Mayurbhanj",
    "nabarangpur": "Nabarangapur",  # shapefile uses Nabarangapur
    "nayagarh": "Nayagarh",
    "nuapada": "Nuapada",
    "puri": "Puri",
    "rayagada": "Rayagada",
    "sambalpur": "Sambalpur",
    "subarnapur": "Sonapur",   # shapefile uses Sonapur
    "sundargarh": "Sundargarh"
}


# -------------------------
# DB Connection
# -------------------------
def get_connection():
    return sqlite3.connect(DB_NAME)


# -------------------------
# Generate Charts
# -------------------------
def generate_charts():
    charts = {}

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT status, COUNT(*) FROM complaints GROUP BY status;")
    rows = cur.fetchall()
    statuses, counts = zip(*rows) if rows else ([], [])

    plt.figure(figsize=(6, 4))
    plt.bar(statuses, counts)
    plt.title("Complaints by Status")
    path = os.path.join(BASE_DIR, "static", "admin_charts", "status_bar.png")
    plt.savefig(path)
    plt.close()
    charts["status_bar"] = "admin_charts/status_bar.png"

    conn.close()
    return charts


# -------------------------
# Generate Odisha Heatmap
# -------------------------
# -------------------------
# Generate Odisha Heatmap
# -------------------------
def generate_odisha_heatmap():
    conn = get_connection()
    cur = conn.cursor()

    # Get complaints grouped by district + status
    cur.execute("SELECT district, status, COUNT(*) FROM complaints GROUP BY district, status;")
    rows = cur.fetchall()
    conn.close()

    # Map DB statuses → normalized keys
    STATUS_MAP = {
        "pending": "Pending",
        "in progress": "InProgress",
        "inprogress": "InProgress",
        "resolved": "Resolved"
    }

    # Build dictionary {district: {"Pending": x, "InProgress": y, "Resolved": z}}
    district_stats = {}
    for d, s, c in rows:
        d = d.lower().strip()
        norm_status = STATUS_MAP.get(s.lower().strip(), None)
        if not norm_status:
            continue  # ignore unknown statuses
        if d not in district_stats:
            district_stats[d] = {"Pending": 0, "InProgress": 0, "Resolved": 0}
        district_stats[d][norm_status] += c   # ✅ counts will now match correctly

    print("📊 District complaint stats:", district_stats)

    # Load Odisha shapefile
    shp_path = os.path.join(BASE_DIR, "data", "gadm41_IND_2.shp")
    gdf = gpd.read_file(shp_path)
    odisha_gdf = gdf[gdf["NAME_1"] == "Odisha"]

    # Create DB-mapped column
    odisha_gdf["db_key"] = odisha_gdf["NAME_2"].apply(
        lambda n: next((k for k, v in DISTRICT_MAP.items() if v.lower() == n.lower()), None)
    )

    # Add complaint counts
    odisha_gdf["pending"] = odisha_gdf["db_key"].apply(
        lambda d: district_stats.get(d, {}).get("Pending", 0) if d else 0
    )
    odisha_gdf["inprogress"] = odisha_gdf["db_key"].apply(
        lambda d: district_stats.get(d, {}).get("InProgress", 0) if d else 0
    )
    odisha_gdf["resolved"] = odisha_gdf["db_key"].apply(
        lambda d: district_stats.get(d, {}).get("Resolved", 0) if d else 0
    )
    odisha_gdf["total"] = odisha_gdf["pending"] + odisha_gdf["inprogress"] + odisha_gdf["resolved"]

    # Map
    m = folium.Map(location=[20.9517, 85.0985], zoom_start=7, tiles="cartodbpositron")

    # Choropleth
    folium.Choropleth(
        geo_data=odisha_gdf,
        data=odisha_gdf,
        columns=["NAME_2", "total"],
        key_on="feature.properties.NAME_2",
        fill_color="YlOrRd",
        fill_opacity=0.7,
        line_opacity=0.8,
        legend_name="Total Complaints",
    ).add_to(m)

    # Tooltip
    folium.GeoJson(
        odisha_gdf,
        name="District Stats",
        style_function=lambda x: {"color": "black", "weight": 1, "fillOpacity": 0},
        tooltip=folium.GeoJsonTooltip(
            fields=["NAME_2", "pending", "inprogress", "resolved", "total"],
            aliases=["District:", "Pending:", "In Progress:", "Resolved:", "Total:"],
            localize=True,
            sticky=True,
        ),
    ).add_to(m)

    # Save
    out_path = os.path.join(BASE_DIR, "static", "admin_charts", "odisha_heatmap.html")
    m.save(out_path)
    print(f"✅ Heatmap with tooltips saved at {out_path}")
    return "admin_charts/odisha_heatmap.html"



# -------------------------
# Run as script
# -------------------------
if __name__ == "__main__":
    print("Generating charts + Odisha heatmap...")
    generate_charts()
    generate_odisha_heatmap()
    print("✅ Done. Check static/admin_charts/")

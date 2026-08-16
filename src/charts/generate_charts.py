"""
-   chart export: queries the analysis viewns & saves matplotlib charts as png iamges to be embedded in the readme
-   uses pandas to bridge sql -> plotting: pd.read_sql() returns a DataFrame directly frm a query, which matplotlib/pandas 
    plotting functions consume w/ very little extra code
"""

import os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import psycopg

load_dotenv()

# charts get saved here
OUTPUT_DIR = "charts"

def get_connection():
    # same connection pattern as load/upsert.py - reads DATABASE_URL from .env
    return psycopg.connect(os.environ["DATABASE_URL"])

def chart_moving_average(conn):
    # line chart: 7 day moving avg temp, one line per city, over time. this directly visualizes v_moving_avg_temp
    df = pd.read_sql("SELECT * FROM v_moving_avg_temp", conn)

    # keep reading_date as plain strings rather than converting to pandas' DatetimeIndex - DatetimeIndex construction 
    # crashes on this particular python 3.14 + pandas combination (a genuine env bug, isolated n confirmed separately)
    # ISO format date strings already sort correctly as plain text
    df.loc[:, "reading_date"] = df["reading_date"].astype(str)

    """
    pivot: reshape from "long" format (one row per city+date) into "wide" format (one column per city, indexed by date)
    - this is the shape matplotlib wants for a multi line chart, one line per column
    """
    pivoted = df.pivot(index = "reading_date", columns = "city_name", values = "temp_7day_avg_c")

    fig, ax = plt.subplots(figsize = (10, 5))
    pivoted.plot(ax = ax)   # plots one line per city automatically, using the pivoted column

    ax.set_title("7-Day Moving Average Temperature by City")
    ax.set_xlabel("Date")
    ax.set_ylabel("Temperature (°C)")
    ax.legend(title = "City")

    # with 60 string based x-axis points, showing every tick would be unreadably crowded - show roughly every 7th 
    # label instead
    ax.set_xticks(range(0, len(pivoted), 7))
    ax.set_xticklabels(pivoted.index[::7], rotation = 45)

    plt.tight_layout()

    output_path = os.path.join(OUTPUT_DIR, "moving_avg_temp.png")
    plt.savefig(output_path, dpi = 120)
    plt.close(fig)  # frees memory -- matters once we're generating several chartsin one script run
    print(f"Saved { output_path }")

def chart_day_over_day(conn, city_name: str = "Seremban"):
    """
    bar chart: day-over-day temperature change for one city. bars naturally show direction (+/-) better than a line
    would - this visualizes v_day_over_day_change, filtered to a single city for readability
    """
    df = pd.read_sql("SELECT * FROM v_day_over_day_change WHERE city_name = %(city)s AND temp_change_c IS NOT NULL",
                    conn,
                    params={"city": city_name},
                    )
    df.loc[:, "reading_date"] = df["reading_date"].astype(str)

    fig, ax = plt.subplots(figsize = (12, 5))

    # color bars by direction: warming days redish, cooling days purpl ish makes the patern readable at a glance w/out 
    # reading every value
    colors = ["#F4A6C1" if v > 0 else "#B39CD0" for v in df["temp_change_c"]]
    ax.bar(df["reading_date"], df["temp_change_c"], color = colors)

    ax.set_title(f"Day-over-Day Temperature Change — {city_name}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Change (°C)")
    ax.axhline(0, color = "black", linewidth = 0.8) # zero line makes direction obvious

    ax.set_xticks(range(0, len(df), 7))
    ax.set_xticklabels(df["reading_date"].iloc[::7], rotation = 45)
    plt.tight_layout()

    output_path = os.path.join(OUTPUT_DIR, "day_over_day_change.png")
    plt.savefig(output_path, dpi = 120)
    plt.close(fig)
    print(f"Saved {output_path}")

def chart_rainfall_ranking(conn):
    """
    horizontal bar chart: total rainfall per city, ranked highest to lowest. directly visualizes v_city_rainfall_ranking 
    - horizontal bars read naturally top to bottom as a ranking n city names as labels dont need rotation the way date
    labels do
    """
    df = pd.read_sql(
        "SELECT * FROM v_city_rainfall_ranking ORDER BY rainfall_rank",
        conn,
    )

    fig, ax = plt.subplots(figsize = (8, 5))

    # reverse the DataFrame order before plotting: matplotlib's barh() draws from bottom to to, so w/out reversing, 
    # the #1 ranked city would appear at the bottom of the chart instead of the top - counterintuitive for a ranking 
    # visual where readers expect the top result to actually be at the top
    df_reversed = df.iloc[::-1]

    ax.barh(df_reversed["city_name"], df_reversed["total_rainfall_mm"], color= "#B39CD0")

    ax.set_title("Total Rainfall by City (60-Day Period)")
    ax.set_xlabel("Total Rainfall (mm)")
    plt.tight_layout()

    output_path = os.path.join(OUTPUT_DIR, "rainfall_ranking.png")
    plt.savefig(output_path, dpi = 120)
    plt.close(fig)
    print(f"Saved { output_path }")

def chart_extremes(conn):
    """
    grouped bar chart: hottest temperature and wettest single day rainfall, side by side, for each city. directly 
    visualizes v_extremes_per_city. 2 different units (°C and mm) on one chart is a real trade off - we're accepting 
    a shared y-axis isnt perfectly meaningful for both series, in exchange for an easy side-by-side city comparison 
    in a single image
    """
    df = pd.read_sql("SELECT * FROM v_extremes_per_city ORDER BY city_name", conn)

    x = range(len(df))
    width = 0.35    # width of each bar - two bars per city means they need to sit side by side, not overlap

    fig, ax = plt.subplots(figsize = (10, 5))

    # offset each series left/right by half the bar width so the two bars per city sit next to each other rather 
    # # than overlapping
    ax.bar([i - width/2 for i in x], df["hottest_temp_c"], width, label ="Hottest Temp (°C)", color = "#F4A6C1")
    ax.bar([i + width/2 for i in x], df["wettest_day_mm"], width, label = "Wettest Day (mm)", color = "#B39CD0")

    ax.set_title("Recorded Extremes by City (60-Day Period)")
    ax.set_xticks(list(x))
    ax.set_xticklabels(df["city_name"])
    ax.legend()
    plt.tight_layout()

    output_path = os.path.join(OUTPUT_DIR, "extremes_per_city.png")
    plt.savefig(output_path, dpi=120)
    plt.close(fig)
    print(f"Saved { output_path }")

if __name__ == "__main__":
    conn = get_connection()
    chart_moving_average(conn)
    chart_day_over_day(conn)
    chart_rainfall_ranking(conn)
    chart_extremes(conn)
    conn.close()
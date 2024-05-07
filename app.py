import streamlit as st
import pandas as pd
import datetime
import requests
import io

@st.cache_data
def fetch_data():
    # Get the current month and year
    now = datetime.datetime.now()
    
    data_by_month = {}
    
    for i in range(12):
        # Calculate the month and year for each of the past 12 months
        month = (now.month - i - 1) % 12 + 1
        year = now.year - (now.month - i - 1) // 12
        
        # Format the month as a 3-letter abbreviation
        month_str = datetime.date(year, month, 1).strftime("%b").lower()
        
        # Format the URL with the correct month and year
        dataurl = f"https://www.td.gov.hk/datagovhk_td/first-reg-vehicle/resources/en/particulars_of_first_registered_vehicle_{month_str}_{year}_eng.csv"
        
        # Download the CSV data
        response = requests.get(dataurl)
        if response.ok:
            # Read the CSV data directly from the response content
            data = pd.read_csv(io.StringIO(response.text))
            data_by_month[(month_str, year)] = data
    
    return data_by_month

data_by_month = fetch_data()


# Extract month_latest and year_latest from the sorted data
sorted_data = sorted(data_by_month.items(), key=lambda x: (x[0][1], datetime.datetime.strptime(x[0][0], '%b').month), reverse=True)
latest_data = sorted_data[0]
(month_latest, year_latest), df_latest = latest_data

st.title(f"How many new Teslas are there in Hong Kong in {month_latest.capitalize()} {year_latest}?")


def display_tesla_data(data_by_month, month_latest, year_latest):
    if data_by_month:
        # Get the data for the previous month
        if len(sorted_data) > 1:
            (month_prev, year_prev), df_prev = sorted_data[1]
        else:
            df_prev = None
        
        df_tesla = df_latest[df_latest['Vehicle Make'] == 'TESLA']
        df_tesla_prev = df_prev[df_prev['Vehicle Make'] == 'TESLA'] if df_prev is not None else pd.DataFrame()
        
        tesla_count = df_tesla.shape[0]
        tesla_prev_count = df_tesla_prev.shape[0] if not df_tesla_prev.empty else 0
        return tesla_count, tesla_prev_count
    else:
        st.write("Insufficient data available.")
        return None, None

tesla_count, tesla_prev_count = display_tesla_data(data_by_month, month_latest, year_latest)
st.metric(label=f"New Tesla {month_latest.capitalize()} {year_latest}", value=tesla_count, delta=tesla_count - tesla_prev_count)

def display_BYD_data(data_by_month):
    if not data_by_month:
        return None, None

    # Sort the data_by_month dictionary by year and month
    sorted_data = sorted(data_by_month.items(), key=lambda x: (x[0][1], datetime.datetime.strptime(x[0][0], '%b').month), reverse=True)
    
    latest_data = sorted_data[0]
    (month_latest, year_latest), df_latest = latest_data
    
    # Get the data for the previous month
    df_prev = sorted_data[1][1] if len(sorted_data) > 1 else None
    
    df_byd_latest = df_latest[df_latest['Vehicle Make'] == 'BYD']
    df_byd_prev = df_prev[df_prev['Vehicle Make'] == 'BYD'] if df_prev is not None else pd.DataFrame()
    
    byd_count = df_byd_latest.shape[0]
    byd_prev_count = df_byd_prev.shape[0] if not df_byd_prev.empty else 0
    
    return byd_count, byd_prev_count, month_latest, year_latest

byd_count, byd_prev_count, month_latest, year_latest = display_BYD_data(data_by_month)
st.metric(label=f"New BYD {month_latest.capitalize()} {year_latest}", value=byd_count, delta=byd_count - byd_prev_count)


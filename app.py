import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date

# ---------------------------------------------------------
# DATABASE SETUP & INITIALIZATION
# ---------------------------------------------------------
DB_FILE = "motor_repairs_v2.db"

def get_connection():
    conn = sqlite3.connect(DB_FILE)
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS repairs (
            job_id TEXT PRIMARY KEY,
            entry_date TEXT,
            motor_name TEXT,
            motor_serial TEXT,
            manufacturer TEXT,
            hp_rating REAL,
            frame_size TEXT,
            symptom TEXT,
            failure_category TEXT,
            failure_mode TEXT,
            root_cause TEXT,
            wire_gauge TEXT,
            turns_per_coil INTEGER,
            repair_action TEXT,
            pre_megger_m_ohm REAL,
            post_megger_m_ohm REAL,
            post_amps REAL
        )
    ''')
    conn.commit()
    conn.close()

# Initialize DB on startup
init_db()

# ---------------------------------------------------------
# STREAMLIT UI CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(page_title="Motor Repair Knowledge Base", layout="wide", page_icon="⚙️")

st.title("⚙️ Motor Repair & Root-Cause Knowledge Base")
st.caption("Capture repair history, standardize fixes, and analyze failure modes across jobs.")

tabs = st.tabs(["➕ Log New Repair", "🔍 Search Repair History", "📊 Failure Analytics"])

# ---------------------------------------------------------
# TAB 1: LOG NEW REPAIR
# ---------------------------------------------------------
with tabs[0]:
    st.subheader("Record Job Details")
    
    with st.form("repair_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("### 1. Motor Specs")
            job_id = st.text_input("Job ID*", placeholder="e.g., JOB-2026-001")
            motor_name = st.text_input("Motor Name / Application", placeholder="e.g., High-Pressure Water Pump Motor")
            motor_serial = st.text_input("Serial Number", placeholder="e.g., SN-882910")
            manufacturer = st.selectbox("Manufacturer", ["Siemens", "ABB", "WEG", "GE", "TECO", "Other"])
            hp_rating = st.number_input("HP / kW Rating", min_value=0.1, value=10.0, step=0.5)
            frame_size = st.text_input("Frame Size", placeholder="e.g., 284T")

        with col2:
            st.markdown("### 2. Failure & Diagnosis")
            symptom = st.text_input("Reported Symptom", placeholder="e.g., Tripping breaker, heavy smoke")
            failure_category = st.selectbox(
                "Failure Category*", 
                ["Electrical", "Mechanical", "Thermal / Overload", "Environmental / Contamination"]
            )
            failure_mode = st.selectbox(
                "Specific Failure Mode",
                [
                    "Stator Coil Burnout", 
                    "Phase-to-Phase Short", 
                    "Bearing Seizure / Wear", 
                    "Rotor Bar Failure", 
                    "Moisture / Oil Contamination",
                    "Insulation Breakdown"
                ]
            )
            root_cause = st.text_area("Root Cause Analysis", placeholder="Why did it break? (e.g., Bearing wear caused rotor drag)")

        with col3:
            st.markdown("### 3. Repair Specs & Testing")
            wire_gauge = st.text_input("Magnet Wire Gauge (AWG/mm)", placeholder="e.g., 0.9 mm / 19 AWG")
            turns_per_coil = st.number_input("Turns Per Coil", min_value=0, value=45)
            repair_action = st.text_area("Repair Action Taken", placeholder="e.g., Rewound stator, replaced drive-end bearing")
            
            st.markdown("**Diagnostic Test Readings**")
            pre_megger = st.number_input("Pre-Test Insulation Resistance (MΩ)", min_value=0.0, value=0.2)
            post_megger = st.number_input("Post-Test Insulation Resistance (MΩ)", min_value=0.0, value=200.0)
            post_amps = st.number_input("Post-Test No-Load Current (A)", min_value=0.0, value=4.5)

        submitted = st.form_submit_button("💾 Save Repair Record")
        
        if submitted:
            if not job_id:
                st.error("Please provide a Job ID.")
            else:
                conn = get_connection()
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                        INSERT INTO repairs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        job_id, str(date.today()), motor_name, motor_serial, manufacturer, hp_rating,
                        frame_size, symptom, failure_category, failure_mode, root_cause,
                        wire_gauge, turns_per_coil, repair_action, pre_megger, post_megger, post_amps
                    ))
                    conn.commit()
                    st.success(f"Successfully recorded Job '{job_id}' into database!")
                except sqlite3.IntegrityError:
                    st.error(f"Job ID '{job_id}' already exists in the database.")
                finally:
                    conn.close()

# ---------------------------------------------------------
# TAB 2: SEARCH REPAIR HISTORY
# ---------------------------------------------------------
with tabs[1]:
    st.subheader("Search & Reference Past Solutions")
    
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM repairs", conn)
    conn.close()
    
    if df.empty:
        st.info("No repair records found yet. Log a job in the first tab to populate the database.")
    else:
        search_term = st.text_input("🔎 Search by Motor Name, Symptom, Failure Mode, Frame Size, or Manufacturer", "")
        
        if search_term:
            filtered_df = df[
                df['motor_name'].str.contains(search_term, case=False, na=False) |
                df['symptom'].str.contains(search_term, case=False, na=False) |
                df['failure_mode'].str.contains(search_term, case=False, na=False) |
                df['frame_size'].str.contains(search_term, case=False, na=False) |
                df['manufacturer'].str.contains(search_term, case=False, na=False)
            ]
        else:
            filtered_df = df

        st.markdown(f"**Showing {len(filtered_df)} record(s)**")
        
        # Display summary table
        st.dataframe(
            filtered_df[[
                'job_id', 'entry_date', 'motor_name', 'manufacturer', 'hp_rating', 
                'frame_size', 'failure_category', 'failure_mode', 'wire_gauge', 'turns_per_coil'
            ]],
            use_container_width=True
        )
        
        # Detailed Card View
        st.markdown("---")
        st.subheader("Detailed Job Card View")
        selected_job = st.selectbox("Select Job ID to view full technical details:", filtered_df['job_id'].unique())
        
        if selected_job:
            row = filtered_df[filtered_df['job_id'] == selected_job].iloc[0]
            
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"**Motor Name / App:** {row['motor_name']}")
                st.markdown(f"**Specs:** {row['manufacturer']} | {row['hp_rating']} HP | Frame {row['frame_size']} | S/N: {row['motor_serial']}")
                st.markdown(f"**Symptom:** {row['symptom']}")
                st.markdown(f"**Failure Category:** {row['failure_category']} ({row['failure_mode']})")
                st.markdown(f"**Root Cause:** {row['root_cause']}")
            with c2:
                st.markdown(f"**Rewind Specs:** {row['wire_gauge']} wire | {row['turns_per_coil']} turns/coil")
                st.markdown(f"**Repair Action:** {row['repair_action']}")
                st.markdown(f"**Megger Test:** {row['pre_megger_m_ohm']} MΩ (Pre) ➔ **{row['post_megger_m_ohm']} MΩ (Post)**")
                st.markdown(f"**Post-Test Current:** {row['post_amps']} A")

# ---------------------------------------------------------
# TAB 3: FAILURE ANALYTICS
# ---------------------------------------------------------
with tabs[2]:
    st.subheader("Failure Mode Insights")
    
    conn = get_connection()
    df_analytics = pd.read_sql_query("SELECT * FROM repairs", conn)
    conn.close()
    
    if df_analytics.empty:
        st.info("Log some repairs first to see visual failure analytics!")
    else:
        col_chart1, col_chart2 = st.columns(2)
        
        with col_chart1:
            fig1 = px.pie(
                df_analytics, 
                names='failure_category', 
                title='Breakdown by Failure Category',
                hole=0.4
            )
            st.plotly_chart(fig1, use_container_width=True)
            
        with col_chart2:
            fig2 = px.bar(
                df_analytics, 
                x='failure_mode', 
                color='manufacturer',
                title='Failure Modes by Manufacturer',
                barmode='stack'
            )
            st.plotly_chart(fig2, use_container_width=True)

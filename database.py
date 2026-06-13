from supabase import create_client
import streamlit as st


def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


def save_prices(prices_dict):
    try:
        db = get_supabase()
        db.table("user_prices").upsert({
            "user_id": "default",
            "prices": prices_dict
        }).execute()
    except Exception as e:
        st.warning(f"Could not save prices: {e}")


def load_prices():
    try:
        db = get_supabase()
        result = db.table("user_prices").select("prices").eq("user_id", "default").execute()
        return result.data[0]["prices"] if result.data else {}
    except Exception as e:
        st.warning(f"Could not load prices: {e}")
        return {}


def save_config(config_dict):
    try:
        db = get_supabase()
        db.table("user_config").upsert({
            "user_id": "default",
            "config": config_dict
        }).execute()
    except Exception as e:
        st.warning(f"Could not save config: {e}")


def load_config():
    try:
        db = get_supabase()
        result = db.table("user_config").select("config").eq("user_id", "default").execute()
        return result.data[0]["config"] if result.data else {}
    except Exception as e:
        st.warning(f"Could not load config: {e}")
        return {}


def save_quote(job_name, total_bid, trade, data_dict):
    try:
        db = get_supabase()
        db.table("quotes").insert({
            "user_id": "default",
            "job_name": job_name,
            "total_bid": total_bid,
            "trade": trade,
            "data": data_dict
        }).execute()
    except Exception as e:
        st.warning(f"Could not save quote: {e}")

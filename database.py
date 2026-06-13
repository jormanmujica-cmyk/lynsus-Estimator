from supabase import create_client
import streamlit as st


def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ── App State (user_config table — single row per user, merge-upsert) ──────

def save_app_state(state_dict):
    """Merge state_dict into the existing user_config row. Never overwrites other keys."""
    try:
        db = get_supabase()
        result = db.table("user_config").select("config").eq("user_id", "default").execute()
        current = result.data[0]["config"] if result.data else {}
        current.update(state_dict)
        db.table("user_config").upsert({
            "user_id": "default",
            "config": current
        }).execute()
    except Exception as e:
        st.warning(f"Could not save state: {e}")


def load_app_state():
    """Load full config dict from user_config table."""
    try:
        db = get_supabase()
        result = db.table("user_config").select("config").eq("user_id", "default").execute()
        return result.data[0]["config"] if result.data else {}
    except Exception as e:
        st.warning(f"Could not load state: {e}")
        return {}


# ── Prices (user_prices table — legacy, keep for backward compat) ──────────

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


# ── Config helpers (kept for compatibility) ────────────────────────────────

def save_config(config_dict):
    save_app_state(config_dict)


def load_config():
    return load_app_state()


# ── Quotes (quotes table — append-only) ───────────────────────────────────

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

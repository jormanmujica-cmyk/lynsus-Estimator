from supabase import create_client
import streamlit as st
import logging

_log = logging.getLogger(__name__)


def get_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)


# ── App State (user_config table — single row per user, merge-upsert) ──────

def save_app_state(state_dict):
    """Merge state_dict into the existing user_config row. Never overwrites other keys."""
    try:
        db = get_supabase()
        user_id = st.session_state.get("user_id", "default")
        result = db.table("user_config").select("config").eq("user_id", user_id).execute()
        current = result.data[0]["config"] if result.data else {}
        current.update(state_dict)
        db.table("user_config").upsert(
            {"user_id": user_id, "config": current},
            on_conflict="user_id"
        ).execute()
    except Exception as e:
        _log.warning("Could not save state: %s", e)


def load_app_state():
    """Load full config dict from user_config table."""
    try:
        db = get_supabase()
        user_id = st.session_state.get("user_id", "default")
        result = db.table("user_config").select("config").eq("user_id", user_id).execute()
        return result.data[0]["config"] if result.data else {}
    except Exception as e:
        _log.warning("Could not load state: %s", e)
        return {}


# ── Prices (user_prices table — legacy, keep for backward compat) ──────────

def save_prices(prices_dict):
    try:
        db = get_supabase()
        user_id = st.session_state.get("user_id", "default")
        db.table("user_prices").upsert(
            {"user_id": user_id, "prices": prices_dict},
            on_conflict="user_id"
        ).execute()
    except Exception as e:
        _log.warning("Could not save prices: %s", e)


def load_prices():
    try:
        db = get_supabase()
        user_id = st.session_state.get("user_id", "default")
        result = db.table("user_prices").select("prices").eq("user_id", user_id).execute()
        return result.data[0]["prices"] if result.data else {}
    except Exception as e:
        _log.warning("Could not load prices: %s", e)
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
        user_id = st.session_state.get("user_id", "default")
        db.table("quotes").insert({
            "user_id": user_id,
            "job_name": job_name,
            "total_bid": total_bid,
            "trade": trade,
            "data": data_dict
        }).execute()
    except Exception as e:
        _log.warning("Could not save quote: %s", e)

import json
import os
from config.settings import DATA_FILE, ALLOWED_USER_IDS

# Global variable: {user_id: {symbol: interval}}
user_watchlists = {}
user_risk_settings = {}

def load_data():
    global user_watchlists
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
                # Migration logic: Check if data is in old format (flat dict)
                # Old format: {"BTCUSDT": "1h", ...}
                # New format: {"123456": {"BTCUSDT": "1h"}, ...}
                if data and isinstance(data, dict):
                    first_key = next(iter(data)) if data else None
                    first_val = data[first_key] if first_key else None
                    
                    # If value is string, it's the old format (symbol -> interval)
                    if isinstance(first_val, str):
                        print("Detected legacy watchlist format. Migrating...")
                        default_user = ALLOWED_USER_IDS[0] if ALLOWED_USER_IDS else "unknown_user"
                        user_watchlists[str(default_user)] = data
                        save_data() # Save immediately in new format
                    else:
                        # New format
                        user_watchlists.update(data)
                        
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading data: {e}")

def save_data():
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_watchlists, f, indent=2)
    except IOError as e:
        print(f"Error saving data: {e}")

def get_user_watchlist(user_id):
    uid = str(user_id)
    if uid not in user_watchlists:
        user_watchlists[uid] = {}
    return user_watchlists[uid]

def add_to_watchlist(user_id, symbol, interval):
    uid = str(user_id)
    if uid not in user_watchlists:
        user_watchlists[uid] = {}
    user_watchlists[uid][symbol] = interval
    save_data()

def remove_from_watchlist(user_id, symbol):
    uid = str(user_id)
    if uid in user_watchlists and symbol in user_watchlists[uid]:
        del user_watchlists[uid][symbol]
        save_data()

def get_all_unique_pairs():
    """Return a set of (symbol, interval) tuples from all users."""
    pairs = set()
    for uid, watchlist in user_watchlists.items():
        for sym, interval in watchlist.items():
            pairs.add((sym, interval))
    return pairs

def get_users_watching(symbol, interval):
    """Return list of user_ids watching this specific pair."""
    users = []
    for uid, watchlist in user_watchlists.items():
        if watchlist.get(symbol) == interval:
            users.append(int(uid) if uid.isdigit() else uid)
    return users

def get_user_risk_settings():
    return user_risk_settings

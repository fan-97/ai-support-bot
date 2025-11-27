import json
import os
from config.settings import DATA_FILE

# 全局变量
watchlist = {}
user_risk_settings = {}

def load_data():
    global watchlist
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                watchlist.update(json.load(f))
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading data: {e}")

def save_data():
    tmp_file = f"{DATA_FILE}.tmp"
    try:
        with open(tmp_file, 'w', encoding='utf-8') as f:
            json.dump(watchlist, f, indent=2)
        os.replace(tmp_file, DATA_FILE)
    except IOError as e:
        print(f"Error saving data: {e}")
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

def get_watchlist():
    return watchlist

def get_user_risk_settings():
    return user_risk_settings

import json
import os
from config.settings import DATA_FILE

# 全局变量
watchlist = {}
user_risk_settings = {}

def load_data():
    global watchlist
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            watchlist.update(json.load(f))

def save_data():
    with open(DATA_FILE, 'w') as f:
        json.dump(watchlist, f)

def get_watchlist():
    return watchlist

def get_user_risk_settings():
    return user_risk_settings

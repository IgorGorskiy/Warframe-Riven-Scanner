# =========================
# Warframe Riven Scanner — Refactored & Analysis‑Ready
# =========================
# Цели рефакторинга:
# 1. Чёткое разделение: API / Worker / DB / UI / Analysis
# 2. Старый функционал алертов сохранён
# 3. Подготовка к анализу цен и ML
# 4. UI расширяем без переписывания логики
import os
os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"

import sys
import time
import json
import sqlite3
import requests
import itertools
import winsound
import random
import pyautogui
import keyboard
import traceback
from collections import deque
from uis3 import Ui_MainWindow
from market_riven_api import MarketAPI, MarketBumperState, BumperWorker
from db import RivenDatabase, PodRollDB
from rivenwidgets import RivenAlertWidget
from prices_analysis import Analyser
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from myplot import PricePlot
import pandas as pd
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QLineEdit, QGroupBox,
    QLCDNumber, QSpacerItem, QSizePolicy, QGraphicsView, QTextEdit
)

from PySide6.QtCore import Qt, QSize, QDateTime, QStringConverter
from PySide6.QtCore import Signal, QThread, QObject
from PySide6.QtMultimedia import QMediaPlayer

# перевод rivenalertwidget на qml   
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickWidgets import QQuickWidget

#говно с клода началось
from PySide6.QtCore import QUrl
from pathlib import Path
from riven_qml_bridge import RivenListModel

app = QApplication(sys.argv)
#engine = QQmlApplicationEngine()
#model = RivenListModelChatGPT()
#engine.rootContext().setContextProperty(
#    "rivenModel",
#    model
#)
#engine.load("qml/Main.qml")

# matplotlib для аналитики
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from rivenstats import STARTING_STATS

# =========================
# CONFIG
# =========================

cur_dir = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(cur_dir, "settings.json")
blacklist_path = os.path.join(cur_dir, "pidors.json")
groll_stats_path = os.path.join(cur_dir, "groll_stats.json")
login_path = os.path.join(cur_dir, "marketLogin.json")
with open(login_path) as ff:
    login = json.load(ff)

#содержимое файла marketLogin.json должно выглядеть так:

{
    "login": "ваш логин",
    "password": "ваш пароль",
    "nickname": "ваш ник на маркете"
}

#конец содержимого


with open(settings_path) as f:
    settingsG = json.load(f)
f.close()

groll_raw_stats = {}
with open(groll_stats_path) as f:
    groll_raw_stats = json.load(f)
f.close()

SVINKA_VSEGDA_VIDNA = False

MODE_TO_COOLDOWN = {
    "WEAPON_FOR_DB_SEARCH": 7,
    "GROLL": 7,
    "FAST_SEARCH": 7,
    "BASE_API": 3
}

BASE_WEAPONS_URL = "https://api.warframe.market/v1/auctions/search?type=riven&sort_by=price_asc&weapon_url_name="
API_AUCTIONS = "https://api.warframe.market/v1/auctions"
API_SEARCH = "https://api.warframe.market/v1/auctions/search?type=riven&positive_stats="
API_SEARCH2 = "&negative_stats="
API_SEARCH3 = "&sort_by=price_asc"

HEADERS = {"accept": "application/json", "platform": "pc"}
DB_PATH = "rivens.db"

GOOD_STATS = [
    "critical_chance",
    "critical_damage",
    "multishot",
]

GOOD_STATS_MELEES1 = [
    "critical_chance",
    "critical_damage",
    "base_damage_/_melee_damage",
]

GOOD_STATS_MELEES2 = [
    "fire_rate_/_attack_speed",
    "critical_damage",
    "range",
]

GOOD_NEGATIVES = {
    "projectile_speed",
    "zoom",
    "ammo_maximum"
}

GOOD_NEGATIVES_MELEES = {
    "finisher_damage",
    "critical_chance_on_slide_attack",
    "channeling_efficiency"
}
    
ACTIVATE_KEY = "alt+v"
ALL_STATS = ["magazine_capacity",
    "status_duration",
    "critical_damage",
    "ammo_maximum",
    "multishot",
    "recoil",
    "zoom",
    "punch_through",
    "puncture_damage",
    "slash_damage",
    "fire_rate_/_attack_speed",
    "reload_speed",
    "projectile_speed",
    "impact_damage",
    "base_damage_/_melee_damage",
    "damage_vs_grineer",
    "damage_vs_infested",
    "damage_vs_corpus",
    "heat_damage",
    "toxin_damage",
    "cold_damage",
    "electric_damage",
    "critical_chance",
    "status_chance",
    "range",
    "combo_duration",
    "channeling_damage",
    "finisher_damage",
    "critical_chance_on_slide_attack",
    "chance_to_gain_extra_combo_count",
    "channeling_efficiency",
    "any"]

def build_URL(pos_attributes, weapon, negative = "any"):
        URL = API_SEARCH

        stats_processed = 0
        while stats_processed < len(pos_attributes):
            URL = URL + pos_attributes[stats_processed]
            stats_processed = stats_processed + 1
            if stats_processed < len(pos_attributes):
                URL = URL + ','
        if negative == "any":
            URL = URL + "&negative_stats=has"
        else:
            URL = URL + "&negative_stats=" + negative
        URL = URL + "&sort_by=price_asc&weapon_url_name=" + weapon
        return URL

def update_blacklist(owner_str):
    blacklist = {}
    with open(blacklist_path, "r") as f:
        blacklist = json.load(f)
        if owner_str in blacklist:
            blacklist[owner_str] += 1
        else:
            blacklist[owner_str] = 1
    with open(blacklist_path, "w") as f:
        json.dump(blacklist, f)

def get_blacklist():
    blacklist = {}
    with open(blacklist_path, "r") as f:
        blacklist = json.load(f)
        return blacklist
        

def build_groll_urls(raw_stats):
    urls = []
    weapons = raw_stats.keys()
    for weapon in weapons:
        stats_for_weapon = raw_stats[weapon]
        var_stats = stats_for_weapon["var"]
        const_stats:list = stats_for_weapon["const"]
        for var_stat in var_stats:
            pos_stats = const_stats.copy()
            pos_stats.append(var_stat)
            url = build_URL(pos_stats, weapon)
            urls.append(url)
    return urls

groll_urls_g = build_groll_urls(groll_raw_stats)

class Glob:
    altvmsg = f"none"
    settings = settingsG
    good_weapons = settings["good_weapons"]
    fast_weapons_list = settings["fast_weapons_list"]
    schedule = settings["schedule"]
    mode_to_cooldown = settings.get("cooldowns", {})
    groll_urls = groll_urls_g

# =========================
# UTILS
# =========================

def play_sound():
    try:
        winsound.Beep(600, 300)
    except Exception:
        pass

# =========================
# RATE LIMITER
# =========================

class RateLimiter:
    def __init__(self, interval_sec):
        self.cooldown = interval_sec
        self.last_call = 0

    def wait(self):
        delta = time.time() - self.last_call
        if delta < self.cooldown:
            time.sleep(self.cooldown - delta)

    def set_interval(self, interval_sec):
        self.cooldown = interval_sec

    def get_response(self, URL, cooldown, headers=HEADERS, timeout=10):
        self.cooldown = cooldown
        #print(f"[get_response] entrance: {time.time()}s; cooldown = {self.cooldown}; last_call = {self.last_call}")
        self.wait()
        #print(f"[get_response] waited. time: {time.time()}s; cooldown = {self.cooldown}; last_call = {self.last_call}")
        r = requests.get(URL, headers = headers, timeout = timeout)
        self.last_call = time.time()
        return r

# =========================
# RIVEN CHECK (старый функционал)
# =========================

def minutes_since_updated(updated_str: str) -> int:
    updated_dt = datetime.fromisoformat(updated_str)
    now = datetime.now(timezone.utc)
    delta = now - updated_dt
    return int(delta.total_seconds() // 60)

def riven_alert_check(auction) -> str:
    buyout = auction.get("buyout_price")
    item = auction.get("item", {})
    if not buyout or buyout <= 1:
        return "none"
    if item.get("type") != "riven":
        return "none"
    updated = auction.get("updated")
    re_rolls = item.get("re_rolls", 0)
    weapon = item.get("weapon_url_name")
    
    # предотвращаем попадания good-ролльных ривенов из запроса для бд
    if minutes_since_updated(updated) > 120:
        return "none"
    
    if are_stats_good(auction):
        return "good stats"

    if minutes_since_updated(updated) > 4:
        return "none"

    if re_rolls / buyout > 3 and re_rolls > 50:
        return "endo"

    if weapon in Glob.good_weapons and buyout <= Glob.good_weapons[weapon]:
        return "pod roll"
    
    return "none"

def is_riven_pod_roll(auction):
    buyout = auction.get("buyout_price")
    item = auction.get("item", {})
    if not buyout or buyout <= 1:
        return False
    if item.get("type") != "riven":
        return False
    updated = auction.get("updated")
    re_rolls = item.get("re_rolls", 0)
    weapon = item.get("weapon_url_name")
    if minutes_since_updated(updated) > 4:
        return False
    if weapon in Glob.good_weapons and buyout <= Glob.good_weapons[weapon]:
        return True
    else:
        return False

def is_riven_endo(auction):
    buyout = auction.get("buyout_price")
    item = auction.get("item", {})
    if not buyout or buyout <= 1:
        return False
    if item.get("type") != "riven":
        return False
    re_rolls = item.get("re_rolls", 0)
    if re_rolls / buyout > 3 and re_rolls > 50:
        return True
    else:
        return False

def is_non_interesting_weapon_groll(attributes):
    interesting = 0
    for stat in attributes:
        if stat.get("positive", 0) == True and (stat.get("url_name") in GOOD_STATS):
            interesting += 1
        elif stat.get("positive", 0) == False and (stat.get("url_name") in GOOD_NEGATIVES):
            interesting += 1
    if interesting < 4:
        interesting = 0
    for stat in attributes:
        if stat.get("positive", 0) == True and (stat.get("url_name") in GOOD_STATS_MELEES1):
            interesting += 1
        elif stat.get("positive", 0) == False and (stat.get("url_name") in GOOD_NEGATIVES_MELEES):
            interesting += 1
    if interesting < 4:
        interesting = 0
    for stat in attributes:
        if stat.get("positive", 0) == True and (stat.get("url_name") in GOOD_STATS_MELEES2):
            interesting += 1
        elif stat.get("positive", 0) == False and (stat.get("url_name") in GOOD_NEGATIVES_MELEES):
            interesting += 1
    if interesting < 4:
        return False
    else:
        return True


def are_stats_good(auction):
    buyout = auction.get("buyout_price")
    updated = auction.get("updated")
    owner = auction["owner"]
    item = auction.get("item", {})
    if not buyout or buyout <= 1:
        return False
    if item.get("type") != "riven":
        return False
    if owner["ingame_name"] == "--Cube":
        return 0
    if owner["ingame_name"] == "Naixon-Samir":
        return 0
    if owner["ingame_name"] == "ClosedLifer2":
        return 0
    attributes = item.get("attributes", {})
    #if minutes_since_updated(updated) > 4 and not item["weapon_url_name"] in Glob.good_weapons:
    #    return 0
    if len(attributes) < 4:
        return 0
    #пенис пися попа сосал
    if item["weapon_url_name"] in groll_raw_stats:
        constscore = 0
        varscore = 0
        stats = []
        for stat in attributes:
            if stat.get("positive", 0) == False:
                neg_stat_name = stat.get("url_name")
            if stat.get("positive", 0) == True and (stat.get("url_name") in groll_raw_stats[item["weapon_url_name"]]["const"]):
                constscore += 1
                stats.append(stat.get("url_name"))
            elif stat.get("positive", 0) == True and (stat.get("url_name") in groll_raw_stats[item["weapon_url_name"]]["var"]):
                varscore += 1
                stats.append(stat.get("url_name"))
            elif stat.get("positive", 0) == False and not (stat.get("url_name") in groll_raw_stats[item["weapon_url_name"]]["neg"]):
                return 0
        if constscore == 2 and varscore == 1:
            product:str = item["weapon_url_name"]
            stats.sort()
            for stat in stats:
                product += stat
            product += neg_stat_name
            auction["quantiles"] = win.analyser.get_quantiles(product, 0.1, 0.25, 0.5)
            return 1
        else:
            return 0
        
    if is_non_interesting_weapon_groll(attributes):
        return 1
    #if  auction["buyout_price"] > 500 and not item["weapon_url_name"] in Glob.good_weapons:
    #    return 0
    return 0

# =========================
# WORKER THREAD
# =========================

class LogPrinter(QObject):
    new_log = Signal(str)

    def __init__(self):
        super().__init__()

    def emit_text(self, text):
        self.new_log.emit(text)

log_printer = LogPrinter()

class Log(QThread):
    logs:list = list()
    visible_logs:list = list()
    altvLogs:list = list()
    workerLogs:list = list()
    new_log = Signal(str)

    @staticmethod
    def log_write(text, logs=None, logs_to_show=None):
        if logs is None:
            logs = Log.logs

        if logs_to_show is None:
            logs_to_show = Log.visible_logs

        while len(logs) > 500:
            logs.pop(0)

        while len(logs_to_show) > 50:
            logs_to_show.pop(0)

        now = datetime.fromtimestamp(time.time()).time()

        logs_to_show.append(f"{now}: {text}")
        logs.append(f"{now}: {text}")

        full_text = "\n".join(logs_to_show)
        log_printer.emit_text(full_text)
    
    def log_print(logs = logs):
        print ("LOGS:")
        print(QDateTime.currentDateTime().toString())
        loglen = len(logs)
        if loglen > 15:
            loglen = 15
        for log in logs[-15:-1]:
            print(log)
        print ("\nALT + V LOGS:")
        for log in Log.altvLogs:
            print(log)
        print("msg = " + Glob.altvmsg)
        print ("\n")

class RivenAnalyser:
    def __init__(self, db: RivenDatabase, analyser:Analyser):
        super().__init__()
        self.db = db
        self.analyser = analyser

    def strepsils(self):
        result = {}
        weapons = groll_raw_stats.keys()
        for weapon in weapons:
            result4 = {}
            stats_for_weapon = groll_raw_stats[weapon]
            var_stats = stats_for_weapon["var"]
            const_stats:list = stats_for_weapon["const"]
            neg_stats = stats_for_weapon["neg"]
            for var_stat in var_stats:
                result2 = {}
                pos_stats = const_stats.copy()
                pos_stats.append(var_stat)
                pos_stats.sort()
                for neg_stat in neg_stats:
                    all_stats = pos_stats.copy()
                    all_stats.append(neg_stat)
                    product = weapon
                    for st in all_stats:
                        product += st
                    plot = self.db.get_price_history(product)
                    prices = plot[1]
                    result31 = self.analyser.calculate_q(prices, 0.10)
                    result32 = self.analyser.calculate_q(prices, 0.50)
                    result33 = self.analyser.calculate_q(prices, 0.90)
                    #result2[neg_stat] = [result31, result32, result33]
                    result2[neg_stat] = result31
                result4[var_stat] = result2
            result[weapon] = result4
        return result
    
    def get_quantiles(self, product:str, q1, q2, q3):
        plot = self.db.get_price_history(product)
        prices = plot[1]
        result31 = self.analyser.calculate_q(prices, q1)
        result32 = self.analyser.calculate_q(prices, q2)
        result33 = self.analyser.calculate_q(prices, q3)
        return [result31, result32, result33]

class AuctionWorker(QThread):
    price_checked = Signal(str, list)  # auction_id, prices
    alert_found = Signal(dict, str)
    newRivensCountUpdate = Signal(int)
    groll_urls_progress = Signal(int)
    pod_roll_progress = Signal(int)

    def __init__(self, db: RivenDatabase, pod_roll_db:PodRollDB):
        super().__init__()
        self.market_limiter = RateLimiter(2)  # 2 запрос / сек
        r = self.market_limiter.get_response("https://api.warframe.market/v2/riven/weapons", 2, HEADERS, 10)
        weapons = r.json()["data"]
        self.weapon_rivens = {}
        for w in weapons:
            self.weapon_rivens[w["slug"]] = w
        self.price_queue = deque()
        self.db = db
        self.pod_roll_db = pod_roll_db
        self.running = True
        self.seen_ids_all = set()
        self.newRivensCount = 0
        self.groll_url_in_queue = ""
        self.tracked_grolls = {}
        self.sold_grolls = {}
        self.grolls_to_dismiss = self.db.get_dismiss_list()

    def write_prices_to_db(self, auctions):
        item = auctions[0].get("item")
        weapon = item["weapon_url_name"]
        i = 0
        prices = []
        Log.log_write(f"starting writing to DB data for {weapon}; amount of auctions: {len(auctions)}")
        offline_count = 0
        for auction in auctions:
            owner = auction["owner"]
            status = owner["status"]
            if status == "offline":
                offline_count = offline_count + 1
            if status != "offline":
                prices.append(auction["buyout_price"])
                i = i + 1
            if i >= 3:
                break
        Log.log_write(f"writing to DB data: {prices} || for time: {int(time.time())}")

        while len(prices) < 3:
            prices.append(-1)
        self.pod_roll_db.insert_prices(weapon, prices[0], prices[1], prices[2], int(time.time()))

        for a in auctions:
            if a["owner"]["status"] == "online" or a["owner"]["status"] == "ingame":
                prices.append(a["buyout_price"])
            if len(prices) == 3:
                break
        if type(prices) == "NoneType":
            prices = [-1, -1, -1]
            print(prices)
        return prices
    
    def count_avg_lowest_price(self, price, product):
        data = self.db.get_price_history(product)
        if len(data) == 0:
            return True
        if not data:
            return False
        prices = data[1]
        if len(prices) > 100:
            prices = prices[-100:-1]
        avg_price = sum(prices) / len(prices)
        return avg_price

    def is_groll_high_stasts(self, auction, avg_price):
        price = auction["buyout_price"]
        item = auction["item"]
        weapon:str = auction["item"]["weapon_url_name"]
        rank = item.get("mod_rank", 0)
        attributes = item.get("attributes", [])
        total_score = 0
        for stat in attributes:
            if stat["positive"] != True:
                neg_stat = stat["url_name"]
                continue
            stat_name = stat["url_name"]
            w_type = self.weapon_rivens[weapon]["rivenType"]
            if w_type in STARTING_STATS:
                dispo = self.weapon_rivens[weapon]["disposition"]
                base_value = STARTING_STATS[w_type][stat_name]
                maxval = 1.1*0.9375*dispo*base_value
                minval = 0.9*0.9375*dispo*base_value
                val = stat["value"]
                if rank < 4 and stat["value"] < minval: #подтираем жопу за дибилами, которые пишут статы для макс мода к моду 0 ранга
                    val = stat["value"] / ((rank + 1) / 9.0) #приводим статы к виду мода 8-го ранга
                max = maxval - minval
                cur = val - minval
                percentage:int = int(100*cur/max)
                if (percentage > 100):
                    percentage = 100
                elif (percentage < 0):
                    percentage = 0
                total_score += percentage
        if total_score > 150 and avg_price * 0.9 > price:
            return True
        elif total_score > 200 and avg_price * 1.0 > price:
            return True 
        elif total_score > 250 and avg_price * 1.5 > price:
            return True
        else:
            return False
    
    def write_groll_prices_to_db(self, auctions):
        weapon:str = auctions[0]["item"]["weapon_url_name"]
        Log.log_write(f"starting writing to GROLL DB data for {weapon}; amount of auctions: {len(auctions)}")
        checked_negs = []
        current_aucs_ids = []
        p_prod_key = ""
        for auction in auctions:
            current_aucs_ids.append(auction["id"])
            owner = auction["owner"]
            status = owner["status"]
            last_seen = owner["last_seen"]
            o_name = owner["ingame_name"]
            item = auction.get("item")
            price = auction["buyout_price"]
            rank = item.get("mod_rank", 0)
            val_den = (rank + 1) / 9.0
            stats = []
            neg_stat_name = ""
            neg_stat_value = 0
            pos_att_name_to_val = {}
            for att in item["attributes"]:
                if att["positive"] == False:
                    neg_stat_name = att["url_name"]
                    neg_stat_value = att["value"]
                else:
                    stats.append(att["url_name"])
                    pos_att_name_to_val[att["url_name"]] = att["value"]
            stats.sort()
            product:str = weapon
            values = []
            for stat in stats:
                product += stat
                values.append(pos_att_name_to_val[stat])
            partial_prod_key = product
            p_prod_key = partial_prod_key
            product += neg_stat_name
            if neg_stat_name in groll_raw_stats[weapon]["neg"]:
                if price is None:
                    continue
                avg_price = self.count_avg_lowest_price(price, product)
                if not avg_price or avg_price is None:
                    avg_price = 9999999
                    print (f"no avg price for {weapon} {stats} {neg_stat_name}")
                if avg_price * 0.8 > price or self.is_groll_high_stasts(auction, avg_price):
                    auction["quantiles"] = win.analyser.get_quantiles(product, 0.1, 0.25, 0.5)
                    self.alert_found.emit(auction, "good stats (dismissable)")
            iso_updated = auction["updated"]
            dt_obj = datetime.fromisoformat(iso_updated) + timedelta(hours=3)
            last_updated = int(dt_obj.timestamp())
            auc = {}
            auc["ts"] = 0
            auc["price"] = price
            auc["last_checked"] = int(time.time())
            auc["last_updated"] = last_updated
            auc["owner_name"] = o_name
            auc["value1"] = values[0]/val_den
            auc["value2"] = values[1]/val_den
            auc["value3"] = values[2]/val_den
            auc["value4"] = neg_stat_value/val_den
            auc["statname1"] = stats[0]
            auc["statname2"] = stats[1]
            auc["statname3"] = stats[2]
            auc["statname4"] = neg_stat_name
            auc["weapon_name"] = weapon
            auc["product"] = product
            # проверка на кубоидных говнопидоров
            if product in self.sold_grolls:
                aucs_to_remove = []
                for sold_auc in self.sold_grolls[product]:
                    if sold_auc["owner_name"] == o_name:
                        print (f"ОБНАРУЖЕН КУБОИДНЫЙ ГОВНОПИДОР ПО КЛИЧКЕ {o_name}")
                        update_blacklist(o_name)
                        self.db.delete_sold_riven(sold_auc["product"], sold_auc["owner_name"])
                        aucs_to_remove.append(sold_auc)
                for todel in aucs_to_remove:
                    self.sold_grolls[product].remove(todel)
            if not partial_prod_key in self.tracked_grolls:
                aucdict = {auction["id"]: auc}
                self.tracked_grolls[partial_prod_key] = aucdict
            else:
                self.tracked_grolls[partial_prod_key][auction["id"]] = auc
            if (minutes_since_updated(last_seen) < 1440) and (not (neg_stat_name in checked_negs)):
                checked_negs.append(neg_stat_name)
            else:
                continue
            self.db.insert_price(product, price, int(time.time()))
        Log.log_write(f"writing to DB groll data for {p_prod_key}")
        ids_to_pop_for_current_prod = []
        for riven_id in self.tracked_grolls[p_prod_key].keys():
            if not riven_id in current_aucs_ids:
                auc = self.tracked_grolls[p_prod_key][riven_id]
                auc["ts"] = int(time.time())
                self.db.insert_sold_riven(auc, auc["product"])
                print (f"Продан ривен на {auc["weapon_name"]} со статами: {auc["statname1"]}, {auc["statname2"]}, {auc["statname3"]}; минус: {auc["statname4"]} за {auc["price"]} платины")
                if not auc["product"] in self.sold_grolls:
                    self.sold_grolls[auc["product"]] = [auc]
                else:
                    self.sold_grolls[auc["product"]].append(auc)
                ids_to_pop_for_current_prod.append(riven_id)
        for c_id in ids_to_pop_for_current_prod:
            self.tracked_grolls[p_prod_key].pop(c_id)

    def on_turned_on_off(self):
        if win.ui.radioButton.isChecked():
            self.turned_off = False
            self.sync_needed = True
        else:
            self.turned_off = True
            self.sync_needed = False

    def run(self):
        self.firstRun = True
        #weapons_list = list(good_weapons.keys())
        self.fast_weap_id = 0
        self.groll_url_len = len(Glob.groll_urls)
        self.groll_url_id = 0
        self.good_weapons_id = 0
        self.good_weapons_len = len(Glob.good_weapons)
        self.good_weapons_list = list(Glob.good_weapons)
        written_to_db = 0
        self.stage_id = 0
        self.mode = "SYNC"
        self.sync_needed = True
        self.turned_off = False
        last_api_updae = time.time()
        while self.running:
            try:
                Log.log_write(f"starting iteration with following parameters: groll_url_len = {self.groll_url_len}; good_weapons_len ="
                              f" {self.good_weapons_len}; fast_weapons_length = {len(Glob.fast_weapons_list)}; fast_weap_id = "
                              f"{self.fast_weap_id}; good_weapons_id = {self.good_weapons_id}; groll_url_id = {self.groll_url_id}; "
                              f"mode = {self.mode}; firstRun = {self.firstRun}; sync_needed = {self.sync_needed}; turned_off = "
                              f"{self.turned_off}; stage_id = {self.stage_id}; amount of stages = {len(Glob.schedule)}; "
                              f"cooldown = {Glob.mode_to_cooldown[self.mode]}")
                if self.sync_needed and self.turned_off != True:
                    self.mode = "SYNC"
                    self.firstRun = True
                    self.sync_needed = False
                if self.turned_off:
                    self.market_limiter.set_interval(14)
                    self.market_limiter.last_call = time.time()
                    self.market_limiter.wait()
                    continue
                if self.mode != "BASE_API" and self.mode != "SYNC":
                    if self.stage_id >= len(Glob.schedule):
                        self.stage_id = 0
                        self.mode = "BASE_API"
                    else:
                        self.mode = Glob.schedule[self.stage_id]
                win.ui.stage_label.setText(f"Текущий режим: {self.mode}; стадия: {self.stage_id + 1}")
                win.ui.seconds_from_update.display(int(time.time() - last_api_updae))
                r = {}
                if self.fast_weap_id >= len(Glob.fast_weapons_list):
                    self.fast_weap_id = 0
                if self.good_weapons_id >= self.good_weapons_len:
                    win.ui.podRollProgressLCD.display(win.ui.podRollProgressLCD.value() + 1)
                    self.good_weapons_id = 0
                if self.groll_url_id >= self.groll_url_len:
                    win.ui.grollProgressLCD.display(win.ui.grollProgressLCD.value() + 1)
                    self.groll_url_id = 0
                if self.mode == "GROLL":
                    errStr = "GROLL"
                    Log.log_write(f"requesting GROLL")
                    groll_url = Glob.groll_urls[self.groll_url_id]
                    r = self.market_limiter.get_response(groll_url, Glob.mode_to_cooldown[self.mode], headers=HEADERS, timeout=10)
                    self.groll_url_id = self.groll_url_id + 1
                    self.groll_urls_progress.emit(self.groll_url_id)
                elif self.mode == "BASE_API" or self.mode == "SYNC":
                    errStr = f"API_AUCTIONS; mode = {self.mode}"
                    Log.log_write(f"requesting API_AUCTIONS; mode = {self.mode}")
                    r = self.market_limiter.get_response(API_AUCTIONS, Glob.mode_to_cooldown[self.mode], headers=HEADERS, timeout=10)
                    #r = self.market_limiter.get_response("https://api.warframe.market/v1/auctions/search?type=riven&positive_stats=multishot,critical_chance,critical_damage&negative_stats=zoom&sort_by=price_asc&weapon_url_name=acceltra", 7, headers=HEADERS, timeout=10)
                    i = 0
                elif self.mode == "FAST_SEARCH":
                    Log.log_write(f"FAST_SEARCH. self.fast_weap_id = {self.fast_weap_id}")
                    weapon_fast = Glob.fast_weapons_list[self.fast_weap_id]
                    Log.log_write(f"got fast weapon. weapon = {weapon_fast}")
                    errStr = f"FAST_SEARCH: BASE_WEAPONS_URL + {weapon_fast}"
                    Log.log_write(f"FAST_SEARCH: requesting BASE_WEAPONS_URL + {weapon_fast}, i = {i}")
                    r = self.market_limiter.get_response(BASE_WEAPONS_URL + weapon_fast, Glob.mode_to_cooldown[self.mode], headers=HEADERS, timeout=10)
                    self.fast_weap_id = self.fast_weap_id + 1
                elif self.mode == "WEAPON_FOR_DB_SEARCH":
                    Log.log_write(f"getting weapon_for_db. good_weapons_id = {self.good_weapons_id}")
                    weapon_for_db = self.good_weapons_list[self.good_weapons_id]
                    Log.log_write(f"got weapon_for_db. weapon_for_db = {weapon_for_db}")
                    errStr = f"WEAPON_FOR_DB_SEARCH: BASE_WEAPONS_URL + {weapon_for_db}"
                    Log.log_write(f"WEAPON_FOR_DB_SEARCH: requesting BASE_WEAPONS_URL + {weapon_for_db}, i = {i}")
                    r = self.market_limiter.get_response(BASE_WEAPONS_URL + weapon_for_db, Glob.mode_to_cooldown[self.mode], headers=HEADERS, timeout=10)
                    self.good_weapons_id = self.good_weapons_id + 1
                    written_to_db = written_to_db + 1
                    self.pod_roll_progress.emit(self.good_weapons_id)
                if r.status_code != 200:
                    play_sound()
                    play_sound()
                    print("HTTP error in " + errStr + ": ", r.status_code, r.text[:200])
                    Log.log_print()
                    self.market_limiter.set_interval(15)
                    self.market_limiter.last_call = time.time()
                    self.market_limiter.wait()
                    self.market_limiter.set_interval(7)
                    with open("RIVEN_ENDO_ERROR_LOG_" + QDateTime.currentDateTime().toString().replace(" ", "_").replace(":", "-") + ".txt", "w") as f:
                        f.write(QDateTime.currentDateTime().toString().replace(" ", "_") + "\n")
                        f.write("HTTP error in " + errStr + ": " + r.text[:200] + "\n")
                        f.write("traceback:" + traceback.format_exc())
                        for log in Log.logs:
                            f.write(log + "\n")
                    f.close
                if self.mode != "BASE_API" and self.mode != "SYNC":
                    self.stage_id += 1

                last_api_updae_formated = datetime.fromtimestamp(last_api_updae).time()
                Log.log_write(f"last_api_updae = {last_api_updae_formated}")
                auctions = r.json()["payload"]["auctions"]
                Log.log_write(f"got {len(auctions)} auctions. mode: {self.mode}")

                self.newRivensCount = 0
                if self.mode == "WEAPON_FOR_DB_SEARCH":
                    self.write_prices_to_db(auctions)
                if self.mode == "GROLL":
                    self.write_groll_prices_to_db(auctions)
                elif self.mode == "BASE_API" or self.mode == "WEAPON_FOR_DB_SEARCH" or self.mode == "SYNC" or self.mode == "FAST_SEARCH":
                    emitted = 0
                    for auction in auctions:
                        #reason = riven_alert_check(auction)
                        reason = "none"
                        if is_riven_pod_roll(auction):
                            reason = "pod roll"
                        elif is_riven_endo(auction):
                            reason = "endo"
                        elif are_stats_good(auction) and self.mode != "WEAPON_FOR_DB_SEARCH" and self.mode != "FAST_SEARCH":
                            reason = "good stats"
                        item = auction["item"]
                        att = item.get("attributes", {})
                        if reason != "none":
                            self.alert_found.emit(auction, reason)
                        auc_id = auction.get("id")
                        if not (auc_id in self.seen_ids_all):
                            self.seen_ids_all.add(auc_id)
                            self.newRivensCount = self.newRivensCount + 1
                if self.newRivensCount > 0 and not (self.firstRun) and (self.mode == "BASE_API" or self.mode == "SYNC"):
                    Log.log_write(f"api update detected. sync aquired. last_call = {self.market_limiter.last_call}s")
                    self.newRivensCountUpdate.emit(self.newRivensCount)
                    #self.mode = "WEAPON_FOR_DB_SEARCH"
                    self.mode = Glob.schedule[0]
                    self.stage_id = 0
                    last_api_updae = time.time()
                #elif self.mode == "WEAPON_FOR_DB_SEARCH" and written_to_db > 2:
                #    Log.log_write(f"mode changes to WEAPON_FAST_SEARCH") 
                #    self.mode = "GROLL"
                #    written_to_db = 0

                if time.time() - last_api_updae > 110 and self.mode != "BASE_API" and self.mode != "SYNC" and self.turned_off != True:
                    Log.log_write(f"mode changes to BASE_API because 110s passed; lastcall = {self.market_limiter.last_call}s")
                    self.mode = "BASE_API"
                self.firstRun = False
            except Exception as e:
                print("Worker error:", e)
                print("traceback:" + traceback.format_exc())
                play_sound()
                play_sound()
                Log.log_print()
                with open("RIVEN_ENDO_ERROR_LOG_" + QDateTime.currentDateTime().toString().replace(" ", "_").replace(":", "-") + ".txt", "w") as f:
                    f.write(QDateTime.currentDateTime().toString() + "\n")
                    f.write("Worker error: " + traceback.format_exc()+ "\n")
                    for log in Log.logs:
                        f.write(log + "\n")
                f.close


    def stop(self):
        self.running = False

    def enqueue_price_check(self, auction):
        self.price_queue.append(auction)

# =========================
# UI: Histogram Widget
# =========================
class ExternalGV(QWidget):
    def __init__(self, GV:QGraphicsView):
        super().__init__()
        layout = QVBoxLayout(GV)
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

    def plot(self, x, Ymat, numPlots = 3):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        i = 0
        colors = ["red", "green", "blue"]
        for line in Ymat:
            ax.plot(x, Ymat[i], color=colors[i]) #marker='o', markersize=1
            i = i + 1
            if i >= numPlots:
                break
        ax.grid()
        ax.set_xlabel("Время")
        ax.set_ylabel("Цена")
        self.canvas.draw()

# =========================
# UI: Main Window
# =========================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.modes_to_cooldown = {}

        self.plot = PricePlot(self.ui.weaponPlot)
        self.groll_plot = PricePlot(self.ui.grollPlot)

        self.alert_widgets: dict[str, RivenAlertWidget] = {}
        self.setWindowTitle("Warframe Riven Scanner + Analysis")
        self.resize(1000, 600)
        self.startupTime = time.time()
        self.scanTimes = []
        self.db = RivenDatabase()
        self.pod_roll_db = PodRollDB(Glob.good_weapons)
        #self.grollDB = MongoDBManager()
        self.podRollText = QTextEdit()
        self.worker = AuctionWorker(self.db, self.pod_roll_db)
        self.worker.price_checked.connect(self.on_price_checked)
        self.worker.alert_found.connect(self.on_alert)
        self.worker.newRivensCountUpdate.connect(self.on_new_rivens_updated)
        self.worker.pod_roll_progress.connect(self.on_pod_roll_progress)
        self.worker.groll_urls_progress.connect(self.on_groll_progress)

        self.analyser = RivenAnalyser(self.db, Analyser())
        #grollIDs = self.grollDB.get_all_ids()
        self.seen_ids = set()
        #for id in grollIDs:
        #    self.seen_ids.add(id)

        #говно с клода началось
        self.riven_model = RivenListModel()
        self.riven_model.groll_to_save.connect(self.db.insert_riven_to_dismiss)
        self.riven_model.plot_from_riven.connect(self.build_plot_from_riven)

        self.qml_widget = QQuickWidget()
        self.qml_widget.setMinimumWidth(800)
        self.qml_widget.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)
        self.qml_widget.rootContext().setContextProperty("rivenModel", self.riven_model)
        self.qml_widget.setSource(QUrl.fromLocalFile(
            str(Path(__file__).parent / "qml" / "RivenAlertsView.qml")
        ))
        # После загрузки QML (setSource):
        self.root = self.qml_widget.rootObject()
        self.root.setProperty(
            "videoSource",
            QUrl.fromLocalFile(r"C:/amyfiles/projects/rivenendo/penis/Frieren2.mp4")
        )
        self.root.setProperty("imageSource", QUrl.fromLocalFile(r"C:/amyfiles/projects/rivenendo/penis/Frieren.png"))
        self.root.changeVolume(0.1)
        #говно с клода закончилось

        self.worker.start()

        # ---------- Bumper UI ----------
        self.bumper_worker = None

        # Группа кнопок бампера
        self.bumper_group = QGroupBox("🚀 Market Bumper")
        bumper_layout = QVBoxLayout()

        btn_row = QHBoxLayout()
        self.bump_btn = QPushButton("⬆️ Поднять ордера (bump)")
        self.decrease_btn = QPushButton("📉 Снизить цены (-1p)")
        self.repost_btn = QPushButton("🔄 Перевыставить ривены")
        self.test_btn = QPushButton("🧪 Тест ривена")
        self.stop_bump_btn = QPushButton("🛑 Стоп")
        self.stop_bump_btn.setEnabled(False)

        self.bump_btn.clicked.connect(self.run_bump)
        self.decrease_btn.clicked.connect(self.run_decrease)
        self.repost_btn.clicked.connect(self.run_repost_rivens)
        self.test_btn.clicked.connect(self.test_riven_alert)
        self.stop_bump_btn.clicked.connect(self.stop_bumper)

        btn_row.addWidget(self.bump_btn)
        btn_row.addWidget(self.decrease_btn)
        btn_row.addWidget(self.repost_btn)
        btn_row.addWidget(self.test_btn)
        btn_row.addWidget(self.stop_bump_btn)

        self.bump_log = QTextEdit()
        self.bump_log.setReadOnly(True)
        if SVINKA_VSEGDA_VIDNA:
            self.bump_log.setMaximumHeight(120)
        else:
            self.bump_log.setMinimumHeight(300)
        self.bump_log.setPlaceholderText("Здесь будут логи бампера...")

        bumper_layout.addLayout(btn_row)
        bumper_layout.addWidget(self.bump_log)
        self.bumper_group.setLayout(bumper_layout)
        if SVINKA_VSEGDA_VIDNA:
            self.bumper_group.setMaximumHeight(170)
        else:
            self.bumper_group.setMinimumHeight(500)

        # ---------- UI Layout ----------
        #root = QWidget()
        #root_layout = QHBoxLayout(root)

        # Alerts panel
        self.rivenDataLayout = QVBoxLayout()
        self.updatesLCD = QLCDNumber()
        self.newRivensLCD = QLCDNumber()
        self.weaponInput = QLineEdit()
        self.buildWeaponPlot = QPushButton()

    # ---------- Riven Scanner методы ----------

    def test_riven_alert(self):
        import random

        fake_auction = {
            "id": f"test_{random.randint(1000,999999)}",
            "buyout_price": random.randint(50, 1000),
            "owner": {
                "ingame_name": "TestSeller",
                "status": "ingame"
            },
            "item": {
                "type": "riven",
                "weapon_url_name": "torid",
                "name": "Test Riven",
                "re_rolls": random.randint(0, 300),
                "attributes": [
                    {
                        "positive": True,
                        "url_name": "critical_chance",
                        "value": 180
                    },
                    {
                        "positive": True,
                        "url_name": "critical_damage",
                        "value": 120
                    },
                    {
                        "positive": True,
                        "url_name": "multishot",
                        "value": 110
                    },
                    {
                        "positive": False,
                        "url_name": "zoom",
                        "value": -80
                    }
                ]
            }
        }

        self.on_alert(fake_auction, "manual request")

    def run_bump(self):
        self._start_bumper("bump")

    def run_decrease(self):
        self._start_bumper("decrease")

    def run_repost_rivens(self):
        self._start_bumper("repost_rivens")

    def _start_bumper(self, mode):
        if self.bumper_worker and self.bumper_worker.isRunning():
            self.bump_log.append("⚠️ Бампер уже запущен!")
            return
        self.bump_log.clear()
        self.bumper_worker = BumperWorker(mode=mode)
        self.bumper_worker.log_signal.connect(self.bump_log.append)
        self.bumper_worker.finished.connect(self._on_bumper_finished)
        self.bump_btn.setEnabled(False)
        self.decrease_btn.setEnabled(False)
        self.repost_btn.setEnabled(False)
        self.stop_bump_btn.setEnabled(True)
        self.bumper_worker.start()

    def stop_bumper(self):
        if self.bumper_worker:
            self.bumper_worker.stop()

    def _on_bumper_finished(self):
        self.bump_btn.setEnabled(True)
        self.decrease_btn.setEnabled(True)
        self.repost_btn.setEnabled(True)
        self.stop_bump_btn.setEnabled(False)

    def on_alert(self, auction, reason):
        auc_id = auction.get("id")
        item = auction.get("item", {})
        owner = auction.get("owner", {})
        owner_name = owner.get("ingame_name", "UNKNOWN")
        weapon = item.get("weapon_url_name", "UNKNOWN")
        riven_name = item.get("name", "UNKNOWN")
        price = auction.get("buyout_price", 0)
        if auc_id in self.seen_ids:
            return
        if reason != "manual request" and reason != "sold riven":
            self.seen_ids.add(auc_id)
        if reason == "good stats":
            self.worker.enqueue_price_check(auction)
        if reason == "pod roll":
            Glob.altvmsg = f"/w {owner_name} Hi! I want to buy {weapon} {riven_name} for {price}p"
            Log.log_write(f"new alt+v msg: {Glob.altvmsg}")

        auc_id = auction["id"]
        if (auc_id,) in self.worker.grolls_to_dismiss:
            Log.log_write(f"dismissed riven with id {auc_id} suppressed")
            return
        if auc_id in RivenAlertWidget.alert_widgets:
            return
        #play_sound()
        item = QListWidgetItem()
        #widget = RivenAlertWidget(auction, item, reason, self.worker.weapon_rivens)
        #claude
        self.riven_model.addAlert(auction, reason, self.worker.weapon_rivens)

        #win.ui.listWidget.addItem(item)
        #win.ui.listWidget.setItemWidget(item, widget)
        #widget.groll_to_save.connect(self.db.insert_riven_to_dismiss)
        #widget.plot_from_riven.connect(self.build_plot_from_riven)
        RivenAlertWidget.alert_widgets[auc_id] = "widget"

    def closeEvent(self, e):
        try:
            if hasattr(self, "worker") and self.worker:
                self.worker.stop()

                if self.worker.isRunning():
                    self.worker.wait(5000)

            if hasattr(self, "bumper_worker") and self.bumper_worker:
                self.bumper_worker.stop()

                if self.bumper_worker.isRunning():
                    self.bumper_worker.wait(5000)

            if hasattr(self, "player"):
                self.player.stop()

        except Exception as ex:
            print("closeEvent error:", ex)

        e.accept()

    def on_price_checked(self, auc_id, prices):
        widget = RivenAlertWidget.alert_widgets.get(auc_id)
        if widget:
            widget.set_market_prices(prices)

    def on_new_rivens_updated(self, count):
        updates = win.ui.updatesLCD.value()
        win.ui.updatesLCD.display(updates + 1)
        now = time.time() - self.startupTime
        self.scanTimes.append(now/3600)
        print(f"Часов: {self.scanTimes[-1]}, или в минутах: {self.scanTimes[-1]*60}, или в секундах: {self.scanTimes[-1]*3600}")

    def draw_pod_roll_plot(self):
        weapon = win.ui.weaponComboBox.currentText()
        data = self.pod_roll_db.get_prices(weapon)
        plot_data = PodRollDB.prepare_plot(data)
        x, y = self.plot.filter_downward_outliers(plot_data[0], plot_data[int(win.ui.plotsCount.text())])
        times, prices = self.plot.insert_gaps(x, y)

        self.plot.set_data(times, prices)

    def draw_groll_plot(self):
        weapon = win.ui.grollWeaponComboBoX.currentText()
        stats = [win.ui.stat1.currentText(), win.ui.stat2.currentText(), win.ui.stat3.currentText()]
        stats.sort()
        product = weapon
        for stat in stats:
            product += stat
        product += win.ui.stat4.currentText()
        data = self.db.get_price_history(product)
        #x, y = self.groll_plot.filter_downward_outliers(data[0], data[1])
        times, prices = self.groll_plot.insert_gaps(data[0], data[1])

        self.groll_plot.set_data(times, prices)

    def build_plot_from_riven(self, auctiom):
        item = auctiom["item"]
        weapon = item["weapon_url_name"]
        attributes = item["attributes"]
        #проверка валидности статов
        if not weapon in groll_raw_stats:
            print("неверное оружие ривена, невозможно построить график")
            return
        constC = 0
        varC = 0
        pos_attributes = []
        neg = "none"
        varstat = "none"
        for att in attributes:
            if att["positive"] == True:
                pos_attributes.append(att["url_name"])
                if att["url_name"] in groll_raw_stats[weapon]["const"]:
                    constC += 1
                if att["url_name"] in groll_raw_stats[weapon]["var"]:
                    varC += 1
                    varstat = att["url_name"]
            else:
                neg = att["url_name"]
        if constC != 2 or varC != 1 or neg == "none" or varstat == "none":
            print(f"неверные статы ривена, невозможно построить график. статы: {constC} {varC} {neg} {varstat}")
            return
        win.ui.grollWeaponComboBoX.setCurrentText(weapon)
        constStats = groll_raw_stats[weapon]["const"]
        win.ui.stat1.setCurrentText(constStats[0])
        win.ui.stat2.setCurrentText(constStats[1])
        win.ui.stat3.setCurrentText(varstat)
        win.ui.stat4.setCurrentText(neg)
        self.draw_groll_plot()
        

    def save_pod_roll_weapons_to_json(self):
        try:
            with open(settings_path, "r") as f:
                settings_cur = json.load(f)
                text = win.ui.podRollText.toPlainText().split("\n")
                weapons = {}
                for line in text:
                    if line != "":
                        line_s = line.split(" ")
                        weapons[line_s[0]] = int(line_s[1])
                settings_cur["good_weapons"] = weapons
                Glob.good_weapons = weapons
                for weapon in weapons:
                    self.worker.pod_roll_db.create_weapon_table(weapon)
                self.worker.good_weapons_id = 0
                self.worker.good_weapons_list = list(Glob.good_weapons)
                self.worker.good_weapons_len = len(self.worker.good_weapons_list)
                self.worker.pod_roll_progress.emit(0)
            f.close()
            with open(settings_path, "w") as f:
                json.dump(settings_cur, f)
            f.close()
        except Exception as e:
            win.ui.lineEdit.setText("НЕ УДАЛОСЬ СОХРАНИТЬ ОРУЖИЯ ПОД РОЛЛ")
            print(e)
            return
        win.ui.lineEdit.setText("УДАЛОСЬ СОХРАНИТЬ ОРУЖИЯ ПОД РОЛЛ")
        Glob.settings = settings_cur
        win.ui.weaponComboBox.clear()
        weapons_to_box = Glob.settings["good_weapons"]
        for weapon in weapons_to_box:
            win.ui.weaponComboBox.addItem(weapon)


    def save_db_weapons_to_json(self):
        try:
            with open(settings_path, "r") as f:
                settings_cur = json.load(f)
                text = win.ui.DBweaponsText.toPlainText().split("\n")
                weapons = []
                for line in text:
                    if line != "":
                        weapons.append(line)
                for weapon in weapons:
                    if not weapon in Glob.good_weapons:
                        print(f"ERROR: Нет оружия {weapon} в списке оружий под ролл.")
                        Log.log_print(f"ERROR: Нет оружия {weapon} в списке оружий под ролл.")
                        win.ui.lineEdit.setText(f"ОШИБКА: Нет оружия {weapon} в списке оружий под ролл.")
                        play_sound()
                        play_sound()
                        return
                settings_cur["fast_weapons_list"] = weapons
                Glob.fast_weapons_list = weapons
                self.worker.fast_weap_id = 0
            f.close()
            with open(settings_path, "w") as f:
                json.dump(settings_cur, f)
            f.close()
        except Exception as e:
            win.ui.lineEdit.setText("НЕ УДАЛОСЬ СОХРАНИТЬ ОРУЖИЯ ДЛЯ УСКОРЕННОЙ ПРОВЕРКИ")
            print(e)
            return
        win.ui.lineEdit.setText("УДАЛОСЬ СОХРАНИТЬ ОРУЖИЯ ДЛЯ УСКОРЕННОЙ ПРОВЕРКИ")
        Glob.settings = settings_cur

    def save_cooldown(self):
        try:
            with open(settings_path, "r") as f:
                settings_cur = json.load(f)
                text = win.ui.cooldownInput.text()
                mode = win.ui.cooldownComboBox.currentText()
                val = Glob.mode_to_cooldown[mode]
                try:
                    val = float(text)
                except ValueError:
                    win.ui.lineEdit.setText("НЕВЕРНЫЙ ВВОД ВРЕМЕНИ! ВВЕДИ ЧИСЛО!")
                    print("НЕВЕРНЫЙ ВВОД ВРЕМЕНИ ОЖИДАНИЯ! ВВЕДИ ЧИСЛО!")
                    win.ui.cooldownInput.settext(Glob.mode_to_cooldown[mode])
                Glob.mode_to_cooldown[mode] = val
                Log.log_write(f"cooldown for {mode} changed to {val} s")
                settings_cur["cooldowns"] = Glob.mode_to_cooldown
            f.close()
            with open(settings_path, "w") as f:
                json.dump(settings_cur, f)
            f.close()
        except Exception as e:
            win.ui.lineEdit.setText("НЕ УДАЛОСЬ СОХРАНИТЬ ВРЕМЯ ОЖИДАНИЯ")
            print(e)
            return
        win.ui.lineEdit.setText("УДАЛОСЬ СОХРАНИТЬ ВРЕМЯ ОЖИДАНИЯ")
        Glob.settings = settings_cur

    def save_schedule_to_json(self):
        try:
            with open(settings_path, "r") as f:
                settings_cur = json.load(f)
                text = win.ui.scheduleText.toPlainText().split("\n")
                stages = []
                for line in text:
                    if line != "":
                        if line in MODE_TO_COOLDOWN:
                            stages.append(line)
                        else:
                            print(f"Ошибка: неверный режим: {line}")
                settings_cur["schedule"] = stages
                Glob.schedule = stages
            f.close()
            with open(settings_path, "w") as f:
                json.dump(settings_cur, f)
            f.close()
        except Exception as e:
            win.ui.lineEdit.setText("НЕ УДАЛОСЬ СОХРАНИТЬ РАСПИСАНИЕ")
            print(e)
            return
        Glob.settings = settings_cur
        secs = 3
        for mode in Glob.schedule:
            secs += Glob.mode_to_cooldown[mode]
        win.ui.lineEdit.setText(f"УДАЛОСЬ СОХРАНИТЬ РАСПИСАНИЕ; РАСЧЁТНОЕ ВРЕМЯ НА ВЫПОЛНЕНИЕ: {secs} СЕУНД")

    def on_plotCOunt_edited(self):
        val = win.ui.plotsCount.text()
        allowedDigits = ['1', '2', '3']
        if not val in allowedDigits:
            if int(val) > 3:
                win.ui.plotsCount.setText("3")
            else:
                win.ui.plotsCount.setText("1")

    def on_cooldown_edited(self):
        val_str = win.ui.cooldownInput.text()
        try:
            val = float(val_str)
        except ValueError:
            win.ui.lineEdit.setText("НЕВЕРНЫЙ ВВОД ВРЕМЕНИ! ВВЕДИ ЧИСЛО!")
            print("НЕВЕРНЫЙ ВВОД ВРЕМЕНИ ОЖИДАНИЯ! ВВЕДИ ЧИСЛО!")
            win.ui.cooldownInput.settext(Glob.mode_to_cooldown[win.ui.cooldownComboBox.currentText()])

    def init_groll_ui(self):
        for weapon in groll_raw_stats.keys():
            win.ui.grollWeaponComboBoX.addItem(weapon)
        self.update_groll_ui()

    def update_groll_ui(self):
        curWeapon = win.ui.grollWeaponComboBoX.currentText()
        constStats = groll_raw_stats[curWeapon]["const"]
        varStats = groll_raw_stats[curWeapon]["var"]
        win.ui.stat1.clear()
        win.ui.stat2.clear()
        win.ui.stat3.clear()
        win.ui.stat4.clear()
        win.ui.stat1.addItem(constStats[0])
        win.ui.stat2.addItem(constStats[1])
        for varstat in varStats:
            win.ui.stat3.addItem(varstat)
        for neg in ALL_STATS:
            win.ui.stat4.addItem(neg)

    def show_sold_grolls(self):
        weapon = win.ui.grollWeaponComboBoX.currentText()
        stats = [win.ui.stat1.currentText(), win.ui.stat2.currentText(), win.ui.stat3.currentText()]
        stats.sort()
        neg =  win.ui.stat4.currentText()
        product = weapon
        for stat in stats:
            product+=stat
        product += neg
        sold_rivens:list = self.worker.db.get_sold_rivens(product)
        if len(sold_rivens) == 0:
            print("no sold rivens")
        blacklist = get_blacklist()
        for riven in sold_rivens:
            riven["pos_stats"] = stats
            riven["neg_stat"] = neg
            riven["weapon_name"] = weapon
            riven["id"] = "0"
            if riven["owner_name"] in blacklist:
                riven["pidorstvo"] = blacklist[riven["owner_name"]]
            self.worker.alert_found.emit(riven, "sold riven")

    def on_pod_roll_progress(self, stage):
        upper_limit = len(self.worker.good_weapons_list)
        win.ui.podRollProgress.setMaximum(upper_limit)
        win.ui.podRollProgress.setValue(stage)

    def on_groll_progress(self, stage):
        win.ui.grollProgress.setValue(stage)

    def on_mode_combobox_changed(self):
        win.ui.cooldownInput.setText(str(Glob.mode_to_cooldown[win.ui.cooldownComboBox.currentText()]))

    def on_volume_changed(self):
        value = float(win.ui.volumeSlider.value()) / 100.0
        self.root.changeVolume(value)

def insertMSG():
    time.sleep(0.15)
    Log.log_write(f"trying to insert alt+v msg: {Glob.altvmsg}", logs = Log.altvLogs)
    pyautogui.write(Glob.altvmsg)
    time.sleep(0.05)

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    default_m_t_c = {"BASE_API": 3.0, "SYNC": 3.0, "FAST_SEARCH": 5.5, "WEAPON_FOR_DB_SEARCH": 5.5, "GROLL": 5.5}
    for mode, value_default in default_m_t_c.items():
        val = Glob.mode_to_cooldown.get(mode, -1)
        if val == -1:
            Glob.mode_to_cooldown[mode] = value_default
    Glob.settings["cooldowns"] = Glob.mode_to_cooldown
    with open(settings_path, "w") as f:
        json.dump(Glob.settings, f)
    win = MainWindow()
    for mode in default_m_t_c:
        win.ui.cooldownComboBox.addItem(mode)

    win.ui.buildWeaponPlot.pressed.connect(win.draw_pod_roll_plot)
    win.ui.buildGrollPlot.pressed.connect(win.draw_groll_plot)
    win.ui.pushButton.pressed.connect(Log.log_print)
    win.ui.pushButton.setText("Вывести логи")

    #setting text
    pod_weapons = Glob.settings["good_weapons"]
    weapons_DB = Glob.settings["fast_weapons_list"]
    sched = Glob.settings["schedule"]
    text = ""
    for weapon in pod_weapons:
        line = weapon + " " + str(pod_weapons[weapon])
        text = text + line + "\n"
    win.ui.podRollText.setText(text)  
    text = ""
    for weapon in weapons_DB:
        line = weapon
        text = text + line + "\n"
    win.ui.DBweaponsText.setText(text)
    text = ""
    for stage in sched:
        line = stage
        text = text + line + "\n"
    win.ui.scheduleText.setText(text) 
    weapons_to_box = Glob.settings["good_weapons"]
    for weapon in weapons_to_box:
        win.ui.weaponComboBox.addItem(weapon)
    win.init_groll_ui()
    win.ui.savePodRollBtn.pressed.connect(win.save_pod_roll_weapons_to_json)
    win.ui.saveBDweaponsBtn.pressed.connect(win.save_db_weapons_to_json)
    win.ui.saveScheduleBtn.pressed.connect(win.save_schedule_to_json)
    win.ui.plotsCount.textEdited.connect(win.on_plotCOunt_edited)
    win.ui.cooldownInput.textEdited.connect(win.on_cooldown_edited)
    win.ui.saveCooldown.pressed.connect(win.save_cooldown)
    win.ui.grollWeaponComboBoX.currentTextChanged.connect(win.update_groll_ui)
    win.ui.showGrollRivensForStats.pressed.connect(win.show_sold_grolls)
    win.ui.radioButton.clicked.connect(win.worker.on_turned_on_off)
    win.ui.cooldownComboBox.currentTextChanged.connect(win.on_mode_combobox_changed)
    win.ui.grollProgress.setMaximum(len(Glob.groll_urls))
    win.ui.podRollProgress.setMaximum(len(Glob.good_weapons))
    win.ui.volumeSlider.valueChanged.connect(win.on_volume_changed)
    log_printer.new_log.connect(win.ui.logsText.setText)

    #claude
    win.ui.verticalLayout_6.replaceWidget(win.ui.listWidget, win.qml_widget)
    #win.ui.listWidget.deleteLater()

    # Добавляем панель бампера в UI
    # Вставляем bumper_group в centralWidget или любой подходящий layout
    # Если в uis3.py есть вертикальный layout (например verticalLayout), делаем так:
    if not SVINKA_VSEGDA_VIDNA:
        try:
            win.ui.pigLayout.addWidget(win.bumper_group)
        except AttributeError:
            print("layout называется иначе — добавляем через centralWidget")
            # Если layout называется иначе — добавляем через centralWidget
            central = win.centralWidget()
            if central and central.layout():
                central.layout().addWidget(win.bumper_group)
    else:
        central = win.centralWidget()
        if central and central.layout():
            central.layout().addWidget(win.bumper_group)

    win.show()
    res = win.analyser.strepsils()
    result, model = win.analyser.analyser.smooth_prices(res["torid"])
    for key1, val1 in result.items():
        for key2, val2 in result[key1].items():
            result[key1][key2] = [result[key1][key2], res["torid"][key1][key2]]
    pretty_json2 = json.dumps(result, indent=4)
    print(pretty_json2)
    print(model)
    pretty_json = json.dumps(res, indent=4)
    print(pretty_json)
    if SVINKA_VSEGDA_VIDNA:
        win.ui.tab_4.deleteLater()
        #win.ui.tab_4.isVisible()
    keyboard.add_hotkey(ACTIVATE_KEY, insertMSG)
    #model.addAlert({
    #"reason": "good stats",
    #"weapon": "torid",
    #"price": 1200,
    #"owner": "Player123"
    #})
    sys.exit(app.exec())
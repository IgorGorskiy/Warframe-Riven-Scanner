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
#import winsound
import random
#import pyautogui
#import keyboard
import traceback
from collections import deque
from uis3 import Ui_MainWindow
from market_riven_api import MarketAPI, MarketBumperState, BumperWorker
from db import RivenDatabase, PodRollDB, SuperDatabase
from rivenwidgets import RivenAlertWidget
from prices_analysis import Analyser
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from myplot import PricePlot
from password_storage import CredentialsStorage
from log_printer import LogPrinter, Log
from auction_worker import AuctionWorker
from optimal_requester import UrlParameters
from riven_qml_bridge import value_to_color
import pandas as pd
import numpy as np

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QLabel, QPushButton, QListWidget, QListWidgetItem,
    QVBoxLayout, QHBoxLayout, QLineEdit, QGroupBox,
    QLCDNumber, QSpacerItem, QSizePolicy, QGraphicsView, QTextEdit,
    QMessageBox, QComboBox, QCompleter
)

from PySide6.QtCore import Qt, QSize, QDateTime, QStringConverter
from PySide6.QtCore import Signal, QThread, QObject, Qt
from PySide6.QtMultimedia import QMediaPlayer

# перевод rivenalertwidget на qml   
from PySide6.QtGui import QGuiApplication, QTextCursor
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
test_path = os.path.join(cur_dir, "test.json")

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

MODE_TO_COOLDOWN = {"main_page_auctions": 3.0, "fast_check": 7.0, "optimal_search": 7.0, "simple_history": 3.0}

BASE_WEAPONS_URL = "https://api.warframe.market/v1/auctions/search?type=riven&sort_by=price_asc&weapon_url_name="
API_AUCTIONS = "https://api.warframe.market/v1/auctions"
API_SEARCH = "https://api.warframe.market/v1/auctions/search?type=riven&positive_stats="
API_SEARCH2 = "&negative_stats="
API_SEARCH3 = "&sort_by=price_asc"

HEADERS = {"accept": "application/json", "platform": "pc"}
DB_PATH = "rivens.db"
CACHE_FILE = "/home/igor/Projects/warframe_projects/Warframe-Riven-Scanner/riven_cache.json"

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
    #weapons = ["torid"]
    for weapon in weapons:
        stats_for_weapon = raw_stats[weapon]
        var_stats = stats_for_weapon["var"]
        const_stats:list = stats_for_weapon["const"]
        for var_stat in var_stats:
             pos_stats = const_stats.copy()
             pos_stats.append(var_stat)
             url = build_URL(pos_stats, weapon)
             urls.append(url)
    print (f"amount of groll urls: {len(urls)}")
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
        play_sound(1000)
        #winsound.Beep(600, 300)
    except Exception:
        pass

# =========================
# WORKER THREAD
# =========================

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
        self.super_db = SuperDatabase()
        self.db = RivenDatabase()
        self.market_account = CredentialsStorage()
        self.pod_roll_db = PodRollDB(Glob.good_weapons)
        #self.grollDB = MongoDBManager()
        self.podRollText = QTextEdit()
        self.worker = AuctionWorker(self.db, self.pod_roll_db, self.super_db, CACHE_FILE)
        self.worker.alert_found.connect(self.on_alert)
        self.worker.newRivensCountUpdate.connect(self.on_new_rivens_updated)
        self.worker.pod_roll_progress.connect(self.on_pod_roll_progress)
        self.worker.groll_urls_progress.connect(self.on_groll_progress)
        self.worker.message_to_ui.connect(self.on_message_to_display)

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
            QUrl.fromLocalFile(r"/home/igor/Projects/warframe_projects/Warframe-Riven-Scanner/penis/Frieren2.mp4")
        )
        self.root.setProperty("imageSource", QUrl.fromLocalFile(r"/home/igor/Projects/warframe_projects/Warframe-Riven-Scanner/penis/Frieren.png"))
        self.root.changeVolume(0.1)
        self.ui.volumeSlider.setValue(10)
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

        class MyWidget(QWidget):
            def __init__(self):
                super().__init__()
                self.setWindowTitle("Автодополнение с валидацией")

                layout = QVBoxLayout(self)

                self.label = QLabel("Начните вводить текст:")
                layout.addWidget(self.label)

                self.line_edit = QLineEdit(self)
                layout.addWidget(self.line_edit)

                self.error_label = QLabel("")
                self.error_label.setStyleSheet("color: red;")
                layout.addWidget(self.error_label)

                # Допустимые варианты
                self.variants = ["Python", "PySide6", "PyQt6", "JavaScript", "Java", "Go", "Rust"]

                completer = QCompleter(self.variants, self)
                completer.setCaseSensitivity(Qt.CaseInsensitive)
                completer.setFilterMode(Qt.MatchContains)
                completer.setCompletionMode(QCompleter.PopupCompletion)
                self.line_edit.setCompleter(completer)

                # Проверка при каждом изменении текста
                self.line_edit.textChanged.connect(self.validate_input)

                # Начальное состояние
                self.validate_input(self.line_edit.text())

            def validate_input(self, text: str):
                is_valid = text in self.variants or text == ""

                if text == "":
                    # Пустое поле — нейтральное состояние, без ошибки
                    self.line_edit.setStyleSheet("")
                    self.error_label.setText("")
                elif is_valid:
                    self.line_edit.setStyleSheet(
                        "QLineEdit { border: 2px solid #2e7d32; background-color: #eaf6ea; }"
                    )
                    self.error_label.setText("")
                else:
                    self.line_edit.setStyleSheet(
                        "QLineEdit { border: 2px solid #c62828; background-color: #fdecea; }"
                    )
                    self.error_label.setText("Недопустимое значение")


        combo = MyWidget()

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

        #btn_row.addWidget(combo)

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

        fake_auction2 = {
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
        self.on_alert(fake_auction2, "manual request")

    def run_bump(self):
        self._start_bumper("bump")

    def run_decrease(self):
        self._start_bumper("decrease")

    def run_repost_rivens(self):
        self._start_bumper("repost_rivens")

    def run_bumper_test(self):
        self._start_bumper("test")

    def _start_bumper(self, mode):
        if self.bumper_worker and self.bumper_worker.isRunning():
            self.bump_log.append("⚠️ Бампер уже запущен!")
            return
        self.bump_log.clear()
        login, password, username = self.market_account.load()
        if login == "fail":
            win.ui.accountDataStasusDisplay.setText("Нет сохранённых данных для входа. Введите и сохраните данные.")
            return
        self.bumper_worker = BumperWorker(login, password, username, mode=mode)
        self.bumper_worker.log_signal.connect(self.bump_log.append)
        self.bumper_worker.finished.connect(self._on_bumper_finished)
        self.bumper_worker.testing_result.connect(self.on_bumper_testing_result)
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
                    self.worker.requestInterruption()
                    self.worker.wait()

            if hasattr(self, "bumper_worker") and self.bumper_worker:
                self.bumper_worker.stop()

                if self.bumper_worker.isRunning():
                    self.bumper_worker.wait()

            if hasattr(self, "player"):
                self.player.stop()

        except Exception as ex:
            print("closeEvent error:", ex)

        e.accept()

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
        weapons = {}
        try:
            text = win.ui.podRollText.toPlainText().split("\n")
            weapons = {}
            for line in text:
                if line != "":
                    line_s = line.split(" ")
                    weapons[line_s[0]] = int(line_s[1])
            self.worker.set_good_weapons(weapons)
            for weapon in weapons:
                self.worker.pod_roll_db.create_weapon_table(weapon)
            settings_cur = {}
            with open(settings_path, "r") as f:
                settings_cur = json.load(f)
                settings_cur["good_weapons"] = weapons
            with open(settings_path, "w") as f:
                json.dump(settings_cur, f)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка ввода", f"Ошибка: не удалось сохранить оружия под ролл. Сохранение не произведено.")
            print(e)
            return
        QMessageBox.information(self, "Успех", f"Оружия под ролл успешно сохранены")
        win.ui.weaponComboBox.clear()
        weapons_to_box = weapons
        for weapon in weapons_to_box:
            win.ui.weaponComboBox.addItem(weapon)

    def save_db_weapons_to_json(self):
        try:
            text = win.ui.DBweaponsText.toPlainText().split("\n")
            weapons = []
            for line in text:
                if line != "":
                    weapons.append(line)
            for weapon in weapons:
                if not weapon in self.worker.queue_manager.const_queues[self.worker.queue_manager.queues.fast_weapons]:
                    print(f"ERROR: Нет оружия {weapon} в списке оружий под ролл.")
                    Log.log_print(f"ERROR: Нет оружия {weapon} в списке оружий под ролл.")
                    QMessageBox.warning(self, "Ошибка", f"Нет оружия {weapon} в списке оружий под ролл. Сохранение не произведено.")
                    play_sound()
                    play_sound()
                    return
            self.worker.set_fast_weapons(weapons)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить оружия для ускоренной проверки. Сохранение не произведено.")
            print(e)
            return
        QMessageBox.information(self, "Успех", f"Оружия для ускоренной проверки успешно сохранены.")

    def save_cooldown(self):
        self.worker.set_cooldown(win.ui.cooldownComboBox.currentText(), win.ui.cooldownInput.text())

    def save_schedule_to_json(self):
        try:
            text = win.ui.scheduleText.toPlainText().split("\n")
            stages = []
            for line in text:
                if line != "":
                    if line in MODE_TO_COOLDOWN:
                        stages.append(line)
                    else:
                        print(f"Ошибка: неверный режим: {line}")
            self.worker.queue_manager.set_schedule(stages)
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить расписание.")
            print(e)
            return
        secs = 3
        for mode in self.worker.queue_manager.const_queues[self.worker.queue_manager.queues.modes_queue]:
            secs += self.worker.mode_to_cooldown[mode]
        QMessageBox.information(self, "Успех", f"Удалось сохранить расписание; расчётное время выполнения - {secs} секунд")

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
            QMessageBox.warning(self, "Ошибка", f"Неверный ввод времени. Введите число!")
            print("НЕВЕРНЫЙ ВВОД ВРЕМЕНИ ОЖИДАНИЯ! ВВЕДИ ЧИСЛО!")
            win.ui.cooldownInput.setText(self.worker.mode_to_cooldown[win.ui.cooldownComboBox.currentText()])

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
        return

    def on_pod_roll_progress(self, stage):
        return

    def on_groll_progress(self, stage):
        win.ui.grollProgress.setValue(stage)

    def on_mode_combobox_changed(self):
        win.ui.cooldownInput.setText(str(self.worker.mode_to_cooldown[win.ui.cooldownComboBox.currentText()]))

    def on_volume_changed(self):
        value = float(win.ui.volumeSlider.value()) / 100.0
        self.root.changeVolume(value)

    def on_bumper_testing_result(self, result:str):
        win.ui.accountDataStasusDisplay.setText(result)

    def on_save_account_data(self):
        login = win.ui.LoginInput.text()
        password = win.ui.PasswordInput.text()
        nickname = win.ui.NicknameInput.text()
        self.market_account.save(login, password, nickname)
        win.ui.LoginInput.setText("")
        win.ui.PasswordInput.setText("")
        win.ui.NicknameInput.setText("")

    def on_turned_on_off(self):
        if win.ui.radioButton.isChecked():
            self.worker.turned_off = False
        else:
            self.worker.turned_off = True

    def on_message_to_display(self, success, msg):
        if success:
            QMessageBox.information(self, "Успех", msg)
        else:
            if msg == "НЕВЕРНЫЙ ВВОД ВРЕМЕНИ! ВВЕДИ ЧИСЛО!":
                win.ui.cooldownInput.setText(self.worker.mode_to_cooldown[mode])
            QMessageBox.warning(self, "Ошибка", msg)

    def on_new_log(self, text):
        win.ui.logsText.setText(text)
        return
    
    def on_save_opt_req_queue(self):
        text = win.ui.opt_req_queue_edit.toPlainText().split("\n")
        url_params = []
        for line in text:
            if line != "":
                if line in self.worker.weapon_rivens:
                    url_params.append(UrlParameters(weapon=line))
                else:
                    print(f"Ошибка: неверное оружие: {line}")
                    QMessageBox.warning(
                        self,
                        "Ошибка ввода",
                        f"Ошибка: введено неверное оружие: {line}. Сохранение не произведено."
                    )
                    return
        QMessageBox.information(
                        self,
                        "Сохранено",
                        f"Очередь из оружий на проверку успешно сформирована"
                    )
        self.worker.set_url_params(url_params)

    def on_opt_req_progress(self, cur_param:UrlParameters, unprocessed:list[UrlParameters], processed:list[UrlParameters],):
        win.ui.opr_req_current_queue_text.setText("")
        if not (processed is None):
            for p in processed:
                win.ui.opr_req_current_queue_text.insertHtml(f'\n<span style="color:{value_to_color(90)};">{p.weapon}</span><br>')
        win.ui.opr_req_current_queue_text.insertHtml(f'\n<span style="color:{value_to_color(50)};">{cur_param.weapon}</span><br>')
        if not (unprocessed is None):
            for p in unprocessed:
                win.ui.opr_req_current_queue_text.insertHtml(f'\n<span style="color:{value_to_color(0)};">{p.weapon}</span><br>')

    def load_opt_req_queue_text_from_file(self):
        with open(settings_path, "r") as f:
            settings_cur = json.load(f)
            url_params = settings_cur["url_params"]
            win.ui.opt_req_queue_edit.setText("")
            for p in url_params:
                win.ui.opt_req_queue_edit.insertPlainText("\n" + p["weapon"])

def insertMSG():
    time.sleep(0.15)
    Log.log_write(f"trying to insert alt+v msg: {Glob.altvmsg}", logs = Log.altvLogs)
    #pyautogui.write(Glob.altvmsg)
    time.sleep(0.05)

# =========================
# ENTRY POINT
# =========================

if __name__ == "__main__":
    win = MainWindow()
    default_m_t_c = {"main_page_auctions": 3.0, "fast_check": 7.0, "optimal_search": 7.0, "simple_history": 3.0}
    for mode, value_default in default_m_t_c.items():
        val = win.worker.mode_to_cooldown.get(mode, -1)
        if val == -1:
            win.worker.set_cooldown(mode, str(value_default))
    for mode in default_m_t_c:
        win.ui.cooldownComboBox.addItem(mode)
    win.ui.cooldownInput.setText(str(win.worker.mode_to_cooldown[win.ui.cooldownComboBox.currentText()]))

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
    win.ui.radioButton.clicked.connect(win.on_turned_on_off)
    win.ui.cooldownComboBox.currentTextChanged.connect(win.on_mode_combobox_changed)
    win.ui.grollProgress.setMaximum(len(Glob.groll_urls))
    win.ui.podRollProgress.setMaximum(len(Glob.good_weapons))
    win.ui.volumeSlider.valueChanged.connect(win.on_volume_changed)
    win.ui.ensureAccountDataBtn.pressed.connect(win.run_bumper_test)
    win.ui.SaveMarketAccountData.pressed.connect(win.on_save_account_data)
    win.ui.save_opt_req_queue.pressed.connect(win.on_save_opt_req_queue)
    Log.log_printer.new_log.connect(win.on_new_log)
    win.worker.requester.queue_updated.connect(win.on_opt_req_progress)
    win.load_opt_req_queue_text_from_file()

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
    #res = win.analyser.strepsils()
    #result, model = win.analyser.analyser.smooth_prices(res["torid"])
    #for key1, val1 in result.items():
    #    for key2, val2 in result[key1].items():
    #        result[key1][key2] = [result[key1][key2], res["torid"][key1][key2]]
    #pretty_json2 = json.dumps(result, indent=4)
    #print(pretty_json2)
    #print(model)
    if SVINKA_VSEGDA_VIDNA:
        win.ui.tab_4.deleteLater()
        #win.ui.tab_4.isVisible()
    #keyboard.add_hotkey(ACTIVATE_KEY, insertMSG)
    sys.exit(app.exec())
import os
os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"

import sys
import time
import json
import sqlite3
import requests
import itertools
import random
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
from optimal_requester import OptimalRequester, UrlParameters
from rate_limiter import RateLimiter
from enums import modes, reasons_to_display
import pandas as pd
import numpy as np

from PySide6.QtCore import Signal, QThread, QObject

from pathlib import Path

from rate_limiter import RateLimiter

HEADERS = {"accept": "application/json", "platform": "pc"}
HEADERS2 = {"accept": "application/json", "platform": "pc", "Language": "ru"}
API_AUCTIONS = "https://api.warframe.market/v1/auctions"
BASE_WEAPONS_URL = "https://api.warframe.market/v1/auctions/search?type=riven&sort_by=price_asc&weapon_url_name="

cur_dir = os.path.dirname(os.path.abspath(__file__))
settings_path = os.path.join(cur_dir, "settings.json")

class QueueManager():
    """
    Отвечает за формирование временной очереди для различных задач.
    ---
    Концепция очередей для различной хуеты в данном модуле заключается в следующем:
    есть постоянный список и временный; постоянный список может изменяться извне в любой момент,
    временный же список копирует постоянный, когда завершится проход по временному списку.
    В процессе прохода по временному списку из него достаются элементы.
    
    Пример использования
    ---
    queue_manager.take_from_queue(QueueManager.queues.fast_weapons)
    """

    class queues:
        fast_weapons = "fw"
        modes_queue = "mq"
        mode_repetative = "mr"
        search_params = "sp"
        good_weapons = "gw"

    def __init__(self, settings_path, opt_req):
        super().__init__()
        self.settings_path = settings_path
        self.temporal_queues = {self.queues.good_weapons: deque(), self.queues.fast_weapons: deque(), self.queues.modes_queue: deque(),\
                                self.queues.mode_repetative: "", self.queues.search_params: deque()}
        self.const_queues = {self.queues.good_weapons: {}, self.queues.fast_weapons: [], self.queues.modes_queue: [],\
                                self.queues.mode_repetative: "", self.queues.search_params: []}
        self.load_schedule_from_settings_file()
        self.schedule_refresh()
        self.load_fast_weapons_from_settings_file()
        self.load_url_params_from_settings_file()
        self.fill_optimal_requester(opt_req, do_step=False)
        # с url params вышла накладка - OptimalRequester уже имеет свою очередь.
        # нужно подхватывать сигнал истощения очереди из OptimalRequester и заполнять его очередь из const_queue
        
    def set_const_queue(self, new_queue_list, new_queue_type):
        self.const_queues[new_queue_type] = new_queue_list

    def on_queue_exhausted(self, queue_type):
        self.temporal_queues[queue_type] = deque(self.const_queues[queue_type])

    def take_from_queue(self, queue_type):
        if not self.temporal_queues[queue_type]:
            #особый случай: когда кончились режимы в расписании - возвращаем повторяющийся режим
            #нужно, чтобы расписание режимов обновлялось после запроса главной страницы аукционов, а не после истощения.
            #то же самое для повторяющегося режима
            if queue_type == self.queues.modes_queue:
                return self.temporal_queues[self.queues.mode_repetative]
            self.on_queue_exhausted(queue_type)
        elem = self.temporal_queues[queue_type].popleft()
        return elem
    
    def force_update(self, queue_type):
        if queue_type == self.queues.mode_repetative:
            print("ERROR: mode_repetative in force_update")
            return
        self.temporal_queues[queue_type] = deque(self.const_queues[queue_type])

    def schedule_refresh(self):
        """
        для расписания режимов и для повторяющегося режима (вызывать, когда обновились ривены на главной маркета)
        """
        self.force_update(self.queues.modes_queue)
        self.temporal_queues[self.queues.mode_repetative] = self.const_queues[self.queues.mode_repetative]

    def load_schedule_from_settings_file(self):
        with open(self.settings_path) as f:
            settings = json.load(f)
            stages = settings.get("schedule", [])
            if len(stages) < 2:
                stages = [modes.optimal_search, modes.optimal_search]
                print("ERROR: cannot get schedule; using default schedule")
            self.set_const_queue(stages[:-1], self.queues.modes_queue)
            self.set_const_queue(stages[-1], self.queues.mode_repetative)

    def set_schedule(self, stages:list):
        self.set_const_queue(stages[:-1], self.queues.modes_queue)
        self.set_const_queue(stages[-1], self.queues.mode_repetative)
        # также записываем в файл
        settings = {}
        with open(self.settings_path) as f:
            settings = json.load(f)
        settings["schedule"] = stages
        with open(self.settings_path, "w") as f:
            json.dump(settings, f)

    def load_fast_weapons_from_settings_file(self):
        with open(self.settings_path) as f:
            settings = json.load(f)
            weapons = settings.get("fast_weapons_list", [])
            if len(weapons) < 1:
                weapons = ["magistar"]
                print("ERROR: cannot get fast_weapons_list; using default fast_weapons_list")
            self.set_const_queue(weapons, self.queues.fast_weapons)

    def set_fast_weapons(self, weapons:list):
        self.set_const_queue(weapons, self.queues.fast_weapons)
        # также записываем в файл
        settings = {}
        with open(self.settings_path) as f:
            settings = json.load(f)
        settings["fast_weapons_list"] = weapons
        with open(self.settings_path, "w") as f:
            json.dump(settings, f)

    def set_good_weapons(self, weapons:dict):
        self.set_const_queue(weapons, self.queues.good_weapons)

    def load_url_params_from_settings_file(self):
        with open(self.settings_path) as f:
            settings = json.load(f)
            params_dict = settings.get("url_params", [])
            if len(params_dict) < 1:
                params_dict = [{"weapon": "torid"}]
                print("ERROR: cannot get url_params; using default url_params")
            params_class = []
            for elem in params_dict:
                params_class.append(UrlParameters.from_dict(elem))
            self.set_const_queue(params_class, self.queues.search_params)

    def set_url_params(self, params:list[UrlParameters]):
        self.set_const_queue(params, self.queues.search_params)
        # также записываем в файл
        settings = {}
        with open(self.settings_path) as f:
            settings = json.load(f)
        params_dict = []
        for elem in params:
            params_dict.append(elem.to_dict())
        settings["url_params"] = params_dict
        with open(self.settings_path, "w") as f:
            json.dump(settings, f)

    def fill_optimal_requester(self, opt_req:OptimalRequester, do_step = True):
        Log.log_write("fill_optimal_requester")
        const_q = self.const_queues[self.queues.search_params]
        opt_req.clear_queue()
        for elem in const_q:
            opt_req.enqueue(elem)
        #долбаёбский код. Об истощении очереди узнаём когда уже не можем сделать запрос!
        #поэтому делаем запрос после дозаправки очереди - ведь предыдущая попытка запроса проебалась.
        #А опциональный параметр нужен для первой заправки реквестера - в этот момент do_step делать не надо.
        if do_step:
            opt_req.do_step()

class OptimalSchedule:
    """
    по запросу выдаёт тип следующей задачи для выполнения
    """
    def __init__(self, queue_manager:QueueManager):
        self.queue_manager = queue_manager
        self.current_stage_id = 0
        self.interval:float = float(120)
        self.unsynchronised = True
        self.init_time = time.time()
        self.refresh_time = time.time()

    #возвращает режим следующего запроса в соответствии с расписанием
    def get_stage(self):
        if self.unsynchronised:
            return modes.main_page_auctions
        current_time = time.time()
        if current_time > self.refresh_time:
            self.refresh_time += self.interval
            self.queue_manager.schedule_refresh()
            return modes.main_page_auctions
        stage_to_ret = self.queue_manager.take_from_queue(QueueManager.queues.modes_queue)
        return stage_to_ret

    def start_main_loop(self):
        if self.unsynchronised:
            Log.log_write("schedule execution starts now")
            self.unsynchronised = False
            self.refresh_time = time.time() + self.interval

def minutes_since_updated(updated_str: str) -> int:
    updated_dt = datetime.fromisoformat(updated_str)
    now = datetime.now(timezone.utc)
    delta = now - updated_dt
    return int(delta.total_seconds() // 60)

class AuctionWorker(QThread):
    alert_found = Signal(dict, str)
    newRivensCountUpdate = Signal(int)
    groll_urls_progress = Signal(int)
    pod_roll_progress = Signal(int)
    message_to_ui = Signal(str, str)
    rivens_for_superDB = Signal(list, int, float)

    def set_good_weapons(self, good_weapons):
        self.good_weapons = good_weapons
        self.queue_manager.set_good_weapons(good_weapons)

    def set_fast_weapons(self, fast_weapons_list):
        self.queue_manager.set_fast_weapons(fast_weapons_list)

    def set_url_params(self, params):
        self.queue_manager.set_url_params(params)

    def set_cooldown(self, mode, cooldown_text):
        mode_to_cooldown = {}
        try:
            with open(settings_path, "r") as f:
                settings_cur = json.load(f)
                text = cooldown_text
                mode_to_cooldown = settings_cur["cooldowns"]
                val = mode_to_cooldown[mode]
                try:
                    val = float(text)
                except ValueError:
                    print("НЕВЕРНЫЙ ВВОД ВРЕМЕНИ ОЖИДАНИЯ! ВВЕДИ ЧИСЛО!")
                    self.message_to_ui.emit("lineEdit", "НЕВЕРНЫЙ ВВОД ВРЕМЕНИ! ВВЕДИ ЧИСЛО!")
                mode_to_cooldown[mode] = val
                Log.log_write(f"cooldown for {mode} changed to {val} s")
                settings_cur["cooldowns"] = mode_to_cooldown
            with open(settings_path, "w") as f:
                json.dump(settings_cur, f)
            f.close()
        except Exception as e:
            self.message_to_ui.emit("lineEdit", "НЕ УДАЛОСЬ СОХРАНИТЬ ВРЕМЯ ОЖИДАНИЯ")
            print(e)
            return
        self.message_to_ui.emit("lineEdit", "УДАЛОСЬ СОХРАНИТЬ ВРЕМЯ ОЖИДАНИЯ")
        self.mode_to_cooldown = mode_to_cooldown

    def load_data_from_settings_file(self, file_path:str):
        with open(file_path) as f:
            settings = json.load(f)
            good_weapons = settings.get("good_weapons", {})
            if len(good_weapons) < 1:
                good_weapons = {"magistar": 200, "verglas": 200, "torid": 100}
                print("ERROR: cannot get good_weapons; using default good_weapons")
            self.good_weapons = good_weapons
            self.queue_manager.set_const_queue(good_weapons, QueueManager.queues.good_weapons)

            fast_weapons_list = settings.get("fast_weapons_list", [])
            if len(fast_weapons_list) < 1:
                fast_weapons_list = ["magistar", "verglas", "torid"]
                print("ERROR: cannot get fast_check_weapons; using default fast_check_weapons")
            self.queue_manager.set_const_queue(fast_weapons_list, QueueManager.queues.fast_weapons)

            self.mode_to_cooldown = settings.get("cooldowns", {})

    def check_riven_for_endo(self, auction):
        buyout = auction.get("buyout_price")
        item = auction.get("item", {})
        if not buyout or buyout <= 1:
            return
        if item.get("type") != "riven":
            return
        re_rolls = item.get("re_rolls", 0)
        if re_rolls / buyout > 3 and re_rolls > 50:
            self.alert_found.emit(auction, reasons_to_display.endo)
        else:
            return
        
    def check_below_set_price(self, auction):
        buyout = auction.get("buyout_price")
        item = auction.get("item", {})
        if not buyout or buyout <= 1:
            return
        if item.get("type") != "riven":
            return
        updated = auction.get("updated")
        weapon = item.get("weapon_url_name")
        if minutes_since_updated(updated) > 4:
            return
        if weapon in self.good_weapons and buyout <= self.good_weapons[weapon]:
            self.alert_found.emit(auction, reasons_to_display.below_max_price)
        else:
            return
        
    def on_optimal_requester_queue_exhausted(self):
        self.queue_manager.fill_optimal_requester(self.requester)

    def process_optimal_requester_auctions(self, current_params:UrlParameters, auctions:list, start_time:float, end_time:float):
        # сначала проверяем, есть ли среди полученных аукционов интересные
        # проверяем абсолютно все ауки на случай изменений
        self.process_auctions(auctions, set())
        # затем заносим информацию обо всех аукционах в БД (доделать!) доделано)
        search_hash = current_params.__hash__()
        #self.super_db.process_rivens_from_requester(auctions, search_hash, end_time)
        self.rivens_for_superDB.emit(auctions, search_hash, end_time)

    def process_auctions(self, auctions, seen_auctions:set):
        # в качестве аргумента seen_auctions будут поступать РАЗНЫЕ списки -> один аукцион может быть проверен дважды
        # такая хуета должна пресекаться на уровне выше - там, куда придут заэмиченные аукционы
        newAuctions = 0
        for auction in auctions:
            auc_id = auction.get("id")
            if not (auc_id in seen_auctions):
                self.check_below_set_price(auction)
                self.check_riven_for_endo(auction)
                # нужно доделать оценщик ривенов на основе базы данных
                #evaluate_riven(auction)
                seen_auctions.add(auc_id)
                newAuctions += 1
        return newAuctions

    def do_fast_check(self):
        weapon = self.queue_manager.take_from_queue(self.queue_manager.queues.fast_weapons)
        r = self.rate_limiter.get_response(BASE_WEAPONS_URL + weapon, self.mode_to_cooldown[modes.fast_check], HEADERS, 10)
        auctions = r.json()["payload"]["auctions"]
        self.process_auctions(auctions, self.processed_fast_auctions_ids)
        self.update_simple_database(auctions)

    def process_main_page(self, responce):
        # отличаем первую порцию аукционов по количеству новых: если около 100 - значит, только началась работа
        auctions = responce.json()["payload"]["auctions"]
        newRivensCount = self.process_auctions(auctions, self.processed_main_page_auctions_ids)
        # если слишком много аукционов -> первый запрос -> не засчитываем как обновление данных с маркета
        if newRivensCount > 80:
            return
        elif newRivensCount > 0:
            # это не первый запрос, и есть новые ривены -> получили время обновления данных на маркете
            # можем начинать выполнение прописанного пользователем расписания
            # не опасаемся повторных вызовов - функция ничего не делает, если была вызвана до этого
            self.newRivensCountUpdate.emit(newRivensCount)
            self.schedule_manager.start_main_loop()

    def process_simple_price_history_request(self):
        weapon = ""
        i = 0
        while True:
            i += 1
            if i > 1000:
                print("ERROR: cannot get good weapon that is not in fast-check-list")
                return
            weapon = self.queue_manager.take_from_queue(self.queue_manager.queues.good_weapons)
            if weapon in self.queue_manager.queues.fast_weapons:
                continue
            else:
                break
        if weapon == "":
            print("ERROR: cannot get good weapon")
            return
        r = self.rate_limiter.get_response(BASE_WEAPONS_URL + weapon, self.mode_to_cooldown[modes.simple_price_history], HEADERS, 10)
        auctions = r.json()["payload"]["auctions"]
        self.process_auctions(auctions, self.processed_fast_auctions_ids)
        self.update_simple_database(auctions)

    def update_simple_database(self, auctions):
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

    def __init__(self, db: RivenDatabase, pod_roll_db:PodRollDB, super_db:SuperDatabase, cache_path:str):
        super().__init__()
        self.market_limiter = RateLimiter(2)  # 2 запрос / сек
        r = self.market_limiter.get_response("https://api.warframe.market/v2/riven/weapons", 2, HEADERS2, 10)
        weapons = r.json()["data"]
        self.weapon_rivens = {}
        for w in weapons:
            self.weapon_rivens[w["slug"]] = w
        self.price_queue = deque()
        self.super_db = super_db
        self.rivens_for_superDB.connect(self.super_db.process_rivens_from_requester)
        self.db = db
        self.pod_roll_db = pod_roll_db
        self.grolls_to_dismiss = self.db.get_dismiss_list()
        self.rate_limiter = RateLimiter(3)
        self.requester = OptimalRequester(self.rate_limiter)
        self.requester.load_cache_from_file(cache_path)
        self.requester.auctions_ready.connect(self.process_optimal_requester_auctions)
        self.queue_manager = QueueManager(settings_path, self.requester)
        self.schedule_manager = OptimalSchedule(self.queue_manager)
        self.good_weapons = {}
        self.mode_to_cooldown = {}
        self.turned_off = False
        self.grolls_to_dismiss = list()

        self.processed_main_page_auctions_ids = set()
        self.processed_fast_auctions_ids = set()
        self.processed_auctions_from_requester = set()

        self.load_data_from_settings_file(settings_path)
        self.running = True

        def on_ready(params, auctions, t_start, t_end):
            Log.log_write(
                f"\n=== ГОТОВО: {params} — {len(auctions)} аукционов "
                f"за {t_end - t_start:.1f} с ==="
            )
            # После каждого успешного результата сохраняем кэш
            self.requester.save_cache_to_file(cache_path)
        self.requester.auctions_ready.connect(on_ready)

    def run(self):
        while self.running and (not self.isInterruptionRequested()):
            start_time = time.perf_counter()
            if self.turned_off:
                time.sleep(1)
                continue
            try:
                mode = self.schedule_manager.get_stage()
                Log.log_write(f"Итерация началась, mode = {mode}")
                if mode == modes.optimal_search:
                    # поскольку requester хранит свой кулдаун внутри себя, задаём ему кулдаун перед каждым его использованием.
                    self.requester.set_cooldown(self.mode_to_cooldown[modes.optimal_search])
                    done = self.requester.do_step()
                    if not done:
                        self.on_optimal_requester_queue_exhausted()
                        done = self.requester.do_step()
                        if not done:
                            print("ERROR: failed to fill requester queue")
                elif mode == modes.main_page_auctions:
                    r = self.rate_limiter.get_response(API_AUCTIONS, self.mode_to_cooldown[modes.main_page_auctions], HEADERS, 10)
                    self.process_main_page(r)
                elif mode == modes.fast_check:
                    self.do_fast_check()
                elif mode == modes.simple_price_history:
                    self.process_simple_price_history_request()
                    
            except Exception as e:
                print("Worker error:", e)
                print("traceback:" + traceback.format_exc())
            end_time = time.perf_counter()
            execution_time = end_time - start_time
            Log.log_write(f"Итерация выполнилась за {execution_time:.4f} секунд, mode = {mode}")

    def stop(self):
        self.running = False
        self.rate_limiter.running = False
import os
os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"
import time
import json
import requests
from pathlib import Path
from PySide6.QtWidgets import QScroller

from PySide6.QtCore import Signal, QThread, QObject

cur_dir = os.path.dirname(os.path.abspath(__file__))

#содержимое файла marketLogin.json должно выглядеть так:

{
    "login": "ваш логин",
    "password": "ваш пароль",
    "nickname": "ваш ник на маркете"
}

#конец содержимого
BUMP_DELAY = 0.3
MIN_INTERVAL_PER_ORDER = 60

class MarketAPI:
    """API клиент для управления ордерами на warframe.market"""

    def __init__(self, login, password, username):
        self.login_str = login
        self.password =  password
        self.token = None
        self.last_status = 0
        self.last_response = ""
        self.nickname = username

    def login(self):
        self.session = requests.Session()
        r = self.session.post(
            "https://api.warframe.market/v1/auth/signin",
            json={
                "auth_type": "header",
                "email": self.login_str,
                "password": self.password,
                "device_id": f"bot-{int(time.time())}"
            },
            headers={
                "Content-Type": "application/json",
                "Platform": "pc",
                "Language": "ru",
                "Authorization": "JWT"
            }
        )
        if r.status_code != 200:
            return False, f"Ошибка логина: {r.status_code} | {r.text[:200]}"
        auth = r.headers.get("Authorization", "").strip()
        if auth.upper().startswith("JWT "):
            auth = auth[4:].strip()
        if not auth:
            return False, f"Токен не найден. Headers: {dict(r.headers)}"
        self.token = auth
        return True, "OK"

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Platform": "pc",
            "Language": "ru",
            "Authorization": f"Bearer {self.token}"
        }

    def _headers_v1(self):
        return {
            "Content-Type": "application/json",
            "Platform": "pc",
            "Language": "ru",
            "Authorization": f"JWT {self.token}"
        }

    def get_orders(self):
        r = self.session.get(
            "https://api.warframe.market/v2/orders/my",
            headers=self._headers()
        )
        data = r.json()
        return data.get("data", [])
    
    def get_orders_by_nickname(self, nickname):
        r = self.session.get(
            "https://api.warframe.market/v2/profile/" + nickname + "/orders",
            headers=self._headers()
        )
        print("https://api.warframe.market/v2/profile/" + nickname + "/orders")
        if r.status_code != 200:
            return {}
        data = r.json()
        return data.get("data", [])

    def update_price(self, order_id, price):
        r = self.session.patch(
            f"https://api.warframe.market/v2/order/{order_id}",
            headers=self._headers(),
            json={"platinum": price}
        )
        return r.status_code == 200

    def get_my_auctions(self):
        r = self.session.get(
            "https://api.warframe.market/v1/profile/" + self.nickname + "/auctions",
            headers=self._headers_v1()
        )
        if r.status_code != 200:
            return []
        return r.json().get("payload", {}).get("auctions", [])

    def close_auction(self, auction_id):
        r = self.session.put(
            f"https://api.warframe.market/v1/auctions/entry/{auction_id}/close",
            headers=self._headers_v1()
        )
        self.last_status = r.status_code
        self.last_response = r.text[:200]
        return r.status_code == 200

    def create_auction(self, item, buyout_price, minimal_reputation=0, note=""):
        attributes = []
        for att in item.get("attributes", []):
            attributes.append({
                "url_name": att["url_name"],
                "value": att["value"],
                "positive": att["positive"]
            })
        payload = {
            "item": {
                "type": "riven",
                "weapon_url_name": item["weapon_url_name"],
                "name": item.get("name", ""),
                "mod_rank": item.get("mod_rank", 0),
                "re_rolls": item.get("re_rolls", 0),
                "polarity": item.get("polarity", "madurai"),
                "mastery_level": item.get("mastery_level") or 16,
                "attributes": attributes
            },
            "buyout_price": buyout_price,
            "starting_price": buyout_price,
            "minimal_reputation": minimal_reputation,
            "note": note,
        }
        r = self.session.post(
            "https://api.warframe.market/v1/auctions/create",
            headers=self._headers_v1(),
            json=payload
        )
        return r.status_code == 200, r.json() if r.status_code != 200 else {}


class MarketBumperState:
    """Хранит состояние кулдаунов между запусками"""

    def __init__(self):
        self.file = Path("bumper_config.json")
        self.data = self._load()

    def _load(self):
        if not self.file.exists():
            return {}
        try:
            return json.loads(self.file.read_text())
        except:
            return {}

    def save(self):
        self.file.write_text(json.dumps(self.data, indent=2))

    def can_bump(self, oid):
        last = self.data.get(oid, 0)
        return (time.time() - last) >= MIN_INTERVAL_PER_ORDER

    def mark(self, oid):
        self.data[oid] = time.time()
        self.save()


class BumperWorker(QThread):
    """Поток для выполнения bump/снижения цен"""
    log_signal = Signal(str)
    finished = Signal()
    testing_result = Signal(str)

    def __init__(self, login, password, username, mode="bump"):
        self.login = login
        self.password = password
        self.username = username
        super().__init__()
        self.mode = mode  # "bump" или "decrease"
        self.running = True

    def update_single_auction(self, a, errors, bumped):
        if not self.running:
            self.log_signal.emit("🛑 Остановлено")
            return False
        auc_id = a["id"]
        item = a.get("item", {})
        weapon = item.get("weapon_url_name", "unknown")
        buyout = a.get("buyout_price")
        note = a.get("note", "")
        minimal_rep = a.get("minimal_reputation", 0)
        if not buyout:
            self.log_signal.emit(f"⏭ [{weapon}] нет buyout — пропуск")
            skipped += 1
            return False
        self.log_signal.emit(f"🗑 [{weapon}] удаляю ({buyout}p)...")
        if not self.api.close_auction(auc_id):
            self.log_signal.emit(f"❌ [{weapon}] не удалось удалить (код: {self.api.last_status} | {self.api.last_response})")
            errors += 1
            return False
        time.sleep(0.5)
        self.log_signal.emit(f"➕ [{weapon}] создаю заново ({buyout}p)...")
        ok, err = self.api.create_auction(item, buyout, minimal_rep, note)
        if ok:
            self.log_signal.emit(f"✅ [{weapon}] перевыставлен ({buyout}p)")
            bumped += 1
        else:
            self.log_signal.emit(f"❌ [{weapon}] ошибка: {err}")
            errors += 1
        time.sleep(1.0)
        return True

    def run(self):
        self.log_signal.emit("🔐 Авторизация...")
        self.api = MarketAPI(self.login, self.password, self.username)
        ok, msg = self.api.login()
        if not ok:
            self.log_signal.emit(f"❌ {msg}")
            self.finished.emit()
            if self.mode == "test":
                self.testing_result.emit(f"❌ Не удалось авторизоваться. | {msg}")
            return
        self.log_signal.emit("✅ Авторизован")

        bumped = 0
        skipped = 0
        errors = 0

        if self.mode in ("bump", "decrease"):
            orders = self.api.get_orders()
            #sell_orders = [o for o in orders if o.get("type") == "sell"]
            sell_orders = orders
            self.log_signal.emit(f"📦 Найдено ордеров на продажу: {len(sell_orders)}")
            state = MarketBumperState()

            for o in sell_orders:
                if not self.running:
                    self.log_signal.emit("🛑 Остановлено")
                    break

                oid = o["id"]
                price = o["platinum"]
                item = o.get("item", {}).get("slug", "unknown")

                if self.mode == "decrease":
                    if price <= 15:
                        self.log_signal.emit(f"⏭ [{item}] {price}p — минимум, пропуск")
                        skipped += 1
                        continue
                    new_price = price - 1
                    if self.api.update_price(oid, new_price):
                        self.log_signal.emit(f"✅ [{item}] {price}p → {new_price}p")
                        bumped += 1
                    else:
                        self.log_signal.emit(f"❌ [{item}] ошибка при изменении цены")
                        errors += 1

                elif self.mode == "bump":
                    if not state.can_bump(oid):
                        self.log_signal.emit(f"⏭ [{item}] кулдаун")
                        skipped += 1
                        continue
                    if self.api.update_price(oid, price):
                        self.log_signal.emit(f"✅ [{item}] поднят ({price}p)")
                        state.mark(oid)
                        bumped += 1
                    else:
                        self.log_signal.emit(f"❌ [{item}] ошибка при поднятии")
                        errors += 1

                time.sleep(BUMP_DELAY)

        elif self.mode == "repost_rivens":
            auctions = self.api.get_my_auctions()
            self.log_signal.emit(f"📦 Найдено аукционов (ривенов): {len(auctions)}")

            for a in auctions:
                self.update_single_auction(a, errors, bumped)

        elif self.mode == "test":
            auctions = self.api.get_my_auctions()
            if len(auctions) < 1:
                self.testing_result.emit("Для сохранённого никнейма нет ордеров на маркете. Это не позволяет провести тест работы свинки")
                return
            a = auctions[0]
            errors = 0
            if self.update_single_auction(a, errors, bumped):
                self.testing_result.emit("ВСЁ ЗАЕБИСЬ, МОЖНО ПОЛЬЗОВАТЬСЯ СВИНКОЙ")
            else:
                self.testing_result.emit("❌ Тест обновления ривена провален. Проверь правильность НИКНЕЙМА!")

        self.log_signal.emit("─" * 30)
        self.log_signal.emit(f"✅ Выполнено: {bumped} | ⏭ Пропущено: {skipped} | ❌ Ошибок: {errors}")
        self.finished.emit()

    def stop(self):
        self.running = False
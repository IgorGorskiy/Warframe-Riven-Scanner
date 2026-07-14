DB_PATH = "rivens.db"
import sqlite3
import json
import os
from typing import List, Tuple
import copy

from datetime import datetime, time, date, timezone, timedelta
import time

def are_values_close(arg1, arg2, max_difference_percentage):
    abs_dif = abs(arg1 - arg2)
    relation = abs_dif / arg1
    if relation < (max_difference_percentage/100):
        return True
    return False

class RivenDatabase:
    def __init__(self, path=None):
        if path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "groll.db")
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_schema()

    def _init_schema(self):
        try:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS prices (
                id INTEGER PRIMARY KEY,
                product_id INTEGER,
                price INTEGER,
                timestamp INTEGER NOT NULL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS sold_rivens (
                id INTEGER PRIMARY KEY,
                product_id INTEGER,
                price INTEGER,
                timestamp INTEGER NOT NULL,
                last_checked INTEGER NOT NULL,
                last_updated INTEGER NOT NULL,
                owner_name TEXT,
                value1 REAL,
                value2 REAL,
                value3 REAL,
                value4 REAL,
                FOREIGN KEY(product_id) REFERENCES products(id)
            )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rivens_to_dismiss (
                id INTEGER PRIMARY KEY,
                riven_id TEXT
            )
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_prices_product_time
            ON prices (product_id, timestamp)
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_sold_product_time
            ON sold_rivens (product_id, timestamp)
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_riv_id
            ON rivens_to_dismiss (riven_id)
            """)
            self.conn.commit()
        except Exception as e:
            print ("podroll dp init failed")


    def insert_riven_to_dismiss(
    self,
    riven_id: str,
    ):
        try:
            self.cursor.execute("""
                INSERT INTO rivens_to_dismiss (riven_id)
                VALUES (?)
            """, (riven_id,))

            self.conn.commit()
        except Exception as e:
            print("insert_riven_to_dismiss failed")

    def get_dismiss_list(self):
        try:
            self.cursor.execute("""
                SELECT riven_id
                FROM rivens_to_dismiss
                ORDER BY riven_id
            """)

            rows = self.cursor.fetchall()
            ids = []
            for ts in rows:
                ids.append(ts)

            return ids
        except Exception as e:
            print ("get_price_history failed")

    def insert_price(
    self,
    product: str,
    price: int,
    timestamp: int = None
    ):
        try:
            if timestamp is None:
                timestamp = int(time.time())

            # Пытаемся получить id товара
            self.cursor.execute("""
                SELECT id FROM products WHERE name=?
            """, (product,))
            row = self.cursor.fetchone()
            if row is None:
                # Товара нет — создаём
                self.cursor.execute("""
                    INSERT INTO products (name) VALUES (?)
                """, (product,))
                product_id = self.cursor.lastrowid
            else:
                product_id = row[0]

            # Вставляем цену
            self.cursor.execute("""
                INSERT INTO prices (product_id, price, timestamp)
                VALUES (?, ?, ?)
            """, (product_id, price, timestamp))

            self.conn.commit()
        except Exception as e:
            print("price insertion failed")


    def insert_sold_riven(
    self,
    auc,
    product: str,
    ):
        try:
            # Пытаемся получить id товара
            self.cursor.execute("""
                SELECT id FROM products WHERE name=?
            """, (product,))
            row = self.cursor.fetchone()
            if row is None:
                # Товара нет — создаём
                self.cursor.execute("""
                    INSERT INTO products (name) VALUES (?)
                """, (product,))
                product_id = self.cursor.lastrowid
            else:
                product_id = row[0]

            # Вставляем данные
            self.cursor.execute("""
                INSERT INTO sold_rivens (product_id, price, timestamp, last_checked, last_updated, owner_name, value1, value2, value3, value4)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (product_id, auc["price"], auc["ts"], auc["last_checked"], auc["last_updated"], auc["owner_name"], auc["value1"], auc["value2"], auc["value3"], auc["value4"]))

            self.conn.commit()
        except Exception as e:
            print(e)
            print("sold riven insertion failed")
    
    def get_price_history(self, product: str):
        try:
            # Получаем id товара
            self.cursor.execute("""
                SELECT id FROM products WHERE name=?
            """, (product,))
            row = self.cursor.fetchone()

            if row is None:
                print(f"no data for {product}")
                return [[], []]  # товара нет

            product_id = row[0]

            # Получаем историю цен
            self.cursor.execute("""
                SELECT timestamp, price
                FROM prices
                WHERE product_id=?
                ORDER BY timestamp
            """, (product_id,))

            rows = self.cursor.fetchall()

            # Разделяем на два списка
            t = []
            prices = []

            for ts, price in rows:
                t.append(ts)
                prices.append(price)

            return [t, prices]
        except Exception as e:
            print ("get_price_history failed")
            return [[],[]]

    def get_sold_rivens(self, product: str):
        try:
            # Получаем id товара
            self.cursor.execute("""
                SELECT id FROM products WHERE name=?
            """, (product,))
            row = self.cursor.fetchone()

            if row is None:
                print(f"no data for {product}")
                return []  # товара нет

            product_id = row[0]

            # Получаем все проданные ривены
            self.cursor.execute("""
                SELECT timestamp, price, last_checked, last_updated, owner_name, value1, value2, value3, value4
                FROM sold_rivens
                WHERE product_id=?
                ORDER BY timestamp
            """, (product_id,))

            rows = self.cursor.fetchall()

            # Разделяем на два списка
            myaucs = []

            for ts, price, last_checked, last_updated, owner_name, value1, value2, value3, value4 in rows:
                auc = {}
                auc["ts"] = ts
                auc["price"] = price
                auc["last_checked"] = last_checked
                auc["last_updated"] = last_updated
                auc["owner_name"] = owner_name
                auc["value1"] = value1
                auc["value2"] = value2
                auc["value3"] = value3
                auc["value4"] = value4
                myaucs.append(auc)

            return myaucs
        except Exception as e:
            print ("get_sold_rivens failed")

    def delete_sold_riven(self, product: str, owner_name):
        try:
            # Получаем id товара
            self.cursor.execute("""
                SELECT id FROM products WHERE name=?
            """, (product,))
            row = self.cursor.fetchone()

            if row is None:
                print(f"no data for {product}")
                return [[], []]  # товара нет

            product_id = row[0]

            # Удаляем ривен
            self.cursor.execute("""
                DELETE FROM sold_rivens
                WHERE product_id=? AND
                owner_name=?;
            """, (product_id, owner_name))

            # Разделяем на два списка

            self.conn.commit()
        except Exception as e:
            print ("delete_sold_riven failed")

class PodRollDB:
    def __init__(self, good_weapons, db_path: str = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(base_dir, "podroll.db")
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        for weapon in good_weapons:
            self.create_weapon_table(weapon)

    def close(self):
        self.conn.close()

    # -----------------------------
    # Utility
    # -----------------------------

    @staticmethod
    def _normalize_table_name(weapon_name: str) -> str:
        return (
            weapon_name.lower()
            .replace(" ", "_")
            .replace("-", "_")
        )

    # -----------------------------
    # Table management
    # -----------------------------

    def create_weapon_table(self, weapon_name: str):
        table_name = self._normalize_table_name(weapon_name)

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                timestamp INTEGER NOT NULL,
                price1 INTEGER NOT NULL,
                price2 INTEGER NOT NULL,
                price3 INTEGER NOT NULL
            )
        """)

        self.cursor.execute(f"""
            CREATE INDEX IF NOT EXISTS idx_{table_name}_timestamp   
            ON {table_name} (timestamp)
        """)

        self.conn.commit()

    # -----------------------------
    # Insert data
    # -----------------------------

    def insert_prices(
        self,
        weapon_name: str,
        price1: int,
        price2: int,
        price3: int,
        timestamp: int = None
    ):
        table_name = self._normalize_table_name(weapon_name)

        if timestamp is None:
            timestamp = int(time.time())

        self.cursor.execute(f"""
            INSERT INTO {table_name}
            (timestamp, price1, price2, price3)
            VALUES (?, ?, ?, ?)
        """, (timestamp, price1, price2, price3))

        self.conn.commit()

    # -----------------------------
    # Query data
    # -----------------------------

    def get_prices_in_period(
        self,
        weapon_name: str,
        period: int,
        offset: int
    ) -> List[Tuple[int, int, int, int]]:
        """
        Возвращает список кортежей:
        (timestamp, price1, price2, price3)
        """

        now = int(time.time())
        table_name = self._normalize_table_name(weapon_name)

        self.cursor.execute(f"""
            SELECT *
            FROM {table_name}
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp
        """, (now - (period + offset)*3600, now - offset*3600))

        return self.cursor.fetchall()
    

    def get_prices(
        self,
        weapon_name: str,
    ) -> List[Tuple[int, int, int, int]]:
        """
        Возвращает список кортежей:
        (timestamp, price1, price2, price3)
        """

        table_name = self._normalize_table_name(weapon_name)
        timest = int(time.time())
        self.cursor.execute(f"""
            SELECT *
            FROM {table_name}
            WHERE timestamp BETWEEN ? AND ?
            ORDER BY timestamp ASC
        """, (0, timest))

        data = self.cursor.fetchall()
        return data
    
    def prepare_plot(data:List[Tuple[int, int, int, int]]):
        x =[]
        y1 =[]
        y2 =[]
        y3 =[]
        for row in data:
            x.append(row[0]) #в часах
            y1.append(row[1])
            y2.append(row[2])
            y3.append(row[3])
        ret = [x, y1, y2, y3]    
        return ret

    # -----------------------------
    # Get latest record
    # -----------------------------

    def get_latest_prices(self, weapon_name: str):
        table_name = self._normalize_table_name(weapon_name)

        self.cursor.execute(f"""
            SELECT *
            FROM {table_name}
            ORDER BY timestamp DESC
            LIMIT 1
        """)

        return self.cursor.fetchone()
    

class SuperDatabase:
    class Statuses:
        online = "online"
        ingame = "ingame"
        offline = "offline"
        visible = "visible"
        # статус hidden может означать как удаление, так и сокрытие ривена
        hidden = "hidden"

    def __init__(self, path=None):
        if path is None:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            path = os.path.join(base_dir, "super.db")
        self.status_to_id = {}
        self.id_to_status = {}
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self._init_schema()
        self.get_status_ids()

    def get_status_ids(self):
        self.cursor.execute(f"""
            SELECT *
            FROM statuses
        """)
        rows = self.cursor.fetchall()
        if len(rows) < 5:
            statuses_list = [self.Statuses.hidden, self.Statuses.offline,\
                             self.Statuses.online, self.Statuses.ingame, self.Statuses.visible]
            for status_name in statuses_list:
                self.cursor.execute(f"""
                    INSERT INTO statuses (status) VALUES (?)
                """, (status_name,))
                sql_id = self.cursor.lastrowid
                self.status_to_id[status_name] = sql_id
                self.id_to_status[sql_id] = status_name
            self.conn.commit()
        else:
            for status_id, status in rows:
                self.status_to_id[status] = status_id
                self.id_to_status[status_id] = status

    def _init_schema(self):
        try:

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS attributes (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS weapons (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS owners (
                id INTEGER PRIMARY KEY,
                name TEXT UNIQUE
            )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS rivens (
                id INTEGER PRIMARY KEY,
                riven_text_id TEXT,
                weapon_id INTEGER,
                price INTEGER,
                created INTEGER NOT NULL,
                owner_id INTEGER,
                mod_rank INTEGER,
                pos_value1 REAL,
                pos_value2 REAL,
                pos_value3 REAL,
                neg_value REAL,
                pos_name1 INTEGER,
                pos_name2 INTEGER,
                pos_name3 INTEGER,
                neg_name INTEGER,
                FOREIGN KEY(pos_name1, pos_name2, pos_name3, neg_name) REFERENCES attributes(id),
                FOREIGN KEY(weapon_id) REFERENCES weapons(id),
                FOREIGN KEY(owner_id) REFERENCES owners(id)
            )
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS att_idx
            ON attributes (name)
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS weapon_idx
            ON weapons (name)
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS owners_idx
            ON owners (name)
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS rivens_idx
            ON rivens (riven_text_id, weapon_id, owner_id, pos_name1, pos_name2, pos_name3, neg_name)
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_params (
                id INTEGER PRIMARY KEY,
                hash INTEGER
            )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS scan_timestamps (
                id INTEGER PRIMARY KEY,
                hash_id INTEGER,
                time INTEGER,
                FOREIGN KEY(hash_id) REFERENCES scan_params(id)
            )
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS hash_idx
            ON scan_params (hash)
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS scans_idx
            ON scan_timestamps (hash_id, time)
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS prev_scanned_rivens (
                id INTEGER PRIMARY KEY,
                hash_id INTEGER,
                riven_id INTEGER,
                FOREIGN KEY(hash_id) REFERENCES scan_params(id),
                FOREIGN KEY(riven_id) REFERENCES rivens(id)
            )
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS prev_idx
            ON prev_scanned_rivens (hash_id)
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS statuses (
                id INTEGER PRIMARY KEY,
                status TEXT UNIQUE
            )
            """)

            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS status_changes (
                id INTEGER PRIMARY KEY,
                riven_id INTEGER,
                status_id INTEGER,
                timestamp INTEGER,
                FOREIGN KEY(status_id) REFERENCES statuses(id),
                FOREIGN KEY(riven_id) REFERENCES rivens(id)
            )
            """)

            self.conn.execute("""
            CREATE INDEX IF NOT EXISTS st_ch_idx
            ON status_changes (riven_id, timestamp)
            """)

            self.conn.commit()
        except Exception as e:
            print ("super db init failed")
    
    def get_id_from_field(self, value, table, field = "name"):
        self.cursor.execute(f"""
                SELECT id FROM {table} WHERE {field}=?
            """, (value,))
        row = self.cursor.fetchone()
        sql_id = -1
        if row is None:
            # оружия нет — создаём
            self.cursor.execute(f"""
                INSERT INTO {table} ({field}) VALUES (?)
            """, (value,))
            sql_id = self.cursor.lastrowid
            self.conn.commit()
        else:
            sql_id = row[0]
        return sql_id
    
    def form_attributes_lists(self, item):
        """Возвращает список имён аттрибутов и список значений аттрибутов
        """
        attributes = item["attributes"]
        attr_dict = {}
        attr_list = []
        neg_att = "none"
        neg_val = 0
        for att in attributes:
            if att["positive"]:
                attr_dict[att["url_name"]] = att["value"]
                attr_list.append(att["url_name"])
            else:
                neg_att = att["url_name"]
                neg_val = att["value"]
        attr_list.sort()
        if len(attr_list) < 3:
            attr_list.append("none")
            attr_dict["none"] = 0
        attr_list.append(neg_att)
        attr_dict[neg_att] = neg_val
        names = attr_list
        values = []
        for elem in attr_list:
            values.append(attr_dict[elem])
        if len(values) !=4:
            print(f"error forming attributes list: len = {len(values)}")
        return names, values
    
    def get_attributes_ids(self, att_names):
        ids = []
        for name in att_names:
            att_id = self.get_id_from_field(name, "attributes")
            ids.append(att_id)
        return ids
    
    def get_latest_search_timestamp(self, hash_id):
        try:
            # Получаем таймстампы
            self.cursor.execute("""
                SELECT time
                FROM scan_timestamps
                WHERE hash_id=?
                ORDER BY time ASC
            """, (hash_id,))
            rows = self.cursor.fetchall()
            if len(rows) < 1:
                return None
            return rows[-1][0]
        except Exception as e:
            print ("get_latest_search_timestamp failed", e)
            return None
        
    def get_previous_rivens_ids(self, hash_id):
        """Возвращает sql-id ривенов из предыдущего запроса (для отслеживания исчезнувших)
        """
        try:
            # Получаем sql-id ривенов
            self.cursor.execute("""
                SELECT riven_id
                FROM prev_scanned_rivens
                WHERE hash_id=?
            """, (hash_id,))
            rows = self.cursor.fetchall()
            if len(rows) < 1 or rows is None:
                return []
            rivens_ids = []
            for r_id, in rows:
                rivens_ids.append(r_id)
            return rivens_ids
        except Exception as e:
            print ("get_latest_search_timestamp failed", e)
            return None
        
    def add_search_timestamp(self, timestamp, hash_id):
        self.cursor.execute(f"""
            INSERT INTO scan_timestamps (hash_id, time) VALUES (?, ?)
        """, (hash_id, timestamp))
        self.conn.commit()

    def delete_riven_from_prev_scanned_rivens(self, riven_id):
        self.cursor.execute("""
            DELETE FROM prev_scanned_rivens
            WHERE riven_id=?
        """, (riven_id,))
        self.conn.commit()

    def add_riven_to_prev_scanned_rivens(self, hash_id, new_id):
        self.cursor.execute(f"""
            INSERT INTO prev_scanned_rivens (hash_id, riven_id) VALUES (?, ?)
        """, (hash_id, new_id))
        self.conn.commit()

    def process_rivens_from_requester(self, auctions, search_hash, timestamp):
        hash_id = self.get_id_from_field(search_hash, "scan_params", "hash")
        old_ids = self.get_previous_rivens_ids(hash_id)
        prev_timestamp = self.get_latest_search_timestamp(hash_id)
        self.add_search_timestamp(timestamp, hash_id)
        # cначала эубрабатываем все пришедшие аукционы, а уже затем смотрим, какие ауки пропали
        new_ids = []
        for auction in auctions:
            r_id = self.insert_or_update_riven(auction, timestamp)
            new_ids.append(r_id)
        # находим пропавшие ривены. обновляем статус, удаляем id из prev_scanned_rivens
        for old_id in old_ids:
            if not old_id in new_ids:
                self.update_current_riven_status(old_id, self.Statuses.hidden, timestamp)
                self.delete_riven_from_prev_scanned_rivens(old_id)
        # находим новые ривены. Статус у них уже обновлён в insert_or_update_riven, только добавляем в prev_scanned_rivens
        for new_id in new_ids:
            if not new_id in old_ids:
                self.add_riven_to_prev_scanned_rivens(hash_id, new_id)

    def iso_to_timestamp(self, iso_str):
        dt = datetime.fromisoformat(iso_str)
        timestamp = dt.timestamp()
        return timestamp
    
    def get_current_statuses(self, riven_id):
        self.cursor.execute("""
            SELECT status_id, timestamp
            FROM status_changes
            WHERE riven_id=?
            ORDER BY timestamp ASC
        """, (riven_id,))
        rows = self.cursor.fetchall()
        owner_statuses = [self.Statuses.ingame, self.Statuses.offline, self.Statuses.online]
        riven_statuses = [self.Statuses.hidden, self.Statuses.visible]
        owner_ts = 0
        riven_ts = 0
        online_status = None
        visibility_status = None
        for status_id, ts in rows:
            if self.id_to_status[status_id] in owner_statuses and ts > owner_ts:
                owner_ts = ts
                online_status = self.id_to_status[status_id]
            elif self.id_to_status[status_id] in riven_statuses and ts > riven_ts:
                riven_ts = ts
                visibility_status = self.id_to_status[status_id]
        return online_status, visibility_status
    
    def update_current_riven_status(self, riven_id, status, timestamp):
        owner_statuses = [self.Statuses.ingame, self.Statuses.offline, self.Statuses.online]
        riven_statuses = [self.Statuses.hidden, self.Statuses.visible]
        if (not status in owner_statuses) and (not status in riven_statuses):
            print(f"incorrect status in update_current_riven_status: {status}")
            return
        #сначала получаем текущие статусы
        online_status, visibility_status = self.get_current_statuses(riven_id)
        if status == online_status or status == visibility_status:
            return
        #если статус поменялся - записываем
        self.cursor.execute(f"""
            INSERT INTO status_changes (riven_id, status_id, timestamp) VALUES (?, ?, ?)
        """, (riven_id, self.status_to_id[status], timestamp))
        self.conn.commit()

    def on_riven_changed(self, riven_id, price_new):
        self.cursor.execute(f"""
            UPDATE rivens
            SET price = ?
            WHERE id = ?
        """, (price_new, riven_id))
        # теперь стираем все предыдущие статусы
        self.cursor.execute("""
            DELETE FROM status_changes
            WHERE riven_id=?
        """, (riven_id,))
        self.conn.commit()

    def insert_or_update_riven(self, auction, timestamp):
        riven_text_id = auction["id"]
        item = auction["item"]
        weapon = item["weapon"]
        owner_item = auction["owner"]
        owner = owner_item["ingame_name"]
        owner_status = owner_item["status"]
        price = auction["buyout_price"]
        mod_rank = int(item["mod_rank"])
        if price is None:
            price = 999999
        weapon_id = self.get_id_from_field(weapon, "weapons")
        owner_id = self.get_id_from_field(owner, "owners")
        att_names, att_values = self.form_attributes_lists(item)
        att_ids = self.get_attributes_ids(att_names)
        updated = int(self.iso_to_timestamp(auction["updated"]))
        created = int(self.iso_to_timestamp(auction["created"]))

        already_existed = False

        self.cursor.execute(f"""
            SELECT *
            FROM rivens
            WHERE riven_text_id=?
        """, (riven_text_id))
        row:tuple = self.cursor.fetchone()
        riven_id = -1
        if row is None:
            # ривена нет - создаём
            self.cursor.execute("""
                INSERT INTO rivens (riven_text_id, weapon_id, price, created, owner_id, mod_rank, pos_value1, pos_value2, pos_value3, neg_value, pos_name1, pos_name2, pos_name3, neg_name) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (riven_text_id, weapon_id, price, created, owner_id, mod_rank, att_values[0], att_values[1], att_values[2], att_values[3], att_ids[0], att_ids[1], att_ids[2], att_ids[3]))
            riven_id = self.cursor.lastrowid
            self.conn.commit()
        else:
            already_existed = True
            riven_id = row[0]
        # вставили ривен в БД, чиназес. Осталось проверить на изменения ривен, если он уже был в БД.
        # Если ривен поменялся - удалить записи о нём из ВСЕХ таблиц, начать отслеживать его заново.
        if already_existed:
            if price != row[3]:
                self.on_riven_changed(riven_id, price)
        # отслеживаем статусы ривена.
        self.update_current_riven_status(riven_id, self.Statuses.visible, timestamp)
        self.update_current_riven_status(riven_id, owner_status, timestamp)
        return riven_id
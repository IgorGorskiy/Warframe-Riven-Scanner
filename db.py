DB_PATH = "rivens.db"
import sqlite3
import json
import os
from typing import List, Tuple
from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError

from datetime import datetime, time, date, timezone, timedelta
import time

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
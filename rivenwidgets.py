import sys
import re
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton, QApplication, QListWidgetItem)
from PySide6.QtCore import Qt, QSize
from PySide6.QtCore import Signal
from datetime import datetime, timezone, timedelta
from rivenstats import STARTING_STATS

def value_to_color(value):
    """
    Преобразует число (0–100) в цвет:
    0 -> красный (255, 0, 0)
    100 -> зелёный (0, 255, 0)
    """
    value = max(0, min(100, value))  # ограничиваем диапазон
    red = int(255 * (1 - value / 100))
    green = int(255 * (value / 100))
    return f"rgb({red}, {green}, 0)"

def colorize_numbers(text):
    """
    Находит числа в тексте и оборачивает их в span с цветом
    """
    def replacer(match):
        number = int(match.group())
        color = value_to_color(number)
        return f'<span style="color:{color}; font-weight:bold;">{number}</span>'

    return re.sub(r'\b\d+\b', replacer, text)

def datetime_str_from_timestamp(ts):
    updated_out = datetime.fromtimestamp(ts)
    s1:str = str(updated_out.date())
    s2:str = str(updated_out.time())
    datetime_str = "Дата: " + s1 + " | Время: " + s2[0:5]
    return datetime_str

class RivenAlertWidget:{}
class RivenAlertWidget(QWidget):
    alert_widgets: dict[str, RivenAlertWidget] = {}
    groll_to_save = Signal(str)
    plot_from_riven = Signal(dict)

    def __init__(self, auction, item:QListWidgetItem, reason, weapon_info):
        super().__init__()
        self.market_prices: list[int] = []
        self.list_item = item
        self.auction = auction
        self.reason = reason
        self.dismissable = False
        if reason == "good stats (dismissable)":
            reason = "good stats"
            self.dismissable = True

        item = auction.get("item", {})
        owner = auction.get("owner", {})
        self.status = owner.get("status", "UNKNOWN")
        self.pidorstvo = auction.get("pidorstvo", 0)
        self.updated = auction.get("updated", "2026-05-02T17:44:15.000+00:00")
        self.owner_name = owner.get("ingame_name", "UNKNOWN")
        self.weapon = item.get("weapon_url_name", "UNKNOWN")
        self.riven_name = item.get("name", "UNKNOWN")
        self.price = auction.get("buyout_price", 0)
        self.re_rolls = item.get("re_rolls", 0)
        self.auc_id = auction.get("id", "UNKNOWN")
        self.attributes = item.get("attributes", [])
        self.rank = item.get("mod_rank", 0)

        if reason == "sold riven":
            self.weapon = auction["weapon_name"]
            self.owner_name = auction["owner_name"]
            self.disappearance_detected = auction["ts"]
            self.price = auction["price"]
            self.last_checked = auction["last_checked"]
            self.last_updated = auction["last_updated"]
            self.attributes = [{
                "positive": True,
                "url_name": auction["pos_stats"][0],
                "value": auction["value1"]},
                {
                "positive": True,
                "url_name": auction["pos_stats"][1],
                "value": auction["value2"]},
                {
                "positive": True,
                "url_name": auction["pos_stats"][2],
                "value": auction["value3"]},
                {
                "positive": False,
                "url_name": auction["neg_stat"],
                "value": auction["value4"]}
                ]

        if reason == "good stats" or reason == "manual request":
            self.list_item.setSizeHint(QSize(0, 170))
        elif reason == "sold riven":
            self.list_item.setSizeHint(QSize(0, 181))
        else:
            self.list_item.setSizeHint(QSize(0, 150))
        
        layout = QVBoxLayout(self)
        if reason == "sold riven":
            last_updated_str = datetime_str_from_timestamp(self.last_updated)
            last_checked_str = datetime_str_from_timestamp(self.last_checked)
            disappearance_detected_str = datetime_str_from_timestamp(self.disappearance_detected)
        updated_out = datetime.fromisoformat(self.updated) + timedelta(hours=3)
        s1:str = str(updated_out.date())
        s2:str = str(updated_out.time())
        self.datetime = s1 + " | Время: " + s2[0:5]

        owner_color = value_to_color(0)
        if self.status == "online":
            owner_color = value_to_color(50)
        if self.status == "ingame":
            owner_color = value_to_color(100)
        if self.price is None:
            self.price = 1
        if self.re_rolls is None:
            self.re_rolls = 1
        label = QLabel(
            f"<b>{reason.upper()}</b><br>"
            f"{self.riven_name}<br>"
            f"Оружие: {self.weapon}<br>"
            f"Цена: {self.price} | Re-rolls: {self.re_rolls} | Ratio: {self.re_rolls/self.price}<br>"
            f'Владелец: {self.owner_name}, статус: <span style="color:{owner_color}; font-weight: bold;">{self.status}</span><br>'
            f"Дата: {self.datetime}<br>"
        )
        if reason == "sold riven":
            pidorstvo_str = f""
            if self.pidorstvo > 0:
                raz = "раз(а)"
                last_digit = self.pidorstvo - int(int(self.pidorstvo)/10)*10
                if last_digit < 2 or last_digit > 4 or self.pidorstvo == 13 or self.pidorstvo == 14 or self.pidorstvo == 12:
                    raz = "раз"
                else:
                    raz = "раза"
                if last_digit < 0:
                    raz = "раз(а)"
                pidorstvo_str = f"; внесён в кубоидные говнопидоры {self.pidorstvo} {raz}"
            label.setText(
                f"<b>{reason.upper()}</b><br>"
                f"Оружие: {self.weapon}<br>"
                f"Цена: {self.price}<br>"
                f'Владелец: {self.owner_name}{pidorstvo_str}<br>'
                f"Продажа замечена: {disappearance_detected_str}<br>"
                f'Последнее обновление: {last_updated_str}<br>'
                f'Отслеживался до момента: {last_checked_str}<br>'
            )
        label.setTextFormat(Qt.TextFormat.RichText)
        self.neg_stat = ""
        if reason == "good stats" or reason == "manual request" or reason == "sold riven":
            strin = f"Значения статов:"
            for stat in self.attributes:
                if stat["positive"] != True:
                    self.neg_stat = stat["url_name"]
                    continue
                stat_name = stat["url_name"]
                #val = stat["value"] / ((self.rank + 1) / 9.0) #приводим статы к виду мода 8-го ранга
                w_type = weapon_info[self.weapon]["rivenType"]
                if w_type in STARTING_STATS:
                    
                    dispo = weapon_info[self.weapon]["disposition"]
                    base_value = STARTING_STATS[w_type][stat_name]
                    maxval = 1.1*0.9375*dispo*base_value
                    minval = 0.9*0.9375*dispo*base_value
                    max = maxval - minval
                    val = stat["value"]
                    if self.rank < 4 and stat["value"] < minval: #подтираем жопу за дибилами, которые пишут статы для макс мода к моду 0 ранга
                        val = stat["value"] / ((self.rank + 1) / 9.0) #приводим статы к виду мода 8-го ранга
                    cur = val - minval
                    percentage:int = int(100*cur/max)
                    if (percentage > 100):
                        percentage = 100
                    elif (percentage < 0):
                        percentage = 0
                else:
                    percentage = 0
                    print("percentage not assigned")
                new = f" {stat_name}: <b>{percentage}</b>%"
                strin += new

        btns = QHBoxLayout()

        btn_owner = QPushButton("📋 Владелец")
        btn_msg = QPushButton("📋 Сообщение")
        btn_link = QPushButton("🔗 Аукцион")
        btn_save = QPushButton("📋 Больше не показывать")
        btn_plot = QPushButton("📋 Построить график")
        btn_del = QPushButton("❌ Удалить")

        btn_owner.clicked.connect(
            lambda: QApplication.clipboard().setText(self.owner_name)
        )
        btn_msg.clicked.connect(
            lambda: QApplication.clipboard().setText(
                f"/w {self.owner_name} Hi! I want to buy {self.weapon} {self.riven_name} for {self.price}p"
            )
        )
        btn_link.clicked.connect(
            lambda: __import__("webbrowser").open(
                f"https://warframe.market/auction/{self.auc_id}"
            )
        )

        btn_save.clicked.connect(
            lambda: (self.groll_to_save.emit(self.auc_id), self.delete_self())
        )

        btn_plot.clicked.connect(
            lambda: self.plot_from_riven.emit(self.auction)
        )

        btn_del.clicked.connect(self.delete_self)

        btns.addWidget(btn_owner)
        btns.addWidget(btn_msg)
        btns.addWidget(btn_link)
        if reason == "good stats" or reason == "manual request":
            btns.addWidget(btn_plot)
        if self.dismissable:
            btns.addWidget(btn_save)
        btns.addStretch()
        btns.addWidget(btn_del)

        layout.addWidget(label)
        g_label = QLabel()
        if reason == "good stats" or reason == "manual request" or reason == "sold riven":
            g_label.setTextFormat(Qt.TextFormat.RichText)
            color = value_to_color(0)
            g_label.setText(colorize_numbers(strin) + f'; минус: <span style="color:{color}; font-weight: bold;">{self.neg_stat}</span>')
            layout.addWidget(g_label)
        layout.addLayout(btns)

    def set_market_prices(self, prices: list[int]):
        self.market_prices = prices

        if prices:
            text = " / ".join(f"{p}p" for p in prices)
            self.price_label.setText(f"Рынок: {text}")
        else:
            self.price_label.setText("Рынок: нет данных")


    def delete_self(self):
        RivenAlertWidget.alert_widgets.pop(self.auc_id)
        lw = self.list_item.listWidget()
        lw.takeItem(lw.row(self.list_item))


    
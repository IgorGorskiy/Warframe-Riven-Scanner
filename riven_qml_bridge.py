"""
riven_qml_bridge.py
~~~~~~~~~~~~~~~~~~~~
Заменяет RivenAlertWidget + QListWidget на QAbstractListModel + QML ListView.

Публичный API (совместим с оригиналом):
    model = RivenListModel()
    model.groll_to_save.connect(db.insert_riven_to_dismiss)
    model.plot_from_riven.connect(build_plot_from_riven)
    model.addAlert(auction, reason, weapon_info)   # вместо ручного создания виджета
"""

import re
import webbrowser
from datetime import datetime, timedelta

from PySide6.QtCore import (
    QObject, Signal, Slot, Property,
    QAbstractListModel, Qt, QModelIndex, QByteArray,
)
from PySide6.QtWidgets import QApplication

from rivenstats import STARTING_STATS


# ══════════════════════════════════════════════════════════════════
#  Helpers (повторяют оригинальные функции)
# ══════════════════════════════════════════════════════════════════

def value_to_color(value: float) -> str:
    """0 → красный, 100 → зелёный."""
    value = max(0.0, min(100.0, float(value)))
    red   = int(255 * (1 - value / 100))
    green = int(255 * (value / 100))
    return f"rgb({red},{green},0)"


def colorize_numbers(text: str) -> str:
    """Оборачивает целые числа в цветные <span>."""
    def replacer(m: re.Match) -> str:
        n = int(m.group())
        return f'<span style="color:{value_to_color(n)};font-weight:bold;">{n}</span>'
    return re.sub(r'\b\d+\b', replacer, text)


def _ts_to_str(ts) -> str:
    dt = datetime.fromtimestamp(ts)
    return f"Дата: {dt.date()} | Время: {str(dt.time())[:5]}"


# ══════════════════════════════════════════════════════════════════
#  RivenAlertItem — одна карточка, видна QML через свойства/слоты
# ══════════════════════════════════════════════════════════════════

class RivenAlertItem(QObject):
    """
    Хранит данные одного аукциона и предоставляет QML:
      • read-only свойства (mainHtml, statsHtml, флаги видимости кнопок)
      • @Slot-методы, вызываемые из обработчиков кнопок в QML
    Испускает сигналы, которые RivenListModel пробрасывает наружу.
    """

    deleteRequested = Signal(str)   # auc_id
    saveRequested   = Signal(str)   # auc_id
    plotRequested   = Signal(dict)  # auction dict

    def __init__(self, auction: dict, reason: str, weapon_info: dict, parent=None):
        super().__init__(parent)

        self._auction = auction

        # ── dismissable-флаг ──────────────────────────────────────
        self._dismissable = (reason == "good stats (dismissable)")
        if self._dismissable:
            reason = "good stats"
        self._reason = reason

        # ── базовые поля ──────────────────────────────────────────
        item_data = auction.get("item", {})
        owner     = auction.get("owner", {})
        status    = owner.get("status", "UNKNOWN")

        self._owner_name = owner.get("ingame_name",        "UNKNOWN")
        self._weapon     = item_data.get("weapon_url_name", "UNKNOWN")
        self._riven_name = item_data.get("name",            "UNKNOWN")
        self._price      = auction.get("buyout_price", 0)
        self._re_rolls   = item_data.get("re_rolls",   0)
        self._auc_id     = auction.get("id",           "UNKNOWN")
        self._attributes = item_data.get("attributes", [])
        self._rank       = item_data.get("mod_rank",   0)
        updated_raw      = auction.get("updated", "2026-01-01T00:00:00.000+00:00")
        quantiles_str = ""
        if "quantiles" in auction.keys():
            quantiles_str = f" | Квантили: q(0.1) = {auction["quantiles"][0]}; q(0.25) = {auction["quantiles"][1]}; q(0.50) = {auction["quantiles"][2]}"

        # ── sold riven: переопределяем поля ──────────────────────
        if reason == "sold riven":
            self._weapon       = auction["weapon_name"]
            self._owner_name   = auction["owner_name"]
            self._price        = auction["price"]
            self._attributes   = [
                {"positive": True,  "url_name": auction["pos_stats"][0], "value": auction["value1"]},
                {"positive": True,  "url_name": auction["pos_stats"][1], "value": auction["value2"]},
                {"positive": True,  "url_name": auction["pos_stats"][2], "value": auction["value3"]},
                {"positive": False, "url_name": auction["neg_stat"],     "value": auction["value4"]},
            ]

        # ── дата/время ────────────────────────────────────────────
        updated_dt    = datetime.fromisoformat(updated_raw) + timedelta(hours=3)
        self._datetime = f"{updated_dt.date()} | {str(updated_dt.time())[:5]}"

        # ── цвет статуса ──────────────────────────────────────────
        status_color = value_to_color({"online": 50, "ingame": 100}.get(status, 0))

        # ── основной HTML ─────────────────────────────────────────
        if reason == "sold riven":
            pidorstvo_str = ""
            p = auction.get("pidorstvo", 0)
            if p > 0:
                ld  = p - int(p / 10) * 10
                raz = "раза" if (2 <= ld <= 4 and p not in (12, 13, 14)) else "раз"
                pidorstvo_str = f"; внесён в кубоидные говнопидоры {p} {raz}"

            self._main_html = (
                "<b>SOLD RIVEN</b><br>"
                f"Оружие: {self._weapon}<br>"
                f"Цена: {self._price}<br>"
                f"Владелец: {self._owner_name}{pidorstvo_str}<br>"
                f"Продажа замечена: {_ts_to_str(auction['ts'])}<br>"
                f"Последнее обновление: {_ts_to_str(auction['last_updated'])}<br>"
                f"Отслеживался до момента: {_ts_to_str(auction['last_checked'])}<br>"
            )
        else:
            ratio = f"{self._re_rolls / self._price:.4f}" if self._price else "∞"
            self._main_html = (
                f"<b>{reason.upper()}</b><br>"
                f"{self._riven_name}<br>"
                f"Оружие: {self._weapon}<br>"
                f"Цена: {self._price} | Re-rolls: {self._re_rolls} | Ratio: {ratio}{quantiles_str}<br>"
                f"Владелец: {self._owner_name}, статус: "
                f'<span style="color:{status_color};font-weight:bold;">{status}</span><br>'
                f"Дата: {self._datetime}<br>"
            )

        # ── HTML статов ───────────────────────────────────────────
        self._stats_html = ""
        if reason in ("good stats", "manual request", "sold riven"):
            parts    = "Значения статов:"
            neg_stat = ""

            for stat in self._attributes:
                if not stat["positive"]:
                    neg_stat = stat["url_name"]
                    continue

                stat_name = stat["url_name"]
                w_info    = weapon_info.get(self._weapon, {})
                w_type    = w_info.get("rivenType", "")

                if w_type in STARTING_STATS:
                    dispo      = w_info["disposition"]
                    base_value = STARTING_STATS[w_type][stat_name]
                    maxval     = 1.1 * 0.9375 * dispo * base_value
                    minval     = 0.9 * 0.9375 * dispo * base_value
                    val        = stat["value"]
                    if self._rank < 4 and val < minval:
                        val = val / ((self._rank + 1) / 9.0)
                    pct = max(0, min(100, int(100 * (val - minval) / (maxval - minval))))
                else:
                    pct = 0
                    print(f"[riven_qml_bridge] percentage not assigned for {stat_name}")

                parts += f" {stat_name}: <b>{pct}</b>%"

            neg_color        = value_to_color(0)
            self._stats_html = (
                colorize_numbers(parts)
                + f'; минус: <span style="color:{neg_color};font-weight:bold;">{neg_stat}</span>'
            )

    # ── Properties (read-only, constant) ──────────────────────────

    @Property(str, constant=True)
    def mainHtml(self) -> str:     return self._main_html

    @Property(str, constant=True)
    def statsHtml(self) -> str:    return self._stats_html

    @Property(bool, constant=True)
    def showStats(self) -> bool:   return bool(self._stats_html)

    @Property(bool, constant=True)
    def showPlot(self) -> bool:
        return self._reason in ("good stats", "manual request")

    @Property(bool, constant=True)
    def dismissable(self) -> bool: return self._dismissable

    @Property(str, constant=True)
    def aucId(self) -> str:        return self._auc_id

    # ── Slots (вызываются из QML) ─────────────────────────────────

    @Slot()
    def copyOwner(self):
        QApplication.clipboard().setText(self._owner_name)

    @Slot()
    def copyMessage(self):
        QApplication.clipboard().setText(
            f"/w {self._owner_name} Hi! I want to buy "
            f"{self._weapon} {self._riven_name} for {self._price}p"
        )

    @Slot()
    def openAuction(self):
        webbrowser.open(f"https://warframe.market/auction/{self._auc_id}")

    @Slot()
    def requestDelete(self):
        self.deleteRequested.emit(self._auc_id)

    @Slot()
    def requestSave(self):
        self.saveRequested.emit(self._auc_id)
        self.deleteRequested.emit(self._auc_id)

    @Slot()
    def requestPlot(self):
        self.plotRequested.emit(self._auction)


# ══════════════════════════════════════════════════════════════════
#  RivenListModel — список карточек для QML ListView
# ══════════════════════════════════════════════════════════════════

class RivenListModel(QAbstractListModel):
    """
    Предоставляет список RivenAlertItem через роль 'item'.
    Агрегирует сигналы всех элементов и пробрасывает их наружу
    через groll_to_save / plot_from_riven — интерфейс совместим
    с оригинальным RivenAlertWidget.
    """

    ItemRole = Qt.ItemDataRole.UserRole + 1

    groll_to_save   = Signal(str)   # совместимо с оригиналом
    plot_from_riven = Signal(dict)  # совместимо с оригиналом
    alertAdded      = Signal()      # QML слушает для запуска видео

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items:       list[RivenAlertItem]      = []
        self._items_by_id: dict[str, RivenAlertItem] = {}

    # ── QAbstractListModel ────────────────────────────────────────

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._items)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        if role == self.ItemRole:
            return self._items[index.row()]
        return None

    def roleNames(self) -> dict:
        return {self.ItemRole: QByteArray(b"alertItem")}

    # ── Публичный API ─────────────────────────────────────────────

    def addAlert(self, auction: dict, reason: str, weapon_info: dict):
        """Создаёт элемент и добавляет его в начало списка."""
        alert = RivenAlertItem(auction, reason, weapon_info)
        alert.deleteRequested.connect(self._remove_alert)
        alert.saveRequested.connect(self.groll_to_save)
        alert.plotRequested.connect(self.plot_from_riven)

        self.beginInsertRows(QModelIndex(), 0, 0)
        self._items.insert(0, alert)
        self._items_by_id[alert.aucId] = alert
        self.endInsertRows()
        self.alertAdded.emit()

    @Slot(str)
    def _remove_alert(self, auc_id: str):
        alert = self._items_by_id.get(auc_id)
        if alert is None:
            return
        row = self._items.index(alert)
        self.beginRemoveRows(QModelIndex(), row, row)
        self._items.pop(row)
        del self._items_by_id[auc_id]
        self.endRemoveRows()

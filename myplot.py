import pyqtgraph as pg
from PySide6 import QtWidgets
import datetime
import numpy as np
import math

class TimeAxisItem(pg.AxisItem):
    def tickStrings(self, values, scale, spacing):
        strings = []

        for v in values:
            # защита от nan/inf
            if not math.isfinite(v):
                strings.append("")
                continue

            # ограничение диапазона timestamp
            # (примерно: 1970–2100)
            if v < 0 or v > 4102444800:
                strings.append("")
                continue

            try:
                dt = datetime.datetime.fromtimestamp(v)
            except (OSError, OverflowError, ValueError):
                strings.append("")
                continue

            # адаптивный формат
            if spacing < 60:
                s = dt.strftime("%H:%M:%S")
            elif spacing < 3600:
                s = dt.strftime("%H:%M")
            elif spacing < 86400:
                s = dt.strftime("%d %H:%M")
            else:
                s = dt.strftime("%Y-%m-%d")

            strings.append(s)

        return strings
    
class PricePlot:
    def __init__(self, container_widget):
        self.plot_widget = pg.PlotWidget(
            parent=container_widget,
            axisItems={'bottom': TimeAxisItem(orientation='bottom')}
        )
        self.parent = container_widget

        layout = QtWidgets.QVBoxLayout(container_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)

        # растянуть на весь контейнер
        self.plot_widget.setGeometry(container_widget.rect())

        # линия
        self.curve = self.plot_widget.plot(pen=pg.mkPen(width=2))

        # сетка
        self.plot_widget.showGrid(x=True, y=True)

        # включаем взаимодействие мышью
        self.plot_widget.setMouseEnabled(x=True, y=False)
        self.plot_widget.setClipToView(True)

        # автоматическое сглаживание
#        self.curve.setDownsampling(mode='peak')
#        self.curve.setClipToView(True)

        # включаем зум колесом
        self.plot_widget.getViewBox().setMouseMode(pg.ViewBox.PanMode)

    def filter_downward_outliers(self, times, prices, window=200, threshold=0.3):
        """
        Удаляет выбросы вниз.

        window — сколько соседей учитывать
        threshold — относительное отклонение (например 0.1 = 10%)
        """

        prices = np.array(prices, dtype=float)
        filtered = prices.copy()

        n = len(prices)

        for i in range(n):
            left = max(0, i - window)
            right = min(n, i + window + 1)
            # берём соседей без самой точки
            neighbors = np.concatenate((prices[left:i], prices[i+1:right]))
            if len(neighbors) < 3:
                continue
            median = np.median(neighbors)
            # если точка сильно ниже медианы → выброс
            if prices[i] < median * (1 - threshold) or prices[i] < 20:
                filtered[i] = np.nan  # или можно np.nan
        return times, filtered.tolist()

    def set_data(self, timestamps, prices):
        self.curve.setData(timestamps, prices)
        self.plot_widget.autoRange()

    def insert_gaps(self, times, prices, max_gap=1800):
        new_t = []
        new_p = []

        for i in range(len(times)):
            if i > 0 and (times[i] - times[i-1]) > max_gap:
                new_t.append(times[i])
                new_p.append(np.nan)  # разрыв линии

            new_t.append(times[i])
            new_p.append(prices[i])

        return new_t, new_p
    
    def update_geometry(self):
        self.plot_widget.setGeometry(self.parent.rect())

    def redraw(self):
        self.plot_widget.setAlignment()
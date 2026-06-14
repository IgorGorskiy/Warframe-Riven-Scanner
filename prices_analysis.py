
import os
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
from datetime import datetime, timezone, timedelta
from typing import List, Tuple
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.datasets import make_regression
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import scale, PolynomialFeatures
from sklearn.linear_model import LinearRegression, Ridge, Lasso, ElasticNet
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score
from sklearn.preprocessing import MultiLabelBinarizer

# анализ цен на ривены. Используется понятие квантиля.
# Квантиль x - это такое значение переменной, ниже которого находится x процентов данных.
# Самая простая задача модуля - присвоение квантиля конкретному ривену на основе истории цен.
# Допустим, ривену присвоен квантиль 90. Это значит, что цена на этот тип ривена в 90% времени
# была ниже, чем на этот ривен.
# Помимо этого, задачей модуля является вычисление цены на один тип ривена
# исходя из данных о других типах ривенов. По сути должна решаться задача регрессии.
# В решении задачи регрессии также потребуются квантили, так как с зависимостью цен от времени работать
# неудобно. Используя квантили, получаем задачу регрессии с двумя входными векторами:
# варьируемый позитивный стат (остальные 2 позитивных стата зафиксированы) и негативный стат;
# выходным вектором является цена (квантиль, взятый из множества измерений цены в разное время).

class MatrixLinearRegression:

    def fit(self, X, y):
        X = np.insert(X, 0, 1, axis=1)   # add ones vector
        XT_X_inv = np.linalg.inv(X.T @ X)   # (X.T * X) ** (-1) inverse matrix
        weights = np.linalg.multi_dot([XT_X_inv, X.T, y])   # XT_X_inv * X.T * y
        self.bias, self.weights = weights[0], weights[1:]

    def predict(self, X_test):
        return X_test @ self.weights + self.bias
    
class GDLinearRegression:
    def __init__(self, learning_rate=0.01, tolerance=1e-8):
        self.learning_rate = learning_rate
        self.tolerance = tolerance

    def fit(self, X, y):
        n_samples, n_features = X.shape
        self.bias, self.weights = 0, np.zeros(n_features)
        previous_db, previous_dw = 0, np.zeros(n_features)

        while True:
            y_pred = X @ self.weights + self.bias
            db = 1 / n_samples * np.sum(y_pred - y)
            dw = 1 / n_samples * X.T @ (y_pred - y)
            self.bias -= self.learning_rate * db
            self.weights -= self.learning_rate * dw

            abs_db_reduction = np.abs(db - previous_db)
            abs_dw_reduction = np.abs(dw - previous_dw)

            if abs_db_reduction < self.tolerance:
                if abs_dw_reduction.all() < self.tolerance:
                    break

            previous_db = db
            previous_dw = dw

    def predict(self, X_test):
        return X_test @ self.weights + self.bias

class Analyser:
    def __init__(self):
        self.a = 0
    
    def calculate_q(self, data:list, q:float):
        if len(data) < 10:
            return -1
        val = np.quantile(data, q)
        return val
    
    def smooth_prices(self, prices: dict[str, dict[str, float]], alpha: float = 1.0):
        rows = []

        for p1, nested in prices.items():
            for p2, price in nested.items():
                rows.append((p1, p2, price))

        df = pd.DataFrame(rows, columns=["p1", "p2", "price"])

        p1_values = sorted(df["p1"].unique())
        p2_values = sorted(df["p2"].unique())

        X = pd.DataFrame(
            0.0,
            index=df.index,
            columns=[
                *(f"p1:{v}" for v in p1_values),
                *(f"p2:{v}" for v in p2_values),
            ],
        )

        for idx, row in df.iterrows():
            X.loc[idx, f"p1:{row.p1}"] = 1.0
            X.loc[idx, f"p2:{row.p2}"] = 1.0

        model = Ridge(alpha=alpha, fit_intercept=True)
        model.fit(X, df["price"])

        df["smoothed"] = model.predict(X)

        result = {}

        for p1, p2, price in zip(
            df["p1"],
            df["p2"],
            df["smoothed"]
        ):
            result.setdefault(p1, {})[p2] = float(price)

        return result, model
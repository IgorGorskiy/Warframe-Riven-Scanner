import os
os.environ["PYQTGRAPH_QT_LIB"] = "PySide6"

import time

from datetime import datetime

from PySide6.QtCore import QDateTime
from PySide6.QtCore import Signal, QThread, QObject

class LogPrinter(QObject):
    new_log = Signal(str)

    def __init__(self):
        super().__init__()

    def emit_text(self, text):
        self.new_log.emit(text)

class Log(QThread):
    logs:list = list()
    visible_logs:list = list()
    altvLogs:list = list()
    workerLogs:list = list()
    new_log = Signal(str)
    log_printer = LogPrinter()

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

        cur = f"{now}: {text}\n"

        full_text = "\n".join(logs_to_show)
        Log.log_printer.emit_text(full_text)
    
    def log_print(logs = logs):
        print ("LOGS:")
        print(QDateTime.currentDateTime().toString())
        loglen = len(logs)
        if loglen > 15:
            loglen = 15
        for log in logs[-15:-1]:
            print(log)
        print ("\n")
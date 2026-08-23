# ---------------------------------------------------------------------------
# RateLimiter
# ---------------------------------------------------------------------------

import time
import requests
import winsound
from log_printer import LogPrinter, Log

HEADERS = {"accept": "application/json", "platform": "pc"}

def play_sound():
    try:
        winsound.Beep(600, 300)
    except Exception:
        pass

class RateLimiter:
    """Ограничитель частоты запросов: выдерживает минимальный интервал между вызовами."""

    def __init__(self, interval_sec: float) -> None:
        self.cooldown = interval_sec
        self.last_call: float = 0.0

    def wait(self) -> None:
        delta = time.time() - self.last_call
        if delta < self.cooldown:
            time.sleep(self.cooldown - delta)

    def set_interval(self, interval_sec: float) -> None:
        self.cooldown = interval_sec

    def get_response(
        self,
        url: str,
        cooldown: float,
        headers: dict = HEADERS,
        timeout: int = 10,
    ) -> requests.Response:
        start_time = time.perf_counter()
        self.cooldown = cooldown
        self.wait()
        r = requests.get(url, headers=headers, timeout=timeout)
        Log.log_write(f"[REQUESTER]: {url}")
        self.last_call = time.time()
        if r.status_code != 200:
            play_sound()
            play_sound()
            print("HTTP error: ", r.status_code, r.text[:400])
            self.set_interval(15)
            self.last_call = time.time()
            self.wait()
        end_time = time.perf_counter()
        execution_time = end_time - start_time
        Log.log_write(f"Реквест выполнился за {execution_time:.4f} секунд")
        return r
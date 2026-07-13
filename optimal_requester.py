"""
requester.py — пошаговый сборщик аукционов с api.warframe.market.

Ключевые изменения по сравнению с оригиналом:
  - OptimalRequester наследует QObject и отдаёт результаты через сигналы
  - Блокирующий цикл заменён методом do_step(), который делает ровно один HTTP-запрос
  - Задачи (UrlParameters) передаются через очередь (enqueue / clear_queue / cancel_current)
  - Кэш диапазонов рероллов сохраняется в JSON-файл и восстанавливается между сессиями
  - Исправлены баги оригинала (хэш UrlParameters, счётчик i в process_new_batch)
"""

from __future__ import annotations

import json
import time
from collections import deque
from typing import Optional
import requests
from PySide6.QtCore import QObject, Signal
import os

from rate_limiter import RateLimiter

cur_dir = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

HEADERS = {"accept": "application/json", "platform": "pc"}
CACHE_VERSION = 1
CACHE_TTL_SECONDS = 100 * 60 * 60          # 100 часов — после этого кэш считается устаревшим
MAX_REROLLS = 14999                       # максимальный номер рероллов в API


# ---------------------------------------------------------------------------
# UrlParameters
# ---------------------------------------------------------------------------

class UrlParameters:
    """
    Параметры поиска аукционов.

    Поля weapon / pos_att / neg_att образуют «ключ» задачи — именно по ним
    строятся __eq__ и __hash__, и именно они сохраняются в кэше между сессиями.
    Остальные поля (sort, MR_*, rerolls_*) используются только внутри одного
    прохода и сбрасываются методом nullify_unnecessary_parameters().
    """

    def __init__(
        self,
        weapon: str = "",
        pos_att: list[str] | None = None,
        neg_att: str = "",
        sort: str = "asc",
        MR_min: Optional[int] = None,
        MR_max: Optional[int] = None,
        rerolls_min: Optional[int] = None,
        rerolls_max: Optional[int] = None,
    ) -> None:
        self.weapon = weapon
        # Избегаем mutable default argument
        self.pos_att: list[str] = pos_att if pos_att is not None else []
        self.neg_att = neg_att
        self.sort = sort
        self.MR_min = MR_min
        self.MR_max = MR_max
        self.rerolls_min = rerolls_min
        self.rerolls_max = rerolls_max

    # --- Сброс «временных» полей ----------------------------------------

    def nullify_unnecessary_parameters(self) -> None:
        self.sort = "asc"
        self.MR_min = None
        self.MR_max = None
        self.rerolls_min = None
        self.rerolls_max = None

    # --- Идентичность задачи (ключ кэша) -----------------------------------

    def _key(self) -> tuple:
        return (self.weapon, tuple(self.pos_att), self.neg_att)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, UrlParameters):
            return NotImplemented
        return self._key() == other._key()

    def __hash__(self) -> int:
        return hash(self._key())

    # --- Сериализация для JSON-кэша ----------------------------------------

    def to_dict(self) -> dict:
        return {
            "weapon": self.weapon,
            "pos_att": self.pos_att,
            "neg_att": self.neg_att,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "UrlParameters":
        return cls(
            weapon=d.get("weapon", ""),
            pos_att=d.get("pos_att", []),
            neg_att=d.get("neg_att", ""),
        )

    def __repr__(self) -> str:
        return f"UrlParameters(weapon={self.weapon!r}, pos_att={self.pos_att}, neg_att={self.neg_att!r})"


# ---------------------------------------------------------------------------
# UrlConstructor
# ---------------------------------------------------------------------------

class UrlConstructor:
    """Собирает URL запроса из объекта UrlParameters."""

    BASE = "https://api.warframe.market/v1/auctions/search?type=riven"

    def __init__(self) -> None:
        self.parameters = UrlParameters()

    def set_parameters(
        self,
        weapon: str = "none",
        pos_att: list[str] | None = None,
        neg_att: str = "none",
        sort: str = "asc",
        MR_min: int = -1,
        MR_max: int = -1,
        rerolls_min: int = -1,
        rerolls_max: int = -1,
    ) -> None:
        if pos_att is not None and pos_att != ["none"]:
            self.parameters.pos_att = pos_att
        if neg_att != "none":
            self.parameters.neg_att = neg_att
        if sort == "asc":
            self.parameters.sort = sort
        if weapon != "none":
            self.parameters.weapon = weapon
        if MR_min != -1:
            self.parameters.MR_min = MR_min
        if MR_max != -1:
            self.parameters.MR_max = MR_max
        if rerolls_min != -1:
            self.parameters.rerolls_min = rerolls_min
        if rerolls_max != -1:
            self.parameters.rerolls_max = rerolls_max
        else:
            # rerolls_max==-1 означает «убрать ограничение сверху»
            self.parameters.rerolls_max = None

    def build_url(self) -> str:
        p = self.parameters
        url = self.BASE
        if p.pos_att:
            url += "&positive_stats=" + ",".join(p.pos_att)
        if p.neg_att:
            url += "&negative_stats=" + p.neg_att
        if p.sort == "asc":
            url += "&sort_by=price_asc"
        if p.weapon:
            url += "&weapon_url_name=" + p.weapon
        if p.MR_min is not None:
            url += "&mastery_rank_min=" + str(p.MR_min)
        if p.MR_max is not None:
            url += "&mastery_rank_max=" + str(p.MR_max)
        if p.rerolls_min is not None:
            url += "&re_rolls_min=" + str(p.rerolls_min)
        if p.rerolls_max is not None:
            url += "&re_rolls_max=" + str(p.rerolls_max)
        return url


# ---------------------------------------------------------------------------
# OptimalRequester
# ---------------------------------------------------------------------------

class OptimalRequester(QObject):
    """
    Пошаговый сборщик аукционов риве́нов.

    Принцип работы
    --------------
    Основная программа вызывает do_step() раз в N секунд (рекомендуется 7 с,
    так как API warframe.market имеет rate-limit на аукционы).  Каждый вызов
    делает ровно один HTTP-запрос и продвигает обработку текущей задачи.
    Между вызовами do_step() планировщик может выполнять другие запросы.

    Очередь задач
    -------------
    Задачи (UrlParameters) добавляются через enqueue().  Как только текущая
    задача завершается — начинается следующая из очереди.

    Сигналы
    -------
    auctions_ready(params, auctions, t_start, t_end)
        Все аукционы для params собраны.  auctions — список словарей из API,
        t_start / t_end — float (unix-timestamp).

    processing_error(params, message)
        Произошла ошибка при обработке params (HTTP-ошибка или упирание
        в лимит при минимальном шаге рероллов).

    queue_exhausted()
        Очередь опустела и текущая задача завершена — делать нечего.
    """

    auctions_ready = Signal(object, list, float, float)
    processing_error = Signal(object, str)
    queue_exhausted = Signal()

    # Настройки алгоритма (можно переопределить снаружи)
    INITIAL_MAX_REROLLS: int = 10
    MAX_AUCTIONS: int = 500
    DENOMINATOR: int = 2          # делитель шага при переполнении
    SAFETY_MULTIPLIER: float = 1.1

    def __init__(self, rate_limiter = RateLimiter(3), parent: Optional[QObject] = None) -> None:
        super().__init__(parent)

        self._rate_limiter = rate_limiter
        self._url_constructor = UrlConstructor()

        # --- Очередь задач --------------------------------------------------
        self._queue: deque[UrlParameters] = deque()
        self._current_params: Optional[UrlParameters] = None

        # --- Состояние текущего прохода ------------------------------------
        self._stage: int = 0               # номер шага (заменяет локальный i)
        self._start_time: float = 0.0
        self._auctions: list[dict] = []
        self._error: bool = False
        self._need_retry: bool = False     # повторить тот же диапазон (было много аукционов)
        self._last_request_in_queue: bool = False
        self._next_rerolls_step: int = self.INITIAL_MAX_REROLLS
        self._current_rerolls: int = 0
        self._mode: str = "cold_start"    # "cold_start" | "from_cache"
        self.cooldown = 7.0

        # --- Кэш ------------------------------------------------------------
        # _step_cache: данные текущего прохода (точки разбиения)
        self._step_cache: dict = {}
        # _cache_dict: персистентный кэш {UrlParameters -> {timestamp, rerolls_sorted}}
        self._cache_dict: dict[UrlParameters, dict] = {}

    # ==========================================================================
    # Публичный API — управление очередью
    # ==========================================================================

    def set_cooldown(self, interval):
        self.cooldown = float(interval)

    def enqueue(self, parameters: UrlParameters) -> None:
        """Добавить задачу в очередь.  Если сейчас ничего не обрабатывается —
        задача начнётся при следующем вызове do_step()."""
        self._queue.append(parameters)

    def clear_queue(self) -> None:
        """Очистить очередь ожидающих задач.
        Текущая задача (если есть) не прерывается."""
        self._queue.clear()

    def cancel_current(self) -> None:
        """Прервать текущую задачу и перейти к следующей из очереди.
        Частично собранные аукционы отбрасываются."""
        if self._current_params is not None:
            print(f"[OptimalRequester] cancel_current: отменяем {self._current_params}")
        self._finish_current(success=False, emit_signal=False)

    def is_idle(self) -> bool:
        """True, если нет текущей задачи и очередь пуста."""
        return self._current_params is None and len(self._queue) == 0

    # ==========================================================================
    # Публичный API — основной шаг
    # ==========================================================================

    def do_step(self) -> None:
        """Сделать один HTTP-запрос, продвигающий обработку текущей задачи.

        Вызывать этот метод следует по расписанию — раз в 7 секунд.
        Метод сам управляет режимами cold_start / from_cache и переходами
        между задачами в очереди.
        """
        # --- Взять следующую задачу, если сейчас ничего не обрабатывается ---
        if self._current_params is None:
            if not self._queue:
                self.queue_exhausted.emit()
                return
            self._start_next_parameters()

        # --- Один запрос ---------------------------------------------------
        done = self._process_new_batch(self._stage)

        # --- Продвинуть счётчик (если не нужен retry того же диапазона) ---
        if not self._need_retry:
            self._stage += 1
        self._need_retry = False

        # --- Завершение или ошибка -----------------------------------------
        if done:
            print(
                f"[OptimalRequester] ЗАВЕРШЕНО: {len(self._auctions)} аукционов "
                f"за {self._stage} запросов [{self._current_params}]"
            )
            self._save_rerolls_to_cache()
            self.auctions_ready.emit(
                self._current_params,
                list(self._auctions),
                self._start_time,
                time.time(),
            )
            self._finish_current(success=True)
        elif self._error:
            msg = f"Ошибка при обработке {self._current_params}"
            print(f"[OptimalRequester] {msg}")
            self.processing_error.emit(self._current_params, msg)
            self._finish_current(success=False)

    # ==========================================================================
    # Публичный API — персистентность кэша
    # ==========================================================================

    def save_cache_to_file(self, path: str) -> None:
        """Сохранить кэш диапазонов рероллов в JSON-файл."""
        entries = []
        for params, cache_data in self._cache_dict.items():
            entries.append(
                {
                    "parameters": params.to_dict(),
                    "timestamp": cache_data["timestamp"],
                    "rerolls_sorted": cache_data["rerolls_sorted"],
                }
            )
        payload = {"version": CACHE_VERSION, "entries": entries}
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
            print(f"[OptimalRequester] кэш сохранён в {path!r} ({len(entries)} записей)")
        except OSError as e:
            print(f"[OptimalRequester] не удалось сохранить кэш: {e}")

    def load_cache_from_file(self, path: str) -> None:
        """Загрузить кэш диапазонов рероллов из JSON-файла.
        Записи с истёкшим TTL пропускаются.
        Вызывать при старте программы."""
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"[OptimalRequester] файл кэша {path!r} не найден — начинаем без кэша")
            return
        except json.JSONDecodeError as e:
            print(f"[OptimalRequester] файл кэша повреждён ({e}) — начинаем без кэша")
            return

        if data.get("version") != CACHE_VERSION:
            print(
                f"[OptimalRequester] версия кэша {data.get('version')!r} "
                f"не совпадает с текущей ({CACHE_VERSION}) — кэш проигнорирован"
            )
            return

        loaded = 0
        skipped = 0
        now = time.time()
        for entry in data.get("entries", []):
            ts = entry.get("timestamp", 0)
            if now - ts > CACHE_TTL_SECONDS:
                skipped += 1
                continue
            try:
                params = UrlParameters.from_dict(entry["parameters"])
                self._cache_dict[params] = {
                    "timestamp": ts,
                    "rerolls_sorted": entry["rerolls_sorted"],
                }
                loaded += 1
            except (KeyError, TypeError) as e:
                print(f"[OptimalRequester] ошибка при разборе записи кэша: {e}")

        print(
            f"[OptimalRequester] кэш загружен из {path!r}: "
            f"{loaded} записей принято, {skipped} устарело"
        )

    # ==========================================================================
    # Совместимость с оригинальным API (блокирующий режим, для тестов)
    # ==========================================================================

    def get_all_auctions(self, parameters: UrlParameters) -> list[dict]:
        """Блокирующий сбор всех аукционов — аналог оригинального метода.

        Использовать только для тестирования; в основной программе
        используйте enqueue() + do_step().

        Возвращает список аукционов (те же данные, что приходят в сигнал
        auctions_ready).
        """
        result: list[dict] = []

        def _on_ready(_params, auctions, _t0, _t1):
            result.extend(auctions)

        self.auctions_ready.connect(_on_ready)
        self.enqueue(parameters)
        try:
            while not self.is_idle():
                self.do_step()
                time.sleep(7)
        finally:
            self.auctions_ready.disconnect(_on_ready)
        return result

    # ==========================================================================
    # Внутренние методы — управление жизненным циклом задачи
    # ==========================================================================

    def _start_next_parameters(self) -> None:
        """Взять задачу из очереди и инициализировать состояние прохода."""
        params = self._queue.popleft()
        params.nullify_unnecessary_parameters()
        self._current_params = params
        self._url_constructor.parameters = params

        self._stage = 0
        self._start_time = time.time()
        self._auctions = []
        self._error = False
        self._need_retry = False
        self._last_request_in_queue = False
        self._next_rerolls_step = self.INITIAL_MAX_REROLLS
        self._current_rerolls = 0

        # Проверяем персистентный кэш для этих параметров
        self._step_cache.clear()
        if params in self._cache_dict:
            self._create_points_from_cache(self._cache_dict[params])

        self._set_mode()
        print(f"[OptimalRequester] начинаем задачу: {params}  режим={self._mode!r}")

    def _finish_current(self, *, success: bool, emit_signal: bool = True) -> None:
        """Завершить текущую задачу (успешно или нет) и сбросить состояние."""
        if success:
            # Сохраняем персистентный кэш автоматически при каждом успехе
            pass  # save_cache_to_file вызывается снаружи при желании;
                  # либо раскомментируйте строку ниже для авто-сохранения:
            # self.save_cache_to_file("riven_cache.json")

        self._current_params = None
        self._step_cache.clear()

    # ==========================================================================
    # Внутренние методы — кэш
    # ==========================================================================

    def _timestamp_to_tolerance(self, ts: float) -> int:
        """Чем старше кэш, тем больше допуск на количество аукционов в батче
        (старые данные о распределении рероллов менее точны)."""
        td = (time.time() - ts) / 3600  # в часах
        if td < 3:
            return 5
        if td < 10:
            return 15
        if td < 20:
            return 25
        if td < 40:
            return 50
        if td < 80:
            return 100
        if td < 160:
            return 200
        return 250

    def _save_rerolls_to_cache(self) -> None:
        """Сохранить отсортированный список рероллов из текущего прохода
        в персистентный кэш (_cache_dict)."""
        re_rolls_list = []
        for auc in self._auctions:
            item = auc.get("item", {})
            re_rolls = item.get("re_rolls", -1)
            if re_rolls < 0:
                print("[OptimalRequester] WARNING: аукцион без поля re_rolls")
                continue
            re_rolls_list.append(re_rolls)
        re_rolls_list.sort()

        # Ключ — параметры без временны́х полей
        key = UrlParameters.from_dict(self._current_params.to_dict())
        self._cache_dict[key] = {
            "timestamp": time.time(),
            "rerolls_sorted": re_rolls_list,
        }
        print(
            f"[OptimalRequester] кэш обновлён для {key}: "
            f"{len(re_rolls_list)} записей о рероллах"
        )

    def _create_points_from_cache(self, cache: dict) -> None:
        """Разбить сохранённый список рероллов на точки-сплиттеры батчей.

        Результат записывается в self._step_cache["rerolls_points"] —
        список значений реролла, на которых надо «разрезать» диапазон.
        Первый элемент всегда -1 (начало).
        """
        re_rolls_list: list[int] = cache["rerolls_sorted"]
        ts: float = cache["timestamp"]
        tolerance = self._timestamp_to_tolerance(ts)
        print(f"[OptimalRequester] tolerance для кэша: {tolerance}")

        if not re_rolls_list:
            return

        re_rolls_points: list[int] = [-1]
        current_elem = re_rolls_list[0]
        prev_elem = re_rolls_list[0]
        elem_count = 0
        leftover = 0

        for elem in re_rolls_list:
            elem_count += 1
            leftover += 1
            if elem_count > 460 - tolerance:
                re_rolls_points.append(prev_elem)
                elem_count = leftover
            if elem > current_elem:
                prev_elem = current_elem
                current_elem = elem
                leftover = 0

        self._step_cache["timestamp"] = time.time()
        self._step_cache["rerolls_points"] = re_rolls_points
        print(
            f"[OptimalRequester] точки сплита из кэша ({len(re_rolls_points) - 1} батчей): "
            f"{re_rolls_points}"
        )

    # ==========================================================================
    # Внутренние методы — режим и запросы
    # ==========================================================================

    def _set_mode(self) -> None:
        """Выбрать режим обхода: from_cache (есть валидные точки) или cold_start."""
        if not self._step_cache.get("rerolls_points"):
            self._mode = "cold_start"
            return
        age = time.time() - self._step_cache.get("timestamp", 0)
        if age > CACHE_TTL_SECONDS:
            self._step_cache.clear()
            self._mode = "cold_start"
        else:
            self._mode = "from_cache"

    def _process_new_batch(self, stage: int) -> bool:
        """Сформировать URL, выполнить запрос и обработать результат.

        Возвращает True, если все аукционы для текущих параметров получены.
        Возвращает False, если нужно продолжить (или произошла ошибка —
        тогда также выставляет self._error = True).

        Побочные эффекты:
          self._need_retry = True  — следующий do_step() повторит тот же stage
        """
        # --- Формирование параметров запроса --------------------------------
        rerolls_points = self._step_cache.get("rerolls_points", [])

        if self._mode == "from_cache":
            if stage + 1 < len(rerolls_points):
                # Обычный батч из кэша
                self._url_constructor.set_parameters(
                    rerolls_min=rerolls_points[stage] + 1,
                    rerolls_max=rerolls_points[stage + 1],
                )
            else:
                # Последний батч кэша — без верхней границы
                self._url_constructor.set_parameters(
                    rerolls_min=rerolls_points[stage] + 1,
                    rerolls_max=-1,  # -1 означает «убрать ограничение»
                )
        else:
            # cold_start
            if self._last_request_in_queue:
                # Финальный запрос без верхней границы
                self._url_constructor.set_parameters(
                    rerolls_min=self._current_rerolls,
                    rerolls_max=-1,
                )
            else:
                self._url_constructor.set_parameters(
                    rerolls_min=self._current_rerolls,
                    rerolls_max=self._current_rerolls + self._next_rerolls_step,
                )

        url = self._url_constructor.build_url()
        print(f"[OptimalRequester] GET {url}")

        # --- HTTP-запрос ----------------------------------------------------
        try:
            r = self._rate_limiter.get_response(url, self.cooldown, HEADERS, 10)
        except requests.RequestException as e:
            print(f"[OptimalRequester] сетевая ошибка: {e}")
            self._error = True
            return False

        if r.status_code != 200:
            print(
                f"[OptimalRequester] HTTP {r.status_code}:\n{r.text[:500]}"
            )
            self._error = True
            return False

        # --- Разбор ответа --------------------------------------------------
        payload = r.json().get("payload", {})
        if not payload:
            print("[OptimalRequester] no payload")
            if self._last_request_in_queue:
                self._last_request_in_queue = False
                return True
            self._error = True
            return False

        auctions: list[dict] = payload["auctions"]

        # --- Проверка переполнения ------------------------------------------
        if len(auctions) >= self.MAX_AUCTIONS - 15:
            if self._mode == "from_cache":
                print(
                    f"[OptimalRequester] ОШИБКА: переполнение в режиме кэша "
                    f"({len(auctions)} аукционов) — кэш сброшен"
                )
                self._step_cache.clear()
                self._error = True
                return False

            print(
                f"[OptimalRequester] WARNING: слишком много аукционов ({len(auctions)}); "
                f"уменьшаем шаг {self._next_rerolls_step} → "
                f"{max(1, self._next_rerolls_step // self.DENOMINATOR)}"
            )
            if self._next_rerolls_step > self.DENOMINATOR:
                self._next_rerolls_step = max(
                    1, self._next_rerolls_step // self.DENOMINATOR
                )
                # Пометить: следующий do_step() повторит тот же stage
                self._need_retry = True
                return False
            else:
                print(
                    "[OptimalRequester] ОШИБКА: шаг рероллов уже минимален, "
                    "но аукционов по-прежнему слишком много"
                )
                self._error = True
                return False

        print(
            f"[OptimalRequester] получено {len(auctions)} аукционов "
            f"(реролы {self._url_constructor.parameters.rerolls_min}–"
            f"{self._url_constructor.parameters.rerolls_max})"
        )

        # --- Продвижение курсора (cold_start) --------------------------------
        self._current_rerolls += self._next_rerolls_step + 1

        auctions_amount = len(auctions)

        # В cold_start: 0 аукционов — значит дошли до конца, делаем финальный запрос
        if auctions_amount == 0 and self._mode != "from_cache" and not self._last_request_in_queue:
            self._last_request_in_queue = True
            return False

        self._auctions.extend(auctions)
        print(
            f"[OptimalRequester] итого аукционов: {len(self._auctions)}"
        )

        # --- Пересчёт шага для следующего батча -----------------------------
        effective_amount = max(1, auctions_amount)
        potential = float(self.MAX_AUCTIONS) / float(effective_amount)
        next_step_float = self._next_rerolls_step * potential * self.SAFETY_MULTIPLIER
        self._next_rerolls_step = max(1, int(next_step_float))

        # Предпоследний батч в cold_start: если следующий шаг выходит за MAX_REROLLS
        if (
            self._mode == "cold_start"
            and not self._last_request_in_queue
            and self._current_rerolls + self._next_rerolls_step >= MAX_REROLLS
        ):
            self._next_rerolls_step = MAX_REROLLS - self._current_rerolls
            self._last_request_in_queue = True
            return False

        # --- Условия завершения ---------------------------------------------
        if self._mode == "from_cache" and stage + 1 >= len(rerolls_points):
            print(
                f"[OptimalRequester] SUCCESS (cache): последний батч, "
                f"аукционов в батче: {auctions_amount}"
            )
            return True

        if self._last_request_in_queue:
            print(
                f"[OptimalRequester] SUCCESS (cold_start): последний батч, "
                f"аукционов в батче: {auctions_amount}"
            )
            self._last_request_in_queue = False
            return True

        return False


# ---------------------------------------------------------------------------
# Пример использования (запускать напрямую для тестирования)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from PySide6.QtCore import QCoreApplication

    CACHE_FILE = "riven_cache.json"

    app = QCoreApplication(sys.argv)
    requester = OptimalRequester()

    # Загрузить кэш прошлой сессии
    requester.load_cache_from_file(CACHE_FILE)

    # Подключить сигналы
    def on_ready(params, auctions, t_start, t_end):
        print(
            f"\n=== ГОТОВО: {params} — {len(auctions)} аукционов "
            f"за {t_end - t_start:.1f} с ==="
        )
        # После каждого успешного результата сохраняем кэш
        requester.save_cache_to_file(CACHE_FILE)

    def on_error(params, msg):
        print(f"\n=== ОШИБКА: {params}: {msg} ===")

    def on_exhausted():
        print("\n=== Очередь пуста ===")

    requester.auctions_ready.connect(on_ready)
    requester.processing_error.connect(on_error)
    requester.queue_exhausted.connect(on_exhausted)

    # Поставить задачи в очередь
    requester.enqueue(UrlParameters(weapon="acceltra"))
    requester.enqueue(UrlParameters(weapon="acceltra"))  # второй вызов — должен использовать кэш

    # Блокирующий тест (в реальном проекте — таймер QTimer)
    while not requester.is_idle():
        requester.do_step()
        time.sleep(7)

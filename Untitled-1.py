
import time
import json

def _create_points_from_cache(cache: dict) -> None:
    """Разбить сохранённый список рероллов на точки-сплиттеры батчей.
    Результат записывается в self._step_cache["rerolls_points"] —
    список значений реролла, на которых надо «разрезать» диапазон.
    Первый элемент всегда -1 (начало).
    """
    re_rolls_list: list[int] = cache["rerolls_sorted"]
    ts: float = cache["timestamp"]
    tolerance = 5
    print(f"[OptimalRequester] tolerance для кэша: {tolerance}")
    if not re_rolls_list:
        return
    re_rolls_points: list[int] = [-1]
    current_elem = re_rolls_list[0]
    prev_elem = re_rolls_list[0]
    elem_count = 0
    leftover = 0
    for elem in re_rolls_list:
        if elem == 69:
            f = 1
        elem_count += 1
        leftover += 1
        if elem_count > 460 - tolerance:
            re_rolls_points.append(prev_elem)
            elem_count = leftover
        if elem > current_elem:
            prev_elem = current_elem
            current_elem = elem
            leftover = 0
    _step_cache = {}
    _step_cache["timestamp"] = time.time()
    _step_cache["rerolls_points"] = re_rolls_points
    print(
        f"[OptimalRequester] точки сплита из кэша ({len(re_rolls_points) - 1} батчей): "
        f"{re_rolls_points}"
    )

with open("C:/amyfiles/projects/rivenendo/riven_cache.json") as f:
    _cache_dict = json.load(f)
entries = _cache_dict["entries"]
e = entries[0]
_create_points_from_cache(e)
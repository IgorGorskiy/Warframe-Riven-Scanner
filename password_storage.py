from __future__ import annotations

import json
from pathlib import Path

import keyring
import os
cur_dir = os.path.dirname(os.path.abspath(__file__))

class CredentialsStorage:
    """
    Безопасное хранение учетных данных.

    Логин сохраняется в конфиг-файле.
    Пароль хранится в системном хранилище секретов ОС.
    """

    SERVICE_NAME = "MyApplication"

    def __init__(self, config_path: str | Path = os.path.join(cur_dir, "login.json")):
        self.config_path = Path(config_path)

    def save(self, login: str, password: str, username: str) -> None:
        # сохраняем пароль в системное хранилище
        keyring.set_password(
            self.SERVICE_NAME,
            username,
            password
        )

        # сохраняем только логин
        data = {
            "username": username,
            "login": login
        }

        self.config_path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )

    def load(self) -> tuple[str, str, str]:
        if not self.config_path.exists():
            #raise FileNotFoundError("Конфигурация не найдена")
            return "fail", "fail","fail"

        data = json.loads(
            self.config_path.read_text(encoding="utf-8")
        )

        username = data["username"]
        login = data["login"]

        password = keyring.get_password(
            self.SERVICE_NAME,
            username
        )

        if password is None:
            raise RuntimeError(
                "Пароль отсутствует в системном хранилище"
            )

        return login, password, username

    def delete(self) -> None:
        if not self.config_path.exists():
            return

        data = json.loads(
            self.config_path.read_text(encoding="utf-8")
        )

        username = data["username"]

        try:
            keyring.delete_password(
                self.SERVICE_NAME,
                username
            )
        except keyring.errors.PasswordDeleteError:
            pass

        self.config_path.unlink()
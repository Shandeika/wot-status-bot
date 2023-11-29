import datetime
from typing import List
from .server import Server


class Cluster:
    def __init__(self, title: str, servers: dict, version: str, version_updated_at: int, flag: str, online: int):
        servers_objects = list()
        for server in servers:
            server_obj = Server(
                name=server.get('name'),
                majority=server.get('majority'),
                recommendation=server.get('recommendation'),
                status=server.get('status'),
                online=server.get('online'),
                state_log=server.get('state_log')
            )
            servers_objects.append(server_obj)
        self._title = title
        self._servers = servers_objects
        self._version = version
        self._version_updated_at = version_updated_at
        self._flag = flag
        self._online = online

    @property
    def title(self) -> str:
        """Возвращает название кластера"""
        return self._title

    @property
    def servers(self) -> List[Server]:
        """Возвращает список серверов в кластере"""
        return self._servers

    @property
    def version(self) -> str:
        """Возвращает версию серверов в кластере"""
        return self._version if self._version else "Неизвестно"

    @property
    def version_updated_at(self) -> datetime.datetime:
        """Возвращает время обновления версии как datetime"""
        return datetime.datetime.fromtimestamp(self._version_updated_at)

    @property
    def flag(self) -> str:
        """Возвращает флаг в формате :flag_code:"""
        flag_emoji = f":flag_{self._flag}:"
        return flag_emoji if self._flag else ""

    @property
    def online(self) -> int | str:
        """Возвращает онлайн серверов в кластере
        Если онлайн неизвестен, возвращает строку "Недоступно" """
        return self._online if self._online else "Недоступно"

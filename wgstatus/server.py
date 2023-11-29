from typing import List

import discord

from .enums import StatusEmoji, StatusWord


class StateLog:
    def __init__(self, timestamp: int, state: str):
        self.timestamp = timestamp
        self.state = state


class Server:
    def __init__(self, name: str, majority: str, recommendation: str, status: str, online: int = None,
                 state_log: dict = None):
        self._name = name
        self._majority = majority
        self._recommendation = recommendation
        self._status = status
        self._online = online
        self._state_log = None
        if state_log:
            self._state_log = list()
            for state in state_log:
                self._state_log.append(StateLog(state[0], state[1]))

    @property
    def online(self) -> int | str:
        """Возвращает онлайн сервера
        Если онлайн неизвестен, возвращает строку "Недоступно" """
        return self._online if self._online else "Недоступно"

    @property
    def name(self) -> str:
        return self._name

    @property
    def majority(self) -> str:
        return self._majority

    @property
    def recommendation(self) -> str:
        return self._recommendation

    @property
    def status(self) -> str:
        return self._status

    @property
    def state_log(self) -> List[StateLog]:
        return self._state_log

    @property
    def status_emoji(self) -> discord.PartialEmoji:
        match self.status:
            case "online":
                return discord.PartialEmoji.from_str(StatusEmoji.ONLINE.value)
            case "offline":
                return discord.PartialEmoji.from_str(StatusEmoji.OFFLINE.value)

    @property
    def status_word(self) -> str:
        match self.status:
            case "online":
                return StatusWord.ONLINE.value
            case "offline":
                return StatusWord.OFFLINE.value


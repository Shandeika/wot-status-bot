from enum import Enum


class StatusEmoji(Enum):
    ONLINE = "<:online:741779665026547813>"
    OFFLINE = "<:offline:741779665017897047>"


class StatusWord(Enum):
    ONLINE = "Онлайн"
    OFFLINE = "Выключен"

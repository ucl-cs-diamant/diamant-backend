from enum import Enum


class Leagues(Enum):
    DIV_ONE = 1
    DIV_TWO = 1 << 1
    DIV_THREE = 1 << 2
    DIV_FOUR = 1 << 3

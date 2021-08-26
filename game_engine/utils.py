from enum import Enum


class Leagues(Enum):
    DIV_1 = 1
    DIV_2 = 1 << 1
    DIV_3 = 1 << 2
    DIV_4 = 1 << 3

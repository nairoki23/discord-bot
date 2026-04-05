import enum
from sqlalchemy import Enum

class Carrier(enum.Enum):
    YAMATO = "yamato"
    SAGAWA = "sagawa"
    JP = "jp"
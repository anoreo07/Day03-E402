"""Tools package for e-commerce agent.

Expose small utility functions used by the Agent and baseline chatbot.
Each tool is implemented as a pure function that takes explicit inputs and
returns simple serializable outputs (dicts, numbers, booleans).
"""

from .check_stock import check_stock, get_stock_level
from .get_price import get_price
from .get_discount import get_discount
from .calc_shipping import calc_shipping
from .calc_tax import calc_tax

__all__ = [
    "check_stock",
    "get_stock_level",
    "get_price",
    "get_discount",
    "calc_shipping",
    "calc_tax",
]

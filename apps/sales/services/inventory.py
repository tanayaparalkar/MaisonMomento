"""
apps/sales/services/inventory.py
==================================
Compatibility shim.

Inventory logic has been extracted to a dedicated domain at apps.inventory.
This file imports everything from the new location to prevent regressions
and preserve existing module paths across the codebase.
"""

from apps.inventory.services import (
    InsufficientStockError,
    check_stock,
    deduct_inventory,
    get_inventory_summary,
    adjust_stock,
)

__all__ = [
    "InsufficientStockError",
    "check_stock",
    "deduct_inventory",
    "get_inventory_summary",
    "adjust_stock",
]

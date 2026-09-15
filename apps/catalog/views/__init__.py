"""
apps/catalog/views/__init__.py
================================
Public API of the catalog views package.

Re-exports every view function that is referenced by:
  - apps/catalog/urls.py          (catalog namespace)
  - maison_momento/urls.py        (root namespace — about, contact, collections)

This means urls.py does NOT need to change:
  from . import views
  views.product_list   → works
  views.about          → works
  etc.
"""

from .collections import collections          # noqa: F401
from .pages import about, contact             # noqa: F401
from .products import product_detail, product_list  # noqa: F401
from .wishlist import toggle_wishlist, wishlist_view  # noqa: F401

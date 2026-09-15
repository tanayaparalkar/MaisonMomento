"""
apps/catalog/views/pages.py
=============================
Flat informational pages — about and contact.
"""

from django.shortcuts import render


def about(request):
    return render(request, "catalog/about.html")


def contact(request):
    return render(request, "catalog/contact.html")

#!/usr/bin/env python3
"""
Secure Container Access Manager — module entry point.

Usage:
    sudo ./venv/bin/python3 -m src <container_name>
"""

import os
import sys

# Ensure src/ directory is on sys.path so sibling modules (db, accounts, etc.)
# can be imported regardless of how this package was invoked.
_here = os.path.dirname(os.path.abspath(__file__))
if _here not in sys.path:
    sys.path.insert(0, _here)

from enter import main

if __name__ == "__main__":
    main()

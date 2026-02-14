#!/usr/bin/env python
"""Quick test para main.py - solo muestra el menu"""

import sys
sys.path.insert(0, 'src')

from main import menu_principal

try:
    menu_principal()
    print("\n[OK] Main.py menu renderizó correctamente sin errores de encoding")
except UnicodeEncodeError as e:
    print(f"[ERROR] Encoding issue: {e}")
except Exception as e:
    print(f"[ERROR] {e}")

"""Navas agent: یک نقطه‌ی ورود برای اجرای سیستم.
استفاده:  python3 run.py case6
"""
import os
import subprocess
import sys

if len(sys.argv) != 2:
    sys.exit("استفاده: python3 run.py <نام پرونده>   مثال: python3 run.py case6")

here = os.path.dirname(os.path.abspath(__file__))
sys.exit(subprocess.call([sys.executable, os.path.join(here, "agent.py"), sys.argv[1]], cwd=here))

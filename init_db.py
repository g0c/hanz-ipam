# v1.0.1
# Skripta za inicijalizaciju baze - smještena u ROOT projekta.

import sys
import os

# Osiguravamo da Python vidi 'app' mapu
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.db import engine, Base
from app.core.models import User, Device, Subnet, AuditLog

def init_db():
    print(f"[*] Inicijalizacija baze na: {engine.url}")
    try:
        # Ovo će stvoriti sve tablice koje nedostaju (npr. audit_logs)
        Base.metadata.create_all(bind=engine)
        print("[+] Tablice su sinkronizirane.")
    except Exception as e:
        print(f"[!] Greška: {e}")

if __name__ == "__main__":
    init_db()
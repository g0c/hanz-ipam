# v1.0.1
# Skripta za automatski backup baze i koda - IPAM projekt.

import os
import subprocess
from datetime import datetime
from app.core.config import settings

def run_backup():
    # 1. Postavljanje varijabli
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"ipam_backup_{timestamp}"
    sql_file = f"{backup_name}.sql"
    archive_file = f"{backup_name}.tar.gz"
    
    # Izvlačenje podataka iz DATABASE_URL (mysql+mysqlconnector://user:pass@host/db)
    # Pretpostavljamo standardni format iz tvojih postavki
    try:
        db_uri = settings.DATABASE_URL.replace("mysql+mysqlconnector://", "")
        auth, rest = db_uri.split("@")
        user, password = auth.split(":")
        host_db = rest.split("/")
        host = host_db[0]
        db_name = host_db[1]
    except Exception as e:
        print(f"Greška pri parsiranju DATABASE_URL: {e}")
        return

    print(f"--- Pokrećem backup za projekt: {settings.APP_NAME} ---")

    # 2. Export baze podataka (SQL Dump)
    print(f"[*] Izvozim bazu '{db_name}'...")
    dump_cmd = [
        "mysqldump",
        f"-u{user}",
        f"-p{password}",
        f"-h{host}",
        db_name
    ]
    
    with open(sql_file, "w") as f:
        result = subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            print(f"[!] Greška kod SQL dump-a: {result.stderr}")
            return

    # 3. Kreiranje komprimirane arhive (Kod + SQL)
    print(f"[*] Pakiram kod i bazu u {archive_file}...")
    # Isključujemo venv, git i cache foldere da arhiva ne bude ogromna
    tar_cmd = [
        "tar",
        "-czf", archive_file,
        "--exclude=venv",
        "--exclude=.git",
        "--exclude=__pycache__",
        "--exclude=*.tar.gz",
        ".",  # Trenutni direktorij
        sql_file
    ]
    
    result = subprocess.run(tar_cmd, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        print(f"[+] Backup uspješan: {archive_file}")
        # Brišemo privremeni SQL file jer je sada unutar tar.gz arhive
        os.remove(sql_file)
    else:
        print(f"[!] Greška kod pakiranja: {result.stderr}")

if __name__ == "__main__":
    run_backup()
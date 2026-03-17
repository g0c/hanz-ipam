# v1.0.3
# Skripta za automatski backup s uključenom čistkom starih arhiva (7 dana).

import os
import subprocess
import time
from datetime import datetime
from urllib.parse import urlparse
from app.core.config import settings

def run_backup():
    base_dir = "/home/su/projects/hanz-ipam"
    backup_dir = os.path.join(base_dir, "backups")
    retention_days = 7  # Koliko dana čuvamo backupe prije brisanja
    
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)

    os.chdir(base_dir)

    # 1. Postavljanje varijabli
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    backup_name = f"ipam_backup_{timestamp}"
    sql_file = f"{backup_name}.sql"
    archive_file = os.path.join(backup_dir, f"{backup_name}.tar.gz")
    
    try:
        db_uri = settings.DATABASE_URL.replace("mysql+mysqlconnector://", "mysql://")
        parsed = urlparse(db_uri)
        user = parsed.username
        password = parsed.password
        host = parsed.hostname
        db_name = parsed.path.lstrip('/')
    except Exception as e:
        print(f"Greška pri parsiranju DATABASE_URL: {e}")
        return

    print(f"--- Pokrećem backup za projekt: {settings.APP_NAME} ---")

    # 2. Export baze podataka (SQL Dump)
    print(f"[*] Izvozim bazu '{db_name}'...")
    dump_cmd = ["mysqldump", f"-u{user}", f"-h{host}", db_name]
    env = os.environ.copy()
    env["MYSQL_PWD"] = password

    with open(sql_file, "w") as f:
        result = subprocess.run(dump_cmd, stdout=f, stderr=subprocess.PIPE, text=True, env=env)
        if result.returncode != 0:
            print(f"[!] Greška kod SQL dump-a: {result.stderr}")
            if os.path.exists(sql_file): os.remove(sql_file)
            return

    # 3. Kreiranje komprimirane arhive
    print(f"[*] Pakiram kod i bazu u {archive_file}...")
    tar_cmd = ["tar", "-czf", archive_file, "--exclude=venv", "--exclude=.git", "--exclude=__pycache__", "--exclude=backups", "."]
    
    result = subprocess.run(tar_cmd, stderr=subprocess.PIPE, text=True)
    if result.returncode == 0:
        print(f"[+] Backup uspješan: {archive_file}")
        if os.path.exists(sql_file): os.remove(sql_file)
        
        # --- 4. ČIŠĆENJE STARIH BACKUPOVA ---
        print(f"[*] Provjeravam stare backupe (starije od {retention_days} dana)...")
        now = time.time()
        for f in os.listdir(backup_dir):
            file_path = os.path.join(backup_dir, f)
            # Provjeravamo samo datoteke koje završavaju na .tar.gz
            if os.path.isfile(file_path) and f.endswith(".tar.gz"):
                file_age_days = (now - os.path.getmtime(file_path)) / (24 * 3600)
                if file_age_days > retention_days:
                    print(f"[#] Brišem staru arhivu: {f}")
                    os.remove(file_path)
        print("[+] Čišćenje završeno.")
        
    else:
        print(f"[!] Greška kod pakiranja: {result.stderr}")

if __name__ == "__main__":
    run_backup()
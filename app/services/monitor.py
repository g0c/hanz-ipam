# v1.0.1
# Servis za pozadinsko pinganje uređaja i ažuriranje statusa (CheckIPAM Lite).

import subprocess
import platform
from datetime import datetime
from sqlalchemy.orm import Session
from app.core.models import Device, DeviceStatus

def ping_ip(ip: str) -> bool:
    """
    Šalje jedan ICMP ping prema IP adresi.
    Vraća True ako je uređaj dostupan, inače False.
    """
    # Određivanje parametara ovisno o OS-u (Linux koristi -c, Windows -n)
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    # -W 1 postavlja timeout na 1 sekundu (Lite monitor mora biti brz)
    command = ['ping', param, '1', '-W', '1', ip] if param == '-c' else ['ping', param, '1', ip]
    
    try:
        result = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return result.returncode == 0
    except Exception:
        return False

def run_monitor_lite(db: Session):
    """
    Prolazi kroz sve uređaje u bazi, pinga ih i ažurira status i last_seen.
    """
    # KOMENTAR: Dohvaćamo sve uređaje koji nisu 'reserved'
    devices = db.query(Device).all()
    
    for device in devices:
        # Rezervirane adrese ne pingamo jer status diktira admin
        if device.status == DeviceStatus.reserved:
            continue
            
        is_alive = ping_ip(device.ip_addr)
        
        if is_alive:
            device.status = DeviceStatus.active
            device.last_seen = datetime.now()
        else:
            # Ako je bio aktivan a sad se ne javlja, stavljamo ga u offline
            if device.status == DeviceStatus.active:
                device.status = DeviceStatus.offline
        
    db.commit()
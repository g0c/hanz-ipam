# v1.0.2
# WebSocket ruter za live streaming mrežnog skeniranja u realnom vremenu.

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import asyncio
import ipaddress

from app.api.dependencies import get_db
from app.services import discovery_service
from app.core.models import Subnet

router = APIRouter()

@router.websocket("/ws/scan/{subnet_id}")
async def websocket_endpoint(websocket: WebSocket, subnet_id: int, db: Session = Depends(get_db)):
    """
    Endpoint za praćenje skeniranja uživo. 
    Prvo prihvaćamo vezu, a zatim šaljemo podatke.
    """
    await websocket.accept()
    
    try:
        # Dohvat subneta iz baze
        subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()
        if not subnet:
            await websocket.send_text("<span class='text-danger'>[ERROR] Subnet not found in database.</span>")
            await websocket.close()
            return

        await websocket.send_text(f"[*] Starting discovery Engine for {subnet.cidr}...")
        await asyncio.sleep(0.3)
        
        # Generiranje IP adresa za skeniranje
        network = ipaddress.ip_network(subnet.cidr)
        hosts = [str(ip) for ip in network.hosts()]
        
        await websocket.send_text(f"[*] Target count: {len(hosts)} hosts. Initiating ping sweep...")

        for ip in hosts:
            # Izvršavanje pinga kroz servis
            is_alive = discovery_service.ping_ip(ip)
            
            if is_alive:
                # Ako je host živ, odmah ga evidentiramo i javljamo terminalu
                await websocket.send_text(f"<span class='text-success fw-bold'>[FOUND]</span> {ip} is active.")
                # Asinkrono ažuriranje baze u pozadini
                discovery_service.scan_single_ip(db, ip, subnet_id)
            else:
                await websocket.send_text(f"<span class='text-muted'>[SKIP]</span>  {ip} no response.")
            
            # Pauza od 50ms osigurava 'scrolling' efekt u terminalu
            await asyncio.sleep(0.05)

        await websocket.send_text("<br><span class='text-warning fw-bold'>[+] SCAN COMPLETED SUCCESSFULLY.</span>")
        
    except WebSocketDisconnect:
        # Klijent je zatvorio tab ili osvježio stranicu
        pass
    except Exception as e:
        await websocket.send_text(f"<span class='text-danger'>[CRITICAL ERROR] {str(e)}</span>")
    finally:
        try:
            await websocket.close()
        except:
            pass
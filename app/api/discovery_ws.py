# v1.1.1
# WebSocket ruter za Turbo Scan - Optimiziran za stabilnost baze.
# Smanjen broj istovremenih pingova kako bi se izbjegao Database Lock.

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
import asyncio
import json
from app.core.db import SessionLocal
from app.services import discovery_service
from app.core.models import Subnet
import ipaddress

router = APIRouter()

# v1.1.2
# Turbo Scan WebSocket - "Hardened" verzija.
# Osigurano slanje 'finish' signala čak i u slučaju grešaka.

@router.websocket("/ws/discovery/{subnet_id}")
async def websocket_discovery(websocket: WebSocket, subnet_id: int):
    await websocket.accept()
    db = SessionLocal()
    try:
        # ... (kod za dohvaćanje subneta ostaje isti) ...
        network = ipaddress.ip_network(subnet.cidr)
        hosts = [str(ip) for ip in network.hosts()]
        await websocket.send_text(json.dumps({"type": "start", "total": len(hosts)}))

        semaphore = asyncio.Semaphore(20)
        tasks = [discovery_service.async_ping(ip, semaphore) for ip in hosts]

        # KOMENTAR: Koristimo wait_for da cijeli scan ne može trajati vječno (npr. max 5 min za /24)
        try:
            for task in asyncio.as_completed(tasks):
                ip, is_online = await task
                try:
                    discovery_service.process_scan_result(db, ip, is_online, subnet_id)
                    db.commit()
                except Exception as db_err:
                    db.rollback()
                    print(f"DB Error na {ip}: {db_err}")

                await websocket.send_text(json.dumps({
                    "type": "result",
                    "ip": ip,
                    "is_online": is_online
                }))
                await asyncio.sleep(0.01)
        except Exception as loop_err:
            print(f"Loop Error: {loop_err}")

        # KOMENTAR: Ovo MURA biti izvan petlje da bi klijent dobio obavijest o kraju
        await websocket.send_text(json.dumps({"type": "finish"}))

    except Exception as e:
        print(f"WS Critical: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except: pass
    finally:
        db.close()
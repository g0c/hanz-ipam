# app/api/discovery_ws.py
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import asyncio
import json
import ipaddress

from app.core.db import SessionLocal
from app.core.models import Subnet
from app.services import discovery_service

router = APIRouter()

# RUTA MORA BITI /ws/discovery/
@router.websocket("/ws/discovery/{subnet_id}")
async def websocket_discovery(websocket: WebSocket, subnet_id: int):
    await websocket.accept()
    
    db = SessionLocal()
    try:
        # OVA LINIJA JE BILA PROBLEM - Sada je tu!
        subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()
        
        if not subnet:
            await websocket.send_text(json.dumps({"type": "error", "message": "Subnet nije pronađen."}))
            return

        network = ipaddress.ip_network(subnet.cidr)
        hosts = [str(ip) for ip in network.hosts()]
        
        await websocket.send_text(json.dumps({"type": "start", "total": len(hosts)}))

        semaphore = asyncio.Semaphore(20)
        tasks = [discovery_service.async_ping(ip, semaphore) for ip in hosts]

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

        await websocket.send_text(json.dumps({"type": "finish"}))

    except WebSocketDisconnect:
        print(f"[*] Korisnik napustio scan subneta {subnet_id}")
    except Exception as e:
        print(f"WS Critical: {e}")
        try:
            await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
        except: 
            pass
    finally:
        db.close()
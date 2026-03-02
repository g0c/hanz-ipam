# v1.0.6
# Servis za logiku mrežnih segmenata - izračuni IP adresa i statistika.

from sqlalchemy.orm import Session
from app.core.models import Subnet, Device
import ipaddress

# Dohvaća osnovni objekt podmreže
def get_subnet(db: Session, subnet_id: int):
    return db.query(Subnet).filter(Subnet.id == subnet_id).first()

# Glavna funkcija koju ruter poziva za listu podmreža sa statistikom
def get_subnets_with_usage(db: Session):
    subnets = db.query(Subnet).all()
    results = []

    for s in subnets:
        try:
            network = ipaddress.ip_network(s.cidr)
            # Ukupan broj iskoristivih adresa (bez mrežne i broadcast)
            # Za /32 i /31 mreže num_addresses je točniji, ali za standardne koristimo hosts()
            total_hosts = network.num_addresses
            
            # Broj uređaja koji su trenutno u bazi vezani za ovaj subnet
            used_hosts = db.query(Device).filter(Device.subnet_id == s.id).count()
            
            # Izračun postotka (pazimo na dijeljenje s nulom)
            usage_pct = 0
            if total_hosts > 0:
                usage_pct = round((used_hosts / total_hosts) * 100, 1)

            results.append({
                "obj": s,
                "used": used_hosts,
                "total": total_hosts,
                "usage_pct": usage_pct
            })
        except ValueError:
            # Ako je CIDR u bazi neispravan, preskačemo ili vraćamo nule
            results.append({
                "obj": s,
                "used": 0,
                "total": 0,
                "usage_pct": 0
            })
    
    return results

# Funkcija za vizualnu mapu IP adresa
def get_subnet_map(db: Session, subnet_id: int):
    subnet = get_subnet(db, subnet_id)
    if not subnet:
        return None

    try:
        network = ipaddress.ip_network(subnet.cidr)
        # Dohvaćamo sve uređaje u ovom subnetu i mapiramo ih po IP adresi radi brže pretrage
        devices = db.query(Device).filter(Device.subnet_id == subnet_id).all()
        device_map = {d.ip_addr: d for d in devices}

        ip_list = []
        for ip in network:
            ip_str = str(ip)
            device = device_map.get(ip_str)
            
            # Određivanje tipa adrese
            addr_type = 'host'
            if ip == network.network_address:
                addr_type = 'network'
            elif ip == network.broadcast_address:
                addr_type = 'broadcast'
            elif ip_str.endswith('.1'): # Pretpostavka za Gateway, može se i u bazi definirati
                addr_type = 'gateway'

            ip_list.append({
                "ip": ip_str,
                "is_used": device is not None,
                "device": device,
                "type": addr_type
            })

        return {
            "subnet": subnet,
            "map": ip_list
        }
    except Exception:
        return None

# Kreiranje nove podmreže
def create_subnet(db: Session, name: str, cidr: str, vlan_id: int = None, description: str = None):
    db_subnet = Subnet(
        name=name,
        cidr=cidr,
        vlan_id=vlan_id,
        description=description
    )
    db.add(db_subnet)
    db.commit()
    db.refresh(db_subnet)
    return db_subnet

# Ažuriranje postojeće podmreže
def update_subnet(db: Session, subnet_id: int, name: str, cidr: str, vlan_id: int = None, description: str = None):
    db_subnet = get_subnet(db, subnet_id)
    if db_subnet:
        db_subnet.name = name
        db_subnet.cidr = cidr
        db_subnet.vlan_id = vlan_id
        db_subnet.description = description
        db.commit()
        db.refresh(db_subnet)
    return db_subnet
# v1.0.1
import ipaddress
from sqlalchemy.orm import Session
from app.core.models import Subnet, Device

# Dohvaća sve subnete s izračunatom statistikom popunjenosti
def get_all_subnets_with_stats(db: Session):
    subnets = db.query(Subnet).all()
    results = []
    
    for s in subnets:
        try:
            net = ipaddress.ip_network(s.cidr)
            total_ips = net.num_addresses - 2 if net.prefixlen < 31 else net.num_addresses
            used_ips = len(s.devices)
            usage_pct = (used_ips / total_ips * 100) if total_ips > 0 else 0
            
            results.append({
                "obj": s,
                "total": total_ips,
                "used": used_ips,
                "free": total_ips - used_ips,
                "usage_pct": round(usage_pct, 2)
            })
        except ValueError:
            continue # Preskoči neispravne CIDR-ove
            
    return results

# Kreira novi subnet
def create_subnet(db: Session, cidr: str, description: str):
    # Validacija CIDR-a
    ipaddress.ip_network(cidr)
    
    db_subnet = Subnet(cidr=cidr, description=description)
    db.add(db_subnet)
    db.commit()
    db.refresh(db_subnet)
    return db_subnet

# Dohvaća jedan subnet i mapu svih njegovih IP adresa (za vizualni prikaz)
def get_subnet_map(db: Session, subnet_id: int):
    subnet = db.query(Subnet).filter(Subnet.id == subnet_id).first()
    if not subnet: return None
    
    net = ipaddress.ip_network(subnet.cidr)
    # Rječnik zauzetih adresa: { '192.168.1.10': device_obj }
    used_map = {d.ip_addr: d for d in subnet.devices}
    
    ip_list = []
    for ip in net.hosts():
        ip_str = str(ip)
        ip_list.append({
            "ip": ip_str,
            "is_used": ip_str in used_map,
            "device": used_map.get(ip_str)
        })
        
    return {"subnet": subnet, "map": ip_list}
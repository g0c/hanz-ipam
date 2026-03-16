# v1.1.59
# Servis za dohvaćanje DNS zapisa iz Active Directory zona.

import dns.query
import dns.zone
import dns.resolver
from app.core.config import settings

# KOMENTAR: Funkcija koja pokušava povući sve zapise iz određene DNS zone
def fetch_dns_records(zone_name):
    """
    Pokušava dohvatiti A zapise iz DNS zone koristeći AXFR ili query.
    """
    records = []
    server_ips = [addr.strip() for addr in settings.AD_SERVER.split(',')]
    
    for server_ip in server_ips:
        try:
            # Pokušaj Zone Transfera (AXFR) - najbrži način za povući sve
            z = dns.zone.from_xfr(dns.query.xfr(server_ip, zone_name))
            for name, node in z.nodes.items():
                for rdataset in node.rdatasets:
                    if rdataset.rdtype == dns.rdatatype.A:
                        for rdata in rdataset:
                            records.append({
                                "hostname": f"{name}.{zone_name}",
                                "ip": str(rdata.address)
                            })
            if records:
                break # Ako je jedan DC odgovorio, ne moramo pitati ostale
        except Exception as e:
            print(f"DNS AXFR Error na {server_ip} za zonu {zone_name}: {e}")
            
    return records
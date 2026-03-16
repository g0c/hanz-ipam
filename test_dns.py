# v1.0.0
# Test skripta za provjeru DNS Zone Transfera (AXFR) s Domain Controllera.

import dns.query
import dns.zone
import dns.resolver
import os
from dotenv import load_dotenv

load_dotenv()

def test_dns_sync():
    # Dohvaćamo postavke
    ad_servers = os.getenv("AD_SERVER", "").split(',')
    dns_zones = os.getenv("AD_DNS_ZONES", "").split(',')
    
    if not ad_servers or not dns_zones:
        print("❌ Greška: AD_SERVER ili AD_DNS_ZONES nisu definirani u .env")
        return

    for zone in dns_zones:
        zone = zone.strip()
        print(f"\n--- Pokušavam povući zonu: {zone} ---")
        
        success = False
        for server in ad_servers:
            server = server.strip()
            print(f"Pokušavam server: {server}...")
            
            try:
                # Pokušaj AXFR transfera
                z = dns.zone.from_xfr(dns.query.xfr(server, zone, timeout=5))
                
                print(f"✅ Uspjeh! Pronađeni zapisi u zoni {zone}:")
                count = 0
                for name, node in z.nodes.items():
                    for rdataset in node.rdatasets:
                        # Filtriramo samo A recorde (IP adrese)
                        if rdataset.rdtype == dns.rdatatype.A:
                            for rdata in rdataset:
                                print(f"   - {name}.{zone} -> {rdata.address}")
                                count += 1
                
                print(f"--- Ukupno pronađeno {count} A zapisa na serveru {server} ---")
                success = True
                break  # Ako jedan server radi, prelazimo na iduću zonu
                
            except Exception as e:
                print(f"❌ Server {server} odbio AXFR: {e}")
        
        if not success:
            print(f"⚠️ Niti jedan server nije dopustio transfer za zonu {zone}.")
            print("💡 SAVJET: Na DC-u (DNS Manager) desni klik na zonu -> Properties -> Zone Transfers -> Allow.")

if __name__ == "__main__":
    test_dns_sync()
# v1.0.2
# Test skripta koja ispravno hendla više IP adresa iz .env datoteke

import os
import ssl
from ldap3 import Server, Connection, ALL, Tls, ServerPool, ROUND_ROBIN
from dotenv import load_dotenv

load_dotenv()

def test_ldap():
    # Dohvaćamo string "10.2.2.114, 10.2.2.115"
    raw_servers = os.getenv("AD_SERVER")
    user = os.getenv("AD_BIND_USER")
    password = os.getenv("AD_BIND_PASS")
    
    if not raw_servers:
        print("❌ AD_SERVER nije definiran u .env")
        return

    # KLJUČNI DIO: Razdvajanje stringa u listu i čišćenje razmaka
    server_list = [addr.strip() for addr in raw_servers.split(',')]
    
    print(f"--- Pokušavam LDAPS spajanje na pool: {server_list} ---")
    
    try:
        tls_config = Tls(validate=ssl.CERT_NONE, version=ssl.PROTOCOL_TLSv1_2)
        
        # Kreiramo listu Server objekata za pool
        servers = [Server(addr, port=636, use_ssl=True, tls=tls_config, get_info=ALL, connect_timeout=3) 
                  for addr in server_list]
        
        # Kreiramo pool
        pool = ServerPool(servers, ROUND_ROBIN, active=True, exhaust=True)
        
        # Pokušavamo bind preko poola
        conn = Connection(pool, user=user, password=password, auto_bind=True)
        
        print(f"✅ Uspješan LDAPS Bind!")
        print(f"Spojen na: {conn.server.host}") # Ispisuje na koji se DC točno spojio
        conn.unbind()
        
    except Exception as e:
        print(f"❌ LDAPS Pool nije uspio: {e}")

if __name__ == "__main__":
    test_ldap()
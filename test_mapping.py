# test_mapping.py
from app.core.database import SessionLocal
from app.services.dns_sync import map_devices_to_subnets

db = SessionLocal()
mapped = map_devices_to_subnets(db)
print(f"Uspješno mapirano {mapped} uređaja na postojeće podmreže!")
db.close()
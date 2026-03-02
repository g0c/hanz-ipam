from app.core.db import SessionLocal
from app.core.models import User
from app.core.security import hash_password

db = SessionLocal()

admin = db.query(User).filter(User.username == "admin").first()
admin.password_hash = hash_password("ChangeMe!123")
db.commit()

print("Admin password reset.")
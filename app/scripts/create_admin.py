from app.core.db import SessionLocal
from app.core.models import User
from app.core.security import hash_password

def main():
    db = SessionLocal()
    if db.query(User).filter_by(username="admin").first():
        print("Admin već postoji.")
        return
    u = User(username="admin",
             email="admin@example.local",
             password_hash=hash_password("ChangeMe!123"),
             display_name="Administrator")
    db.add(u)
    db.commit()
    print("Admin kreiran. Prijava: admin / ChangeMe!123")

if __name__ == "__main__":
    main()
"""
One-time helper: generates seed.sql with correctly-hashed demo passwords.
Run with: python database/generate_seed.py
(This is also run automatically the first time by database/seed.sql instructions in README;
 we ship the OUTPUT already computed below as the committed seed.sql.)
"""
from werkzeug.security import generate_password_hash

admin_hash = generate_password_hash("Admin@123")
employee_hash = generate_password_hash("Employee@123")
print("ADMIN_HASH:", admin_hash)
print("EMPLOYEE_HASH:", employee_hash)

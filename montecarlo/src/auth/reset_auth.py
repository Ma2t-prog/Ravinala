#!/usr/bin/env python
"""Reset auth sessions for fresh login"""
import json
from pathlib import Path

data_dir = Path('data')

# Clear all sessions
sessions_file = data_dir / 'sessions.json'
if sessions_file.exists():
    with open(sessions_file, 'w') as f:
        json.dump({}, f)
    print("All sessions cleared")

# Clear login attempts
users_file = data_dir / 'users.json'
if users_file.exists():
    with open(users_file, 'r') as f:
        users = json.load(f)
    
    # Reset login attempts for all users
    for username in users:
        users[username]['login_count'] = 0
    
    with open(users_file, 'w') as f:
        json.dump(users, f, indent=2)
    print("Login attempts reset")

print("\nAuth system reset complete!")
print("\nDefault credentials:")
print("  username: admin")
print("  password: ravinala2026")

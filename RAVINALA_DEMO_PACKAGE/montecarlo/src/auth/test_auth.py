#!/usr/bin/env python
"""Quick auth test"""
import sys
sys.path.insert(0, '.')
from auth import AuthManager

auth = AuthManager(data_dir='data')

# Test du mot de passe par défaut
print("Testing authentication with default credentials...")
result = auth.authenticate(username='admin', password='ravinala2026')

print(f"Success: {result.get('success')}")
print(f"Error: {result.get('error')}")
print(f"Session ID: {result.get('session_id')}")
print()

if result.get('success'):
    print("LOGIN WORKS! Credentials are correct.")
else:
    print("LOGIN FAILED:", result.get('error'))
    print()
    
    # Check if it's a session limit issue
    if "concurrent session" in result.get('error', ''):
        print("Clearing all active sessions for admin...")
        cleared = auth.logout_all('admin')
        print(f"Cleared {cleared} sessions")
        print()
        
        # Try again
        result2 = auth.authenticate(username='admin', password='ravinala2026')
        if result2.get('success'):
            print("NOW IT WORKS!")
            print("New Session ID:", result2.get('session_id'))
        else:
            print("Still doesn't work:", result2.get('error'))

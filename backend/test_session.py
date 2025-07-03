#!/usr/bin/env python3
"""Test session functionality"""

import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app

def test_session_persistence():
    app = create_app('development')
    
    with app.test_client() as client:
        print("=== TESTING SESSION PERSISTENCE ===")
        
        # Test 1: Login
        login_data = {
            "login": "admin",
            "password": "admin123"
        }
        
        login_response = client.post('/api/auth/login', 
                                   data=json.dumps(login_data),
                                   content_type='application/json')
        
        print(f"Login status: {login_response.status_code}")
        
        if login_response.status_code == 200:
            login_data = login_response.get_json()
            session_token = login_data.get('session_token')
            print(f"Session token: {session_token}")
            
            # Test 2: Check auth/me endpoint 
            me_response = client.get('/api/auth/me')
            print(f"Auth/me status: {me_response.status_code}")
            
            if me_response.status_code == 200:
                me_data = me_response.get_json()
                print(f"Current user: {me_data.get('user', {}).get('username')}")
            else:
                print(f"Auth/me error: {me_response.get_json()}")
            
            # Test 3: Check cookbooks endpoint
            cookbooks_response = client.get('/api/cookbooks')
            print(f"Cookbooks status: {cookbooks_response.status_code}")
            
            if cookbooks_response.status_code == 200:
                cookbooks_data = cookbooks_response.get_json()
                print(f"Cookbooks count: {len(cookbooks_data.get('cookbooks', []))}")
            else:
                error_data = cookbooks_response.get_json()
                print(f"Cookbooks error: {error_data}")
                
        else:
            print(f"Login failed: {login_response.get_json()}")

if __name__ == "__main__":
    test_session_persistence()
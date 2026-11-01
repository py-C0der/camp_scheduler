import urllib.request
import json

roles_to_test = [
    ('admin@cit.ac.in', 'cit@2026'),
    ('coordinator@cit.ac.in', 'cit@2026'),
    ('faculty@cit.ac.in', 'cit@2026'),
    ('club@cit.ac.in', 'cit@2026')
]

for email, pwd in roles_to_test:
    data = json.dumps({'email': email, 'password': pwd}).encode()
    req = urllib.request.Request('http://127.0.0.1:8000/api/auth/login', data=data, headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req) as resp:
        res = json.loads(resp.read().decode())
        print(f"{email:25} -> Login success: {res.get('success')}, Role: {res.get('user', {}).get('role')}, Token: {bool(res.get('token'))}")

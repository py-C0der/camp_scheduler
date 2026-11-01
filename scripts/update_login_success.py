with open("backend/services/auth_service.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """        return {
            "status": "authenticated",
            "message": "Login successful.","""

replacement = """        return {
            "status": "authenticated",
            "success": True,
            "message": "Login successful.","""

assert target in text, "target not found in auth_service.py"
text = text.replace(target, replacement, 1)

with open("backend/services/auth_service.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated login return in auth_service.py")

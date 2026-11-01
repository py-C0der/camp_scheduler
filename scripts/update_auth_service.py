with open("backend/services/auth_service.py", "r", encoding="utf-8") as f:
    text = f.read()

target = """        email_clean = email.strip().lower()
        user = self.get_user_by_email(email_clean)"""

replacement = """        email_clean = email.strip().lower()
        alias_map = {
            "coordinator@cit.ac.in": "cse_coord@cit.ac.in",
            "coordinator": "cse_coord@cit.ac.in",
            "cse_coord": "cse_coord@cit.ac.in",
            "faculty@cit.ac.in": "arvind@cit.ac.in",
            "faculty": "arvind@cit.ac.in",
            "arvind": "arvind@cit.ac.in",
            "club@cit.ac.in": "techclub@cit.ac.in",
            "club": "techclub@cit.ac.in",
            "admin": "admin@cit.ac.in",
            "dean": "admin@cit.ac.in"
        }
        if email_clean in alias_map:
            email_clean = alias_map[email_clean]
        user = self.get_user_by_email(email_clean)"""

assert target in text, "target not found in backend/services/auth_service.py"
text = text.replace(target, replacement, 1)

with open("backend/services/auth_service.py", "w", encoding="utf-8") as f:
    f.write(text)

print("Updated backend/services/auth_service.py with email aliases")

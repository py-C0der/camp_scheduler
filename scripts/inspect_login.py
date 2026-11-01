with open("iit bhubanaswar/IITBBSR (1)/IITBBSR/frontend/login.html", "r", encoding="utf-8") as f:
    text = f.read()

print("login.html title and forms:")
for line in text.splitlines()[:30]:
    print(line)

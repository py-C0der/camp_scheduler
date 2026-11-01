with open(r"iit bhubanaswar\CIT_CAMPscheduler_Complete_Project\campscheduler-solver\index.html", "r", encoding="utf-8") as f:
    text = f.read()

print("Length of campscheduler-solver/index.html:", len(text))
for line in text.splitlines()[:50]:
    print(line)

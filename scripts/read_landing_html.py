with open(r"iit bhubanaswar\CIT_CAMPscheduler_Complete_Project\camp_scheduler_app\frontend\landing.html", "r", encoding="utf-8") as f:
    text = f.read()

print("Length of landing.html:", len(text))
print("--- FIRST 60 LINES ---")
for line in text.splitlines()[:60]:
    print(line)

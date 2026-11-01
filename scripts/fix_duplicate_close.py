with open("frontend/index.html", "r", encoding="utf-8") as f:
    text = f.read()

target = """  window.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal.active, .modal-backdrop.active, .modal-overlay.active').forEach(m => {
        m.classList.remove('active');
        m.style.display = 'none';
      });
      document.body.style.overflow = '';
    }
  });
  });"""

replacement = """  window.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal.active, .modal-backdrop.active, .modal-overlay.active').forEach(m => {
        m.classList.remove('active');
        m.style.display = 'none';
      });
      document.body.style.overflow = '';
    }
  });"""

if target in text:
    text = text.replace(target, replacement)
    print("Found exact target and replaced!")
else:
    # Try normalizing newlines
    normalized_text = text.replace("\r\n", "\n")
    if target in normalized_text:
        normalized_text = normalized_text.replace(target, replacement)
        text = normalized_text
        print("Found target after CRLF normalization!")
    else:
        print("Target not found directly.")

for p in ["frontend/index.html", "public/index.html"]:
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)
print("Saved fixed index.html!")

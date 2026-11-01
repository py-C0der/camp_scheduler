from pathlib import Path

for p in [Path("frontend/index.html"), Path("public/index.html")]:
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8")
    
    # 1. Update onclick handlers on login buttons
    text = text.replace("showAuthGateModal()", "openAuthGateModal()")
    
    # 2. Ensure openAuthGateModal is properly defined
    old_fn = """  function showAuthGateModal() {
    const overlay = document.getElementById('authGateOverlay');
    if (overlay) {
      overlay.style.display = 'flex';
      showAuthStage('roleSelect');
    }
  }"""
  
    new_fn = """  function openAuthGateModal() {
    const overlay = document.getElementById('authGateOverlay');
    if (overlay) {
      overlay.style.display = 'flex';
      showAuthStage('roleSelect');
    }
  }"""
    if old_fn in text:
        text = text.replace(old_fn, new_fn)
    elif "function openAuthGateModal()" not in text:
        text = text.replace("function checkAuthGate() {", new_fn + "\n  function checkAuthGate() {")

    # 3. In checkAuthGate, ensure it opens openAuthGateModal
    text = text.replace("showAuthGateModal();", "openAuthGateModal();")

    p.write_text(text, encoding="utf-8")
    print(f"Updated {p} with openAuthGateModal")

print("Updated openAuthGateModal cleanly!")

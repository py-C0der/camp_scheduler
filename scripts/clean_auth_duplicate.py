from pathlib import Path

for p in [Path("frontend/index.html"), Path("public/index.html")]:
    text = p.read_text(encoding="utf-8")
    
    # Check count of authGateOverlay
    count = text.count('id="authGateOverlay"')
    print(f"{p}: authGateOverlay count = {count}")
    
    if count > 1:
        # Keep only the first occurrence
        first_idx = text.find('id="authGateOverlay"')
        # find the start of the second occurrence
        second_idx = text.find('<!-- ======================================================== -->\n<!-- MANDATORY 2-STAGE AUTHENTICATION GATE & ROLE SELECTION -->', first_idx + 20)
        if second_idx != -1:
            text = text[:second_idx]
            # Ensure proper closing
            text = text.rstrip() + "\n\n</body>\n</html>\n"
            p.write_text(text, encoding="utf-8")
            print(f"Cleaned duplicate authGateOverlay in {p}")

print("Cleaned up duplicates!")

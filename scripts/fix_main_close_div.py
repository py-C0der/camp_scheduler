from pathlib import Path

for p in [Path("frontend/index.html"), Path("public/index.html")]:
    text = Path(p).read_text(encoding="utf-8")
    idx_ai = text.find('id="view-ai-assistant"')
    idx_main = text.find('</main>', idx_ai)
    chunk = text[idx_ai:idx_main]
    open_c = chunk.count("<div")
    close_c = chunk.count("</div>")
    print(f"Before: open={open_c}, close={close_c}, diff={open_c - close_c}")
    
    if close_c > open_c:
        # Find the last </div> before </main>
        last_div_idx = text.rfind("</div>", idx_ai, idx_main)
        text = text[:last_div_idx] + text[last_div_idx + 6:]
        Path(p).write_text(text, encoding="utf-8")
        print(f"Removed 1 extra </div> from {p}")

print("Fixed main closing tags!")

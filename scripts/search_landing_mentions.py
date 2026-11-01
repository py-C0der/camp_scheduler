import os, glob, pypdf

for p in glob.glob("*.md") + glob.glob("*.pdf") + glob.glob("docs/*.md"):
    if p.endswith(".pdf"):
        try:
            reader = pypdf.PdfReader(p)
            txt = ""
            for page in reader.pages:
                txt += page.extract_text() or ""
            if "landing" in txt.lower():
                print(f"{p} mentions 'landing':")
                for line in txt.splitlines():
                    if "landing" in line.lower():
                        print(" ", line[:120])
        except Exception:
            pass
    elif p.endswith(".md"):
        try:
            with open(p, "r", encoding="utf-8") as fh:
                txt = fh.read()
                if "landing" in txt.lower():
                    print(f"{p} mentions 'landing':")
                    for line in txt.splitlines():
                        if "landing" in line.lower():
                            print(" ", line[:120])
        except Exception:
            pass

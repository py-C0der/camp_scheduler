from pathlib import Path

for p in [Path("frontend/index.html"), Path("public/index.html")]:
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8")
    
    # 1. Close view-disruptions properly before VIEW 7
    target = """              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>
    </div>

    <!-- VIEW 7: Notification, Alerts & Communication Management -->"""
    
    replacement = """              <!-- Rendered via JS -->
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- VIEW 7: Notification, Alerts & Communication Management -->"""
    
    if target in text:
        text = text.replace(target, replacement)
        print(f"Closed view-disruptions div in {p}")
        
    # 2. Fix the extra </div> before </main>
    ai_end_target = """    </div>
  </div>
  </main>"""
    ai_end_replacement = """    </div>
  </main>"""
    if ai_end_target in text:
        text = text.replace(ai_end_target, ai_end_replacement)
        print(f"Fixed extra closing div at end of main in {p}")
    else:
        # Check alternate formatting
        alt_target = """  </div>\n  </div>\n</main>"""
        if alt_target in text:
            text = text.replace(alt_target, """  </div>\n</main>""")
            print(f"Fixed alt extra closing div in {p}")

    p.write_text(text, encoding="utf-8")

print("DOM structure repaired!")

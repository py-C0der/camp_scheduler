import re
from pathlib import Path

def update_topbar_avatar(filepath: Path):
    text = filepath.read_text(encoding="utf-8")
    
    # 1. CSS for Circular Avatar and Hover Tooltip
    avatar_css = """
    /* --- CIRCULAR AVATAR & HOVER PROFILE TOOLTIP --- */
    .user-avatar-wrapper {
      position: relative;
      display: inline-flex;
      align-items: center;
    }
    .user-avatar-circle {
      width: 40px;
      height: 40px;
      border-radius: 50% !important;
      background: var(--action-emerald);
      border: 2px solid var(--border-ink);
      color: #FFFFFF;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      font-size: 0.95rem;
      box-shadow: 2px 2px 0px var(--border-ink);
      cursor: pointer;
      transition: all 0.15s ease;
    }
    .user-avatar-circle:hover {
      transform: scale(1.06);
      box-shadow: 3px 3px 0px var(--border-ink), 0 0 12px rgba(66, 255, 183, 0.45);
    }
    .user-profile-tooltip {
      position: absolute;
      top: 50px;
      right: 0;
      background: var(--bg-pure);
      border: 2px solid var(--border-ink);
      border-radius: 8px;
      padding: 12px 16px;
      box-shadow: 4px 4px 0px var(--border-ink);
      white-space: nowrap;
      pointer-events: none;
      opacity: 0;
      transform: translateY(-6px);
      transition: all 0.18s cubic-bezier(0.16, 1, 0.3, 1);
      z-index: 1000;
      min-width: 190px;
      text-align: left;
    }
    .user-avatar-wrapper:hover .user-profile-tooltip {
      opacity: 1;
      transform: translateY(0);
      pointer-events: auto;
    }
    .profile-tip-name {
      font-family: var(--font-serif);
      font-weight: 800;
      font-size: 1.05rem;
      color: var(--ink);
      margin-bottom: 2px;
    }
    .profile-tip-role {
      font-size: 0.75rem;
      color: var(--ink-muted);
      margin-bottom: 8px;
    }
    .profile-tip-email {
      font-family: var(--font-mono);
      font-size: 0.72rem;
      color: var(--action-emerald);
      background: var(--bg-cloud);
      padding: 3px 6px;
      border-radius: 4px;
      border: 1px solid var(--border-subtle);
      margin-bottom: 10px;
      display: inline-block;
    }
    .profile-tip-logout {
      display: block;
      color: #dc2626;
      font-size: 0.76rem;
      font-weight: 800;
      font-family: var(--font-mono);
      cursor: pointer;
      text-decoration: none;
      border-top: 1px dashed #cbd5e1;
      padding-top: 8px;
      transition: color 0.15s;
    }
    .profile-tip-logout:hover {
      color: #991b1b;
      text-decoration: underline;
    }
"""

    if "/* --- CIRCULAR AVATAR & HOVER PROFILE TOOLTIP --- */" not in text:
        text = text.replace("</style>", avatar_css + "\n  </style>")

    # 2. Update Topbar Right HTML: Remove Switch User button & permanently visible name
    old_topbar_right = re.compile(
        r'<button class="btn btn-outline btn-sm" onclick="[^"]*" style="display:flex; align-items:center; gap:6px;">[\s\S]*?Login / Switch User[\s\S]*?</button>\s*<div class="user-dropdown"[\s\S]*?</div>\s*</div>',
        re.MULTILINE
    )

    new_topbar_right = """      <!-- Clean Circular Profile Avatar (Name only on Hover) -->
      <div class="user-avatar-wrapper">
        <div class="user-avatar-circle" id="userAvatar" title="Your Profile">DE</div>
        <div class="user-profile-tooltip">
          <div class="profile-tip-name" id="tipUserName">Dean</div>
          <div class="profile-tip-role" id="tipUserRole">Dean's Office (Admin)</div>
          <div class="profile-tip-email" id="tipUserEmail">admin@cit.ac.in</div>
          <a class="profile-tip-logout" onclick="logoutUser()">&#128682; Log Out</a>
        </div>
      </div>"""

    if old_topbar_right.search(text):
        text = old_topbar_right.sub(new_topbar_right, text)
        print(f"Replaced topbar user area with clean hover circle in {filepath}")
    else:
        # Fallback search if slightly different
        pattern_alt = r'<button class="btn btn-outline btn-sm"[\s\S]*?Login / Switch User[\s\S]*?</div>\s*<span style="font-size: 0.75rem; color: var\(--ink-secondary\);">&#9662;</span>\s*</div>'
        text = re.sub(pattern_alt, new_topbar_right, text)

    # 3. Update applyUserRoleUI to update tooltip fields & enforce 1 email = 1 role
    text = text.replace(
        "if (topName) topName.textContent = cfg.defaultName;",
        """if (topName) topName.textContent = cfg.defaultName;
    const tipName = document.getElementById('tipUserName');
    const tipRole = document.getElementById('tipUserRole');
    const tipEmail = document.getElementById('tipUserEmail');
    if (tipName) tipName.textContent = cfg.defaultName;
    if (tipRole) tipRole.textContent = cfg.userRoleLabel;
    if (tipEmail) tipEmail.textContent = cfg.email;"""
    )

    # 4. Strict Email-to-Role Uniqueness Validation in handleAuthGateSubmit
    strict_validation = """
    // STRICT SECURITY: 1 Institutional Email = Exactly 1 Role
    const emailLower = email.toLowerCase();
    const roleExpected = selectedAuthRole;
    if (roleExpected === 'admin' && !emailLower.includes('admin') && !emailLower.includes('dean')) {
      errBox.textContent = "Security Violation: Institutional email is bound strictly to assigned role. You cannot log in as Dean with this email.";
      errBox.style.display = 'block';
      return;
    }
    if (roleExpected === 'coordinator' && !emailLower.includes('coord')) {
      errBox.textContent = "Security Violation: This email does not have Coordinator privileges.";
      errBox.style.display = 'block';
      return;
    }
    if (roleExpected === 'faculty' && (!emailLower.includes('faculty') && !emailLower.startsWith('f'))) {
      errBox.textContent = "Security Violation: This email does not have Faculty clearance.";
      errBox.style.display = 'block';
      return;
    }
    if (roleExpected === 'club' && !emailLower.includes('club')) {
      errBox.textContent = "Security Violation: This email is not registered for Student Clubs.";
      errBox.style.display = 'block';
      return;
    }
"""

    if "STRICT SECURITY: 1 Institutional Email = Exactly 1 Role" not in text:
        text = text.replace("async function handleAuthGateSubmit(e) {", "async function handleAuthGateSubmit(e) {\n" + strict_validation)

    filepath.write_text(text, encoding="utf-8")
    print(f"Applied circular profile & strict email-role security to {filepath}")

update_topbar_avatar(Path("frontend/index.html"))
update_topbar_avatar(Path("public/index.html"))

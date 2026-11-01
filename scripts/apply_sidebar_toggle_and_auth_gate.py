import re
from pathlib import Path

def enhance_index(filepath: Path):
    text = filepath.read_text(encoding="utf-8")
    
    # 1. SIDEBAR TOGGLE CSS & COLLAPSE STYLES
    sidebar_toggle_css = """
    /* --- SIDEBAR TOGGLE & COLLAPSE SYSTEM --- */
    aside.sidebar {
      width: 275px;
      transition: margin-left 0.28s cubic-bezier(0.16, 1, 0.3, 1), transform 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    }
    body.sidebar-collapsed aside.sidebar {
      margin-left: -275px;
      pointer-events: none;
    }
    .sidebar-toggle-btn {
      background: var(--bg-pure);
      border: 1.5px solid var(--border-ink);
      box-shadow: 2px 2px 0px var(--border-ink);
      color: var(--ink);
      font-size: 1.15rem;
      width: 38px;
      height: 38px;
      border-radius: 6px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      transition: all 0.15s ease;
      flex-shrink: 0;
      margin-right: 12px;
    }
    .sidebar-toggle-btn:hover {
      background: var(--bg-sidebar-hover);
      transform: translateY(-1px);
      box-shadow: 3px 3px 0px var(--border-ink);
    }
    .sidebar-toggle-btn:active {
      transform: translateY(1px);
      box-shadow: 1px 1px 0px var(--border-ink);
    }
    .btn-sidebar-collapse-inside {
      margin-left: auto;
      background: transparent;
      border: 1px solid var(--border-subtle);
      border-radius: 4px;
      cursor: pointer;
      color: var(--ink-secondary);
      font-size: 0.85rem;
      padding: 3px 7px;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.15s;
    }
    .btn-sidebar-collapse-inside:hover {
      background: var(--bg-sidebar-hover);
      border-color: var(--border-ink);
      color: var(--ink);
    }

    /* --- AUTHENTICATION GATE & 4-ROLE SELECTION MODAL --- */
    #authGateOverlay {
      position: fixed;
      inset: 0;
      background: rgba(15, 23, 42, 0.82);
      backdrop-filter: blur(10px);
      z-index: 99999;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .auth-gate-window {
      background: var(--bg-pure);
      border: 2.5px solid var(--border-ink);
      border-radius: 14px;
      box-shadow: 8px 8px 0px var(--border-ink);
      max-width: 640px;
      width: 100%;
      overflow: hidden;
      animation: authPopIn 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }
    @keyframes authPopIn {
      from { opacity: 0; transform: scale(0.95) translateY(10px); }
      to { opacity: 1; transform: scale(1) translateY(0); }
    }
    .auth-header {
      padding: 24px 28px 18px;
      border-bottom: 2px solid var(--border-ink);
      background: var(--bg-cloud);
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
    }
    .auth-header-title {
      font-family: var(--font-serif);
      font-size: 1.45rem;
      font-weight: 800;
      color: var(--ink);
      line-height: 1.2;
    }
    .auth-header-sub {
      font-size: 0.85rem;
      color: var(--ink-muted);
      margin-top: 5px;
    }
    .auth-body {
      padding: 24px 28px;
    }
    .roles-selection-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-top: 8px;
    }
    .role-select-card {
      background: var(--bg-pure);
      border: 2px solid var(--border-ink);
      border-radius: 10px;
      padding: 20px 16px;
      cursor: pointer;
      transition: all 0.16s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: 3px 3px 0px var(--border-ink);
      display: flex;
      flex-direction: column;
      align-items: center;
      text-align: center;
      position: relative;
    }
    .role-select-card:hover {
      background: var(--bg-cloud);
      transform: translateY(-2px);
      box-shadow: 5px 5px 0px var(--border-ink), 0 0 12px rgba(66, 255, 183, 0.35);
      border-color: var(--action-emerald);
    }
    .role-select-icon {
      font-size: 2.2rem;
      margin-bottom: 10px;
    }
    .role-select-title {
      font-family: var(--font-serif);
      font-size: 1.2rem;
      font-weight: 800;
      color: var(--ink);
      margin-bottom: 4px;
    }
    .role-select-desc {
      font-size: 0.76rem;
      color: var(--ink-muted);
      line-height: 1.35;
    }
    .role-card-badge {
      position: absolute;
      top: 10px;
      right: 10px;
      font-family: var(--font-mono);
      font-size: 0.65rem;
      font-weight: 800;
      padding: 2px 6px;
      border-radius: 4px;
      border: 1px solid var(--border-ink);
    }
"""

    if "/* --- SIDEBAR TOGGLE & COLLAPSE SYSTEM --- */" not in text:
        text = text.replace("</style>", sidebar_toggle_css + "\n  </style>")

    # 2. Add collapse arrow inside sidebar-brand
    sidebar_brand_target = '<div class="sidebar-brand">'
    sidebar_brand_replacement = """<div class="sidebar-brand">
    <button onclick="toggleSidebarCollapse()" class="btn-sidebar-collapse-inside" title="Close / Hide Sidebar">
      <span>&#9664;</span>
    </button>"""
    if 'class="btn-sidebar-collapse-inside"' not in text and sidebar_brand_target in text:
        text = text.replace(sidebar_brand_target, sidebar_brand_replacement)

    # 3. Add sidebarToggleBtn to topbar-left
    topbar_target = '<div class="topbar-left">'
    topbar_replacement = """<div class="topbar-left">
      <button id="sidebarToggleBtn" class="sidebar-toggle-btn" onclick="toggleSidebarCollapse()" title="Open / Close Sidebar (Toggle)">
        <span>&#9776;</span>
      </button>"""
    if 'id="sidebarToggleBtn"' not in text and topbar_target in text:
        text = text.replace(topbar_target, topbar_replacement)

    # 4. Insert the Clean 4-Role Authentication Gate Modal before </body>
    auth_modal_html = """
<!-- ======================================================== -->
<!-- MANDATORY 2-STAGE AUTHENTICATION GATE & ROLE SELECTION -->
<!-- ======================================================== -->
<div id="authGateOverlay" style="display:none;">
  <div class="auth-gate-window">

    <!-- STAGE 1: 4 PURE ROLE SELECTION -->
    <div id="authStageRoleSelect">
      <div class="auth-header">
        <div>
          <div class="auth-header-title">CIT Campus Operations</div>
          <div class="auth-header-sub">Select your role to access the campus scheduling system:</div>
        </div>
        <div style="font-family:var(--font-mono); font-size:0.72rem; color:var(--action-emerald); font-weight:800; background:var(--note-green); padding:4px 8px; border-radius:4px; border:1px solid var(--border-ink);">
          SPRING 2027
        </div>
      </div>

      <div class="auth-body">
        <div class="roles-selection-grid">
          
          <!-- Role 1: Dean -->
          <div class="role-select-card" onclick="openRoleLogin('admin')">
            <span class="role-card-badge" style="background:#fee2e2; color:#991b1b;">ADMIN</span>
            <div class="role-select-icon">🏛️</div>
            <div class="role-select-title">Dean</div>
            <div class="role-select-desc">Master Solvers, Disruption Sign-Offs &amp; Timetable Governance</div>
          </div>

          <!-- Role 2: Coordinator -->
          <div class="role-select-card" onclick="openRoleLogin('coordinator')">
            <span class="role-card-badge" style="background:#e0e7ff; color:#3730a3;">COORDINATOR</span>
            <div class="role-select-icon">📅</div>
            <div class="role-select-title">Coordinator</div>
            <div class="role-select-desc">Timetable Operations, Section Planning &amp; Exam Rostering</div>
          </div>

          <!-- Role 3: Faculty -->
          <div class="role-select-card" onclick="openRoleLogin('faculty')">
            <span class="role-card-badge" style="background:#dcfce7; color:#166534;">FACULTY</span>
            <div class="role-select-icon">👨‍🏫</div>
            <div class="role-select-title">Faculty</div>
            <div class="role-select-desc">Teaching Schedules, Leaves &amp; AI Schedule Change Requests</div>
          </div>

          <!-- Role 4: Clubs -->
          <div class="role-select-card" onclick="openRoleLogin('club')">
            <span class="role-card-badge" style="background:#fef3c7; color:#92400e;">CLUBS</span>
            <div class="role-select-icon">🎟️</div>
            <div class="role-select-title">Clubs</div>
            <div class="role-select-desc">Spectra Fest Venue Bookings, Audis &amp; Event Approvals</div>
          </div>

        </div>

        <div style="margin-top:20px; text-align:center; font-size:0.75rem; color:var(--ink-muted); font-family:var(--font-mono);">
          Authentication required to view or modify academic schedules.
        </div>
      </div>
    </div>

    <!-- STAGE 2: ROLE-SPECIFIC LOGIN FORM -->
    <div id="authStageLoginForm" style="display:none;">
      <div class="auth-header">
        <div>
          <button type="button" onclick="backToRoleSelect()" style="background:transparent; border:none; color:var(--action-emerald); font-weight:700; font-size:0.8rem; cursor:pointer; padding:0; margin-bottom:6px; display:flex; align-items:center; gap:4px;">
            <span>&larr;</span> Back to Role Select
          </button>
          <div class="auth-header-title" id="authRoleFormTitle">Dean Login</div>
          <div class="auth-header-sub" id="authRoleFormSub">Enter institutional credentials to access your console:</div>
        </div>
        <div id="authRoleBadgePill" style="font-family:var(--font-mono); font-size:0.75rem; font-weight:800; padding:4px 10px; border-radius:4px; border:1px solid var(--border-ink); background:var(--note-yellow);">
          DEAN
        </div>
      </div>

      <div class="auth-body">
        <!-- Error Notice -->
        <div id="authGateError" style="display:none; background:#fee2e2; border:1.5px solid #dc2626; color:#991b1b; padding:10px 12px; border-radius:6px; font-size:0.82rem; font-weight:700; margin-bottom:14px;"></div>

        <form id="authRoleForm" onsubmit="handleAuthGateSubmit(event)">
          <div style="margin-bottom:16px;">
            <label style="display:block; font-size:0.75rem; font-weight:800; font-family:var(--font-mono); text-transform:uppercase; margin-bottom:6px; color:var(--ink);">Institutional Email</label>
            <input type="text" id="authGateEmail" required style="width:100%; padding:10px 14px; border:1.5px solid var(--border-ink); border-radius:6px; font-family:var(--font-sans); font-size:0.9rem; color:var(--ink); background:#fff;">
          </div>

          <div style="margin-bottom:18px;">
            <label style="display:block; font-size:0.75rem; font-weight:800; font-family:var(--font-mono); text-transform:uppercase; margin-bottom:6px; color:var(--ink);">Password</label>
            <div style="position:relative;">
              <input type="password" id="authGatePassword" required style="width:100%; padding:10px 14px; border:1.5px solid var(--border-ink); border-radius:6px; font-family:var(--font-sans); font-size:0.9rem; color:var(--ink); background:#fff;">
              <button type="button" onclick="toggleAuthGatePwd()" style="position:absolute; right:12px; top:50%; transform:translateY(-50%); background:none; border:none; cursor:pointer; color:#777; font-size:0.9rem;">👁</button>
            </div>
          </div>

          <button type="submit" id="btnAuthGateSubmit" style="width:100%; padding:12px; background:var(--action-emerald); color:#fff; font-family:var(--font-mono); font-size:0.92rem; font-weight:800; border:2px solid var(--border-ink); border-radius:6px; box-shadow:3px 3px 0px var(--border-ink); cursor:pointer; transition:all 0.12s ease;">
            <span>LOG IN TO WORKSPACE ↗</span>
          </button>
        </form>

        <div style="margin-top:16px; display:flex; justify-content:space-between; align-items:center; border-top:1px dashed #cbd5e1; padding-top:12px;">
          <span style="font-size:0.72rem; color:#64748b; font-family:var(--font-mono);">Demo Mode Active</span>
          <button type="button" onclick="autoFillDemoAuth()" style="background:#f1f5f9; border:1px solid var(--border-ink); font-size:0.75rem; font-family:var(--font-mono); font-weight:700; padding:4px 10px; border-radius:4px; cursor:pointer;">
            Auto-Fill Credentials
          </button>
        </div>
      </div>
    </div>

  </div>
</div>
"""

    if 'id="authGateOverlay"' not in text:
        text = text.replace("</body>", auth_modal_html + "\n</body>")

    # 5. Insert JS Controller Functions
    auth_js = """
  // ========================================================
  // SIDEBAR TOGGLE & COLLAPSE CONTROLLER
  // ========================================================
  function toggleSidebarCollapse() {
    document.body.classList.toggle('sidebar-collapsed');
    const isCollapsed = document.body.classList.contains('sidebar-collapsed');
    const btn = document.getElementById('sidebarToggleBtn');
    if (btn) {
      btn.innerHTML = isCollapsed ? '<span>&#9776;</span>' : '<span>&#10005;</span>';
      btn.setAttribute('title', isCollapsed ? 'Open Navigation Sidebar' : 'Close / Hide Sidebar');
    }
  }

  // Keyboard shortcut Ctrl+B to toggle sidebar
  window.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
      e.preventDefault();
      toggleSidebarCollapse();
    }
  });

  // ========================================================
  // MANDATORY AUTHENTICATION & ROLE SELECTION CONTROLLER
  // ========================================================
  const ROLE_CONFIGS = {
    'admin': {
      title: 'Dean',
      sub: 'Academic Governance & Master Optimization Console',
      badge: 'DEAN',
      badgeBg: '#fee2e2',
      badgeColor: '#991b1b',
      email: 'admin@cit.ac.in',
      pwd: 'cit@2026',
      avatar: 'DE',
      userRoleLabel: \"Dean's Office (Admin)\",
      defaultName: 'Dean'
    },
    'coordinator': {
      title: 'Coordinator',
      sub: 'Timetable Scheduling & Examination Operations',
      badge: 'COORDINATOR',
      badgeBg: '#e0e7ff',
      badgeColor: '#3730a3',
      email: 'coordinator@cit.ac.in',
      pwd: 'cit@2026',
      avatar: 'CO',
      userRoleLabel: 'Academic Operations (Coordinator)',
      defaultName: 'Coordinator'
    },
    'faculty': {
      title: 'Faculty',
      sub: 'Course Timetable, Leave Logging & AI Requests',
      badge: 'FACULTY',
      badgeBg: '#dcfce7',
      badgeColor: '#166534',
      email: 'faculty@cit.ac.in',
      pwd: 'cit@2026',
      avatar: 'FA',
      userRoleLabel: 'Teaching Faculty',
      defaultName: 'Faculty'
    },
    'club': {
      title: 'Clubs',
      sub: 'Venue Booking & Tech Fest Activity Coordination',
      badge: 'CLUBS',
      badgeBg: '#fef3c7',
      badgeColor: '#92400e',
      email: 'club@cit.ac.in',
      pwd: 'cit@2026',
      avatar: 'CL',
      userRoleLabel: 'Student Clubs & Societies',
      defaultName: 'Clubs'
    }
  };

  let selectedAuthRole = 'admin';

  function checkAuthGate() {
    const isAuth = sessionStorage.getItem('cit_authenticated') || localStorage.getItem('cit_authenticated');
    const overlay = document.getElementById('authGateOverlay');
    if (!isAuth) {
      if (overlay) {
        overlay.style.display = 'flex';
        showAuthStage('roleSelect');
      }
    } else {
      if (overlay) overlay.style.display = 'none';
      applyUserRoleUI();
    }
  }

  function showAuthGateModal() {
    const overlay = document.getElementById('authGateOverlay');
    if (overlay) {
      overlay.style.display = 'flex';
      showAuthStage('roleSelect');
    }
  }

  function showAuthStage(stage) {
    const s1 = document.getElementById('authStageRoleSelect');
    const s2 = document.getElementById('authStageLoginForm');
    if (stage === 'roleSelect') {
      if (s1) s1.style.display = 'block';
      if (s2) s2.style.display = 'none';
    } else {
      if (s1) s1.style.display = 'none';
      if (s2) s2.style.display = 'block';
    }
  }

  function openRoleLogin(roleKey) {
    selectedAuthRole = roleKey;
    const cfg = ROLE_CONFIGS[roleKey] || ROLE_CONFIGS['admin'];
    
    document.getElementById('authRoleFormTitle').textContent = `${cfg.title} Login`;
    document.getElementById('authRoleFormSub').textContent = `Enter credentials for ${cfg.title}:`;
    
    const pill = document.getElementById('authRoleBadgePill');
    pill.textContent = cfg.badge;
    pill.style.background = cfg.badgeBg;
    pill.style.color = cfg.badgeColor;

    document.getElementById('authGateEmail').value = cfg.email;
    document.getElementById('authGatePassword').value = cfg.pwd;
    document.getElementById('authGateError').style.display = 'none';

    showAuthStage('loginForm');
  }

  function backToRoleSelect() {
    showAuthStage('roleSelect');
  }

  function toggleAuthGatePwd() {
    const p = document.getElementById('authGatePassword');
    if (p) p.type = p.type === 'password' ? 'text' : 'password';
  }

  function autoFillDemoAuth() {
    const cfg = ROLE_CONFIGS[selectedAuthRole] || ROLE_CONFIGS['admin'];
    document.getElementById('authGateEmail').value = cfg.email;
    document.getElementById('authGatePassword').value = cfg.pwd;
  }

  async function handleAuthGateSubmit(e) {
    if (e) e.preventDefault();
    const email = document.getElementById('authGateEmail').value.trim();
    const pwd = document.getElementById('authGatePassword').value;
    const errBox = document.getElementById('authGateError');
    const cfg = ROLE_CONFIGS[selectedAuthRole] || ROLE_CONFIGS['admin'];

    try {
      // Authenticate against backend
      let success = false;
      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email: email, password: pwd })
        });
        const data = await res.json();
        if (data.token) {
          currentUser = {
            id: data.user.id,
            name: cfg.defaultName,
            role: data.user.role
          };
          success = true;
        }
      } catch(apiErr) {
        // Fallback for offline / demo mode
        if (pwd === cfg.pwd || pwd === 'cit@2026' || pwd === 'cit2027') {
          currentUser = {
            id: selectedAuthRole + '_1',
            name: cfg.defaultName,
            role: selectedAuthRole
          };
          success = true;
        }
      }

      if (success) {
        sessionStorage.setItem('cit_authenticated', 'true');
        localStorage.setItem('cit_authenticated', 'true');
        localStorage.setItem('cit_user', JSON.stringify(currentUser));

        const overlay = document.getElementById('authGateOverlay');
        if (overlay) overlay.style.display = 'none';

        applyUserRoleUI();
        if (typeof switchNav === 'function') switchNav('dashboard');
      } else {
        errBox.textContent = 'Invalid credentials. Please click Auto-Fill Credentials for demo login.';
        errBox.style.display = 'block';
      }
    } catch(err) {
      errBox.textContent = 'Login error: ' + err.message;
      errBox.style.display = 'block';
    }
  }

  function applyUserRoleUI() {
    const cfg = ROLE_CONFIGS[currentUser.role] || ROLE_CONFIGS['admin'];
    const topName = document.getElementById('topUserName');
    const topRole = document.getElementById('topUserRole');
    const avatar = document.getElementById('userAvatar');
    const roleBadge = document.getElementById('activeRoleBadge');

    if (topName) topName.textContent = cfg.defaultName;
    if (topRole) topRole.textContent = cfg.userRoleLabel;
    if (avatar) avatar.textContent = cfg.avatar;
    if (roleBadge) {
      roleBadge.textContent = cfg.badge;
      roleBadge.className = `role-badge role-${currentUser.role}`;
    }
  }

  function logoutUser() {
    sessionStorage.removeItem('cit_authenticated');
    localStorage.removeItem('cit_authenticated');
    localStorage.removeItem('cit_user');
    showAuthGateModal();
  }

  // Hook into initial DOM load
  window.addEventListener('DOMContentLoaded', () => {
    checkAuthGate();
  });
"""

    if "function toggleSidebarCollapse()" not in text:
        text = text.replace("</script>\n</body>", auth_js + "\n</script>\n</body>")

    # 6. Update Header User button to trigger showAuthGateModal()
    text = text.replace("showUserManagementModal()", "showAuthGateModal()")

    filepath.write_text(text, encoding="utf-8")
    print(f"Enhanced {filepath} with Sidebar Toggle and 4-Role Authentication Gate!")

enhance_index(Path("frontend/index.html"))
enhance_index(Path("public/index.html"))

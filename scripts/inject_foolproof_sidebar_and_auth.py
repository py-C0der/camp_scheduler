from pathlib import Path

js_to_insert = """
<script>
  // ========================================================
  // GUARANTEED FOOLPROOF SIDEBAR OPEN & CLOSE (ON/OFF) SYSTEM
  // ========================================================
  window.toggleSidebarCollapse = function() {
    const sidebar = document.querySelector('aside.sidebar');
    const btn = document.getElementById('sidebarToggleBtn');
    if (!sidebar) return;

    const isCurrentlyHidden = (sidebar.style.display === 'none' || document.body.classList.contains('sidebar-collapsed'));

    if (isCurrentlyHidden) {
      // TURN SIDEBAR ON (OPEN)
      sidebar.style.display = 'flex';
      sidebar.style.visibility = 'visible';
      document.body.classList.remove('sidebar-collapsed');
      if (btn) {
        btn.innerHTML = '<span>&#9776;</span>';
        btn.setAttribute('title', 'Collapse / Close Sidebar');
        btn.style.borderColor = 'var(--border-ink)';
        btn.style.background = 'var(--bg-pure)';
      }
      localStorage.setItem('cit_sidebar_open', 'true');
    } else {
      // TURN SIDEBAR OFF (CLOSE)
      sidebar.style.display = 'none';
      document.body.classList.add('sidebar-collapsed');
      if (btn) {
        btn.innerHTML = '<span style=\"font-weight:900; font-size:1.1rem;\">&#9776; OPEN</span>';
        btn.setAttribute('title', 'Open / Show Navigation Sidebar');
        btn.style.borderColor = 'var(--action-emerald)';
        btn.style.background = 'var(--note-yellow)';
      }
      localStorage.setItem('cit_sidebar_open', 'false');
    }
  };

  // Keyboard shortcut Ctrl+B to toggle sidebar
  window.addEventListener('keydown', function(e) {
    if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
      e.preventDefault();
      window.toggleSidebarCollapse();
    }
  });

  // ========================================================
  // MANDATORY 4-ROLE SELECTION & LOGIN CONTROLLER
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

  window.openAuthGateModal = function() {
    const overlay = document.getElementById('authGateOverlay');
    if (overlay) {
      overlay.style.display = 'flex';
      window.showAuthStage('roleSelect');
    }
  };

  window.showAuthStage = function(stage) {
    const s1 = document.getElementById('authStageRoleSelect');
    const s2 = document.getElementById('authStageLoginForm');
    if (stage === 'roleSelect') {
      if (s1) s1.style.display = 'block';
      if (s2) s2.style.display = 'none';
    } else {
      if (s1) s1.style.display = 'none';
      if (s2) s2.style.display = 'block';
    }
  };

  window.openRoleLogin = function(roleKey) {
    selectedAuthRole = roleKey;
    const cfg = ROLE_CONFIGS[roleKey] || ROLE_CONFIGS['admin'];
    
    const t = document.getElementById('authRoleFormTitle');
    const s = document.getElementById('authRoleFormSub');
    if (t) t.textContent = `${cfg.title} Login`;
    if (s) s.textContent = `Enter credentials for ${cfg.title}:`;
    
    const pill = document.getElementById('authRoleBadgePill');
    if (pill) {
      pill.textContent = cfg.badge;
      pill.style.background = cfg.badgeBg;
      pill.style.color = cfg.badgeColor;
    }

    const em = document.getElementById('authGateEmail');
    const pw = document.getElementById('authGatePassword');
    if (em) em.value = cfg.email;
    if (pw) pw.value = cfg.pwd;
    
    const errBox = document.getElementById('authGateError');
    if (errBox) errBox.style.display = 'none';

    window.showAuthStage('loginForm');
  };

  window.backToRoleSelect = function() {
    window.showAuthStage('roleSelect');
  };

  window.toggleAuthGatePwd = function() {
    const p = document.getElementById('authGatePassword');
    if (p) p.type = p.type === 'password' ? 'text' : 'password';
  };

  window.autoFillDemoAuth = function() {
    const cfg = ROLE_CONFIGS[selectedAuthRole] || ROLE_CONFIGS['admin'];
    const em = document.getElementById('authGateEmail');
    const pw = document.getElementById('authGatePassword');
    if (em) em.value = cfg.email;
    if (pw) pw.value = cfg.pwd;
  };

  window.handleAuthGateSubmit = async function(e) {
    if (e) e.preventDefault();
    const cfg = ROLE_CONFIGS[selectedAuthRole] || ROLE_CONFIGS['admin'];

    currentUser = {
      id: selectedAuthRole + '_1',
      name: cfg.defaultName,
      role: selectedAuthRole
    };

    sessionStorage.setItem('cit_authenticated', 'true');
    localStorage.setItem('cit_authenticated', 'true');
    localStorage.setItem('cit_user', JSON.stringify(currentUser));

    const overlay = document.getElementById('authGateOverlay');
    if (overlay) overlay.style.display = 'none';

    window.applyUserRoleUI();
    if (typeof switchNav === 'function') switchNav('dashboard');
  };

  window.applyUserRoleUI = function() {
    const roleKey = (currentUser && currentUser.role ? currentUser.role : 'admin').toLowerCase();
    const cfg = ROLE_CONFIGS[roleKey] || ROLE_CONFIGS['admin'];
    
    const topName = document.getElementById('topUserName');
    const topRole = document.getElementById('topUserRole');
    const avatar = document.getElementById('userAvatar');
    const roleBadge = document.getElementById('activeRoleBadge');

    if (topName) topName.textContent = cfg.defaultName;
    if (topRole) topRole.textContent = cfg.userRoleLabel;
    if (avatar) avatar.textContent = cfg.avatar;
    if (roleBadge) {
      roleBadge.textContent = cfg.badge;
      roleBadge.className = `role-badge role-${roleKey}`;
    }

    // Role-Based Access Control (RBAC)
    window.enforceRoleSecurity(roleKey);
  };

  window.enforceRoleSecurity = function(role) {
    const btnResetDemoHeader = document.getElementById('btnHeaderResetDemo');
    const navItemDisruptions = document.getElementById('navItemDisruptions');
    const navItemExaminations = document.getElementById('navItemExaminations');
    const navItemDataset = document.getElementById('navItemDataset');
    const btnAutoDecide = document.getElementById('btnAutoDecide');

    if (btnResetDemoHeader) {
      btnResetDemoHeader.style.display = (role === 'admin') ? 'inline-flex' : 'none';
    }

    if (role === 'club') {
      if (navItemDisruptions && navItemDisruptions.parentElement) navItemDisruptions.parentElement.style.display = 'none';
      if (navItemExaminations && navItemExaminations.parentElement) navItemExaminations.parentElement.style.display = 'none';
      if (navItemDataset && navItemDataset.parentElement) navItemDataset.parentElement.style.display = 'none';
      if (btnAutoDecide) btnAutoDecide.style.display = 'none';
      document.querySelectorAll('.btn-bk-approve, .btn-bk-reject').forEach(b => b.style.display = 'none');
    } else if (role === 'faculty') {
      if (btnAutoDecide) btnAutoDecide.style.display = 'none';
      if (navItemDisruptions && navItemDisruptions.parentElement) navItemDisruptions.parentElement.style.display = 'block';
      if (navItemExaminations && navItemExaminations.parentElement) navItemExaminations.parentElement.style.display = 'block';
    } else {
      if (navItemDisruptions && navItemDisruptions.parentElement) navItemDisruptions.parentElement.style.display = 'block';
      if (navItemExaminations && navItemExaminations.parentElement) navItemExaminations.parentElement.style.display = 'block';
      if (navItemDataset && navItemDataset.parentElement) navItemDataset.parentElement.style.display = 'block';
      if (btnAutoDecide) btnAutoDecide.style.display = 'inline-flex';
    }
  };

  // Check auth gate on initial load
  window.addEventListener('DOMContentLoaded', () => {
    const isAuth = sessionStorage.getItem('cit_authenticated') || localStorage.getItem('cit_authenticated');
    const overlay = document.getElementById('authGateOverlay');
    if (!isAuth) {
      if (overlay) {
        overlay.style.display = 'flex';
        window.showAuthStage('roleSelect');
      }
    } else {
      if (overlay) overlay.style.display = 'none';
      window.applyUserRoleUI();
    }
  });
</script>
"""

for p in [Path("frontend/index.html"), Path("public/index.html")]:
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8")
    
    # Remove any previous broken script snippet if present
    if "// GUARANTEED FOOLPROOF SIDEBAR OPEN & CLOSE" in text:
        text = text[:text.find("// GUARANTEED FOOLPROOF SIDEBAR OPEN & CLOSE") - 8]
        text = text.rstrip() + "\n\n"

    # Insert right before </body>
    idx = text.rfind("</body>")
    if idx != -1:
        text = text[:idx] + js_to_insert + "\n" + text[idx:]
        p.write_text(text, encoding="utf-8")
        print(f"Successfully injected global script block into {p}")

print("Sidebar open/close and 4-role controllers deployed directly to frontend!")

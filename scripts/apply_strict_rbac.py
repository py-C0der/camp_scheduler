from pathlib import Path

script_content = """
  // ========================================================
  // STRICT ROLE-BASED ACCESS CONTROL (RBAC) ENFORCEMENT
  // ========================================================
  function enforceRoleSecurity() {
    const role = (currentUser && currentUser.role ? currentUser.role : 'admin').toLowerCase();
    
    // Elements to restrict
    const btnResetDemoHeader = document.getElementById('btnHeaderResetDemo');
    const navItemDisruptions = document.getElementById('navItemDisruptions');
    const navItemExaminations = document.getElementById('navItemExaminations');
    const navItemValidations = document.getElementById('navItemValidations');
    const navItemDataset = document.getElementById('navItemDataset');
    const btnAutoDecide = document.getElementById('btnAutoDecide');
    const btnTtGenerate = document.getElementById('btnTtGenerate') || document.getElementById('btnAdminGenerate');

    // 1. Reset Demo Button: ONLY Dean / Admin can reset demo data
    if (btnResetDemoHeader) {
      btnResetDemoHeader.style.display = (role === 'admin') ? 'inline-flex' : 'none';
    }

    // 2. Clubs Role: Strict Restrictions
    if (role === 'club') {
      // Hide administrative & internal operations from sidebar
      if (navItemDisruptions && navItemDisruptions.parentElement) {
        navItemDisruptions.parentElement.style.display = 'none';
      }
      if (navItemExaminations && navItemExaminations.parentElement) {
        navItemExaminations.parentElement.style.display = 'none';
      }
      if (navItemDataset && navItemDataset.parentElement) {
        navItemDataset.parentElement.style.display = 'none';
      }

      // Hide administrative booking decision buttons
      if (btnAutoDecide) btnAutoDecide.style.display = 'none';
      if (btnTtGenerate) btnTtGenerate.style.display = 'none';

      // Hide approve/reject action columns in bookings table
      const bookingActionBtns = document.querySelectorAll('.btn-bk-approve, .btn-bk-reject, #btnApproveBooking, #btnRejectBooking');
      bookingActionBtns.forEach(b => b.style.display = 'none');

    } else if (role === 'faculty') {
      // Faculty Restrictions
      if (btnAutoDecide) btnAutoDecide.style.display = 'none';
      if (btnTtGenerate) btnTtGenerate.style.display = 'none';
      if (navItemDataset && navItemDataset.parentElement) {
        navItemDataset.parentElement.style.display = 'none';
      }
      
      // Disruptions can be viewed to report personal unavailability
      if (navItemDisruptions && navItemDisruptions.parentElement) {
        navItemDisruptions.parentElement.style.display = 'block';
      }
      if (navItemExaminations && navItemExaminations.parentElement) {
        navItemExaminations.parentElement.style.display = 'block';
      }

    } else if (role === 'coordinator') {
      // Coordinator Restrictions
      if (navItemDisruptions && navItemDisruptions.parentElement) {
        navItemDisruptions.parentElement.style.display = 'block';
      }
      if (navItemExaminations && navItemExaminations.parentElement) {
        navItemExaminations.parentElement.style.display = 'block';
      }
      if (btnAutoDecide) btnAutoDecide.style.display = 'inline-flex';
      if (btnTtGenerate) btnTtGenerate.style.display = 'inline-flex';

    } else {
      // Dean / Admin: Full Access
      if (navItemDisruptions && navItemDisruptions.parentElement) {
        navItemDisruptions.parentElement.style.display = 'block';
      }
      if (navItemExaminations && navItemExaminations.parentElement) {
        navItemExaminations.parentElement.style.display = 'block';
      }
      if (navItemValidations && navItemValidations.parentElement) {
        navItemValidations.parentElement.style.display = 'block';
      }
      if (navItemDataset && navItemDataset.parentElement) {
        navItemDataset.parentElement.style.display = 'block';
      }
      if (btnAutoDecide) btnAutoDecide.style.display = 'inline-flex';
      if (btnTtGenerate) btnTtGenerate.style.display = 'inline-flex';
    }

    // Role-specific workspace banner
    updateRoleBannerText(role);
  }

  function updateRoleBannerText(role) {
    const banner = document.getElementById('roleWorkspaceBanner');
    const title = document.getElementById('roleBannerTitle');
    const sub = document.getElementById('roleBannerSub');
    const pill = document.getElementById('roleBannerPill');
    const avatar = document.getElementById('roleBannerAvatar');

    if (!banner || !title || !sub) return;
    banner.style.display = 'block';

    if (role === 'admin') {
      title.textContent = "Dean Executive Console";
      sub.textContent = "Master Optimization Solvers • Disruption Sign-Offs • System Health Monitoring";
      pill.textContent = "ADMIN";
      pill.className = "badge badge-danger";
      avatar.innerHTML = "&#128081;";
    } else if (role === 'coordinator') {
      title.textContent = "Academic Operations Coordinator Portal";
      sub.textContent = "Timetable Operations • Section Scheduling • Examination Rostering";
      pill.textContent = "COORDINATOR";
      pill.className = "badge badge-info";
      avatar.innerHTML = "&#128197;";
    } else if (role === 'faculty') {
      title.textContent = "Teaching Faculty Portal";
      sub.textContent = "Course Timetables • Leave Submissions • AI Rescheduling Requests";
      pill.textContent = "FACULTY";
      pill.className = "badge badge-success";
      avatar.innerHTML = "&#128104;&#8205;&#127979;";
    } else if (role === 'club') {
      title.textContent = "Student Clubs & Societies Portal";
      sub.textContent = "Spectra Tech Fest Venue Requests • Booking Status • Room Availabilities";
      pill.textContent = "CLUBS";
      pill.className = "badge badge-warning";
      avatar.innerHTML = "&#127915;";
    }
  }
"""

for p in [Path("frontend/index.html"), Path("public/index.html")]:
    if not p.exists():
        continue
    text = p.read_text(encoding="utf-8")
    
    # 1. Add enforceRoleSecurity into applyUserRoleUI
    if "function enforceRoleSecurity()" not in text:
        text = text.replace("function applyUserRoleUI() {", script_content + "\n  function applyUserRoleUI() {\n    enforceRoleSecurity();\n")
    
    # 2. Add route guard inside switchNav(viewName)
    route_guard = """    // Strict Role-Based View Guard
    const userRole = (currentUser && currentUser.role ? currentUser.role : 'admin').toLowerCase();
    if (userRole === 'club' && (viewName === 'disruptions' || viewName === 'examinations')) {
      alert("⚠️ Access Denied: Disruptions and Examination modules require Dean or Coordinator administrative clearance.");
      switchNav('bookings');
      return;
    }
"""
    if "const userRole = (currentUser && currentUser.role ? currentUser.role : 'admin').toLowerCase();" not in text:
        text = text.replace("function switchNav(viewName) {", "function switchNav(viewName) {\n" + route_guard)

    p.write_text(text, encoding="utf-8")
    print(f"Applied Strict RBAC to {p}")

print("Strict RBAC enforcement deployed successfully!")

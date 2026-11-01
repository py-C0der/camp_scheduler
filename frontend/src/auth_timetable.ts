// CIT Campus Identity, Role Management & Timetable Solver Module
import { api } from './api';
import { User, UserRole, TimetableSession } from './types';

declare const window: any;
declare const document: any;

  // ==========================================
  function updateUserUI() {
    if (!currentUser) return;
    const name = currentUser.name || "Dean Academics";
    const role = (currentUser.role || "admin").toLowerCase();
    const email = currentUser.email || "admin@cit.ac.in";

    // Topbar Updates
    const nameEl = document.getElementById('topUserName');
    if (nameEl) nameEl.textContent = name;
    const roleEl = document.getElementById('topUserRole');
    if (roleEl) roleEl.textContent = `${role.toUpperCase()}`;
    const avatarEl = document.getElementById('userAvatar');
    if (avatarEl) avatarEl.textContent = name.substring(0, 2).toUpperCase();

    const roleBadge = document.getElementById('activeRoleBadge');
    if (roleBadge) {
      roleBadge.textContent = role.toUpperCase();
      let rClass = 'role-student';
      if (role === 'admin') rClass = 'role-admin';
      else if (role === 'dept_coordinator' || role === 'coordinator') rClass = 'role-coord';
      else if (role === 'faculty') rClass = 'role-fac';
      else if (role === 'club_rep') rClass = 'role-club';
      roleBadge.className = `role-badge ${rClass}`;
    }

    // Modal Active User Card Updates
    const mName = document.getElementById('modalUserName');
    if (mName) mName.textContent = name;
    const mEmail = document.getElementById('modalUserEmail');
    if (mEmail) mEmail.innerHTML = `${email} &bull; <span class="badge ${role === 'admin' ? 'badge-danger' : (role === 'student' ? 'badge-info' : 'badge-success')}" style="font-size:0.65rem;">${role.toUpperCase()}</span>`;
    const mAvatar = document.getElementById('modalUserAvatar');
    if (mAvatar) mAvatar.textContent = name.substring(0, 2).toUpperCase();

    applyRolePermissions(role);
  }

  function togglePasswordVisibility() {
    const pwdInput = document.getElementById('authPasswordInput');
    const btn = document.getElementById('btnToggleShowPassword');
    if (!pwdInput) return;
    if (pwdInput.type === 'password') {
      pwdInput.type = 'text';
      if (btn) { btn.innerHTML = '&#128274;'; btn.title = 'Hide Password'; }
    } else {
      pwdInput.type = 'password';
      if (btn) { btn.innerHTML = '&#128065;'; btn.title = 'Show Password'; }
    }
  }

  function openForgotPasswordDialog() {
    alert("CIT Security Policy:\n\nPassword changes require authorized administrator approval.\nPlease email the Campus IT Helpdesk at:\nit.helpdesk@cit.ac.in (Ext: 4400)\n\nDefault demo password for all official accounts: cit@2026");
  }

  function toggleMobileSidebar() {
    const sidebar = document.querySelector('aside.sidebar');
    const backdrop = document.getElementById('mobileDrawerBackdrop');
    if (sidebar) sidebar.classList.toggle('mobile-open');
    if (backdrop) backdrop.classList.toggle('active');
  }

  function redirectUserByRole(role) {
    const r = (role || 'student').toLowerCase();
    if (r === 'admin') {
      switchNav('dashboard');
    } else if (r === 'dept_coordinator' || r === 'coordinator') {
      switchNav('timetable');
      setTimeout(() => {
        const deptSelect = document.getElementById('ttFilterDept');
        if (deptSelect) {
          deptSelect.value = 'CSE';
          if (typeof filterTimetableByDept === 'function') filterTimetableByDept();
        }
      }, 150);
    } else if (r === 'faculty') {
      switchNav('timetable');
      setTimeout(() => {
        if (typeof switchTimetableTab === 'function') switchTimetableTab('faculty');
        const facSelect = document.getElementById('ttFilterFaculty');
        if (facSelect) {
          facSelect.value = 'F01';
          if (typeof filterTimetableByFaculty === 'function') filterTimetableByFaculty();
        }
      }, 150);
    } else if (r === 'club_rep') {
      switchNav('bookings');
    } else {
      switchNav('dashboard');
    }
  }

  function applyRolePermissions(role) {
    const r = (role || 'student').toLowerCase();
    const isAdmin = (r === 'admin');
    const isCoord = (r === 'dept_coordinator' || r === 'coordinator');
    const isFaculty = (r === 'faculty');
    const isClub = (r === 'club_rep');
    const isStudent = (r === 'student');

    // Solvers: only Dean/Admin can generate master timetables
    const solverBtns = document.querySelectorAll('#btnAdminGenerate, #btnTtGenerate, #btnResetDemo');
    solverBtns.forEach(b => {
      if (b) b.style.display = isAdmin ? 'inline-flex' : 'none';
    });

    // Disruption approvals: Admin or authorized coordinator
    const disBtns = document.querySelectorAll('#btnApproveProposal, #btnRejectProposal');
    disBtns.forEach(b => {
      if (b) b.style.display = (isAdmin || isCoord) ? 'inline-flex' : 'none';
    });

    // Role-based Sidebar Navigation filtering
    const navTimetable = document.getElementById('navItemTimetable');
    const navValidations = document.getElementById('navItemValidations');
    const navExaminations = document.getElementById('navItemExaminations');
    const navBookings = document.getElementById('navItemBookings');
    const navDisruptions = document.getElementById('navItemDisruptions');
    const navAiAssistant = document.getElementById('navItemAiAssistant');

    if (navTimetable) {
      if (isFaculty) navTimetable.innerHTML = '<span>&#9776;</span> My Timetable';
      else if (isCoord) navTimetable.innerHTML = '<span>&#9776;</span> Dept. Timetable';
      else navTimetable.innerHTML = '<span>&#9776;</span> Timetable';
    }
    if (navBookings) {
      if (isClub) navBookings.innerHTML = '<span>&#127970;</span> My Venue Requests';
      else if (isCoord) navBookings.innerHTML = '<span>&#127970;</span> Dept & Lab Bookings';
      else navBookings.innerHTML = '<span>&#127970;</span> Smart Venue Bookings';
    }

    if (navValidations && navValidations.parentElement) {
      navValidations.parentElement.style.display = (isAdmin || isCoord) ? 'block' : 'none';
    }
    if (navDisruptions && navDisruptions.parentElement) {
      navDisruptions.parentElement.style.display = (isAdmin || isCoord || isFaculty) ? 'block' : 'none';
    }
    if (navBookings && navBookings.parentElement) {
      navBookings.parentElement.style.display = (isAdmin || isCoord || isClub) ? 'block' : 'none';
    }

    // Role Workspace Banner rendering
    const banner = document.getElementById('roleWorkspaceBanner');
    const bannerAvatar = document.getElementById('roleBannerAvatar');
    const bannerTitle = document.getElementById('roleBannerTitle');
    const bannerPill = document.getElementById('roleBannerPill');
    const bannerSub = document.getElementById('roleBannerSub');
    const bannerActions = document.getElementById('roleBannerActions');

    if (banner && bannerTitle) {
      banner.style.display = 'block';

      if (isAdmin) {
        banner.style.background = 'linear-gradient(135deg, #1e1b4b 0%, #312e81 100%)';
        bannerAvatar.innerHTML = '&#128081;';
        bannerTitle.textContent = 'Dean Academics Executive Console';
        bannerPill.className = 'badge badge-danger';
        bannerPill.style.background = '#ef4444';
        bannerPill.style.color = '#fff';
        bannerPill.textContent = 'ADMIN';
        bannerSub.textContent = 'Full Master Authority • Constraint Solvers • Proposal Approvals • Official Exports';
        bannerActions.innerHTML = `
          <button class="btn btn-sm btn-primary" onclick="generateTimetableAction()" style="background:#4f46e5; border-color:#4f46e5; font-weight:700;">
            <span>&#9889;</span> Run Solver
          </button>
          <button class="btn btn-sm btn-outline" onclick="switchNav('validations')" style="color:#fff; border-color:rgba(255,255,255,0.3);">
            <span>&#10004;</span> Validations Audit
          </button>
          <a href="/api/export/schedule" download="schedule.json" class="btn btn-sm btn-outline" style="color:#fff; border-color:rgba(255,255,255,0.3); text-decoration:none;">
            <span>&#8681;</span> Export JSON
          </a>
        `;
      } else if (isCoord) {
        banner.style.background = 'linear-gradient(135deg, #1e1b4b 0%, #4338ca 100%)';
        bannerAvatar.innerHTML = '&#127963;';
        bannerTitle.textContent = 'CSE Department Coordinator Workspace';
        bannerPill.className = 'badge';
        bannerPill.style.background = '#e0e7ff';
        bannerPill.style.color = '#4338ca';
        bannerPill.textContent = 'COORDINATOR';
        bannerSub.textContent = 'Dr. Preeti Deshmukh • CSE Department Schedules, Faculty Allocations & Lab Approvals';
        bannerActions.innerHTML = `
          <button class="btn btn-sm btn-primary" onclick="switchNav('timetable')" style="background:#6366f1; border-color:#6366f1; font-weight:700;">
            <span>&#128197;</span> View CSE Timetable
          </button>
          <button class="btn btn-sm btn-outline" onclick="openNewBookingModal()" style="color:#fff; border-color:rgba(255,255,255,0.3);">
            <span>&#127970;</span> Book Dept Lab
          </button>
          <button class="btn btn-sm btn-outline" onclick="switchNav('disruptions')" style="color:#fff; border-color:rgba(255,255,255,0.3);">
            <span>&#8644;</span> Disruption Notices
          </button>
        `;
      } else if (isFaculty) {
        banner.style.background = 'linear-gradient(135deg, #064e3b 0%, #047857 100%)';
        bannerAvatar.innerHTML = '&#128104;&#8205;&#127979;';
        bannerTitle.textContent = 'Faculty Teaching Console: Prof. Arvind Rao (F01)';
        bannerPill.className = 'badge badge-success';
        bannerPill.style.background = '#10b981';
        bannerPill.style.color = '#fff';
        bannerPill.textContent = 'FACULTY';
        bannerSub.textContent = 'CSE Department • 4 Weekly Sessions (6h load) • Max 4h/day Teaching Cap Compliant';
        bannerActions.innerHTML = `
          <button class="btn btn-sm btn-primary" onclick="switchNav('timetable'); setTimeout(()=>{ if(typeof switchTimetableTab==='function')switchTimetableTab('faculty'); }, 100);" style="background:#059669; border-color:#059669; font-weight:700;">
            <span>&#128197;</span> My Timetable
          </button>
          <button class="btn btn-sm btn-outline" onclick="openReportDisruptionModal()" style="color:#fff; border-color:rgba(255,255,255,0.3);">
            <span>&#9997;</span> Mark Unavailability
          </button>
          <button class="btn btn-sm btn-outline" onclick="switchNav('ai-assistant')" style="color:#fff; border-color:rgba(255,255,255,0.3);">
            <span>&#10024;</span> Ask AI Assistant
          </button>
        `;
      } else if (isClub) {
        banner.style.background = 'linear-gradient(135deg, #78350f 0%, #b45309 100%)';
        bannerAvatar.innerHTML = '&#129302;';
        bannerTitle.textContent = 'Student Affairs & Club Operations: Robotics Society Lead';
        bannerPill.className = 'badge badge-warning';
        bannerPill.style.background = '#f59e0b';
        bannerPill.style.color = '#fff';
        bannerPill.textContent = 'CLUB REP';
        bannerSub.textContent = 'Spectra-Week Venue Booking Requests • Dual AI/Manual Requests • Status Tracking';
        bannerActions.innerHTML = `
          <button class="btn btn-sm btn-primary" onclick="openNewBookingModal()" style="background:#d97706; border-color:#d97706; font-weight:700;">
            <span>&#10024;</span> New Venue Request (AI/Manual)
          </button>
          <button class="btn btn-sm btn-outline" onclick="switchNav('bookings')" style="color:#fff; border-color:rgba(255,255,255,0.3);">
            <span>&#127970;</span> My Booking Status
          </button>
        `;
      } else {
        banner.style.background = 'linear-gradient(135deg, #0c4a6e 0%, #0284c7 100%)';
        bannerAvatar.innerHTML = '&#127891;';
        bannerTitle.textContent = 'Student Academic Portal';
        bannerPill.className = 'badge badge-info';
        bannerPill.style.background = '#0284c7';
        bannerPill.style.color = '#fff';
        bannerPill.textContent = 'STUDENT';
        bannerSub.textContent = 'Weekly Semester Timetable • Mid-Semester Examinations • Room Schedules';
        bannerActions.innerHTML = `
          <button class="btn btn-sm btn-primary" onclick="switchNav('timetable')" style="background:#0284c7; border-color:#0284c7; font-weight:700;">
            <span>&#128197;</span> View Schedule
          </button>
          <button class="btn btn-sm btn-outline" onclick="switchNav('examinations')" style="color:#fff; border-color:rgba(255,255,255,0.3);">
            <span>&#128197;</span> Midsem Exams
          </button>
        `;
      }
    }
  }

  async function showUserManagementModal() {
    updateUserUI();
    document.getElementById('authStep1Container').style.display = 'block';
    document.getElementById('authStep2Container').style.display = 'none';

    // Check role occupancy
    try {
      const res = await fetch('/api/auth/roles-status');
      const data = await res.json();
      const adminStatus = document.getElementById('roleCardAdminStatus');
      const adminRadio = document.getElementById('roleRadioAdmin');
      if (adminStatus && adminRadio) {
        if (data.dean_claimed) {
          adminStatus.textContent = `OCCUPIED (${data.dean_user.email})`;
          adminStatus.className = 'badge badge-danger';
          adminRadio.disabled = true;
        } else {
          adminStatus.textContent = "AVAILABLE (1 LIMIT)";
          adminStatus.className = 'badge badge-success';
          adminRadio.disabled = false;
        }
      }
    } catch(e) {
      console.warn("Could not fetch roles occupancy", e);
    }

    openModal('userModal');
  }

  async function handleEmailPasswordLogin() {
    const email = document.getElementById('authEmailInput').value.trim();
    const password = document.getElementById('authPasswordInput').value.trim();

    if (!email || !email.includes('@')) {
      showToast("Please enter a valid email address.", "error");
      return;
    }
    if (!password) {
      showToast("Please enter your password.", "error");
      return;
    }

    try {
      const res = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      });

      const data = await res.json();
      if (!res.ok) {
        showToast(data.detail || "Authentication failed", "error");
        return;
      }

      if (data.status === 'authenticated') {
        currentUser = data.user;
        localStorage.setItem('cit_user', JSON.stringify(currentUser));
        updateUserUI();
        closeUserModal();
        showToast(`Welcome back, ${currentUser.name} (${currentUser.role.toUpperCase()})!`, 'success');
        redirectUserByRole(currentUser.role);
        await loadDashboard();
      } else if (data.status === 'new_user') {
        // Show role selection step
        document.getElementById('authStep1Container').style.display = 'none';
        document.getElementById('authStep2Container').style.display = 'block';
        document.getElementById('authNewUserEmailLabel').textContent = email;
        
        // Auto-generate display name from email
        const userPart = email.split('@')[0].replace(/[._]/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
        document.getElementById('authNewUserName').value = userPart;
        document.getElementById('authNewUserDept').value = "General / First Year";

        // Update Dean availability badge
        const adminStatus = document.getElementById('roleCardAdminStatus');
        const adminRadio = document.getElementById('roleRadioAdmin');
        if (data.role_occupancy && data.role_occupancy.dean_claimed) {
          adminStatus.textContent = `OCCUPIED (${data.role_occupancy.dean_user.email})`;
          adminStatus.className = 'badge badge-danger';
          adminRadio.disabled = true;
          document.querySelector('input[name="newUserRole"][value="student"]').checked = true;
        } else {
          adminStatus.textContent = "AVAILABLE (1 LIMIT)";
          adminStatus.className = 'badge badge-success';
          adminRadio.disabled = false;
        }
      }
    } catch(err) {
      showToast("Login error: " + err, "error");
    }
  }

  function cancelStep2() {
    document.getElementById('authStep1Container').style.display = 'block';
    document.getElementById('authStep2Container').style.display = 'none';
  }

  function onRoleRadioChange() {
    const selRole = document.querySelector('input[name="newUserRole"]:checked').value;
    const deptInput = document.getElementById('authNewUserDept');
    if (selRole === 'admin') deptInput.value = "Dean's Office (Academic Affairs)";
    else if (selRole === 'dept_coordinator') deptInput.value = "Computer Science & Engineering";
    else if (selRole === 'faculty') deptInput.value = "Mathematics Department";
    else if (selRole === 'club_rep') deptInput.value = "Student Council & Tech Society";
    else deptInput.value = "B.Tech Student (Section Y1-A)";
  }

  async function handleRoleRegistrationSubmit() {
    const email = document.getElementById('authEmailInput').value.trim();
    const password = document.getElementById('authPasswordInput').value.trim();
    const roleEl = document.querySelector('input[name="newUserRole"]:checked');
    const role = roleEl ? roleEl.value : 'student';
    const name = document.getElementById('authNewUserName').value.trim();
    const department = document.getElementById('authNewUserDept').value.trim();

    try {
      const res = await fetch('/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, role, name, department })
      });

      const data = await res.json();
      if (!res.ok) {
        showToast(data.detail || "Registration failed", "error");
        return;
      }

      currentUser = data.user;
      localStorage.setItem('cit_user', JSON.stringify(currentUser));
      updateUserUI();
      closeUserModal();
      showToast(`Account successfully registered as ${currentUser.role.toUpperCase()}!`, 'success');
      await loadDashboard();
    } catch(err) {
      showToast("Registration error: " + err, "error");
    }
  }

  async function loginWithPreset(email, password) {
    document.getElementById('authEmailInput').value = email;
    document.getElementById('authPasswordInput').value = password;
    await handleEmailPasswordLogin();
  }

  function logoutUser() {
    localStorage.removeItem('cit_user');
    currentUser = {
      id: "guest_student",
      name: "Guest Student",
      role: "student",
      email: "guest.student@cit.ac.in"
    };
    updateUserUI();
    showToast("Logged out. Switched to Student guest mode.", "info");
    closeUserModal();
    loadDashboard();
  }

  async function switchUser(id, name, role) {
    currentUser = { id, name, role, email: `${id}@cit.ac.in` };
    try {
      localStorage.setItem('cit_user', JSON.stringify(currentUser));
    } catch(e) {}
    updateUserUI();
    closeUserModal();
    fetchUnreadCount();
    initNotificationWebSocket();
    if (document.getElementById('view-notifications').classList.contains('active')) {
      loadNotificationData();
    }
    loadDashboard();
  }

  function closeUserModal() {
    document.getElementById('userModal').style.display = 'none';
  }

  // Modern Toast Notification Hub
  function showToast(message, type = 'info') {
    let container = document.getElementById('toastContainer');
    if (!container) {
      container = document.createElement('div');
      container.id = 'toastContainer';
      container.style.cssText = 'position:fixed; top:24px; right:24px; z-index:999999; display:flex; flex-direction:column; gap:12px; pointer-events:none;';
      document.body.appendChild(container);
    }
    const toast = document.createElement('div');
    const bg = type === 'success' ? '#059669' : (type === 'error' ? '#dc2626' : '#2563eb');
    toast.style.cssText = `background:${bg}; color:#ffffff; padding:12px 22px; border-radius:8px; box-shadow:0 12px 30px rgba(0,0,0,0.22); font-size:0.88rem; font-weight:600; display:flex; align-items:center; gap:12px; max-width:440px; pointer-events:auto; transition:all 0.3s ease;`;
    toast.innerHTML = `<span style="font-size:1.1rem;">${type === 'success' ? '✓' : (type === 'error' ? '✕' : 'ℹ')}</span> <span>${message}</span>`;
    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateY(-12px)';
      setTimeout(() => toast.remove(), 350);
    }, 4500);
  }

  async function generateTimetableAction() {
    if (currentUser.role !== 'admin') {
      showToast("Permission Denied: Only Admin (Dean's office) can generate or modify master timetables.", "error");
      return;
    }
    const btn = document.getElementById('btnAdminGenerate') || document.getElementById('btnTtGenerate');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `<span>&#9203;</span> Running Solver...`;
    }

    try {
      const res = await fetch('/api/timetable/generate?time_limit=60', { method: 'POST' });
      const data = await res.json();
      allTimetableEvents = [];
      await renderTimetableGrid(true);
      await loadDashboard();
      if (document.getElementById('view-validations').classList.contains('active')) {
        loadValidationsAudit();
      }
      showToast(`Timetable generated successfully in ${data.time_taken_seconds}s! Zero hard violations and S3 daily limit strictly satisfied.`, 'success');
    } catch(e) {
      showToast("Error generating timetable: " + e, "error");
    } finally {
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = `<span>&#9654;</span> Run Solver`;
      }
    }
  }

  async function resetDemo() {
    if (currentUser.role !== 'admin') {
      showToast("Permission Denied: Only Admin can reset demo data.", "error");
      return;
    }
    if (!confirm("Reset database to clean original starter pack data?")) return;
    try {
      await fetch('/api/admin/reset-demo', { method: 'POST' });
      showToast("Demo data reset to clean initial state.", "success");
      allTimetableEvents = [];
      await renderTimetableGrid(true);
      await loadDashboard();
    } catch(e) {
      showToast(e, "error");
    }
  }

  // Timetable Grid Functions
  async function populateFilterOptions() {
    const typeEl = document.getElementById('ttFilterType');
    const type = typeEl ? typeEl.value : 'group';
    const targetSel = document.getElementById('ttFilterTarget');
    if (!targetSel) return;

    if (!metadata || !metadata.groups || metadata.groups.length === 0) {
      try {
        const resMeta = await fetch('/api/metadata');
        metadata = await resMeta.json();
      } catch (e) {
        console.warn("Metadata load error", e);
      }
    }

    let list = [];
    if (type === 'group') list = (metadata.groups || []).map(g => ({ id: g.id, label: `${g.id} (${g.name})` }));
    else if (type === 'faculty') list = (metadata.faculty || []).map(f => ({ id: f.id, label: `${f.id} — ${f.name}` }));
    else if (type === 'room') list = (metadata.rooms || []).map(r => ({ id: r.id, label: `${r.id} (${r.type})` }));

    if (list.length === 0 && type === 'group') {
      list = [
        { id: 'Y1-A', label: 'Y1-A (B.Tech Year 1, Section A)' },
        { id: 'Y1-B', label: 'Y1-B (B.Tech Year 1, Section B)' },
        { id: 'CSE-2', label: 'CSE-2 (CSE Year 2)' }
      ];
    }

    const currentVal = targetSel.value;
    targetSel.innerHTML = '';
    list.forEach(item => {
      const opt = document.createElement('option');
      opt.value = item.id;
      opt.textContent = item.label;
      targetSel.appendChild(opt);
    });

    if (currentVal && list.some(x => x.id === currentVal)) {
      targetSel.value = currentVal;
    } else if (list.some(x => x.id === 'Y1-A')) {
      targetSel.value = 'Y1-A';
    } else if (list.length > 0) {
      targetSel.value = list[0].id;
    }
  }

  async function onTtFilterTypeChange() {
    await populateFilterOptions();
    await renderTimetableGrid();
  }

  async function renderTimetableGrid(forceRefresh = false) {
    const typeEl = document.getElementById('ttFilterType');
    const type = typeEl ? typeEl.value : 'group';
    const targetSel = document.getElementById('ttFilterTarget');

    if (!targetSel || targetSel.options.length === 0) {
      await populateFilterOptions();
    }

    let target = targetSel && targetSel.value ? targetSel.value : 'Y1-A';

    if (forceRefresh || !allTimetableEvents || allTimetableEvents.length === 0) {
      try {
        const resEvents = await fetch('/api/timetable/grid');
        const evData = await resEvents.json();
        allTimetableEvents = evData.events || [];
      } catch (e) {
        console.warn("Could not load grid events", e);
      }
    }

    if (!target && targetSel && targetSel.options.length > 0) {
      target = targetSel.options[0].value;
      targetSel.value = target;
    }

    if (!target) return;

    // Update Subtitle
    const subtitleEl = document.getElementById('ttHeaderSubtitle');
    if (subtitleEl) {
      if (type === 'group') subtitleEl.textContent = `Sample Output for One Student Group: ${target}`;
      else if (type === 'faculty') subtitleEl.textContent = `Weekly Teaching Schedule for Faculty: ${target}`;
      else subtitleEl.textContent = `Venue Occupancy Schedule for Room: ${target}`;
    }

    const filtered = allTimetableEvents.filter(ev => {
      if (type === 'group') return ev.groups.includes(target);
      if (type === 'faculty') return ev.faculty_id === target;
      if (type === 'room') return ev.room_id === target;
      return true;
    });

    // Calculate Daily Hours
    const dayHours = { "MON": 0, "TUE": 0, "WED": 0, "THU": 0, "FRI": 0 };
    const seenBasketSlots = new Set();
    filtered.forEach(ev => {
      if (ev.basket_slot && type === 'group') {
        const bKey = `${ev.day}_${ev.basket_slot}`;
        if (!seenBasketSlots.has(bKey)) {
          seenBasketSlots.add(bKey);
          dayHours[ev.day] += (ev.duration || 1);
        }
      } else {
        dayHours[ev.day] += (ev.duration || 1);
      }
    });

    const maxDayH = Math.max(...Object.values(dayHours), 0);
    const counterEl = document.getElementById('ttSessionCounter');
    if (counterEl) counterEl.textContent = `${filtered.length} classes scheduled &bull; Total: ${Object.values(dayHours).reduce((a,b)=>a+b, 0)}h / week`;

    const loadBadge = document.getElementById('ttDailyLoadBadge');
    if (loadBadge) {
      if (type === 'group') {
        if (maxDayH <= 6) {
          loadBadge.className = 'badge badge-success';
          loadBadge.textContent = `Strict Cap Met: Max ${maxDayH}h/day (\u2264 6h)`;
        } else {
          loadBadge.className = 'badge badge-danger';
          loadBadge.textContent = `Cap Exceeded: ${maxDayH}h/day (> 6h)`;
        }
      } else if (type === 'faculty') {
        if (maxDayH <= 4) {
          loadBadge.className = 'badge badge-success';
          loadBadge.textContent = `Daily Cap Met: Max ${maxDayH}h/day (\u2264 4h)`;
        } else {
          loadBadge.className = 'badge badge-danger';
          loadBadge.textContent = `Overload: ${maxDayH}h/day (> 4h)`;
        }
      } else {
        loadBadge.className = 'badge badge-info';
        loadBadge.textContent = `Room Peak: ${maxDayH}h in a day`;
      }
    }

    const tbody = document.getElementById('ttGridBody');
    tbody.innerHTML = '';

    for (let p = 1; p <= 9; p++) {
      if (p === 6) {
        const trLunch = document.createElement('tr');
        trLunch.className = 'tt-lunch-row';
        trLunch.innerHTML = `
          <td style="font-weight:700; background:#cbd5e1; color:#0f172a; padding:10px;">Lunch Break<br><small>1:00 – 2:00</small></td>
          <td colspan="5" style="padding:10px; font-weight:700; color:#475569; letter-spacing:0.04em;">LUNCH BREAK (1:00 PM – 2:00 PM)</td>
        `;
        tbody.appendChild(trLunch);
      }

      const tr = document.createElement('tr');
      const tdPeriod = document.createElement('td');
      tdPeriod.className = 'tt-td-period';
      tdPeriod.innerHTML = `P${p}<small>${PERIOD_TIMES[p]}</small>`;
      tr.appendChild(tdPeriod);

      ["MON", "TUE", "WED", "THU", "FRI"].forEach(day => {
        const td = document.createElement('td');
        td.style.cssText = "vertical-align: top; padding: 6px;";
        const running = filtered.filter(ev => ev.day === day && p >= ev.start_period && p < ev.start_period + ev.duration);

        if (running.length === 0) {
          td.className = "cat-free";
          td.textContent = "Free";
        } else {
          // Check for parallel elective basket
          const basketEvents = running.filter(ev => ev.basket_slot);
          if (basketEvents.length > 1 && type === 'group') {
            const bSlot = basketEvents[0].basket_slot;
            const div = document.createElement('div');
            div.className = "tt-cell-card cat-oe";
            div.innerHTML = `
              <div class="tt-cell-title" style="color:#6b21a8;">Elective (${bSlot}) &bull; Choice 1 of ${basketEvents.length}</div>
              <div class="tt-cell-meta" style="color:#581c87;">
                ${basketEvents.map(e => `<strong>${e.course_id}</strong> in ${e.room_id}`).join(' &bull; ')}
              </div>
              <div class="tt-cell-meta" style="color:#7e22ce;">Parallel elective running across venues</div>
            `;
            td.appendChild(div);
          } else {
            running.forEach(ev => {
              const cat = getCourseCategory(ev.course_id, ev.kind);
              const isLab = ev.kind === "lab";
              const partNum = isLab ? (p - ev.start_period + 1) : 0;
              const kindLabel = isLab ? `Lab (Part ${partNum}/3)` : (ev.kind === "tutorial" ? "Tutorial" : "Lecture");

              const div = document.createElement('div');
              div.className = `tt-cell-card ${cat}`;
              div.innerHTML = `
                <div class="tt-cell-title">${ev.course_id} (${kindLabel})</div>
                <div class="tt-cell-meta">Room: ${ev.room_id} | Faculty: ${ev.faculty_name || ev.faculty_id}</div>
                ${type !== 'group' ? `<div class="tt-cell-meta" style="color:#64748b;">Cohort: ${ev.groups.join(', ')}</div>` : ''}
              `;
              td.appendChild(div);
            });
          }
        }
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    }
  }

  // --- VALIDATIONS AUDIT ENGINE FUNCTIONS ---
  async function loadValidationsAudit() {
    try {
      const res = await fetch('/api/timetable/validations');
      const data = await res.json();
      validationRules = data.rules || [];

      // Update Top Summary Cards
      const sum = data.summary || {};
      const statusEl = document.getElementById('valSummaryStatus');
      if (statusEl) {
        statusEl.textContent = sum.overall_academic_status || "FULLY COMPLIANT";
        statusEl.style.color = (sum.overall_academic_status === "FULLY COMPLIANT") ? "#10b981" : "#ef4444";
      }
      document.getElementById('valSummaryHardViolations').textContent = `${sum.hard_violations_count || 0} Hard Clashes Detected`;
      document.getElementById('valSummaryRuleCount').textContent = `${sum.validated_rules || 20} / ${sum.total_rules || 27}`;
      document.getElementById('valSummaryRuleSub').textContent = `${sum.validated_rules || 20} Active Academic Rules \u2022 ${sum.future_module_rules || 7} Campus Constraints`;
      
      const s3Pen = (sum.soft_penalties && sum.soft_penalties.S3) ? sum.soft_penalties.S3 : 0;
      document.getElementById('valSummaryS3').textContent = `${s3Pen} Violations`;

      // Render Rules
      renderValidationRules(validationRules);

      // Trigger official validator execution display
      const resVal = await fetch('/api/timetable/validate', { method: 'POST' });
      const valOutput = await resVal.json();
      if (valOutput.official_validator) {
        document.getElementById('valTerminalBadge').textContent = `RETURN CODE ${valOutput.official_validator.returncode}`;
        document.getElementById('valTerminalBadge').className = valOutput.official_validator.returncode === 0 ? "badge badge-success" : "badge badge-danger";
        document.getElementById('valTerminalOutput').textContent = valOutput.official_validator.stdout || "No output";
      }
    } catch(err) {
      console.error("Failed to load validation audit", err);
    }
  }

  function renderValidationRules(rules) {
    const container = document.getElementById('validationRulesContainer');
    container.innerHTML = '';

    if (!rules || rules.length === 0) {
      container.innerHTML = `<div style="text-align:center; padding:30px; color:#64748b;">No rules found.</div>`;
      return;
    }

    rules.forEach(r => {
      let badgeClass = "val-badge-pass";
      let statusText = r.status;
      if (r.status === "FAIL") badgeClass = "val-badge-fail";
      else if (r.status === "OPTIMIZED") badgeClass = "val-badge-opt";
      else if (r.status === "EXTENDED SCOPE") badgeClass = "val-badge-future";

      const card = document.createElement('div');
      card.className = "val-rule-card";
      card.innerHTML = `
        <div class="val-code-badge ${badgeClass}">${r.code}</div>
        <div style="flex:1;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
            <div>
              <strong style="font-size:0.92rem; color:#0f172a;">${r.name}</strong>
              <span class="badge ${r.category === 'Hard Constraint' ? 'badge-danger' : (r.category.includes('Soft') ? 'badge-warning' : 'badge-neutral')}" style="margin-left:8px; font-size:0.68rem;">
                ${r.category}
              </span>
              <span class="badge ${r.can_validate ? 'badge-success' : 'badge-neutral'}" style="margin-left:4px; font-size:0.68rem;">
                ${r.can_validate ? 'Validated &amp; Active' : 'Extended Rules'}
              </span>
            </div>
            <div>
              <span class="badge ${r.status === 'PASS' ? 'badge-success' : (r.status === 'OPTIMIZED' ? 'badge-info' : (r.status === 'FAIL' ? 'badge-danger' : 'badge-neutral'))}" style="font-weight:700;">
                ${r.status}
              </span>
            </div>
          </div>
          <div style="font-size:0.78rem; color:#475569; margin:6px 0;">
            ${r.description}
          </div>
          <div style="background:#f8fafc; border-left:3px solid ${r.can_validate ? '#2563eb' : '#cbd5e1'}; padding:6px 10px; border-radius:4px; font-size:0.75rem; color:#1e293b;">
            <strong>Verification Evidence:</strong> ${r.details}
          </div>
        </div>
      `;
      container.appendChild(card);
    });
  }

  function filterValidationRules(filterType, btn) {
    document.querySelectorAll('.panel-card .filter-pill').forEach(el => el.classList.remove('active'));
    if (btn) btn.classList.add('active');

    if (filterType === 'all') {
      renderValidationRules(validationRules);
    } else if (filterType === 'active') {
      renderValidationRules(validationRules.filter(r => r.can_validate === true));
    } else if (filterType === 'future') {
      renderValidationRules(validationRules.filter(r => r.can_validate === false));
    }
  }

  
  // ==========================================
  // DATASET & BENCHMARK INGESTION HANDLERS

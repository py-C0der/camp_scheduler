with open("frontend/src/app.ts", "r", encoding="utf-8") as f:
    text = f.read()

# 1. Update switchNav
old_switch_nav = """  function switchNav(viewName) {
    document.querySelectorAll('.view-panel').forEach(el => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));

    try {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch(e) {}

    if (viewName === 'dashboard') {
      document.getElementById('view-dashboard').classList.add('active');
      const dItem = document.getElementById('navItemDashboard');
      if (dItem) dItem.classList.add('active');
      document.getElementById('pageTitle').textContent = "Campus Operations Dashboard";
    } else if (viewName === 'timetable') {
      document.getElementById('view-timetable').classList.add('active');
      const tItem = document.getElementById('navItemTimetable');
      if (tItem) tItem.classList.add('active');
      document.getElementById('pageTitle').textContent = "Academic Timetable Management";
      renderTimetableGrid();
    } else if (viewName === 'validations') {
      document.getElementById('view-validations').classList.add('active');
      const valItem = document.getElementById('navItemValidations');
      if (valItem) valItem.classList.add('active');
      document.getElementById('pageTitle').textContent = "System Constraints & Validation Audit";
      loadValidationsAudit();
    } else if (viewName === 'disruptions') {
      document.getElementById('view-disruptions').classList.add('active');
      const disItem = document.getElementById('navItemDisruptions');
      if (disItem) disItem.classList.add('active');
      document.getElementById('pageTitle').textContent = "Disruption Management & Rescheduling Engine";
      loadDisruptionData();
    } else if (viewName === 'bookings') {
      document.getElementById('view-bookings').classList.add('active');
      const bkItem = document.getElementById('navItemBookings');
      if (bkItem) bkItem.classList.add('active');
      document.getElementById('pageTitle').textContent = "Smart Venue Booking & Approval Management";
      loadBookingData();
    } else if (viewName === 'examinations') {
      document.getElementById('view-examinations').classList.add('active');
      const exItem = document.getElementById('navItemExaminations');
      if (exItem) exItem.classList.add('active');
      document.getElementById('pageTitle').textContent = "Examination Scheduling Management";
      loadExamData();
    } else if (viewName === 'notifications') {
      document.getElementById('view-notifications').classList.add('active');
      const notifItem = document.getElementById('navItemNotifications');
      if (notifItem) notifItem.classList.add('active');
      document.getElementById('pageTitle').textContent = "Notification, Alerts & Communication Management";
      loadNotificationData();
    } else if (viewName === 'ai-assistant') {
      document.getElementById('view-ai-assistant').classList.add('active');
      const aiItem = document.getElementById('navItemAiAssistant');
      if (aiItem) aiItem.classList.add('active');
      document.getElementById('pageTitle').textContent = "AI Scheduling Assistant & Decision Explainability";
      loadAiAssistantData();
    }
  }"""

new_switch_nav = """  function switchNav(viewName: string) {
    const targetPanel = document.getElementById(`view-${viewName}`);
    
    // If the panel does not exist in the current document (e.g. on a separate standalone page), redirect
    if (!targetPanel) {
      if (viewName === 'dashboard') window.location.href = 'index.html#/dashboard';
      else window.location.href = `${viewName}.html`;
      return;
    }

    document.querySelectorAll('.view-panel').forEach((el: any) => el.classList.remove('active'));
    document.querySelectorAll('.nav-item').forEach((el: any) => el.classList.remove('active'));

    try {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } catch(e) {}

    // Synchronize URL hash
    try {
      if (window.location.hash !== `#/${viewName}`) {
        window.history.pushState(null, '', `#/${viewName}`);
      }
    } catch(e) {}

    targetPanel.classList.add('active');

    // Capitalize nav item id mapping
    const navItemIdMap: { [k: string]: string } = {
      'dashboard': 'navItemDashboard',
      'timetable': 'navItemTimetable',
      'validations': 'navItemValidations',
      'disruptions': 'navItemDisruptions',
      'bookings': 'navItemBookings',
      'examinations': 'navItemExaminations',
      'notifications': 'navItemNotifications',
      'ai-assistant': 'navItemAiAssistant'
    };

    const navId = navItemIdMap[viewName];
    if (navId) {
      const navEl = document.getElementById(navId);
      if (navEl) navEl.classList.add('active');
    }

    const pTitle = document.getElementById('pageTitle');
    if (viewName === 'dashboard') {
      if (pTitle) pTitle.textContent = "Campus Operations Dashboard";
    } else if (viewName === 'timetable') {
      if (pTitle) pTitle.textContent = "Academic Timetable Management";
      if (typeof renderTimetableGrid === 'function') renderTimetableGrid();
    } else if (viewName === 'validations') {
      if (pTitle) pTitle.textContent = "System Constraints & Validation Audit";
      if (typeof loadValidationsAudit === 'function') loadValidationsAudit();
      if (typeof renderCsvMatrixGrid === 'function') renderCsvMatrixGrid();
    } else if (viewName === 'disruptions') {
      if (pTitle) pTitle.textContent = "Disruption Management & Rescheduling Engine";
      if (typeof loadDisruptionData === 'function') loadDisruptionData();
    } else if (viewName === 'bookings') {
      if (pTitle) pTitle.textContent = "Smart Venue Booking & Approval Management";
      if (typeof loadBookingData === 'function') loadBookingData();
    } else if (viewName === 'examinations') {
      if (pTitle) pTitle.textContent = "Examination Scheduling Management";
      if (typeof loadExamData === 'function') loadExamData();
    } else if (viewName === 'notifications') {
      if (pTitle) pTitle.textContent = "Notification, Alerts & Communication Management";
      if (typeof loadNotificationData === 'function') loadNotificationData();
    } else if (viewName === 'ai-assistant') {
      if (pTitle) pTitle.textContent = "AI Scheduling Assistant & Decision Explainability";
      if (typeof loadAiAssistantData === 'function') loadAiAssistantData();
    }
  }

  // Support direct browser hash routing (e.g. #/timetable, #/bookings)
  window.addEventListener('hashchange', function() {
    const hash = (window.location.hash || '').replace('#/', '').replace('#', '');
    if (hash && document.getElementById(`view-${hash}`)) {
      switchNav(hash);
    }
  });"""

norm_text = text.replace("\r\n", "\n")
norm_old = old_switch_nav.replace("\r\n", "\n")
assert norm_old in norm_text, "old_switch_nav not found"
norm_text = norm_text.replace(norm_old, new_switch_nav.replace("\r\n", "\n"), 1)

# 2. Add processSelectedDatasetFile definition
old_files_func = "  async function processSelectedDatasetFiles(files: File[]) {"
new_files_func = """  function processSelectedDatasetFile(file: any) {
    if (file) processSelectedDatasetFiles([file]);
  }

  async function processSelectedDatasetFiles(files: File[]) {"""

assert old_files_func in norm_text, "old_files_func not found"
norm_text = norm_text.replace(old_files_func, new_files_func, 1)

with open("frontend/src/app.ts", "w", encoding="utf-8") as f:
    f.write(norm_text.replace("\n", "\r\n"))

print("Updated switchNav and processSelectedDatasetFile in frontend/src/app.ts")

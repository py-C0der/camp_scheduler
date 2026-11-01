import os
import re
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
PUBLIC_DIR = BASE_DIR / "public"

with open(FRONTEND_DIR / "index.html", "r", encoding="utf-8") as f:
    full_html = f.read()

# Views definition mapping: (id, name, file_name, title, nav_id, init_fn)
PAGES = [
    {
        "id": "view-dashboard",
        "file": "dashboard.html",
        "title": "Campus Operations Dashboard",
        "nav_id": "navItemDashboard",
        "init": "loadDashboard();"
    },
    {
        "id": "view-timetable",
        "file": "timetable.html",
        "title": "Academic Timetable Management",
        "nav_id": "navItemTimetable",
        "init": "renderTimetableGrid();"
    },
    {
        "id": "view-validations",
        "file": "validations.html",
        "title": "System Constraints & Validation Audit",
        "nav_id": "navItemValidations",
        "init": "loadValidationsAudit(); renderCsvMatrixGrid();"
    },
    {
        "id": "view-examinations",
        "file": "examinations.html",
        "title": "Examination Scheduling Management",
        "nav_id": "navItemExaminations",
        "init": "loadExamData();"
    },
    {
        "id": "view-bookings",
        "file": "bookings.html",
        "title": "Smart Venue Booking & Approval Management",
        "nav_id": "navItemBookings",
        "init": "loadBookingData();"
    },
    {
        "id": "view-disruptions",
        "file": "disruptions.html",
        "title": "Disruption Management & Rescheduling Engine",
        "nav_id": "navItemDisruptions",
        "init": "loadDisruptionData();"
    },
    {
        "id": "view-notifications",
        "file": "notifications.html",
        "title": "Notification, Alerts & Communication Management",
        "nav_id": "navItemNotifications",
        "init": "loadNotificationData();"
    },
    {
        "id": "view-ai-assistant",
        "file": "ai-assistant.html",
        "title": "AI Scheduling Assistant & Decision Explainability",
        "nav_id": "navItemAiAssistant",
        "init": "loadAiAssistantData();"
    }
]

# Find where the view-panels start and where they end
first_panel_idx = full_html.find('<div id="view-dashboard"')
assert first_panel_idx != -1, "First view panel not found"

# Find end of all panels: right before <!-- Universal Modals or authModal
modals_start_idx = full_html.find('<!-- Auth Modal')
if modals_start_idx == -1:
    modals_start_idx = full_html.find('id="authModal"')
    modals_start_idx = full_html.rfind('<div', 0, modals_start_idx)

assert modals_start_idx != -1, "Modals start not found"

head_and_nav = full_html[:first_panel_idx]
modals_and_foot = full_html[modals_start_idx:]

# Extract each view panel HTML
panels_html = full_html[first_panel_idx:modals_start_idx]

# Pattern to extract individual view panel blocks
panel_pattern = re.compile(r'(<div\s+id="(view-[^"]+)"\s+class="view-panel[^"]*">.*?)(?=<div\s+id="view-|\s*<!--\s*Auth\s*Modal|$)', re.DOTALL)
extracted_panels = {}
for match in panel_pattern.finditer(panels_html):
    panel_full = match.group(1).strip()
    panel_id = match.group(2).strip()
    extracted_panels[panel_id] = panel_full

print(f"Extracted {len(extracted_panels)} view panels: {list(extracted_panels.keys())}")

# Update sidebar in head_and_nav to use proper hrefs and active states
nav_links_updated = head_and_nav

sidebar_replacements = [
    ('id="navItemDashboard" onclick="switchNav(\'dashboard\')"', 'id="navItemDashboard" href="dashboard.html" onclick="if(window.switchNav){switchNav(\'dashboard\'); return false;}"'),
    ('id="navItemTimetable" onclick="switchNav(\'timetable\')"', 'id="navItemTimetable" href="timetable.html" onclick="if(window.switchNav){switchNav(\'timetable\'); return false;}"'),
    ('id="navItemValidations" onclick="switchNav(\'validations\')"', 'id="navItemValidations" href="validations.html" onclick="if(window.switchNav){switchNav(\'validations\'); return false;}"'),
    ('id="navItemExaminations" onclick="switchNav(\'examinations\')"', 'id="navItemExaminations" href="examinations.html" onclick="if(window.switchNav){switchNav(\'examinations\'); return false;}"'),
    ('id="navItemBookings" onclick="switchNav(\'bookings\')"', 'id="navItemBookings" href="bookings.html" onclick="if(window.switchNav){switchNav(\'bookings\'); return false;}"'),
    ('id="navItemDisruptions" onclick="switchNav(\'disruptions\')"', 'id="navItemDisruptions" href="disruptions.html" onclick="if(window.switchNav){switchNav(\'disruptions\'); return false;}"'),
    ('id="navItemNotifications" onclick="switchNav(\'notifications\')"', 'id="navItemNotifications" href="notifications.html" onclick="if(window.switchNav){switchNav(\'notifications\'); return false;}"'),
    ('id="navItemAiAssistant" onclick="switchNav(\'ai-assistant\')"', 'id="navItemAiAssistant" href="ai-assistant.html" onclick="if(window.switchNav){switchNav(\'ai-assistant\'); return false;}"'),
    ('onclick="showUserManagementModal()"', 'href="login.html" onclick="if(window.showUserManagementModal){showUserManagementModal(); return false;}"')
]

for old_s, new_s in sidebar_replacements:
    nav_links_updated = nav_links_updated.replace(old_s, new_s)

# Also update index.html with these resilient sidebar links
updated_index_html = nav_links_updated + panels_html + modals_and_foot
with open(FRONTEND_DIR / "index.html", "w", encoding="utf-8") as f:
    f.write(updated_index_html)
print("Updated frontend/index.html with dual-action sidebar links")

# Generate dedicated pages
for p in PAGES:
    p_id = p["id"]
    p_file = p["file"]
    p_title = p["title"]
    p_nav = p["nav_id"]
    p_init = p["init"]

    if p_id not in extracted_panels:
        print(f"Warning: {p_id} not found in extracted panels, skipping")
        continue

    panel_content = extracted_panels[p_id]
    # Ensure this panel has 'active' class
    panel_content = re.sub(r'class="view-panel[^"]*"', 'class="view-panel active"', panel_content, count=1)

    # Customize head and header for this page
    page_head = nav_links_updated
    # Update <title>
    page_head = re.sub(r'<title>.*?</title>', f'<title>{p_title} - Chilika Institute of Technology</title>', page_head)
    # Update pageTitle text
    page_head = re.sub(r'<div class="page-title"[^>]*>.*?</div>', f'<div class="page-title" id="pageTitle">{p_title}</div>', page_head)

    # Update active class in sidebar: remove active from all nav-item, add to p_nav
    page_head = re.sub(r'class="nav-item active"', 'class="nav-item"', page_head)
    page_head = page_head.replace(f'id="{p_nav}" class="nav-item"', f'id="{p_nav}" class="nav-item active"')
    page_head = page_head.replace(f'class="nav-item" id="{p_nav}"', f'class="nav-item active" id="{p_nav}"')

    # Add inline auto-init script right before </body>
    init_script = f"""
    <script>
      window.addEventListener('DOMContentLoaded', function() {{
        setTimeout(function() {{
          try {{
            {p_init}
          }} catch(e) {{
            console.warn('Auto-init warning for {p_file}:', e);
          }}
        }}, 100);
      }});
    </script>
</body>
"""
    page_foot = modals_and_foot.replace('</body>', init_script)

    full_page = page_head + "\n" + panel_content + "\n" + page_foot
    with open(FRONTEND_DIR / p_file, "w", encoding="utf-8") as f:
        f.write(full_page)
    print(f"Generated page: frontend/{p_file}")

# Generate dedicated login.html
login_html = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Institutional Authentication &amp; Role Portal - Chilika Institute of Technology</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="/css/main.css">
  <style>
    body {
      background: radial-gradient(circle at 10% 20%, #eef2ff 0%, #f8fafc 90%);
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 24px;
      font-family: 'Plus Jakarta Sans', sans-serif;
    }
    .auth-portal-card {
      background: #ffffff;
      border-radius: 16px;
      box-shadow: 0 20px 40px -15px rgba(30, 41, 59, 0.15), 0 0 1px 1px rgba(226, 232, 240, 0.8);
      width: 100%;
      max-width: 900px;
      display: grid;
      grid-template-columns: 1fr 1.1fr;
      overflow: hidden;
      border: 1px solid #e2e8f0;
    }
    @media (max-width: 768px) {
      .auth-portal-card {
        grid-template-columns: 1fr;
      }
    }
    .auth-sidebar {
      background: linear-gradient(135deg, #1e1b4b 0%, #312e81 60%, #4338ca 100%);
      color: #ffffff;
      padding: 40px 32px;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }
    .auth-form-wrap {
      padding: 40px;
      display: flex;
      flex-direction: column;
      justify-content: center;
    }
    .role-preset-btn {
      background: #ffffff;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      padding: 10px 14px;
      text-align: left;
      cursor: pointer;
      transition: all 0.15s ease;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    .role-preset-btn:hover {
      border-color: #6366f1;
      background: #f8fafc;
      transform: translateY(-1px);
    }
    .role-badge {
      font-size: 0.7rem;
      font-weight: 700;
      padding: 2px 6px;
      border-radius: 4px;
      text-transform: uppercase;
    }
  </style>
</head>
<body>

  <div class="auth-portal-card">
    <!-- Left Hero Banner -->
    <div class="auth-sidebar">
      <div>
        <div style="display:flex; align-items:center; gap:12px; margin-bottom:24px;">
          <div style="background:#6366f1; color:#fff; font-weight:800; font-size:1.2rem; width:44px; height:44px; border-radius:10px; display:flex; align-items:center; justify-content:center; box-shadow:0 4px 10px rgba(99,102,241,0.4);">
            CIT
          </div>
          <div>
            <div style="font-weight:800; font-size:1.15rem; letter-spacing:-0.02em;">Chilika Institute of Technology</div>
            <div style="font-size:0.75rem; color:#c7d2fe; text-transform:uppercase; letter-spacing:0.06em; font-weight:600;">Scheduling &amp; Venue Management Platform</div>
          </div>
        </div>

        <h2 style="font-size:1.4rem; font-weight:700; margin-bottom:12px; line-height:1.3;">
          Institutional Academic Resource &amp; Operations Portal
        </h2>
        <p style="font-size:0.85rem; color:#cbd5e1; line-height:1.6; margin-bottom:24px;">
          Integrated governance platform connecting Academic Administration, Department Coordinators, Faculty Members, and Student Clubs.
        </p>

        <div style="border-top:1px solid rgba(255,255,255,0.15); padding-top:20px;">
          <div style="font-size:0.75rem; font-weight:700; text-transform:uppercase; letter-spacing:0.06em; color:#a5b4fc; margin-bottom:12px;">
            Core Platform Capabilities
          </div>
          <div style="font-size:0.8rem; color:#e0e7ff; display:flex; flex-direction:column; gap:8px;">
            <div>&#10004; <strong>0-Clash Timetable</strong> with Google OR-Tools CP-SAT</div>
            <div>&#10004; <strong>Midsem Exams</strong> &amp; Capacity Seating Optimization</div>
            <div>&#10004; <strong>Smart Venue Bookings</strong> with Role Priority Caps</div>
            <div>&#10004; <strong>Disruption Management</strong> with Minimal Perturbation</div>
            <div>&#10004; <strong>AI Scheduling Assistant</strong> &amp; Grounded Decisions</div>
          </div>
        </div>
      </div>

      <div style="font-size:0.75rem; color:#94a3b8; border-top:1px solid rgba(255,255,255,0.1); padding-top:16px;">
        &copy; 2026-2027 Chilika Institute of Technology &middot; All Rights Reserved
      </div>
    </div>

    <!-- Right Login Form -->
    <div class="auth-form-wrap">
      <div style="margin-bottom: 24px;">
        <h3 style="font-size:1.3rem; font-weight:800; color:#0f172a; margin:0 0 6px 0;">Sign In to Your Account</h3>
        <p style="font-size:0.85rem; color:#64748b; margin:0;">Enter institutional credentials or select a quick-access role profile.</p>
      </div>

      <div id="loginFeedback" style="display:none; margin-bottom:16px; padding:10px 14px; border-radius:6px; font-size:0.85rem;"></div>

      <form id="portalLoginForm" onsubmit="handlePortalLogin(event)" style="display:flex; flex-direction:column; gap:16px;">
        <div>
          <label style="display:block; font-size:0.82rem; font-weight:600; color:#334155; margin-bottom:6px;">Institutional Email or Username</label>
          <input type="text" id="portalEmail" class="form-input" placeholder="e.g. admin@cit.ac.in" required style="width:100%; padding:10px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:0.9rem;" value="admin@cit.ac.in">
        </div>

        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
            <label style="font-size:0.82rem; font-weight:600; color:#334155; margin:0;">Password</label>
            <span style="font-size:0.75rem; color:#6366f1; cursor:pointer;" onclick="togglePortalPassword()">Show Password</span>
          </div>
          <input type="password" id="portalPassword" class="form-input" placeholder="Enter password" required style="width:100%; padding:10px 12px; border:1px solid #cbd5e1; border-radius:8px; font-size:0.9rem;" value="cit@2026">
        </div>

        <div style="display:flex; justify-content:space-between; align-items:center;">
          <label style="display:flex; align-items:center; gap:8px; font-size:0.82rem; color:#475569; cursor:pointer;">
            <input type="checkbox" id="portalRemember" checked> Remember this session
          </label>
          <a href="#" onclick="alert('Please contact Dean Academics (admin@cit.ac.in) for password reset.'); return false;" style="font-size:0.82rem; color:#6366f1; text-decoration:none;">Forgot password?</a>
        </div>

        <button type="submit" id="portalLoginBtn" class="btn btn-primary" style="background:#4338ca; padding:12px; font-size:0.95rem; font-weight:700; border-radius:8px; box-shadow:0 4px 12px rgba(67, 56, 202, 0.3);">
          <span>&#128273;</span> Sign In to CIT Platform
        </button>
      </form>

      <!-- 1-Click Role Presets for Judges -->
      <div style="margin-top:28px; border-top:1px solid #e2e8f0; padding-top:20px;">
        <div style="font-size:0.78rem; font-weight:700; color:#64748b; text-transform:uppercase; letter-spacing:0.04em; margin-bottom:12px;">
          Fast 1-Click Role Access (Evaluation Presets)
        </div>
        <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
          <div class="role-preset-btn" onclick="selectPreset('admin@cit.ac.in', 'cit@2026')">
            <span style="font-size:1.2rem;">&#128737;&#65039;</span>
            <div>
              <div style="font-weight:700; font-size:0.8rem; color:#0f172a;">Dean Academics</div>
              <span class="role-badge" style="background:#e0e7ff; color:#3730a3;">Admin</span>
            </div>
          </div>
          <div class="role-preset-btn" onclick="selectPreset('coordinator@cit.ac.in', 'cit@2026')">
            <span style="font-size:1.2rem;">&#127963;&#65039;</span>
            <div>
              <div style="font-weight:700; font-size:0.8rem; color:#0f172a;">CSE Coordinator</div>
              <span class="role-badge" style="background:#fef3c7; color:#92400e;">Coordinator</span>
            </div>
          </div>
          <div class="role-preset-btn" onclick="selectPreset('faculty@cit.ac.in', 'cit@2026')">
            <span style="font-size:1.2rem;">&#128104;&#8205;&#127979;</span>
            <div>
              <div style="font-weight:700; font-size:0.8rem; color:#0f172a;">Dr. Arvind Kumar</div>
              <span class="role-badge" style="background:#ecfdf5; color:#065f46;">Faculty (F01)</span>
            </div>
          </div>
          <div class="role-preset-btn" onclick="selectPreset('club@cit.ac.in', 'cit@2026')">
            <span style="font-size:1.2rem;">&#127914;</span>
            <div>
              <div style="font-weight:700; font-size:0.8rem; color:#0f172a;">Robotics Society</div>
              <span class="role-badge" style="background:#fce7f3; color:#9d174d;">Club Rep</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>

  <script src="/dist/app.bundle.js"></script>
  <script>
    function selectPreset(email, pass) {
      document.getElementById('portalEmail').value = email;
      document.getElementById('portalPassword').value = pass;
      document.getElementById('portalLoginForm').dispatchEvent(new Event('submit', { cancelable: true }));
    }

    function togglePortalPassword() {
      const input = document.getElementById('portalPassword');
      if (input.type === 'password') input.type = 'text';
      else input.type = 'password';
    }

    async function handlePortalLogin(e) {
      e.preventDefault();
      const email = document.getElementById('portalEmail').value.trim();
      const password = document.getElementById('portalPassword').value;
      const btn = document.getElementById('portalLoginBtn');
      const feedback = document.getElementById('loginFeedback');

      btn.disabled = true;
      btn.innerHTML = '<span>&#9203;</span> Verifying Credentials...';
      feedback.style.display = 'none';

      try {
        const res = await fetch('/api/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          localStorage.setItem('cit_user', JSON.stringify(data.user));
          feedback.style.display = 'block';
          feedback.style.background = '#ecfdf5';
          feedback.style.color = '#065f46';
          feedback.style.border = '1px solid #a7f3d0';
          feedback.innerHTML = `<strong>&#10004; Authenticated as ${data.user.name} (${data.user.role.toUpperCase()})!</strong> Redirecting to dashboard...`;

          setTimeout(() => {
            const role = data.user.role.toLowerCase();
            if (role === 'admin') window.location.href = 'dashboard.html';
            else if (role === 'dept_coordinator' || role === 'coordinator') window.location.href = 'timetable.html';
            else if (role === 'faculty') window.location.href = 'timetable.html';
            else if (role === 'club_rep' || role === 'club') window.location.href = 'bookings.html';
            else window.location.href = 'dashboard.html';
          }, 600);
        } else {
          feedback.style.display = 'block';
          feedback.style.background = '#fef2f2';
          feedback.style.color = '#991b1b';
          feedback.style.border = '1px solid #fecaca';
          feedback.innerHTML = `<strong>&#10006; Sign-in failed:</strong> ${data.detail || data.message || 'Invalid credentials'}`;
          btn.disabled = false;
          btn.innerHTML = '<span>&#128273;</span> Sign In to CIT Platform';
        }
      } catch(err) {
        feedback.style.display = 'block';
        feedback.style.background = '#fef2f2';
        feedback.style.color = '#991b1b';
        feedback.style.border = '1px solid #fecaca';
        feedback.innerHTML = `<strong>&#10006; Network Error:</strong> ${err.message}`;
        btn.disabled = false;
        btn.innerHTML = '<span>&#128273;</span> Sign In to CIT Platform';
      }
    }
  </script>
</body>
</html>
"""

with open(FRONTEND_DIR / "login.html", "w", encoding="utf-8") as f:
    f.write(login_html)
print("Generated page: frontend/login.html")

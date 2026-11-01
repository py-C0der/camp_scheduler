// CIT Campus Real-Time Notification & Alerts Hub Module
import { api } from './api';
import { CampusNotification } from './types';

declare const window: any;
declare const document: any;

  // =========================================================================
  let currentNotifFilter = { category: '', status: '', search: '' };
  let allUserNotifications = [];
  let activeNotifSubTab = 'inbox';
  let notifWs = null;

  async function fetchUnreadCount() {
    try {
      const res = await fetch(`/api/notifications/unread-count?user_id=${currentUser.id}`, {
        headers: { 'X-User-Id': currentUser.id, 'X-User-Role': currentUser.role }
      });
      if (!res.ok) return;
      const data = await res.json();
      const count = data.unread_count || 0;

      const badge = document.getElementById('notifBadge');
      if (badge) {
        badge.textContent = count > 99 ? '99+' : count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';
      }

      const dropCount = document.getElementById('notifDropdownCount');
      if (dropCount) {
        dropCount.textContent = `${count} unread`;
      }

      const inboxCount = document.getElementById('inboxBadgeCount');
      if (inboxCount) {
        inboxCount.textContent = count;
      }
    } catch (err) {
      console.warn("Unread count fetch error:", err);
    }
  }

  function toggleNotifDropdown(e) {
    if (e) e.stopPropagation();
    const dropdown = document.getElementById('notifDropdown');
    if (!dropdown) return;
    const isShowing = dropdown.style.display === 'block';
    dropdown.style.display = isShowing ? 'none' : 'block';
    if (!isShowing) {
      loadDropdownNotifications();
    }
  }

  document.addEventListener('click', function(e) {
    const dropdown = document.getElementById('notifDropdown');
    const bellBtn = document.getElementById('notifBellBtn');
    if (dropdown && dropdown.style.display === 'block') {
      if (!dropdown.contains(e.target) && !bellBtn.contains(e.target)) {
        dropdown.style.display = 'none';
      }
    }
  });

  async function loadDropdownNotifications() {
    try {
      const res = await fetch(`/api/notifications?limit=5`, {
        headers: { 'X-User-Id': currentUser.id, 'X-User-Role': currentUser.role }
      });
      if (!res.ok) return;
      const data = await res.json();
      const listEl = document.getElementById('notifDropdownList');
      if (!listEl) return;

      if (!data.notifications || data.notifications.length === 0) {
        listEl.innerHTML = '<div style="padding: 24px; text-align: center; color: #94a3b8; font-size: 0.85rem;">No notifications found</div>';
        return;
      }

      const sevDotColors = { critical: '#ef4444', high: '#f59e0b', medium: '#2563eb', low: '#94a3b8' };

      listEl.innerHTML = data.notifications.map(n => `
        <div onclick="openNotificationDetail('${n.id}', '${n.related_module}', '${n.related_record_id || ''}')" style="padding: 12px 16px; border-bottom: 1px solid #f1f5f9; cursor: pointer; transition: background 0.15s; background: ${n.is_read ? '#fff' : '#f0f9ff'};" onmouseover="this.style.background='#f8fafc'" onmouseout="this.style.background='${n.is_read ? '#fff' : '#f0f9ff'}'">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
            <div style="display:flex; align-items:center; gap:6px;">
              <span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${sevDotColors[n.severity] || '#2563eb'};"></span>
              <strong style="font-size:0.82rem; color:#0f172a; max-width:240px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">${n.title}</strong>
            </div>
            <span style="font-size:0.7rem; color:#94a3b8;">${n.created_at.substring(11, 16) || ''}</span>
          </div>
          <div style="font-size:0.78rem; color:#475569; line-height:1.3; max-height:2.6em; overflow:hidden; text-overflow:ellipsis;">${n.message}</div>
        </div>
      `).join('');
    } catch (err) {
      console.warn("Dropdown notif load error:", err);
    }
  }

  async function loadNotificationData() {
    await fetchUnreadCount();
    if (activeNotifSubTab === 'inbox') {
      await loadNotificationsInbox();
    } else if (activeNotifSubTab === 'preferences') {
      await loadNotificationPreferences();
    } else if (activeNotifSubTab === 'admin') {
      await loadAdminNotificationDashboard();
    }
  }

  function switchNotifSubTab(tabName) {
    activeNotifSubTab = tabName;
    ['inbox', 'preferences', 'admin'].forEach(t => {
      const btn = document.getElementById(`tabBtnNotif${t.charAt(0).toUpperCase() + t.slice(1)}`);
      const panel = document.getElementById(`notifSubtab${t.charAt(0).toUpperCase() + t.slice(1)}`);
      if (btn) {
        if (t === tabName) {
          btn.classList.add('active');
          btn.style.borderBottom = '2px solid #2563eb';
          btn.style.fontWeight = '700';
        } else {
          btn.classList.remove('active');
          btn.style.borderBottom = 'none';
          btn.style.fontWeight = '500';
        }
      }
      if (panel) panel.style.display = t === tabName ? 'block' : 'none';
    });

    if (tabName === 'inbox') loadNotificationsInbox();
    else if (tabName === 'preferences') loadNotificationPreferences();
    else if (tabName === 'admin') loadAdminNotificationDashboard();
  }

  async function loadNotificationsInbox() {
    try {
      let url = `/api/notifications?limit=100`;
      if (currentNotifFilter.category) url += `&category=${encodeURIComponent(currentNotifFilter.category)}`;
      if (currentNotifFilter.status === 'unread') url += `&is_read=false`;
      if (currentNotifFilter.status === 'read') url += `&is_read=true`;
      if (currentNotifFilter.search) url += `&search=${encodeURIComponent(currentNotifFilter.search)}`;

      const res = await fetch(url, {
        headers: { 'X-User-Id': currentUser.id, 'X-User-Role': currentUser.role }
      });
      if (!res.ok) throw new Error("Failed to load notifications");
      const data = await res.json();
      allUserNotifications = data.notifications || [];
      renderNotificationList(allUserNotifications);
    } catch (err) {
      const listEl = document.getElementById('notifListContainer');
      if (listEl) listEl.innerHTML = `<div class="panel-card" style="padding:24px; text-align:center; color:#ef4444;">Error loading notifications: ${err.message}</div>`;
    }
  }

  function filterNotifsCategory(cat, btn) {
    currentNotifFilter.category = cat;
    if (btn && btn.parentElement) {
      btn.parentElement.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
    }
    loadNotificationsInbox();
  }

  function filterNotifsStatus(st, btn) {
    currentNotifFilter.status = st;
    if (btn && btn.parentElement) {
      btn.parentElement.querySelectorAll('.filter-pill').forEach(p => p.classList.remove('active'));
      btn.classList.add('active');
    }
    loadNotificationsInbox();
  }

  let searchTimeout = null;
  function searchNotifs(q) {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      currentNotifFilter.search = q.trim();
      loadNotificationsInbox();
    }, 250);
  }

  function renderNotificationList(items) {
    const listEl = document.getElementById('notifListContainer');
    if (!listEl) return;

    if (!items || items.length === 0) {
      listEl.innerHTML = `
        <div class="panel-card" style="padding:48px 24px; text-align:center;">
          <div style="font-size:2.5rem; margin-bottom:12px;">&#128236;</div>
          <h3 style="font-size:1.1rem; font-weight:700; color:#0f172a; margin-bottom:6px;">No Notifications</h3>
          <p style="font-size:0.85rem; color:#64748b; margin:0;">There are no alerts matching the active category or status filter.</p>
        </div>`;
      return;
    }

    const sevStyles = {
      critical: { bg: '#fee2e2', color: '#b91c1c', border: '#fca5a5', label: 'CRITICAL' },
      high: { bg: '#fef3c7', color: '#b45309', border: '#fcd34d', label: 'HIGH' },
      medium: { bg: '#e0e7ff', color: '#4338ca', border: '#a5b4fc', label: 'MEDIUM' },
      low: { bg: '#f1f5f9', color: '#475569', border: '#cbd5e1', label: 'LOW' }
    };

    listEl.innerHTML = items.map(n => {
      const s = sevStyles[n.severity.toLowerCase()] || sevStyles.medium;
      const catLabel = n.category.replace('_', ' ').toUpperCase();

      return `
        <div class="panel-card" style="margin-bottom:0; border-left: 4px solid ${s.color}; background:${n.is_read ? '#fff' : '#f8fafc'}; transition: transform 0.15s;">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:12px; margin-bottom:8px; flex-wrap:wrap;">
            <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
              <span class="badge" style="background:${s.bg}; color:${s.color}; border:1px solid ${s.border};">${s.label}</span>
              <span class="badge badge-neutral">${catLabel}</span>
              ${n.related_record_id ? `<span class="badge badge-info" style="font-family:'JetBrains Mono', monospace;">ID: ${n.related_record_id}</span>` : ''}
              ${!n.is_read ? `<span class="badge" style="background:#3b82f6; color:#fff;">UNREAD</span>` : ''}
            </div>
            <div style="font-size:0.75rem; color:#64748b; font-weight:500;">
              ${n.created_at}
            </div>
          </div>

          <h3 style="font-size:1.02rem; font-weight:700; color:#0f172a; margin-bottom:6px;">${n.title}</h3>
          <p style="font-size:0.86rem; color:#334155; line-height:1.5; margin-bottom:14px; white-space:pre-line;">${n.message}</p>

          <div style="display:flex; justify-content:space-between; align-items:center; border-top:1px solid #f1f5f9; padding-top:10px; flex-wrap:wrap; gap:8px;">
            <div>
              ${getActionNavButton(n.related_module, n.related_record_id)}
            </div>
            <div style="display:flex; gap:8px;">
              ${!n.is_read ? `
                <button class="btn btn-outline btn-sm" onclick="markNotificationRead('${n.id}')">
                  <span>&#10003;</span> Mark Read
                </button>
              ` : ''}
              <button class="btn btn-outline btn-sm" style="color:#64748b;" onclick="archiveNotification('${n.id}')" title="Archive / Dismiss">
                <span>&#128465;</span> Archive
              </button>
            </div>
          </div>
        </div>
      `;
    }).join('');
  }

  function getActionNavButton(domainName, recordId) {
    if (!domainName) return '';
    const m = domainName.toLowerCase();
    if (m === 'module_2' || m === 'timetable') {
      return `<button class="btn btn-primary btn-sm" onclick="switchNav('timetable')"><span>&#9776;</span> View Master Timetable &rarr;</button>`;
    } else if (m === 'module_3' || m === 'examinations') {
      return `<button class="btn btn-primary btn-sm" onclick="switchNav('examinations')"><span>&#128197;</span> View Exam Timetable &rarr;</button>`;
    } else if (m === 'module_4' || m === 'venue_bookings' || m === 'bookings') {
      return `<button class="btn btn-primary btn-sm" onclick="switchNav('bookings')"><span>&#127970;</span> View Venue Bookings &rarr;</button>`;
    } else if (m === 'module_5' || m === 'disruptions') {
      return `<button class="btn btn-primary btn-sm" onclick="switchNav('disruptions')"><span>&#8644;</span> Inspect Disruption Engine &rarr;</button>`;
    }
    return '';
  }

  async function openNotificationDetail(id, relatedModule, recordId) {
    await markNotificationRead(id);
    toggleNotifDropdown();
    if (relatedModule === 'module_2') switchNav('timetable');
    else if (relatedModule === 'module_3') switchNav('examinations');
    else if (relatedModule === 'module_4') switchNav('bookings');
    else if (relatedModule === 'module_5') switchNav('disruptions');
    else switchNav('notifications');
  }

  async function markNotificationRead(id) {
    try {
      const res = await fetch(`/api/notifications/${id}/read`, {
        method: 'PATCH',
        headers: { 'X-User-Id': currentUser.id, 'X-User-Role': currentUser.role }
      });
      if (res.ok) {
        await fetchUnreadCount();
        if (activeNotifSubTab === 'inbox') loadNotificationsInbox();
      }
    } catch (err) {
      console.warn("Mark read error:", err);
    }
  }

  async function markAllNotifsRead() {
    try {
      const res = await fetch(`/api/notifications/mark-all-read`, {
        method: 'POST',
        headers: { 'X-User-Id': currentUser.id, 'X-User-Role': currentUser.role }
      });
      if (res.ok) {
        await fetchUnreadCount();
        if (activeNotifSubTab === 'inbox') loadNotificationsInbox();
      }
    } catch (err) {
      console.warn("Mark all read error:", err);
    }
  }

  async function archiveNotification(id) {
    try {
      const res = await fetch(`/api/notifications/${id}`, {
        method: 'DELETE',
        headers: { 'X-User-Id': currentUser.id, 'X-User-Role': currentUser.role }
      });
      if (res.ok) {
        await fetchUnreadCount();
        if (activeNotifSubTab === 'inbox') loadNotificationsInbox();
      }
    } catch (err) {
      console.warn("Archive error:", err);
    }
  }

  async function loadNotificationPreferences() {
    try {
      const res = await fetch('/api/notifications/preferences', {
        headers: { 'X-User-Id': currentUser.id, 'X-User-Role': currentUser.role }
      });
      if (!res.ok) return;
      const p = await res.json();

      document.getElementById('prefInApp').checked = !!p.in_app_enabled;
      document.getElementById('prefEmail').checked = !!p.email_enabled;
      document.getElementById('prefWhatsApp').checked = !!p.whatsapp_enabled;
      document.getElementById('prefSMS').checked = !!p.sms_enabled;

      const cats = p.categories || {};
      document.getElementById('prefCatTimetable').checked = cats.timetable !== false;
      document.getElementById('prefCatExam').checked = cats.examination !== false;
      document.getElementById('prefCatBooking').checked = cats.venue_booking !== false;
      document.getElementById('prefCatDisruption').checked = cats.disruption !== false;
      document.getElementById('prefCatApproval').checked = cats.approval !== false;

      document.getElementById('prefMinSeverity').value = p.min_severity || 'low';
    } catch (err) {
      console.warn("Preferences load error:", err);
    }
  }

  async function saveNotificationPreferences() {
    const payload = {
      in_app_enabled: document.getElementById('prefInApp').checked,
      email_enabled: document.getElementById('prefEmail').checked,
      whatsapp_enabled: document.getElementById('prefWhatsApp').checked,
      sms_enabled: document.getElementById('prefSMS').checked,
      categories: {
        timetable: document.getElementById('prefCatTimetable').checked,
        examination: document.getElementById('prefCatExam').checked,
        venue_booking: document.getElementById('prefCatBooking').checked,
        disruption: document.getElementById('prefCatDisruption').checked,
        approval: document.getElementById('prefCatApproval').checked
      },
      min_severity: document.getElementById('prefMinSeverity').value
    };

    try {
      const res = await fetch('/api/notifications/preferences', {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': currentUser.id,
          'X-User-Role': currentUser.role
        },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error("Failed to save preferences");
      alert("Notification preferences successfully updated!");
    } catch (err) {
      alert(`Error saving preferences: ${err.message}`);
    }
  }

  async function loadAdminNotificationDashboard() {
    if (currentUser.role !== 'admin') {
      const adminSub = document.getElementById('notifSubtabAdmin');
      if (adminSub) adminSub.innerHTML = `<div class="panel-card" style="padding:32px; text-align:center; color:#dc2626;">Access Restricted: Only Dean Academics (Admin) can inspect delivery logs and gateway health.</div>`;
      return;
    }

    try {
      const [sumRes, logsRes] = await Promise.all([
        fetch('/api/admin/notifications/summary', {
          headers: { 'X-User-Id': currentUser.id, 'X-User-Role': currentUser.role }
        }),
        fetch('/api/admin/notifications/delivery-logs?limit=50', {
          headers: { 'X-User-Id': currentUser.id, 'X-User-Role': currentUser.role }
        })
      ]);

      if (sumRes.ok) {
        const sumData = await sumRes.json();
        document.getElementById('adminMetricTotal').textContent = sumData.total_notifications || 0;
        document.getElementById('adminMetricDelivered').textContent = sumData.total_delivered || 0;
        document.getElementById('adminMetricFailed').textContent = sumData.total_failed || 0;
      }

      if (logsRes.ok) {
        const logs = await logsRes.json();
        const tbody = document.getElementById('adminLogsTableBody');
        if (!tbody) return;

        if (!logs || logs.length === 0) {
          tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:24px; color:#94a3b8;">No delivery attempts logged yet.</td></tr>';
          return;
        }

        const statusBadges = {
          delivered: '<span class="badge badge-success">DELIVERED</span>',
          failed: '<span class="badge badge-danger">FAILED</span>',
          skipped: '<span class="badge badge-neutral">SKIPPED (OPT-OUT)</span>',
          not_configured: '<span class="badge badge-warning">NOT CONFIGURED</span>',
          pending: '<span class="badge badge-info">PENDING</span>'
        };

        tbody.innerHTML = logs.map(l => `
          <tr>
            <td style="font-family:'JetBrains Mono', monospace; font-weight:600;">#${l.id}</td>
            <td><strong>${l.recipient_name}</strong><br><small style="color:#64748b;">${l.recipient_id}</small></td>
            <td><span class="badge badge-neutral">${l.channel.toUpperCase()}</span></td>
            <td>${statusBadges[l.status] || l.status}</td>
            <td>${l.title || l.notification_id}</td>
            <td>${l.attempt_count}</td>
            <td style="font-size:0.75rem; color:#64748b;">${l.sent_at}</td>
            <td style="font-size:0.75rem; color:${l.error_message ? '#dc2626' : '#64748b'};">${l.error_message || 'OK / Dispatched'}</td>
          </tr>
        `).join('');
      }
    } catch (err) {
      console.warn("Admin dashboard load error:", err);
    }
  }

  async function testCommunicationGateway() {
    const channel = document.getElementById('probeChannelSelect').value;
    const target = document.getElementById('probeTargetInput').value.trim();
    if (!target) {
      alert("Please enter a target email address or phone number.");
      return;
    }

    const resBox = document.getElementById('probeResultBox');
    resBox.style.display = 'block';
    resBox.textContent = `Dispatching live probe to ${channel} gateway (${target})...`;

    try {
      const res = await fetch('/api/admin/notifications/test', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Id': currentUser.id,
          'X-User-Role': currentUser.role
        },
        body: JSON.stringify({ channel, target })
      });
      const data = await res.json();
      resBox.innerHTML = `<strong>Result:</strong> ${data.status.toUpperCase()}<br><strong>Configured:</strong> ${data.configured}<br><strong>Details:</strong> ${data.details}`;
      resBox.style.color = data.status === 'delivered' ? '#15803d' : (data.status === 'not_configured' ? '#b45309' : '#dc2626');
      loadAdminNotificationDashboard();
    } catch (err) {
      resBox.textContent = `Error testing gateway: ${err.message}`;
      resBox.style.color = '#dc2626';
    }
  }

  function initNotificationWebSocket() {
    try {
      if (notifWs) {
        notifWs.close();
      }
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${proto}//${window.location.host}/api/notifications/ws?user_id=${currentUser.id}`;
      notifWs = new WebSocket(wsUrl);

      notifWs.onopen = function() {
        console.log("CIT Real-Time Notification Socket Connected.");
      };

      notifWs.onmessage = function(event) {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'NEW_NOTIFICATION') {
            fetchUnreadCount();
            if (activeNotifSubTab === 'inbox') loadNotificationsInbox();
          }
        } catch (e) {}
      };

      notifWs.onclose = function() {
        // Auto-reconnect after 8s
        setTimeout(initNotificationWebSocket, 8000);
      };
    } catch (e) {
      console.warn("WebSocket init error:", e);
    }
  }

  // =========================================================================
  // AI SCHEDULING ASSISTANT & DECISION EXPLAINABILITY JAVASCRIPT

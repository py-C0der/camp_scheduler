// CIT Campus Smart Venue Booking & Spectra Management Module
import { api } from './api';
import { BookingRequest, BookingTimeWindow } from './types';

declare const window: any;
declare const document: any;

  // =========================================================================
  let bkAllRequests = [];
  let bkActiveSummary = null;
  let bkSelectedBooking = null;

  async function loadBookingData() {
    try {
      // 1. Fetch summary
      const sumRes = await fetch('/api/bookings/summary');
      if (sumRes.ok) {
        bkActiveSummary = await sumRes.json();
        document.getElementById('bkStatTotal').textContent = bkActiveSummary.total_requests;
        document.getElementById('bkStatApproved').textContent = bkActiveSummary.approved_requests;
        document.getElementById('bkStatAlternatives').textContent = bkActiveSummary.alternative_offers;
        document.getElementById('bkStatRejected').textContent = bkActiveSummary.rejected_requests;
        document.getElementById('bkStatCancelled').textContent = bkActiveSummary.cancelled_requests;
        document.getElementById('bkStatInversions').textContent = bkActiveSummary.priority_inversions ? bkActiveSummary.priority_inversions.length : 0;
        document.getElementById('bkStatScore').textContent = (bkActiveSummary.booking_score || 0).toFixed(1);
        document.getElementById('bkStatScoreMax').textContent = `of ${(bkActiveSummary.max_possible_score || 85).toFixed(1)} max points`;
      }

      // 2. Fetch all bookings
      const bkRes = await fetch('/api/bookings?limit=100');
      if (bkRes.ok) {
        const data = await bkRes.json();
        bkAllRequests = data.bookings || [];
        renderBookingsTable(bkAllRequests);
      }

      // 3. Render Venue Availability Calendar
      renderVenueCalendarGrid();
    } catch (err) {
      console.error('Error loading bookings:', err);
    }
  }

  function renderBookingsTable(bookings) {
    const tbody = document.getElementById('bkRequestsTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!bookings || bookings.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:24px; color:#94a3b8;">No venue booking requests found matching filters.</td></tr>';
      return;
    }

    bookings.forEach(b => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid #f1f5f9';

      // Status pill styling
      let statusBadge = '<span class="badge" style="background:#f1f5f9; color:#475569;">Pending</span>';
      if (b.status === 'approved') {
        statusBadge = '<span class="badge" style="background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0;">Approved</span>';
      } else if (b.status === 'alternative_offered') {
        statusBadge = '<span class="badge" style="background:#fffbeb; color:#92400e; border:1px solid #fde68a;">Alternative</span>';
      } else if (b.status === 'rejected') {
        statusBadge = '<span class="badge" style="background:#fef2f2; color:#991b1b; border:1px solid #fecaca;">Rejected</span>';
      } else if (b.status === 'cancelled') {
        statusBadge = '<span class="badge" style="background:#f3f4f6; color:#6b7280; text-decoration:line-through;">Cancelled</span>';
      }

      // Timing display
      let timingStr = 'Any Window';
      if (b.assigned_room_id && b.assigned_day) {
        timingStr = `<b>${b.assigned_day}</b> P${b.assigned_start_period}–P${b.assigned_end_period}`;
      } else if (b.windows && b.windows.length > 0) {
        timingStr = `${b.windows[0].day} P${b.windows[0].from_period}–P${b.windows[0].to_period}`;
      }

      const roomStr = b.assigned_room_id ? `<span class="badge" style="background:#eff6ff; color:#1d4ed8; font-weight:700;">${b.assigned_room_id}</span>` : (b.requested_room || '<span style="color:#94a3b8;">--</span>');

      tr.innerHTML = `
        <td style="padding:10px 12px; font-weight:700; color:#1e293b;">${b.id}</td>
        <td style="padding:10px 12px; font-weight:600; color:#0f172a;">${b.title || b.id}</td>
        <td style="padding:10px 12px; color:#475569;"><span style="font-size:0.75rem; color:#64748b;">${b.role}</span><br>${b.requester || 'User'}</td>
        <td style="padding:10px 12px;"><span class="badge" style="background:#f1f5f9; color:#334155;">${b.effective_category || b.requested_category}</span></td>
        <td style="padding:10px 12px; color:#334155;">${timingStr}</td>
        <td style="padding:10px 12px; text-align:center; font-weight:600;">${b.attendance}</td>
        <td style="padding:10px 12px;">${roomStr}</td>
        <td style="padding:10px 12px;">${statusBadge}</td>
        <td style="padding:10px 12px; text-align:center;">
          <button class="btn btn-outline" style="padding:3px 8px; font-size:0.75rem;" onclick="inspectBooking('${b.id}')">Inspect</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function applyBookingFilters() {
    const q = (document.getElementById('bkFilterSearch').value || '').toLowerCase();
    const cat = document.getElementById('bkFilterCategory').value;
    const st = document.getElementById('bkFilterStatus').value;

    const filtered = bkAllRequests.filter(b => {
      const matchQ = !q || (b.title && b.title.toLowerCase().includes(q)) || (b.id && b.id.toLowerCase().includes(q)) || (b.requester && b.requester.toLowerCase().includes(q));
      const matchCat = !cat || b.requested_category === cat || b.effective_category === cat;
      const matchSt = !st || b.status === st;
      return matchQ && matchCat && matchSt;
    });
    renderBookingsTable(filtered);
  }

  async function inspectBooking(bookingId) {
    try {
      const res = await fetch(`/api/bookings/${bookingId}`);
      if (!res.ok) throw new Error('Failed to load booking details');
      const b = await res.json();
      bkSelectedBooking = b;

      document.getElementById('mdlBkTitle').textContent = b.title || b.id;
      document.getElementById('mdlBkId').textContent = `Request ID: ${b.id} | Submitted: ${b.submitted_at || 'N/A'}`;
      document.getElementById('mdlBkRequester').textContent = `${b.requester || 'User'} (${b.role})`;
      document.getElementById('mdlBkRawText').textContent = b.raw_text || 'No raw message provided';

      // Status badge
      const stEl = document.getElementById('mdlBkStatusBadge');
      stEl.textContent = (b.status || 'pending').toUpperCase();
      stEl.style.background = b.status === 'approved' ? '#059669' : (b.status === 'alternative_offered' ? '#d97706' : (b.status === 'rejected' ? '#dc2626' : '#6b7280'));
      stEl.style.color = '#fff';

      document.getElementById('mdlBkCategoryBadge').textContent = b.effective_category || b.requested_category;

      document.getElementById('mdlBkRoom').textContent = b.assigned_room_id || (b.requested_room ? `${b.requested_room} (Requested)` : 'Not Allocated');
      document.getElementById('mdlBkTiming').textContent = b.assigned_room_id ? `${b.assigned_day} P${b.assigned_start_period}–P${b.assigned_end_period}` : (b.windows && b.windows.length ? `${b.windows[0].day} P${b.windows[0].from_period}–P${b.windows[0].to_period}` : '--');
      document.getElementById('mdlBkAttendance').textContent = `${b.attendance} seats | ${b.duration_periods} periods`;

      document.getElementById('mdlBkReason').textContent = b.decision_reason || 'Request complies with priority ranking rules and room availability checks.';

      // Check self approval warning
      const currentUser = STATE && STATE.active_user ? STATE.active_user : { id: 'admin_1', role: 'admin' };
      const isSelf = (b.created_by && b.created_by === currentUser.id) || (b.requester && currentUser.name && b.requester.toLowerCase().includes(currentUser.name.toLowerCase()));
      document.getElementById('selfApprovalWarning').style.display = isSelf ? 'block' : 'none';
      document.getElementById('btnMdlApprove').disabled = isSelf;

      // Handle alternatives display
      const altBox = document.getElementById('mdlBkAlternativesBox');
      const altList = document.getElementById('mdlBkAlternativesList');
      if (b.alternatives && b.alternatives.length > 0) {
        altBox.style.display = 'block';
        altList.innerHTML = '';
        b.alternatives.forEach(alt => {
          const div = document.createElement('div');
          div.style.cssText = 'display:flex; justify-content:space-between; align-items:center; background:#fff; border:1px solid #cbd5e1; border-radius:4px; padding:8px 12px; margin-bottom:6px; font-size:0.78rem;';
          div.innerHTML = `
            <div>
              <b>${alt.room_id}</b> on <b>${alt.day}</b> (P${alt.start_period}–P${alt.end_period}) | Cap: ${alt.capacity} seats<br>
              <span style="color:#64748b;">${alt.reason}</span>
            </div>
            <button class="btn btn-outline" style="padding:3px 8px; font-size:0.72rem; color:#059669; border-color:#059669;" onclick="acceptAlternativeOffer(${alt.id})">Accept Slot</button>
          `;
          altList.appendChild(div);
        });
      } else {
        altBox.style.display = 'none';
      }

      openModal('bookingDetailModal');
    } catch (err) {
      alert(`Error loading booking: ${err.message}`);
    }
  }

  async function triggerApproveBooking() {
    if (!bkSelectedBooking) return;
    try {
      const res = await fetch(`/api/bookings/${bkSelectedBooking.id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Approval failed');
      }
      alert(`Booking ${bkSelectedBooking.id} approved successfully!`);
      closeModal('bookingDetailModal');
      loadBookingData();
    } catch (err) {
      alert(`Approval error: ${err.message}`);
    }
  }

  async function triggerRejectBooking() {
    if (!bkSelectedBooking) return;
    const reason = prompt('Please enter the mandatory explanation for rejecting this request:');
    if (!reason || !reason.strip()) return;

    try {
      const res = await fetch(`/api/bookings/${bkSelectedBooking.id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Rejection failed');
      }
      alert(`Booking ${bkSelectedBooking.id} rejected.`);
      closeModal('bookingDetailModal');
      loadBookingData();
    } catch (err) {
      alert(`Rejection error: ${err.message}`);
    }
  }

  async function triggerCancelBooking() {
    if (!bkSelectedBooking) return;
    if (!confirm(`Are you sure you want to cancel booking ${bkSelectedBooking.id}?`)) return;

    try {
      const res = await fetch(`/api/bookings/${bkSelectedBooking.id}/cancel`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Cancelled by user from portal' })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Cancellation failed');
      }
      alert(`Booking ${bkSelectedBooking.id} cancelled. Room capacity released.`);
      closeModal('bookingDetailModal');
      loadBookingData();
    } catch (err) {
      alert(`Cancellation error: ${err.message}`);
    }
  }

  async function acceptAlternativeOffer(altId) {
    if (!bkSelectedBooking) return;
    try {
      const res = await fetch(`/api/bookings/${bkSelectedBooking.id}/accept-alternative`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ alternative_id: altId })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to accept alternative');
      }
      alert(`Alternative slot accepted for ${bkSelectedBooking.id}!`);
      closeModal('bookingDetailModal');
      loadBookingData();
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  async function runSpectraAutoDecide() {
    const btn = document.getElementById('btnAutoDecide');
    btn.disabled = true;
    btn.innerHTML = '<span>&#9881;</span> Resolving Priorities...';
    try {
      const res = await fetch('/api/bookings/decide-all', { method: 'POST' });
      if (!res.ok) throw new Error('Failed to resolve bookings');
      const data = await res.json();
      alert(`Spectra-week auto resolution complete!\nApproved: ${data.stats.approved}\nAlternatives: ${data.stats.alternatives}\nRejected: ${data.stats.rejected}\nScore: ${data.booking_score}`);
      loadBookingData();
    } catch (err) {
      alert(`Auto-decide error: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>&#9881;</span> Run Spectra Auto-Decide';
    }
  }

  // Dual-mode New Booking Logic
  function openNewBookingModal() {
    switchBookingMode('ai');
    openModal('newBookingModal');
  }

  function switchBookingMode(mode) {
    const aiTab = document.getElementById('tabBtnAiBooking');
    const manualTab = document.getElementById('tabBtnManualBooking');
    const aiSec = document.getElementById('bookingModeAi');
    const manualSec = document.getElementById('bookingModeManual');

    if (mode === 'ai') {
      aiTab.style.background = '#2563eb';
      aiTab.style.color = '#fff';
      manualTab.style.background = 'transparent';
      manualTab.style.color = '#64748b';
      aiSec.style.display = 'block';
      manualSec.style.display = 'none';
    } else {
      manualTab.style.background = '#2563eb';
      manualTab.style.color = '#fff';
      aiTab.style.background = 'transparent';
      aiTab.style.color = '#64748b';
      manualSec.style.display = 'block';
      aiSec.style.display = 'none';
    }
  }

  function setAiBookingSample(num) {
    const input = document.getElementById('aiBookingInput');
    if (num === 1) {
      input.value = "Need auditorium for robotics competition on Friday from 10 AM to 1 PM for around 200 students.";
    } else if (num === 2) {
      input.value = "Kal afternoon ek seminar hall chahiye, guest lecture ke liye, around 80 students.";
    } else if (num === 3) {
      input.value = "Computer lab book karna hai for coding hackathon, Saturday morning, 60 participants.";
    }
  }

  async function parseAiBookingRequest() {
    const text = (document.getElementById('aiBookingInput').value || '').trim();
    if (!text) {
      alert('Please enter a booking request in plain English or Hinglish.');
      return;
    }

    const btn = document.getElementById('btnParseAi');
    btn.disabled = true;
    btn.innerHTML = '<span>&#10024;</span> Extracting...';

    try {
      const res = await fetch('/api/bookings/parse', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text })
      });
      if (!res.ok) throw new Error('Failed to parse message');
      const draft = await res.json();

      document.getElementById('aiDraftContainer').style.display = 'block';
      const ext = draft.extracted || {};
      document.getElementById('aiDraftTitle').value = ext.title || 'Campus Event';
      document.getElementById('aiDraftCategory').value = ext.requested_category || 'club_event';
      document.getElementById('aiDraftDay').value = ext.detected_day || 'FRI';
      document.getElementById('aiDraftDuration').value = ext.duration_periods || 2;
      document.getElementById('aiDraftAttendance').value = ext.attendance || 60;
      if (ext.room_types && ext.room_types.length > 0) {
        document.getElementById('aiDraftRoomType').value = ext.room_types[0];
      }

      // Clarifications box
      const clarBox = document.getElementById('aiClarificationBox');
      const badge = document.getElementById('aiCompletenessBadge');
      if (!draft.is_complete && draft.clarification_questions && draft.clarification_questions.length > 0) {
        badge.textContent = 'Clarification Needed';
        badge.style.background = '#f59e0b';
        clarBox.style.display = 'block';
        clarBox.innerHTML = `<b>Follow-up Clarification:</b><br>${draft.clarification_questions.join('<br>')}`;
      } else {
        badge.textContent = 'Complete';
        badge.style.background = '#10b981';
        clarBox.style.display = 'none';
      }
    } catch (err) {
      alert(`AI Extraction Error: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<span>&#10024;</span> Parse &amp; Extract Fields';
    }
  }

  async function submitAiDraftBooking() {
    const title = document.getElementById('aiDraftTitle').value.trim();
    const cat = document.getElementById('aiDraftCategory').value;
    const day = document.getElementById('aiDraftDay').value;
    const dur = parseInt(document.getElementById('aiDraftDuration').value) || 2;
    const att = parseInt(document.getElementById('aiDraftAttendance').value) || 50;
    const rtype = document.getElementById('aiDraftRoomType').value;
    const raw = document.getElementById('aiBookingInput').value;

    const payload = {
      title: title,
      requested_category: cat,
      attendance: att,
      duration_periods: dur,
      room_types: [rtype],
      windows: [{ day: day, from_period: 4, to_period: 4 + dur - 1 }],
      needs: [],
      raw_text: raw
    };

    try {
      const res = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Submission failed');
      }
      alert('Booking request submitted successfully! It is now pending admin/priority evaluation.');
      closeModal('newBookingModal');
      loadBookingData();
    } catch (err) {
      alert(`Submission error: ${err.message}`);
    }
  }

  async function submitManualBookingForm() {
    const title = document.getElementById('manualBkTitle').value.trim();
    if (!title) {
      alert('Event title is required.');
      return;
    }
    const cat = document.getElementById('manualBkCategory').value;
    const att = parseInt(document.getElementById('manualBkAttendance').value) || 50;
    const day = document.getElementById('manualBkDay').value;
    const sp = parseInt(document.getElementById('manualBkStartPeriod').value) || 3;
    const dur = parseInt(document.getElementById('manualBkDuration').value) || 2;
    const rtype = document.getElementById('manualBkRoomType').value;

    const needs = [];
    if (document.getElementById('needProjector').checked) needs.push('projector');
    if (document.getElementById('needAudio').checked) needs.push('pa_system');
    if (document.getElementById('needComputers').checked) needs.push('computers');
    if (document.getElementById('needStage').checked) needs.push('stage');

    const payload = {
      title: title,
      requested_category: cat,
      attendance: att,
      duration_periods: dur,
      room_types: [rtype],
      windows: [{ day: day, from_period: sp, to_period: sp + dur - 1 }],
      needs: needs,
      raw_text: `Manual submission: ${title}`
    };

    try {
      const res = await fetch('/api/bookings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Submission failed');
      }
      alert('Manual booking submitted successfully!');
      closeModal('newBookingModal');
      loadBookingData();
    } catch (err) {
      alert(`Submission error: ${err.message}`);
    }
  }

  // Interactive Venue Availability Matrix
  async function renderVenueCalendarGrid() {
    const tbody = document.getElementById('bkVenueCalendarBody');
    if (!tbody) return;
    const day = document.getElementById('bkCalDayFilter').value || 'MON';
    tbody.innerHTML = '<tr><td colspan="16" style="text-align:center; padding:16px;">Loading venue occupancy...</td></tr>';

    try {
      // 19 authorized campus event venues
      const rooms = [
        { id: 'AUD', name: 'Main Auditorium', cap: 500 },
        { id: 'OAT', name: 'Open Air Theatre', cap: 600 },
        { id: 'SH-1', name: 'Seminar Hall 1', cap: 120 },
        { id: 'SH-2', name: 'Seminar Hall 2', cap: 120 },
        { id: 'LH-1', name: 'Lecture Hall 1', cap: 120 },
        { id: 'LH-2', name: 'Lecture Hall 2', cap: 120 },
        { id: 'LH-3', name: 'Lecture Hall 3', cap: 120 },
        { id: 'LH-4', name: 'Lecture Hall 4', cap: 120 },
        { id: 'LH-5', name: 'Lecture Hall 5', cap: 90 },
        { id: 'LH-6', name: 'Lecture Hall 6', cap: 90 },
        { id: 'CR-101', name: 'Classroom 101', cap: 60 },
        { id: 'CR-102', name: 'Classroom 102', cap: 60 },
        { id: 'CR-103', name: 'Classroom 103', cap: 60 },
        { id: 'CR-104', name: 'Classroom 104', cap: 60 },
        { id: 'CR-201', name: 'Classroom 201', cap: 60 },
        { id: 'LAB-CS1', name: 'Computer Lab 1', cap: 70 },
        { id: 'LAB-CS2', name: 'Computer Lab 2', cap: 70 },
        { id: 'LAB-EE1', name: 'Electronics Lab 1', cap: 50 },
        { id: 'LAB-ME1', name: 'Mechanical Lab 1', cap: 50 }
      ];

      // Fetch conflicts/occupancy from backend
      const res = await fetch(`/api/bookings/conflicts?day=${day}`);
      const data = res.ok ? await res.json() : { conflicts: [] };
      const occMap = {};
      (data.conflicts || []).forEach(c => {
        occMap[`${c.room_id}_${c.period}`] = c;
      });

      tbody.innerHTML = '';
      rooms.forEach(r => {
        const tr = document.createElement('tr');
        tr.style.borderBottom = '1px solid #f1f5f9';

        let html = `
          <td style="padding:6px 10px; font-weight:700; color:#1e293b;">${r.id}<br><span style="font-size:0.68rem; color:#64748b; font-weight:400;">${r.name}</span></td>
          <td style="padding:6px 10px; text-align:center; color:#64748b;">${r.cap}</td>
        `;

        // Periods 1..4
        for (let p = 1; p <= 4; p++) {
          html += getSlotCellHtml(occMap[`${r.id}_${p}`]);
        }

        // Lunch break
        html += '<td style="background:#f8fafc; border-left:1px dashed #cbd5e1; border-right:1px dashed #cbd5e1; text-align:center; font-size:0.65rem; color:#94a3b8;">--</td>';

        // Periods 5..13
        for (let p = 5; p <= 13; p++) {
          html += getSlotCellHtml(occMap[`${r.id}_${p}`]);
        }

        tr.innerHTML = html;
        tbody.appendChild(tr);
      });
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="16" style="color:#dc2626; text-align:center; padding:12px;">Error: ${err.message}</td></tr>`;
    }
  }

  function getSlotCellHtml(occ) {
    if (!occ) {
      return '<td style="padding:3px; text-align:center;"><div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:3px; height:24px;" title="Available"></div></td>';
    }
    if (occ.type === 'maintenance') {
      return '<td style="padding:3px; text-align:center;"><div style="background:#fef2f2; border:1px solid #f87171; color:#b91c1c; border-radius:3px; height:24px; font-size:0.65rem; display:flex; align-items:center; justify-content:center; font-weight:700;" title="Scheduled Maintenance">Maint</div></td>';
    }
    if (occ.type === 'booking') {
      return `<td style="padding:3px; text-align:center;"><div style="background:#ecfdf5; border:1px solid #34d399; color:#065f46; border-radius:3px; height:24px; font-size:0.65rem; display:flex; align-items:center; justify-content:center; font-weight:700;" title="Approved Event Booking ${occ.entity || ''}">Event</div></td>`;
    }
    if (occ.type === 'teaching_session') {
      return `<td style="padding:3px; text-align:center;"><div style="background:#eff6ff; border:1px solid #60a5fa; color:#1e40af; border-radius:3px; height:24px; font-size:0.65rem; display:flex; align-items:center; justify-content:center; font-weight:600;" title="Class ${occ.entity || ''}">Class</div></td>`;
    }
    return '<td style="padding:3px; text-align:center;"><div style="background:#f1f5f9; height:24px; border-radius:3px;"></div></td>';
  }


  // =========================================================================
  // DISRUPTION MANAGEMENT AND RESCHEDULING ENGINE JAVASCRIPT

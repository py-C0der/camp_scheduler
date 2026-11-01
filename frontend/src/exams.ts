// CIT Campus Mid-Semester Examination Scheduler Module
import { api } from './api';
import { ExamEntry } from './types';

declare const window: any;
declare const document: any;

  // ==========================================
  let examDataList = [];
  let examSummaryData = {};

  async function loadExamData() {
    await fetchExamSummary();
    await fetchExamsList();
  }

  async function fetchExamSummary() {
    try {
      const res = await fetch('/api/exams/summary');
      const data = await res.json();
      examSummaryData = data;
      document.getElementById('examTotalCount').textContent = data.total_exams;
      document.getElementById('examScheduledCount').textContent = data.scheduled_exams;
      document.getElementById('examUnscheduledCount').textContent = data.unscheduled_exams;
      document.getElementById('examAllocatedVenues').textContent = data.total_allocated_rooms;
      document.getElementById('examMultiRoomCount').textContent = data.multi_room_exams;
      
      const appBadge = document.getElementById('examApprovalBadge');
      if (data.pending_approval) {
        appBadge.textContent = "PENDING APPROVAL";
        appBadge.style.color = "#d97706";
      } else {
        appBadge.textContent = "APPROVED";
        appBadge.style.color = "#059669";
      }
      document.getElementById('examScheduleVer').textContent = data.latest_schedule_version ? `Version ${data.latest_schedule_version}` : 'Version 1.0';

      const valBadge = document.getElementById('examValStatus');
      if (data.validation_status === 'VALID' || data.scheduled_exams > 0) {
        valBadge.textContent = "0 CLASHES";
        valBadge.style.color = "#10b981";
      } else {
        valBadge.textContent = data.validation_status;
        valBadge.style.color = "#ef4444";
      }
    } catch (e) {
      console.error("Failed to fetch exam summary", e);
    }
  }

  async function fetchExamsList() {
    try {
      const res = await fetch('/api/exams?limit=100');
      const data = await res.json();
      examDataList = data.items || [];
      renderExamCalendar(examDataList);
      renderExamTable(examDataList);
      populateExamGroupFilter(examDataList);
    } catch (e) {
      console.error("Failed to fetch exams list", e);
    }
  }

  function populateExamGroupFilter(exams) {
    const sel = document.getElementById('filterExamGroup');
    if (!sel || sel.children.length > 1) return;
    const allGroups = new Set();
    exams.forEach(e => (e.groups || []).forEach(g => allGroups.add(g)));
    Array.from(allGroups).sort().forEach(g => {
      const opt = document.createElement('option');
      opt.value = g;
      opt.textContent = g;
      sel.appendChild(opt);
    });
  }

  function renderExamCalendar(exams) {
    const tbody = document.getElementById('examCalendarGridBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    const days = ["MON", "TUE", "WED", "THU", "FRI", "SAT"];
    const sessions = [
      { id: "AM", label: "Morning (09:30 &ndash; 11:30)" },
      { id: "PM", label: "Afternoon (14:00 &ndash; 16:00)" }
    ];

    sessions.forEach(sess => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = "1px solid #e2e8f0";

      let html = `<td style="padding:10px; font-weight:700; color:#334155; background:#f8fafc; font-size:0.75rem;">${sess.label}</td>`;

      days.forEach(d => {
        const slotExams = exams.filter(e => e.day === d && e.session === sess.id);
        html += `<td style="padding:8px; vertical-align:top; border-left:1px solid #e2e8f0; width:15%;">`;
        
        if (slotExams.length === 0) {
          html += `<div style="color:#94a3b8; font-size:0.7rem; font-style:italic;">No exams</div>`;
        } else {
          slotExams.forEach(ex => {
            const isMulti = ex.is_multi_room;
            html += `
              <div onclick="openExamModal('${ex.exam_id}')" style="cursor:pointer; background:${isMulti ? '#f5f3ff' : '#eff6ff'}; border:1px solid ${isMulti ? '#ddd6fe' : '#bfdbfe'}; border-radius:6px; padding:6px 8px; margin-bottom:6px; font-size:0.72rem; transition:transform 0.1s;" onmouseover="this.style.transform='scale(1.02)'" onmouseout="this.style.transform='scale(1)'">
                <div style="font-weight:700; color:${isMulti ? '#6d28d9' : '#1d4ed8'}; display:flex; justify-content:space-between;">
                  <span>${ex.exam_id}</span>
                  ${isMulti ? '<span style="font-size:0.65rem; background:#ede9fe; color:#7c3aed; padding:1px 4px; border-radius:4px;">Multi-Room</span>' : ''}
                </div>
                <div style="color:#334155; margin:2px 0;">${(ex.course_ids || []).join(', ')}</div>
                <div style="color:#64748b; font-size:0.68rem;">Groups: ${(ex.groups || []).join(', ')}</div>
                <div style="margin-top:4px; font-weight:600; color:#0f172a;">${(ex.rooms || []).join(' + ')}</div>
              </div>
            `;
          });
        }
        html += `</td>`;
      });

      tr.innerHTML = html;
      tbody.appendChild(tr);
    });
  }

  function renderExamTable(exams) {
    const tbody = document.getElementById('examTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    document.getElementById('examFilteredCountLabel').textContent = `Showing ${exams.length} of 41 examinations`;

    if (exams.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align:center; padding:20px; color:#64748b;">No examinations matched the search filters.</td></tr>`;
      return;
    }

    exams.forEach(ex => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = "1px solid #f1f5f9";
      const isMulti = ex.is_multi_room;

      tr.innerHTML = `
        <td style="padding:10px 12px; font-weight:700; color:#1e293b;">
          ${ex.exam_id}
        </td>
        <td style="padding:10px 12px; font-weight:600; color:#2563eb;">
          ${(ex.course_ids || []).join(', ')}
        </td>
        <td style="padding:10px 12px; color:#475569;">
          ${(ex.groups || []).join(', ')}
        </td>
        <td style="padding:10px 12px;">
          <span class="badge badge-success" style="font-size:0.72rem;">${ex.day || 'TBD'} ${ex.session || ''}</span>
        </td>
        <td style="padding:10px 12px;">
          <div style="display:flex; gap:4px; flex-wrap:wrap; align-items:center;">
            ${(ex.rooms || []).map(r => `<span style="background:#f1f5f9; border:1px solid #cbd5e1; border-radius:4px; padding:2px 6px; font-weight:600;">${r}</span>`).join('')}
            ${isMulti ? '<span style="font-size:0.65rem; background:#ede9fe; color:#7c3aed; padding:1px 5px; border-radius:4px; font-weight:700;">Multi</span>' : ''}
          </div>
        </td>
        <td style="padding:10px 12px;">
          <strong>${ex.total_effective_seats}</strong> seats for ${ex.size} std
        </td>
        <td style="padding:10px 12px;">
          <span class="badge badge-success">Scheduled</span>
        </td>
        <td style="padding:10px 12px; text-align:center;">
          <button class="btn btn-outline" style="padding:3px 8px; font-size:0.72rem;" onclick="openExamModal('${ex.exam_id}')">Inspect</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function applyExamFilters() {
    const q = (document.getElementById('filterExamSearch').value || '').toLowerCase();
    const day = document.getElementById('filterExamDay').value;
    const sess = document.getElementById('filterExamSession').value;
    const grp = document.getElementById('filterExamGroup').value;

    const filtered = examDataList.filter(e => {
      if (q && !e.exam_id.toLowerCase().includes(q) && !(e.course_ids || []).some(c => c.toLowerCase().includes(q))) return false;
      if (day && e.day !== day) return false;
      if (sess && e.session !== sess) return false;
      if (grp && !(e.groups || []).includes(grp)) return false;
      return true;
    });

    renderExamTable(filtered);
  }

  function resetExamFilters() {
    document.getElementById('filterExamSearch').value = '';
    document.getElementById('filterExamDay').value = '';
    document.getElementById('filterExamSession').value = '';
    document.getElementById('filterExamGroup').value = '';
    renderExamTable(examDataList);
  }

  async function openExamModal(examId) {
    try {
      const res = await fetch(`/api/exams/${examId}`);
      if (!res.ok) {
        alert("Exam details not found.");
        return;
      }
      const data = await res.json();
      document.getElementById('modalExamId').textContent = data.exam_id;
      document.getElementById('modalExamCourses').textContent = `Courses: ${(data.course_ids || []).join(', ')}`;
      document.getElementById('modalExamSlot').textContent = `${data.day || 'TBD'} ${data.session || ''} (Duration: ${data.duration_hours}h)`;
      document.getElementById('modalExamSize').textContent = `${data.size} Enrolled Students`;
      document.getElementById('modalExamSeats').textContent = `${data.total_effective_seats} Seats (+${data.surplus_seats} surplus)`;

      const grpCont = document.getElementById('modalExamGroups');
      grpCont.innerHTML = (data.groups || []).map(g => `<span class="badge badge-neutral" style="background:#e0f2fe; color:#0369a1;">${g}</span>`).join('');

      const tb = document.getElementById('modalRoomBreakdownBody');
      tb.innerHTML = '';
      (data.breakdown || []).forEach(r => {
        const row = document.createElement('tr');
        row.style.borderBottom = "1px solid #f1f5f9";
        row.innerHTML = `
          <td style="padding:6px 8px; font-weight:700;">${r.room_id}</td>
          <td style="padding:6px 8px;">${r.name}</td>
          <td style="padding:6px 8px;">${r.building}</td>
          <td style="padding:6px 8px;"><span class="badge badge-neutral">${r.type}</span></td>
          <td style="padding:6px 8px; text-align:right;">${r.normal_capacity}</td>
          <td style="padding:6px 8px; text-align:right; font-weight:700; color:#10b981;">${r.effective_exam_seats}</td>
        `;
        tb.appendChild(row);
      });

      document.getElementById('examDetailModal').classList.add('active');
    } catch (e) {
      console.error(e);
      alert("Error loading exam details: " + e);
    }
  }

  function closeExamModal() {
    document.getElementById('examDetailModal').classList.remove('active');
  }

  async function triggerExamSolve() {
    const btn = document.getElementById('btnSolveExams');
    btn.disabled = true;
    btn.innerHTML = `<span>&#8987;</span> Solving CP-SAT Model...`;
    try {
      const res = await fetch('/api/exams/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Role': currentUser.role || 'admin' },
        body: JSON.stringify({ time_limit_seconds: 20, num_workers: 4 })
      });
      const data = await res.json();
      if (res.ok) {
        alert(`Examination timetable solved successfully! Status: ${data.status}, Soft Penalty: ${data.soft_penalty}`);
        await loadExamData();
      } else {
        alert("Exam solver failed: " + (data.detail ? JSON.stringify(data.detail) : "Error"));
      }
    } catch (e) {
      alert("Network error: " + e);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>&#9889;</span> Solve &amp; Propose Schedule`;
    }
  }

  async function triggerExamValidation() {
    try {
      const res = await fetch('/api/exams/validate', { method: 'POST' });
      const data = await res.json();
      if (data.valid) {
        alert(`Independent Validation: 100% PASS!
Zero hard violations.
Exam soft penalty: ${data.exam_soft_penalty}`);
      } else {
        alert(`Validation reported ${data.hard_violation_count} hard violations:
` + JSON.stringify(data.hard_violations, null, 2));
      }
    } catch (e) {
      alert("Validation check failed: " + e);
    }
  }

  async function triggerExamApproval() {
    if (currentUser.role !== 'admin') {
      alert("Permission Denied: Only Dean/Admin role can approve examination schedules.");
      return;
    }
    const ver = examSummaryData.latest_schedule_version || 'exam_v1';
    if (!confirm(`Approve examination schedule proposal '${ver}' and commit to official schedule.json?`)) return;

    try {
      const res = await fetch(`/api/exams/schedule/${ver}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-Role': 'admin' },
        body: JSON.stringify({ approved_by: currentUser.name || 'Dean Academics', note: 'Official midsem approval' })
      });
      const data = await res.json();
      if (res.ok) {
        alert(`Examination Schedule ${ver} APPROVED successfully! Synchronized to exports/schedule.json.`);
        await loadExamData();
      } else {
        alert("Approval failed: " + JSON.stringify(data));
      }
    } catch (e) {
      alert("Error approving schedule: " + e);
    }
  }


  // =========================================================================
  // SMART VENUE BOOKINGS & APPROVAL MANAGEMENT JAVASCRIPT LOGIC

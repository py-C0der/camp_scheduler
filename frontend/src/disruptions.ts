// CIT Campus Disruption Engine & Rescheduling Module
import { api } from './api';
import { DisruptionReport, RescheduleProposal } from './types';

declare const window: any;
declare const document: any;

  // =========================================================================
  let disStagedChanges = [];
  let disSelectedProposalId = null;

  async function loadDisruptionData() {
    try {
      // 1. Fetch dashboard summary
      const sumRes = await fetch('/api/disruptions/summary');
      if (sumRes.ok) {
        const sum = await sumRes.json();
        document.getElementById('disStatTotal').textContent = sum.total_disruptions;
        document.getElementById('disStatOpen').textContent = sum.open_disruptions + sum.analyzing_disruptions;
        document.getElementById('disStatProposals').textContent = sum.proposals_awaiting_approval;
        document.getElementById('disStatApproved').textContent = sum.approved_reschedulings;
        document.getElementById('disStatActiveVersion').textContent = sum.active_timetable_version;
      }

      // 2. Fetch disruptions list
      const disRes = await fetch('/api/disruptions');
      if (disRes.ok) {
        const disList = await disRes.json();
        renderDisruptionsTable(disList);
      }

      // 3. Fetch proposals list
      const propRes = await fetch('/api/rescheduling-proposals');
      if (propRes.ok) {
        const propList = await propRes.json();
        renderProposalsTable(propList);
      }

      // 4. Fetch timetable versions
      const verRes = await fetch('/api/timetable-versions');
      if (verRes.ok) {
        const verList = await verRes.json();
        renderVersionsTable(verList);
      }
    } catch (err) {
      console.error('Error loading disruptions:', err);
    }
  }

  function renderDisruptionsTable(disruptions) {
    const tbody = document.getElementById('disTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!disruptions || disruptions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:#94a3b8;">No disruption reports found.</td></tr>';
      return;
    }

    disruptions.forEach(d => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid #f1f5f9';

      let statusBadge = '<span class="badge" style="background:#f1f5f9; color:#475569;">Reported</span>';
      if (d.status === 'approved') {
        statusBadge = '<span class="badge" style="background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0;">Approved</span>';
      } else if (d.status === 'proposal_generated') {
        statusBadge = '<span class="badge" style="background:#f5f3ff; color:#6d28d9; border:1px solid #ddd6fe;">Proposed</span>';
      } else if (d.status === 'analyzing') {
        statusBadge = '<span class="badge" style="background:#fffbeb; color:#92400e; border:1px solid #fde68a;">Analyzing</span>';
      } else if (d.status === 'rejected') {
        statusBadge = '<span class="badge" style="background:#fef2f2; color:#991b1b; border:1px solid #fecaca;">Rejected</span>';
      }

      const changesCount = d.changes ? d.changes.length : 0;
      const reportedAtStr = d.reported_at ? d.reported_at.substring(0, 16).replace('T', ' ') : '--';

      tr.innerHTML = `
        <td style="padding:10px 12px; font-weight:700; color:#1e293b;">${d.id}</td>
        <td style="padding:10px 12px;"><b>${d.title || d.id}</b><br><span style="font-size:0.75rem; color:#64748b;">${d.description}</span></td>
        <td style="padding:10px 12px;"><span class="badge" style="background:#f1f5f9; color:#334155;">${changesCount} items</span></td>
        <td style="padding:10px 12px; color:#475569;">${d.reported_by || 'Admin'}</td>
        <td style="padding:10px 12px; color:#64748b; font-size:0.75rem;">${reportedAtStr}</td>
        <td style="padding:10px 12px;">${statusBadge}</td>
        <td style="padding:10px 12px; text-align:center;">
          <button class="btn btn-outline" style="padding:3px 8px; font-size:0.75rem; margin-right:4px;" onclick="triggerImpactAnalysis('${d.id}')">Analyze</button>
          <button class="btn btn-primary" style="padding:3px 8px; font-size:0.75rem;" onclick="triggerReschedule('${d.id}')">Reschedule</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderProposalsTable(proposals) {
    const tbody = document.getElementById('propTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!proposals || proposals.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center; padding:20px; color:#94a3b8;">No rescheduling proposals generated yet.</td></tr>';
      return;
    }

    proposals.forEach(p => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid #f1f5f9';

      let statusBadge = '<span class="badge" style="background:#f5f3ff; color:#6d28d9; border:1px solid #ddd6fe;">Proposed</span>';
      if (p.status === 'approved') {
        statusBadge = '<span class="badge" style="background:#ecfdf5; color:#065f46; border:1px solid #a7f3d0;">Approved</span>';
      } else if (p.status === 'rejected') {
        statusBadge = '<span class="badge" style="background:#fef2f2; color:#991b1b; border:1px solid #fecaca;">Rejected</span>';
      }

      const violBadge = p.hard_violations_count === 0 ? '<span class="badge" style="background:#ecfdf5; color:#065f46;">0 Viol</span>' : `<span class="badge" style="background:#fef2f2; color:#dc2626;">${p.hard_violations_count} Viol</span>`;

      tr.innerHTML = `
        <td style="padding:10px 12px; font-weight:700; color:#1e293b;">${p.id}</td>
        <td style="padding:10px 12px; color:#475569;">${p.disruption_id}</td>
        <td style="padding:10px 12px;"><span class="badge" style="background:#eff6ff; color:#1d4ed8; font-weight:700;">${p.target_timetable_version}</span></td>
        <td style="padding:10px 12px; font-weight:700; color:#b91c1c;">${p.sessions_moved}</td>
        <td style="padding:10px 12px; color:#d97706;">${p.time_changed}</td>
        <td style="padding:10px 12px; color:#2563eb;">${p.room_only_changed}</td>
        <td style="padding:10px 12px;">${violBadge}</td>
        <td style="padding:10px 12px;">${statusBadge}</td>
        <td style="padding:10px 12px; text-align:center;">
          <button class="btn btn-outline" style="padding:3px 8px; font-size:0.75rem;" onclick="viewProposalComparison('${p.id}')">Inspect Diff</button>
        </td>
      `;
      tbody.appendChild(tr);
    });
  }

  function renderVersionsTable(versions) {
    const tbody = document.getElementById('verTableBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (!versions || versions.length === 0) {
      tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:20px; color:#94a3b8;">No timetable versions recorded.</td></tr>';
      return;
    }

    versions.forEach(v => {
      const tr = document.createElement('tr');
      tr.style.borderBottom = '1px solid #f1f5f9';

      const statusBadge = v.is_active ? '<span class="badge" style="background:#10b981; color:#fff; font-weight:700;">ACTIVE</span>' : '<span class="badge" style="background:#f1f5f9; color:#64748b;">Archived</span>';

      tr.innerHTML = `
        <td style="padding:10px 12px; font-weight:700; color:#1e293b;">${v.id}</td>
        <td style="padding:10px 12px; font-weight:600; color:#0f172a;">${v.name}</td>
        <td style="padding:10px 12px;">${statusBadge}</td>
        <td style="padding:10px 12px; color:#475569;"><span class="badge" style="background:#f8fafc; color:#334155;">${v.source}</span></td>
        <td style="padding:10px 12px; font-weight:600;">${v.sessions_count}</td>
        <td style="padding:10px 12px; color:#64748b;">${v.sessions_moved_from_baseline} sessions</td>
        <td style="padding:10px 12px; color:#64748b; font-size:0.75rem;">${v.created_at ? v.created_at.substring(0, 16).replace('T', ' ') : '--'}</td>
      `;
      tbody.appendChild(tr);
    });
  }

  // Trigger impact analysis
  async function triggerImpactAnalysis(disruptionId) {
    try {
      const res = await fetch(`/api/disruptions/${disruptionId}/impact`);
      if (!res.ok) throw new Error('Impact analysis failed');
      const impact = await res.json();

      document.getElementById('disImpactCard').style.display = 'block';
      document.getElementById('disImpactSummaryText').textContent = impact.summary_text;
      document.getElementById('disImpactSessCount').textContent = impact.total_affected_sessions;
      document.getElementById('disImpactFacList').textContent = (impact.affected_faculty || []).map(f => f.id).join(', ') || 'None';
      document.getElementById('disImpactRoomList').textContent = (impact.affected_rooms || []).map(r => r.id).join(', ') || 'None';
      document.getElementById('disImpactGrpList').textContent = (impact.affected_student_groups || []).join(', ') || 'None';

      const tbl = document.getElementById('disImpactSessionsTableContainer');
      if (impact.directly_affected_sessions && impact.directly_affected_sessions.length > 0) {
        let html = '<table style="width:100%; border-collapse:collapse; font-size:0.75rem;"><tr style="background:#fff7ed; text-align:left;"><th style="padding:6px;">Session</th><th>Course</th><th>Faculty</th><th>Room</th><th>Day & Period</th><th>Conflict Reason</th></tr>';
        impact.directly_affected_sessions.forEach(s => {
          html += `<tr style="border-bottom:1px solid #fed7aa;"><td style="padding:6px; font-weight:700;">${s.session_id}</td><td>${s.course_id}</td><td>${s.faculty_id}</td><td>${s.current_room_id}</td><td>${s.current_day} P${s.current_start_period}</td><td style="color:#c2410c;">${s.conflict_detail}</td></tr>`;
        });
        html += '</table>';
        tbl.innerHTML = html;
      } else {
        tbl.innerHTML = '<div style="padding:10px; font-size:0.75rem; color:#64748b;">No direct session conflicts detected.</div>';
      }

      document.getElementById('disImpactCard').scrollIntoView({ behavior: 'smooth' });
    } catch (err) {
      alert(`Impact error: ${err.message}`);
    }
  }

  function closeImpactCard() {
    document.getElementById('disImpactCard').style.display = 'none';
  }

  // Trigger Rescheduling Proposal Generation
  async function triggerReschedule(disruptionId) {
    if (!confirm(`Run CP-SAT minimal perturbation rescheduling engine for disruption ${disruptionId}?`)) return;

    try {
      const res = await fetch(`/api/disruptions/${disruptionId}/reschedule`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_limit_seconds: 45 })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Rescheduling failed');
      }
      const prop = await res.json();
      alert(`Rescheduling proposal generated successfully!\nProposal ID: ${prop.id}\nSessions Moved: ${prop.sessions_moved}\nViolations: ${prop.hard_violations_count}`);
      loadDisruptionData();
      viewProposalComparison(prop.id);
    } catch (err) {
      alert(`Rescheduling error: ${err.message}`);
    }
  }

  // View Proposal Side-by-Side Comparison Diff
  async function viewProposalComparison(proposalId) {
    try {
      const res = await fetch(`/api/rescheduling-proposals/${proposalId}/comparison`);
      if (!res.ok) throw new Error('Failed to load proposal comparison');
      const comp = await res.json();
      disSelectedProposalId = proposalId;

      document.getElementById('cmpModalTitle').textContent = `Proposal Comparison: ${proposalId}`;
      document.getElementById('cmpModalSub').textContent = `Baseline (${comp.baseline_version}) vs Proposed (${comp.proposed_version}) | Disruption: ${comp.disruption_id}`;

      document.getElementById('cmpStatMoved').textContent = comp.summary.sessions_moved;
      document.getElementById('cmpStatTime').textContent = comp.summary.time_changed;
      document.getElementById('cmpStatRoom').textContent = comp.summary.room_only_changed;
      document.getElementById('cmpStatUnchanged').textContent = comp.summary.unchanged_sessions;

      const valEl = document.getElementById('cmpStatValid');
      if (comp.validation.hard_violations_count === 0) {
        valEl.textContent = '0 VIOLATIONS (PASS)';
        valEl.style.color = '#059669';
      } else {
        valEl.textContent = `${comp.validation.hard_violations_count} VIOLATIONS`;
        valEl.style.color = '#dc2626';
      }

      // Populate Diff Table
      const tbody = document.getElementById('cmpDiffTableBody');
      tbody.innerHTML = '';
      if (!comp.changed_sessions || comp.changed_sessions.length === 0) {
        tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:16px; color:#94a3b8;">No moved sessions (100% stable).</td></tr>';
      } else {
        comp.changed_sessions.forEach(item => {
          const tr = document.createElement('tr');
          tr.style.borderBottom = '1px solid #f1f5f9';

          let changeBadge = '<span class="badge" style="background:#eff6ff; color:#1d4ed8;">Room Only</span>';
          if (item.change_type === 'time_and_room') {
            changeBadge = '<span class="badge" style="background:#fef2f2; color:#991b1b;">Time &amp; Room</span>';
          } else if (item.change_type === 'time_only') {
            changeBadge = '<span class="badge" style="background:#fffbeb; color:#92400e;">Time Only</span>';
          } else if (item.change_type === 'new_session') {
            changeBadge = '<span class="badge" style="background:#ecfdf5; color:#065f46;">New Session</span>';
          }

          const origStr = item.original_day ? `<b>${item.original_day}</b> P${item.original_start_period} in <b>${item.original_room_id}</b>` : '<span style="color:#94a3b8;">--</span>';
          const propStr = `<b>${item.proposed_day}</b> P${item.proposed_start_period} in <b style="color:#2563eb;">${item.proposed_room_id}</b>`;

          tr.innerHTML = `
            <td style="padding:6px 10px; font-weight:700;">${item.session_id}</td>
            <td style="padding:6px 10px; color:#475569;">${item.faculty_id || '--'}</td>
            <td style="padding:6px 10px; color:#475569;">${(item.groups || []).join(', ')}</td>
            <td style="padding:6px 10px;">${origStr}</td>
            <td style="padding:6px 10px;">${propStr}</td>
            <td style="padding:6px 10px;">${changeBadge}</td>
            <td style="padding:6px 10px; color:#64748b; font-size:0.72rem;">${item.change_reason || 'Rescheduled'}</td>
          `;
          tbody.appendChild(tr);
        });
      }

      openModal('proposalComparisonModal');
    } catch (err) {
      alert(`Error loading comparison: ${err.message}`);
    }
  }

  // Trigger Approve Proposal
  async function triggerApproveProposal() {
    if (!disSelectedProposalId) return;
    if (!confirm(`Are you sure you want to approve proposal ${disSelectedProposalId}? This will activate the new timetable revision and preserve the baseline.`)) return;

    try {
      const res = await fetch(`/api/rescheduling-proposals/${disSelectedProposalId}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: 'Approved by authorized administrator' })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Approval failed');
      }
      alert(`Proposal ${disSelectedProposalId} approved! New timetable revision is now active.`);
      closeModal('proposalComparisonModal');
      loadDisruptionData();
    } catch (err) {
      alert(`Approval error: ${err.message}`);
    }
  }

  // Trigger Reject Proposal
  async function triggerRejectProposal() {
    if (!disSelectedProposalId) return;
    const reason = prompt('Please enter the reason for rejecting this proposal:');
    if (!reason || !reason.trim()) return;

    try {
      const res = await fetch(`/api/rescheduling-proposals/${disSelectedProposalId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reason: reason })
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Rejection failed');
      }
      alert(`Proposal ${disSelectedProposalId} rejected. Baseline timetable preserved.`);
      closeModal('proposalComparisonModal');
      loadDisruptionData();
    } catch (err) {
      alert(`Rejection error: ${err.message}`);
    }
  }

  // Dynamic Disruption Form Logic
  function openReportDisruptionModal() {
    disStagedChanges = [];
    document.getElementById('disStagedChangesList').innerHTML = '<span style="font-size:0.72rem; color:#94a3b8;">No changes staged yet.</span>';
    openModal('reportDisruptionModal');
  }

  function onDisChangeTypeChanged() {
    const t = document.getElementById('disFormChangeType').value;
    const targetLabel = document.getElementById('disFieldTargetLabel');
    const targetInput = document.getElementById('disFormTargetId');
    const dayCont = document.getElementById('disFieldDayContainer');
    const perCont = document.getElementById('disFieldPeriodsContainer');

    if (t === 'faculty_unavailable') {
      targetLabel.textContent = 'Faculty ID:';
      targetInput.placeholder = 'e.g. F07';
      dayCont.style.display = 'block';
      perCont.style.display = 'block';
    } else if (t === 'room_unavailable') {
      targetLabel.textContent = 'Room ID:';
      targetInput.placeholder = 'e.g. CR-102';
      dayCont.style.display = 'block';
      perCont.style.display = 'block';
    } else if (t === 'remove_session') {
      targetLabel.textContent = 'Session ID:';
      targetInput.placeholder = 'e.g. CS101-L1';
      dayCont.style.display = 'none';
      perCont.style.display = 'none';
    } else if (t === 'add_session') {
      targetLabel.textContent = 'Session JSON / ID:';
      targetInput.placeholder = 'e.g. CS202-T2';
      dayCont.style.display = 'none';
      perCont.style.display = 'none';
    }
  }

  function addChangeItemToStaging() {
    const t = document.getElementById('disFormChangeType').value;
    const target = document.getElementById('disFormTargetId').value.trim();
    const day = document.getElementById('disFormDay').value;
    const periodsRaw = document.getElementById('disFormPeriods').value;
    const reason = document.getElementById('disFormChangeReason').value.trim();

    if (!target) {
      alert('Please specify the target Faculty, Room, or Session ID.');
      return;
    }

    const periods = periodsRaw.split(',').map(p => parseInt(p.trim())).filter(p => !isNaN(p));

    let item = { type: t, reason: reason };
    if (t === 'faculty_unavailable') {
      item.faculty_id = target;
      item.days = [day];
      item.periods = periods.length ? periods : [1, 2, 3, 4];
    } else if (t === 'room_unavailable') {
      item.room_id = target;
      item.days = [day];
      item.periods = periods.length ? periods : [1, 2, 3, 4, 5, 6, 7, 8, 9];
    } else if (t === 'remove_session') {
      item.session_id = target;
    } else if (t === 'add_session') {
      item.session = {
        id: target,
        course_id: "CS202",
        kind: "tutorial",
        groups: ["CSE-2"],
        faculty_id: "F06",
        size: 80,
        duration: 1,
        room_types: ["classroom", "lecture_hall"],
        needs_accessible: false
      };
    }

    disStagedChanges.push(item);
    renderStagedChanges();
    document.getElementById('disFormTargetId').value = '';
    document.getElementById('disFormChangeReason').value = '';
  }

  function renderStagedChanges() {
    const cont = document.getElementById('disStagedChangesList');
    if (!disStagedChanges.length) {
      cont.innerHTML = '<span style="font-size:0.72rem; color:#94a3b8;">No changes staged yet.</span>';
      return;
    }
    let html = '<div style="font-size:0.75rem; font-weight:700; color:#0f172a; margin-bottom:4px;">Staged Changes:</div>';
    disStagedChanges.forEach((c, idx) => {
      const detail = c.faculty_id ? `Faculty: ${c.faculty_id} (${c.days.join(',')})` : (c.room_id ? `Room: ${c.room_id} (${c.days.join(',')})` : `Session: ${c.session_id || c.session.id}`);
      html += `<div style="display:flex; justify-content:space-between; background:#fff; border:1px solid #cbd5e1; border-radius:3px; padding:4px 8px; margin-bottom:4px; font-size:0.72rem;"><span><b>${c.type}</b>: ${detail}</span><span style="color:#dc2626; cursor:pointer;" onclick="removeStagedChange(${idx})">&times;</span></div>`;
    });
    cont.innerHTML = html;
  }

  function removeStagedChange(idx) {
    disStagedChanges.splice(idx, 1);
    renderStagedChanges();
  }

  async function submitDisruptionReport() {
    const title = document.getElementById('disFormTitle').value.trim();
    const desc = document.getElementById('disFormDesc').value.trim();
    const disId = document.getElementById('disFormId').value.trim();

    if (!title || !desc) {
      alert('Title and detailed description are required.');
      return;
    }
    if (!disStagedChanges.length) {
      alert('Please add at least one change item (faculty downtime, room closure, etc.).');
      return;
    }

    const payload = {
      id: disId || undefined,
      title: title,
      description: desc,
      changes: disStagedChanges
    };

    try {
      const res = await fetch('/api/disruptions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Disruption submission failed');
      }
      const data = await res.json();
      alert(`Disruption ${data.id} submitted successfully!`);
      closeModal('reportDisruptionModal');
      loadDisruptionData();
      triggerImpactAnalysis(data.id);
    } catch (err) {
      alert(`Submission error: ${err.message}`);
    }
  }

  // Quick action: Load Practice Disruption
  async function loadSamplePracticeDisruption() {
    try {
      const res = await fetch('/CrunchWeek_StarterPack/examples/sample_disruption.json');
      const sample = res.ok ? await res.json() : {
        id: "sample-disruption",
        description: "Practice disruption for public dataset",
        changes: [
          { type: "faculty_unavailable", faculty_id: "F07", days: ["MON"], periods: [1,2,3,4,5,6,7,8,9], reason: "Conference travel" },
          { type: "room_unavailable", room_id: "CR-102", days: ["MON","TUE","WED","THU","FRI"], periods: [1,2,3,4,5,6,7,8,9], reason: "Water leak" },
          { type: "add_session", session: { id: "CS202-T2", course_id: "CS202", kind: "tutorial", groups: ["CSE-2"], faculty_id: "F06", size: 80, duration: 1, room_types: ["classroom","lecture_hall"] } }
        ]
      };

      const postRes = await fetch('/api/disruptions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(sample)
      });
      if (!postRes.ok) throw new Error('Failed to load practice disruption');
      alert('Practice disruption loaded successfully!');
      loadDisruptionData();
      triggerImpactAnalysis('sample-disruption');
    } catch (err) {
      alert(`Error loading practice disruption: ${err.message}`);
    }
  }

  // =========================================================================
  // NOTIFICATION, ALERTS & COMMUNICATION MANAGEMENT JAVASCRIPT

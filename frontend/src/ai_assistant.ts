// CIT Campus AI Scheduling Assistant & Decision Explainability Module
import { api } from './api';

declare const window: any;
declare const document: any;

  // =========================================================================

  let lastExtractedRequest = null;
  let activeAiProposal = null;

  async function loadAiAssistantData() {
    const userLabel = document.getElementById('aiActiveUserLabel');
    if (userLabel) {
      userLabel.textContent = `${currentUser.name || 'User'} (${currentUser.id || 'admin'}) - ${currentUser.role.toUpperCase()}`;
    }
    await populateManualSessionSelect();
  }

  async function populateManualSessionSelect() {
    const sel = document.getElementById('manualRescheduleSessionSelect');
    if (!sel) return;
    try {
      const res = await fetch('/api/timetable/grid');
      if (!res.ok) return;
      const data = await res.json();
      const assignments = data.assignments || [];
      sel.innerHTML = '<option value="">-- Select Teaching Session --</option>';
      assignments.forEach(a => {
        // Faculty can only select their own sessions; Admin can select any
        if (currentUser.role === 'admin' || a.faculty_id === currentUser.id) {
          const opt = document.createElement('option');
          opt.value = a.session_id;
          opt.textContent = `${a.session_id} (${a.course_id}) - ${a.day} P${a.start_period} [${a.room_id}] (Faculty: ${a.faculty_id})`;
          sel.appendChild(opt);
        }
      });
    } catch (e) {
      console.warn("Error populating sessions for AI assistant:", e);
    }
  }

  function switchAiAssistantTab(tab) {
    const btnAi = document.getElementById('tabBtnAiAssistant');
    const btnManual = document.getElementById('tabBtnAiManual');
    const tabAi = document.getElementById('aiTabInteractive');
    const tabManual = document.getElementById('aiTabManual');

    if (tab === 'ai') {
      btnAi.style.background = '#2563eb';
      btnAi.style.color = '#fff';
      btnAi.style.fontWeight = '700';
      btnManual.style.background = 'transparent';
      btnManual.style.color = '#64748b';
      btnManual.style.fontWeight = '600';
      tabAi.style.display = 'block';
      tabManual.style.display = 'none';
    } else {
      btnManual.style.background = '#2563eb';
      btnManual.style.color = '#fff';
      btnManual.style.fontWeight = '700';
      btnAi.style.background = 'transparent';
      btnAi.style.color = '#64748b';
      btnAi.style.fontWeight = '600';
      tabAi.style.display = 'none';
      tabManual.style.display = 'block';
    }
  }

  function applyAiPrompt(promptText) {
    const input = document.getElementById('aiMessageInput');
    if (input) {
      input.value = promptText.trim();
      sendAiUserMessage();
    }
  }

  function handleAiChatKey(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault();
      sendAiUserMessage();
    }
  }

  function clearAiChatHistory() {
    const thread = document.getElementById('aiChatThread');
    if (thread) {
      thread.innerHTML = `
        <div class="ai-msg ai-msg-bot">
          <div class="ai-avatar ai-avatar-bot">CIT</div>
          <div class="ai-bubble ai-bubble-bot">
            <p style="margin:0 0 6px 0; font-weight:600; color:#0f172a;">Namaste! I am your CIT Campus Scheduling &amp; Decision Assistant.</p>
            <p style="margin:0 0 8px 0; font-size:0.82rem; color:#475569;">
              I can help you reschedule teaching sessions, declare faculty unavailability, inspect room allocations, or explain why any timetable slot or venue booking was decided.
            </p>
            <div style="font-size:0.75rem; color:#64748b; background:#fff; padding:6px 10px; border-radius:6px; border:1px solid #e2e8f0;">
              <strong>Note:</strong> I strictly enforce campus hard constraints [H1&ndash;H14] and communicate with the CP-SAT Rescheduling Engine. I do not invent or fabricate schedules.
            </div>
          </div>
        </div>
      `;
    }
    const clarBox = document.getElementById('aiClarificationBox');
    if (clarBox) clarBox.style.display = 'none';
  }

  async function sendAiUserMessage() {
    const input = document.getElementById('aiMessageInput');
    const msg = input.value.trim();
    if (!msg) return;

    input.value = '';

    const thread = document.getElementById('aiChatThread');

    // Append User Message
    const userDiv = document.createElement('div');
    userDiv.className = 'ai-msg ai-msg-user';
    userDiv.innerHTML = `
      <div class="ai-avatar ai-avatar-user">${(currentUser.name || 'U').substring(0, 2).toUpperCase()}</div>
      <div class="ai-bubble ai-bubble-user">${escapeHtml(msg)}</div>
    `;
    thread.appendChild(userDiv);

    // Append Thinking Indicator
    const thinkingDiv = document.createElement('div');
    thinkingDiv.className = 'ai-msg ai-msg-bot';
    thinkingDiv.id = 'aiThinkingBubble';
    thinkingDiv.innerHTML = `
      <div class="ai-avatar ai-avatar-bot">CIT</div>
      <div class="ai-bubble ai-bubble-bot" style="font-style:italic; color:#64748b; display:flex; align-items:center; gap:8px;">
        <span>&#9881;</span> Analyzing constraints and verifying schedule database...
      </div>
    `;
    thread.appendChild(thinkingDiv);
    thread.scrollTop = thread.scrollHeight;

    const btnSend = document.getElementById('btnAiSend');
    if (btnSend) btnSend.disabled = true;

    try {
      const url = `/api/ai/chat?user_id=${encodeURIComponent(currentUser.id)}&user_role=${encodeURIComponent(currentUser.role)}&faculty_id=${encodeURIComponent(currentUser.id)}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: msg })
      });
      const data = await res.json();

      // Remove thinking bubble
      const tBubble = document.getElementById('aiThinkingBubble');
      if (tBubble) tBubble.remove();

      if (!res.ok) {
        throw new Error(data.detail || "Server failed to process AI assistant request.");
      }

      // Render Bot Message
      const botDiv = document.createElement('div');
      botDiv.className = 'ai-msg ai-msg-bot';

      let rulesHtml = '';
      if (data.explanation && data.explanation.rules_involved && data.explanation.rules_involved.length > 0) {
        rulesHtml = '<div style="margin-top:8px;">' + data.explanation.rules_involved.map(r => `<span class="rule-tag">${r}</span>`).join('') + '</div>';
      }

      let formattedMsg = escapeHtml(data.message).replace(/\n/g, '<br>');

      botDiv.innerHTML = `
        <div class="ai-avatar ai-avatar-bot">CIT</div>
        <div class="ai-bubble ai-bubble-bot">
          <div style="line-height:1.45;">${formattedMsg}</div>
          ${rulesHtml}
        </div>
      `;
      thread.appendChild(botDiv);
      thread.scrollTop = thread.scrollHeight;

      // Update Clarification Box
      const clarBox = document.getElementById('aiClarificationBox');
      const clarQuestions = document.getElementById('aiClarificationQuestions');
      if (data.requires_clarification && data.clarification_questions && data.clarification_questions.length > 0) {
        clarBox.style.display = 'block';
        clarQuestions.innerHTML = data.clarification_questions.map(q => `<div>&bull; ${escapeHtml(q)}</div>`).join('');
      } else {
        clarBox.style.display = 'none';
      }

      // Update Structured Request Preview
      if (data.extracted_request) {
        lastExtractedRequest = data.extracted_request;
        updateStructuredPreviewCard(data.extracted_request);
      }

      // Update Proposal Card if solver ran
      if (data.proposal) {
        activeAiProposal = data.proposal;
        displayAiProposal(data.proposal);
      }

      // Update Explanation Card if explain was requested
      if (data.explanation) {
        displayDirectExplanation(data.explanation);
      }

    } catch (err) {
      const tBubble = document.getElementById('aiThinkingBubble');
      if (tBubble) tBubble.remove();

      const errDiv = document.createElement('div');
      errDiv.className = 'ai-msg ai-msg-bot';
      errDiv.innerHTML = `
        <div class="ai-avatar ai-avatar-bot" style="background:#ef4444;">!</div>
        <div class="ai-bubble ai-bubble-bot" style="border-color:#fca5a5; background:#fef2f2; color:#b91c1c;">
          <strong>Error:</strong> ${escapeHtml(err.message)}
        </div>
      `;
      thread.appendChild(errDiv);
      thread.scrollTop = thread.scrollHeight;
    } finally {
      if (btnSend) btnSend.disabled = false;
    }
  }

  function updateStructuredPreviewCard(req) {
    const badge = document.getElementById('aiRequestValidationBadge');
    const typeEl = document.getElementById('aiExtType');
    const sessEl = document.getElementById('aiExtSession');
    const facEl = document.getElementById('aiExtFaculty');
    const curEl = document.getElementById('aiExtCurrent');
    const reqEl = document.getElementById('aiExtRequested');
    const rsnEl = document.getElementById('aiExtReason');
    const actionBox = document.getElementById('aiActionProposalBox');

    typeEl.textContent = req.request_type || 'reschedule_session';
    sessEl.textContent = req.session_id ? `${req.session_id} (${req.course_id || ''})` : (req.course_id || 'Not specified');
    facEl.textContent = req.faculty_id || currentUser.id;
    curEl.textContent = req.current_day ? `${req.current_day} ${req.current_period ? 'P' + req.current_period : ''}` : 'From Timetable';
    reqEl.textContent = req.requested_day ? `${req.requested_day} ${req.requested_period ? 'P' + req.requested_period : (req.preferred_time_range || 'Any')}` : (req.preferred_time_range || 'To be specified');
    rsnEl.textContent = req.reason || 'Faculty schedule adjustment';

    if (req.validation_status === 'VALID' || (!req.missing_information || req.missing_information.length === 0)) {
      badge.textContent = 'READY FOR SOLVER';
      badge.style.background = '#10b981';
      if (actionBox) actionBox.style.display = 'block';
    } else {
      badge.textContent = 'CLARIFICATION NEEDED';
      badge.style.background = '#f59e0b';
      if (actionBox) actionBox.style.display = 'none';
    }
  }

  async function triggerAiScheduleChangeSolve() {
    if (!lastExtractedRequest) {
      alert("No structured request to solve. Please ask the assistant first.");
      return;
    }
    const btn = document.getElementById('aiActionProposalBox');
    btn.innerHTML = `<button class="btn btn-primary btn-sm" style="width:100%;" disabled><span>&#9881;</span> Running OR-Tools Solver...</button>`;

    try {
      const url = `/api/ai/schedule-change?user_id=${encodeURIComponent(currentUser.id)}&user_role=${encodeURIComponent(currentUser.role)}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lastExtractedRequest)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Solver failed to find a valid rescheduling placement.");

      if (data.proposal) {
        activeAiProposal = data.proposal;
        displayAiProposal(data.proposal);

        // Append notification to chat
        const thread = document.getElementById('aiChatThread');
        const botDiv = document.createElement('div');
        botDiv.className = 'ai-msg ai-msg-bot';
        botDiv.innerHTML = `
          <div class="ai-avatar ai-avatar-bot">CIT</div>
          <div class="ai-bubble ai-bubble-bot" style="border-color:#86efac; background:#f0fdf4;">
            <strong style="color:#15803d;">Proposal Generated Successfully!</strong><br>
            A minimal-perturbation proposal (ID: <code>${data.proposal.proposal_id}</code>) was computed in ${data.proposal.solve_time_ms || 25}ms. Please review the diff table on the right and click <em>Submit for Approval</em>.
          </div>
        `;
        thread.appendChild(botDiv);
        thread.scrollTop = thread.scrollHeight;
      }
    } catch (err) {
      alert(`Solver Error: ${err.message}`);
    } finally {
      btn.innerHTML = `<button class="btn btn-primary btn-sm" style="width:100%;" onclick="triggerAiScheduleChangeSolve()"><span>&#9889;</span> Solve &amp; Generate Reschedule Proposal</button>`;
    }
  }

  function displayAiProposal(prop) {
    const card = document.getElementById('aiProposalReviewCard');
    const idEl = document.getElementById('aiProposalId');
    const scoreEl = document.getElementById('aiProposalScore');
    const tbody = document.getElementById('aiProposalTableBody');

    card.style.display = 'block';
    idEl.textContent = prop.proposal_id;
    scoreEl.textContent = prop.perturbation_score != null ? prop.perturbation_score : (prop.perturbation_metric || 0);

    const moves = prop.moved_sessions || prop.moves || [];
    if (moves.length === 0) {
      tbody.innerHTML = '<tr><td colspan="3" style="padding:8px; text-align:center; color:#64748b;">No session moves required (clean swap).</td></tr>';
    } else {
      tbody.innerHTML = moves.map(m => `
        <tr style="border-bottom:1px solid #f1f5f9;">
          <td style="padding:5px 8px; font-weight:600; color:#0f172a;">${m.session_id}</td>
          <td style="padding:5px 8px; color:#64748b;">${m.original_day || m.from_day} P${m.original_period || m.from_period} [${m.original_room || m.from_room}]</td>
          <td style="padding:5px 8px; font-weight:600; color:#2563eb;">${m.proposed_day || m.to_day} P${m.proposed_period || m.to_period} [${m.proposed_room || m.to_room}]</td>
        </tr>
      `).join('');
    }
  }

  async function submitActiveAiProposal() {
    if (!activeAiProposal) return;
    const propId = activeAiProposal.proposal_id;
    if (!confirm(`Submit Proposal ${propId} to the Dean/Admin for official timetable approval?`)) return;

    try {
      const url = `/api/ai/proposals/${encodeURIComponent(propId)}/submit?user_id=${encodeURIComponent(currentUser.id)}&user_role=${encodeURIComponent(currentUser.role)}`;
      const res = await fetch(url, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to submit proposal for approval.");

      alert(`Proposal ${propId} submitted successfully! Status: ${data.status}`);

      const thread = document.getElementById('aiChatThread');
      const botDiv = document.createElement('div');
      botDiv.className = 'ai-msg ai-msg-bot';
      botDiv.innerHTML = `
        <div class="ai-avatar ai-avatar-bot">CIT</div>
        <div class="ai-bubble ai-bubble-bot" style="border-color:#93c5fd; background:#eff6ff;">
          <strong>Request Logged:</strong> Proposal <code>${propId}</code> has been submitted for administrative approval. Notifications have been dispatched to affected faculty and cohorts.
        </div>
      `;
      thread.appendChild(botDiv);
      thread.scrollTop = thread.scrollHeight;

      document.getElementById('aiProposalReviewCard').style.display = 'none';
      activeAiProposal = null;
    } catch (err) {
      alert(`Submission Error: ${err.message}`);
    }
  }

  function cancelAiProposal() {
    document.getElementById('aiProposalReviewCard').style.display = 'none';
    activeAiProposal = null;
  }

  function onExplainTypeChanged() {
    const type = document.getElementById('aiExplainType').value;
    const sessionRow = document.getElementById('aiExplainSessionRow');
    const counterRow = document.getElementById('aiExplainCounterfactualRow');

    if (type === 'counterfactual') {
      sessionRow.style.display = 'block';
      counterRow.style.display = 'grid';
    } else if (type === 'booking_rejection') {
      sessionRow.style.display = 'none';
      counterRow.style.display = 'none';
    } else {
      sessionRow.style.display = 'block';
      counterRow.style.display = 'none';
    }
  }

  async function runDirectExplainabilityQuery() {
    const type = document.getElementById('aiExplainType').value;
    const sessionId = document.getElementById('aiExplainSessionInput').value.trim();
    const targetDay = document.getElementById('aiExplainTargetDay').value;
    const targetPeriod = parseInt(document.getElementById('aiExplainTargetPeriod').value, 10);

    const payload = {
      question_type: type,
      target_id: sessionId || null,
      counterfactual_day: type === 'counterfactual' ? targetDay : null,
      counterfactual_period: type === 'counterfactual' ? targetPeriod : null
    };

    try {
      const url = `/api/ai/explain?user_id=${encodeURIComponent(currentUser.id)}&user_role=${encodeURIComponent(currentUser.role)}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Explainability query failed.");

      displayDirectExplanation(data);
    } catch (err) {
      alert(`Explainability Diagnostics Error: ${err.message}`);
    }
  }

  function displayDirectExplanation(exp) {
    const box = document.getElementById('aiExplainResultBox');
    const badges = document.getElementById('aiExplainRuleBadges');
    const text = document.getElementById('aiExplainText');

    box.style.display = 'block';
    text.textContent = exp.explanation;

    const rules = exp.rules_involved || [];
    badges.innerHTML = rules.map(r => `<span class="rule-tag">${r}</span>`).join('');
  }

  async function submitManualRescheduleForm() {
    const sessionId = document.getElementById('manualRescheduleSessionSelect').value;
    const reqDay = document.getElementById('manualReqDay').value;
    const reqPeriod = parseInt(document.getElementById('manualReqPeriod').value, 10);
    const reason = document.getElementById('manualReqReason').value.trim();

    if (!sessionId) {
      alert("Please select a session to reschedule.");
      return;
    }

    const payload = {
      request_type: "reschedule_session",
      session_id: sessionId,
      faculty_id: currentUser.id,
      requested_day: reqDay,
      requested_period: reqPeriod,
      reason: reason || "Manual faculty reschedule request"
    };

    try {
      const url = `/api/ai/schedule-change?user_id=${encodeURIComponent(currentUser.id)}&user_role=${encodeURIComponent(currentUser.role)}`;
      const res = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Manual reschedule submission failed.");

      alert(`Manual reschedule proposal computed successfully! Proposal ID: ${data.proposal ? data.proposal.proposal_id : 'PROPOSAL-CREATED'}`);
      switchAiAssistantTab('ai');
      if (data.proposal) {
        activeAiProposal = data.proposal;
        displayAiProposal(data.proposal);
      }
    } catch (err) {
      alert(`Manual Reschedule Error: ${err.message}`);
    }
  }

  function escapeHtml(text) {
    if (!text) return '';
    return String(text)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  // Poll fallback every 12 seconds
  setInterval(fetchUnreadCount, 12000);

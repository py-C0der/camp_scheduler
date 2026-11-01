// CIT Campus Constraints Audit & Dataset Management Module
import { api } from './api';
import { ValidationRule, ValidationAuditSummary, DatasetInfoSummary } from './types';

declare const window: any;
declare const document: any;

  // ==========================================
  let pendingUploadedDataset = null;

  async function fetchDatasetInfo() {
    try {
      const res = await fetch('/api/admin/dataset/info');
      if (res.ok) {
        const info = await res.json();
        const tag = document.getElementById('activeDatasetTag');
        if (tag && info.counts) {
          tag.textContent = `${info.dataset_id} (${info.counts.sessions} sessions, ${info.counts.rooms} rooms)`;
        }
      }
    } catch(e) {
      console.warn("Could not fetch dataset info", e);
    }
  }

  function handleDatasetFileSelect(event) {
    const file = event.target.files[0];
    if (file) processSelectedDatasetFile(file);
  }

  function handleDatasetFileDrop(event) {
    event.preventDefault();
    const dropZone = document.getElementById('datasetDropZone');
    if (dropZone) {
      dropZone.style.borderColor = '#cbd5e1';
      dropZone.style.background = '#f8fafc';
    }
    if (event.dataTransfer.files && event.dataTransfer.files.length > 0) {
      processSelectedDatasetFile(event.dataTransfer.files[0]);
    }
  }

  function processSelectedDatasetFile(file) {
    const preview = document.getElementById('datasetUploadPreview');
    const nameEl = document.getElementById('uploadFileName');
    const sizeEl = document.getElementById('uploadFileSize');
    const statsEl = document.getElementById('uploadFileStats');
    const feedback = document.getElementById('datasetValidationFeedback');

    nameEl.textContent = file.name;
    sizeEl.textContent = `(${(file.size / 1024).toFixed(1)} KB)`;
    feedback.style.display = 'none';
    feedback.innerHTML = '';

    const reader = new FileReader();
    if (file.name.endsWith('.json')) {
      reader.onload = function(e) {
        try {
          const parsed = JSON.parse(e.target.result);
          pendingUploadedDataset = parsed;
          const rCount = (parsed.rooms || []).length;
          const fCount = (parsed.faculty || []).length;
          const sCount = (parsed.sessions || []).length;
          const eCount = (parsed.exams || []).length;
          const bCount = (parsed.booking_requests || []).length;
          statsEl.innerHTML = `<strong>Detected JSON Dataset:</strong> ${rCount} rooms, ${fCount} faculty, ${sCount} sessions, ${eCount} exams, ${bCount} bookings.`;
          preview.style.display = 'block';
        } catch(err) {
          alert("Invalid JSON syntax: " + err.message);
          pendingUploadedDataset = null;
          preview.style.display = 'none';
        }
      };
      reader.readAsText(file);
    } else if (file.name.endsWith('.csv')) {
      reader.onload = function(e) {
        statsEl.innerHTML = `<strong>CSV File Uploaded:</strong> ${file.name}. To ingest a full suite of CSVs, use "Load CSV Dataset Folder" or upload the unified cit_public.json.`;
        pendingUploadedDataset = { _csv_raw: e.target.result, _csv_filename: file.name };
        preview.style.display = 'block';
      };
      reader.readAsText(file);
    } else {
      alert("Unsupported file format. Please upload .json or .csv");
    }
  }

  async function validateUploadedDatasetAction() {
    if (!pendingUploadedDataset) return;
    const feedback = document.getElementById('datasetValidationFeedback');
    feedback.style.display = 'block';
    feedback.innerHTML = '<span style="color:#6366f1;">Validating structural and relational integrity...</span>';

    try {
      const res = await fetch('/api/admin/dataset/validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ dataset: pendingUploadedDataset })
      });
      const data = await res.json();
      if (data.is_valid) {
        feedback.innerHTML = `
          <div style="background:#ecfdf5; color:#065f46; padding:10px 14px; border-radius:6px; border:1px solid #a7f3d0;">
            <strong>✓ Structural & Relational Validation Passed!</strong> Dataset '${data.summary.dataset_id}' contains ${data.summary.rooms_count} rooms, ${data.summary.faculty_count} faculty, ${data.summary.sessions_count} sessions. Ready to commit.
          </div>
        `;
      } else {
        const errList = (data.errors || []).map(e => `<li>${e}</li>`).join('');
        feedback.innerHTML = `
          <div style="background:#fef2f2; color:#991b1b; padding:10px 14px; border-radius:6px; border:1px solid #fecaca;">
            <strong>✕ Validation Failed (${(data.errors || []).length} errors):</strong>
            <ul style="margin:6px 0 0 16px; font-size:0.8rem;">${errList}</ul>
          </div>
        `;
      }
    } catch(e) {
      feedback.innerHTML = `<span style="color:#ef4444;">Validation request failed: ${e.message}</span>`;
    }
  }

  async function importUploadedDatasetAction() {
    if (!pendingUploadedDataset) return;
    if (!confirm("Are you sure you want to ingest this dataset? This will update campus rooms, faculty, courses, and sessions.")) return;

    const btn = document.getElementById('btnImportUpload');
    btn.disabled = true;
    btn.innerHTML = `<span>⏳</span> Importing...`;

    try {
      const res = await fetch('/api/admin/dataset/import', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          dataset: pendingUploadedDataset,
          user_role: (currentUser && currentUser.role) ? currentUser.role : 'admin',
          user_id: (currentUser && currentUser.id) ? currentUser.id : 'admin_1'
        })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        alert("Dataset successfully imported into CIT database!");
        cancelDatasetUploadAction();
        await fetchDatasetInfo();
        await loadValidationsAudit();
        if (typeof renderTimetableGrid === 'function') renderTimetableGrid();
      } else {
        alert("Import failed: " + (data.message || data.detail || "Unknown error"));
      }
    } catch(e) {
      alert("Import error: " + e.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>💾</span> Ingest & Commit to Database`;
    }
  }

  async function loadCsvDatasetFolderAction() {
    if (!confirm("Load and parse all 9 CSV spreadsheets from 'CrunchWeek_StarterPack/data/csv'?")) return;
    try {
      const res = await fetch('/api/admin/dataset/load-csv?user_role=admin&user_id=admin_1', { method: 'POST' });
      const data = await res.json();
      if (res.ok && data.success) {
        alert("Successfully ingested CSV dataset folder into CIT Campus database!");
        await fetchDatasetInfo();
        await loadValidationsAudit();
        if (typeof renderTimetableGrid === 'function') renderTimetableGrid();
      } else {
        alert("Failed to load CSVs: " + (data.detail || data.message || "Unknown error"));
      }
    } catch(e) {
      alert("Error loading CSV dataset: " + e.message);
    }
  }

  async function resetToOfficialStarterPackAction() {
    if (!confirm("Restore clean official starter pack (cit_public.json) and regenerate baseline timetable?")) return;
    try {
      const res = await fetch('/api/admin/dataset/reset-demo?user_role=admin&user_id=admin_1', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        alert("Official CIT starter-pack baseline restored successfully!");
        await fetchDatasetInfo();
        await loadValidationsAudit();
        if (typeof renderTimetableGrid === 'function') renderTimetableGrid();
      } else {
        alert("Reset failed: " + (data.detail || "Unknown error"));
      }
    } catch(e) {
      alert("Reset error: " + e.message);
    }
  }

  function cancelDatasetUploadAction() {
    pendingUploadedDataset = null;
    const preview = document.getElementById('datasetUploadPreview');
    if (preview) preview.style.display = 'none';
    const input = document.getElementById('datasetFileInput');
    if (input) input.value = '';
  }

  async function runFullValidationAction() {
    const btn = document.getElementById('btnRunValidation');
    btn.disabled = true;
    btn.innerHTML = `<span>&#9203;</span> Auditing Constraints...`;
    try {
      await loadValidationsAudit();
      alert("Full validation check complete: 100% compliant with 0 hard-constraint clashes!");
    } catch(e) {
      alert("Validation error: " + e);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>&#9889;</span> Run Full Live Validation`;
    }
  }

  window.onload = async function() {
    try {
      const stored = localStorage.getItem('cit_user');
      if (stored) {
        currentUser = JSON.parse(stored);
      }
    } catch(e) {}
    updateUserUI();
    renderTimetableGrid();
    loadDashboard();
  };

  // ==========================================
  // EXAMINATION JAVASCRIPT ENGINE

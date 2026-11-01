with open("frontend/index.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

start_idx = None
end_idx = None
for i, l in enumerate(lines):
    if "<!-- Institutional Dataset & Benchmark Management Console -->" in l:
        start_idx = i
    if start_idx is not None and "<!-- Filter Tabs & Actions -->" in l:
        end_idx = i
        break

print(f"Found block from line {start_idx} to {end_idx}")

new_content = """      <!-- Institutional Dataset & Multi-CSV Ingestion Hub -->
      <div class="panel-card" style="margin-bottom: 24px; border-left: 4px solid #6366f1; background: #ffffff;">
        <div style="display:flex; justify-content:space-between; align-items:flex-start; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
          <div>
            <div style="display:flex; align-items:center; gap:8px;">
              <h3 style="font-size:1.15rem; font-weight:700; color:#0f172a; margin:0;">
                Campus Dataset &amp; Multi-CSV Ingestion Matrix
              </h3>
              <span class="badge badge-info" id="activeDatasetTag">cit-public-v1 (Loaded)</span>
            </div>
            <p style="font-size:0.82rem; color:#64748b; margin:4px 0 0 0;">
              Upload institutional JSON (<code style="color:#6366f1; font-weight:600;">cit_public.json</code>) or input the <strong>9 official CSV spreadsheets</strong> simultaneously. Solvers automatically decide and commit the 0-clash schedule.
            </p>
          </div>
          <div style="display:flex; gap:8px; flex-wrap:wrap;">
            <button class="btn btn-outline" onclick="document.getElementById('datasetFileInput').click()" title="Select multiple CSV files simultaneously">
              <span>&#128194;</span> Select Multiple CSVs
            </button>
            <button class="btn btn-outline" onclick="loadCsvDatasetFolderAction()" title="Load all CSV spreadsheets from CrunchWeek_StarterPack/data/csv">
              <span>&#128196;</span> Load CSV Dataset Folder
            </button>
            <button class="btn btn-outline" onclick="resetToOfficialStarterPackAction()" title="Restore clean cit_public.json baseline">
              <span>&#8635;</span> Restore Baseline Dataset
            </button>
          </div>
        </div>

        <!-- Drag & Drop Upload Zone -->
        <div id="datasetDropZone" style="border: 2px dashed #6366f1; border-radius: 10px; padding: 22px; text-align: center; background: #f8fafc; cursor: pointer; transition: all 0.2s ease;"
             onclick="document.getElementById('datasetFileInput').click()"
             ondragover="event.preventDefault(); this.style.borderColor='#4338ca'; this.style.background='#eef2ff';"
             ondragleave="this.style.borderColor='#6366f1'; this.style.background='#f8fafc';"
             ondrop="handleDatasetFileDrop(event)">
          <input type="file" id="datasetFileInput" accept=".json,.csv" multiple style="display:none;" onchange="handleDatasetFileSelect(event)">
          <div style="font-size: 2.2rem; margin-bottom: 6px;">&#128229;</div>
          <div style="font-weight: 700; font-size: 0.98rem; color: #1e293b;">
            Drop <code style="color:#4f46e5;">cit_public.json</code> or multiple CSV files here (all 9 CSVs supported), or <span style="color:#4f46e5; text-decoration:underline;">browse files</span>
          </div>
          <div style="font-size: 0.78rem; color: #64748b; margin-top: 4px;">
            Multi-selection supported: <code>rooms.csv</code>, <code>courses.csv</code>, <code>sessions.csv</code>, <code>faculty.csv</code>, <code>student_groups.csv</code>, <code>exams.csv</code>, <code>booking_requests.csv</code>, <code>room_unavailability.csv</code>, <code>cancellations.csv</code>
          </div>
        </div>

        <!-- 9-CSV Dataset Ingestion Matrix (3x3 Grid) -->
        <div id="datasetMatrixContainer" style="margin-top: 18px;">
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; flex-wrap:wrap; gap:8px;">
            <div style="font-size:0.85rem; font-weight:700; color:#334155; text-transform:uppercase; letter-spacing:0.04em; display:flex; align-items:center; gap:6px;">
              <span>&#128202;</span> 9-Spreadsheet Ingestion Matrix
            </div>
            <div id="matrixBatchStatusBadge" style="font-size:0.78rem; font-weight:600; color:#4338ca; background:#eef2ff; padding:3px 10px; border-radius:12px; border:1px solid #c7d2fe;">
              Baseline Benchmark Active (9/9 Tables Ready)
            </div>
          </div>
          <div class="matrix-grid" id="csvMatrixGrid" style="display:grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px;">
            <!-- Matrix cards rendered by TS/JS -->
          </div>
        </div>

        <!-- Ingestion Actions & Solve Timetable Bar -->
        <div id="datasetUploadPreview" style="display:none; margin-top: 16px; padding: 14px 18px; background: #f8fafc; border-radius: 8px; border: 1px solid #cbd5e1;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:10px;">
            <div>
              <span style="font-weight:700; color:#0f172a; font-size:0.92rem;" id="uploadFileName">Dataset Ready for Ingestion</span>
              <span style="font-size:0.8rem; color:#64748b; margin-left:8px;" id="uploadFileSize"></span>
              <div style="font-size:0.82rem; color:#475569; margin-top:4px;" id="uploadFileStats">Parsed: -- rooms, -- faculty, -- sessions</div>
            </div>
            <div style="display:flex; gap:8px; flex-wrap:wrap;">
              <button class="btn btn-outline" id="btnValidateUpload" onclick="validateUploadedDatasetAction()">
                <span>&#10004;</span> Validate Schema
              </button>
              <button class="btn btn-primary" id="btnImportAndSolve" onclick="importAndSolveDatasetAction()" style="background:linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border:none; box-shadow:0 2px 4px rgba(79,70,229,0.3); font-weight:600;">
                <span>&#9889;</span> Ingest &amp; Decide Timetable
              </button>
              <button class="btn btn-outline" id="btnImportUpload" onclick="importUploadedDatasetAction()" style="background:#fff; color:#475569;">
                <span>&#128190;</span> Ingest Only
              </button>
              <button class="btn btn-outline" onclick="cancelDatasetUploadAction()" style="border-color:#ef4444; color:#ef4444;">
                Cancel
              </button>
            </div>
          </div>
          <div id="datasetValidationFeedback" style="margin-top:12px; font-size:0.82rem; display:none;"></div>
        </div>
      </div>

"""

final_lines = lines[:start_idx] + [new_content] + lines[end_idx:]
with open("frontend/index.html", "w", encoding="utf-8") as f:
    f.writelines(final_lines)

print("Updated frontend/index.html successfully")

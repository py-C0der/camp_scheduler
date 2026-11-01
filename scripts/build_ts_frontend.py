import re
from pathlib import Path

backup_path = Path("frontend/index.html.original_backup")
html_text = backup_path.read_text(encoding="utf-8")

# Extract CSS
style_match = re.search(r"<style>(.*?)</style>", html_text, re.DOTALL)
css_code = style_match.group(1).strip() if style_match else ""

# Extract JS
script_match = re.search(r"<script>(.*?)</script>", html_text, re.DOTALL)
js_code = script_match.group(1).strip() if script_match else ""

# Write CSS
Path("frontend/css/main.css").write_text(css_code, encoding="utf-8")
Path("public/css/main.css").write_text(css_code, encoding="utf-8")
print("Wrote frontend/css/main.css and public/css/main.css")

# Prepare TypeScript modules
# We can create clean TS modules and a master main.ts that exports and binds to window
lines = js_code.splitlines()

# Lines ranges:
# Modal & Dashboard & Nav: 0 to 370
# Auth & Timetable: 371 to 1174
# Dataset & Ingestion: 1175 to 1395
# Exams: 1396 to 1701
# Bookings: 1702 to 2233
# Disruptions: 2234 to 2732
# Notifications: 2733 to 3222
# AI Assistant: 3223 to end

mod_dashboard = "\n".join(lines[0:371])
mod_auth_timetable = "\n".join(lines[371:1175])
mod_validations = "\n".join(lines[1175:1396])
mod_exams = "\n".join(lines[1396:1702])
mod_bookings = "\n".join(lines[1702:2234])
mod_disruptions = "\n".join(lines[2234:2733])
mod_notifications = "\n".join(lines[2733:3223])
mod_ai_assistant = "\n".join(lines[3223:])

# Save individual TypeScript modules
Path("frontend/src/dashboard.ts").write_text(f"""// CIT Campus Dashboard & Navigation Module
import {{ api }} from './api';
import {{ User, TimetableSession }} from './types';

declare const window: any;
declare const document: any;

{mod_dashboard}
""", encoding="utf-8")

Path("frontend/src/auth_timetable.ts").write_text(f"""// CIT Campus Identity, Role Management & Timetable Solver Module
import {{ api }} from './api';
import {{ User, UserRole, TimetableSession }} from './types';

declare const window: any;
declare const document: any;

{mod_auth_timetable}
""", encoding="utf-8")

Path("frontend/src/validations.ts").write_text(f"""// CIT Campus Constraints Audit & Dataset Management Module
import {{ api }} from './api';
import {{ ValidationRule, ValidationAuditSummary, DatasetInfoSummary }} from './types';

declare const window: any;
declare const document: any;

{mod_validations}
""", encoding="utf-8")

Path("frontend/src/exams.ts").write_text(f"""// CIT Campus Mid-Semester Examination Scheduler Module
import {{ api }} from './api';
import {{ ExamEntry }} from './types';

declare const window: any;
declare const document: any;

{mod_exams}
""", encoding="utf-8")

Path("frontend/src/bookings.ts").write_text(f"""// CIT Campus Smart Venue Booking & Spectra Management Module
import {{ api }} from './api';
import {{ BookingRequest, BookingTimeWindow }} from './types';

declare const window: any;
declare const document: any;

{mod_bookings}
""", encoding="utf-8")

Path("frontend/src/disruptions.ts").write_text(f"""// CIT Campus Disruption Engine & Rescheduling Module
import {{ api }} from './api';
import {{ DisruptionReport, RescheduleProposal }} from './types';

declare const window: any;
declare const document: any;

{mod_disruptions}
""", encoding="utf-8")

Path("frontend/src/notifications.ts").write_text(f"""// CIT Campus Real-Time Notification & Alerts Hub Module
import {{ api }} from './api';
import {{ CampusNotification }} from './types';

declare const window: any;
declare const document: any;

{mod_notifications}
""", encoding="utf-8")

Path("frontend/src/ai_assistant.ts").write_text(f"""// CIT Campus AI Scheduling Assistant & Decision Explainability Module
import {{ api }} from './api';

declare const window: any;
declare const document: any;

{mod_ai_assistant}
""", encoding="utf-8")

# Master entrypoint main.ts
Path("frontend/src/main.ts").write_text("""/**
 * CIT Campus Scheduling and Venue Management Platform
 * Application Master Bootstrap
 */

import './types';
import './api';
import './dashboard';
import './auth_timetable';
import './validations';
import './exams';
import './bookings';
import './disruptions';
import './notifications';
import './ai_assistant';

console.log('[CIT Platform] Modern TypeScript Application Initialized.');
""", encoding="utf-8")

print("Created all TypeScript modules in frontend/src/")

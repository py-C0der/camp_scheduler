/**
 * CIT Campus Scheduling and Venue Management Platform
 * Unified TypeScript Type Definitions
 */

export type UserRole = 'admin' | 'dept_coordinator' | 'faculty' | 'club_rep';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  department?: string;
  faculty_id?: string;
  is_active?: boolean;
}

export interface AuthState {
  currentUser: User;
  token?: string;
  isAuthenticated: boolean;
}

export interface Room {
  id: string;
  name: string;
  building: string;
  type: string;
  capacity: number;
  features: string[];
  accessible: boolean;
  allowed_uses: string[];
}

export interface StudentGroup {
  id: string;
  name: string;
  year: number;
  department: string;
  size: number;
  needs_accessible: boolean;
}

export interface Course {
  id: string;
  title: string;
  department: string;
  year: number;
  lecture_hours: number;
  tutorial_hours: number;
  lab_blocks: number;
}

export interface Faculty {
  id: string;
  name: string;
  department: string;
  max_hours_per_day: number;
  needs_accessible: boolean;
  unavailable: Array<{ day: string; periods: number[]; reason?: string }>;
  preferences: Array<{ type: string; days?: string[]; periods?: number[]; note?: string }>;
}

export interface TimetableSession {
  id: string;
  course_id: string;
  kind: 'lecture' | 'tutorial' | 'lab';
  groups: string[];
  faculty_id: string;
  size: number;
  duration: number;
  room_types: string[];
  needs_accessible: boolean;
  basket_slot?: string | null;
  fixed_slot?: { day: string; start_period: number } | null;
  day?: string;
  start_period?: number;
  room_id?: string;
}

export interface TimetableGridSlot {
  session_id: string;
  course_id: string;
  kind: string;
  groups: string[];
  faculty_id: string;
  faculty_name?: string;
  room_id: string;
  day: string;
  start_period: number;
  duration: number;
  is_clash?: boolean;
  is_disrupted?: boolean;
}

export interface ExamEntry {
  exam_id: string;
  course_ids: string[];
  groups: string[];
  size: number;
  duration_hours: number;
  day: string;
  session: 'AM' | 'PM';
  rooms: string[];
  status?: string;
}

export interface BookingTimeWindow {
  day: string;
  from_period: number;
  to_period: number;
}

export interface BookingRequest {
  id: string;
  submitted_at: string;
  requester: string;
  role: 'admin' | 'department_coordinator' | 'faculty' | 'club';
  requested_category: 'institute_event' | 'dept_event' | 'guest_lecture' | 'club_event';
  effective_category?: string;
  title: string;
  attendance: number;
  duration_periods: number;
  windows: BookingTimeWindow[];
  room_types: string[];
  needs: string[];
  requested_room?: string | null;
  mandatory_for_groups?: string[];
  status: 'approved' | 'rejected' | 'alternative_offered' | 'pending';
  reason?: string;
  decision_reason?: string;
  assigned_room_id?: string | null;
  assigned_day?: string | null;
  assigned_start_period?: number | null;
  assigned_end_period?: number | null;
  created_by?: string;
  alternative_options?: Array<{
    day: string;
    start_period: number;
    end_period: number;
    room_id: string;
    score: number;
  }>;
}

export interface DisruptionChangeItem {
  type: 'faculty_unavailable' | 'room_unavailable' | 'add_faculty' | 'add_session' | 'remove_session';
  faculty_id?: string;
  room_id?: string;
  days?: string[];
  periods?: number[];
  reason?: string;
  faculty?: Partial<Faculty>;
  session?: Partial<TimetableSession>;
  session_id?: string;
}

export interface DisruptionReport {
  id: string;
  submitted_at: string;
  reported_by: string;
  reason: string;
  changes: DisruptionChangeItem[];
  status: 'PENDING' | 'RESOLVED' | 'SUPERSEDED';
}

export interface RescheduleProposal {
  id: string;
  disruption_id: string;
  created_at: string;
  created_by: string;
  solver_status: 'OPTIMAL' | 'FEASIBLE' | 'INFEASIBLE';
  sessions_moved_count: number;
  stability_score: number;
  moved_sessions: Array<{
    session_id: string;
    course_id: string;
    old_day: string;
    old_start_period: number;
    old_room_id: string;
    new_day: string;
    new_start_period: number;
    new_room_id: string;
    reason?: string;
  }>;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
}

export interface ValidationRule {
  code: string;
  name: string;
  category: 'hard' | 'soft';
  description: string;
  penalty_weight?: number;
  can_validate: boolean;
  status: 'PASS' | 'FAIL' | 'OPTIMIZED' | 'EXTENDED SCOPE';
  violations_count: number;
  details?: string;
  hard_constraint: boolean;
}

export interface ValidationAuditSummary {
  overall_academic_status: 'FULLY COMPLIANT' | 'VIOLATIONS DETECTED';
  total_rules: number;
  validated_rules: number;
  future_module_rules: number;
  hard_violations_count: number;
  soft_penalties: {
    S1?: number;
    S2?: number;
    S3?: number;
    S4?: number;
    S5?: number;
    S6?: number;
  };
  official_validator?: {
    returncode: number;
    stdout: string;
    stderr?: string;
  };
}

export interface CampusNotification {
  id: string;
  title: string;
  message: string;
  created_at: string;
  category: 'SCHEDULE_CHANGE' | 'EXAM_ALERT' | 'BOOKING_UPDATE' | 'DISRUPTION_ALERT' | 'SYSTEM';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  is_read: boolean;
  related_domain?: string;
  related_record_id?: string;
}

export interface DatasetInfoSummary {
  dataset_id: string;
  description: string;
  counts: {
    rooms: number;
    faculty: number;
    student_groups: number;
    courses: number;
    sessions: number;
    exams: number;
    booking_requests: number;
  };
}

/**
 * CIT Campus Scheduling and Venue Management Platform
 * Typed HTTP API Client Module
 */

import {
  User,
  TimetableSession,
  ExamEntry,
  BookingRequest,
  DisruptionReport,
  RescheduleProposal,
  ValidationAuditSummary,
  ValidationRule,
  CampusNotification,
  DatasetInfoSummary
} from './types';

class ApiClient {
  private getAuthHeader(): Record<string, string> {
    const token = localStorage.getItem('cit_token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
  }

  private async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const headers = {
      'Content-Type': 'application/json',
      ...this.getAuthHeader(),
      ...(options.headers || {})
    };

    const response = await fetch(endpoint, { ...options, headers });
    if (!response.ok) {
      let errorMsg = `API Error ${response.status}: ${response.statusText}`;
      try {
        const errorJson = await response.json();
        errorMsg = errorJson.detail || errorJson.message || errorMsg;
      } catch (_) {}
      throw new Error(errorMsg);
    }
    return response.json();
  }

  // --- Auth APIs ---
  async login(email: string, password: string): Promise<{ token: string; user: User }> {
    return this.request('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password })
    });
  }

  async getMe(): Promise<{ user: User }> {
    return this.request('/api/auth/me');
  }

  async getRoles(): Promise<{ users: User[]; active_user: string }> {
    return this.request('/api/auth/roles');
  }

  async switchUser(userId: string): Promise<{ success: boolean; active_user: string }> {
    return this.request('/api/auth/switch', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId })
    });
  }

  // --- Timetable APIs ---
  async getTimetableGrid(filterType?: string, filterValue?: string): Promise<{
    sessions: TimetableSession[];
    groups: string[];
    faculty: Array<{ id: string; name: string }>;
    rooms: Array<{ id: string; name: string; capacity: number }>;
  }> {
    const params = new URLSearchParams();
    if (filterType && filterValue) {
      params.append(filterType, filterValue);
    }
    return this.request(`/api/timetable/grid?${params.toString()}`);
  }

  async generateTimetable(): Promise<{ success: boolean; message: string; hard_violations: number }> {
    return this.request('/api/timetable/generate', { method: 'POST' });
  }

  async getValidations(): Promise<{ summary: ValidationAuditSummary; rules: ValidationRule[] }> {
    return this.request('/api/timetable/validations');
  }

  async runOfficialValidation(): Promise<{
    success: boolean;
    official_validator: { returncode: number; stdout: string; stderr: string };
  }> {
    return this.request('/api/timetable/validate', { method: 'POST' });
  }

  // --- Exam APIs ---
  async getExamsList(): Promise<{ exams: ExamEntry[] }> {
    return this.request('/api/exams');
  }

  async getExamSummary(): Promise<any> {
    return this.request('/api/exams/summary');
  }

  async solveExams(): Promise<any> {
    return this.request('/api/exams/solve', { method: 'POST' });
  }

  async validateExams(): Promise<any> {
    return this.request('/api/exams/validate', { method: 'POST' });
  }

  async approveExams(userId: string): Promise<any> {
    return this.request('/api/exams/approve', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId })
    });
  }

  // --- Venue Booking APIs ---
  async getBookings(): Promise<{ bookings: BookingRequest[]; summary?: any }> {
    return this.request('/api/bookings');
  }

  async getBookingDetail(bookingId: string): Promise<BookingRequest> {
    return this.request(`/api/bookings/${bookingId}`);
  }

  async submitBooking(payload: any): Promise<{ success: boolean; booking: BookingRequest }> {
    return this.request('/api/bookings/submit', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async runSpectraAutoDecide(): Promise<any> {
    return this.request('/api/bookings/auto-decide', { method: 'POST' });
  }

  async approveBooking(bookingId: string, userId: string, userRole: string): Promise<any> {
    return this.request(`/api/bookings/${bookingId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, user_role: userRole })
    });
  }

  async rejectBooking(bookingId: string, reason: string, userId: string, userRole: string): Promise<any> {
    return this.request(`/api/bookings/${bookingId}/reject`, {
      method: 'POST',
      body: JSON.stringify({ reason, user_id: userId, user_role: userRole })
    });
  }

  async cancelBooking(bookingId: string, userId: string): Promise<any> {
    return this.request(`/api/bookings/${bookingId}/cancel`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId })
    });
  }

  async acceptAlternativeOffer(altId: string, userId: string): Promise<any> {
    return this.request(`/api/bookings/${altId}/accept-alternative`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId })
    });
  }

  // --- Disruption APIs ---
  async getDisruptions(): Promise<{ disruptions: DisruptionReport[]; proposals: RescheduleProposal[] }> {
    return this.request('/api/disruptions');
  }

  async reportDisruption(payload: any): Promise<any> {
    return this.request('/api/disruptions/report', {
      method: 'POST',
      body: JSON.stringify(payload)
    });
  }

  async getImpactAnalysis(disruptionId: string): Promise<any> {
    return this.request(`/api/disruptions/${disruptionId}/impact`);
  }

  async triggerReschedule(disruptionId: string, userId: string): Promise<any> {
    return this.request(`/api/disruptions/${disruptionId}/reschedule`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId })
    });
  }

  async getProposalDetail(proposalId: string): Promise<any> {
    return this.request(`/api/disruptions/proposals/${proposalId}`);
  }

  async approveProposal(proposalId: string, userId: string, userRole: string): Promise<any> {
    return this.request(`/api/disruptions/proposals/${proposalId}/approve`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId, user_role: userRole })
    });
  }

  // --- Dataset Management APIs ---
  async getDatasetInfo(): Promise<DatasetInfoSummary> {
    return this.request('/api/admin/dataset/info');
  }

  async validateDataset(dataset: any): Promise<any> {
    return this.request('/api/admin/dataset/validate', {
      method: 'POST',
      body: JSON.stringify({ dataset })
    });
  }

  async importDataset(dataset: any, userRole: string, userId: string): Promise<any> {
    return this.request('/api/admin/dataset/import', {
      method: 'POST',
      body: JSON.stringify({ dataset, user_role: userRole, user_id: userId })
    });
  }

  async loadCsvDataset(userRole: string = 'admin', userId: string = 'admin_1'): Promise<any> {
    return this.request(`/api/admin/dataset/load-csv?user_role=${userRole}&user_id=${userId}`, {
      method: 'POST'
    });
  }

  async resetDemo(userRole: string = 'admin', userId: string = 'admin_1'): Promise<any> {
    return this.request(`/api/admin/dataset/reset-demo?user_role=${userRole}&user_id=${userId}`, {
      method: 'POST'
    });
  }

  // --- AI Scheduling Assistant APIs ---
  async askAi(query: string, userRole: string, userId: string): Promise<any> {
    return this.request('/api/ai/chat', {
      method: 'POST',
      body: JSON.stringify({ query, user_role: userRole, user_id: userId })
    });
  }

  async explainDecision(entityType: string, entityId: string): Promise<any> {
    return this.request('/api/ai/explain', {
      method: 'POST',
      body: JSON.stringify({ entity_type: entityType, entity_id: entityId })
    });
  }

  // --- Notification APIs ---
  async getNotifications(userId: string): Promise<{ notifications: CampusNotification[] }> {
    return this.request(`/api/notifications?user_id=${userId}`);
  }

  async getUnreadCount(userId: string): Promise<{ unread_count: number }> {
    return this.request(`/api/notifications/unread-count?user_id=${userId}`);
  }

  async markNotificationRead(id: string, userId: string): Promise<any> {
    return this.request(`/api/notifications/${id}/read`, {
      method: 'POST',
      body: JSON.stringify({ user_id: userId })
    });
  }

  async markAllNotificationsRead(userId: string): Promise<any> {
    return this.request('/api/notifications/read-all', {
      method: 'POST',
      body: JSON.stringify({ user_id: userId })
    });
  }
}

export const api = new ApiClient();

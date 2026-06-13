const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'
export const examSocketUrl = (examId: string) => {
  const token = window.localStorage.getItem('examguard-access-token') ?? ''
  return `${API_BASE.replace(/^http/, 'ws')}/ws/exams/${examId}?token=${encodeURIComponent(token)}`
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = window.localStorage.getItem('examguard-access-token')
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(Array.isArray(error.detail) ? error.detail.join(' ') : error.detail || response.statusText)
  }
  return response.json() as Promise<T>
}

async function requestRaw(path: string, options: RequestInit = {}): Promise<Response> {
  const token = window.localStorage.getItem('examguard-access-token')
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(Array.isArray(error.detail) ? error.detail.join(' ') : error.detail || response.statusText)
  }
  return response
}

// --- Types ------------------------------------------------------------------

export type ApiUser = {
  id: string
  email: string
  display_name: string
  role: 'teacher' | 'student'
}

export type ApiExam = {
  id: string
  teacher_id: string
  title: string
  subject: string
  duration_minutes: number
  total_marks: number
  join_code: string
  status: string
  paper_config?: Record<string, unknown>
  activated_at?: string | null
  ended_at?: string | null
  created_at?: string
}

export type ApiMaterial = {
  id: string
  exam_id: string
  filename: string
  status: string
  chunk_count: number
  chapter_counts: Record<string, number>
  source_type?: 'syllabus' | 'material'
}

export type ApiQuestion = {
  id: string
  exam_id: string
  section_id: string
  type: string
  text: string
  options: string[]
  correct_answer: string
  marks: number
  bloom_level: string
  chapter_tag: string
  source_chunk_ids: (string | number)[]
  groundedness: number
  teacher_modified: boolean
}

export type ApiSession = {
  id: string
  student_id: string
  student_name: string
  exam_id: string
  status: string
  consent: boolean
  liveness: boolean
  integrity: {
    score: number
    status: string
    ci: number | null
    baseline_tier: number
    factors?: Record<string, number>
  }
  review_status: string
  grade_released: boolean
  answers_count?: number
  events_count?: number
  joined_at?: string
  grade?: { earned_marks: number; total_marks: number; percentage: number }
}

export type ApiAnswer = {
  id: string
  session_id: string
  question_id: string
  answer_text: string
  selected_option?: string | null
  time_spent_seconds: number
  saved_at?: string
}

export type ApiReportSummary = {
  exam_id: string
  total_students: number
  average_integrity: number
  min_integrity: number
  max_integrity: number
  status_counts: Record<string, number>
  appeals_open: number
}

export type ApiExamReports = {
  exam_id: string
  reports_ready: number
  students: ApiSession[]
  average_integrity: number
}

// --- API Client -------------------------------------------------------------

export const api = {
  // Auth
  login: (payload: { email: string; password: string; role: 'teacher' | 'student'; display_name?: string }) =>
    request<{ user: ApiUser; token: string }>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),

  signup: (payload: { email: string; password: string; role: 'teacher' | 'student'; display_name?: string }) =>
    request<{ user: ApiUser; token: string }>('/auth/signup', { method: 'POST', body: JSON.stringify(payload) }),

  resetRequest: (email: string) =>
    request<{ status: string }>('/auth/reset-request', { method: 'POST', body: JSON.stringify({ email }) }),

  resetConfirm: (password: string, token: string) =>
    request<{ status: string }>('/auth/reset-confirm', { method: 'POST', body: JSON.stringify({ password, token }) }),

  // Exams
  exams: (teacherId?: string) => request<ApiExam[]>(`/exams${teacherId ? `?teacher_id=${teacherId}` : ''}`),

  getExam: (examId: string) => request<ApiExam>(`/exams/${examId}`),

  createExam: (payload: { teacher_id: string; title: string; subject: string; duration_minutes: number; total_marks: number }) =>
    request<ApiExam>('/exams', { method: 'POST', body: JSON.stringify(payload) }),

  deleteExam: (examId: string) =>
    request<{ status: string }>(`/exams/${examId}`, { method: 'DELETE' }),

  cloneExam: (examId: string) =>
    request<ApiExam>(`/exams/${examId}/clone`, { method: 'POST' }),

  activateExam: (examId: string) =>
    request<ApiExam>(`/exams/${examId}/activate`, { method: 'POST' }),

  pauseExam: (examId: string) =>
    request<ApiExam>(`/exams/${examId}/pause`, { method: 'POST' }),

  resumeExam: (examId: string) =>
    request<ApiExam>(`/exams/${examId}/resume`, { method: 'POST' }),

  endExam: (examId: string) =>
    request<ApiExam>(`/exams/${examId}/end`, { method: 'POST' }),

  examStudents: (examId: string) =>
    request<ApiSession[]>(`/exams/${examId}/students`),

  // Materials
  materials: (examId: string) => request<ApiMaterial[]>(`/exams/${examId}/materials`),

  uploadMaterial: (examId: string, file: File, sourceType: 'syllabus' | 'material' = 'material') => {
    const form = new FormData()
    form.append('file', file)
    return request<ApiMaterial>(`/materials/upload?exam_id=${examId}&source_type=${sourceType}`, { method: 'POST', body: form })
  },

  deleteMaterial: (materialId: string) =>
    request<{ status: string }>(`/materials/${materialId}`, { method: 'DELETE' }),

  // Paper Config
  savePaperConfig: (examId: string, payload: unknown) =>
    request(`/exams/${examId}/paper-config`, { method: 'PUT', body: JSON.stringify(payload) }),

  generatePaper: (examId: string) =>
    request<{ status: string; count: number; questions: ApiQuestion[] }>(`/exams/${examId}/generate`, { method: 'POST' }),

  // Sessions
  joinSession: (payload: { join_code: string; student_name: string; email?: string }) =>
    request<ApiSession>('/sessions/join', { method: 'POST', body: JSON.stringify(payload) }),

  saveConsent: (sessionId: string) =>
    request<ApiSession>(`/sessions/${sessionId}/consent`, { method: 'POST' }),

  saveLiveness: (sessionId: string, evidence: { method: 'mediapipe_ear'; blink_count: number; duration_ms: number; threshold: number }) =>
    request<ApiSession>(`/sessions/${sessionId}/liveness`, { method: 'POST', body: JSON.stringify(evidence) }),

  sessionQuestions: (sessionId: string) =>
    request<ApiQuestion[]>(`/sessions/${sessionId}/questions`),

  sessionExam: (sessionId: string) =>
    request<Pick<ApiExam, 'id' | 'title' | 'subject' | 'duration_minutes' | 'total_marks' | 'status'>>(`/sessions/${sessionId}/exam`),

  saveAnswer: (sessionId: string, payload: { question_id: string; answer_text: string; selected_option?: string; time_spent_seconds?: number }) =>
    request<ApiAnswer>(`/sessions/${sessionId}/answers`, { method: 'POST', body: JSON.stringify(payload) }),

  endSession: (sessionId: string) =>
    request<ApiSession>(`/sessions/${sessionId}/end`, { method: 'POST' }),

  sessionIntegrity: (sessionId: string) =>
    request<Record<string, unknown>>(`/sessions/${sessionId}/integrity`),

  sessionResult: (sessionId: string) =>
    request<{ session_id: string; student_name: string; status: string; integrity: Record<string, any>; review_status: string; grade_released: boolean; answers_count: number; answers: ApiAnswer[]; grade?: { earned_marks: number; total_marks: number; percentage: number } }>(`/sessions/${sessionId}/result`),

  // Appeals & Review
  submitAppeal: (sessionId: string, response: string) =>
    request<{ response: string; submitted_at: string; status: string }>(`/sessions/${sessionId}/appeal`, { method: 'POST', body: JSON.stringify({ response }) }),

  teacherDecision: (sessionId: string, decision: 'clear' | 'confirm_flag', teacher_note: string) =>
    request(`/sessions/${sessionId}/decision`, { method: 'PUT', body: JSON.stringify({ decision, teacher_note }) }),

  // Proctoring Events
  logEvent: (sessionId: string, event_type: string, metadata: Record<string, unknown> = {}) =>
    request<{ status: string }>(`/sessions/${sessionId}/events`, { method: 'POST', body: JSON.stringify({ event_type, metadata }) }),

  // Reports
  examReports: (examId: string) =>
    request<ApiExamReports>(`/exams/${examId}/reports`),

  examSummary: (examId: string) =>
    request<ApiReportSummary>(`/exams/${examId}/reports/summary`),

  generateReport: (sessionId: string) =>
    request<{ status: string; download_url: string }>(`/sessions/${sessionId}/reports/generate`, { method: 'POST' }),

  downloadReportPdf: (sessionId: string) =>
    requestRaw(`/sessions/${sessionId}/reports/pdf`),

  downloadReportsCsv: (examId: string) =>
    requestRaw(`/exams/${examId}/reports/csv`),

  downloadExamReportPdf: (examId: string) =>
    requestRaw(`/exams/${examId}/reports/pdf`),

  // Settings
  saveSettings: (userId: string, payload: { display_name: string; institute_name: string; email_on_flag?: boolean }) =>
    request(`/users/${userId}/settings`, { method: 'PUT', body: JSON.stringify(payload) }),
}

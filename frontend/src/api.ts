const API_BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000/api/v1'

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      ...(options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...options.headers,
    },
  })
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }))
    throw new Error(Array.isArray(error.detail) ? error.detail.join(' ') : error.detail || response.statusText)
  }
  return response.json() as Promise<T>
}

export type ApiUser = {
  id: string
  email: string
  display_name: string
  role: 'teacher' | 'student'
}

export type ApiExam = {
  id: string
  title: string
  subject: string
  duration_minutes: number
  total_marks: number
  join_code: string
  status: string
}

export type ApiMaterial = {
  id: string
  exam_id: string
  filename: string
  status: string
  chunk_count: number
  chapter_counts: Record<string, number>
}

export const api = {
  login: (payload: { email: string; password: string; role: 'teacher' | 'student'; display_name?: string }) =>
    request<{ user: ApiUser; token: string }>('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  exams: (teacherId?: string) => request<ApiExam[]>(`/exams${teacherId ? `?teacher_id=${teacherId}` : ''}`),
  materials: (examId: string) => request<ApiMaterial[]>(`/exams/${examId}/materials`),
  uploadMaterial: (examId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<ApiMaterial>(`/materials/upload?exam_id=${examId}`, { method: 'POST', body: form })
  },
  savePaperConfig: (examId: string, payload: unknown) =>
    request(`/exams/${examId}/paper-config`, { method: 'PUT', body: JSON.stringify(payload) }),
  generatePaper: (examId: string) => request<{ status: string; count: number; questions: unknown[] }>(`/exams/${examId}/generate`, { method: 'POST' }),
  joinSession: (payload: { join_code: string; student_name: string; email?: string }) =>
    request<{ id: string; exam_id: string; student_name: string }>('/sessions/join', { method: 'POST', body: JSON.stringify(payload) }),
}

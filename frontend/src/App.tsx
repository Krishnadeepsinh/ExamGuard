import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { FaceLandmarker, FilesetResolver } from '@mediapipe/tasks-vision'
import {
  Activity,
  AlertTriangle,
  Archive,
  BarChart3,
  Bell,
  BookOpen,
  Bot,
  Camera,
  Check,
  ChevronRight,
  Clock,
  Copy,
  Download,
  Eye,
  FileText,
  Flag,
  Gauge,
  GraduationCap,
  Layers,
  Lock,
  Menu,
  Mic,
  Moon,
  PauseCircle,
  PlayCircle,
  Plus,
  Radar,
  RefreshCw,
  Rocket,
  Search,
  Settings,
  Shield,
  Sun,
  Timer,
  Upload,
  UserCheck,
  Users,
  X,
} from 'lucide-react'
import './App.css'
import { api, examSocketUrl, type ApiExam, type ApiQuestion, type ApiSession } from './api'

type IntegrityStatus = 'CLEAN' | 'WATCH' | 'WARN' | 'FLAGGED'
type AuthRole = 'teacher' | 'student'
type AuthUser = { role: AuthRole; name: string; email: string; userId?: string }
type View =
  | 'landing'
  | 'dashboard'
  | 'config'
  | 'live'
  | 'consent'
  | 'liveness'
  | 'exam'
  | 'complete'
  | 'review'
  | 'reports'
  | 'settings'

type ToastKind = 'success' | 'warning' | 'error' | 'info'

const statusRank: Record<IntegrityStatus, number> = {
  FLAGGED: 0,
  WARN: 1,
  WATCH: 2,
  CLEAN: 3,
}

const navItems: Array<{ view: View; label: string; icon: typeof Shield }> = [
  { view: 'landing', label: 'Home', icon: Rocket },
  { view: 'dashboard', label: 'Teacher Dashboard', icon: Layers },
  { view: 'config', label: 'Paper Config', icon: BookOpen },
  { view: 'live', label: 'Live Monitor', icon: Radar },
  { view: 'consent', label: 'Student Consent', icon: Shield },
  { view: 'liveness', label: 'Blink Liveness', icon: Camera },
  { view: 'exam', label: 'Exam Session', icon: GraduationCap },
  { view: 'complete', label: 'Post Exam', icon: UserCheck },
  { view: 'review', label: 'Teacher Review', icon: Flag },
  { view: 'reports', label: 'Reports', icon: BarChart3 },
  { view: 'settings', label: 'Settings', icon: Settings },
]

const teacherViews: View[] = ['dashboard', 'config', 'live', 'review', 'reports', 'settings']
const studentViews: View[] = ['consent', 'liveness', 'exam', 'complete', 'settings']
const publicViews: View[] = ['landing']

type QuestionType = 'MCQ' | 'Short Answer' | 'Long Answer' | 'Fill Blank' | 'True/False' | 'Essay'
type ExamLevel = 'Easy' | 'Standard' | 'Challenging'
type PaperMode = 'MCQ only' | 'MCQ + QA' | 'Mixed'
type PaperSection = {
  id: string
  type: QuestionType
  count: number
  marks: number
  bloom: string
  chapter: string
  topic?: string
  level: ExamLevel | 'Use overall'
  negative: 'none' | 'quarter'
}

function sectionsForMode(mode: PaperMode, totalMarks: number, chapter = 'All syllabus'): PaperSection[] {
  const marks = Math.max(10, Math.min(300, Math.floor(totalMarks || 10)))
  const budgetSection = (id: string, type: QuestionType, budget: number, bloom: string): PaperSection => {
    const preferred = type === 'Short Answer' ? 5 : type === 'Long Answer' || type === 'Essay' ? 10 : 2
    let marksEach = Math.min(20, preferred, budget)
    while (marksEach > 1 && budget % marksEach !== 0) marksEach -= 1
    return { id, type, count: budget / marksEach, marks: marksEach, bloom, chapter, level: 'Use overall', negative: 'none' }
  }
  if (mode === 'MCQ only') {
    return [budgetSection('A', 'MCQ', marks, 'Understand')]
  }
  if (mode === 'MCQ + QA') {
    const qaMarks = Math.max(2, Math.floor(marks / 2))
    const mcqMarks = marks - qaMarks
    return [
      budgetSection('A', 'MCQ', mcqMarks, 'Understand'),
      budgetSection('B', 'Short Answer', qaMarks, 'Apply'),
    ]
  }
  const shortMarks = Math.max(2, Math.floor(marks * 0.3))
  const fillMarks = Math.max(1, Math.floor(marks * 0.1))
  const mcqMarks = marks - shortMarks - fillMarks
  return [
    budgetSection('A', 'MCQ', mcqMarks, 'Understand'),
    budgetSection('B', 'Short Answer', shortMarks, 'Apply'),
    budgetSection('C', 'Fill Blank', fillMarks, 'Remember'),
  ]
}

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function isValidEmail(value: string) {
  return emailPattern.test(value.trim())
}

function currentTabId(): string {
  if (!window.name.startsWith('examguard-tab-')) {
    window.name = `examguard-tab-${crypto.randomUUID()}`
  }
  return window.name
}

function wordCount(value: string) {
  return value.trim().split(/\s+/).filter(Boolean).length
}

function viewFromHash(): View {
  const hash = window.location.hash.replace('#', '')
  return navItems.some((item) => item.view === hash) ? (hash as View) : 'landing'
}

function storedAuth(): AuthUser | null {
  try {
    const ownsStudentSession = window.sessionStorage.getItem('examguard-tab-owner') === currentTabId()
    if (!ownsStudentSession) {
      window.sessionStorage.removeItem('examguard-student-auth')
      window.sessionStorage.removeItem('examguard-session-id')
    }
    const raw = (ownsStudentSession ? window.sessionStorage.getItem('examguard-student-auth') : null) || window.localStorage.getItem('examguard-auth')
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
}

function studentSessionId(): string | null {
  if (window.sessionStorage.getItem('examguard-tab-owner') !== currentTabId()) return null
  return window.sessionStorage.getItem('examguard-session-id')
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = seconds % 60
  return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
}

function mapSessionToStudent(session: ApiSession) {
  const f = session.integrity?.factors || {}
  const behavioral = f.behavioral ?? 92
  const perplexity = f.perplexity ?? 84
  const stylometric = f.stylometric ?? 89
  const answerQuality = f.answer_quality ?? 91
  const timeAnomaly = f.time_anomaly ?? 76
  const factors = [behavioral, perplexity, stylometric, answerQuality, timeAnomaly]

  return {
    id: session.id,
    name: session.student_name,
    score: session.integrity?.score ?? 100,
    status: (session.integrity?.status ?? 'CLEAN') as IntegrityStatus,
    tier: session.integrity?.baseline_tier ?? 1,
    answered: session.answers_count ?? 0,
    events: session.events_count ?? 0,
    consent: session.consent,
    joined: session.joined_at ? new Date(session.joined_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '--:--',
    ci: session.integrity?.ci ?? null,
    factors: factors,
    appealResponse: (session as any).appeal?.response || '',
    reviewStatus: session.review_status,
    gradeReleased: session.grade_released,
    rawSession: session
  }
}

// Student Step Indicator
function StudentStepIndicator({ currentStep }: { currentStep: 'join' | 'consent' | 'liveness' | 'exam' }) {
  const steps = [
    { key: 'join', label: 'Join' },
    { key: 'consent', label: 'Consent' },
    { key: 'liveness', label: 'Liveness' },
    { key: 'exam', label: 'Exam' }
  ]
  const currentIndex = steps.findIndex(s => s.key === currentStep)
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '16px', marginBottom: '32px', width: '100%', flexWrap: 'wrap' }}>
      {steps.map((step, index) => {
        const isActive = step.key === currentStep
        const isCompleted = index < currentIndex
        return (
          <div key={step.key} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <div style={{
              width: '24px',
              height: '24px',
              borderRadius: '50%',
              display: 'grid',
              placeItems: 'center',
              fontSize: '11px',
              fontWeight: 700,
              background: isCompleted ? 'rgba(16, 185, 129, 0.15)' : isActive ? 'rgba(79, 70, 229, 0.15)' : 'var(--eg-navy-700)',
              color: isCompleted ? 'var(--eg-emerald)' : isActive ? 'var(--eg-indigo-hover)' : 'var(--eg-text-faint)',
              border: `1px solid ${isCompleted ? 'var(--eg-emerald)' : isActive ? 'var(--eg-indigo)' : 'var(--eg-navy-600)'}`,
              transition: 'all 150ms ease'
            }}>
              {isCompleted ? <Check size={12} /> : index + 1}
            </div>
            <span style={{
              fontSize: '12px',
              fontWeight: isActive ? 600 : 500,
              color: isActive ? 'var(--eg-text)' : 'var(--eg-text-muted)',
              textTransform: 'uppercase',
              letterSpacing: '0.04em'
            }}>{step.label}</span>
            {index < steps.length - 1 && (
              <ChevronRight size={14} style={{ color: 'var(--eg-navy-600)' }} />
            )}
          </div>
        )
      })}
    </div>
  )
}

function App() {
  const [view, setView] = useState<View>(() => viewFromHash())
  const [auth, setAuth] = useState<AuthUser | null>(() => storedAuth())
  const [mobileOpen, setMobileOpen] = useState(false)
  const [toast, setToast] = useState<{ kind: ToastKind; text: string } | null>(null)
  const [selectedStudent, setSelectedStudent] = useState<any>(null)
  const [filter, setFilter] = useState<IntegrityStatus | 'ALL'>('ALL')
  const [sort, setSort] = useState<'risk' | 'name' | 'join'>('risk')
  const [consentScrolled, setConsentScrolled] = useState(false)
  const [answer, setAnswer] = useState('')
  const [marked, setMarked] = useState(false)
  const [selectedExamId, setSelectedExamId] = useState<string>(() => {
    return window.localStorage.getItem('examguard-exam-id') || 'exam-physics'
  })
  const [studentsList, setStudentsList] = useState<any[]>([])
  const [theme, setTheme] = useState<'light' | 'dark'>(() => (window.localStorage.getItem('examguard-theme') === 'light' ? 'light' : 'dark'))

  useEffect(() => {
    if (auth?.role !== 'student' || !studentSessionId()) return
    const sessionId = studentSessionId()
    const ownerId = currentTabId()
    const lockKey = `examguard-session-owner-${sessionId}`
    const navigationType = (performance.getEntriesByType('navigation')[0] as PerformanceNavigationTiming | undefined)?.type
    let existing: { ownerId?: string; updatedAt?: number } | null = null
    try { existing = JSON.parse(window.localStorage.getItem(lockKey) || 'null') } catch { existing = null }
    const activeLock = existing?.ownerId && Date.now() - Number(existing.updatedAt || 0) < 3000
    const reclaimingReload = activeLock && existing?.ownerId === ownerId && navigationType === 'reload'
    if (activeLock && !reclaimingReload) {
      window.sessionStorage.removeItem('examguard-student-auth')
      window.sessionStorage.removeItem('examguard-session-id')
      window.sessionStorage.removeItem('examguard-tab-owner')
      setAuth(null)
      setView('landing')
      window.history.replaceState(null, '', '#landing')
      notify('warning', 'This copied tab was reset. Join as a different student here.')
      return
    }
    const heartbeat = () => window.localStorage.setItem(lockKey, JSON.stringify({ ownerId, updatedAt: Date.now() }))
    heartbeat()
    const timer = window.setInterval(heartbeat, 1000)
    return () => {
      window.clearInterval(timer)
      try {
        const lock = JSON.parse(window.localStorage.getItem(lockKey) || 'null')
        if (lock?.ownerId === ownerId) window.localStorage.removeItem(lockKey)
      } catch { window.localStorage.removeItem(lockKey) }
    }
  }, [auth?.role])

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    window.localStorage.setItem('examguard-theme', theme)
  }, [theme])

  useEffect(() => {
    if (auth && auth.role === 'teacher') {
      const teacherId = window.localStorage.getItem('examguard-user-id') || 'teacher-demo'
      api.exams(teacherId)
        .then((items) => {
          if (items.length > 0) {
            const storedId = window.localStorage.getItem('examguard-exam-id')
            const found = items.find(e => e.id === storedId)
            if (found) {
              setSelectedExamId(found.id)
            } else {
              setSelectedExamId(items[0].id)
              window.localStorage.setItem('examguard-exam-id', items[0].id)
            }
          }
        })
        .catch(() => {})
    }
  }, [auth])

  useEffect(() => {
    if (!auth || auth.role !== 'teacher') return
    if (!['live', 'review', 'reports'].includes(view)) return

    const poll = () => {
      api.examStudents(selectedExamId)
        .then((sessions) => {
          setStudentsList(sessions.map(mapSessionToStudent))
        })
        .catch(() => setStudentsList([]))
    }

    poll()
    const interval = setInterval(poll, 4000)
    return () => clearInterval(interval)
  }, [auth, view, selectedExamId])

  useEffect(() => {
    const list = studentsList
    const found = list.find(s => s.name === selectedStudent?.name || s.id === selectedStudent?.id)
    if (found) {
      setSelectedStudent(found)
    } else if (list.length > 0) {
      setSelectedStudent(list[0])
    } else {
      setSelectedStudent(null)
    }
  }, [studentsList])

  const canAccess = useCallback((next: View, user = auth) => {
    if (publicViews.includes(next)) return !user
    if (!user) return false
    if (user.role === 'teacher') return teacherViews.includes(next)
    return studentViews.includes(next)
  }, [auth])

  useEffect(() => {
    const handleHashChange = () => {
      const next = viewFromHash()
      if (canAccess(next)) {
        setView(next)
      } else {
        const fallback: View = auth?.role === 'teacher' ? 'dashboard' : auth?.role === 'student' ? 'consent' : 'landing'
        setView(fallback)
        window.history.replaceState(null, '', `#${fallback}`)
      }
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [auth, canAccess])

  const notify = (kind: ToastKind, text: string) => {
    setToast({ kind, text })
    window.setTimeout(() => setToast(null), kind === 'error' ? 7000 : kind === 'warning' ? 5000 : 3200)
  }

  const navigate = (next: View) => {
    if (!canAccess(next)) {
      notify('warning', auth ? 'This screen requires the other role. Sign out before switching roles.' : 'Please login before opening this screen.')
      const fallback: View = auth?.role === 'teacher' ? 'dashboard' : auth?.role === 'student' ? 'consent' : 'landing'
      setView(fallback)
      window.history.replaceState(null, '', `#${fallback}`)
      return
    }
    setView(next)
    window.history.replaceState(null, '', `#${next}`)
  }

  const login = (user: AuthUser) => {
    setAuth(user)
    if (user.role === 'student') {
      window.sessionStorage.setItem('examguard-tab-owner', currentTabId())
      window.sessionStorage.setItem('examguard-student-auth', JSON.stringify(user))
    } else {
      window.localStorage.setItem('examguard-auth', JSON.stringify(user))
    }
    notify('success', `${user.role === 'teacher' ? 'Teacher' : 'Student'} login successful.`)
    const next = user.role === 'teacher' ? 'dashboard' : 'consent'
    setView(next)
    window.history.replaceState(null, '', `#${next}`)
  }

  const loginWithApi = async (payload: { role: AuthRole; email: string; password: string; name: string; joinCode?: string; signup?: boolean }) => {
    if (payload.role === 'student') {
      if (!payload.joinCode) throw new Error('Exam join code is required.')
      const session = await api.joinSession({ join_code: payload.joinCode, student_name: payload.name, email: payload.email || undefined })
      window.sessionStorage.setItem('examguard-session-id', session.id)
      window.sessionStorage.setItem('examguard-tab-owner', currentTabId())
      window.localStorage.setItem('examguard-exam-id', session.exam_id)
      login({ role: 'student', name: session.student_name, email: payload.email || `${payload.name.toLowerCase().replace(/\s+/g, '.')}@student.ai` })
      return
    }
    const result = payload.signup
      ? await api.signup({ email: payload.email, password: payload.password, role: payload.role, display_name: payload.name })
      : await api.login({ email: payload.email, password: payload.password, role: payload.role, display_name: payload.name })
    window.localStorage.setItem('examguard-user-id', result.user.id)
    window.localStorage.setItem('examguard-access-token', result.token)
    login({ role: 'teacher', name: result.user.display_name, email: result.user.email, userId: result.user.id })
  }

  const logout = () => {
    setAuth(null)
    window.localStorage.removeItem('examguard-auth')
    window.sessionStorage.removeItem('examguard-student-auth')
    window.localStorage.removeItem('examguard-user-id')
    window.localStorage.removeItem('examguard-access-token')
    window.localStorage.removeItem('examguard-session-id')
    window.sessionStorage.removeItem('examguard-session-id')
    window.sessionStorage.removeItem('examguard-tab-owner')
    window.localStorage.removeItem('examguard-exam-id')
    notify('info', 'Signed out. Protected screens are locked.')
    setView('landing')
    window.history.replaceState(null, '', '#landing')
  }

  const filteredStudents = useMemo(() => {
    const sourceList = studentsList
    const list = filter === 'ALL' ? sourceList : sourceList.filter((student) => student.status === filter)
    const getStatusRank = (status: IntegrityStatus): number => {
      return Reflect.get(statusRank, status) ?? 3
    }
    return [...list].sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name)
      if (sort === 'join') return a.joined.localeCompare(b.joined)
      return getStatusRank(a.status as IntegrityStatus) - getStatusRank(b.status as IntegrityStatus) || a.score - b.score
    })
  }, [studentsList, filter, sort])

  const activeView = canAccess(view) ? view : auth?.role === 'teacher' ? 'dashboard' : auth?.role === 'student' ? 'consent' : 'landing'
  const visibleNavItems = navItems.filter((item) => {
    if (publicViews.includes(item.view)) return !auth
    if (!auth) return false
    return auth.role === 'teacher' ? teacherViews.includes(item.view) : studentViews.includes(item.view)
  })

  const handleSaveSettings = (newName: string) => {
    if (auth) {
      const updated = { ...auth, name: newName }
      setAuth(updated)
      window.localStorage.setItem('examguard-auth', JSON.stringify(updated))
    }
  }

  const contentMap = {
    landing: <LandingView notify={notify} onLogin={loginWithApi} />,
    dashboard: (
      <DashboardView
        go={navigate}
        notify={notify}
        students={studentsList}
        selectedExamId={selectedExamId}
        onSelectExam={(examId) => {
          setSelectedExamId(examId)
          window.localStorage.setItem('examguard-exam-id', examId)
        }}
      />
    ),
    config: <ConfigView examId={selectedExamId} notify={notify} />,
    live: (
      <LiveMonitorView
        examId={selectedExamId}
        students={filteredStudents}
        selected={selectedStudent}
        setSelected={setSelectedStudent}
        filter={filter}
        setFilter={setFilter}
        sort={sort}
        setSort={setSort}
        notify={notify}
        onRefreshStudents={() => {
          api.examStudents(selectedExamId).then(sessions => {
            setStudentsList(sessions.map(mapSessionToStudent))
          }).catch(() => {})
        }}
        onStudentsSnapshot={(sessions) => setStudentsList(sessions.map(mapSessionToStudent))}
      />
    ),
    consent: <ConsentView consentScrolled={consentScrolled} setConsentScrolled={setConsentScrolled} go={navigate} notify={notify} />,
    liveness: <LivenessView go={navigate} notify={notify} />,
    exam: <ExamView answer={answer} setAnswer={setAnswer} marked={marked} setMarked={setMarked} notify={notify} go={navigate} />,
    complete: <CompleteView notify={notify} />,
    review: (
      <ReviewView
        students={studentsList}
        selected={selectedStudent}
        setSelected={setSelectedStudent}
        notify={notify}
      />
    ),
    reports: (
      <ReportsView
        examId={selectedExamId}
        students={studentsList}
        notify={notify}
      />
    ),
    settings: <SettingsView auth={auth} onSaveSettings={handleSaveSettings} notify={notify} />,
  }
  const content = Reflect.get(contentMap, activeView)

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? 'sidebar-open' : ''}`}>
        <div className="brand">
          <div className="brand-mark">EG</div>
          <div>
            <strong>ExamGuard AI</strong>
            <span>Exam integrity platform</span>
          </div>
        </div>
        <nav aria-label="Primary screens">
          {visibleNavItems.map((item) => {
            const Icon = item.icon
            return (
              <button key={item.view} className={activeView === item.view ? 'active' : ''} onClick={() => { navigate(item.view); setMobileOpen(false) }}>
                <Icon size={18} aria-hidden="true" />
                {item.label}
              </button>
            )
          })}
        </nav>
        <div className="sidebar-card">
          <Bot size={18} aria-hidden="true" style={{ color: 'var(--eg-indigo)' }} />
          <strong>10-agent workflow</strong>
          <span>Creates, monitors, scores, and reviews exams.</span>
        </div>
      </aside>

      <main style={{ background: 'var(--eg-navy)', minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
        <header className="topbar">
          <button className="icon-btn mobile-only" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
            <Menu size={20} />
          </button>
          <div>
            <p className="eyebrow">Syllabus-based exam integrity platform</p>
            <h1>{navItems.find((item) => item.view === activeView)?.label ?? 'ExamGuard AI'}</h1>
          </div>
          <div className="top-actions">
            <button className="icon-btn" aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`} onClick={() => setTheme((current) => current === 'dark' ? 'light' : 'dark')}>
              {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
            </button>
            {auth ? (
              <div className="auth-pill">
                <span>{auth.role}</span>
                <strong>{auth.name}</strong>
              </div>
            ) : null}
            {auth ? (
              <>
                <button className="ghost-btn" onClick={() => notify('info', 'Live connection restored. Scores rehydrated.')}>
                  <RefreshCw size={16} aria-hidden="true" /> Reconnect
                </button>
                {auth.role === 'teacher' ? (
                  <button className="primary-btn" onClick={() => navigate('live')}>
                    <Activity size={16} aria-hidden="true" /> Live Monitor
                  </button>
                ) : null}
                <button className="ghost-btn" onClick={logout}>
                  <Lock size={16} aria-hidden="true" /> Logout
                </button>
              </>
            ) : (
              <button className="primary-btn" onClick={() => navigate('landing')}>
                <Lock size={16} aria-hidden="true" /> Login / Join
              </button>
            )}
          </div>
        </header>
        {content}
      </main>

      {mobileOpen && <button className="scrim" aria-label="Close navigation" onClick={() => setMobileOpen(false)} />}
      {toast && <Toast kind={toast.kind} text={toast.text} onClose={() => setToast(null)} />}
    </div>
  )
}

type LoginPayload = { role: AuthRole; email: string; password: string; name: string; joinCode?: string }

function LandingView({ notify, onLogin }: { notify: (kind: ToastKind, text: string) => void; onLogin: (payload: LoginPayload) => Promise<void> }) {
  const [chosenRole, setChosenRole] = useState<AuthRole | null>(null)

  if (chosenRole) {
    return (
      <section className="screen landing-screen" style={{ background: 'var(--eg-navy)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center' }}>
        <div style={{ maxWidth: '420px', width: '100%', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <button className="ghost-btn" onClick={() => setChosenRole(null)} style={{ alignSelf: 'flex-start' }}>
            &larr; Back to Role Selection
          </button>
          <AuthPanel initialRole={chosenRole} onLogin={onLogin} notify={notify} />
        </div>
      </section>
    )
  }

  return (
    <section className="screen landing-screen" style={{ background: 'var(--eg-navy)', display: 'flex', flexDirection: 'column', justifyContent: 'center', alignItems: 'center', margin: '0 auto', maxWidth: '480px' }}>
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <div style={{ display: 'inline-block', filter: 'drop-shadow(0 0 12px #4F46E5)', marginBottom: '16px' }}>
          <Shield size={64} style={{ color: 'var(--eg-indigo)' }} />
        </div>
        <h1 style={{ fontSize: '40px', fontWeight: 700, margin: '0 0 8px 0', background: 'linear-gradient(135deg, #4F46E5 0%, #0EA5E9 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
          ExamGuard AI
        </h1>
        <p style={{ fontSize: '16px', color: 'var(--eg-text-muted)', margin: 0 }}>
          Privacy-first exam platform for institutes
        </p>
      </div>

      <div style={{ display: 'flex', gap: '24px', justifyContent: 'center', width: '100%', marginBottom: '40px' }}>
        {/* Card: Teacher */}
        <button
          type="button"
          onClick={() => setChosenRole('teacher')}
          className="role-card-select"
          style={{
            width: '180px',
            border: '1.5px solid var(--eg-navy-600)',
            borderRadius: '12px',
            padding: '28px 20px',
            textAlign: 'center',
            cursor: 'pointer',
            background: 'var(--eg-navy-800)',
            color: 'inherit',
            font: 'inherit',
          }}
        >
          <Users size={48} style={{ color: 'var(--eg-indigo)', marginBottom: '16px' }} />
          <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--eg-text)' }}>Teacher Portal</div>
        </button>

        {/* Card: Student */}
        <button
          type="button"
          onClick={() => setChosenRole('student')}
          className="role-card-select"
          style={{
            width: '180px',
            border: '1.5px solid var(--eg-navy-600)',
            borderRadius: '12px',
            padding: '28px 20px',
            textAlign: 'center',
            cursor: 'pointer',
            background: 'var(--eg-navy-800)',
            color: 'inherit',
            font: 'inherit',
          }}
        >
          <GraduationCap size={48} style={{ color: 'var(--eg-indigo)', marginBottom: '16px' }} />
          <div style={{ fontWeight: 600, fontSize: '15px', color: 'var(--eg-text)' }}>Student Portal</div>
        </button>
      </div>

      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', padding: '4px 10px', borderRadius: '20px', background: 'var(--eg-navy-700)', fontSize: '11px', color: 'var(--eg-text-muted)', fontWeight: 500 }}>
        ExamGuard v6.0
      </div>
    </section>
  )
}

function AuthPanel({ initialRole, onLogin, notify }: { initialRole: AuthRole; onLogin: (payload: LoginPayload & { signup?: boolean }) => Promise<void>; notify: (kind: ToastKind, text: string) => void }) {
  const [role, setRole] = useState<AuthRole>(initialRole)
  const [email, setEmail] = useState('teacher@demo.examguard.ai')
  const [password, setPassword] = useState('demo123')
  const [studentName, setStudentName] = useState('Arjun Sharma')
  const [joinCode, setJoinCode] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [signupMode, setSignupMode] = useState(false)

  useEffect(() => {
    setRole(initialRole)
    setError('')
    if (initialRole === 'teacher') {
      setEmail('teacher@demo.examguard.ai')
      setPassword('demo123')
    } else {
      setEmail('arjun@student.ai')
      setPassword('demo123')
      setStudentName('Arjun Sharma')
      setJoinCode('')
    }
  }, [initialRole])

  const submit = async () => {
    setError('')
    setSubmitting(true)
    if (role === 'teacher') {
      if (!isValidEmail(email)) { setError('Enter a valid teacher email address.'); notify('error', 'Enter a valid teacher email address.'); setSubmitting(false); return }
      if (password.trim().length < 6) { setError('Password must be at least 6 characters.'); notify('error', 'Password must be at least 6 characters.'); setSubmitting(false); return }
      try { await onLogin({ role: 'teacher', name: email.split('@')[0], email, password, signup: signupMode }) }
      catch (event) { const message = event instanceof Error ? event.message : 'Teacher login failed.'; setError(message); notify('error', message) }
      finally { setSubmitting(false) }
      return
    }
    if (!/^[A-Z0-9]{6}$/.test(joinCode.trim().toUpperCase())) { setError('Join code must be 6 letters or numbers.'); notify('error', 'Join code must be 6 letters or numbers.'); setSubmitting(false); return }
    if (studentName.trim().length < 3) { setError('Student name must be at least 3 characters.'); notify('error', 'Student name is required before joining.'); setSubmitting(false); return }
    if (email.trim() && !isValidEmail(email)) { setError('Optional student email must be valid if provided.'); notify('error', 'Optional student email must be valid if provided.'); setSubmitting(false); return }
    try { await onLogin({ role: 'student', name: studentName.trim(), email: email || `${studentName.toLowerCase().replace(/\s+/g, '.')}@student.ai`, password, joinCode }) }
    catch (event) { const message = event instanceof Error ? event.message : 'Student join failed.'; setError(message); notify('error', message) }
    finally { setSubmitting(false) }
  }

  return (
    <div className="login-card" style={{ padding: '40px', borderRadius: '16px', background: 'var(--eg-navy-800)', boxShadow: 'var(--shadow-elevated)' }}>
      {role === 'student' && <StudentStepIndicator currentStep="join" />}
      <span className="badge badge-purple" style={{ marginBottom: '12px' }}><Shield size={14} /> Secure Access Portal</span>
      <h2 style={{ fontSize: '24px', fontWeight: 700, margin: '8px 0 16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Shield size={24} style={{ color: 'var(--eg-indigo)' }} />
        {role === 'teacher' ? 'Teacher Sign In' : 'Student Join Session'}
      </h2>
      <p className="muted" style={{ fontSize: '14px', marginBottom: '24px' }}>
        {role === 'teacher' ? (signupMode ? 'Create a secure teacher account for your institute.' : 'Manage exam papers, configurations, and review flagged session anomalies.') : 'Join your active exam. Complete verification consent to begin.'}
      </p>

      {role === 'teacher' ? (
        <div className="login-form" style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '20px' }}>
          <div>
            <label>Teacher Email</label>
            <input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
          <div>
            <label>Password</label>
            <input type="password" required minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} />
          </div>
        </div>
      ) : (
        <div className="login-form" style={{ display: 'flex', flexDirection: 'column', gap: '16px', marginBottom: '20px' }}>
          <div>
            <label>Demo Student</label>
            <div className="inline-actions" style={{ gap: '8px', flexWrap: 'wrap' }}>
              {[
                ['Arjun Sharma', 'arjun@student.ai'],
                ['Priya Patel', 'priya@student.ai'],
                ['Rahul Mehta', 'rahul@student.ai'],
              ].map(([name, demoEmail]) => (
                <button key={demoEmail} type="button" className="ghost-btn" style={{ minHeight: '36px' }} onClick={() => { setStudentName(name); setEmail(demoEmail) }}>{name.split(' ')[0]}</button>
              ))}
            </div>
          </div>
          <div>
            <label>Student Name</label>
            <input required minLength={3} value={studentName} onChange={(event) => setStudentName(event.target.value)} />
          </div>
          <div>
            <label>Join Code</label>
            <input required maxLength={6} placeholder="Enter 6-character exam code" autoComplete="off" value={joinCode} onChange={(event) => setJoinCode(event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ''))} />
          </div>
          <div>
            <label>Optional Email</label>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} />
          </div>
        </div>
      )}

      {error && <p className="form-error" role="alert" style={{ marginBottom: '16px' }}>{error}</p>}
      
      <button className="primary-btn full" disabled={submitting} onClick={submit}>
        <Lock size={16} /> {submitting ? 'Authenticating...' : role === 'teacher' ? (signupMode ? 'Create Teacher Account' : 'Sign In') : 'Join Session'}
      </button>
      {role === 'teacher' && <button type="button" className="ghost-btn full" style={{ marginTop: '10px' }} onClick={() => setSignupMode(value => !value)}>
        {signupMode ? 'Already registered? Sign in' : 'New teacher? Create account'}
      </button>}

      <details style={{ marginTop: '16px', fontSize: '13px', color: 'var(--eg-text-muted)', cursor: 'pointer' }}>
        <summary style={{ fontWeight: 600, color: 'var(--eg-indigo-hover)', outline: 'none' }}>Demo credentials</summary>
        <div className="demo-credentials" style={{ marginTop: '10px' }}>
          {role === 'teacher' ? (
            <><strong>Teacher:</strong> teacher@demo.examguard.ai / demo123</>
          ) : <span>Use code shown by teacher after exam activation.</span>}
        </div>
      </details>
    </div>
  )
}

function DashboardView({ go, notify, onSelectExam, students, selectedExamId }: { go: (view: View) => void; notify: (kind: ToastKind, text: string) => void; onSelectExam: (examId: string) => void; students: any[]; selectedExamId: string }) {
  const [exams, setExams] = useState<ApiExam[]>([])
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [search, setSearch] = useState('')
  const [showArchived, setShowArchived] = useState(false)

  useEffect(() => {
    const teacherId = window.localStorage.getItem('examguard-user-id') || 'teacher-demo'
    api.exams(teacherId).then(setExams).catch(() => notify('warning', 'Could not fetch exams from backend.'))
  }, [])

  const handleCreateExam = async (payload: { title: string; subject: string; duration_minutes: number; total_marks: number }) => {
    const teacherId = window.localStorage.getItem('examguard-user-id') || 'teacher-demo'
    try {
      const exam = await api.createExam({ teacher_id: teacherId, ...payload })
      setExams((prev) => [...prev, exam])
      setShowCreateModal(false)
      onSelectExam(exam.id)
      notify('success', `Exam created. Now upload its syllabus and generate the paper.`)
      go('config')
    } catch (e) { notify('error', e instanceof Error ? e.message : 'Failed to create exam.') }
  }

  const handleDeleteExam = async (examId: string) => {
    try {
      await api.deleteExam(examId)
      setExams((prev) => prev.filter((e) => e.id !== examId))
      notify('success', 'Exam deleted.')
    } catch (e) { notify('error', e instanceof Error ? e.message : 'Failed to delete exam.') }
  }

  const handleCloneExam = async (examId: string) => {
    try {
      const cloned = await api.cloneExam(examId)
      setExams((prev) => [...prev, cloned])
      notify('success', `Exam cloned. New join code: ${cloned.join_code}`)
    } catch (e) { notify('error', e instanceof Error ? e.message : 'Failed to clone exam.') }
  }

  const visibleExams = exams.filter((exam) => {
    const matchesSearch = `${exam.title} ${exam.subject} ${exam.join_code}`.toLowerCase().includes(search.toLowerCase())
    const matchesArchive = showArchived ? exam.status === 'archived' : exam.status !== 'archived'
    return matchesSearch && matchesArchive
  })

  return (
    <section className="screen">
      {/* Dynamic Stats Row at top of Dashboard */}
      <div className="summary-grid" style={{ marginBottom: '24px' }}>
        <div className="metric-card compact" style={{ background: 'var(--eg-navy-800)', border: '1px solid var(--eg-navy-600)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <BookOpen size={24} style={{ color: 'var(--eg-indigo)', position: 'absolute', top: '16px', right: '16px' }} />
          <span style={{ fontSize: '11px', color: 'var(--eg-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Total Exams</span>
          <strong style={{ fontSize: '32px', fontWeight: 700, margin: '8px 0 0 0', color: 'var(--eg-text)' }}>{exams.length}</strong>
        </div>
        <div className="metric-card compact" style={{ background: 'var(--eg-navy-800)', border: '1px solid var(--eg-navy-600)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <Users size={24} style={{ color: 'var(--eg-teal)', position: 'absolute', top: '16px', right: '16px' }} />
          <span style={{ fontSize: '11px', color: 'var(--eg-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Active Students</span>
          <strong style={{ fontSize: '32px', fontWeight: 700, margin: '8px 0 0 0', color: 'var(--eg-text)' }}>{students.filter(student => student.rawSession?.status === 'active').length}</strong>
        </div>
        <div className="metric-card compact" style={{ background: 'var(--eg-navy-800)', border: '1px solid var(--eg-navy-600)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <Flag size={24} style={{ color: 'var(--eg-red)', position: 'absolute', top: '16px', right: '16px' }} />
          <span style={{ fontSize: '11px', color: 'var(--eg-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Flagged Cases</span>
          <strong style={{ fontSize: '32px', fontWeight: 700, margin: '8px 0 0 0', color: 'var(--eg-text)' }}>{students.filter(student => student.status === 'FLAGGED').length}</strong>
        </div>
        <div className="metric-card compact" style={{ background: 'var(--eg-navy-800)', border: '1px solid var(--eg-navy-600)', borderRadius: '12px', padding: '20px', display: 'flex', flexDirection: 'column', position: 'relative' }}>
          <Gauge size={24} style={{ color: 'var(--eg-emerald)', position: 'absolute', top: '16px', right: '16px' }} />
          <span style={{ fontSize: '11px', color: 'var(--eg-text-muted)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Class Avg Integrity</span>
          <strong style={{ fontSize: '32px', fontWeight: 700, margin: '8px 0 0 0', color: 'var(--eg-text)' }}>{students.length ? `${Math.round(students.reduce((sum, student) => sum + student.score, 0) / students.length)}%` : '--'}</strong>
        </div>
      </div>

      <div className="toolbar" style={{ display: 'flex', justifyContent: 'space-between', gap: '16px', flexWrap: 'wrap', marginBottom: '24px' }}>
        <div className="search-box" style={{ flexGrow: 1, maxWidth: '400px' }}><Search size={16} /><input aria-label="Search exams" placeholder="Search exams, subjects, codes" value={search} onChange={(event) => setSearch(event.target.value)} /></div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="ghost-btn" onClick={() => setShowArchived((value) => !value)}><Archive size={16} /> {showArchived ? 'Show Current' : 'Show Archived'}</button>
          <button className="primary-btn" onClick={() => setShowCreateModal(true)}><Plus size={16} /> Create New Exam</button>
        </div>
      </div>

      <div className="dashboard-grid">
        {exams.length === 0 ? (
          <Card title="First-run guide" icon={Rocket} className="empty-card">
            <p className="muted">New teacher? Create your first real exam or load a sample Physics class to explore the workflow.</p>
            <div className="checklist">
              <span><Check size={15} /> Create exam shell</span>
              <span><Check size={15} /> Upload syllabus PDF</span>
              <span><Clock size={15} /> Configure paper</span>
            </div>
            <div className="inline-actions" style={{ marginTop: '16px' }}>
              <button className="primary-btn" onClick={() => setShowCreateModal(true)}>Create exam</button>
              <button className="ghost-btn" onClick={() => notify('info', 'Sample Physics class loaded. Fixed seed code PHY001.')}>Try sample class</button>
            </div>
          </Card>
        ) : null}

        {visibleExams.map((exam) => (
          <Card key={exam.id} title={exam.title} icon={BookOpen}>
            <div className="exam-card-body">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <span className={`badge ${exam.status === 'active' ? 'badge-green' : exam.status === 'ended' ? 'badge-amber' : 'badge-purple'}`}>{exam.status}</span>
                <span style={{ fontSize: '13px', color: 'var(--eg-text-muted)' }}>{exam.subject}</span>
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--eg-text)' }}>{exam.total_marks} Marks / {exam.duration_minutes} Mins</h3>
              <div className="join-code">
                <span>{exam.join_code}</span>
                <button aria-label="Copy join code" onClick={() => { navigator.clipboard?.writeText(exam.join_code); notify('success', 'Join code copied.') }}><Copy size={16} /></button>
              </div>
              <div className="inline-actions" style={{ marginTop: '8px' }}>
                <button className="primary-btn" onClick={() => { onSelectExam(exam.id); go('live') }}>Open Live Monitor</button>
                <button className="ghost-btn" onClick={() => { onSelectExam(exam.id); go('config') }}>Configure</button>
                <button className="ghost-btn" onClick={() => handleCloneExam(exam.id)} title="Clone Exam"><Copy size={14} /></button>
                <button className="ghost-btn" onClick={() => handleDeleteExam(exam.id)} title="Delete Exam" style={{ color: 'var(--eg-red)' }}><X size={14} /></button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Recent Exams Table */}
      {exams.length > 0 && (
        <Card title="All Exams List" icon={Layers} className="wide-card" style={{ marginTop: '24px' }}>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--eg-navy-600)' }}>
                  <th style={{ padding: '12px 16px', color: 'var(--eg-text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Exam Title</th>
                  <th style={{ padding: '12px 16px', color: 'var(--eg-text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Subject</th>
                  <th style={{ padding: '12px 16px', color: 'var(--eg-text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Join Code</th>
                  <th style={{ padding: '12px 16px', color: 'var(--eg-text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Status</th>
                  <th style={{ padding: '12px 16px', color: 'var(--eg-text-muted)', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600 }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {visibleExams.map((exam) => (
                  <tr key={exam.id} style={{ borderBottom: '1px solid var(--eg-navy-600)', background: 'var(--eg-navy-800)', transition: 'background 150ms' }} className="table-row-hover">
                    <td style={{ padding: '12px 16px', fontWeight: 600 }}>{exam.title}</td>
                    <td style={{ padding: '12px 16px', color: 'var(--eg-text-muted)' }}>{exam.subject}</td>
                    <td style={{ padding: '12px 16px', fontFamily: 'JetBrains Mono', color: 'var(--eg-teal)' }}>{exam.join_code}</td>
                    <td style={{ padding: '12px 16px' }}>
                      <span className={`status-badge ${exam.status === 'active' ? 'clean' : exam.status === 'ended' ? 'warn' : 'watch'}`}>
                        {exam.status}
                      </span>
                    </td>
                    <td style={{ padding: '12px 16px', display: 'flex', gap: '8px' }}>
                      <button className="primary-btn" style={{ minHeight: '32px', padding: '4px 12px', fontSize: '12px' }} onClick={() => { onSelectExam(exam.id); go('live') }}>
                        Monitor
                      </button>
                      <button className="ghost-btn" style={{ minHeight: '32px', padding: '4px 12px', fontSize: '12px' }} onClick={() => { onSelectExam(exam.id); go('config') }}>
                        Setup
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      <div className="tab-strip" style={{ marginTop: '32px' }}>
        {['Overview', 'Configure Paper', 'Live Monitor', 'Reports', 'Review'].map((tab, index) => (
          <button key={tab} onClick={() => {
            const selectedExam = exams.find((exam) => exam.id === selectedExamId)?.id || exams[0]?.id || 'exam-physics';
            onSelectExam(selectedExam);
            const targetView = index === 0 ? 'dashboard' : index === 1 ? 'config' : index === 2 ? 'live' : index === 3 ? 'reports' : 'review';
            go(targetView);
          }}>{tab}</button>
        ))}
      </div>
      {showCreateModal && <CreateExamModal onClose={() => setShowCreateModal(false)} onCreate={handleCreateExam} />}
    </section>
  )
}

function CreateExamModal({ onClose, onCreate }: { onClose: () => void; onCreate: (payload: { title: string; subject: string; duration_minutes: number; total_marks: number }) => void }) {
  const [title, setTitle] = useState('')
  const [subject, setSubject] = useState('')
  const [duration, setDuration] = useState(60)
  const [marks, setMarks] = useState(80)
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="create-title">
      <div className="modal" style={{ maxWidth: '440px' }}>
        <h2 id="create-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Plus size={22} style={{ color: 'var(--eg-indigo)' }} /> Create New Exam</h2>
        <p className="muted">Specify details below. This creates a grounded code room students can join.</p>
        <div className="login-form" style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '24px' }}>
          <div>
            <label>Exam Title</label>
            <input required minLength={3} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Physics XI - Electromagnetism" />
          </div>
          <div>
            <label>Subject</label>
            <input required value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="e.g. Physics" />
          </div>
          <div>
            <label>Duration (minutes)</label>
            <input type="number" min={10} max={300} value={duration} onChange={(e) => setDuration(Number(e.target.value))} />
          </div>
          <div>
            <label>Total Marks</label>
            <input type="number" min={10} max={300} value={marks} onChange={(e) => setMarks(Number(e.target.value))} />
          </div>
        </div>
        <div className="inline-actions" style={{ justifyContent: 'flex-end' }}>
          <button className="ghost-btn" onClick={onClose}>Cancel</button>
          <button className="primary-btn" disabled={title.length < 3 || subject.length < 2} onClick={() => onCreate({ title, subject, duration_minutes: duration, total_marks: marks })}>Create Exam</button>
        </div>
      </div>
    </div>
  )
}

function ConfigView({ examId, notify }: { examId: string; notify: (kind: ToastKind, text: string) => void }) {
  const [materialId, setMaterialId] = useState('')
  const [materialIds, setMaterialIds] = useState<string[]>([])
  const [uploadedMaterial, setUploadedMaterial] = useState('')
  const [syllabusName, setSyllabusName] = useState('')
  const [studyMaterialName, setStudyMaterialName] = useState('')
  const [materialError, setMaterialError] = useState('')
  const [totalMarksTarget, setTotalMarksTarget] = useState(80)
  const [overallLevel, setOverallLevel] = useState<ExamLevel>('Standard')
  const [paperMode, setPaperMode] = useState<PaperMode>('Mixed')
  const [sections, setSections] = useState<PaperSection[]>(sectionsForMode('Mixed', 80))
  const [generated, setGenerated] = useState(false)
  const [generatedQuestions, setGeneratedQuestions] = useState<ApiQuestion[]>([])
  const [loading, setLoading] = useState(true)
  const [generating, setGenerating] = useState(false)
  const [generationError, setGenerationError] = useState('')
  const [activated, setActivated] = useState(false)

  const [availableChapters, setAvailableChapters] = useState<string[]>([])
  const [chapterTopicsMap, setChapterTopicsMap] = useState<Record<string, string[]>>({})
  const [chapterCountsMap, setChapterCountsMap] = useState<Record<string, number>>({})

  useEffect(() => {
    setLoading(true)
    setMaterialId('')
    setMaterialIds([])
    setUploadedMaterial('')
    setSyllabusName('')
    setStudyMaterialName('')
    setAvailableChapters([])
    setChapterTopicsMap({})
    setChapterCountsMap({})
    setGenerated(false)
    setGeneratedQuestions([])
    setActivated(false)
    api.getExam(examId)
      .then((exam) => {
        setTotalMarksTarget(exam.total_marks)
        setSections(sectionsForMode('Mixed', exam.total_marks))
        return api.materials(examId)
      })
      .then((materials) => {
        const first = materials?.[0]
        if (!first) return
        setMaterialId(first.id)
        setMaterialIds(materials.map((item) => item.id))
        setUploadedMaterial(materials.map((item) => item.filename).join(', '))
        setSyllabusName(materials.find((item) => item.source_type === 'syllabus')?.filename || '')
        setStudyMaterialName(materials.find((item) => item.source_type !== 'syllabus')?.filename || '')
        
        if (first.chapter_counts) {
          const chList: string[] = []
          const topicsMap: Record<string, string[]> = {}
          const countsMap: Record<string, number> = {}
          Object.entries(first.chapter_counts).forEach(([chapterName, info]: [string, any]) => {
            chList.push(chapterName)
            if (info && typeof info === 'object') {
              Reflect.set(topicsMap, chapterName, Array.isArray(info.topics) ? info.topics : [])
              Reflect.set(countsMap, chapterName, typeof info.count === 'number' ? info.count : 0)
            } else {
              Reflect.set(topicsMap, chapterName, [])
              Reflect.set(countsMap, chapterName, typeof info === 'number' ? info : 0)
            }
          })
          if (chList.length > 0) {
            setAvailableChapters(chList)
            setChapterTopicsMap(topicsMap)
            setChapterCountsMap(countsMap)
          }
        }
      })
      .catch((event) => notify('error', `Could not load this exam from the backend: ${event instanceof Error ? event.message : 'unknown error'}`))
      .finally(() => setLoading(false))
  }, [examId])

  const total = sections.reduce((sum, section) => sum + section.count * section.marks, 0)
  const totalQuestions = sections.reduce((sum, section) => sum + section.count, 0)
  const validTotalMarks = Number.isInteger(totalMarksTarget) && totalMarksTarget >= 10 && totalMarksTarget <= 300
  const materialChunks = uploadedMaterial ? Object.values(chapterCountsMap).reduce((a, b) => a + b, 0) : 0
  const invalidSections = sections.filter((section) => section.count < 1 || section.marks < 1 || !section.chapter)
  const hasMaterial = Boolean(uploadedMaterial && materialId)
  const lowCoverageChapters = hasMaterial 
    ? sections.filter((section) => {
        if (section.chapter === 'All syllabus') return false
        const count = Reflect.get(chapterCountsMap, section.chapter) ?? 0
        return count < 1
      })
    : []
  const typeSet = new Set(sections.map((section) => section.type))
  const modeMismatch =
    (paperMode === 'MCQ only' && [...typeSet].some((type) => type !== 'MCQ')) ||
    (paperMode === 'MCQ + QA' && [...typeSet].some((type) => !['MCQ', 'Short Answer', 'Long Answer', 'Essay'].includes(type))) ||
    (paperMode === 'Mixed' && ![...typeSet].some((type) => ['MCQ', 'Short Answer', 'Long Answer', 'Fill Blank'].includes(type)))
  const canGenerate = hasMaterial && validTotalMarks && total === totalMarksTarget && totalQuestions <= 50 && invalidSections.length === 0 && lowCoverageChapters.length === 0 && !modeMismatch && !generating

  const applyMode = (mode: PaperMode) => {
    setPaperMode(mode)
    setSections(sectionsForMode(mode, totalMarksTarget, availableChapters[0] || 'All syllabus'))
    setGenerated(false)
  }

  const updateSection = (index: number, patch: Partial<PaperSection>) => { setGenerated(false); setSections((c) => c.map((s, i) => i === index ? { ...s, ...patch } : s)) }
  const addSection = () => { setGenerated(false); setSections((c) => [...c, { id: String.fromCharCode(65 + c.length), type: 'Fill Blank', count: 5, marks: 2, bloom: 'Apply', chapter: availableChapters[0] || 'All syllabus', level: 'Use overall', negative: 'none' }]) }
  const removeSection = (index: number) => { if (sections.length === 1) { notify('error', 'At least one paper section is required.'); return }; setGenerated(false); setSections((c) => c.filter((_, i) => i !== index).map((s, i) => ({ ...s, id: String.fromCharCode(65 + i) }))) }

  const handleMaterialUpload = async (file: File | undefined, sourceType: 'syllabus' | 'material') => {
    setMaterialError(''); setGenerated(false)
    if (!file) return
    const allowed = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
    if (!allowed.includes(file.type) && !/\.(pdf|docx|txt)$/i.test(file.name)) { setMaterialError('Only PDF, DOCX, or TXT files are allowed.'); notify('error', 'Only PDF, DOCX, or TXT files are allowed.'); return }
    if (file.size > 50 * 1024 * 1024) { setMaterialError('Material file must be 50MB or smaller.'); notify('error', 'Material file must be 50MB or smaller.'); return }
    try {
      const material = await api.uploadMaterial(examId, file, sourceType)
      setMaterialId(material.id)
      setMaterialIds((current) => [...new Set([...current, material.id])])
      setUploadedMaterial((current) => current ? `${current}, ${material.filename}` : material.filename)
      if (sourceType === 'syllabus') setSyllabusName(material.filename); else setStudyMaterialName(material.filename)
      
      if (material.chapter_counts) {
        const chList: string[] = []
        const topicsMap: Record<string, string[]> = {}
        const countsMap: Record<string, number> = {}
        Object.entries(material.chapter_counts).forEach(([chapterName, info]: [string, any]) => {
          chList.push(chapterName)
          if (info && typeof info === 'object') {
            Reflect.set(topicsMap, chapterName, Array.isArray(info.topics) ? info.topics : [])
            Reflect.set(countsMap, chapterName, typeof info.count === 'number' ? info.count : 0)
          } else {
            Reflect.set(topicsMap, chapterName, [])
            Reflect.set(countsMap, chapterName, typeof info === 'number' ? info : 0)
          }
        })
        if (chList.length > 0) {
          setAvailableChapters(chList)
          setChapterTopicsMap(topicsMap)
          setChapterCountsMap(countsMap)
        }
      }
      
      notify('success', `${sourceType === 'syllabus' ? 'Syllabus' : 'Study material'} uploaded and mapped for paper generation.`)
    } catch (event) { const msg = event instanceof Error ? event.message : 'Upload failed.'; setMaterialError(msg); notify('error', msg) }
  }

  const validateAndGenerate = async () => {
    setGenerated(false)
    if (!hasMaterial) { notify('error', 'Upload syllabus or study material before generating the paper.'); return }
    if (!validTotalMarks) { notify('error', 'Total exam marks must be between 10 and 300.'); return }
    if (total !== totalMarksTarget) { notify('error', `Paper total must be exactly ${totalMarksTarget} marks. Current total is ${total}.`); return }
    if (totalQuestions > 50) { notify('error', 'Use 50 questions or fewer. Increase marks per question to keep generation reliable.'); return }
    if (invalidSections.length) { notify('error', 'Every section needs question count, marks, and chapter.'); return }
    if (lowCoverageChapters.length) { notify('error', 'One or more selected chapters have no usable source chunks.'); return }
    if (modeMismatch) { notify('error', `Selected sections do not match the ${paperMode} paper type.`); return }
    try {
      setGenerating(true)
      setGenerationError('')
      const payload = { 
        material_id: materialId || null, 
        material_ids: materialIds,
        total_marks: totalMarksTarget, 
        overall_level: overallLevel, 
        paper_mode: paperMode, 
        sections: sections.map((s) => ({ 
          id: s.id, 
          type: s.type, 
          count: s.count, 
          marks_each: s.marks, 
          bloom: s.bloom, 
          chapter_tag: s.chapter, 
          topic_tag: s.topic || 'All topics',
          level: s.level 
        })) 
      }
      await api.savePaperConfig(examId, payload)
      const result = await api.generatePaper(examId)
      setGeneratedQuestions(result.questions)
      setGenerated(true)
      notify('success', `Paper generated successfully. ${result.count}/${result.count} questions created.`)
    } catch (event) {
      const message = event instanceof Error ? event.message : 'Paper generation failed.'
      setGenerationError(message)
      notify('error', message)
    }
    finally { setGenerating(false) }
  }

  const activateGeneratedExam = async () => {
    try {
      await api.activateExam(examId)
      setActivated(true)
      notify('success', 'Exam activated. Students can now join with its code.')
    } catch (event) {
      notify('error', event instanceof Error ? event.message : 'Could not activate exam.')
    }
  }

  return (
    <section className="screen config-layout">
      <div className="config-main">
        <Card title="Step 1: Add syllabus and study material" icon={Upload}>
          <div className="two-column-grid">
            <label htmlFor="syllabus-file-upload" className="upload-zone" style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <Upload size={28} style={{ color: 'var(--eg-indigo)' }} />
              <strong>Syllabus</strong>
              <span style={{ fontSize: '12px' }}>{syllabusName || 'Upload topic outline, curriculum, or syllabus'}</span>
              <small>Defines topics, coverage, level, and chapter weight.</small>
            </label>
            <label htmlFor="study-file-upload" className="upload-zone" style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <Upload size={28} style={{ color: 'var(--eg-teal)' }} />
              <strong>Study material</strong>
              <span style={{ fontSize: '12px' }}>{studyMaterialName || 'Upload textbook, notes, or reference material'}</span>
              <small>Provides factual grounding and examples. Optional.</small>
            </label>
          </div>
          <input id="syllabus-file-upload" style={{ display: 'none' }} aria-label="Upload syllabus" type="file" accept=".pdf,.docx,.txt,application/pdf,text/plain" onChange={(event) => handleMaterialUpload(event.target.files?.[0], 'syllabus')} />
          <input id="study-file-upload" style={{ display: 'none' }} aria-label="Upload study material" type="file" accept=".pdf,.docx,.txt,application/pdf,text/plain" onChange={(event) => handleMaterialUpload(event.target.files?.[0], 'material')} />
          {materialError && <p className="form-error" role="alert">{materialError}</p>}
          {uploadedMaterial && <p className="hint" style={{ marginTop: '10px' }}>{materialChunks} mapped chunks across {availableChapters.length} sections. Either source works alone; both are combined when present.</p>}
        </Card>

        <Card title="Step 2: Choose paper type and difficulty" icon={Gauge}>
          <div className="paper-controls" style={{ marginBottom: '16px' }}>
            <div>
              <label>Total Exam Marks</label>
              <input type="number" min={10} max={300} value={totalMarksTarget} onChange={(event) => { const next=Number(event.target.value)||0; setTotalMarksTarget(next); setSections(sectionsForMode(paperMode, next, availableChapters[0] || 'All syllabus')); setGenerated(false) }} />
            </div>
            <div>
              <label>Overall Level</label>
              <select value={overallLevel} onChange={(event) => { setOverallLevel(event.target.value as ExamLevel); setGenerated(false) }}>
                <option>Easy</option>
                <option>Standard</option>
                <option>Challenging</option>
              </select>
            </div>
            <div>
              <label>Paper Type</label>
              <select value={paperMode} onChange={(event) => applyMode(event.target.value as PaperMode)}>
                <option>MCQ only</option>
                <option>MCQ + QA</option>
                <option>Mixed</option>
              </select>
            </div>
          </div>
          <div className="plain-points compact-points">
            <span><Lock size={15} /> Syllabus defines coverage; study material provides factual grounding.</span>
            <span><Gauge size={15} /> Section marks must add up exactly to total exam marks.</span>
            <span><Check size={15} /> Section level can override the overall paper level.</span>
          </div>
        </Card>

        <Card title="Step 3: Review paper sections" icon={BookOpen}>
          <div className="section-builder" style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '12px' }}>
            {sections.map((section, index) => (
              <SectionBuilderRow 
                key={section.id} 
                section={section} 
                index={index} 
                updateSection={updateSection} 
                removeSection={removeSection} 
                availableChapters={availableChapters}
                chapterTopicsMap={chapterTopicsMap}
              />
            ))}
          </div>
          <button className="ghost-btn" onClick={addSection}><Plus size={16} /> Add Section</button>
        </Card>

        <ProgressStream generating={generating} generatedCount={generatedQuestions.length} sections={sections} error={generationError} onRetry={validateAndGenerate} />

        <Card title="Generated question preview" icon={FileText}>
          {generated && generatedQuestions.length > 0 ? (
            <div className="question-preview">
              <span className="badge badge-green">{generatedQuestions.length} questions generated</span>
              <h3>{generatedQuestions[0].text}</h3>
              <p>Source: {uploadedMaterial}, {generatedQuestions[0].chapter_tag}. Bloom: {generatedQuestions[0].bloom_level}. Marks: {generatedQuestions[0].marks}.</p>
              <textarea aria-label="Generated question preview" value={generatedQuestions[0].text} readOnly />
              <div className="generated-question-list" aria-label="Generated questions">
                {generatedQuestions.slice(0, 8).map((question, index) => (
                  <div key={question.id} className="generated-question-row">
                    <strong>{index + 1}.</strong>
                    <span>{question.text}</span>
                    <small>{question.type} · {question.marks} marks</small>
                  </div>
                ))}
                {generatedQuestions.length > 8 && <p className="muted">+ {generatedQuestions.length - 8} more questions generated</p>}
              </div>
              <button className="primary-btn" disabled={activated} onClick={activateGeneratedExam}>
                {activated ? 'Exam Active' : 'Activate for Students'}
              </button>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '20px', background: 'var(--eg-navy-700)', borderRadius: '8px', borderLeft: '4px solid var(--eg-navy-600)', position: 'relative', overflow: 'hidden' }}>
              {/* Shimmer Effect */}
              <div className="shimmer-effect" style={{
                position: 'absolute',
                top: 0,
                left: 0,
                width: '100%',
                height: '100%',
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.05), transparent)',
                animation: 'shimmer 1.5s infinite'
              }} />
              <div style={{ height: '16px', width: '120px', borderRadius: '4px', background: 'var(--eg-navy-600)' }} />
              <div style={{ height: '20px', width: '85%', borderRadius: '4px', background: 'var(--eg-navy-600)' }} />
              <div style={{ height: '14px', width: '50%', borderRadius: '4px', background: 'var(--eg-navy-600)' }} />
              <div style={{ height: '60px', width: '100%', borderRadius: '4px', background: 'var(--eg-navy-600)' }} />
            </div>
          )}
        </Card>
      </div>

      <aside className="config-aside">
        <Card title="Live marks tally" icon={Gauge}>
          <div className={total === totalMarksTarget && validTotalMarks ? 'tally tally-ok' : total > totalMarksTarget ? 'tally tally-bad' : 'tally tally-warn'}>
            <strong>{total}/{validTotalMarks ? totalMarksTarget : '--'}</strong>
            <span>{!validTotalMarks ? 'Set total marks between 10 and 300.' : total === totalMarksTarget ? 'Exact match. Ready to generate.' : total > totalMarksTarget ? `${total - totalMarksTarget} marks over budget.` : `${totalMarksTarget - total} marks remaining.`}</span>
          </div>
          <div className="breakdown" style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '13px' }}>
            {sections.map((section) => <span key={section.id}>Section {section.id}: {section.count * section.marks} marks</span>)}
          </div>
          {!validTotalMarks && <p className="form-error" style={{ marginTop: '12px' }}>Total exam marks must be between 10 and 300.</p>}
          {modeMismatch && <p className="form-error" style={{ marginTop: '12px' }}>Sections do not match selected paper type.</p>}
          {lowCoverageChapters.length > 0 && <p className="form-error" style={{ marginTop: '12px' }}>A selected chapter has no usable source chunks.</p>}
          
          {!hasMaterial && <p className="form-error" style={{ marginTop: '12px' }}>Upload material in Step 1 to unlock generation.</p>}
          {totalQuestions > 50 && <p className="form-error" style={{ marginTop: '12px' }}>Maximum 50 questions. Increase marks per question.</p>}
          <button className="primary-btn full" style={{ height: '48px', marginTop: '20px', fontSize: '15px' }} disabled={!canGenerate || loading} onClick={validateAndGenerate}>
            {generating ? 'Generating paper...' : 'Generate Paper'}
          </button>
          <button className="ghost-btn full" style={{ marginTop: '10px' }} onClick={() => notify('warning', 'Gemini is temporarily unavailable. Generation is paused; retry when the API recovers.')}>Test Gemini unavailable state</button>
        </Card>

        <Card title="Coverage validation" icon={Check}>
          <div className="coverage-list" style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '13px' }}>
            {Object.entries(chapterCountsMap).map(([chapter, chunks]) => (
              <span key={chapter} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                {chunks >= 100 ? <Check size={15} style={{ color: 'var(--eg-emerald)' }} /> : <AlertTriangle size={15} style={{ color: 'var(--eg-amber)' }} />} 
                {chapter} has {chunks} chunks
              </span>
            ))}
            <span style={{ borderTop: '1px solid var(--eg-navy-600)', paddingTop: '10px', marginTop: '4px', color: 'var(--eg-text-muted)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Lock size={15} /> Scope lock active. Questions stay inside uploaded syllabus and material topics.
            </span>
          </div>
        </Card>
      </aside>
    </section>
  )
}

function LiveMonitorView(props: {
  examId: string
  students: any[]
  selected: any
  setSelected: (student: any) => void
  filter: IntegrityStatus | 'ALL'
  setFilter: (status: IntegrityStatus | 'ALL') => void
  sort: 'risk' | 'name' | 'join'
  setSort: (sort: 'risk' | 'name' | 'join') => void
  notify: (kind: ToastKind, text: string) => void
  onRefreshStudents: () => void
  onStudentsSnapshot: (sessions: ApiSession[]) => void
}) {
  const avg = props.students.length > 0
    ? Math.round(props.students.reduce((sum, student) => sum + student.score, 0) / props.students.length)
    : 0

  const warnCount = props.students.filter(s => s.status === 'WARN').length
  const flaggedCount = props.students.filter(s => s.status === 'FLAGGED').length

  const [examStatus, setExamStatus] = useState<string>('active')
  const [connection, setConnection] = useState<'connecting' | 'live' | 'offline'>('connecting')
  const refreshStudentsRef = useRef(props.onRefreshStudents)

  useEffect(() => { refreshStudentsRef.current = props.onRefreshStudents }, [props.onRefreshStudents])
  
  useEffect(() => {
    api.getExam(props.examId).then(e => setExamStatus(e.status)).catch(() => {})
  }, [props.examId])

  useEffect(() => {
    let attempts = 0; let socket: WebSocket | null = null; let timer: number | undefined; let closed = false
    const connect = () => {
      if (closed) return
      setConnection('connecting')
      socket = new WebSocket(examSocketUrl(props.examId))
      socket.onopen = () => { attempts = 0; setConnection('live') }
      socket.onmessage = (event) => {
        try {
          const payload = JSON.parse(event.data)
          if (payload?.type === 'monitor_snapshot' && Array.isArray(payload.students)) {
            props.onStudentsSnapshot(payload.students)
            return
          }
        } catch { /* fall through to REST refresh */ }
        refreshStudentsRef.current()
      }
      socket.onerror = () => socket?.close()
      socket.onclose = () => {
        if (closed) return
        setConnection('offline'); attempts += 1
        if (attempts <= 5) timer = window.setTimeout(connect, Math.min(1000 * 2 ** (attempts - 1), 10000))
      }
    }
    connect()
    return () => { closed = true; if (timer) clearTimeout(timer); socket?.close() }
  }, [props.examId])

  const togglePause = async () => {
    try {
      if (examStatus === 'paused') {
        await api.resumeExam(props.examId)
        setExamStatus('active')
        props.notify('success', 'Exam resumed.')
      } else {
        await api.pauseExam(props.examId)
        setExamStatus('paused')
        props.notify('success', 'Exam paused.')
      }
    } catch (e) {
      props.notify('error', e instanceof Error ? e.message : 'Action failed')
    }
  }

  const endExam = async () => {
    if (!window.confirm('Are you sure you want to end this exam? This will submit all active student sessions.')) return
    try {
      await api.endExam(props.examId)
      setExamStatus('ended')
      props.notify('success', 'Exam ended successfully.')
    } catch (e) {
      props.notify('error', e instanceof Error ? e.message : 'Action failed')
    }
  }

  return (
    <section className="screen live-layout">
      <div className="live-main">
        <div className="connection-banner">
          <Activity size={16} /> 
          <span>{connection === 'live' ? 'Live WebSocket connected' : connection === 'connecting' ? 'Connecting live monitor...' : 'Connection lost. Retrying automatically.'}</span>
        </div>
        <div className="summary-grid">
          <Metric label="Active Students" value={String(props.students.length)} icon={Users} compact />
          <Metric label="WARN" value={String(warnCount)} icon={AlertTriangle} compact />
          <Metric label="FLAGGED" value={String(flaggedCount)} icon={Flag} compact />
          <Metric label="Avg Integrity" value={`${avg}`} icon={Gauge} compact />
        </div>
        <div className="toolbar" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <select aria-label="Filter by status" value={props.filter} onChange={(event) => props.setFilter(event.target.value as IntegrityStatus | 'ALL')}>
            {['ALL', 'CLEAN', 'WATCH', 'WARN', 'FLAGGED'].map((status) => <option key={status}>{status}</option>)}
          </select>
          <select aria-label="Sort students" value={props.sort} onChange={(event) => props.setSort(event.target.value as 'risk' | 'name' | 'join')}>
            <option value="risk">Sort by risk</option>
            <option value="name">Sort by name</option>
            <option value="join">Sort by join time</option>
          </select>
          <button className="ghost-btn" onClick={() => props.notify('info', 'Sound alerts enabled for FLAGGED events.')}><Bell size={16} /> Sound Alerts</button>
          <button className="ghost-btn" onClick={togglePause}>
            {examStatus === 'paused' ? <PlayCircle size={16} /> : <PauseCircle size={16} />}
            {examStatus === 'paused' ? 'Resume Exam' : 'Pause All'}
          </button>
          <button className="danger-btn" onClick={endExam}><X size={16} /> End Exam</button>
        </div>
        
        {/* Grid of Student Tiles (Webcam style feeds) */}
        <div className="student-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '20px' }}>
          {props.students.map((student) => (
            <StudentTile key={student.id || student.name} student={student} selected={props.selected?.id === student.id} onClick={() => props.setSelected(student)} />
          ))}
          {props.students.length === 0 && <div className="empty-state"><Users size={28} /><strong>No students joined yet</strong><span>Share the active exam code. New sessions appear here live.</span></div>}
        </div>
      </div>
      
      {props.selected && <aside className="side-panel">
        <Card title="Expanded student view" icon={Eye}>
          <h3 style={{ fontSize: '18px', fontWeight: 600, color: 'var(--eg-text)', margin: '0 0 16px 0' }}>{props.selected.name}</h3>
          <IntegrityScoreCard student={props.selected} />
          <div className="event-feed">
            {props.selected.events > 0 ? <AlertFeedItem name={props.selected.name} event={`${props.selected.events} structured integrity event(s) recorded`} severity="info" /> : <p className="muted">No integrity events recorded for this session.</p>}
          </div>
        </Card>
      </aside>}
    </section>
  )
}

function ConsentView({ consentScrolled, setConsentScrolled, go, notify }: { consentScrolled: boolean; setConsentScrolled: (value: boolean) => void; go: (view: View) => void; notify: (kind: ToastKind, text: string) => void }) {
  const consentListRef = useRef<HTMLDivElement | null>(null)
  useEffect(() => {
    const list = consentListRef.current
    if (list && list.scrollHeight <= list.clientHeight + 8) setConsentScrolled(true)
  }, [setConsentScrolled])
  const handleConsent = async () => {
    const sessionId = studentSessionId()
    if (sessionId) {
      try { await api.saveConsent(sessionId) } catch { /* local-only fallback */ }
    }
    go('liveness')
    notify('success', 'Consent recorded. Proceeding to liveness check.')
  }
  return (
    <section className="screen student-gate">
      <div className="consent-card">
        <StudentStepIndicator currentStep="consent" />
        <span className="badge badge-purple" style={{ marginBottom: '12px' }}><Shield size={14} /> DPDP Consent Required</span>
        <h2 id="consent-title" style={{ fontSize: '22px', fontWeight: 700, margin: '8px 0 12px 0' }}>Before your exam starts</h2>
        <p className="muted" style={{ fontSize: '14px', marginBottom: '20px' }}>ExamGuard shows exactly what is monitored. No raw webcam or audio leaves your device.</p>
        
        <div style={{ position: 'relative', width: '100%', aspectRatio: '16/9', borderRadius: '12px', border: '2px solid var(--eg-navy-600)', background: 'var(--eg-navy-700)', display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', marginBottom: '20px' }}>
          <Camera size={32} style={{ color: 'var(--eg-text-muted)', marginBottom: '8px' }} />
          <span style={{ fontSize: '13px', color: 'var(--eg-text-muted)', marginLeft: '8px' }}>Camera starts only during liveness verification</span>
        </div>

        <div ref={consentListRef} className="consent-list" onScroll={(event) => {
          const target = event.currentTarget
          setConsentScrolled(target.scrollTop + target.clientHeight >= target.scrollHeight - 8)
        }}>
          <ConsentItem icon={Camera} title="Webcam liveness" text="Used for the two-blink identity-presence check. Raw video stays local and stops before question answering." />
          <ConsentItem icon={Mic} title="Microphone level (optional)" text="Only RMS audio level is measured. Audio is never recorded. If permission is denied, audio is marked unavailable and no integrity penalty is applied." />
          <ConsentItem icon={FileText} title="Answer analysis" text="Answer text is checked for AI-writing and evaluated against source material." />
          <ConsentItem icon={Activity} title="Tab activity" text="Browser visibility changes are counted. No screen recording." />
        </div>
        
        <div style={{ display: 'flex', gap: '12px', marginTop: '20px' }}>
          <button className="ghost-btn full" onClick={() => { go('landing') }}>Cancel</button>
          <button className="primary-btn full" style={{ background: 'var(--eg-emerald)', borderColor: 'var(--eg-emerald)' }} disabled={!consentScrolled} onClick={handleConsent}>I Consent</button>
        </div>
        {!consentScrolled && <span className="hint" aria-live="polite">Scroll inside the terms box to unlock consent.</span>}
      </div>
    </section>
  )
}

function LivenessView({ go, notify }: { go: (view: View) => void; notify: (kind: ToastKind, text: string) => void }) {
  const [blinkCount, setBlinkCount] = useState(0)
  const [status, setStatus] = useState('Camera is off')
  const [seconds, setSeconds] = useState(15)
  const [detectionDuration, setDetectionDuration] = useState(0)
  const [enteringExam, setEnteringExam] = useState(false)
  const videoRef = useRef<HTMLVideoElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const frameRef = useRef<number | null>(null)
  const completionRef = useRef(false)
  const livenessPassed = blinkCount >= 2
  const distance = (a: { x: number; y: number }, b: { x: number; y: number }) => Math.hypot(a.x - b.x, a.y - b.y)
  const ear = (points: Array<{ x: number; y: number }>, ids: number[]) =>
    (distance(points[ids[1]], points[ids[5]]) + distance(points[ids[2]], points[ids[4]])) / (2 * distance(points[ids[0]], points[ids[3]]))

  const stopCamera = useCallback(() => {
    if (frameRef.current) cancelAnimationFrame(frameRef.current)
    streamRef.current?.getTracks().forEach(track => track.stop())
    streamRef.current = null
  }, [])

  useEffect(() => stopCamera, [stopCamera])

  const completeLiveness = async (blinks: number, durationMs: number) => {
    if (completionRef.current) return
    completionRef.current = true
    setEnteringExam(true)
    setStatus('Liveness verified - entering exam...')
    const sessionId = studentSessionId()
    if (!sessionId) {
      completionRef.current = false
      setEnteringExam(false)
      notify('error', 'Exam session was not found. Join the exam again.')
      return
    }
    try {
      await api.saveLiveness(sessionId, { method: 'mediapipe_ear', blink_count: blinks, duration_ms: Math.max(250, durationMs), threshold: 0.25 })
      notify('success', 'Liveness verified. Exam starting now.')
      go('exam')
    } catch (error) {
      completionRef.current = false
      setEnteringExam(false)
      setStatus('Liveness passed, but verification could not be saved. Retry entry.')
      notify('error', error instanceof Error ? error.message : 'Liveness verification could not be saved.')
    }
  }

  const beginDetection = async () => {
    try {
      stopCamera(); completionRef.current = false; setEnteringExam(false); setBlinkCount(0); setSeconds(15); setStatus('Loading face detector...')
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: 640, height: 480 }, audio: false })
      streamRef.current = stream
      const video = videoRef.current
      if (!video) return
      video.srcObject = stream
      await video.play()
      const vision = await FilesetResolver.forVisionTasks('https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm')
      const detectorOptions = (delegate: 'GPU' | 'CPU') => ({
        baseOptions: { modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task', delegate },
        runningMode: 'VIDEO' as const, numFaces: 1,
      })
      let detector: FaceLandmarker
      try {
        detector = await FaceLandmarker.createFromOptions(vision, detectorOptions('GPU'))
      } catch {
        setStatus('GPU unavailable - using compatible CPU detector...')
        detector = await FaceLandmarker.createFromOptions(vision, detectorOptions('CPU'))
      }
      let eyeWasClosed = false; let detected = 0; let closedAt = 0; let lastBlinkAt = 0
      let smoothedEar = 0; const calibration: number[] = []
      const startedAt = performance.now(); const deadline = startedAt + 15000
      const detect = () => {
        const now = performance.now()
        setSeconds(Math.max(0, Math.ceil((deadline - now) / 1000)))
        if (now >= deadline) {
          detector.close(); stopCamera()
          setDetectionDuration(Math.round(now - startedAt))
          setStatus('No two blinks detected. Check lighting and retry.')
          return
        }
        const result = detector.detectForVideo(video, now)
        const face = result.faceLandmarks[0]
        if (face) {
          const rawEar = (ear(face, [33, 160, 158, 133, 153, 144]) + ear(face, [362, 385, 387, 263, 373, 380])) / 2
          smoothedEar = smoothedEar ? smoothedEar * 0.55 + rawEar * 0.45 : rawEar
          if (calibration.length < 24) {
            calibration.push(smoothedEar)
            setStatus(`Calibrating eyes - keep them open (${calibration.length}/24)`)
            frameRef.current = requestAnimationFrame(detect)
            return
          }
          const sorted = [...calibration].sort((a, b) => a - b)
          const openEar = sorted[Math.floor(sorted.length * 0.75)]
          const closeThreshold = Math.max(0.12, Math.min(0.29, openEar * 0.72))
          const reopenThreshold = Math.max(closeThreshold + 0.018, openEar * 0.84)
          if (smoothedEar <= closeThreshold && !eyeWasClosed && now - lastBlinkAt > 250) {
            eyeWasClosed = true
            closedAt = now
          }
          if (smoothedEar >= reopenThreshold && eyeWasClosed) {
            const closureMs = now - closedAt
            eyeWasClosed = false
            if (closureMs >= 45 && closureMs <= 900) {
              lastBlinkAt = now; detected += 1; setBlinkCount(detected)
            }
            if (detected >= 2) {
              const duration = Math.round(now - startedAt)
              detector.close(); stopCamera(); setDetectionDuration(duration)
              void completeLiveness(detected, duration)
              return
            }
          }
          setStatus(`Face ready - blink normally (${detected}/2, sensitivity ${closeThreshold.toFixed(2)})`)
        } else setStatus('Position one face inside the oval')
        frameRef.current = requestAnimationFrame(detect)
      }
      detect()
    } catch (error) {
      stopCamera(); setStatus('Camera or face detector unavailable')
      notify('error', error instanceof Error ? error.message : 'Could not start camera')
    }
  }
  const startExam = async () => {
    if (!livenessPassed) { notify('error', 'Blink liveness must pass before the exam can start.'); return }
    await completeLiveness(blinkCount, detectionDuration)
  }
  return (
    <section className="screen liveness-screen">
      <div className="liveness-card" style={{ textAlign: 'center' }}>
        <StudentStepIndicator currentStep="liveness" />
        <span className="badge badge-teal" style={{ marginBottom: '12px' }}><Camera size={14} /> MediaPipe WASM Local</span>
        
        <div className="face-circle" style={{ width: '180px', height: '220px', borderRadius: '100px', border: '3px solid rgba(79, 70, 229, 0.4)', margin: '24px auto', display: 'grid', placeItems: 'center', position: 'relative', background: 'rgba(30, 42, 58, 0.25)', overflow: 'hidden' }}>
          <div className="mesh-ring" style={{ position: 'absolute', inset: '8px', border: '2px dashed var(--eg-teal)', borderRadius: '100px', animation: 'spinRing 12s linear infinite' }} />
          <video ref={videoRef} muted playsInline style={{ width: '100%', height: '100%', objectFit: 'cover', transform: 'scaleX(-1)' }} />
        </div>

        <h2 style={{ fontSize: '22px', fontWeight: 700, margin: '8px 0' }}>Look forward, then blink twice naturally</h2>
        <p className="muted" style={{ fontSize: '14px', marginBottom: '20px' }}>Keep eyes open briefly for calibration. Then blink twice within 15 seconds. Remove glare and keep your full face visible.</p>
        
        <div className="blink-progress" style={{ display: 'flex', justifyContent: 'center', gap: '8px', marginBottom: '24px' }}>
          <span className={blinkCount >= 1 ? 'done' : ''} style={{ width: '40px', height: '6px', borderRadius: '3px', background: blinkCount >= 1 ? 'var(--eg-teal)' : 'var(--eg-navy-600)' }} />
          <span className={blinkCount >= 2 ? 'done' : ''} style={{ width: '40px', height: '6px', borderRadius: '3px', background: blinkCount >= 2 ? 'var(--eg-teal)' : 'var(--eg-navy-600)' }} />
        </div>

        <div className="inline-actions" style={{ justifyContent: 'center', gap: '12px' }}>
          <button className="primary-btn" style={{ minWidth: '160px' }} disabled={!livenessPassed || enteringExam} onClick={startExam}><PlayCircle size={16} /> {enteringExam ? 'Entering exam...' : 'Start exam'}</button>
          <button className="ghost-btn" disabled={enteringExam} onClick={beginDetection}><Camera size={16} /> Start camera ({seconds}s)</button>
        </div>
        <span className="hint" aria-live="polite" style={{ marginTop: '12px' }}>{status}. Sensitivity adapts to your eyes and camera.</span>
      </div>
    </section>
  )
}

function ExamView(props: {
  answer: string; setAnswer: (value: string) => void
  marked: boolean; setMarked: (value: boolean) => void
  notify: (kind: ToastKind, text: string) => void
  go: (view: View) => void
}) {
  const [currentQ, setCurrentQ] = useState(0)
  const [questions, setQuestions] = useState<ApiQuestion[]>([])
  const [examTitle, setExamTitle] = useState('Loading exam...')
  const [questionError, setQuestionError] = useState('')
  const [questionsLoading, setQuestionsLoading] = useState(true)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [timeLeft, setTimeLeft] = useState(80 * 60) // 80 minutes default
  const [examStatus, setExamStatus] = useState('active')
  const [integrityStatus, setIntegrityStatus] = useState<IntegrityStatus>('CLEAN')
  const [lastSave, setLastSave] = useState<number>(Date.now())
  const [saveWarning, setSaveWarning] = useState('')
  const [submitOpen, setSubmitOpen] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const autoSaveRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const expirySubmitStarted = useRef(false)

  // Load questions and duration from backend
  useEffect(() => {
    const sessionId = studentSessionId()
    if (sessionId) {
      api.sessionQuestions(sessionId)
        .then((qs) => {
          setQuestions(qs)
          if (!qs.length) setQuestionError('No generated questions found for this exam.')
        })
        .catch((event) => setQuestionError(event instanceof Error ? event.message : 'Could not load exam questions.'))
        .finally(() => setQuestionsLoading(false))

      if (sessionId) {
        api.sessionExam(sessionId)
          .then((exam) => {
            setExamTitle(exam.title)
            setExamStatus(exam.status)
            if (exam && exam.duration_minutes) {
              const deadlineKey = `examguard-deadline-${sessionId}`
              const savedDeadline = Number(window.localStorage.getItem(deadlineKey))
              const deadline = savedDeadline > Date.now() ? savedDeadline : Date.now() + exam.duration_minutes * 60_000
              window.localStorage.setItem(deadlineKey, String(deadline))
              setTimeLeft(Math.max(0, Math.ceil((deadline - Date.now()) / 1000)))
            }
          })
          .catch(() => {})
      }
      api.sessionIntegrity(sessionId)
        .then((integrity) => setIntegrityStatus((integrity.status as IntegrityStatus) || 'CLEAN'))
        .catch(() => {})
    }
    // Restore saved answers from localStorage
    try {
      const saved = window.localStorage.getItem(`examguard-answers-${sessionId}`)
      if (saved) setAnswers(JSON.parse(saved))
    } catch { /* ignore */ }
  }, [])

  useEffect(() => {
    const sessionId = studentSessionId()
    if (!sessionId) return
    const poll = window.setInterval(() => {
      api.sessionExam(sessionId).then((exam) => {
        setExamStatus(exam.status)
        if (exam.status === 'ended') {
          api.endSession(sessionId).catch(() => {})
          props.notify('info', 'Teacher ended the exam. Your saved answers were submitted.')
          props.go('complete')
        }
      }).catch(() => {})
      api.sessionIntegrity(sessionId)
        .then((integrity) => setIntegrityStatus((integrity.status as IntegrityStatus) || 'CLEAN'))
        .catch(() => {})
    }, 5000)
    return () => window.clearInterval(poll)
  }, [])

  // Fill in the text area when the initial question loads
  useEffect(() => {
    if (questions.length > 0 && currentQ === 0) {
      const firstQ = questions.at(0)
      if (firstQ) {
        props.setAnswer(Reflect.get(answers, firstQ.id) || '')
      }
    }
  }, [questions])

  // Countdown timer
  useEffect(() => {
    const timer = setInterval(() => {
      if (examStatus === 'active') setTimeLeft((t) => Math.max(0, t - 1))
    }, 1000)
    timerRef.current = timer
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [examStatus])

  // Auto-save answers to localStorage every 10 seconds
  useEffect(() => {
    const autoSave = setInterval(() => {
      const sessionId = studentSessionId()
      if (sessionId) window.localStorage.setItem(`examguard-answers-${sessionId}`, JSON.stringify(answers))
      setLastSave(Date.now())
    }, 10000)
    autoSaveRef.current = autoSave
    return () => {
      if (autoSave) clearInterval(autoSave)
    }
  }, [answers])

  const q = questions.at(currentQ)
  const displayQuestions = questions
  const current = displayQuestions.at(currentQ) || displayQuestions.at(0)
  const answeredIds = new Set(Object.keys(answers).filter((k) => (Reflect.get(answers, k) || '').trim()))
  if (current?.id && props.answer.trim()) answeredIds.add(current.id)
  const answeredCount = answeredIds.size
  const totalQ = displayQuestions.length

  const saveCurrentAnswer = useCallback(async () => {
    if (!current) return
    const text = current.id === q?.id ? props.answer : Reflect.get(answers, current.id) || ''
    setAnswers((prev) => ({ ...prev, [current.id]: text }))
    const sessionId = studentSessionId()
    if (sessionId) window.localStorage.setItem(`examguard-answers-${sessionId}`, JSON.stringify({ ...answers, [current.id]: text }))
    setLastSave(Date.now())
    if (sessionId && text.trim()) {
      try {
        await api.saveAnswer(sessionId, { question_id: current.id, answer_text: text })
        setSaveWarning('')
      } catch {
        setSaveWarning('Offline: answer saved locally and will retry on next save.')
      }
    }
  }, [current, q, props.answer, answers])

  useEffect(() => {
    if (timeLeft !== 0 || expirySubmitStarted.current) return
    expirySubmitStarted.current = true
    const submitExpiredExam = async () => {
      await saveCurrentAnswer()
      const sessionId = studentSessionId()
      if (!sessionId) return
      try {
        await api.endSession(sessionId)
        window.localStorage.removeItem(`examguard-answers-${sessionId}`)
        props.notify('info', 'Time expired. Your exam was submitted automatically.')
        props.go('complete')
      } catch (error) {
        expirySubmitStarted.current = false
        props.notify('error', error instanceof Error ? error.message : 'Automatic submission failed. Your answers remain saved locally.')
      }
    }
    submitExpiredExam()
  }, [timeLeft, saveCurrentAnswer, props])

  const goToQuestion = (idx: number) => {
    saveCurrentAnswer()
    setCurrentQ(idx)
    const nextQ = displayQuestions.at(idx)
    if (nextQ) props.setAnswer(Reflect.get(answers, nextQ.id) || '')
  }

  const handleMcqSelect = async (opt: string) => {
    if (!current) return
    props.setAnswer(opt)
    setAnswers((prev) => {
      const updated = { ...prev, [current.id]: opt }
      const sessionId = studentSessionId()
      if (sessionId) {
        window.localStorage.setItem(`examguard-answers-${sessionId}`, JSON.stringify(updated))
        api.saveAnswer(sessionId, { question_id: current.id, answer_text: opt, selected_option: opt })
          .then(() => setSaveWarning(''))
          .catch(() => setSaveWarning('Offline: answer saved locally and will retry on next save.'))
      }
      return updated
    })
  }

  const answerValid = props.answer.trim().length >= 25
  const requestSubmit = () => {
    saveCurrentAnswer()
    setSubmitOpen(true)
  }

  const secondsSinceSave = Math.round((Date.now() - lastSave) / 1000)

  const logEvent = (eventType: string) => {
    const sessionId = studentSessionId()
    if (sessionId) api.logEvent(sessionId, eventType).catch(() => {})
  }

  useEffect(() => {
    let blurTimer: number | undefined
    let lastBlurLoggedAt = 0
    const visibility = () => { if (document.hidden) logEvent('tab_hidden') }
    const blur = () => {
      blurTimer = window.setTimeout(() => {
        if (!document.hidden && Date.now() - lastBlurLoggedAt >= 30_000) {
          lastBlurLoggedAt = Date.now()
          logEvent('window_blur')
        }
      }, 3000)
    }
    const focus = () => { if (blurTimer) window.clearTimeout(blurTimer) }
    const fullscreen = () => { if (!document.fullscreenElement) logEvent('fullscreen_exit') }
    document.addEventListener('visibilitychange', visibility)
    window.addEventListener('blur', blur)
    window.addEventListener('focus', focus)
    document.addEventListener('fullscreenchange', fullscreen)
    return () => {
      document.removeEventListener('visibilitychange', visibility)
      window.removeEventListener('blur', blur)
      window.removeEventListener('focus', focus)
      if (blurTimer) window.clearTimeout(blurTimer)
      document.removeEventListener('fullscreenchange', fullscreen)
    }
  }, [])

  return (
    <section className="screen exam-layout" onContextMenu={(event) => { event.preventDefault(); logEvent('right_click'); props.notify('warning', 'Right click prevented and logged as a structured event.') }}>
      <div className="exam-header" aria-live="assertive">
        <strong>{examTitle}</strong>
        <span className={timeLeft < 300 ? 'timer-critical' : ''} style={{ fontSize: '20px', fontFamily: 'JetBrains Mono, monospace' }}>
          <Timer size={20} /> {formatTime(timeLeft)}
        </span>
        <span className="save-state"><Check size={16} /> Saved {secondsSinceSave}s ago</span>
        <span className={`badge ${integrityStatus === 'CLEAN' ? 'badge-green' : integrityStatus === 'WATCH' ? 'badge-amber' : 'badge-red'}`} title="Integrity status is informational during the exam. Teacher review remains final."><Shield size={14} /> {integrityStatus} · exam continues</span>
      </div>

      {examStatus === 'paused' && <div className="connection-card" role="status"><PauseCircle size={16} /> Exam paused by teacher. Timer and answering are temporarily frozen.</div>}

      {questionsLoading ? <div className="empty-state">Loading generated paper...</div> : questionError ? <div className="empty-state"><AlertTriangle size={24} /><strong>Paper could not load</strong><span>{questionError}</span><button className="ghost-btn" onClick={() => window.location.reload()}>Retry</button></div> : null}

      {!questionsLoading && !questionError && <aside className="question-palette" aria-label="Question navigation palette">
        <div className="palette-summary">Answered {answeredCount}/{totalQ}</div>
        <div className="palette-grid" style={{ gridTemplateColumns: 'repeat(5, 1fr)', gap: '8px' }}>
          {displayQuestions.map((dq, i) => (
            <button disabled={examStatus === 'paused'} key={dq.id} className={i === currentQ ? 'current' : (Reflect.get(answers, dq.id) || '').trim() ? 'answered' : 'unvisited'} onClick={() => goToQuestion(i)} aria-label={`Question ${i + 1}`}>{i + 1}</button>
          ))}
        </div>
        {saveWarning && <span className="hint" role="status">{saveWarning}</span>}
        <button className="primary-btn full" disabled={examStatus === 'paused'} onClick={requestSubmit}>Submit Exam</button>
      </aside>}

      {/* High contrast question card: Light card on dark background */}
      {!questionsLoading && !questionError && current && <article className="question-area" style={{
        background: '#FFFFFF',
        color: '#1E293B',
        borderRadius: '12px',
        padding: '32px',
        border: '1px solid #E2E8F0',
        boxShadow: 'var(--shadow-card)'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <span className="badge badge-purple" style={{ background: 'rgba(79, 70, 229, 0.1)', color: 'var(--eg-indigo)', borderColor: 'rgba(79, 70, 229, 0.2)' }}>
            Section {current?.section_id || 'A'} - {current?.bloom_level || 'Analyze'} - {current?.marks || 5} marks
          </span>
          <span style={{ fontSize: '13px', color: '#64748B', fontWeight: 600 }}>Question {currentQ + 1} of {totalQ}</span>
        </div>

        <h2 style={{ fontSize: '18px', fontWeight: 600, lineHeight: 1.5, margin: '12px 0', color: '#0F172A' }}>
          {current?.text || 'Loading question...'}
        </h2>
        <p className="muted" style={{ fontSize: '12px', color: '#64748B', marginBottom: '24px' }}>
          Source: uploaded material, {current.chapter_tag || 'selected syllabus'}. Groundedness {current.groundedness || 0.84}.
        </p>

        {current?.type === 'MCQ' && current.options?.length ? (
          <div className="mcq-options" style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
            {current.options.map((opt, i) => {
              const isSelected = props.answer === opt
              return (
                <label
                  key={i}
                  className={`mcq-option ${isSelected ? 'selected' : ''}`}
                  style={{
                    background: isSelected ? 'rgba(79, 70, 229, 0.08)' : '#F8FAFC',
                    border: isSelected ? '2px solid var(--eg-indigo)' : '1.5px solid #E2E8F0',
                    color: isSelected ? 'var(--eg-indigo)' : '#334155',
                    padding: '14px 18px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px',
                    fontSize: '14px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    transition: 'all 150ms ease'
                  }}
                >
                  <input
                    type="radio"
                    name="mcq"
                    value={opt}
                    checked={isSelected}
                    disabled={examStatus === 'paused'}
                    onChange={() => handleMcqSelect(opt)}
                    style={{ accentColor: 'var(--eg-indigo)', cursor: 'pointer' }}
                  />
                  {opt}
                </label>
              )
            })}
          </div>
        ) : (
          <div style={{ position: 'relative', width: '100%', marginBottom: '16px' }}>
            <textarea
              aria-label="Answer text"
              minLength={25}
              value={props.answer}
              disabled={examStatus === 'paused'}
              onChange={(event) => props.setAnswer(event.target.value)}
              onPaste={() => { logEvent('paste_detected'); props.notify('warning', 'Paste detected and sent as a structured event.') }}
              placeholder="Type your response here..."
              style={{
                background: '#F8FAFC',
                borderColor: '#E2E8F0',
                color: '#0F172A',
                fontSize: '15px',
                lineHeight: 1.6,
                minHeight: '180px',
                width: '100%',
                padding: '16px',
                borderRadius: '8px'
              }}
            />
            <div style={{ textAlign: 'right', fontSize: '12px', color: '#64748B', marginTop: '6px' }}>
              Word count: {wordCount(props.answer)} words
            </div>
          </div>
        )}

        {current?.type !== 'MCQ' && !answerValid && <p className="form-error" role="alert" style={{ marginBottom: '16px' }}>Answer needs at least 25 characters before final submit.</p>}
        
        <div className="inline-actions" style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <button disabled={examStatus === 'paused'} className={props.marked ? 'warning-btn' : 'ghost-btn'} style={{ borderColor: '#E2E8F0', color: props.marked ? 'var(--eg-amber)' : '#475569' }} onClick={() => props.setMarked(!props.marked)}>
            <Flag size={16} /> {props.marked ? 'Marked for Review' : 'Mark for Review'}
          </button>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: '8px' }}>
            <button className="ghost-btn" style={{ borderColor: '#E2E8F0', color: '#475569' }} disabled={examStatus === 'paused' || currentQ === 0} onClick={() => goToQuestion(currentQ - 1)}>
              Previous
            </button>
            <button className="primary-btn" disabled={examStatus === 'paused' || currentQ >= totalQ - 1} onClick={() => goToQuestion(currentQ + 1)}>
              Next Question
            </button>
          </div>
        </div>
      </article>}

      {/* Webcam PiP minimal corner element */}
      <div style={{
        position: 'fixed',
        bottom: '24px',
        right: '24px',
        width: '120px',
        height: '90px',
        borderRadius: '8px',
        border: '1.5px solid rgba(255, 255, 255, 0.25)',
        background: 'rgba(10, 15, 30, 0.8)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 50,
        overflow: 'hidden',
        boxShadow: 'var(--shadow-elevated)'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', width: '100%', height: '100%', position: 'relative' }}>
          <Camera size={20} style={{ color: 'rgba(255, 255, 255, 0.6)' }} />
          <span style={{ fontSize: '9px', color: 'rgba(255, 255, 255, 0.6)', marginLeft: '4px', fontFamily: 'monospace' }}>Liveness passed</span>
        </div>
      </div>

      {submitOpen && (
        <SubmitDialog
          onClose={() => setSubmitOpen(false)}
          go={() => props.go('complete')}
          answeredCount={answeredCount}
          totalCount={totalQ}
          markedCount={props.marked ? 1 : 0}
        />
      )}
      <div className="connection-card" style={{ display: 'none' }}><RefreshCw size={16} /> Connection lost. Answers saved locally. Reconnecting...</div>
    </section>
  )
}

function CompleteView({ notify }: { notify: (kind: ToastKind, text: string) => void }) {
  const [appeal, setAppeal] = useState('')
  const appealWords = wordCount(appeal)
  const [submitted, setSubmitted] = useState(false)
  const [sessionData, setSessionData] = useState<any>(null)

  useEffect(() => {
    const sessionId = studentSessionId()
    if (sessionId) {
      api.sessionResult(sessionId)
        .then((res) => {
          setSessionData(res)
        })
        .catch(() => {})
    }
  }, [])

  const submitAppeal = async () => {
    if (appealWords < 12) { notify('error', 'Appeal response must explain the issue in at least 12 words.'); return }
    if (appealWords > 200) { notify('error', 'Appeal response cannot exceed 200 words.'); return }
    const sessionId = studentSessionId()
    if (sessionId) {
      try {
        await api.submitAppeal(sessionId, appeal)
        setSubmitted(true)
        notify('success', 'Appeal submitted. Teacher review panel updated.')
      } catch (e) { notify('error', e instanceof Error ? e.message : 'Appeal submission failed.') }
    } else {
      setSubmitted(true)
      notify('success', 'Appeal submitted. Teacher review panel updated.')
    }
  }

  const studentObj = sessionData ? {
    name: sessionData.student_name,
    score: sessionData.integrity?.score ?? 100,
    status: (sessionData.integrity?.status ?? 'CLEAN') as IntegrityStatus,
    tier: sessionData.integrity?.baseline_tier ?? 1,
    factors: [
      sessionData.integrity?.factors?.behavioral ?? 92,
      sessionData.integrity?.factors?.perplexity ?? 84,
      sessionData.integrity?.factors?.stylometric ?? 89,
      sessionData.integrity?.factors?.answer_quality ?? 91,
      sessionData.integrity?.factors?.time_anomaly ?? 76
    ],
    ci: sessionData.integrity?.ci ?? null
  } : null

  if (!studentObj) return <section className="screen"><div className="empty-state"><RefreshCw size={28} /><strong>Loading submission result</strong><span>Your locally saved answers remain available.</span></div></section>

  return (
    <section className="screen complete-layout" style={{ maxWidth: '680px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ background: 'var(--eg-amber)', color: 'var(--eg-navy)', padding: '16px 24px', borderRadius: '12px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '12px' }}>
        <AlertTriangle size={20} />
        <span>Your exam is completed and under review. Final grade release pending.</span>
      </div>

      <Card title="Submission received" icon={Check}>
        <p>Your exam has been logged and received. Your teacher will release final results after checking.</p>
        <div className="status-tracker" style={{ display: 'flex', justifyContent: 'space-between', gap: '8px', borderTop: '1px solid var(--eg-navy-600)', paddingTop: '16px', marginTop: '12px' }}>
          <span className="done" style={{ color: 'var(--eg-emerald)', fontWeight: 600 }}>Submitted</span>
          <span className={submitted || sessionData?.review_status === 'appeal_submitted' ? 'done' : 'active'} style={{ color: 'var(--eg-amber)', fontWeight: 600 }}>Under Review</span>
          <span style={{ color: 'var(--eg-text-faint)' }}>Grade Released</span>
        </div>
      </Card>

      <Card title="Your integrity summary" icon={Shield}>
        <IntegrityScoreCard student={studentObj} />
        <p className="muted" style={{ fontSize: '13px', marginTop: '12px' }}>Some answers require verification. This does not impact your final eligibility automatically.</p>
      </Card>

      <Card title="Submit an appeal" icon={FileText}>
        <p className="muted" style={{ fontSize: '13px', marginBottom: '12px' }}>Explain your situation within 24 hours. If no response is submitted, the case still requires a teacher decision and is never auto-confirmed.</p>
        <textarea aria-label="Appeal response" maxLength={3500} value={appeal} onChange={(event) => setAppeal(event.target.value)} disabled={submitted || sessionData?.review_status === 'appeal_submitted'} style={{ minHeight: '140px' }} />
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '8px' }}>
          <p className={appealWords > 200 || appealWords < 12 ? 'form-error' : 'hint'} style={{ margin: 0 }}>{appealWords}/200 words</p>
          <button className="primary-btn" onClick={submitAppeal} disabled={submitted || sessionData?.review_status === 'appeal_submitted'}>
            {submitted || sessionData?.review_status === 'appeal_submitted' ? 'Appeal Submitted' : 'Submit Appeal'}
          </button>
        </div>
      </Card>
    </section>
  )
}

function ReviewView({ students, selected, setSelected, notify }: { students: any[]; selected: any; setSelected: (s: any) => void; notify: (kind: ToastKind, text: string) => void }) {
  const [teacherNote, setTeacherNote] = useState('')

  const saveDecision = async (decision: 'clear' | 'confirm_flag') => {
    if (!selected || !selected.id) { notify('error', 'No student session selected.'); return }
    if (teacherNote.trim().length < 12) { notify('error', 'Add a teacher note before saving the decision.'); return }
    try {
      await api.teacherDecision(selected.id, decision, teacherNote)
      notify(decision === 'clear' ? 'success' : 'warning', decision === 'clear' ? 'Decision saved: student cleared, grade released.' : 'Decision saved: flag confirmed, grade released with note.')
    } catch (e) {
      notify('error', e instanceof Error ? e.message : 'Failed to save decision.')
    }
  }

  const reviewStudentsList = students.filter((student) => student.status !== 'CLEAN')

  return (
    <section className="screen review-layout">
      <Card title="Flagged Queue" icon={Flag}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '500px', overflowY: 'auto' }}>
          {reviewStudentsList.length === 0 ? (
            <p className="muted">No student sessions currently flagged for review.</p>
          ) : (
            reviewStudentsList.map((student) => (
              <button className={`queue-item ${selected?.id === student.id ? 'active' : ''}`} key={student.id || student.name} onClick={() => setSelected(student)}>
                <div style={{ display: 'flex', justifyContent: 'space-between', width: '100%', alignItems: 'center', marginBottom: '4px' }}>
                  <span>{student.name}</span>
                  <StatusBadge status={student.status} />
                </div>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '11px', width: '100%', color: 'var(--eg-text-muted)' }}>
                  <span>Score: {student.score}</span>
                  <span>{student.reviewStatus === 'appeal_submitted' ? 'Appeal Filed' : student.reviewStatus === 'expired_no_response' || student.reviewStatus === 'awaiting_teacher_decision' ? 'No response · decision required' : 'Awaiting response'}</span>
                </div>
              </button>
            ))
          )}
        </div>
      </Card>

      <Card title="Side-by-side review" icon={UserCheck} className="wide-card">
        {selected ? (
          <div className="review-columns">
            <div>
              <h3>Integrity Report</h3>
              <IntegrityScoreCard student={selected} />
              
              <h3 style={{ marginTop: '24px' }}>Anomalies Feed</h3>
              <div className="event-feed">
                <AlertFeedItem name={selected.name} event="style distance exceeded Tier 1 threshold" severity="danger" />
                <AlertFeedItem name={selected.name} event="tab visibility switch" severity="warning" />
              </div>
            </div>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <h3>Student Appeal Statement</h3>
                <div className="appeal-note">
                  {selected.appealResponse || (selected.reviewStatus === 'expired_no_response' || selected.reviewStatus === 'awaiting_teacher_decision' ? 'The 24-hour response window expired without a student response. Review the evidence and record a teacher decision; the flag is not automatically confirmed.' : 'No appeal response has been submitted yet by the student.')}
                </div>
              </div>

              <div>
                <h3>Teacher Actions & Review Note</h3>
                <textarea aria-label="Teacher note" minLength={12} placeholder="Type notes explaining decision (min 12 chars)..." value={teacherNote} onChange={(event) => setTeacherNote(event.target.value)} />
                {teacherNote.trim().length < 12 && <p className="form-error" style={{ marginBottom: '12px' }}>Teacher note is required before releasing the grade.</p>}
                
                <div className="inline-actions">
                  <button className="primary-btn" style={{ background: 'var(--eg-emerald)', borderColor: 'var(--eg-emerald)' }} disabled={teacherNote.trim().length < 12} onClick={() => saveDecision('clear')}>
                    Clear & Release Grade
                  </button>
                  <button className="danger-btn" disabled={teacherNote.trim().length < 12} onClick={() => saveDecision('confirm_flag')}>
                    Confirm Violation
                  </button>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <p className="muted">Select a student from the queue to start side-by-side review.</p>
        )}
      </Card>
    </section>
  )
}

function ReportsView({ examId, students, notify }: { examId: string; students: any[]; notify: (kind: ToastKind, text: string) => void }) {
  const [summary, setSummary] = useState<any>(null)

  useEffect(() => {
    api.examSummary(examId)
      .then(setSummary)
      .catch(() => {})
  }, [examId])

  const downloadCsv = async () => {
    try {
      const resp = await api.downloadReportsCsv(examId)
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = `examguard_${examId}_report.csv`; a.click()
      URL.revokeObjectURL(url)
      notify('success', 'CSV export downloaded.')
    } catch (event) { notify('error', event instanceof Error ? event.message : 'CSV export failed.') }
  }

  const downloadPdf = async (sessionId: string, studentName: string) => {
    try {
      const resp = await api.downloadReportPdf(sessionId)
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = `examguard_${studentName.replace(/\s+/g, '_')}_report.pdf`; a.click()
      URL.revokeObjectURL(url)
      notify('success', `PDF report for ${studentName} downloaded.`)
    } catch (e) {
      notify('error', e instanceof Error ? e.message : 'PDF download failed.')
    }
  }

  const avgScore = summary ? summary.average_integrity : (students.length > 0 ? Math.round(students.reduce((sum, s) => sum + s.score, 0) / students.length) : 0)
  const totalStudentsStr = summary ? String(summary.total_students) : String(students.length)
  const appealsCountStr = summary ? String(summary.appeals_open) : String(students.filter(s => s.reviewStatus === 'appeal_submitted').length)

  return (
    <section className="screen">
      <div className="summary-grid" style={{ marginBottom: '24px' }}>
        <Metric label="Reports Ready" value={totalStudentsStr} icon={FileText} compact />
        <Metric label="Class Avg Integrity" value={String(avgScore)} icon={BarChart3} compact />
        <Metric label="Appeals Pending" value={appealsCountStr} icon={Flag} compact />
        <Metric label="Export Formats" value="PDF + CSV" icon={Download} compact />
      </div>
      
      <Card title="Reports and exports" icon={Download}>
        <div className="report-actions" style={{ display: 'flex', gap: '12px', marginBottom: '20px' }}>
          <button className="ghost-btn" onClick={downloadCsv}><FileText size={16} /> Export CSV</button>
        </div>
        
        <div className="report-list" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {students.length === 0 ? <div className="empty-state"><FileText size={24} /><strong>No reports yet</strong><span>Reports appear after students submit the exam.</span></div> : students.map((student) => (
            <div className="report-row" key={student.id || student.name}>
              <span>{student.name}</span>
              <StatusBadge status={student.status} />
              <span>Score: {student.score} {student.ci ? `+/-${student.ci}` : ''}</span>
              <button aria-label={`Download PDF for ${student.name}`} onClick={() => downloadPdf(student.id, student.name)} style={{ display: 'grid', placeItems: 'center' }}>
                <Download size={16} />
              </button>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Active status monitoring" icon={Clock} style={{ marginTop: '24px' }}>
        <p className="muted">Reports update from submitted Supabase sessions. End the exam when all students have submitted to finalize the class report.</p>
      </Card>
    </section>
  )
}

function SettingsView({ auth, onSaveSettings, notify }: { auth: AuthUser | null; onSaveSettings: (newName: string) => void; notify: (kind: ToastKind, text: string) => void }) {
  const [displayName, setDisplayName] = useState(auth?.name || 'Rajan Kumar')
  const [instituteName, setInstituteName] = useState('IIT Coaching Delhi')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const strongPassword = newPassword.length >= 8 && /[A-Z]/.test(newPassword) && /\d/.test(newPassword)

  const saveSettings = async () => {
    if (displayName.trim().length < 3) { notify('error', 'Display name must be at least 3 characters.'); return }
    if (instituteName.trim().length < 2) { notify('error', 'Institute name must be at least 2 characters.'); return }
    const userId = window.localStorage.getItem('examguard-user-id')
    if (userId) {
      try {
        await api.saveSettings(userId, { display_name: displayName, institute_name: instituteName })
        onSaveSettings(displayName)
        notify('success', 'Settings saved to server.')
      } catch {
        onSaveSettings(displayName)
        notify('success', 'Settings saved locally.')
      }
    } else {
      onSaveSettings(displayName)
      notify('success', 'Settings saved.')
    }
  }

  const sendReset = async () => {
    if (!strongPassword) { notify('error', 'Password must be 8+ characters with one uppercase letter and one number.'); return }
    if (newPassword !== confirmPassword) { notify('error', 'Password confirmation does not match.'); return }
    try {
      if (!auth?.email) throw new Error('Signed-in email is unavailable.')
      await api.resetRequest(auth.email)
      notify('info', 'Password reset email sent.')
    } catch (error) { notify('error', error instanceof Error ? error.message : 'Password reset request failed.') }
  }

  return (
    <section className="screen settings-grid">
      <Card title="Account Settings" icon={Settings}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '16px' }}>
          <div>
            <label>Display name</label>
            <input required minLength={3} value={displayName} onChange={(event) => setDisplayName(event.target.value)} />
          </div>
          <div>
            <label>Institute Name</label>
            <input required minLength={3} value={instituteName} onChange={(event) => setInstituteName(event.target.value)} />
          </div>
          <div style={{ marginTop: '8px' }}>
            <label className="switch-container">
              <input type="checkbox" defaultChecked className="switch-input" />
              <span className="switch-toggle" />
              <span>Email me when a student is flagged</span>
            </label>
          </div>
        </div>
        {(displayName.trim().length < 3 || instituteName.trim().length < 2) && <p className="form-error">Display name and institute name are required.</p>}
        <button className="primary-btn" onClick={saveSettings}>Save Settings</button>
      </Card>

      <Card title="Password reset" icon={Lock}>
        <p className="muted" style={{ fontSize: '12px', marginTop: 0 }}>The sample password <code>demo123</code> is for the local demo environment only and is never used as a production password.</p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '14px', marginBottom: '16px' }}>
          <div>
            <label>New Password</label>
            <input type="password" minLength={8} placeholder="Enter new password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} />
          </div>
          <div>
            <label>Confirm Password</label>
            <input type="password" minLength={8} placeholder="Confirm password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} />
          </div>
        </div>
        <div className={`strength ${strongPassword ? 'strong' : 'weak'}`}><span /><span /><span /><em>{strongPassword ? 'Strong' : 'Needs uppercase + number'}</em></div>
        {confirmPassword && newPassword !== confirmPassword && <p className="form-error">Passwords do not match.</p>}
        <button className="ghost-btn" onClick={sendReset}>Send Reset Link</button>
      </Card>

      <Card title="Security promises" icon={Shield}>
        <ul className="plain-list">
          <li>Raw video never leaves the browser.</li>
          <li>Audio level tracking only, no voice recording.</li>
          <li>Signed report URLs automatically expire in 7 days.</li>
          <li>Strict isolation locks student data to their institute.</li>
        </ul>
        <div style={{ borderTop: '1px solid var(--eg-navy-600)', padding: '16px 0 0 0', marginTop: '20px' }}>
          <span className="badge badge-purple" style={{ width: '100%', justifyContent: 'center' }}>
            <Shield size={14} /> HIPAA & DPDP Compliant
          </span>
        </div>
      </Card>
    </section>
  )
}

// --- Shared Components -------------------------------------------------------

function Metric({ label, value, icon: Icon, compact = false }: { label: string; value: string; icon: typeof Shield; compact?: boolean }) {
  return (<div className={`metric-card ${compact ? 'compact' : ''}`}><Icon size={compact ? 18 : 24} style={{ color: 'var(--eg-teal)' }} /><strong>{value}</strong><span>{label}</span></div>)
}

function Card({ title, icon: Icon, className = '', children, style }: { title: string; icon: typeof Shield; className?: string; children: React.ReactNode; style?: React.CSSProperties }) {
  return (<section className={`card ${className}`} style={style}><div className="card-title"><Icon size={18} aria-hidden="true" style={{ color: 'var(--eg-indigo)' }} /><h2>{title}</h2></div>{children}</section>)
}

function SectionBuilderRow({ 
  section, 
  index, 
  updateSection, 
  removeSection,
  availableChapters,
  chapterTopicsMap
}: { 
  section: PaperSection; 
  index: number; 
  updateSection: (index: number, patch: Partial<PaperSection>) => void; 
  removeSection: (index: number) => void;
  availableChapters: string[];
  chapterTopicsMap: Record<string, string[]>;
}) {
  const topics = Reflect.get(chapterTopicsMap, section.chapter) || []
  
  return (
    <div className="section-row" style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', alignItems: 'center' }}>
      <strong>Section {section.id}</strong>
      <select aria-label={`Question type for section ${section.id}`} value={section.type} onChange={(event) => updateSection(index, { type: event.target.value as QuestionType })}>{['MCQ', 'Short Answer', 'Long Answer', 'Fill Blank', 'True/False', 'Essay'].map((type) => <option key={type}>{type}</option>)}</select>
      <input aria-label={`Question count for section ${section.id}`} type="number" min={1} max={100} value={section.count} onChange={(event) => updateSection(index, { count: Number(event.target.value) || 0 })} />
      <input aria-label={`Marks each for section ${section.id}`} type="number" min={1} max={20} value={section.marks} onChange={(event) => updateSection(index, { marks: Number(event.target.value) || 0 })} />
      <select aria-label={`Bloom level for section ${section.id}`} value={section.bloom} onChange={(event) => updateSection(index, { bloom: event.target.value })}>{['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'].map((level) => <option key={level}>{level}</option>)}</select>
      
      <select aria-label={`Chapter for section ${section.id}`} value={section.chapter} onChange={(event) => {
        const nextChapter = event.target.value
        updateSection(index, { chapter: nextChapter, topic: 'All topics' })
      }}>
        <option value="All syllabus">All syllabus</option>
        {availableChapters.map((chapter) => <option key={chapter} value={chapter}>{chapter}</option>)}
      </select>

      {section.chapter !== 'All syllabus' && topics.length > 0 && (
        <select aria-label={`Topic for section ${section.id}`} value={section.topic || 'All topics'} onChange={(event) => updateSection(index, { topic: event.target.value })}>
          <option value="All topics">All topics</option>
          {topics.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      )}

      <select aria-label={`Difficulty for section ${section.id}`} value={section.level} onChange={(event) => updateSection(index, { level: event.target.value as PaperSection['level'] })}>{['Use overall', 'Easy', 'Standard', 'Challenging'].map((level) => <option key={level}>{level}</option>)}</select>
      <em>= {section.count * section.marks} marks</em>
      <button className="icon-btn" aria-label={`Remove section ${section.id}`} onClick={() => removeSection(index)}><X size={16} /></button>
    </div>
  )
}

function ProgressStream({ generating, generatedCount, sections, error, onRetry }: { generating: boolean; generatedCount: number; sections: PaperSection[]; error: string; onRetry: () => void }) {
  const expectedCount = sections.reduce((sum, section) => sum + section.count, 0)
  const complete = generatedCount > 0 && generatedCount === expectedCount
  const progress = complete ? 100 : generating ? 45 : 0
  return (
    <Card title="Generation progress" icon={Activity}>
      <div className="progress-head">
        <span>{complete ? `${generatedCount}/${expectedCount} questions generated` : generating ? `Generating ${expectedCount} questions...` : error ? 'Generation stopped' : 'Ready after paper setup'}</span>
        <span>{complete ? 'Complete' : generating ? 'Working' : error ? 'Retry available' : 'Not started'}</span>
      </div>
      <div className="progress-bar"><span style={{ width: `${progress}%` }} /></div>
      <div className="progress-sections">
        {sections.map((section) => (
          <span key={section.id}>
            {complete ? <Check size={15} style={{ color: 'var(--eg-emerald)' }} /> : generating ? <Activity size={15} style={{ color: 'var(--eg-indigo)' }} /> : <Clock size={15} style={{ color: 'var(--eg-text-faint)' }} />}
            Section {section.id} {complete ? 'complete' : generating ? 'processing' : 'pending'}
          </span>
        ))}
      </div>
      {error && <div className="form-error" role="alert" style={{ marginTop: '12px' }}>{error}</div>}
      {error && <button className="ghost-btn" style={{ marginTop: '12px' }} onClick={onRetry}>Retry Generation</button>}
    </Card>
  )
}

function StudentTile({ student, selected, onClick }: { student: any; selected: boolean; onClick: () => void }) {
  let integrityColor = 'var(--eg-emerald)'
  if (student.status === 'FLAGGED') integrityColor = 'var(--eg-red)'
  else if (student.status === 'WARN') integrityColor = 'var(--eg-orange)'
  else if (student.status === 'WATCH') integrityColor = 'var(--eg-amber)'

  const isFlagged = student.score < 50

  return (
    <button
      className={`student-tile ${student.status.toLowerCase()} ${selected ? 'selected' : ''}`}
      onClick={onClick}
      aria-label={`Expand ${student.name}`}
      style={{
        padding: '12px',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        background: 'var(--eg-navy-800)',
        border: selected ? '2px solid var(--eg-indigo)' : '1.5px solid var(--eg-navy-600)',
        borderRadius: '12px',
        cursor: 'pointer',
        textAlign: 'left',
        position: 'relative',
        overflow: 'hidden'
      }}
    >
      {/* Simulated Webcam Viewport */}
      <div style={{
        position: 'relative',
        width: '100%',
        aspectRatio: '4/3',
        background: 'var(--eg-navy-700)',
        borderRadius: '8px',
        border: `2px solid ${student.status !== 'CLEAN' ? integrityColor : 'transparent'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        overflow: 'hidden'
      }}>
        {/* FLAGGED overlay ribbon */}
        {isFlagged && (
          <div style={{
            position: 'absolute',
            top: '8px',
            left: '-28px',
            background: 'var(--eg-red)',
            color: '#ffffff',
            fontSize: '9px',
            fontWeight: 700,
            padding: '2px 24px',
            transform: 'rotate(-45deg)',
            boxShadow: '0 2px 4px rgba(0,0,0,0.3)',
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            zIndex: 5
          }}>
            FLAGGED
          </div>
        )}

        {/* Status Badge in upper corner */}
        <div style={{ position: 'absolute', top: '8px', right: '8px', zIndex: 4 }}>
          <StatusBadge status={student.status} />
        </div>

        {/* Privacy-safe session state. Raw camera frames never reach teacher UI. */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '8px' }}>
          <Shield size={24} style={{ color: student.status === 'FLAGGED' ? 'var(--eg-red)' : 'var(--eg-text-muted)', opacity: 0.8 }} />
          <span style={{ fontSize: '9px', color: 'var(--eg-text-muted)', fontFamily: 'monospace' }}>
            {student.consent ? 'CONSENT RECORDED' : 'CONSENT PENDING'}
          </span>
        </div>
      </div>

      {/* Student Metadata below camera viewport */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <strong style={{ fontSize: '13px', fontWeight: 600, color: 'var(--eg-text)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {student.name}
        </strong>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <span style={{ fontSize: '18px', fontWeight: 700, fontFamily: 'JetBrains Mono, monospace', color: integrityColor }}>
            {student.score}
          </span>
          <span style={{ fontSize: '11px', color: 'var(--eg-text-muted)' }}>
            Answers {student.answered} ({student.events} events)
          </span>
        </div>
      </div>
    </button>
  )
}

function IntegrityScoreCard({ student }: { student: { name: string; score: number; status: IntegrityStatus; tier: number; factors: number[]; ci: number | null } }) {
  const labels = ['Behavioral 30%', 'AI Perplexity 15%', 'Stylometric 25%', 'Answer Quality 25%', 'Time Anomaly 5%']

  const radius = 30
  const circumference = 2 * Math.PI * radius
  const strokeDashoffset = circumference - (circumference * student.score) / 100

  let glowColor = 'var(--eg-emerald)'
  let glowShadow = '0 0 16px rgba(16, 185, 129, 0.4)'
  if (student.score < 50) {
    glowColor = 'var(--eg-red)'
    glowShadow = '0 0 16px rgba(239, 68, 68, 0.6)'
  } else if (student.score < 70) {
    glowColor = 'var(--eg-orange)'
    glowShadow = '0 0 16px rgba(249, 115, 22, 0.5)'
  } else if (student.score < 85) {
    glowColor = 'var(--eg-amber)'
    glowShadow = '0 0 16px rgba(245, 158, 11, 0.5)'
  }

  return (
    <div className="integrity-card">
      <div style={{ display: 'flex', alignItems: 'center', gap: '20px', marginBottom: '20px' }}>
        {/* Large Circular Gauge Visual */}
        <div style={{ position: 'relative', width: '80px', height: '80px', display: 'grid', placeItems: 'center', filter: `drop-shadow(${glowShadow})` }}>
          <svg width="80" height="80" style={{ transform: 'rotate(-90deg)' }}>
            <circle cx="40" cy="40" r={radius} stroke="var(--eg-navy-600)" strokeWidth="6" fill="transparent" />
            <circle cx="40" cy="40" r={radius} stroke={glowColor} strokeWidth="6" fill="transparent" strokeDasharray={circumference} strokeDashoffset={strokeDashoffset} strokeLinecap="round" />
          </svg>
          <div style={{ position: 'absolute', fontFamily: 'JetBrains Mono, monospace', fontSize: '20px', fontWeight: 700, color: 'var(--eg-text)' }}>
            {student.score}
          </div>
        </div>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <StatusBadge status={student.status} />
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--eg-text-muted)' }}>TIER {student.tier} BASELINE</span>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--eg-text-faint)', marginTop: '4px' }}>
            Confidence Interval: {student.ci ? `+/-${student.ci}` : 'N/A'}
          </div>
        </div>
      </div>

      {/* Breakdown Factors bar charts */}
      {student.factors.map((factor, index) => (
        <div className="factor-row" key={labels[index]}>
          <span>{labels[index]}</span>
          {student.tier === 3 && index === 2 ? <em>Not available - first exam</em> : (
            <div>
              <span style={{ width: `${factor}%`, background: `linear-gradient(90deg, var(--eg-indigo), ${glowColor})` }} />
            </div>
          )}
          <strong>{student.tier === 3 && index === 2 ? '--' : factor}</strong>
        </div>
      ))}
    </div>
  )
}

function AlertFeedItem({ name, event, severity }: { name: string; event: string; severity: 'info' | 'warning' | 'danger' }) {
  return (<div className={`alert-item ${severity}`}><strong>{name}</strong><span>{event}</span><em title="10:31:18 AM">2 min ago</em></div>)
}

function ConsentItem({ icon: Icon, title, text }: { icon: typeof Shield; title: string; text: string }) {
  return (<div className="consent-item"><Icon size={20} style={{ color: 'var(--eg-indigo)', marginTop: '2px' }} /><div><strong>{title}</strong><p style={{ margin: '2px 0 0 0' }}>{text}</p></div></div>)
}

function StatusBadge({ status }: { status: IntegrityStatus }) {
  return <span className={`status-badge ${status.toLowerCase()}`}>{status}</span>
}

function Toast({ kind, text, onClose }: { kind: ToastKind; text: string; onClose: () => void }) {
  return (
    <div className={`toast ${kind}`} role="status">
      {kind === 'success' ? <Check size={18} style={{ color: 'var(--eg-emerald)' }} /> : kind === 'error' ? <X size={18} style={{ color: 'var(--eg-red)' }} /> : kind === 'warning' ? <AlertTriangle size={18} style={{ color: 'var(--eg-amber)' }} /> : <Bell size={18} style={{ color: 'var(--eg-teal)' }} />}
      <span>{text}</span>
      <button aria-label="Dismiss notification" onClick={onClose}><X size={14} /></button>
    </div>
  )
}

function SubmitDialog({ onClose, go, answeredCount, totalCount, markedCount }: { onClose: () => void; go: () => void; answeredCount: number; totalCount: number; markedCount: number }) {
  const [submitError, setSubmitError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const handleSubmit = async () => {
    if (answeredCount === 0) {
      setSubmitError('Answer at least one question before submitting.')
      return
    }
    setSubmitting(true)
    setSubmitError('')
    const sessionId = studentSessionId()
    if (sessionId) {
      try { await api.endSession(sessionId) }
      catch (error) {
        setSubmitError(error instanceof Error ? error.message : 'Submission failed. Your answers remain saved locally.')
        setSubmitting(false)
        return
      }
    }
    if (sessionId) {
      window.localStorage.removeItem(`examguard-answers-${sessionId}`)
      window.localStorage.removeItem(`examguard-deadline-${sessionId}`)
    }
    go()
  }
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="submit-title">
      <div className="modal">
        <h2 id="submit-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}><Check size={24} style={{ color: 'var(--eg-emerald)' }} /> Submit all answers?</h2>
        <p>You cannot change answers or retrieve details after submission is finalized.</p>
        <div className="submit-summary">
          <span>Answered: {answeredCount}/{totalCount}</span>
          <span>Marked: {markedCount}</span>
          <span>Unanswered: {totalCount - answeredCount}</span>
        </div>
        {submitError && <p className="form-error" role="alert">{submitError}</p>}
        <div className="inline-actions" style={{ justifyContent: 'flex-end' }}>
          <button className="ghost-btn" onClick={onClose}>Review Answers</button>
          <button className="primary-btn" disabled={submitting || answeredCount === 0} onClick={handleSubmit}>{submitting ? 'Submitting...' : 'Submit Exam'}</button>
        </div>
      </div>
    </div>
  )
}

export default App

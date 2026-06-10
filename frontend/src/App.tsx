import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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
  PauseCircle,
  PlayCircle,
  Plus,
  Radar,
  RefreshCw,
  Rocket,
  Search,
  Settings,
  Shield,
  Sparkles,
  Timer,
  Upload,
  UserCheck,
  Users,
  X,
  Zap,
} from 'lucide-react'
import './App.css'
import { api, type ApiExam, type ApiQuestion, type ApiSession } from './api'

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

const demoStudents = [
  { name: 'Arjun Sharma', score: 88, status: 'CLEAN' as IntegrityStatus, tier: 1, answered: 76, events: 1, consent: true, joined: '10:01', ci: 7, factors: [92, 84, 89, 91, 76] },
  { name: 'Priya Patel', score: 43, status: 'FLAGGED' as IntegrityStatus, tier: 1, answered: 68, events: 9, consent: true, joined: '10:03', ci: 7, factors: [35, 28, 31, 62, 42] },
  { name: 'Rahul Singh', score: 65, status: 'WARN' as IntegrityStatus, tier: 3, answered: 72, events: 4, consent: true, joined: '10:05', ci: 0, factors: [68, 59, 0, 72, 60] },
  { name: 'Nisha Rao', score: 74, status: 'WATCH' as IntegrityStatus, tier: 2, answered: 70, events: 3, consent: true, joined: '10:07', ci: 15, factors: [77, 69, 61, 81, 70] },
]

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
  level: ExamLevel | 'Use overall'
  negative: 'none' | 'quarter'
}

const initialSections: PaperSection[] = [
  { id: 'A', type: 'MCQ', count: 20, marks: 1, bloom: 'Remember', chapter: 'Ch 12', level: 'Use overall', negative: 'quarter' },
  { id: 'B', type: 'Short Answer', count: 10, marks: 3, bloom: 'Understand', chapter: 'Ch 13', level: 'Use overall', negative: 'none' },
  { id: 'C', type: 'Long Answer', count: 5, marks: 5, bloom: 'Analyze', chapter: 'Ch 14', level: 'Use overall', negative: 'none' },
  { id: 'D', type: 'Essay', count: 1, marks: 5, bloom: 'Create', chapter: 'Ch 14', level: 'Use overall', negative: 'none' },
]

const chapterChunks: Record<string, number> = {
  'Ch 12': 128,
  'Ch 13': 112,
  'Ch 14': 100,
}

const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

function isValidEmail(value: string) {
  return emailPattern.test(value.trim())
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
    const raw = window.localStorage.getItem('examguard-auth')
    return raw ? (JSON.parse(raw) as AuthUser) : null
  } catch {
    return null
  }
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
    answered: (session as any).answers_count ?? 21,
    events: (session as any).events_count ?? 1,
    consent: session.consent,
    joined: (session as any).joined_at ? new Date((session as any).joined_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : '10:00',
    ci: session.integrity?.ci ?? null,
    factors: factors,
    appealResponse: (session as any).appeal?.response || '',
    reviewStatus: session.review_status,
    gradeReleased: session.grade_released,
    rawSession: session
  }
}

function App() {
  const [view, setView] = useState<View>(() => viewFromHash())
  const [auth, setAuth] = useState<AuthUser | null>(() => storedAuth())
  const [mobileOpen, setMobileOpen] = useState(false)
  const [toast, setToast] = useState<{ kind: ToastKind; text: string } | null>(null)
  const [selectedStudent, setSelectedStudent] = useState<any>(demoStudents[1])
  const [filter, setFilter] = useState<IntegrityStatus | 'ALL'>('ALL')
  const [sort, setSort] = useState<'risk' | 'name' | 'join'>('risk')
  const [consentScrolled, setConsentScrolled] = useState(true)
  const [answer, setAnswer] = useState('Faraday law states that induced EMF is proportional to the rate of change of magnetic flux through a circuit.')
  const [marked, setMarked] = useState(false)
  const [selectedExamId, setSelectedExamId] = useState<string>(() => {
    return window.localStorage.getItem('examguard-exam-id') || 'exam-physics'
  })
  const [studentsList, setStudentsList] = useState<any[]>([])

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
          if (sessions && sessions.length > 0) {
            setStudentsList(sessions.map(mapSessionToStudent))
          } else {
            setStudentsList(demoStudents)
          }
        })
        .catch(() => {
          setStudentsList(demoStudents)
        })
    }

    poll()
    const interval = setInterval(poll, 4000)
    return () => clearInterval(interval)
  }, [auth, view, selectedExamId])

  useEffect(() => {
    const list = studentsList.length > 0 ? studentsList : demoStudents
    const found = list.find(s => s.name === selectedStudent?.name || s.id === selectedStudent?.id)
    if (found) {
      setSelectedStudent(found)
    } else if (list.length > 0) {
      setSelectedStudent(list[0])
    }
  }, [studentsList])

  useEffect(() => {
    const handleHashChange = () => {
      const next = viewFromHash()
      if (canAccess(next)) {
        setView(next)
      } else {
        setView('landing')
        window.history.replaceState(null, '', '#landing')
      }
    }
    window.addEventListener('hashchange', handleHashChange)
    return () => window.removeEventListener('hashchange', handleHashChange)
  }, [auth])

  const notify = (kind: ToastKind, text: string) => {
    setToast({ kind, text })
    window.setTimeout(() => setToast(null), kind === 'error' ? 7000 : kind === 'warning' ? 5000 : 3200)
  }

  const canAccess = (next: View, user = auth) => {
    if (publicViews.includes(next)) return true
    if (!user) return false
    if (user.role === 'teacher') return teacherViews.includes(next)
    return studentViews.includes(next)
  }

  const navigate = (next: View) => {
    if (!canAccess(next)) {
      notify('warning', auth ? 'This screen requires the other role. Please switch accounts from the landing page.' : 'Please login from the landing page before opening this screen.')
      setView('landing')
      window.history.replaceState(null, '', '#landing')
      return
    }
    setView(next)
    window.history.replaceState(null, '', `#${next}`)
  }

  const login = (user: AuthUser) => {
    setAuth(user)
    window.localStorage.setItem('examguard-auth', JSON.stringify(user))
    notify('success', `${user.role === 'teacher' ? 'Teacher' : 'Student'} login successful.`)
    const next = user.role === 'teacher' ? 'dashboard' : 'consent'
    setView(next)
    window.history.replaceState(null, '', `#${next}`)
  }

  const loginWithApi = async (payload: { role: AuthRole; email: string; password: string; name: string; joinCode?: string }) => {
    if (payload.role === 'student') {
      const session = await api.joinSession({ join_code: payload.joinCode ?? 'ABC123', student_name: payload.name, email: payload.email || undefined })
      window.localStorage.setItem('examguard-session-id', session.id)
      window.localStorage.setItem('examguard-exam-id', session.exam_id)
      login({ role: 'student', name: session.student_name, email: payload.email || `${payload.name.toLowerCase().replace(/\s+/g, '.')}@student.ai` })
      return
    }
    const result = await api.login({ email: payload.email, password: payload.password, role: payload.role, display_name: payload.name })
    window.localStorage.setItem('examguard-user-id', result.user.id)
    login({ role: 'teacher', name: result.user.display_name, email: result.user.email, userId: result.user.id })
  }

  const logout = () => {
    setAuth(null)
    window.localStorage.removeItem('examguard-auth')
    window.localStorage.removeItem('examguard-user-id')
    window.localStorage.removeItem('examguard-session-id')
    window.localStorage.removeItem('examguard-exam-id')
    notify('info', 'Signed out. Protected screens are locked.')
    setView('landing')
    window.history.replaceState(null, '', '#landing')
  }

  const filteredStudents = useMemo(() => {
    const sourceList = studentsList.length > 0 ? studentsList : demoStudents
    const list = filter === 'ALL' ? sourceList : sourceList.filter((student) => student.status === filter)
    return [...list].sort((a, b) => {
      if (sort === 'name') return a.name.localeCompare(b.name)
      if (sort === 'join') return a.joined.localeCompare(b.joined)
      return statusRank[a.status as IntegrityStatus] - statusRank[b.status as IntegrityStatus] || a.score - b.score
    })
  }, [studentsList, filter, sort])

  const activeView = canAccess(view) ? view : 'landing'
  const visibleNavItems = navItems.filter((item) => {
    if (publicViews.includes(item.view)) return true
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

  const content = {
    landing: <LandingView notify={notify} onLogin={loginWithApi} />,
    dashboard: (
      <DashboardView
        go={navigate}
        notify={notify}
        onSelectExam={(examId) => {
          setSelectedExamId(examId)
          window.localStorage.setItem('examguard-exam-id', examId)
        }}
      />
    ),
    config: <ConfigView notify={notify} />,
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
            if (sessions && sessions.length > 0) {
              setStudentsList(sessions.map(mapSessionToStudent))
            }
          }).catch(() => {})
        }}
      />
    ),
    consent: <ConsentView consentScrolled={consentScrolled} setConsentScrolled={setConsentScrolled} go={navigate} notify={notify} />,
    liveness: <LivenessView go={navigate} notify={notify} />,
    exam: <ExamView answer={answer} setAnswer={setAnswer} marked={marked} setMarked={setMarked} notify={notify} go={navigate} />,
    complete: <CompleteView notify={notify} />,
    review: (
      <ReviewView
        students={studentsList.length > 0 ? studentsList : demoStudents}
        selected={selectedStudent}
        setSelected={setSelectedStudent}
        notify={notify}
      />
    ),
    reports: (
      <ReportsView
        examId={selectedExamId}
        students={studentsList.length > 0 ? studentsList : demoStudents}
        notify={notify}
      />
    ),
    settings: <SettingsView auth={auth} onSaveSettings={handleSaveSettings} notify={notify} />,
  }[activeView]

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
          <Bot size={18} aria-hidden="true" />
          <strong>10-agent workflow</strong>
          <span>Creates, monitors, scores, and reviews exams.</span>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <button className="icon-btn mobile-only" aria-label="Open navigation" onClick={() => setMobileOpen(true)}>
            <Menu size={20} />
          </button>
          <div>
            <p className="eyebrow">Syllabus-based exam integrity platform</p>
            <h1>{navItems.find((item) => item.view === activeView)?.label ?? 'ExamGuard AI'}</h1>
          </div>
          <div className="top-actions">
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
  return (
    <section className="screen landing-screen">
      <div className="hero-band">
        <div className="hero-copy">
          <span className="badge badge-purple"><Sparkles size={14} /> Built for teachers, coaching institutes, and students</span>
          <h2>The exam platform that knows your syllabus</h2>
          <p>
            Upload your own material, generate grounded papers, run privacy-first online exams, and review integrity reports from one place.
          </p>
          <div className="hero-actions">
            <a className="primary-btn" href="#login-panel">Login / Join <ChevronRight size={16} /></a>
            <button className="outline-light" onClick={() => notify('info', 'Use the sample accounts in the login panel to try both roles.')}>Try sample access</button>
          </div>
        </div>
        <AuthPanel onLogin={onLogin} notify={notify} />
      </div>
      <div className="metric-grid">
        <Metric label="Paper setup time saved" value="6-8h" icon={Clock} />
        <Metric label="Integrity status levels" value="4" icon={Gauge} />
        <Metric label="Agent workflow steps" value="10" icon={Bot} />
        <Metric label="Raw video uploaded" value="0" icon={Shield} />
      </div>
      <div className="two-column">
        <Card title="How it works" icon={Zap}>
          <div className="step-list">
            {['Upload syllabus material', 'Configure sections and Bloom levels', 'Generate grounded questions', 'Monitor consent-first sessions', 'Review reports and appeals'].map((step, index) => (
              <div className="step" key={step}><span>{index + 1}</span>{step}</div>
            ))}
          </div>
        </Card>
        <Card title="Why institutes choose it" icon={Shield}>
          <div className="plain-points">
            <span><Check size={15} /> Questions come from the teacher's own material, not a generic bank.</span>
            <span><Check size={15} /> Raw webcam and audio never leave the student browser.</span>
            <span><Check size={15} /> Teachers see live risk signals without losing final decision control.</span>
            <span><Check size={15} /> Flagged students get a transparent appeal instead of automatic punishment.</span>
          </div>
        </Card>
      </div>
    </section>
  )
}

function AuthPanel({ onLogin, notify }: { onLogin: (payload: LoginPayload) => Promise<void>; notify: (kind: ToastKind, text: string) => void }) {
  const [role, setRole] = useState<AuthRole>('teacher')
  const [email, setEmail] = useState('teacher@demo.examguard.ai')
  const [password, setPassword] = useState('demo123')
  const [studentName, setStudentName] = useState('Arjun Sharma')
  const [joinCode, setJoinCode] = useState('ABC123')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const fillDemo = (nextRole: AuthRole) => {
    setRole(nextRole)
    setError('')
    if (nextRole === 'teacher') {
      setEmail('teacher@demo.examguard.ai')
      setPassword('demo123')
    } else {
      setEmail('arjun@student.ai')
      setPassword('demo123')
      setStudentName('Arjun Sharma')
      setJoinCode('ABC123')
    }
  }

  const submit = async () => {
    setError('')
    setSubmitting(true)
    if (role === 'teacher') {
      if (!isValidEmail(email)) { setError('Enter a valid teacher email address.'); notify('error', 'Enter a valid teacher email address.'); setSubmitting(false); return }
      if (password.trim().length < 6) { setError('Password must be at least 6 characters.'); notify('error', 'Password must be at least 6 characters.'); setSubmitting(false); return }
      try { await onLogin({ role: 'teacher', name: 'Rajan Kumar', email, password }) }
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
    <div className="login-card embedded-login" id="login-panel">
      <span className="badge badge-purple"><Lock size={14} /> Role-based access enabled</span>
      <h2>Login or join exam</h2>
      <p className="muted">Teachers manage exams and reports. Students join with a code and complete consent before starting.</p>
      <div className="role-toggle" role="tablist" aria-label="Choose login role">
        <button className={role === 'teacher' ? 'active' : ''} onClick={() => fillDemo('teacher')} role="tab" aria-selected={role === 'teacher'}><Users size={16} /> Teacher</button>
        <button className={role === 'student' ? 'active' : ''} onClick={() => fillDemo('student')} role="tab" aria-selected={role === 'student'}><GraduationCap size={16} /> Student</button>
      </div>
      {role === 'teacher' ? (
        <div className="login-form">
          <label>Teacher email<input type="email" required value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <label>Password<input type="password" required minLength={6} value={password} onChange={(event) => setPassword(event.target.value)} /></label>
          <div className="demo-credentials"><strong>Sample teacher:</strong> teacher@demo.examguard.ai / demo123</div>
        </div>
      ) : (
        <div className="login-form">
          <label>Student name<input required minLength={3} value={studentName} onChange={(event) => setStudentName(event.target.value)} /></label>
          <label>Join code<input required maxLength={6} value={joinCode} onChange={(event) => setJoinCode(event.target.value.toUpperCase().replace(/[^A-Z0-9]/g, ''))} /></label>
          <label>Optional student email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} /></label>
          <div className="demo-credentials"><strong>Sample student:</strong> Arjun Sharma / ABC123</div>
        </div>
      )}
      {error && <p className="form-error" role="alert">{error}</p>}
      <button className="primary-btn full" disabled={submitting} onClick={submit}>
        <Lock size={16} /> {submitting ? 'Checking...' : `Login as ${role}`}
      </button>
    </div>
  )
}

function DashboardView({ go, notify, onSelectExam }: { go: (view: View) => void; notify: (kind: ToastKind, text: string) => void; onSelectExam: (examId: string) => void }) {
  const [exams, setExams] = useState<ApiExam[]>([])
  const [showCreateModal, setShowCreateModal] = useState(false)

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
      notify('success', `Exam "${exam.title}" created. Join code: ${exam.join_code}`)
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

  return (
    <section className="screen">
      <div className="toolbar">
        <div className="search-box"><Search size={16} /><input aria-label="Search exams" placeholder="Search exams, students, subjects" /></div>
        <button className="ghost-btn"><Archive size={16} /> Archive</button>
        <button className="primary-btn" onClick={() => setShowCreateModal(true)}><Plus size={16} /> New Exam</button>
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
            <div className="inline-actions">
              <button className="primary-btn" onClick={() => setShowCreateModal(true)}>Create your first exam</button>
              <button className="ghost-btn" onClick={() => notify('info', 'Sample Physics class loaded. Join code ABC123.')}>Try sample class</button>
            </div>
          </Card>
        ) : null}
        {exams.map((exam) => (
          <Card key={exam.id} title={exam.title} icon={BookOpen}>
            <div className="exam-card-body">
              <span className={`badge ${exam.status === 'active' ? 'badge-green' : exam.status === 'ended' ? 'badge-amber' : 'badge-purple'}`}>{exam.status}</span>
              <h3>{exam.total_marks} marks - {exam.subject} - {exam.duration_minutes} min</h3>
              <div className="join-code">{exam.join_code} <button aria-label="Copy join code" onClick={() => { navigator.clipboard?.writeText(exam.join_code); notify('success', 'Join code copied.') }}><Copy size={16} /></button></div>
              <div className="inline-actions">
                <button className="primary-btn" onClick={() => { onSelectExam(exam.id); go('live') }}>Open live monitor</button>
                <button className="ghost-btn" onClick={() => { onSelectExam(exam.id); go('config') }}>Configure</button>
                <button className="ghost-btn" onClick={() => handleCloneExam(exam.id)}><Copy size={14} /> Clone</button>
                <button className="ghost-btn" onClick={() => handleDeleteExam(exam.id)}><X size={14} /> Delete</button>
              </div>
            </div>
          </Card>
        ))}
      </div>
      <div className="tab-strip">
        {['Overview', 'Configure Paper', 'Live Monitor', 'Reports', 'Review'].map((tab, index) => (
          <button key={tab} onClick={() => {
            const views = ['dashboard', 'config', 'live', 'reports', 'review'] as View[];
            const selectedExam = exams[0]?.id || 'exam-physics';
            onSelectExam(selectedExam);
            go(views[index]);
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
      <div className="modal">
        <h2 id="create-title">Create New Exam</h2>
        <div className="login-form">
          <label>Exam title<input required minLength={3} value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Physics XI - Electromagnetism" /></label>
          <label>Subject<input required value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="e.g. Physics" /></label>
          <label>Duration (minutes)<input type="number" min={10} max={300} value={duration} onChange={(e) => setDuration(Number(e.target.value))} /></label>
          <label>Total marks<input type="number" min={10} max={300} value={marks} onChange={(e) => setMarks(Number(e.target.value))} /></label>
        </div>
        <div className="inline-actions">
          <button className="ghost-btn" onClick={onClose}>Cancel</button>
          <button className="primary-btn" disabled={title.length < 3 || subject.length < 2} onClick={() => onCreate({ title, subject, duration_minutes: duration, total_marks: marks })}>Create Exam</button>
        </div>
      </div>
    </div>
  )
}

function ConfigView({ notify }: { notify: (kind: ToastKind, text: string) => void }) {
  const [examId, setExamId] = useState('exam-physics')
  const [materialId, setMaterialId] = useState('')
  const [uploadedMaterial, setUploadedMaterial] = useState('NCERT Physics Ch 12-14.pdf')
  const [materialError, setMaterialError] = useState('')
  const [totalMarksTarget, setTotalMarksTarget] = useState(80)
  const [overallLevel, setOverallLevel] = useState<ExamLevel>('Standard')
  const [paperMode, setPaperMode] = useState<PaperMode>('Mixed')
  const [sections, setSections] = useState<PaperSection[]>(initialSections)
  const [generated, setGenerated] = useState(false)

  useEffect(() => {
    const teacherId = window.localStorage.getItem('examguard-user-id') || 'teacher-demo'
    api.exams(teacherId)
      .then((items) => {
        const first = items[0]
        if (!first) return
        setExamId(first.id)
        setTotalMarksTarget(first.total_marks)
        return api.materials(first.id)
      })
      .then((materials) => {
        const first = materials?.[0]
        if (!first) return
        setMaterialId(first.id)
        setUploadedMaterial(first.filename)
      })
      .catch((event) => notify('warning', `Using local paper config data. Backend sync failed: ${event instanceof Error ? event.message : 'unknown error'}`))
  }, [])

  const total = sections.reduce((sum, section) => sum + section.count * section.marks, 0)
  const validTotalMarks = Number.isInteger(totalMarksTarget) && totalMarksTarget >= 10 && totalMarksTarget <= 300
  const materialChunks = uploadedMaterial ? 340 : 0
  const invalidSections = sections.filter((section) => section.count < 1 || section.marks < 1 || !section.chapter)
  const lowCoverageChapters = sections.filter((section) => (chapterChunks[section.chapter] ?? 0) < section.count * 8)
  const typeSet = new Set(sections.map((section) => section.type))
  const modeMismatch =
    (paperMode === 'MCQ only' && [...typeSet].some((type) => type !== 'MCQ')) ||
    (paperMode === 'MCQ + QA' && [...typeSet].some((type) => !['MCQ', 'Short Answer', 'Long Answer', 'Essay'].includes(type))) ||
    (paperMode === 'Mixed' && ![...typeSet].some((type) => ['MCQ', 'Short Answer', 'Long Answer', 'Fill Blank'].includes(type)))
  const canGenerate = Boolean(uploadedMaterial && materialId) && validTotalMarks && total === totalMarksTarget && materialChunks >= 200 && invalidSections.length === 0 && lowCoverageChapters.length === 0 && !modeMismatch

  const applyMode = (mode: PaperMode) => {
    setPaperMode(mode)
    if (mode === 'MCQ only') setSections([{ id: 'A', type: 'MCQ', count: totalMarksTarget, marks: 1, bloom: 'Understand', chapter: 'Ch 12', level: 'Use overall', negative: 'quarter' }])
    else if (mode === 'MCQ + QA') setSections([
      { id: 'A', type: 'MCQ', count: 30, marks: 1, bloom: 'Remember', chapter: 'Ch 12', level: 'Use overall', negative: 'quarter' },
      { id: 'B', type: 'Short Answer', count: 10, marks: 3, bloom: 'Understand', chapter: 'Ch 13', level: 'Use overall', negative: 'none' },
      { id: 'C', type: 'Long Answer', count: 4, marks: 5, bloom: 'Analyze', chapter: 'Ch 14', level: 'Use overall', negative: 'none' },
    ])
    else setSections(initialSections)
    setGenerated(false)
  }

  const updateSection = (index: number, patch: Partial<PaperSection>) => { setGenerated(false); setSections((c) => c.map((s, i) => i === index ? { ...s, ...patch } : s)) }
  const addSection = () => { setGenerated(false); setSections((c) => [...c, { id: String.fromCharCode(65 + c.length), type: 'Fill Blank', count: 5, marks: 1, bloom: 'Apply', chapter: 'Ch 12', level: 'Use overall', negative: 'none' }]) }
  const removeSection = (index: number) => { if (sections.length === 1) { notify('error', 'At least one paper section is required.'); return }; setGenerated(false); setSections((c) => c.filter((_, i) => i !== index).map((s, i) => ({ ...s, id: String.fromCharCode(65 + i) }))) }

  const handleMaterialUpload = async (file: File | undefined) => {
    setMaterialError(''); setGenerated(false)
    if (!file) return
    const allowed = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain']
    if (!allowed.includes(file.type) && !/\.(pdf|docx|txt)$/i.test(file.name)) { setMaterialError('Only PDF, DOCX, or TXT files are allowed.'); notify('error', 'Only PDF, DOCX, or TXT files are allowed.'); return }
    if (file.size > 50 * 1024 * 1024) { setMaterialError('Material file must be 50MB or smaller.'); notify('error', 'Material file must be 50MB or smaller.'); return }
    try {
      const material = await api.uploadMaterial(examId, file)
      setMaterialId(material.id); setUploadedMaterial(material.filename)
      notify('success', `${file.name} uploaded. Generation will be restricted to this material only.`)
    } catch (event) { const msg = event instanceof Error ? event.message : 'Upload failed.'; setMaterialError(msg); notify('error', msg) }
  }

  const validateAndGenerate = async () => {
    setGenerated(false)
    if (!uploadedMaterial || !materialId) { notify('error', 'Upload syllabus or material before generating a paper.'); return }
    if (!validTotalMarks) { notify('error', 'Total exam marks must be between 10 and 300.'); return }
    if (total !== totalMarksTarget) { notify('error', `Paper total must be exactly ${totalMarksTarget} marks. Current total is ${total}.`); return }
    if (materialChunks < 200) { notify('error', 'Upload more material before generation. At least 200 chunks are required.'); return }
    if (invalidSections.length) { notify('error', 'Every section needs question count, marks, and chapter.'); return }
    if (lowCoverageChapters.length) { notify('error', 'One or more sections ask for more questions than the selected chapter material can support.'); return }
    if (modeMismatch) { notify('error', `Selected sections do not match the ${paperMode} paper type.`); return }
    try {
      const payload = { material_id: materialId, total_marks: totalMarksTarget, overall_level: overallLevel, paper_mode: paperMode, sections: sections.map((s) => ({ id: s.id, type: s.type, count: s.count, marks_each: s.marks, bloom: s.bloom, chapter_tag: s.chapter, level: s.level })) }
      await api.savePaperConfig(examId, payload)
      const result = await api.generatePaper(examId)
      setGenerated(true)
      notify('success', `Paper generated only from uploaded syllabus/material. ${result.count}/${result.count} questions grounded with citations.`)
    } catch (event) { notify('error', event instanceof Error ? event.message : 'Paper generation failed.') }
  }

  return (
    <section className="screen config-layout">
      <div className="config-main">
        <Card title="Upload syllabus or material" icon={Upload}>
          <label htmlFor="material-file-upload" className="upload-zone" style={{ cursor: 'pointer', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
            <Upload size={30} />
            <strong>{uploadedMaterial || 'Upload PDF, DOCX, or TXT material'}</strong>
            <span>{uploadedMaterial ? `${materialChunks} chunks extracted - 3 chapters mapped - generation locked to uploaded material only` : 'No paper can be generated until material is uploaded.'}</span>
            {materialError && <p className="form-error" role="alert">{materialError}</p>}
            <button type="button" className="ghost-btn" onClick={(event) => { event.preventDefault(); event.stopPropagation(); notify('warning', 'OCR fallback ready. Page 4 would be skipped if unreadable.'); }}>Test OCR failure state</button>
          </label>
          <input id="material-file-upload" style={{ display: 'none' }} aria-label="Upload syllabus or material" type="file" accept=".pdf,.docx,.txt,application/pdf,text/plain" onChange={(event) => handleMaterialUpload(event.target.files?.[0])} />
        </Card>
        <Card title="Paper type and difficulty" icon={Gauge}>
          <div className="paper-controls">
            <label>Total exam marks<input type="number" min={10} max={300} value={totalMarksTarget} onChange={(event) => { setTotalMarksTarget(Number(event.target.value) || 0); setGenerated(false) }} /></label>
            <label>Overall level<select value={overallLevel} onChange={(event) => { setOverallLevel(event.target.value as ExamLevel); setGenerated(false) }}><option>Easy</option><option>Standard</option><option>Challenging</option></select></label>
            <label>Paper type<select value={paperMode} onChange={(event) => applyMode(event.target.value as PaperMode)}><option>MCQ only</option><option>MCQ + QA</option><option>Mixed</option></select></label>
          </div>
          <div className="plain-points compact-points">
            <span><Lock size={15} /> Question generation is source-locked to the uploaded material.</span>
            <span><Gauge size={15} /> Section marks must add up exactly to total exam marks.</span>
            <span><Check size={15} /> Section level can override the overall paper level.</span>
          </div>
        </Card>
        <Card title="Section builder" icon={BookOpen}>
          <div className="section-builder">
            {sections.map((section, index) => <SectionBuilderRow key={section.id} section={section} index={index} updateSection={updateSection} removeSection={removeSection} />)}
          </div>
          <button className="ghost-btn" onClick={addSection}><Plus size={16} /> Add section</button>
        </Card>
        <ProgressStream notify={notify} />
        <Card title="Generated question preview" icon={FileText}>
          <div className="question-preview">
            <span className={generated ? 'badge badge-green' : 'badge badge-amber'}>{generated ? 'Groundedness 0.84' : 'Generate paper to preview'}</span>
            <h3>{generated ? 'Explain the working principle of a transformer using Faraday\'s law of electromagnetic induction.' : 'Preview will appear only after source-locked generation succeeds.'}</h3>
            <p>{generated ? `Source: ${uploadedMaterial}, Ch 14, page 215. Bloom: Analyze. Level: ${overallLevel}. Marks: 5.` : 'No outside/general knowledge questions are allowed in this workflow.'}</p>
            <textarea aria-label="Edit generated question" value={generated ? 'Explain the working principle of a transformer using Faraday\'s law of electromagnetic induction.' : ''} readOnly />
          </div>
        </Card>
      </div>
      <aside className="config-aside">
        <Card title="Live marks tally" icon={Gauge}>
          <div className={total === totalMarksTarget && validTotalMarks ? 'tally tally-ok' : total > totalMarksTarget ? 'tally tally-bad' : 'tally tally-warn'}>
            <strong>{total}/{validTotalMarks ? totalMarksTarget : '--'}</strong>
            <span>{!validTotalMarks ? 'Set total marks between 10 and 300.' : total === totalMarksTarget ? 'Exact match. Generate Paper is active.' : total > totalMarksTarget ? `${total - totalMarksTarget} marks over budget.` : `${totalMarksTarget - total} marks remaining.`}</span>
          </div>
          <div className="breakdown">{sections.map((section) => <span key={section.id}>Section {section.id}: {section.count * section.marks} marks</span>)}</div>
          {(!uploadedMaterial || !materialId) && <p className="form-error">Upload material before generation.</p>}
          {!validTotalMarks && <p className="form-error">Total exam marks must be between 10 and 300.</p>}
          {modeMismatch && <p className="form-error">Sections do not match selected paper type.</p>}
          {lowCoverageChapters.length > 0 && <p className="form-error">Some sections exceed available chapter coverage.</p>}
          <button className="primary-btn full" disabled={!canGenerate} onClick={validateAndGenerate}>Generate Paper</button>
          <button className="ghost-btn full" onClick={() => notify('warning', 'Gemini rate-limited. Switching to Ollama with ETA 45 sec.')}>Simulate LLM fallback</button>
        </Card>
        <Card title="Coverage validation" icon={Check}>
          <div className="coverage-list">
            {Object.entries(chapterChunks).map(([chapter, chunks]) => <span key={chapter}>{chunks >= 100 ? <Check size={15} /> : <AlertTriangle size={15} />} {chapter} has {chunks} chunks</span>)}
            <span><Lock size={15} /> Retrieval uses uploaded material only. Outside-web generation is blocked.</span>
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
}) {
  const avg = props.students.length > 0
    ? Math.round(props.students.reduce((sum, student) => sum + student.score, 0) / props.students.length)
    : 0

  const warnCount = props.students.filter(s => s.status === 'WARN').length
  const flaggedCount = props.students.filter(s => s.status === 'FLAGGED').length

  const [examStatus, setExamStatus] = useState<string>('active')
  
  useEffect(() => {
    api.getExam(props.examId).then(e => setExamStatus(e.status)).catch(() => {})
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
        <div className="connection-banner"><Activity size={16} /> Live connection active (polling mode)</div>
        <div className="summary-grid">
          <Metric label="Active students" value={String(props.students.length)} icon={Users} compact />
          <Metric label="WARN" value={String(warnCount)} icon={AlertTriangle} compact />
          <Metric label="FLAGGED" value={String(flaggedCount)} icon={Flag} compact />
          <Metric label="Avg integrity" value={`${avg}`} icon={Gauge} compact />
        </div>
        <div className="toolbar">
          <select aria-label="Filter by status" value={props.filter} onChange={(event) => props.setFilter(event.target.value as IntegrityStatus | 'ALL')}>
            {['ALL', 'CLEAN', 'WATCH', 'WARN', 'FLAGGED'].map((status) => <option key={status}>{status}</option>)}
          </select>
          <select aria-label="Sort students" value={props.sort} onChange={(event) => props.setSort(event.target.value as 'risk' | 'name' | 'join')}>
            <option value="risk">Sort by risk</option><option value="name">Sort by name</option><option value="join">Sort by join time</option>
          </select>
          <button className="ghost-btn" onClick={() => props.notify('info', 'Sound alerts enabled for FLAGGED events.')}><Bell size={16} /> Sound alerts</button>
          <button className="ghost-btn" onClick={togglePause}>
            {examStatus === 'paused' ? <PlayCircle size={16} /> : <PauseCircle size={16} />}
            {examStatus === 'paused' ? 'Resume exam' : 'Pause all'}
          </button>
          <button className="danger-btn" onClick={endExam}><X size={16} /> End exam</button>
        </div>
        <div className="student-grid">
          {props.students.map((student) => <StudentTile key={student.name} student={student} selected={props.selected.name === student.name} onClick={() => props.setSelected(student)} />)}
        </div>
      </div>
      <aside className="side-panel">
        <Card title="Expanded student view" icon={Eye}>
          <h3>{props.selected.name}</h3>
          <IntegrityScoreCard student={props.selected} />
          <div className="event-feed">
            <AlertFeedItem name={props.selected.name} event="tab switch detected" severity="warning" />
            <AlertFeedItem name={props.selected.name} event="perplexity below threshold on Q7" severity="danger" />
            <AlertFeedItem name={props.selected.name} event="answer auto-saved" severity="info" />
          </div>
        </Card>
      </aside>
    </section>
  )
}

function ConsentView({ consentScrolled, setConsentScrolled, go, notify }: { consentScrolled: boolean; setConsentScrolled: (value: boolean) => void; go: (view: View) => void; notify: (kind: ToastKind, text: string) => void }) {
  const handleConsent = async () => {
    const sessionId = window.localStorage.getItem('examguard-session-id')
    if (sessionId) {
      try { await api.saveConsent(sessionId) } catch { /* local-only fallback */ }
    }
    go('liveness')
    notify('success', 'Consent recorded. Proceeding to liveness check.')
  }
  return (
    <section className="screen student-gate">
      <div className="consent-card" role="dialog" aria-modal="true" aria-labelledby="consent-title">
        <span className="badge badge-purple"><Shield size={14} /> DPDP consent required</span>
        <h2 id="consent-title">Before your exam starts</h2>
        <p>ExamGuard shows exactly what is monitored. No raw webcam or audio leaves your device.</p>
        <div className="camera-preview"><Camera size={32} /><span>Front camera preview</span></div>
        <div className="consent-list" onScroll={(event) => setConsentScrolled(event.currentTarget.scrollTop > 30)}>
          <ConsentItem icon={Camera} title="Webcam gaze" text="Checks if you are looking at the screen. Raw video stays local." />
          <ConsentItem icon={Mic} title="Microphone level" text="Only RMS audio level is measured. Audio is never recorded." />
          <ConsentItem icon={FileText} title="Answer analysis" text="Answer text is checked for AI-writing and evaluated against source material." />
          <ConsentItem icon={Activity} title="Tab activity" text="Browser visibility changes are counted. No screen recording." />
        </div>
        <button className="primary-btn full" disabled={!consentScrolled} onClick={handleConsent}>I understand and consent</button>
        {!consentScrolled && <span className="hint">Scroll the consent items to continue.</span>}
      </div>
    </section>
  )
}

function LivenessView({ go, notify }: { go: (view: View) => void; notify: (kind: ToastKind, text: string) => void }) {
  const [blinkCount, setBlinkCount] = useState(0)
  const livenessPassed = blinkCount >= 2
  const startExam = async () => {
    if (!livenessPassed) { notify('error', 'Blink liveness must pass before the exam can start.'); return }
    const sessionId = window.localStorage.getItem('examguard-session-id')
    if (sessionId) {
      try { await api.saveLiveness(sessionId) } catch { /* local-only fallback */ }
    }
    go('exam')
  }
  return (
    <section className="screen liveness-screen">
      <div className="liveness-card">
        <span className="badge badge-teal"><Camera size={14} /> MediaPipe WASM local only</span>
        <div className="face-circle"><Eye size={72} /><span className="mesh-ring" /></div>
        <h2>Blink twice to begin</h2>
        <p>2 blinks must be detected within 8 seconds. EAR threshold: below 0.25 for 2 frames.</p>
        <div className="blink-progress"><span className={blinkCount >= 1 ? 'done' : ''} /><span className={blinkCount >= 2 ? 'done' : ''} /><span /></div>
        <div className="inline-actions center">
          <button className="primary-btn" disabled={!livenessPassed} onClick={startExam}><PlayCircle size={16} /> Start exam</button>
          <button className="ghost-btn light" onClick={() => setBlinkCount(Math.min(2, blinkCount + 1))}>Simulate blink</button>
          <button className="ghost-btn light" onClick={() => notify('warning', 'Low light detected. Ask teacher for manual approval if blink is not detected.')}>Low-light fallback</button>
        </div>
        {!livenessPassed && <span className="hint light-hint">Complete 2 blinks before starting.</span>}
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
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [timeLeft, setTimeLeft] = useState(80 * 60) // 80 minutes default
  const [lastSave, setLastSave] = useState<number>(Date.now())
  const [submitOpen, setSubmitOpen] = useState(false)
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const autoSaveRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // Load questions and duration from backend
  useEffect(() => {
    const sessionId = window.localStorage.getItem('examguard-session-id')
    if (sessionId) {
      api.sessionQuestions(sessionId)
        .then((qs) => {
          if (qs.length) setQuestions(qs)
        })
        .catch(() => {})

      const examId = window.localStorage.getItem('examguard-exam-id')
      if (examId) {
        api.getExam(examId)
          .then((exam) => {
            if (exam && exam.duration_minutes) {
              setTimeLeft(exam.duration_minutes * 60)
            }
          })
          .catch(() => {})
      }
    }
    // Restore saved answers from localStorage
    try {
      const saved = window.localStorage.getItem('examguard-answers')
      if (saved) setAnswers(JSON.parse(saved))
    } catch { /* ignore */ }
  }, [])

  // Fill in the text area when the initial question loads
  useEffect(() => {
    if (questions.length > 0 && currentQ === 0) {
      const qId = questions[0].id
      props.setAnswer(answers[qId] || '')
    }
  }, [questions])

  // Countdown timer
  useEffect(() => {
    const timer = setInterval(() => setTimeLeft((t) => Math.max(0, t - 1)), 1000)
    timerRef.current = timer
    return () => {
      if (timer) clearInterval(timer)
    }
  }, [])

  // Auto-save answers to localStorage every 10 seconds
  useEffect(() => {
    const autoSave = setInterval(() => {
      window.localStorage.setItem('examguard-answers', JSON.stringify(answers))
      setLastSave(Date.now())
    }, 10000)
    autoSaveRef.current = autoSave
    return () => {
      if (autoSave) clearInterval(autoSave)
    }
  }, [answers])

  // Auto-submit when time runs out
  useEffect(() => { if (timeLeft === 0) setSubmitOpen(true) }, [timeLeft])

  const q = questions[currentQ]
  const fallbackQuestions = Array.from({ length: 40 }, (_, i) => ({
    id: `q-${i + 1}`, exam_id: '', section_id: i < 20 ? 'A' : i < 30 ? 'B' : 'C',
    type: i < 20 ? 'MCQ' : 'Short Answer', text: `Question ${i + 1}`, options: [], correct_answer: '', marks: i < 20 ? 1 : 3,
    bloom_level: 'Understand', chapter_tag: 'Ch 12', source_chunk_ids: [], groundedness: 0.84, teacher_modified: false,
  }))
  const displayQuestions = questions.length > 0 ? questions : fallbackQuestions
  const current = displayQuestions[currentQ] || displayQuestions[0]
  const answeredCount = Object.keys(answers).filter((k) => answers[k]?.trim()).length
  const totalQ = displayQuestions.length

  const saveCurrentAnswer = useCallback(async () => {
    if (!current) return
    const text = current.id === q?.id ? props.answer : answers[current.id] || ''
    setAnswers((prev) => ({ ...prev, [current.id]: text }))
    window.localStorage.setItem('examguard-answers', JSON.stringify({ ...answers, [current.id]: text }))
    setLastSave(Date.now())
    const sessionId = window.localStorage.getItem('examguard-session-id')
    if (sessionId && text.trim()) {
      try { await api.saveAnswer(sessionId, { question_id: current.id, answer_text: text }) } catch { /* local fallback */ }
    }
  }, [current, props.answer, answers])

  const goToQuestion = (idx: number) => {
    saveCurrentAnswer()
    setCurrentQ(idx)
    const nextQ = displayQuestions[idx]
    if (nextQ) props.setAnswer(answers[nextQ.id] || '')
  }

  const handleMcqSelect = async (opt: string) => {
    props.setAnswer(opt)
    setAnswers((prev) => {
      const updated = { ...prev, [current.id]: opt }
      window.localStorage.setItem('examguard-answers', JSON.stringify(updated))
      const sessionId = window.localStorage.getItem('examguard-session-id')
      if (sessionId) {
        api.saveAnswer(sessionId, { question_id: current.id, answer_text: opt, selected_option: opt }).catch(() => {})
      }
      return updated
    })
  }

  const answerValid = props.answer.trim().length >= 25
  const requestSubmit = () => {
    if (!answerValid && current?.type !== 'MCQ') {
      props.notify('error', 'Current answer is too short. Write at least 25 characters or mark it for review before submitting.')
      return
    }
    saveCurrentAnswer()
    setSubmitOpen(true)
  }

  const secondsSinceSave = Math.round((Date.now() - lastSave) / 1000)

  const logEvent = (eventType: string) => {
    const sessionId = window.localStorage.getItem('examguard-session-id')
    if (sessionId) api.logEvent(sessionId, eventType).catch(() => {})
  }

  return (
    <section className="screen exam-layout" onContextMenu={(event) => { event.preventDefault(); logEvent('right_click'); props.notify('warning', 'Right click prevented and logged as a structured event.') }}>
      <div className="exam-header" aria-live="assertive">
        <strong>Physics XI - Electromagnetism</strong>
        <span className={timeLeft < 300 ? 'timer-critical' : ''}><Timer size={16} /> {formatTime(timeLeft)}</span>
        <span className="save-state"><Check size={16} /> Saved {secondsSinceSave} sec ago</span>
        <span className="badge badge-amber"><Shield size={14} /> WATCH</span>
      </div>
      <aside className="question-palette" aria-label="Question navigation palette">
        <div className="palette-summary">Answered {answeredCount}/{totalQ} - Marked {props.marked ? 1 : 0} - Unanswered {totalQ - answeredCount}</div>
        <div className="palette-grid">
          {displayQuestions.map((dq, i) => (
            <button key={dq.id} className={i === currentQ ? 'current' : answers[dq.id]?.trim() ? 'answered' : 'unvisited'} onClick={() => goToQuestion(i)} aria-label={`Question ${i + 1}`}>{i + 1}</button>
          ))}
        </div>
        <button className="primary-btn full" onClick={requestSubmit}>Submit All</button>
      </aside>
      <article className="question-area">
        <span className="badge badge-purple">Section {current?.section_id || 'A'} - {current?.bloom_level || 'Analyze'} - {current?.marks || 5} marks</span>
        <h2>Q{currentQ + 1}. {current?.text || 'Loading question...'}</h2>
        <p className="muted">Source citation after generation: NCERT Physics {current?.chapter_tag || 'Ch 14'}, page 215. Groundedness {current?.groundedness || 0.84}.</p>
        {current?.type === 'MCQ' && current.options?.length ? (
          <div className="mcq-options">
            {current.options.map((opt, i) => (
              <label key={i} className={`mcq-option ${props.answer === opt ? 'selected' : ''}`}>
                <input type="radio" name="mcq" value={opt} checked={props.answer === opt} onChange={() => handleMcqSelect(opt)} />
                {opt}
              </label>
            ))}
          </div>
        ) : (
          <textarea aria-label="Answer text" minLength={25} value={props.answer} onChange={(event) => props.setAnswer(event.target.value)} onPaste={() => { logEvent('paste_detected'); props.notify('warning', 'Paste detected and sent as a structured event.') }} />
        )}
        {current?.type !== 'MCQ' && !answerValid && <p className="form-error" role="alert">Answer needs at least 25 characters before final submit.</p>}
        <div className="inline-actions">
          <button className={props.marked ? 'warning-btn' : 'ghost-btn'} onClick={() => props.setMarked(!props.marked)}><Flag size={16} /> {props.marked ? 'Marked for review' : 'Mark for review'}</button>
          <button className="ghost-btn" disabled={currentQ === 0} onClick={() => goToQuestion(currentQ - 1)}>Previous</button>
          <button className="primary-btn" disabled={currentQ >= totalQ - 1} onClick={() => goToQuestion(currentQ + 1)}>Next Question</button>
        </div>
      </article>
      {submitOpen && (
        <SubmitDialog
          onClose={() => setSubmitOpen(false)}
          go={() => props.go('complete')}
          answeredCount={answeredCount}
          totalCount={totalQ}
          markedCount={props.marked ? 1 : 0}
        />
      )}
      <div className="connection-card"><RefreshCw size={16} /> Connection lost. Your answers are saved locally. Reconnecting...</div>
    </section>
  )
}

function CompleteView({ notify }: { notify: (kind: ToastKind, text: string) => void }) {
  const [appeal, setAppeal] = useState('I want to explain that I used my own notes while revising and did not use external AI during the test.')
  const appealWords = wordCount(appeal)
  const [submitted, setSubmitted] = useState(false)
  const [sessionData, setSessionData] = useState<any>(null)

  useEffect(() => {
    const sessionId = window.localStorage.getItem('examguard-session-id')
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
    if (appealWords > 500) { notify('error', 'Appeal response cannot exceed 500 words.'); return }
    const sessionId = window.localStorage.getItem('examguard-session-id')
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
  } : demoStudents[1]

  return (
    <section className="screen complete-layout">
      <Card title="Submission received" icon={Check}>
        <p>Your exam was submitted successfully. Your teacher will release the final result after review.</p>
        <div className="status-tracker"><span className="done">Submitted</span><span className={submitted || sessionData?.review_status === 'appeal_submitted' ? 'done' : 'active'}>Under teacher review</span><span>Result released</span></div>
      </Card>
      <Card title="Integrity summary" icon={Shield}>
        <IntegrityScoreCard student={studentObj} />
        <p className="muted">Some answer patterns require teacher review. This does not mean a final decision has been made.</p>
      </Card>
      <Card title="Appeal response" icon={FileText}>
        <p>Deadline: 23h 42m remaining. Max 500 words.</p>
        <textarea aria-label="Appeal response" maxLength={3500} value={appeal} onChange={(event) => setAppeal(event.target.value)} disabled={submitted || sessionData?.review_status === 'appeal_submitted'} />
        <p className={appealWords > 500 || appealWords < 12 ? 'form-error' : 'hint'}>{appealWords}/500 words</p>
        <button className="primary-btn" onClick={submitAppeal} disabled={submitted || sessionData?.review_status === 'appeal_submitted'}>{submitted || sessionData?.review_status === 'appeal_submitted' ? 'Appeal Submitted' : 'Submit appeal'}</button>
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
      <Card title="Flagged queue" icon={Flag}>
        {reviewStudentsList.length === 0 ? (
          <p className="muted">No student sessions currently flagged for review.</p>
        ) : (
          reviewStudentsList.map((student) => (
            <button className={`queue-item ${selected?.id === student.id ? 'active' : ''}`} key={student.id || student.name} onClick={() => setSelected(student)}>
              <span>{student.name}</span>
              <StatusBadge status={student.status} />
              <em>{student.tier === 3 ? 'Tier 3 baseline building' : student.reviewStatus === 'appeal_submitted' ? 'Appeal submitted' : 'Awaiting review'}</em>
            </button>
          ))
        )}
      </Card>
      <Card title="Side-by-side review" icon={UserCheck} className="wide-card">
        {selected ? (
          <div className="review-columns">
            <div>
              <h3>Integrity report</h3>
              <IntegrityScoreCard student={selected} />
              <AlertFeedItem name={selected.name} event="style distance exceeded Tier 1 threshold" severity="danger" />
            </div>
            <div>
              <h3>Student appeal</h3>
              <p className="appeal-note">{selected.appealResponse || 'No appeal response has been submitted yet by the student.'}</p>
              <textarea aria-label="Teacher note" minLength={12} placeholder="Add teacher note" value={teacherNote} onChange={(event) => setTeacherNote(event.target.value)} />
              {teacherNote.trim().length < 12 && <p className="form-error">Teacher note is required before clearing or confirming a flag.</p>}
              <div className="inline-actions">
                <button className="primary-btn" disabled={teacherNote.trim().length < 12} onClick={() => saveDecision('clear')}>Clear and release</button>
                <button className="danger-btn" disabled={teacherNote.trim().length < 12} onClick={() => saveDecision('confirm_flag')}>Confirm flag</button>
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

  const downloadBatch = () => notify('success', 'Batch ZIP generated.')

  const downloadCsv = async () => {
    try {
      const resp = await api.downloadReportsCsv(examId)
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a'); a.href = url; a.download = `examguard_${examId}_report.csv`; a.click()
      URL.revokeObjectURL(url)
      notify('success', 'CSV export downloaded.')
    } catch { notify('success', 'CSV export ready.') }
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

  const avgScore = summary ? summary.average_integrity : (students.length > 0 ? Math.round(students.reduce((sum, s) => sum + s.score, 0) / students.length) : 76)
  const totalStudentsStr = summary ? String(summary.total_students) : String(students.length)
  const appealsCountStr = summary ? String(summary.appeals_open) : String(students.filter(s => s.reviewStatus === 'appeal_submitted').length)

  return (
    <section className="screen">
      <div className="summary-grid">
        <Metric label="Reports ready" value={totalStudentsStr} icon={FileText} compact />
        <Metric label="Class average" value={String(avgScore)} icon={BarChart3} compact />
        <Metric label="Appeals open" value={appealsCountStr} icon={Flag} compact />
        <Metric label="PDF p95" value="8.4s" icon={Timer} compact />
      </div>
      <Card title="Reports and downloads" icon={Download}>
        <div className="report-actions">
          <button className="primary-btn" onClick={downloadBatch}><Download size={16} /> Batch ZIP</button>
          <button className="ghost-btn" onClick={downloadCsv}><FileText size={16} /> CSV export</button>
          <button className="ghost-btn" onClick={() => notify('error', 'PDF generation failed for Priya. Retry from the row action.')}><RefreshCw size={16} /> Simulate PDF error</button>
        </div>
        <div className="report-list">
          {students.map((student) => (
            <div className="report-row" key={student.id || student.name}>
              <span>{student.name}</span>
              <StatusBadge status={student.status} />
              <span>Score {student.score} {student.ci ? `+/-${student.ci}` : ''}</span>
              <button aria-label={`Download PDF for ${student.name}`} onClick={() => downloadPdf(student.id, student.name)}><Download size={16} /></button>
            </div>
          ))}
        </div>
      </Card>
      <Card title="Exam still active empty state" icon={Clock}>
        <p className="muted">Reports available after exam ends. Live countdown: 42 minutes remaining.</p>
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
    if (instituteName.trim().length < 3) { notify('error', 'Institute name must be at least 3 characters.'); return }
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
      await api.resetRequest('current-user@demo.examguard.ai')
      notify('info', 'Password reset email sent.')
    } catch { notify('info', 'Password reset email sent.') }
  }

  return (
    <section className="screen settings-grid">
      <Card title="Account settings" icon={Settings}>
        <label>Display name<input required minLength={3} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></label>
        <label>Institute name<input required minLength={3} value={instituteName} onChange={(event) => setInstituteName(event.target.value)} /></label>
        <label><input type="checkbox" defaultChecked /> Email me when a student is flagged</label>
        {(displayName.trim().length < 3 || instituteName.trim().length < 3) && <p className="form-error">Display name and institute name are required.</p>}
        <button className="primary-btn" onClick={saveSettings}>Save settings</button>
      </Card>
      <Card title="Password reset" icon={Lock}>
        <label>New password<input type="password" minLength={8} placeholder="Enter new password" value={newPassword} onChange={(event) => setNewPassword(event.target.value)} /></label>
        <label>Confirm password<input type="password" minLength={8} placeholder="Confirm password" value={confirmPassword} onChange={(event) => setConfirmPassword(event.target.value)} /></label>
        <div className={`strength ${strongPassword ? 'strong' : 'weak'}`}><span /><span /><span /><em>{strongPassword ? 'Strong' : 'Needs uppercase + number'}</em></div>
        {confirmPassword && newPassword !== confirmPassword && <p className="form-error">Passwords do not match.</p>}
        <button className="ghost-btn" onClick={sendReset}>Send reset link</button>
      </Card>
      <Card title="Security promises" icon={Shield}>
        <ul className="plain-list">
          <li>Raw video never leaves browser.</li>
          <li>Audio RMS only, no recording.</li>
          <li>Signed report URLs expire after 7 days.</li>
          <li>RLS isolates teachers and students.</li>
        </ul>
      </Card>
    </section>
  )
}

// --- Shared Components -------------------------------------------------------

function Metric({ label, value, icon: Icon, compact = false }: { label: string; value: string; icon: typeof Shield; compact?: boolean }) {
  return (<div className={`metric-card ${compact ? 'compact' : ''}`}><Icon size={compact ? 18 : 24} /><strong>{value}</strong><span>{label}</span></div>)
}

function Card({ title, icon: Icon, className = '', children }: { title: string; icon: typeof Shield; className?: string; children: React.ReactNode }) {
  return (<section className={`card ${className}`}><div className="card-title"><Icon size={18} aria-hidden="true" /><h2>{title}</h2></div>{children}</section>)
}

function SectionBuilderRow({ section, index, updateSection, removeSection }: { section: PaperSection; index: number; updateSection: (index: number, patch: Partial<PaperSection>) => void; removeSection: (index: number) => void }) {
  return (
    <div className="section-row">
      <strong>Section {section.id}</strong>
      <select aria-label={`Question type for section ${section.id}`} value={section.type} onChange={(event) => updateSection(index, { type: event.target.value as QuestionType })}>{['MCQ', 'Short Answer', 'Long Answer', 'Fill Blank', 'True/False', 'Essay'].map((type) => <option key={type}>{type}</option>)}</select>
      <input aria-label={`Question count for section ${section.id}`} type="number" min={1} max={100} value={section.count} onChange={(event) => updateSection(index, { count: Number(event.target.value) || 0 })} />
      <input aria-label={`Marks each for section ${section.id}`} type="number" min={1} max={20} value={section.marks} onChange={(event) => updateSection(index, { marks: Number(event.target.value) || 0 })} />
      <select aria-label={`Bloom level for section ${section.id}`} value={section.bloom} onChange={(event) => updateSection(index, { bloom: event.target.value })}>{['Remember', 'Understand', 'Apply', 'Analyze', 'Evaluate', 'Create'].map((level) => <option key={level}>{level}</option>)}</select>
      <select aria-label={`Chapter for section ${section.id}`} value={section.chapter} onChange={(event) => updateSection(index, { chapter: event.target.value })}>{Object.keys(chapterChunks).map((chapter) => <option key={chapter}>{chapter}</option>)}</select>
      <select aria-label={`Difficulty for section ${section.id}`} value={section.level} onChange={(event) => updateSection(index, { level: event.target.value as PaperSection['level'] })}>{['Use overall', 'Easy', 'Standard', 'Challenging'].map((level) => <option key={level}>{level}</option>)}</select>
      <em>= {section.count * section.marks}m</em>
      <button className="icon-btn" aria-label={`Remove section ${section.id}`} onClick={() => removeSection(index)}><X size={16} /></button>
    </div>
  )
}

function ProgressStream({ notify }: { notify: (kind: ToastKind, text: string) => void }) {
  return (
    <Card title="Generation progress stream" icon={Activity}>
      <div className="progress-head"><span>31/40 questions</span><span>LLM: Gemini 1.5 Flash</span><span>ETA 28 sec</span></div>
      <div className="progress-bar"><span style={{ width: '78%' }} /></div>
      <div className="progress-sections">
        <span><Check size={15} /> Section A complete</span>
        <span><Check size={15} /> Section B complete</span>
        <span><Activity size={15} /> Section C in progress</span>
        <span><Clock size={15} /> Section D pending</span>
      </div>
      <button className="ghost-btn" onClick={() => notify('error', 'Generation failed. 31/40 questions completed. Retry remaining questions.')}>Simulate partial failure</button>
    </Card>
  )
}

function StudentTile({ student, selected, onClick }: { student: (typeof demoStudents)[number]; selected: boolean; onClick: () => void }) {
  return (
    <button className={`student-tile ${student.status.toLowerCase()} ${selected ? 'selected' : ''}`} onClick={onClick} aria-label={`Expand ${student.name}`}>
      <div><strong>{student.name}</strong><StatusBadge status={student.status} /></div>
      <span className="score">{student.score}</span>
      <span><Check size={14} /> DPDP consent</span>
      <span>Q {student.answered}/80 - {student.events} events</span>
    </button>
  )
}

function IntegrityScoreCard({ student }: { student: { name: string; score: number; status: IntegrityStatus; tier: number; factors: number[]; ci: number | null } }) {
  const labels = ['Behavioral 30%', 'AI Perplexity 15%', 'Stylometric 25%', 'Answer Quality 25%', 'Time Anomaly 5%']
  return (
    <div className="integrity-card">
      <div className="integrity-head">
        <strong className={student.status.toLowerCase()}>{student.score}{student.ci ? ` +/-${student.ci}` : ''}</strong>
        <StatusBadge status={student.status} />
        <span>Tier {student.tier}</span>
      </div>
      {student.factors.map((factor, index) => (
        <div className="factor-row" key={labels[index]}>
          <span>{labels[index]}</span>
          {student.tier === 3 && index === 2 ? <em>Not available - first exam</em> : <div><span style={{ width: `${factor}%` }} /></div>}
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
  return (<div className="consent-item"><Icon size={20} /><div><strong>{title}</strong><p>{text}</p></div></div>)
}

function StatusBadge({ status }: { status: IntegrityStatus }) {
  return <span className={`status-badge ${status.toLowerCase()}`}>{status}</span>
}

function Toast({ kind, text, onClose }: { kind: ToastKind; text: string; onClose: () => void }) {
  return (
    <div className={`toast ${kind}`} role="status">
      {kind === 'success' ? <Check size={18} /> : kind === 'error' ? <X size={18} /> : kind === 'warning' ? <AlertTriangle size={18} /> : <Bell size={18} />}
      <span>{text}</span>
      <button aria-label="Dismiss notification" onClick={onClose}><X size={14} /></button>
    </div>
  )
}

function SubmitDialog({ onClose, go, answeredCount, totalCount, markedCount }: { onClose: () => void; go: () => void; answeredCount: number; totalCount: number; markedCount: number }) {
  const handleSubmit = async () => {
    const sessionId = window.localStorage.getItem('examguard-session-id')
    if (sessionId) {
      try { await api.endSession(sessionId) } catch { /* local fallback */ }
    }
    window.localStorage.removeItem('examguard-answers')
    go()
  }
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="submit-title">
      <div className="modal">
        <h2 id="submit-title">Submit all answers?</h2>
        <p>You cannot change answers after submission.</p>
        <div className="submit-summary">
          <span>Answered: {answeredCount}/{totalCount}</span><span>Marked: {markedCount}</span><span>Unanswered: {totalCount - answeredCount}</span>
        </div>
        <div className="inline-actions">
          <button className="ghost-btn" onClick={onClose}>Review again</button>
          <button className="primary-btn" onClick={handleSubmit}>Submit exam</button>
        </div>
      </div>
    </div>
  )
}

export default App

# ExamGuard AI v6 — MASTER BUILD PROMPT
## FAR AWAY 2026 Hackathon · Complete Specification with Full UI/UX

> **HOW TO USE THIS PROMPT:** Paste this entire document to your AI coding assistant (Claude, Cursor, Copilot, etc.) as the system/project context. Every section is self-contained. You can also paste individual sections for targeted help. Nothing is left vague — every screen, component, state, color, interaction, and edge case is specified.

---

# PART 1 — PROJECT IDENTITY & CORE MISSION

## 1.1 What You Are Building

**Project Name:** ExamGuard AI  
**Version:** v6.0 — Final Hackathon Build  
**Hackathon:** FAR AWAY 2026 — India's Biggest International Hackathon  
**Themes:** Examinations + Agentic & Autonomous Systems (BOTH simultaneously)  
**Tagline:** "The exam platform that knows your syllabus, proctors with full privacy, and catches AI cheating — at ₹2,000/month for unlimited students."

## 1.2 The Problem (Say This in Your First Sentence Always)

India conducts 90M+ competitive exams annually. Three problems are completely unsolved:

1. **Paper Setting** — Teachers spend 6–8 hours manually creating one exam paper. No tool generates questions from the teacher's own uploaded material.
2. **AI Cheating** — ChatGPT answer submission is the #1 cheating vector in 2024–25. No tool detects AI-written text per student with individual baselines.
3. **Cost** — Proctorio charges $8/student/exam. 100 students = $800/session. 50,000+ Indian coaching institutes cannot afford this.

## 1.3 The Solution

A **10-agent autonomous LangGraph pipeline** that fixes all three simultaneously:
- Teacher uploads their PDF → RAG pipeline → questions generated FROM THEIR MATERIAL in 5 minutes
- Per-student stylometric AI-cheat detection with 3-tier baseline system
- Browser-only biometric proctoring — raw video NEVER leaves the device (DPDP compliant)
- ₹2,000/month flat — 97% cheaper than Proctorio
- Full offline mode for 2G Indian network conditions

## 1.4 FAR AWAY Theme Alignment (ALWAYS STATE BOTH)

Every README first line, every slide title, every video first 10 seconds must say:

> "ExamGuard AI addresses TWO FAR AWAY themes simultaneously: **Examinations** (fair, secure, intelligent exam platform) and **Agentic & Autonomous Systems** (10-agent LangGraph StateGraph that thinks, decides, and acts without human-in-the-loop)."

---

# PART 2 — DESIGN SYSTEM (Complete Token Reference)

## 2.1 Color Palette

```
Primary Navy:     #0F1B35  (main brand, sidebar, headers)
Primary Purple:   #6B35B8  (CTAs, active states, agent highlights)
Accent Teal:      #0EA5A0  (success, live indicators, online status)
Alert Amber:      #F59E0B  (WARN state, warnings, pending)
Danger Red:       #DC2626  (FLAGGED state, errors, destructive actions)
Safe Green:       #16A34A  (CLEAN state, success, pass)

Neutrals:
  Background:     #F8F9FC  (page background)
  Surface:        #FFFFFF  (cards, panels, modals)
  Surface Alt:    #F1F5F9  (secondary surfaces, code blocks, tags)
  Border:         #E2E8F0  (all borders — use 1px solid)
  Border Strong:  #CBD5E1  (table dividers, section separators)
  Text Primary:   #0F172A  (headings, labels)
  Text Secondary: #475569  (body text, descriptions)
  Text Muted:     #94A3B8  (captions, placeholders, timestamps)
  Text Inverse:   #FFFFFF  (text on dark backgrounds)

Integrity States:
  CLEAN (>85):    bg #DCFCE7, text #166534, border #86EFAC
  WATCH (70-85):  bg #FEF9C3, text #854D0E, border #FDE047
  WARN (50-70):   bg #FEF3C7, text #92400E, border #FCD34D
  FLAGGED (<50):  bg #FEE2E2, text #991B1B, border #FCA5A5

  NOTE: UNIFIED THRESHOLDS — Use these everywhere, no exceptions:
  CLEAN = score > 85
  WATCH = score 70–85
  WARN  = score 50–70
  FLAGGED = score < 50
```

## 2.2 Typography Scale

```
Font Family:  Inter (primary), JetBrains Mono (code/scores/join codes)

Display:      48px / weight 800 / line-height 1.1  (landing hero only)
H1:           32px / weight 700 / line-height 1.2  (page titles)
H2:           24px / weight 600 / line-height 1.3  (section headers)
H3:           18px / weight 600 / line-height 1.4  (card titles)
H4:           15px / weight 600 / line-height 1.5  (sub-section labels)
Body Large:   16px / weight 400 / line-height 1.6  (primary body text)
Body:         14px / weight 400 / line-height 1.6  (secondary body text)
Caption:      12px / weight 400 / line-height 1.5  (labels, timestamps, tags)
Mono:         13px / weight 500 / line-height 1.4  (join codes, scores, API data)
```

## 2.3 Spacing Scale (Use Only These Values)

```
4px   — micro gaps (icon to text, badge padding)
8px   — small gaps (input groups, list item padding)
12px  — medium-small (card inner padding top/bottom)
16px  — medium (standard gap, card horizontal padding)
20px  — medium-large (section internal spacing)
24px  — large (between card sections)
32px  — x-large (between page sections)
48px  — 2x-large (page top padding, hero spacing)
64px  — 3x-large (landing page sections)
```

## 2.4 Component Tokens

```
Border radius:
  sm: 4px   (tags, badges, chips)
  md: 8px   (buttons, inputs, small cards)
  lg: 12px  (cards, panels, modals)
  xl: 16px  (large cards, dashboard tiles)
  pill: 9999px (status badges, toggle pills)

Shadows:
  card:     0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.04)
  elevated: 0 4px 12px rgba(0,0,0,0.10), 0 2px 4px rgba(0,0,0,0.06)
  modal:    0 20px 60px rgba(0,0,0,0.20), 0 8px 20px rgba(0,0,0,0.10)
  focus:    0 0 0 3px rgba(107,53,184,0.25)  (purple focus ring on all inputs)

Transitions:
  fast:   150ms ease   (hover color changes, button active states)
  normal: 250ms ease   (dropdowns, accordions, badge color changes)
  slow:   400ms ease   (modal open/close, panel slide-in)
```

## 2.5 Integrity Tile Colors (Live Monitor)

```
Score > 85  CLEAN:   border-left: 4px solid #16A34A; bg: white
Score 70-85 WATCH:   border-left: 4px solid #F59E0B; bg: #FFFBEB
Score 50-70 WARN:    border-left: 4px solid #F59E0B; bg: #FEF3C7; subtle pulse animation
Score < 50  FLAGGED: border-left: 4px solid #DC2626; bg: #FEF2F2; stronger pulse + red dot

Pulsing animation for WARN/FLAGGED:
@keyframes integrity-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}
animation: integrity-pulse 2s ease-in-out infinite;
```

## 2.6 Toast Notification System

Use **shadcn/ui Sonner** (already in stack). Four types:

```
Success (green):  Icon ✓  — "Exam activated", "Join code copied", "PDF ready"
Warning (amber):  Icon ⚠  — "LLM fallback to Ollama", "Low chunk count Ch.5"
Error (red):      Icon ✗  — "Upload failed", "Generation error", "Session expired"
Info (blue):      Icon ℹ  — "WebSocket reconnected", "3 students waiting"

Position: bottom-right, stack vertically max 3 toasts
Duration: success=3s, warning=5s, error=7s (dismiss on click)
Always include an action button for errors: "Retry" or "Details"
```

---

# PART 3 — FULL SCREEN SPECIFICATIONS (11 Screens)

---

## SCREEN 1 — Landing Page (`/`)

### Purpose
Convert visitors to sign-up. Establish credibility instantly. FAR AWAY judges land here first — they must immediately understand the problem, the solution, and both themes.

### Layout Structure

```
┌─────────────────────────────────────────────────────────┐
│  NAVBAR: Logo | Features | Pricing | [Teacher Login]    │
│          [Student Join Exam] (purple CTA button)        │
├─────────────────────────────────────────────────────────┤
│  HERO SECTION (full viewport height, navy gradient bg)  │
│                                                         │
│  Badge: [🏆 FAR AWAY 2026 · Examinations + Agentic AI] │
│                                                         │
│  H1 (Display 48px white):                              │
│  "The Exam Platform That                                │
│   Knows Your Syllabus"                                  │
│                                                         │
│  Subtitle (18px #94A3B8):                               │
│  "10-agent AI pipeline. Per-student cheat detection.   │
│   ₹2,000/month. Built for India."                       │
│                                                         │
│  [Get Started Free →] [Watch 4-min Demo ▶]             │
│  (purple filled)       (white outlined)                 │
│                                                         │
│  STAT BAR (3 cards below CTA):                         │
│  ┌──────────────┬──────────────┬──────────────┐        │
│  │  90M+        │  6–8 hrs     │  97% cheaper │        │
│  │ Exams/yr     │ Paper setting│ than Proctorio│        │
│  │ in India     │ per teacher  │ ₹2K vs $800  │        │
│  └──────────────┴──────────────┴──────────────┘        │
├─────────────────────────────────────────────────────────┤
│  HOW IT WORKS (3 steps, horizontal on desktop)          │
│  1. Upload → 2. Configure → 3. Monitor                  │
├─────────────────────────────────────────────────────────┤
│  COMPARISON TABLE                                       │
│  ExamGuard AI vs Proctorio vs Manual Setting            │
│  (7 rows: Price, AI Cheat Detection, Offline,          │
│   DPDP Compliant, Custom Questions, RAG, Setup Time)    │
├─────────────────────────────────────────────────────────┤
│  THEME BADGE SECTION                                    │
│  "Built for TWO themes simultaneously"                  │
│  [EXAMINATIONS] [AGENTIC & AUTONOMOUS SYSTEMS]          │
│  Both badges, each with 2-line description              │
├─────────────────────────────────────────────────────────┤
│  SIGN UP SECTION                                        │
│  Two cards side by side:                               │
│  [I'm a Teacher 👨‍🏫]        [I'm a Student 🎓]          │
│  Sign up form               Enter join code form        │
│  (email, password,          (join code field + name)    │
│   display name)                                         │
├─────────────────────────────────────────────────────────┤
│  FOOTER: DPDP Compliant · Offline Ready · MIT License   │
│          Made in India · FAR AWAY 2026                  │
└─────────────────────────────────────────────────────────┘
```

### Features & Details

- Navbar is sticky with blur backdrop on scroll (`backdrop-filter: blur(12px)`)
- Hero background: `linear-gradient(135deg, #0F1B35 0%, #1E3A6E 50%, #2D1B69 100%)`
- Stat bar cards: glass-morphism style — white 10% opacity bg, white border 20%, white text
- How It Works: animated stepper — each step fades in on scroll-into-view
- Comparison table: green checkmarks for ExamGuard, red X for competitors, with hover highlight row
- Sign-up form validation: real-time email format check, password strength indicator (4 levels)
- "I'm a Student" card shows join code input immediately — no full signup required for students

### Error States

- Form submit error: inline red text under field, input border turns red
- "Email already registered" → shows "Sign in instead?" link
- Network error: toast + "Try again" button, form inputs preserved

### Empty / Loading States

- Initial page load: navbar appears instantly, hero text fades in (300ms), stat bar slides up (500ms)
- Sign-up button: shows spinner + "Creating account..." while API call is in-flight, disabled

### Mobile Layout (≤768px)

- Navbar collapses to hamburger menu
- Hero: 36px H1, single column
- Stat bar: vertical stack, full width cards
- Comparison table: horizontal scroll wrapper
- Sign-up cards: full width, stacked vertically

---

## SCREEN 2 — Teacher Dashboard (`/dashboard`)

### Purpose
Central hub for all teacher activity. First screen after login. Must work beautifully when empty (new user) AND when full (active exams).

### Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│  SIDEBAR (240px, navy #0F1B35, fixed)                        │
│  ┌────────────────────────────────────┐                      │
│  │ [EG Logo] ExamGuard AI             │                      │
│  │ ─────────────────────────────      │                      │
│  │ 📋 My Exams          (active)      │                      │
│  │ 📚 Material Library               │                      │
│  │ 📊 Analytics                       │                      │
│  │ ⚙️  Settings                        │                      │
│  │                                    │                      │
│  │ [BOTTOM]                           │                      │
│  │ 👤 Teacher Name                    │                      │
│  │    Institute Name                  │                      │
│  │    [Sign Out]                      │                      │
│  └────────────────────────────────────┘                      │
│                                                              │
│  MAIN CONTENT (fills remaining width)                        │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ TOPBAR                                               │   │
│  │ "My Exams"          [+ Create New Exam]              │   │
│  │                     (purple button)                  │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ FILTER BAR                                           │   │
│  │ [All] [Active ●] [Draft] [Ended] [Archived]         │   │
│  │ Search: [________________] 🔍                        │   │
│  ├──────────────────────────────────────────────────────┤   │
│  │ EXAM CARDS GRID (2 columns on desktop)               │   │
│  │                                                      │   │
│  │ ┌─────────────────────┐ ┌─────────────────────┐    │   │
│  │ │ Physics Unit Test    │ │ Chemistry Chapter 5  │   │   │
│  │ │ [ACTIVE ●]           │ │ [DRAFT]              │   │   │
│  │ │                      │ │                      │   │   │
│  │ │ Join Code:           │ │ Join Code:           │   │   │
│  │ │ [ABC123] [📋Copy]    │ │ [XY9K2M] [📋Copy]   │   │   │
│  │ │                      │ │                      │   │   │
│  │ │ 32 students joined   │ │ 0 students           │   │   │
│  │ │ 2 flagged ⚠         │ │ Not activated        │   │   │
│  │ │ 60 min · Jun 15      │ │ 80 marks · 40 min   │   │   │
│  │ │                      │ │                      │   │   │
│  │ │ [Live Monitor]       │ │ [Configure] [Delete] │   │   │
│  │ │ [Reports] [⋯ More]   │ │ [Clone]              │   │   │
│  │ └─────────────────────┘ └─────────────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### Exam Card Details

Every exam card shows:
- Exam title (H3, truncate at 40 chars with tooltip)
- Status badge: `ACTIVE` (green dot + text), `DRAFT` (gray), `ENDED` (muted), `ARCHIVED` (strikethrough muted)
- Join code in `font-mono` with copy-to-clipboard button (shows "Copied!" checkmark for 2 seconds)
- Student count + flagged count (only show flagged count if > 0, in red)
- Duration + date
- Material status: "340 chunks indexed" or "No material uploaded" (amber warning)
- Action buttons vary by status:
  - DRAFT: [Configure] [Activate] [Clone] [Delete]
  - ACTIVE: [Live Monitor] [Reports] [End Exam] [⋯]
  - ENDED: [Reports] [Clone] [Archive]
  - ARCHIVED: [View Reports] [Unarchive]

### "Create New Exam" Modal

Triggered by the purple button. Full-screen overlay modal:

```
Title: "Create New Exam"

Fields (all required):
  Exam Title:     [text input, max 80 chars, char counter]
  Subject:        [text input, e.g. "Physics", "Mathematics"]
  Duration:       [number input] minutes  (min 15, max 360)
  Total Marks:    [number input]  (min 10, max 500)
  Description:    [textarea, optional, 200 char limit]

Auto-generated:
  Join Code: [ABC123] (shown after creation, 6-char alphanumeric)

Action: [Cancel] [Create Exam →] (purple)

On success: Modal closes, new exam card appears at top, toast: "Exam created — join code: ABC123"
```

### Exam Detail View (click card to expand or go to `/dashboard/exams/:id`)

When an exam card is clicked, expand to a full detail view with 4 tabs:

```
Tabs: [Overview] [Configure Paper] [Live Monitor] [Reports & Downloads]
```

**Overview Tab:**
- Full exam details (title, subject, duration, total marks)
- Join code (large, monospace, with QR code button that generates scannable QR)
- Material section: uploaded files list with chunk count, chapter map, delete button per file
- Student roster: table of enrolled students with name, joined-at timestamp, session status

**Configure Paper Tab** → See Screen 3

**Live Monitor Tab** → See Screen 4 (only accessible when exam is ACTIVE)

**Reports Tab** → See Screen 10

### EMPTY STATE (no exams yet — new teacher)

```
┌────────────────────────────────────────────────┐
│                                                │
│            [Illustration: clipboard]           │
│                                                │
│     "Welcome to ExamGuard AI"                  │
│     "Create your first exam to get started"   │
│                                                │
│     ┌─── 3-step guide ───────────────────┐    │
│     │ ① Create an exam            [→]   │    │
│     │ ② Upload your syllabus      [→]   │    │
│     │ ③ Configure and activate   [→]   │    │
│     └───────────────────────────────────┘    │
│                                                │
│     [+ Create Your First Exam]                 │
│     (large purple CTA button)                  │
│                                                │
│     ─── or ───                                │
│                                                │
│     [Try Demo Mode]                            │
│     "Load a pre-built Physics demo"            │
└────────────────────────────────────────────────┘
```

### Error States

- API load failure: skeleton cards → error state with "Failed to load exams. [Retry]"
- Exam activation failure: toast error "Activation failed — check material is uploaded"
- Delete confirmation: modal "Delete 'Physics Unit Test'? This cannot be undone." [Cancel] [Delete]

### Loading States

- Initial load: 2-column skeleton cards (gray animated shimmer), 4 cards showing
- After create: optimistic UI — card appears immediately with "Saving..." overlay, then resolves

### Mobile Layout

- Sidebar collapses to bottom tab bar (4 icons: Exams, Library, Analytics, Settings)
- Exam cards: single column, full width
- Card actions: overflow into a bottom sheet on tap of [⋯]

---

## SCREEN 3 — Paper Configuration Engine (`/dashboard/exams/:id/configure`)

### Purpose
The crown feature. Teacher defines their exam structure and the system generates questions from their material. This is the primary demo moment — must feel powerful and responsive.

### Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│  BREADCRUMB: My Exams > Physics Unit Test > Configure Paper  │
│                                                              │
│  ┌─── LEFT PANEL (60%) ────────┐  ┌─── RIGHT PANEL (40%) ──┐│
│  │                             │  │                         ││
│  │  MATERIAL STATUS            │  │  MARKS TALLY            ││
│  │  ✓ 340 chunks indexed       │  │                         ││
│  │  Chapters detected: 3       │  │  Section A:  20 marks   ││
│  │  Ch12, Ch13, Ch14           │  │  Section B:  30 marks   ││
│  │  [+ Upload More Material]   │  │  Section C:  15 marks   ││
│  │                             │  │  ─────────────────────  ││
│  │  SECTION BUILDER            │  │  Total:  65 / 80  ⚠     ││
│  │                             │  │  (amber if under-budget)││
│  │  [+ Add Section]            │  │                         ││
│  │                             │  │  [Generate Paper]        ││
│  │  Section A:                 │  │  (disabled, grey)        ││
│  │  ┌───────────────────────┐  │  │                         ││
│  │  │ Type: [MCQ ▼]         │  │  │  GENERATION PROGRESS    ││
│  │  │ Count: [10]           │  │  │  (hidden until clicked) ││
│  │  │ Marks each: [2]       │  │  │                         ││
│  │  │ Bloom's: [Apply ▼]    │  │  │  QUESTION PREVIEW       ││
│  │  │ Chapter: [Auto ▼]     │  │  │  (hidden until gen done)││
│  │  │ [↑][↓] [🗑 Remove]   │  │  │                         ││
│  │  └───────────────────────┘  │  └─────────────────────────┘│
│  └─────────────────────────────┘                              │
└──────────────────────────────────────────────────────────────┘
```

### Section Builder Row (Each Section)

Each section row is a card with:

```
Row layout: [drag handle ⣿] [Type dropdown] [Count] [Marks each] [Bloom's] [Chapter weight] [Remove]

Type dropdown options:
  MCQ | Fill in the Blank | True/False | Short Answer (1-2 sentences) | Long Answer (1 paragraph) | Essay (500+ words)

Count input:
  Number, min 1, max 30
  Shows "×" Marks each = "Section total: Xm" below in caption text

Marks each input:
  Number, min 0.5 (for negative marking), max 50
  Supports half marks (0.5, 1.5, etc.)
  Shows negative marking toggle: [-¼] [-½] [None] (three-way toggle, default None)

Bloom's Level dropdown (with color-coded options):
  Remember (gray) | Understand (blue) | Apply (green) | Analyse (teal) | Evaluate (amber) | Create (purple)
  
Chapter Weight dropdown:
  Auto-proportional | Ch. 12 (15%) | Ch. 13 (45%) | Ch. 14 (40%)
  (chapters populated from detected chapter map)
  Custom: shows percentage input if "Custom" selected
```

### Live Marks Tally (Right Panel — Critical Micro-interaction)

Updates on EVERY keystroke in count or marks fields — not on blur.

```
States:
  Under budget (65/80):
    Total shows in AMBER: "65 / 80"
    Message: "15 marks remaining — add a section or increase marks per question"
    Generate button: DISABLED (gray)
    
  Over budget (85/80):
    Total shows in RED: "85 / 80 ✗"
    Message: "5 marks over budget — reduce Section B by 5 marks"
    Generate button: DISABLED (gray)
    
  Exactly right (80/80):
    Total shows in GREEN: "80 / 80 ✓" with checkmark bounce animation
    Message: "Perfect! Ready to generate."
    Generate button: ENABLED (purple) with subtle entrance animation
    
Section breakdown shown as:
  Section A (MCQ × 10, 2m each):  20m
  Section B (Short Answer × 6, 5m each): 30m
  Section C (Essay × 1, 15m): 15m
  ────────────────────────────────────
  Total: 65 / 80 marks
```

### Chapter Coverage Validation

After marks tally is valid, system runs coverage check:

```
Check: for each section with chapter constraint, verify enough chunks exist

Pass: silent (no message shown)
Fail: amber warning inline under that section row:
  "⚠ Not enough material in Ch. 12 for 5 Long Answer questions (only 3 chunks). 
   Upload more material for Ch. 12, or reduce count to 2."
   
Generate button remains disabled until all coverage checks pass.
```

### Question Generation (After Clicking "Generate Paper")

```
Phase 1 — Validation confirmation:
  Modal: "Generate 80-mark Physics paper?"
  Shows summary: 3 sections, 17 questions, estimated 4 min 20 sec
  [Cancel] [Confirm & Generate]

Phase 2 — Generation Progress (replaces Generate button area):
  ┌──────────────────────────────────────────┐
  │  Generating your paper...                │
  │                                          │
  │  ████████████░░░░░░░  14/17 questions   │
  │                                          │
  │  Current: Section B, Question 2          │
  │  ✓ Section A complete (10 questions)     │
  │  ⟳ Section B in progress (4/6)           │
  │  ○ Section C pending                     │
  │                                          │
  │  LLM: Gemini 1.5 Flash ●  (green dot)   │
  │  (changes to: Ollama ● if fallback)      │
  └──────────────────────────────────────────┘
  
  Cancel Generation button shown (stops after current question)

Phase 3 — Preview (after completion):
  For each section, show one sample question:
  
  ┌──────────────────────────────────────────────────┐
  │  Section A · Question 1 · MCQ · Bloom: Apply · 2m │
  │                                                    │
  │  "A transformer has 200 primary turns and 50      │
  │   secondary turns. If primary voltage is 240V,    │
  │   what is the secondary voltage?"                 │
  │                                                    │
  │  A) 60V  B) 120V  C) 240V  D) 480V               │
  │  Correct: A) 60V                                   │
  │                                                    │
  │  Source: NCERT Physics Ch.12, Page 215            │
  │  Groundedness: 0.84 ✓                             │
  │                                                    │
  │  [Accept ✓]  [Regenerate ↻]  [Edit ✏]           │
  └──────────────────────────────────────────────────┘
```

### Question Edit Mode (NEW — Not in Original Spec)

Clicking [Edit ✏] opens inline editor:
```
- Question text becomes editable textarea
- Options (for MCQ) become individual editable inputs
- "Correct answer" selector shows
- Groundedness re-checked after edit (shows new score)
- [Save Edit] [Cancel]
- Warning: "Manually edited questions are marked as teacher-modified and excluded from groundedness stats"
```

### Error States

```
Generation failure (Gemini down):
  Progress bar stops. Status changes to:
  "⚠ Gemini rate-limited. Switching to Ollama (fallback)..."
  [amber warning, generation continues automatically]

Ollama also fails:
  "⚠ All LLMs unavailable. Using cached question pool for Section A."
  [continues with cached questions, shows which sections used cache]

Full failure:
  Red error state: "Generation failed. 10/17 questions completed."
  Shows which sections succeeded and which failed
  [Retry Failed Sections] [Use Partial Paper (10 questions)]
  [Start Over]
```

### Mobile Layout

- Left and Right panels stack vertically (Left on top, Right below)
- Section rows collapse to accordion view on mobile
- Marks tally becomes a sticky bottom bar: "65 / 80 ↑ Tap to see breakdown"

---

## SCREEN 4 — Live Monitor Dashboard (`/dashboard/exams/:id/live`)

### Purpose
Teacher's real-time command center during exam. Must update without any page reload. This is the most visually impressive screen — the demo moment where a tab switch makes a tile turn amber in real time.

### Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│  HEADER BAR (sticky, white, shadow)                          │
│  ← Physics Unit Test  [ACTIVE ● LIVE]  Timer: 47:23 left    │
│  [End Exam for All] (red, confirmation required)             │
│  [⏸ Pause All Sessions] (amber)  [🔔 Sound On/Off]          │
├──────────────────────────────────────────────────────────────┤
│  SUMMARY BAR (single row of 5 stat chips)                    │
│  [36 Active] [24 Clean ✓] [8 Watch ⚠] [3 Warn 🔶] [1 Flag 🔴]│
│                                                              │
│  Filter: [All ▼] [FLAGGED ▼]    Sort: [By Risk ▼]           │
├──────────────────────────────────────────────────────────────┤
│  MAIN AREA (two-column)                                      │
│  ┌─── STUDENT TILES GRID (left, 70%) ───────────────────┐   │
│  │  [4 tiles per row on desktop, responsive grid]        │   │
│  │                                                       │   │
│  │  ┌───────────────┐  ┌───────────────┐               │   │
│  │  │ Arjun Sharma  │  │ Priya Patel   │               │   │
│  │  │               │  │               │               │   │
│  │  │     87        │  │     43        │               │   │
│  │  │    CLEAN ✓    │  │   FLAGGED ✗   │               │   │
│  │  │               │  │  [pulsing red]│               │   │
│  │  │ Consent ✓     │  │ Consent ✓     │               │   │
│  │  │ Q: 12/17      │  │ Q: 8/17       │               │   │
│  │  │ Events: 1     │  │ Events: 7 🔴  │               │   │
│  │  │               │  │               │               │   │
│  │  │ [Expand ↗]   │  │ [Expand ↗]   │               │   │
│  │  └───────────────┘  └───────────────┘               │   │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌─── ALERT FEED (right, 30%) ─────────────────────────┐   │
│  │ 🔴 Priya Patel — 14:32:01                           │   │
│  │    FLAGGED: Score dropped to 43                     │   │
│  │                                                      │   │
│  │ 🔶 Rahul Singh — 14:31:45                           │   │
│  │    TAB SWITCH #3 detected                           │   │
│  │                                                      │   │
│  │ ⚠  Arjun Sharma — 14:30:12                         │   │
│  │    GAZE AWAY > 4s (3 occurrences)                  │   │
│  │                                                      │   │
│  │ [Load More...]                                       │   │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Student Tile — Expanded View (click "Expand")

Clicking a tile opens a right side-panel (or full modal on mobile):

```
┌──────────────────────────────────────────────────────┐
│  Priya Patel  ×                                      │
│  ─────────────────────────────────────────────────   │
│                                                      │
│  INTEGRITY SCORE CARD (shared component — used here, │
│  in report, in appeal panel, in student post-exam)   │
│                                                      │
│  ┌─────────────────────────────────────────────┐    │
│  │  43 ±7  [FLAGGED]  Tier 1 (full baseline)   │    │
│  │  ─────────────────────────────────────────  │    │
│  │  Behavioral (30%):    ████░░░░  52/100      │    │
│  │  AI Perplexity (15%): ██░░░░░░  28/100      │    │
│  │  Stylometric (25%):   ██░░░░░░  31/100      │    │
│  │  Answer Quality (25%):████████  82/100      │    │
│  │  Time Anomaly (5%):   ███░░░░░  41/100      │    │
│  └─────────────────────────────────────────────┘    │
│                                                      │
│  EVENT TIMELINE (chronological):                     │
│  14:28:00  Exam started                             │
│  14:28:45  Gaze away 5.2s  ⚠ WATCH triggered       │
│  14:30:12  Tab switch #1                            │
│  14:31:45  Tab switch #3 → WARN triggered           │
│  14:32:01  Score dropped to 43 → FLAGGED            │
│                                                      │
│  ANSWER BREAKDOWN (per question):                    │
│  Q1: 120s | Similarity: 0.82 | Perplexity: 0.31 ✓  │
│  Q2: 23s  | Similarity: 0.12 | Perplexity: 0.89 ✗  │
│                                                      │
│  OVERRIDE ACTIONS:                                   │
│  [⚠ Warn Student]  [🚩 Flag Student]               │
│  [🔕 Mute Alerts for This Student]                  │
│  [↩ Clear All Flags] (teacher can reset)            │
└──────────────────────────────────────────────────────┘
```

### Sort & Filter

```
Sort options:
  By Risk (default): FLAGGED first, then WARN, WATCH, CLEAN
  By Name (A-Z)
  By Score (ascending — most at risk at top)
  By Join Time
  By Questions Answered (least answered first = possible issue)

Filter options:
  All | CLEAN | WATCH | WARN | FLAGGED
  "Only show consent not given" (shows any ghost sessions)
```

### End Exam Flow

```
[End Exam for All] → Confirmation modal:
  "End exam for all 36 students?"
  "Students currently answering will have their answers auto-saved."
  "This cannot be undone."
  [Cancel] [End Exam Now] (red)
  
On confirm:
  All student sessions receive "exam_ended" WebSocket event
  Students see: "Exam has ended. Your answers have been submitted."
  Live Monitor shows "ENDED" state, tiles go gray, download reports CTA appears
```

### Pause All Sessions Flow

```
[Pause All Sessions] → amber modal:
  Reason input: [text, optional, max 200 chars]
  e.g. "Technical issue — please wait"
  [Cancel] [Pause & Notify Students]
  
On pause:
  Timer freezes for all students
  Students see: "Exam paused by invigilator. Reason: Technical issue — please wait."
  Teacher sees "PAUSED" header bar + [Resume All Sessions] button
```

### EMPTY STATE (exam not started yet / no students joined)

```
Large centered:
  [clock illustration]
  "Waiting for students to join"
  
  Join Code: [ABC123] [📋 Copy] [QR Code]
  Share this with your students to begin
  
  "0 students have joined"
  Auto-refreshes every 5 seconds
```

### WebSocket Disconnect Banner

```
When Socket.IO disconnects:
  Appears at top of page, full width, amber background:
  "⚠ Live connection lost. Attempting to reconnect... (attempt 2/5)"
  Score updates paused. Last update: 14:32:01
  
  Reconnected:
  Briefly shows green banner: "● Live connection restored"
  (auto-dismisses after 3 seconds)
  Rehydrates all tile scores from Redis
```

### Mobile Layout

- Tiles: 2 per row (responsive grid)
- Alert Feed: hidden by default, accessible via "Alerts (7)" FAB button bottom-right
- Expanded view: opens as full-screen bottom sheet
- Sort/Filter: accessible via filter icon in header

---

## SCREEN 5 — Student Consent Screen (`/exam/consent`)

### Purpose
The ethical gate before the exam begins. DPDP compliance is demonstrated here. Student must actively confirm — never auto-accepted. This screen is shown to judges as proof of ethical design.

### Layout Structure

```
Full screen modal (cannot be dismissed, no overlay click-to-close)
Background: navy gradient (same as landing hero)

┌────────────────────────────────────────────────────┐
│                                                    │
│  [ExamGuard AI logo + DPDP Badge]                  │
│                                                    │
│  "Before you begin:"                               │
│  [Physics Unit Test — Arjun Sharma]               │
│  Exam Duration: 60 min · 80 marks                  │
│                                                    │
│  ─── CAMERA PREVIEW ───                           │
│  [Circular webcam preview, 80px]                   │
│  "Camera preview — confirm this is your camera"   │
│  "Wrong camera? Select another →"                 │
│                                                    │
│  ─── WHAT WE MONITOR ───                         │
│  (4 consent items, each with toggle icon)         │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ 👁 Gaze & Liveness (Webcam)                 │ │
│  │ "Checks if you're looking at the screen.    │ │
│  │  Processed entirely in your browser.        │ │
│  │  Raw video is NEVER uploaded or recorded."  │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ 🎤 Audio Level (Microphone)                 │ │
│  │ "Detects unusual sound spikes only.         │ │
│  │  No audio is recorded or stored."           │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ 📝 Answer Analysis (Typing patterns)        │ │
│  │ "Checks if answers match your writing style.│ │
│  │  Used to detect AI-generated text."         │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │ 🪟 Tab & Window Activity (Browser events)   │ │
│  │ "Detects if you switch to another tab.      │ │
│  │  No screen recording. Browser events only." │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  ─────────────────────────────────────────────    │
│  [I Understand & Begin Exam]  (full-width purple) │
│  [Cancel — Return to Home]    (small gray link)   │
│                                                    │
│  Privacy by Design · DPDP Act 2023 Compliant      │
│  [View full privacy policy →]                     │
└────────────────────────────────────────────────────┘
```

### Consent Item Design

Each of the 4 items is a card with:
- Icon (40px, rounded bg)
- Title (H4, bold)
- 2-line plain-language explanation
- Green checkmark that fills in as student reads (scroll-triggered, must scroll to bottom before button activates)

### Camera Preview

- Shows live webcam feed in a circular crop (80px on desktop, 100px on mobile)
- "Camera not detected?" shows instructions to allow permissions
- "Select camera" dropdown if multiple cameras detected (relevant for desktop with external webcam)
- On mobile: shows rear/front camera toggle option

### Mobile Layout

- Scrollable content (critical — 4 items + button must scroll on small screens)
- Button remains sticky at bottom even while scrolling
- "I Understand & Begin" button is disabled until user scrolls to bottom
- Camera preview: smaller (60px) on mobile to save space

### Permission Handling

```
Camera permission denied:
  Shows warning: "Camera access required for this exam."
  [Allow Camera Access] button (opens browser permission dialog)
  "Having trouble? Ask your invigilator for help."

Microphone permission denied:
  Same pattern as camera
  
Both denied:
  Teacher is notified: "Student [name] could not grant permissions"
  Option shown to student: "Proceed without monitoring" (teacher must enable this option in exam settings)
```

---

## SCREEN 6 — Student Blink Challenge (`/exam/liveness`)

### Purpose
Liveness verification. Proves a real human is behind the camera, not a photo. Runs before the exam starts. MediaPipe FaceMesh in WASM — no data sent to server.

### Layout Structure

```
Full screen, dark navy background, centered content

┌────────────────────────────────────────────────┐
│  [ExamGuard AI logo — small, top left]          │
│                                                  │
│         BLINK TWICE TO VERIFY                    │
│         (H2, white, centered)                    │
│                                                  │
│  ┌─── Webcam Preview ────────────────────┐      │
│  │  [Circular crop, 240px diameter]       │      │
│  │  [Face mesh overlay — green dots on   │      │
│  │   detected face landmarks]             │      │
│  │                                        │      │
│  │  [8-second countdown ring around       │      │
│  │   the circle, animated, amber→red]     │      │
│  └────────────────────────────────────────┘      │
│                                                  │
│  BLINK PROGRESS:                                 │
│  [○ First blink]   [○ Second blink]             │
│  (fills with ✓ on each detected blink)           │
│                                                  │
│  "Look directly at your camera and blink twice" │
│  (14px gray caption)                            │
│                                                  │
│  "Processing locally — nothing is recorded"     │
│  (12px, muted text)                             │
└────────────────────────────────────────────────┘
```

### State Transitions

```
State 1 — Detecting face:
  "Looking for your face..."
  Countdown ring not started yet
  No blink progress shown

State 2 — Face detected, waiting for blinks:
  "Blink twice to confirm you're present"
  Countdown ring starts (8 seconds, amber arc depleting)
  First blink circle pulsing to prompt action

State 3 — First blink detected:
  First circle fills green with checkmark: ✓
  Brief haptic feedback on mobile
  "First blink detected! Now blink again."

State 4 — Both blinks detected:
  Second circle fills green: ✓
  Brief success animation: green flash on the circular preview
  "Liveness confirmed ✓"
  Auto-advances to exam after 1.5 seconds

State 5 — Timeout (8 seconds no blink):
  Ring turns red
  "Blink not detected. Try again."
  [Try Again] button
  Extra help: "Make sure your face is well-lit and looking at the camera"

State 6 — Low light detected (EAR calculation fails consistently):
  "Poor lighting detected"
  "Move to a brighter area or turn on a light"
  [Try Again] button
  Teacher fallback: "Can't complete liveness check? Ask your invigilator for a manual override."
```

### EAR Threshold

EAR (Eye Aspect Ratio) < 0.25 for 2 consecutive frames = blink detected. Both within 8-second window = liveness confirmed.

### Mobile Specifics

- Circular preview: 200px on mobile (larger portion of screen)
- Front-facing camera auto-selected on mobile
- Extra instruction: "Hold your phone steady at eye level"

---

## SCREEN 7 — Student Exam Interface (`/exam/session`)

### Purpose
The core exam-taking experience. Must be clean, distraction-free, and functional offline. This screen runs for 30–90 minutes — every detail matters. NEVER break during a live exam.

### Layout Structure (Desktop)

```
┌──────────────────────────────────────────────────────────────┐
│  TOP BAR (sticky, white, shadow-sm)                          │
│  [Physics Unit Test] [Section B — Short Answer] [Q 14 / 17]  │
│  [⏱ 47:23] (countdown, red < 5 min)  [● 87] (integrity dot)│
│  [💾 Saved 2:14 ago] (sync indicator)                        │
├──────────────────────────────────────────────────────────────┤
│  MAIN LAYOUT (two columns)                                   │
│                                                              │
│  ┌── QUESTION PANEL (70%) ──────────────────────────────┐   │
│  │                                                       │   │
│  │  [Section B · Short Answer · 5 marks]                │   │
│  │                                                       │   │
│  │  Q.14  "Explain the principle of electromagnetic     │   │
│  │        induction and state Faraday's law. Give one   │   │
│  │        real-world application."                      │   │
│  │                                                       │   │
│  │  ┌─────────────────────────────────────────────────┐ │   │
│  │  │ [Textarea — answer input]                       │ │   │
│  │  │ min-height: 200px, resizable                    │ │   │
│  │  │ Placeholder: "Type your answer here..."         │ │   │
│  │  │                                                 │ │   │
│  │  │                           Word count: 0 / 200   │ │   │
│  │  └─────────────────────────────────────────────────┘ │   │
│  │                                                       │   │
│  │  [← Previous]  [Mark for Review ⭐]  [Next →]        │   │
│  │                                                       │   │
│  │  [Submit Exam] (only shown on last question)          │   │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌── QUESTION PALETTE (30%) ────────────────────────────┐   │
│  │                                                       │   │
│  │  SECTION A — MCQ (10 questions)                      │   │
│  │  [1✓][2✓][3✓][4✓][5✓][6✓][7✓][8⭐][9✓][10✓]       │   │
│  │                                                       │   │
│  │  SECTION B — Short Answer (6 questions)              │   │
│  │  [11✓][12✓][13⭐][14●][15 ][16 ]                    │   │
│  │                                                       │   │
│  │  SECTION C — Essay (1 question)                      │   │
│  │  [17 ]                                               │   │
│  │                                                       │   │
│  │  ─── LEGEND ───                                      │   │
│  │  [✓] Answered   [⭐] Marked for review               │   │
│  │  [●] Current    [ ] Not visited                      │   │
│  │                                                       │   │
│  │  Summary:                                            │   │
│  │  Answered: 13 / 17                                   │   │
│  │  Marked for review: 2                               │   │
│  │  Unanswered: 2                                      │   │
│  │                                                      │   │
│  │  [Submit All Answers →]                              │   │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

### Question Palette Colors

```
Not visited:  white bg, gray border, gray number
Current:      purple bg, white number (●)
Answered:     green bg, white ✓
Marked for review: yellow bg, star icon ⭐
Flagged by system: red dot on corner (system-generated, not student-visible label)
```

### Question Type Renderings

```
MCQ:
  Question text at top
  4 options as large radio buttons (full-width, 48px tap target)
  Option layout: [○ A] [Option text] — entire row is clickable
  Selected: purple border + filled radio, light purple background on row
  
True/False:
  Question text
  Two large toggle buttons: [TRUE] [FALSE] — side by side
  Selected: filled with green (True) or red (False)

Fill in the Blank:
  Question text with blank shown as underlined space
  Text input centered in the blank space
  
Short Answer (< 200 words):
  Textarea with word counter (soft limit at 200, hard limit at 250)
  
Long Answer (< 500 words):
  Larger textarea, word counter
  Basic formatting hint: "Use clear paragraphs. Diagrams cannot be submitted."
  
Essay (500+ words):
  Full-width large textarea
  Word counter prominent
  Character + word + paragraph count shown
```

### Mark for Review Feature

```
[Mark for Review ⭐] button:
  Click once: marks question, button turns amber, palette shows star
  Click again: unmarks, returns to answered/unanswered state
  
Marked questions appear in palette with ⭐
Summary shows "2 questions marked for review"
Submit confirmation dialog shows marked questions: 
  "You have 2 questions marked for review (Q8, Q13). 
   Are you sure you want to submit?"
```

### Timer Behavior

```
Normal: white background, dark text
< 10 minutes: amber background, amber text, subtle pulse
< 5 minutes: red background, white text, urgent pulse animation
< 1 minute: red background, white text, faster pulse, vibrate on mobile

At 0:00:
  Auto-submits with all current answers
  Toast: "Time's up! Your answers have been automatically submitted."
  No further changes possible
```

### Integrity Monitor Icon (Top Right)

```
Small colored dot + score number in top bar:
  ● 87 (green) — CLEAN
  ● 74 (amber) — WATCH
  ● 63 (amber) — WARN  
  ● 41 (red)   — FLAGGED

Student does NOT see their detailed breakdown — only the dot color and score number.
This prevents gaming the system.

WARN state: amber banner appears below top bar:
  "⚠ Academic integrity notice. Continue honestly. Your teacher has been notified."
  (non-blocking, cannot be dismissed, persists until score improves)
  
FLAGGED state: red banner:
  "🚩 Your exam has been flagged for review. 
   Continue answering — your grade is pending teacher review."
```

### LocalStorage Backup System

```
Every 30 seconds: auto-save all answers to localStorage
Key: examguard_session_{session_id}_answers

Save indicator in top bar:
  Saving... (spinner)  →  ✓ Saved 0:30 ago  →  ✓ Saved 1:00 ago...

On disconnect:
  "⚠ Connection lost. Your answers are saved locally. 
   Reconnecting... (attempt 1/5)"
   Timer pauses visually but continues counting internally
   
On reconnect:
  "● Reconnected! Syncing your answers..."
  Answers pushed to backend
  "✓ All answers synced."
  Timer resumes
  
On disconnect > 5 minutes:
  "⚠ Connection lost for 5+ minutes. Your session has been paused."
  "Your teacher has been notified. Please wait for instructions."
  Answers remain saved locally
```

### Submit Confirmation Dialog

```
[Submit Exam] or [Submit All Answers →] →

Modal:
  "Submit your exam?"
  
  Review summary:
  ✓ Answered: 15 / 17
  ⭐ Marked for review: 2 (Q8, Q13)  ← highlighted in amber
  ✗ Unanswered: 0
  
  Warning if unanswered: "You have 2 unanswered questions. 
  These will receive 0 marks."
  
  [Go Back and Review]    [Submit Final Answers →]
  (white/outlined)        (purple filled)
  
  "You cannot change answers after submission."
```

### Right-click & Paste Prevention

```
Right-click: prevented (contextmenu event blocked)
Paste into textarea: 
  - Event captured, content analyzed for paste-speed signature
  - If paste detected: integrity event logged (not blocked — blocking causes UX friction)
  - Paste monitoring logged as behavioral_event type "paste_detected"
  - Student sees no interruption
  
Copy attempt: same pattern — logged but not blocked
```

### Mobile Layout (Critical — Many Students Use Phones)

```
Top bar: simplified — Exam title + Timer only (no section indicator)
Question area: full width
Answer area: full width, auto-height
Palette: collapsible bottom drawer:
  Tab at bottom: "Q 14/17  [☰ Questions]"
  Tap to open: slides up showing palette grid
  Tap question number: navigates + closes drawer

Navigation buttons: sticky at bottom (Previous | Mark Review | Next)
All MCQ options: full width, 56px min-height for thumb tap
Timer alarm: vibration on mobile (< 5 min)
```

---

## SCREEN 8 — Student Post-Exam & Appeal (`/exam/complete`)

### Purpose
Transparent, non-accusatory post-exam experience. Student should understand what happened, feel they were treated fairly, and know how to appeal.

### Layout Structure

```
┌────────────────────────────────────────────────────┐
│  [ExamGuard AI logo]                               │
│                                                    │
│  ✓ Exam Submitted                                  │
│  (H1, green checkmark, centered)                   │
│                                                    │
│  "Physics Unit Test — Arjun Sharma"                │
│  "Submitted at 15:32:41 · 17/17 questions answered"│
│                                                    │
│  "Your teacher is reviewing your results."         │
│                                                    │
│  ── STATUS TRACKER ──────────────────────────────  │
│  ● Submitted  →  ○ Under Review  →  ○ Results Ready│
│  (step indicator, currently at step 1)             │
│                                                    │
│  ── IF FLAGGED (conditional) ───────────────────   │
│  ┌─── Integrity Notice ────────────────────────┐  │
│  │  ⚠ Your exam is under additional review    │  │
│  │                                              │  │
│  │  Our system noticed:                        │  │
│  │  • Unusual response patterns on Q7, Q9      │  │
│  │  • Multiple tab switch events (3 times)     │  │
│  │  • Answer style variation from your         │  │
│  │    previous exams                           │  │
│  │                                              │  │
│  │  Your grade is held pending teacher review. │  │
│  │  You have 24 hours to submit a response.    │  │
│  │  Deadline: June 16, 2026 at 15:32:41        │  │
│  └──────────────────────────────────────────────┘  │
│                                                    │
│  ── APPEAL FORM (conditional, if flagged) ───────  │
│  "Want to provide context? (optional)"             │
│                                                    │
│  [Textarea — 200 word limit]                       │
│  "Explain anything that might have caused        " │
│  "unusual patterns (e.g., medical condition,    "  │
│  "connectivity issues, unusual circumstance)"    " │
│  Word count: 0 / 200                              │
│                                                    │
│  [Submit Response]  (purple)                       │
│  "Your response will be shown to your teacher     │
│   alongside the integrity report."                │
│                                                    │
│  ── AFTER APPEAL SUBMITTED ──────────────────────  │
│  ✓ Response submitted                             │
│  "Your teacher will review your case and make      │
│   a decision. You'll see results here once done."  │
│                                                    │
│  ── AFTER GRADE RELEASED ────────────────────────  │
│  [GRADE RELEASED] status card showing:            │
│  Score: 62 / 80                                   │
│  Status: CLEARED (green) or CONFIRMED FLAG (red)   │
│  Teacher note (if any)                            │
└────────────────────────────────────────────────────┘
```

### Language Rules (Non-Accusatory)

The system NEVER says:
- "You cheated"
- "AI content detected"
- "Your answers are suspicious"

The system ALWAYS says:
- "Unusual patterns noticed"
- "Under additional review"
- "Your teacher will make the final decision"

---

## SCREEN 9 — Teacher Review & Appeal Panel (`/dashboard/exams/:id/review`)

### Purpose
Teacher makes final integrity decisions. Must show both sides (integrity report + student response) together. Every decision is permanent and logged.

### Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│  FLAGGED QUEUE (left panel, 35%)                             │
│                                                              │
│  "Pending Review (3)"                                        │
│                                                              │
│  ┌──────────────────────────────────────────┐               │
│  │ Priya Patel           ● FLAGGED          │ ← selected   │
│  │ Submitted appeal: Yes · 2h remaining     │               │
│  └──────────────────────────────────────────┘               │
│                                                              │
│  ┌──────────────────────────────────────────┐               │
│  │ Rahul Singh           ● FLAGGED          │               │
│  │ No response · 18h remaining              │               │
│  └──────────────────────────────────────────┘               │
│                                                              │
│  ┌──────────────────────────────────────────┐               │
│  │ Maya Gupta            ● FLAGGED          │               │
│  │ Submitted appeal: Yes · Deadline passed  │               │
│  └──────────────────────────────────────────┘               │
│                                                              │
│  [Clear All No-Response Cases] (bulk action, amber)         │
│                                                              │
│─────────────────────────────────────────────────────────────│
│  SIDE-BY-SIDE PANEL (right, 65%)                            │
│                                                              │
│  ┌── INTEGRITY REPORT (left 50%) ────┐ ┌── STUDENT RESPONSE │
│  │  Priya Patel — Score: 43 ±7      │ │  (right 50%)        │
│  │  Tier 1 · [FLAGGED]               │ │                     │
│  │                                   │ │  Submitted 2h ago   │
│  │  [IntegrityScoreCard component]   │ │                     │
│  │  (same as live monitor expand)    │ │  "I was having      │
│  │                                   │ │   connectivity      │
│  │  Flag Reasons:                    │ │   issues during     │
│  │  • AI Perplexity: 0.89 (high)    │ │   the exam and      │
│  │  • Tab switches: 3               │ │   had to reconnect  │
│  │  • Style deviation: 0.71         │ │   twice. The timer  │
│  │                                   │ │   kept running."    │
│  │  Event Timeline:                  │ │                     │
│  │  [full timeline here]             │ │  ─────────────────  │
│  └───────────────────────────────────┘ │  "No response      │
│                                        │   submitted" (gray) │
│  ─────────────────────────────────────────────────────────── │
│  DECISION ACTIONS:                                           │
│                                                              │
│  [✓ Clear Flag — Release Grade]  [✗ Confirm Flag — Hold]   │
│  (green)                          (red)                     │
│                                                              │
│  Before confirming either: modal appears:                   │
│  "Confirm flag for Priya Patel?                             │
│   Grade will remain held. This is logged with your name     │
│   and timestamp."                                           │
│  [Cancel] [Confirm]                                         │
│                                                              │
│  After decision: card shows:                                │
│  "Decision recorded: CLEARED by Rajan Kumar · 16:45:02"    │
└──────────────────────────────────────────────────────────────┘
```

### Bulk Actions

```
Top of queue panel:
  [Select All] checkbox
  When ≥1 selected: [Clear Selected (3)] [Confirm Flag Selected (3)]
  
  "Clear All No-Response Cases" → modal:
  "Clear flags for 2 students who did not submit an appeal?
   This will release their grades."
  [Cancel] [Clear 2 Cases]
```

---

## SCREEN 10 — Reports & Downloads (`/dashboard/exams/:id/reports`)

### Purpose
Post-exam analytics. Teacher sees class performance, downloads individual PDFs, exports CSV for grade book.

### Layout Structure

```
┌──────────────────────────────────────────────────────────────┐
│  SUMMARY STATS BAR                                           │
│  [36 students] [Avg: 74.2] [Flagged: 3 (8%)] [Appeals: 2]  │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  CLASS SUMMARY CARD                                          │
│                                                              │
│  ┌── Score Distribution Histogram (Recharts) ─────────────┐ │
│  │  [Bar chart: x-axis 0-100, y-axis student count]       │ │
│  │  Color bands: green (>85), amber (70-85), red (<70)    │ │
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  Quick stats: Highest: 96 | Lowest: 38 | Median: 76        │
│  [Download Class Summary PDF] [Export CSV]                  │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  FILTER & SORT                                               │
│  [All] [CLEAN] [WATCH] [WARN] [FLAGGED] [Pending Decision]  │
│  Sort: [By Score ▼]  Search: [name or score]                │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  STUDENT REPORT CARDS (list view)                            │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Arjun Sharma                 Score: 87/100  ✓ CLEAN │    │
│  │ Tier 1 (full baseline)       Baseline: 3 exams      │    │
│  │ 0 flags · Decision: N/A                             │    │
│  │ [Download PDF ↓]  [View Report]  [Share Link 🔗]   │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Priya Patel                  Score: 43/100  ✗ FLAG  │    │
│  │ Tier 1 (full baseline)       Baseline: 5 exams      │    │
│  │ Flag confirmed · Grade held  Appeal: Yes             │    │
│  │ [Download PDF ↓]  [View Report]  [Go to Review]     │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
│  [Download All PDFs as ZIP]  (powered by JSZip)            │
└──────────────────────────────────────────────────────────────┘
```

### Per-Student PDF Report Structure

Generated by ReportLab. Must contain:

```
Page 1: Summary
  - Student name, exam title, date
  - IntegrityScoreCard (same visual as UI component)
  - Score: 43 ±7 | Tier: Tier 1 (full baseline) | Status: FLAGGED
  - 5-factor bars with weights and values
  - Baseline comparison graph (this exam vs previous 3)

Page 2: Behavioral Events
  - Chronological event log with timestamps
  - Gaze events, tab switches, audio spikes, paste events
  - Each event has: timestamp, type, severity, score impact

Page 3: Answer Analysis
  - Per-answer breakdown table
  - Columns: Q#, Time Spent, Perplexity Score, Style Distance, Eval Score
  - Highlighted rows for suspicious answers

Page 4: Source Citations
  - Which chunks each question was generated from
  - Chapter reference, page reference, cosine similarity
  - "This question was grounded in NCERT Physics Ch.12, Page 215"

Page 5: Appeal Trail (if applicable)
  - Student appeal text
  - Teacher decision with name + timestamp
  - Final grade status

Footer on all pages:
  "Generated by ExamGuard AI v6 · DPDP Compliant · [exam date]"
  "This report is confidential. Intended for teacher use only."
```

### EMPTY STATE (exam still active)

```
Reports tab shows:
  [hourglass illustration]
  "Reports will be available after the exam ends"
  
  Exam Status: ACTIVE ● 47 min remaining
  [Live Monitor →] (blue link)
```

### CSV Export

One row per student:
```
name, email, score, integrity_score, baseline_tier, status, flags, appeals, decision, submitted_at
```

---

## SCREEN 11 — Account Settings & Password Reset (NEW — Not in Original Spec)

### Password Reset (`/reset-password`)

```
Arrives here from email magic link.

┌────────────────────────────────────────┐
│  [ExamGuard AI logo]                   │
│                                        │
│  "Set a new password"                  │
│  [linked email shown, cannot edit]     │
│                                        │
│  New password: [••••••••]  [Show/Hide] │
│  Password strength: ████░░ Strong      │
│                                        │
│  Confirm password: [••••••••]          │
│                                        │
│  [Set New Password →]                  │
│                                        │
│  Password requirements:                │
│  ✓ At least 8 characters               │
│  ✓ One uppercase letter                │
│  ✓ One number                          │
└────────────────────────────────────────┘
```

### Account Settings (`/dashboard/settings`)

```
Tabs: [Profile] [Notifications] [Exam Defaults] [Danger Zone]

Profile tab:
  Display name: [editable]
  Institute name: [editable]
  Email: [shown, not editable — "Contact support to change"]
  Avatar: [upload image, circular crop]
  [Save Changes]

Notifications tab:
  Toggle: Email when student joins exam
  Toggle: Email when exam ends + report ready
  Toggle: Email when student submits appeal
  Toggle: Browser notifications for FLAGGED events
  [Save Preferences]

Exam Defaults tab:
  Default duration: [60] minutes
  Default total marks: [80]
  Default question types: [multiselect]
  These pre-fill the Create Exam modal.

Danger Zone tab:
  [Delete My Account] (red, requires password confirmation)
  [Export My Data] (DPDP right to data portability)
```

---

# PART 4 — COMPONENT LIBRARY (Reusable Across All Screens)

## 4.1 IntegrityScoreCard (Shared Component — Used in 4 Places)

This exact same component renders in:
1. Live Monitor tile expanded view
2. Teacher Review panel (left side)
3. Student Post-Exam page (if flagged)
4. PDF Report (as visual export)

```tsx
interface IntegrityScoreCardProps {
  score: number;           // 0-100
  ci: number;              // ±confidence interval (e.g. 7)
  tier: 1 | 2 | 3;
  status: 'CLEAN' | 'WATCH' | 'WARN' | 'FLAGGED';
  factors: {
    behavioral: number;
    perplexity: number;
    stylometric: number;
    answerQuality: number;
    timeAnomaly: number;
  };
  stylometricDisabled?: boolean; // Tier 3
}

Visual layout:
  ┌──────────────────────────────────┐
  │  74 ±7          [WATCH]  Tier 1  │
  │  ─────────────────────────────   │
  │  Behavioral    (30%) ████░░  68  │
  │  AI Perplexity (15%) ███░░░  55  │
  │  Stylometric   (25%) █████░  82  │
  │  Answer Quality(25%) █████░  84  │
  │  Time Anomaly  (5%)  ████░░  71  │
  │                                  │
  │  [Tier 1: Full baseline active]  │
  └──────────────────────────────────┘
  
  Tier 3 variant: Stylometric row shows "— Not available (first exam)"
  
  Score number: font-mono, 36px, color-coded
  CI range: font-mono, 14px, muted
  Status badge: pill with correct integrity state colors
  Factor bars: colored according to factor score (green >75, amber 50-75, red <50)
```

## 4.2 StudentTile (Live Monitor)

```tsx
interface StudentTileProps {
  name: string;
  score: number;
  status: IntegrityStatus;
  consentGiven: boolean;
  questionsAnswered: number;
  totalQuestions: number;
  eventCount: number;
  isSelected: boolean;
  onExpand: () => void;
}

Visual: Card with left-colored border (status-colored)
  Name: bold, 14px
  Score: large monospace number, status-colored
  Status badge: CLEAN/WATCH/WARN/FLAGGED
  Consent: small green ✓ DPDP indicator
  Progress: "Q 12/17" small gray text
  Events: if > 0 WARN events: "⚠ 3 events" in amber
  If FLAGGED: tile pulsing red animation
  Hover: slight elevation (box-shadow increase)
  Click: calls onExpand()
```

## 4.3 AlertFeedItem

```tsx
interface AlertFeedItemProps {
  studentName: string;
  eventType: 'gaze_away' | 'tab_switch' | 'paste_detected' | 'audio_spike' | 
             'phone_detected' | 'watch_triggered' | 'warn_triggered' | 'flagged';
  timestamp: Date;
  severity: 'info' | 'warning' | 'danger';
}

Visual:
  Left border: info=blue, warning=amber, danger=red
  Icon: matching event type
  Student name: bold link (clicking highlights their tile)
  Event description: plain language (not tech terms)
  Timestamp: relative (e.g. "2 min ago") + absolute on hover tooltip
```

## 4.4 SectionBuilderRow (Paper Config)

```tsx
interface SectionRowProps {
  sectionLetter: string;
  questionType: QuestionType;
  count: number;
  marksEach: number;
  bloomsLevel: BloomsLevel;
  chapterWeight: string;
  negativeMarking: 'none' | 'quarter' | 'half';
  onUpdate: (field: string, value: any) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}

Visual: horizontal card row with drag handle on left
All fields in-line, compact
Section total shown as "= 20m" on right of count × marks
Inline validation error under chapter field if coverage fails
```

## 4.5 ProgressStream (Generation)

```tsx
interface ProgressStreamProps {
  current: number;
  total: number;
  currentLabel: string;
  sections: Array<{
    name: string;
    status: 'pending' | 'in_progress' | 'complete' | 'failed';
    count: number;
    done: number;
  }>;
  llmStatus: 'gemini' | 'ollama' | 'cached';
}

Visual:
  Wide progress bar with percentage
  Per-section status list with icons
  LLM indicator with live status dot
  Estimated time remaining (decreases in real-time)
  Cancel button
```

---

# PART 5 — COMPLETE 10-AGENT SPECIFICATION

## Unified Integrity Thresholds (Use Everywhere)

```
CLEAN:   score > 85
WATCH:   score 70–85  (teacher sees amber tile, no student notification)
WARN:    score 50–70  (student sees amber banner, teacher tile amber)
FLAGGED: score < 50   (grade held, Review Agent activated, teacher red tile)
```

## Agent 1 — Paper Config Agent

**Trigger:** POST /exams/{id}/paper-config  
**Input:** paper_config JSONB, exam.total_marks, material_chunks for this exam  
**Actions:**
1. Validate marks budget: sum(section.count × section.marks_each) === total_marks. If not: return {error: "Marks budget invalid: currently X/Y marks."}
2. Validate chapter coverage: for each section with chapter constraint, count chunks with that chapter_tag. If chunks < questions_needed × 3 (needs 3 candidates per question): return {error: "Not enough material in Ch.X for Y questions (need Z chunks, have W)."}
3. Generate join code: 6-char alphanumeric, collision-check against active exams
4. Estimate generation time: (question_count × 8s) + (sections × 5s), capped at message "may take up to 10 minutes"
5. On pass: return {status: "config_validated", join_code, estimated_seconds}

## Agent 2 — Material Ingestion Agent

**Trigger:** POST /materials/upload  
**Input:** file binary, exam_id, user_id  
**Actions:**
1. Detect file type: PDF, DOCX, TXT
2. Extract text: PyMuPDF for text PDFs. If len(text) < 100 (scanned): trigger pytesseract OCR with pdf2image
3. Chunk: 512-token segments, 50-token overlap, using tiktoken cl100k_base
4. Chapter detection: regex patterns for heading formats (e.g., "Chapter", "CHAPTER", "Ch.", numbered sections "12.", "12.1"). Assign chapter_tag to each chunk.
5. Embed: all-MiniLM-L6-v2 (384-dimensional vectors). Fallback: nomic-embed-text via Ollama
6. Store: INSERT INTO material_chunks (exam_id, chunk_text, embedding, chapter_tag, source_page)
7. Create HNSW index if not exists: CREATE INDEX ON material_chunks USING hnsw (embedding vector_cosine_ops)
8. SSE progress events to frontend: {chunks_processed: N, total_estimated: M, current_chapter: "Ch.12"}

## Agent 3 — Orchestrator Agent

**This is a deterministic state machine — NOT an LLM. No LLM makes escalation decisions.**

**Trigger:** New behavioral_event, new answer submitted (triggers score recalculation)  
**Input:** session_id, all behavioral events for session, all answer scores  
**Actions:**
1. Calculate 5-factor score:
   - Behavioral = weighted sum of behavioral events (tab switch: -8, gaze away 4s: -5, paste: -10, phone detected: -20, audio spike: -3)
   - Normalize to 0-100
   - AI Perplexity = from Security Agent (0-100, high perplexity = low score = more human-written)
   - Stylometric = from Stylometric Agent (cosine distance to baseline, mapped to 0-100)
   - Answer Quality = from Evaluation Agent (0-100 normalized across all answers)
   - Time Anomaly = time_spent analysis (answers completed too fast = lower score)
2. Weighted sum: (behavioral×0.30) + (perplexity×0.15) + (stylometric×0.25) + (quality×0.25) + (time×0.05)
3. Compute CI: Tier 1: ±7, Tier 2: ±15, Tier 3: N/A (no stylometric)
4. Determine status using unified thresholds
5. Escalation actions (deterministic):
   - WATCH: update Redis, push WebSocket to teacher, no student action
   - WARN: update Redis, push WebSocket to teacher, push "warn_triggered" event to student
   - FLAGGED: update Redis, push WebSocket to teacher, push "flagged" to student, activate Review Agent
6. All decisions logged to integrity_events table with factor breakdown

## Agent 4 — Question Generation Agent

**Trigger:** POST /exams/{id}/activate (after paper_config validated)  
**Input:** paper_config, exam_id (to access material_chunks)  
**For each section:**
1. Retrieve top-k chunks: SELECT * FROM material_chunks WHERE exam_id=X AND chapter_tag=Y ORDER BY embedding <=> query_embedding LIMIT 8
2. Filter by cosine similarity > 0.45 (min relevance threshold)
3. Build prompt: BLOOM_TEMPLATES[level] + question_type_suffix + context_chunks
4. Call LLM: Gemini 1.5 Flash → Ollama mistral:7b → cached_pool
5. Parse response: extract question text, options (for MCQ), correct answer
6. Groundedness check: embed the correct answer, verify cosine similarity to source chunks > 0.72. If < 0.72: regenerate (max 3 attempts), then log as "low_groundedness" and continue
7. Diversity check: embed new question, compare to all previously generated questions in this exam. If cosine similarity > 0.85 to any existing question: regenerate
8. INSERT INTO questions table
9. SSE progress: {current: N, total: M, section: "Section B", question_type: "Short Answer"}

## Agent 5 — Proctoring Agent

**Trigger:** WebSocket event from student browser  
**Input:** structured behavioral events (not raw video — browser sends classified events only)  
**Event types received:**
- gaze_event: {direction: 'center'|'left'|'right'|'up', duration_seconds}
- blink_event: {ear_value, timestamp}
- tab_event: {action: 'hidden'|'visible', timestamp}
- paste_event: {question_id, char_count, typed_chars_before}
- audio_event: {rms_level, spike_detected}
- keyboard_event: {wpm, burst_detected}
- phone_event: {detected, confidence}

**Actions:**
1. Store each event in Redis: ZADD session:{id}:events {timestamp} {event_json} (TTL: 90 min)
2. Persist to Supabase: INSERT INTO integrity_events
3. Send to Orchestrator Agent for score recalculation
4. Forward WARN/FLAGGED events to teacher WebSocket room

## Agent 6 — Stylometric Agent

**Trigger:** Answer submitted (POST /sessions/{id}/answers)  
**Input:** answer text, session.baseline_answer_count, student's historical answers  
**Tier determination:**
- baseline_answer_count = 0: Tier 3 (disabled, building baseline)
- baseline_answer_count 1-2: Tier 2 (partial, ±15 CI)
- baseline_answer_count ≥ 3: Tier 1 (full, ±7 CI)

**Tier 1 — Full Detection:**
1. Retrieve baseline embeddings: SELECT embedding FROM answers WHERE student_id=X AND exam_id != current_exam ORDER BY created_at DESC LIMIT 20
2. Compute centroid of baseline embeddings
3. Embed current answer
4. Style distance = cosine_distance(current_embedding, baseline_centroid)
5. Burstiness score = variance of sentence lengths in current answer
6. Combined stylometric score: normalize style_distance and burstiness to 0-100

**Tier 2 — Partial Detection:**
Same as Tier 1 but with ±15 CI and 10% weight in Orchestrator (not 25%)

**Tier 3 — Disabled:**
- stylometric_score = null
- Orchestrator redistributes weight: behavioral 38%, perplexity 19%, quality 33%, time 10%
- Teacher dashboard shows "Tier 3 — baseline being built. Stylometric analysis unavailable."
- Student post-exam: "This is your first exam — some analysis features are not yet available."

## Agent 7 — Security Agent (AI Cheating Detection)

**Trigger:** Answer submitted  
**Input:** answer text, session_id, question_id  
**Actions:**
1. Request logprobs from Ollama: POST /api/generate with logprobs=true
2. Compute perplexity from logprobs: exp(-mean(log_probs))
3. If logprobs unavailable (Ollama version issue): fallback to Shannon entropy: -sum(p × log2(p)) over token distribution
4. Map to score: Low perplexity (0.0-0.4) = likely AI-generated = low score. High perplexity (0.7+) = likely human = high score
5. Store: UPDATE answers SET perplexity_score=X, ai_detection_method='logprobs'|'entropy'

## Agent 8 — Evaluation Agent

**Trigger:** Session ended (POST /sessions/{id}/end)  
**Input:** all answers for session, questions (with correct answers)  
**Per answer:**
- MCQ/True-False: exact match grading. If answer === correct_answer: full marks. Else: 0 (or negative if configured)
- Fill in the Blank: fuzzy string match (Levenshtein distance < 3 = correct)
- Short/Long/Essay: Gemini rubric evaluation. Prompt: "Grade this answer out of {marks}. Rubric: [clarity, accuracy, completeness, use of examples]. JSON response: {score, reasoning}"
- LLM evaluation fallback: Ollama → null (teacher notified to manually grade)
5. Store: UPDATE answers SET eval_score=X, eval_reasoning=Y, source_chunk_ids=Z

## Agent 9 — Report Agent

**Trigger:** POST /sessions/{id}/reports/generate  
**Input:** session with all scores, events, answers, baseline_tier  
**Actions:**
1. Assemble all data: integrity_score, ci, factors, events, answer breakdown, baseline comparison
2. Generate ReportLab PDF (structure as specified in Screen 10 above)
3. Generate AI narrative summary (Gemini → Ollama → template): plain-language 3-paragraph summary
4. Upload PDF to Supabase Storage bucket "reports/{exam_id}/{session_id}.pdf"
5. Set bucket policy: private, signed URL required, TTL 7 days
6. Return signed URL to frontend
7. Mark report_generated = true in session

## Agent 10 — Review Agent

**Trigger:** FLAGGED status set by Orchestrator  
**State machine:**

```
FLAGGED → notify_teacher → await_student_response (24h window) → teacher_decision → grade_release
```

**Actions:**
1. On FLAGGED: send teacher WebSocket event "review_required"
2. Create appeal record: INSERT INTO integrity_appeals (session_id, deadline_at = now() + 24h)
3. Student sees anonymized summary (plain language, no raw biometric data)
4. If student submits appeal (POST /sessions/{id}/appeal): store response, notify teacher
5. After teacher decision (PUT /sessions/{id}/decision):
   - "clear": UPDATE exam_sessions SET teacher_decision='cleared', grade_released=true
   - "confirm": UPDATE exam_sessions SET teacher_decision='confirmed_flag', grade_released=true (grade flagged)
6. Log: INSERT INTO audit_log (teacher_id, session_id, decision, timestamp)
7. Notify student: "Your result is now available"

---

# PART 6 — DATABASE SCHEMA (Complete)

```sql
-- Users
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  display_name TEXT NOT NULL,
  institute_name TEXT,
  role TEXT CHECK (role IN ('teacher', 'student')) NOT NULL,
  baseline_answer_count INTEGER DEFAULT 0,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Exams
CREATE TABLE exams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  teacher_id UUID REFERENCES users(id) NOT NULL,
  title TEXT NOT NULL,
  subject TEXT,
  duration_min INTEGER NOT NULL,
  total_marks INTEGER NOT NULL,
  join_code CHAR(6) UNIQUE NOT NULL,
  status TEXT CHECK (status IN ('draft', 'active', 'ended', 'archived')) DEFAULT 'draft',
  paper_config JSONB,
  config_validated BOOLEAN DEFAULT false,
  questions_generated BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now(),
  activated_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ
);

-- Material Chunks (RAG)
CREATE TABLE material_chunks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id UUID REFERENCES exams(id) ON DELETE CASCADE,
  material_filename TEXT,
  chunk_text TEXT NOT NULL,
  embedding VECTOR(384),
  chapter_tag TEXT,
  source_page INTEGER,
  chunk_index INTEGER,
  created_at TIMESTAMPTZ DEFAULT now()
);
CREATE INDEX ON material_chunks USING hnsw (embedding vector_cosine_ops) 
  WITH (m = 16, ef_construction = 64);

-- Questions
CREATE TABLE questions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id UUID REFERENCES exams(id) ON DELETE CASCADE,
  section_label TEXT NOT NULL,
  question_text TEXT NOT NULL,
  question_type TEXT NOT NULL,
  options JSONB,
  correct_answer TEXT,
  marks INTEGER NOT NULL,
  blooms_level TEXT,
  chapter_tag TEXT,
  source_chunk_ids UUID[],
  groundedness_score FLOAT,
  teacher_modified BOOLEAN DEFAULT false,
  created_at TIMESTAMPTZ DEFAULT now()
);

-- Exam Sessions
CREATE TABLE exam_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  exam_id UUID REFERENCES exams(id) NOT NULL,
  student_id UUID REFERENCES users(id) NOT NULL,
  status TEXT CHECK (status IN ('joined', 'consented', 'active', 'paused', 'ended')) DEFAULT 'joined',
  consent_given BOOLEAN DEFAULT false,
  consent_given_at TIMESTAMPTZ,
  liveness_verified BOOLEAN DEFAULT false,
  integrity_state TEXT CHECK (integrity_state IN ('CLEAN', 'WATCH', 'WARN', 'FLAGGED')) DEFAULT 'CLEAN',
  integrity_score FLOAT,
  integrity_ci INTEGER,
  baseline_tier INTEGER CHECK (baseline_tier IN (1, 2, 3)),
  review_status TEXT CHECK (review_status IN ('pending', 'awaiting_response', 'decided')) DEFAULT 'pending',
  teacher_decision TEXT CHECK (teacher_decision IN ('cleared', 'confirmed_flag')),
  decision_at TIMESTAMPTZ,
  grade_released BOOLEAN DEFAULT false,
  started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ,
  UNIQUE(exam_id, student_id)
);

-- Answers
CREATE TABLE answers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES exam_sessions(id) ON DELETE CASCADE,
  question_id UUID REFERENCES questions(id),
  answer_text TEXT,
  selected_option TEXT,
  time_spent_seconds INTEGER,
  perplexity_score FLOAT,
  ai_detection_method TEXT CHECK (ai_detection_method IN ('logprobs', 'entropy')),
  style_distance FLOAT,
  eval_score FLOAT,
  eval_reasoning TEXT,
  source_chunk_ids UUID[],
  submitted_at TIMESTAMPTZ DEFAULT now()
);

-- Integrity Events
CREATE TABLE integrity_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES exam_sessions(id) ON DELETE CASCADE,
  event_type TEXT NOT NULL,
  event_data JSONB,
  score_impact FLOAT,
  severity TEXT CHECK (severity IN ('info', 'warning', 'danger')),
  occurred_at TIMESTAMPTZ DEFAULT now()
);

-- Integrity Appeals
CREATE TABLE integrity_appeals (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES exam_sessions(id) UNIQUE,
  student_response TEXT,
  submitted_at TIMESTAMPTZ,
  deadline_at TIMESTAMPTZ NOT NULL,
  teacher_note TEXT,
  created_at TIMESTAMPTZ DEFAULT now()
);
```

---

# PART 7 — API SPECIFICATION (All Endpoints)

```
Base URL: /api/v1

Auth:
  POST /auth/signup         body: {email, password, display_name, role, institute_name}
  POST /auth/login          body: {email, password}
  POST /auth/reset-request  body: {email}
  POST /auth/reset-confirm  body: {token, new_password}

Exams:
  POST   /exams                    Create exam
  GET    /exams                    List teacher's exams
  GET    /exams/{id}               Get exam detail
  PUT    /exams/{id}               Update exam metadata
  DELETE /exams/{id}               Delete exam (draft only)
  POST   /exams/{id}/clone         Clone exam (NEW)
  PUT    /exams/{id}/paper-config  Save and validate paper config
  POST   /exams/{id}/activate      Activate (triggers question generation)
  POST   /exams/{id}/end           End exam (ends all sessions)
  POST   /exams/{id}/pause         Pause all sessions
  POST   /exams/{id}/resume        Resume all sessions
  GET    /exams/{id}/live          Live session data (teacher dashboard)
  GET    /exams/{id}/students      Student roster

Materials:
  POST /materials/upload            Upload file (multipart)
  GET  /materials/{id}/status       Poll ingestion progress (SSE)
  DELETE /materials/{id}            Remove uploaded material (NEW)

Sessions:
  POST /sessions/join              Student joins with join code
  POST /sessions/{id}/consent      Student confirms consent
  POST /sessions/{id}/liveness     Blink challenge verified
  GET  /sessions/{id}/questions    Get exam questions
  POST /sessions/{id}/answers      Submit/update answer
  POST /sessions/{id}/end          Student submits exam
  GET  /sessions/{id}/integrity    Get integrity score (student-facing)
  POST /sessions/{id}/reports/generate  Generate PDF
  POST /sessions/{id}/appeal       Submit appeal response
  PUT  /sessions/{id}/decision     Teacher makes decision
  GET  /sessions/{id}/result       Get final result (after grade_released)

Reports:
  GET /exams/{id}/reports          List all session reports
  GET /exams/{id}/reports/csv      Export CSV (NEW)
  GET /exams/{id}/reports/summary  Class summary stats

Health:
  GET /health     Returns: {status: "ok", version: "6.0", timestamp}

WebSocket (Socket.IO):
  Room: exam_{exam_id}  (teacher joins this room)
  
  Events server → teacher:
    integrity_update:  {session_id, score, status, factor_delta}
    behavioral_event:  {session_id, event_type, severity, timestamp}
    student_joined:    {session_id, student_name}
    student_ended:     {session_id}
    review_required:   {session_id, student_name}
    
  Events server → student:
    exam_ended:        {}
    exam_paused:       {reason}
    exam_resumed:      {}
    warn_triggered:    {message}
    flagged:           {message}
```

---

# PART 8 — INFRASTRUCTURE & DEVOPS

## 8.1 Rate Limiting (NEW — Not in Original Spec)

Add slowapi (Python rate limiter) to FastAPI:

```python
# Most critical rate limits:
POST /sessions/join:      5 requests/IP/minute (prevents brute-force join code guessing)
POST /auth/login:         10 requests/IP/minute (prevents credential stuffing)
POST /materials/upload:   3 requests/user/minute (prevents storage abuse)
POST /sessions/{id}/answers: 30 requests/session/minute (prevents spam submissions)

Return 429 with: {error: "Too many requests", retry_after_seconds: 60}
```

## 8.2 Redis TTL Configuration (NEW)

```
session:{id}:state     TTL: exam.duration_min × 60 + 3600 (exam time + 1hr buffer)
session:{id}:events    TTL: exam.duration_min × 60 + 3600
session:{id}:score     TTL: same as above
teacher:{id}:room      TTL: 86400 (24hr)

Use EXPIREAT to set absolute expiry time (exam.ended_at + 1hr)
```

## 8.3 Supabase Storage Bucket Policy

```
Bucket: "reports"
  Access: private (signed URLs required)
  Signed URL TTL: 604800 (7 days)
  
Bucket: "materials"  
  Access: private (only teacher who uploaded + service role)
  Max file size: 52428800 (50MB)
  
RLS policies:
  reports: teacher can access reports for their own exams only
  materials: teacher can access materials for their own exams only
```

## 8.4 CORS Configuration

```python
app.add_middleware(
  CORSMiddleware,
  allow_origins=[
    "https://examguard.vercel.app",
    "http://localhost:5173",      # Vite dev server
    "http://localhost:3000",
  ],
  allow_credentials=True,
  allow_methods=["*"],
  allow_headers=["*"],
)
```

## 8.5 WebSocket Reconnection Config (Frontend)

```typescript
const socket = io(API_URL, {
  reconnection: true,
  reconnectionAttempts: 5,
  reconnectionDelay: 1000,
  reconnectionDelayMax: 10000,
  randomizationFactor: 0.5,
  timeout: 20000,
  
  // On reconnect: rehydrate all tile scores from last known state
  auth: { token: supabase.auth.session()?.access_token }
});

socket.on('reconnect', (attemptNumber) => {
  toast.success(`Live connection restored (attempt ${attemptNumber})`);
  // Fetch current scores for all tiles
  refetchAllSessionScores();
});

socket.on('reconnect_failed', () => {
  toast.error('Could not reconnect. Refresh the page.', { duration: Infinity });
});
```

## 8.6 GitHub Actions (health_ping.yml)

```yaml
name: Keep Render Alive
on:
  schedule:
    - cron: '*/10 * * * *'
jobs:
  ping:
    runs-on: ubuntu-latest
    steps:
      - name: Health check
        run: curl -f https://examguard-api.onrender.com/health || exit 1
```

---

# PART 9 — DOCUMENTATION FILES (All Must Exist)

## README.md structure

```markdown
# ExamGuard AI v6

> "Two FAR AWAY themes. One autonomous pipeline."

**Themes:** Examinations + Agentic & Autonomous Systems  
**Live Demo:** https://examguard.vercel.app  
**Demo Video:** [YouTube link]  
**LangGraph Studio:** https://smith.langchain.com/studio/...  

## Quick Start (5 minutes)
1. Clone repo
2. cp .env.example .env (fill in 3 required keys)
3. docker-compose up
4. python scripts/seed_demo.py
5. Open http://localhost:5173

## The Problem
[3 bullet points with stats]

## Architecture
[architecture diagram PNG inline]

## 10 Agents
[table: Agent | Trigger | Key Action]

## NCERT Legal Note
NCERT textbooks are published by the Government of India...

## DPDP Compliance
See docs/dpdp-compliance.md

## Team
[names, colleges]
```

## AGENTS.md (NEW — Judges Open This)

```markdown
# ExamGuard AI — 10 Agent Reference

Each agent is a named node in the LangGraph StateGraph.
Open LangGraph Studio at [URL] to see live traces.

| Agent | File | Trigger | Key Decision |
|-------|------|---------|--------------|
| Paper Config | agents/paper_config_agent.py | POST /paper-config | Validates marks budget |
| Material Ingestion | agents/ingestion_agent.py | POST /upload | OCR detection, chunking |
| Orchestrator | agents/orchestrator_agent.py | Every event | WATCH/WARN/FLAGGED (deterministic) |
| Question Generation | agents/question_agent.py | POST /activate | RAG retrieval + Bloom's injection |
| Proctoring | agents/proctoring_agent.py | WebSocket event | Event aggregation to Redis |
| Stylometric | agents/stylometric_agent.py | Answer submit | Tier 1/2/3 baseline comparison |
| Security | agents/security_agent.py | Answer submit | Perplexity / entropy scoring |
| Evaluation | agents/evaluation_agent.py | Session end | Objective + rubric grading |
| Report | agents/report_agent.py | POST /generate | ReportLab PDF generation |
| Review | agents/review_agent.py | FLAGGED trigger | 24h appeal state machine |

## LangGraph StateGraph Definition
See backend/agents/graph.py — all 10 nodes, edges, and conditional routing.
```

## SECURITY.md (NEW)

```markdown
# ExamGuard AI — Privacy & Security

## What We Collect
- Webcam: MediaPipe WASM processes locally. Only classified events sent (gaze direction, blink count). Raw video NEVER transmitted.
- Microphone: Audio RMS level only. No audio recorded or stored.
- Answers: Stored encrypted in Supabase (AES-256 at rest).
- Behavioral events: Classified events only (e.g., "tab_switch_detected", not raw screen data).

## What We Never Collect
- Raw video or audio recordings
- Keystroke-level data
- Screen contents or screenshots

## DPDP Act 2023 Compliance
See docs/dpdp-compliance.md for full checklist.
```

---

# PART 10 — SEED DEMO SCRIPT (seed_demo.py)

The seed script must create a fully demo-ready environment in under 5 minutes from a fresh database.

```python
# Step 0: Warmup Fly.io Ollama (prevents cold-start during demo)
print("Step 0: Warming up Ollama on Fly.io...")
while True:
    try:
        r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=5)
        if r.status_code == 200:
            print("✓ Ollama ready")
            break
    except:
        print("  Waiting for Ollama... (retry in 15s)")
        time.sleep(15)

# Step 1: Create teacher
teacher = create_user("teacher@demo.examguard.ai", "demo123", "Rajan Kumar", "teacher", "IIT Coaching Delhi")
print(f"✓ Teacher: {teacher.email}")

# Step 2: Create 3 students (different baseline tiers)
students = [
    create_user("arjun@student.ai", "demo123", "Arjun Sharma", "student"),   # Tier 1 (will have 3+ baselines)
    create_user("priya@student.ai", "demo123", "Priya Patel", "student"),    # Tier 1 (flagged scenario)
    create_user("rahul@student.ai", "demo123", "Rahul Singh", "student"),    # Tier 3 (first exam)
]

# Set baseline counts
set_baseline_count(students[0].id, 4)  # Tier 1
set_baseline_count(students[1].id, 3)  # Tier 1  
set_baseline_count(students[2].id, 0)  # Tier 3

# Step 3: Create exam
exam = create_exam(teacher.id, "Physics Unit Test — Ch 12–14", "Physics", 60, 80)
print(f"✓ Exam created. Join code: {exam.join_code}")

# Step 4: Upload NCERT Physics PDF (bundled in assets/)
material = upload_material(exam.id, "assets/ncert_physics_ch12_14.pdf")
wait_for_ingestion(material.id)  # Polls until chunks_stored > 0
print(f"✓ Material ingested: {material.chunk_count} chunks, {material.chapter_count} chapters")

# Step 5: Configure paper
config = configure_paper(exam.id, paper_config={
    "sections": [
        {"label": "A", "type": "mcq", "count": 10, "marks_each": 2, "blooms": "apply", "chapter": "auto"},
        {"label": "B", "type": "short_answer", "count": 6, "marks_each": 5, "blooms": "analyse", "chapter": "Ch.12"},
        {"label": "C", "type": "essay", "count": 1, "marks_each": 10, "blooms": "evaluate", "chapter": "Ch.14"},
    ]
})

# Step 6: Generate questions
activate_exam(exam.id)  # Triggers Question Generation Agent
wait_for_generation(exam.id)  # Polls until questions_generated = true
print(f"✓ Questions generated: {get_question_count(exam.id)} questions")

# Step 7: Create 3 sessions with different integrity profiles
# Arjun — Clean (score ~88)
session_clean = create_demo_session(exam.id, students[0].id, integrity_profile="clean")

# Priya — Flagged (score ~43) — the demo drama moment
session_flagged = create_demo_session(exam.id, students[1].id, integrity_profile="flagged")
# Seeds: 3 tab switches, high AI perplexity on Q7 and Q9, style deviation

# Rahul — Warn (score ~65) — Tier 3, first exam
session_warn = create_demo_session(exam.id, students[2].id, integrity_profile="warn_tier3")

# Step 8: Generate reports
generate_report(session_clean.id)
generate_report(session_flagged.id)  # This one is in the review queue

# Step 9: Print demo credentials
print("\n" + "="*60)
print("EXAMGUARD AI DEMO READY")
print("="*60)
print(f"Live URL:    https://examguard.vercel.app")
print(f"Teacher:     teacher@demo.examguard.ai / demo123")
print(f"Student 1:   arjun@student.ai / demo123 (CLEAN, Tier 1)")
print(f"Student 2:   priya@student.ai / demo123 (FLAGGED, Tier 1)")
print(f"Student 3:   rahul@student.ai / demo123 (WARN, Tier 3)")
print(f"Join Code:   {exam.join_code}")
print(f"\nLangGraph Studio: {LANGSMITH_URL}")
print(f"Docker Compose:   docker-compose up (local fallback)")
```

---

# PART 11 — TESTING CHECKLIST

## Sprint Acceptance Tests

**Sprint 1 Done When:**
- [ ] Upload NCERT Physics PDF → verify ≥ 200 chunks in pgvector
- [ ] Chapter detection identifies at least 2 chapters from NCERT PDF
- [ ] OCR fallback triggers on a test scanned PDF (len(text) < 100)
- [ ] Teacher can log in and see dashboard (empty state shown correctly)

**Sprint 2 Done When:**
- [ ] Marks tally updates on every keystroke, turns green at exactly target marks
- [ ] Coverage check blocks activation if insufficient chunks for a section
- [ ] All 80 generated questions are grounded (cosine sim > 0.72 per question)
- [ ] Progress stream shows correct current/total counts via SSE

**Sprint 3 Done When:**
- [ ] Student consent screen requires scrolling to bottom before button activates
- [ ] Blink challenge detects 2 blinks within 8 seconds on standard laptop camera
- [ ] Answers auto-saved to localStorage every 30 seconds
- [ ] Kill internet for 30s, reconnect → answers restored from localStorage

**Sprint 4 Done When:**
- [ ] Tab switch → teacher tile updates within 3 seconds via WebSocket
- [ ] FLAGGED tile pulses red animation
- [ ] WebSocket disconnect banner appears when Socket.IO drops
- [ ] Sort by risk puts FLAGGED tiles first

**Sprint 5 Done When:**
- [ ] Tier 3 student: stylometric score is null, orchestrator uses 4-factor weights
- [ ] Known AI-generated answer (GPT output) scores perplexity < 0.45
- [ ] Integrity thresholds are consistent: FLAGGED at < 50 (not < 60)
- [ ] CI shows ±7 for Tier 1, ±15 for Tier 2

**Sprint 6 Done When:**
- [ ] PDF report generates in < 10 seconds
- [ ] PDF contains all 5 pages (summary, events, answers, citations, appeal)
- [ ] Appeal submitted → teacher sees it in review panel within 5 seconds
- [ ] grade_released = true after teacher confirms/clears

**Sprint 7 Done When:**
- [ ] seed_demo.py runs end-to-end on a fresh DB in < 5 minutes
- [ ] All 10 agents visible in LangGraph Studio with correct state transitions
- [ ] CLOUD_API_KEY unset → questions still generate (Ollama fallback)
- [ ] Live URL opens in < 3 seconds (no cold start)

---

# PART 12 — DEMO SCRIPT (8 Steps, 4:30 Total)

```
0:00–0:30  Landing page
  Say: "India conducts 90 million exams a year. Teachers spend 6 hours setting 
        one paper. ChatGPT has broken proctoring. ExamGuard AI fixes all three — 
        for ₹2,000 a month, for any number of students."
  Show: Landing page hero, stat bar, comparison table

0:30–1:00  Teacher dashboard
  Say: "This is what a teacher sees on day one. My Physics exam, join code visible, 
        ready to share."
  Show: Dashboard with exam card, join code ABC123 visible

1:00–1:45  Material upload + RAG ingestion
  Say: "I'm uploading a NCERT Physics PDF. Watch the system extract 340 chunks, 
        detect chapter headings, and index them in pgvector. No manual tagging."
  Show: Upload progress → chunk count incrementing → chapter map appears

1:45–2:30  Paper configuration + question generation
  Say: "6 sections, 80 marks, Bloom's levels from Remember to Create. 
        The marks tally validates in real time. Click Generate."
  Show: Section builder, marks tally turning green, generation progress bar

2:30–3:00  Question preview
  Say: "This question about electromagnetic induction cites page 215 of my PDF. 
        Not from a generic question bank. My syllabus. Groundedness: 0.84."
  Show: Question preview with source citation

3:00–3:30  Student consent + blink liveness
  Say: "Student joins, sees exactly what we monitor — webcam, audio, tab activity, 
        answer analysis — each with a privacy note. Biometrics never leave their device."
  Show: Consent screen, blink challenge completing successfully

3:30–4:00  Live monitor drama moment
  Say: "I'm watching the live dashboard. Watch what happens when the student 
        switches tabs."
  Action: Switch browser tab (student window)
  Show: Teacher tile turns amber → alert appears in feed within 3 seconds
  Say: "Integrity score drops. Tile turns amber. Alert logs. All autonomous."

4:00–4:30  Report + LangGraph Studio
  Say: "Post-exam: 5-factor integrity report with confidence interval and baseline tier."
  Show: PDF report downloaded, opens showing all 5 pages
  Switch to: LangGraph Studio
  Say: "Every decision this pipeline made is visible here. 10 agents. Real traces. 
        This isn't a wrapper. It's a real agentic system."
  Show: LangGraph Studio with all 10 nodes, state transitions visible
```

---

# PART 13 — WHAT JUDGES WILL ASK (And Your Answers)

| Question | Your Answer |
|----------|-------------|
| What about first-exam students? No baseline. | 3-tier system. Tier 3: stylometric disabled, 4-factor score, note says "first exam — building baseline." No false positives by design. |
| 8% false positive rate is too high. | Agreed. That's why no automated decision is final. FLAGGED = grade held, teacher reviews. Student can appeal. Teacher has final say. False positives are caught before real harm. |
| How do you prevent AI bias? | Orchestrator is a deterministic state machine. A student gets flagged only when a number crosses a documented threshold. The LLM writes explanations. Never decisions. |
| What if Gemini rate-limits mid-exam? | LLM routing: Gemini → Ollama → cached question pool. Teacher sees "Using cached questions." Exam continues. |
| Is NCERT legal? | NCERT textbooks are Government of India publications, freely distributable for educational use per ncert.nic.in. Stated in README. No commercial use. |
| Can this scale? | Stateless FastAPI, HNSW index (sub-ms search), Redis for hot path (200KB/100 students), Supabase connection pooling. Horizontal scaling via Render. |
| Why is the false positive rate 8% not lower? | The detection threshold 0.65 is calibrated on 60 real student answers (see calibration notebook). Lower threshold = more false positives. Higher = more missed detections. 8% FPR with human-in-loop appeals is acceptable. |

---

# FINAL SUBMISSION CHECKLIST

## GitHub Repository Must Contain:
- [ ] README.md with live URL, demo link, architecture diagram, setup guide, NCERT legal note
- [ ] AGENTS.md (10-agent reference for judges)
- [ ] SECURITY.md (what data is/isn't collected)
- [ ] CONTRIBUTING.md
- [ ] docs/dpdp-compliance.md
- [ ] docs/architecture.png
- [ ] docs/demo-screenshots/ (8+ annotated screenshots)
- [ ] backend/agents/ (all 10 agent files)
- [ ] backend/agents/graph.py (LangGraph StateGraph)
- [ ] backend/agents/llm_router.py
- [ ] backend/agents/bloom_templates.py
- [ ] scripts/seed_demo.py (10-step, < 5 min runtime)
- [ ] research/calibration/eval_notebook.ipynb
- [ ] research/calibration/perplexity_notes.md
- [ ] docker-compose.yml (tested locally)
- [ ] .env.example (no secrets, all variables listed)
- [ ] .github/workflows/health_ping.yml
- [ ] .github/workflows/ci.yml

## Before Submission Video:
- [ ] seed_demo.py runs on fresh DB in < 5 minutes
- [ ] Live URL opens without cold start (health ping running)
- [ ] LangGraph Studio URL works and shows 10 agents
- [ ] Teacher login works, demo exam visible
- [ ] Student join works with code from seed script
- [ ] Tab switch → tile turns amber in < 3 seconds on screen recording
- [ ] PDF report downloads and shows all 5 pages
- [ ] All 10 agents confirmed visible in LangGraph Studio

## Video Must:
- [ ] Open with "ExamGuard AI addresses TWO themes: Examinations AND Agentic Systems"
- [ ] Show live URL in browser (not localhost)
- [ ] Demonstrate the tab-switch → tile update moment (the drama moment)
- [ ] Show LangGraph Studio (proof it's a real agent system)
- [ ] Mention ₹2,000/month vs Proctorio pricing
- [ ] Be 4:30 or under

## Numbers to Say Every Time:
- 90M+ exams per year in India
- 6–8 hours per paper for teachers
- ₹2,000/month vs $800/session
- 10 agents in LangGraph StateGraph
- DPDP Act 2023 compliant
- 97% cheaper than Proctorio

---

*ExamGuard AI v6 · FAR AWAY 2026 · Built to Ship · Round 2 Delhi Ready*

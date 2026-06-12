# Complete Screen Specifications: Review, Reports, Settings

## Screen 9 - Teacher Review

### Primary workflow

- Risk-sorted queue with status, score, tier, appeal state, and deadline.
- Selecting a student opens integrity evidence and appeal side by side.
- Teacher note is mandatory before clear or confirm.
- Expired unanswered appeals show `No response received`; they remain undecided.
- Decisions write an audit entry and release/hold grade according to policy.

### States

- Loading: stable skeleton rows and evidence panel.
- Empty: no cases require review; link back to live monitor/reports.
- Error: preserve selected case and allow retry.
- Stale data: show last sync time and reconnect action.
- Mobile: queue becomes a top sheet; evidence and appeal stack vertically.

### Language

- Never say `caught cheating` before teacher decision.
- Use `requires review`, `integrity signal`, and `student response`.
- Status always includes text/icon, never color alone.

## Screen 10 - Reports And Downloads

### Primary workflow

- Class summary, distribution, median, flagged count, and report readiness.
- Per-student row provides PDF generation/retry and decision state.
- CSV and batch ZIP actions show progress and completion/failure notifications.
- Reports remain unavailable until the exam ends.

### States

- Loading: summary/chart/table skeletons with fixed dimensions.
- Empty active exam: countdown and link to live monitor.
- Partial failure: failed row keeps retry action without blocking other downloads.
- No students: clear empty state, no zero-value fake analytics.
- Mobile: summary cards stack; table becomes labeled rows, not horizontal clipping.

### Accessibility

- Charts require text summaries and accessible labels.
- Download buttons include student names in aria labels.
- Print/PDF colors remain distinguishable in grayscale.

## Screen 11 - Account Settings And Password Reset

### Account settings

- Display name, institute, email-notification preference.
- Dirty-state indicator and unsaved-changes confirmation.
- Field-level validation and backend error mapping.

### Password reset

- Request flow never reveals whether an email exists.
- Reset token validation, expiration state, and resend action.
- Password requires minimum length, uppercase, number, and confirmation match.
- Demo password is explicitly labeled demo-only.

### States And Mobile

- Loading preserves form layout.
- Success is announced to assistive technology.
- Session expiry returns to Home without losing non-sensitive draft settings.
- Mobile uses one column and 48px minimum controls.

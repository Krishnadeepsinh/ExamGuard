# ExamGuard AI - Privacy and Security

## What We Collect

- Webcam: MediaPipe WASM processes frames locally. Only classified events are sent.
- Microphone: RMS amplitude level only. No audio is recorded or stored.
- Answer text: stored for grading, AI-writing checks, and appeals.
- Behavioral events: classified events such as `tab_switch` or `gaze_away`.

## What We Never Collect

- Raw video
- Raw audio
- Screen contents
- Screenshots
- Keystroke-level surveillance

## Controls

- Explicit consent before monitoring starts.
- Row-level security for teacher/student isolation.
- Private storage buckets with signed URLs.
- API secrets only through environment variables.
- Rate limiting on public join and auth endpoints.

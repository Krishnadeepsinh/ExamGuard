import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

// English translations – extend this file when adding other languages
const en = {
  translation: {
    // App / branding
    'ExamGuard AI': 'ExamGuard AI',
    'Exam integrity platform': 'Exam integrity platform',
    'Creates, monitors, scores, and reviews exams.': 'Creates, monitors, scores, and reviews exams.',
    'Syllabus-based exam integrity platform': 'Syllabus-based exam integrity platform',
    'Privacy-first exam platform for institutes': 'Privacy-first exam platform for institutes',
    'ExamGuard v6.0': 'ExamGuard v6.0',

    // Auth / Landing
    'Teacher Portal': 'Teacher Portal',
    'Student Portal': 'Student Portal',
    'Teacher Email': 'Teacher Email',
    Password: 'Password',
    'Student Name': 'Student Name',
    'Join Code': 'Join Code',
    'Optional Email': 'Optional Email',
    'Teacher:': 'Teacher:',
    'Student:': 'Student:',

    // Dashboard
    'Total Exams': 'Total Exams',
    'Active Students': 'Active Students',
    'Flagged Cases': 'Flagged Cases',
    'Class Avg Integrity': 'Class Avg Integrity',
    'Create exam': 'Create exam',
    'Try sample class': 'Try sample class',
    'Open Live Monitor': 'Open Live Monitor',
    Configure: 'Configure',
    'Exam Title': 'Exam Title',
    Subject: 'Subject',
    Status: 'Status',
    Actions: 'Actions',
    Monitor: 'Monitor',
    Setup: 'Setup',

    // Create exam modal
    'Specify details below. This creates a grounded code room students can join.':
      'Specify details below. This creates a grounded code room students can join.',
    'Duration (minutes)': 'Duration (minutes)',
    'Total Marks': 'Total Marks',
    Cancel: 'Cancel',
    'Create Exam': 'Create Exam',

    // Config
    'Test OCR failure state': 'Test OCR failure state',
    'Remove Material': 'Remove Material',
    'Total Exam Marks': 'Total Exam Marks',
    'Overall Level': 'Overall Level',
    Easy: 'Easy',
    Standard: 'Standard',
    Challenging: 'Challenging',
    'Paper Type': 'Paper Type',
    'MCQ only': 'MCQ only',
    'MCQ + QA': 'MCQ + QA',
    Mixed: 'Mixed',
    'Groundedness 0.84': 'Groundedness 0.84',
    "Explain the working principle of a transformer using Faraday's law of electromagnetic induction.":
      "Explain the working principle of a transformer using Faraday's law of electromagnetic induction.",
    'Source: ': 'Source: ',
    'Section ': 'Section ',
    'Total exam marks must be between 10 and 300.': 'Total exam marks must be between 10 and 300.',
    'Sections do not match selected paper type.': 'Sections do not match selected paper type.',
    'Some sections exceed available chapter coverage.': 'Some sections exceed available chapter coverage.',
    'Generate Paper': 'Generate Paper',

    // Live monitor
    'Live connection active (polling mode)': 'Live connection active (polling mode)',
    'Sort by risk': 'Sort by risk',
    'Sort by name': 'Sort by name',
    'Sort by join time': 'Sort by join time',

    // Consent
    'Before your exam starts': 'Before your exam starts',
    'ExamGuard shows exactly what is monitored. No raw webcam or audio leaves your device.':
      'ExamGuard shows exactly what is monitored. No raw webcam or audio leaves your device.',
    'I Consent': 'I Consent',
    'Scroll all terms to unlock the consent button.': 'Scroll all terms to unlock the consent button.',

    // Liveness
    'Looking for face...': 'Looking for face...',
    'Blink twice to begin liveness check': 'Blink twice to begin liveness check',
    'Position your face in the oval. 2 blinks must be detected within 8 seconds.':
      'Position your face in the oval. 2 blinks must be detected within 8 seconds.',
    'Low-light Fallback': 'Low-light Fallback',
    'EAR threshold: below 0.25. Blink twice to proceed.': 'EAR threshold: below 0.25. Blink twice to proceed.',

    // Exam session
    'Physics XI - Electromagnetism': 'Physics XI - Electromagnetism',
    'Answered ': 'Answered ',
    'Submit Exam': 'Submit Exam',
    'Question ': 'Question ',
    'Source citation after generation: NCERT Physics ': 'Source citation after generation: NCERT Physics ',
  },
}

i18n.use(initReactI18next).init({
  resources: { en },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export default i18n

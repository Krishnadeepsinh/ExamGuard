from __future__ import annotations

import unittest

from backend.agents.constants import status_for_score
from backend.agents.orchestrator_agent import compute_integrity_score
from backend.agents.review_agent import expire_appeal_without_response
from backend.agents.paper_config_agent import validate_paper_config
from backend.agents.graph import AGENT_NODES, run_workflow
from backend.agents.evaluation_agent import grade_objective, grade_subjective
from backend.store import LocalStore
from backend.main import ProctoringEventRequest, student_safe_question
from backend.agents.llm_router import question_quality_errors
from pydantic import ValidationError


class IntegrityPolicyTests(unittest.TestCase):
    def test_question_quality_rejects_source_leaks_and_bad_mcq(self) -> None:
        errors = question_quality_errors({
            "text": "According to the material, choose",
            "options": ["A", "A", "B"],
            "correct_answer": "C",
        }, "MCQ")
        self.assertTrue(errors)

    def test_proctoring_event_allowlist_rejects_forged_type(self) -> None:
        with self.assertRaises(ValidationError):
            ProctoringEventRequest(event_type="set_score_to_zero", metadata={})

    def test_objective_and_subjective_grading_are_bounded(self) -> None:
        self.assertEqual(grade_objective("SELECT", "SELECT", 2)["score"], 2)
        subjective = grade_subjective("A transaction uses commit and rollback for atomic changes", "commit rollback atomic transaction", 5)
        self.assertGreater(subjective["score"], 0)
        self.assertLessEqual(subjective["score"], 5)
    def test_threshold_boundaries(self) -> None:
        self.assertEqual(status_for_score(85.01).value, "CLEAN")
        self.assertEqual(status_for_score(85).value, "WATCH")
        self.assertEqual(status_for_score(70).value, "WATCH")
        self.assertEqual(status_for_score(69.99).value, "WARN")
        self.assertEqual(status_for_score(50).value, "WARN")
        self.assertEqual(status_for_score(49.99).value, "FLAGGED")

    def test_tier_two_is_partial_not_full_weighting(self) -> None:
        factors = {
            "behavioral": 80,
            "perplexity": 70,
            "stylometric": 20,
            "answer_quality": 75,
            "time_anomaly": 90,
        }
        tier_one = compute_integrity_score(factors, 1)
        tier_two = compute_integrity_score(factors, 2)
        self.assertNotEqual(tier_one["score"], tier_two["score"])
        self.assertEqual(tier_two["ci"], 15)

    def test_tier_three_has_no_confidence_interval(self) -> None:
        factors = {
            "behavioral": 68,
            "perplexity": 59,
            "stylometric": 0,
            "answer_quality": 72,
            "time_anomaly": 60,
        }
        result = compute_integrity_score(factors, 3)
        self.assertIsNone(result["ci"])
        self.assertEqual(result["status"], "WARN")

    def test_expired_appeal_never_auto_confirms(self) -> None:
        result = expire_appeal_without_response("session-1", "teacher-1")
        self.assertEqual(result["appeal_status"], "expired_no_response")
        self.assertEqual(result["review_status"], "awaiting_teacher_decision")
        self.assertFalse(result["grade_released"])
        self.assertNotIn("teacher_decision", result)


class StoreBehaviorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = LocalStore()
        self.store.users["teacher-demo"] = {
            "id": "teacher-demo", "email": "teacher@example.test", "display_name": "Test Teacher",
            "role": "teacher", "institute": "Test Institute", "baseline_answer_count": 0,
        }
        self.store.exams["exam-physics"] = {
            "id": "exam-physics", "teacher_id": "teacher-demo", "title": "Test Exam", "subject": "Test Subject",
            "duration_minutes": 60, "total_marks": 80, "join_code": "PHY001", "status": "draft",
            "paper_config": {}, "activated_at": None, "ended_at": None, "created_at": "2026-01-01T00:00:00+00:00",
        }
        source = ("Chapter 1 Fundamentals explains definitions, examples, applications, and evaluation methods. ") * 100
        self.store.add_material("exam-physics", "fixture.txt", source.encode("utf-8"))

    def test_clone_gets_new_code_and_no_sessions(self) -> None:
        source = self.store.exams["exam-physics"]
        clone = self.store.clone_exam(source["id"])
        self.assertEqual(clone["status"], "draft")
        self.assertNotEqual(clone["join_code"], source["join_code"])
        self.assertFalse(any(session["exam_id"] == clone["id"] for session in self.store.sessions.values()))

    def test_answer_save_is_upsert(self) -> None:
        self.store.exams["exam-physics"]["status"] = "active"
        session = self.store.join_session("PHY001", "Arjun Sharma", "arjun@student.ai")
        first = self.store.save_answer(session["id"], {"question_id": "q1", "answer_text": "first"})
        second = self.store.save_answer(session["id"], {"question_id": "q1", "answer_text": "latest"})
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.answers[session["id"]]), 1)
        self.assertEqual(second["answer_text"], "latest")

    def test_answer_retry_with_same_idempotency_key_is_not_duplicated(self) -> None:
        self.store.exams["exam-physics"]["status"] = "active"
        session = self.store.join_session("PHY001", "Retry Student", "retry@student.ai")
        payload = {"question_id": "q1", "answer_text": "stable", "idempotency_key": "retry-key-123"}
        first = self.store.save_answer(session["id"], payload)
        second = self.store.save_answer(session["id"], payload)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(len(self.store.answers[session["id"]]), 1)

    def test_activation_captures_immutable_paper_snapshot(self) -> None:
        self.store.questions["exam-physics"] = [{"id": "q1", "text": "What is SQL?", "marks": 2}]
        activated = self.store.activate_exam("exam-physics")
        self.assertEqual(activated["paper_version"], 1)
        self.assertEqual(activated["paper_snapshot"]["questions"][0]["id"], "q1")
        with self.assertRaisesRegex(ValueError, "immutable"):
            self.store.generate_questions("exam-physics")

    def test_integrity_events_form_hash_chain(self) -> None:
        self.store.exams["exam-physics"]["status"] = "active"
        session = self.store.join_session("PHY001", "Chain Student", "chain@student.ai")
        first = self.store.log_integrity_event(session["id"], "tab_hidden", {})
        second = self.store.log_integrity_event(session["id"], "window_blur", {})
        self.assertEqual(first["sequence_number"], 1)
        self.assertEqual(second["sequence_number"], 2)
        self.assertEqual(second["previous_hash"], first["event_hash"])
        self.assertEqual(len(second["event_hash"]), 64)

    def test_generation_requires_uploaded_material(self) -> None:
        exam = self.store.create_exam("teacher-demo", {
            "title": "No Material Exam", "subject": "SQL", "duration_minutes": 60, "total_marks": 10,
        })
        exam["paper_config"] = {"material_id": None, "overall_level": "Standard", "sections": []}
        with self.assertRaisesRegex(ValueError, "Upload syllabus"):
            self.store.generate_questions(exam["id"])

    def test_activation_rejects_empty_generated_paper(self) -> None:
        exam = self.store.create_exam("teacher-demo", {
            "title": "Empty Paper", "subject": "SQL", "duration_minutes": 60, "total_marks": 10,
        })
        self.store.questions[exam["id"]] = []
        with self.assertRaisesRegex(ValueError, "generate questions"):
            self.store.activate_exam(exam["id"])

    def test_syllabus_and_material_are_kept_as_distinct_sources(self) -> None:
        exam = self.store.create_exam("teacher-demo", {
            "title": "Combined Sources", "subject": "SQL", "duration_minutes": 60, "total_marks": 10,
        })
        syllabus = self.store.add_material(exam["id"], "syllabus.txt", b"SQL syllabus covers SELECT queries, joins, grouping, filtering, constraints, normalization, transactions, indexes, views, security, and database design concepts for learners.", "syllabus")
        material = self.store.add_material(exam["id"], "notes.txt", b"SQL SELECT retrieves rows. JOIN combines related tables. GROUP BY aggregates values. WHERE filters rows. Transactions use commit and rollback. Indexes improve lookup performance in relational databases.", "material")
        self.assertEqual(self.store.get_material(syllabus["id"])["source_type"], "syllabus")
        self.assertEqual(self.store.get_material(material["id"])["source_type"], "material")

    def test_paper_config_rejects_missing_material(self) -> None:
        result = validate_paper_config({
            "material_id": None, "total_marks": 10, "paper_mode": "MCQ only", "overall_level": "Standard",
            "sections": [{"type": "MCQ", "count": 5, "marks_each": 2, "chapter_tag": "SQL", "level": "Standard"}],
        }, {"SQL": 10})
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("Upload syllabus" in error for error in result["errors"]))

    def test_paper_config_rejects_more_than_fifty_questions(self) -> None:
        result = validate_paper_config({
            "material_id": "material-1", "total_marks": 102, "paper_mode": "MCQ only", "overall_level": "Standard",
            "sections": [{"type": "MCQ", "count": 51, "marks_each": 2, "chapter_tag": "SQL", "level": "Standard"}],
        }, {"SQL": 1})
        self.assertEqual(result["status"], "invalid")
        self.assertTrue(any("maximum supported" in error for error in result["errors"]))

    def test_end_exam_finalizes_active_sessions(self) -> None:
        self.store.exams["exam-physics"]["status"] = "active"
        session = self.store.join_session("PHY001", "End Test", "end@test.example")
        self.store.end_exam("exam-physics")
        self.assertEqual(self.store.exams["exam-physics"]["status"], "ended")
        self.assertEqual(self.store.sessions[session["id"]]["status"], "ended")

    def test_langgraph_flagged_route_includes_review(self) -> None:
        result = run_workflow("proctor", {"event": "tab_hidden"}, "FLAGGED")
        self.assertEqual(result["completed_agents"], [
            "proctoring_agent", "orchestrator_agent", "review_agent", "report_agent",
        ])

    def test_all_ten_agent_stages_are_reachable(self) -> None:
        completed: set[str] = set()
        for workflow in ("ingest", "generate", "proctor", "answer", "finish"):
            completed.update(run_workflow(workflow, {}, "FLAGGED")["completed_agents"])
        self.assertEqual(completed, set(AGENT_NODES))

    def test_proctoring_events_change_integrity_status(self) -> None:
        self.store.exams["exam-physics"]["status"] = "active"
        session = self.store.join_session("PHY001", "Risk Student", "risk@student.ai")
        initial = session["integrity"]["score"]
        self.store.log_integrity_event(session["id"], "tab_hidden", {})
        self.store.log_integrity_event(session["id"], "window_blur", {})
        updated = self.store.sessions[session["id"]]["integrity"]
        self.assertLess(updated["score"], initial)
        self.assertNotEqual(updated["status"], "FLAGGED")

    def test_multi_vector_cheating_pattern_is_flagged(self) -> None:
        self.store.exams["exam-physics"]["status"] = "active"
        session = self.store.join_session("PHY001", "Pattern Student", "pattern@student.ai")
        for event, metadata in (
            ("tab_hidden", {}), ("tab_hidden", {}), ("tab_hidden", {}),
            ("paste_detected", {"bulk_paste": True}), ("fullscreen_exit", {}),
        ):
            self.store.log_integrity_event(session["id"], event, metadata)
        updated = self.store.sessions[session["id"]]["integrity"]
        self.assertEqual(updated["status"], "FLAGGED")
        self.assertLess(updated["score"], 50)

    def test_grade_is_hidden_until_teacher_releases_result(self) -> None:
        self.store.exams["exam-physics"]["status"] = "active"
        self.store.questions["exam-physics"] = [{
            "id": "grade-q1", "exam_id": "exam-physics", "type": "MCQ", "correct_answer": "Correct",
            "marks": 2, "text": "Choose", "options": ["Correct", "Wrong", "Other", "None"],
        }]
        session = self.store.join_session("PHY001", "Grade Student", "grade@student.ai")
        self.store.save_answer(session["id"], {"question_id": "grade-q1", "answer_text": "Correct", "selected_option": "Correct"})
        self.store.evaluate_session(session["id"])
        self.assertIsNone(self.store.get_session_result(session["id"])["grade"])
        self.store.teacher_decision(session["id"], "clear", "Reviewed and approved")
        result = self.store.get_session_result(session["id"])
        self.assertEqual(result["grade"]["earned_marks"], 2)
        self.assertTrue(result["grade_released"])

    def test_student_question_endpoint_never_exposes_answer_key(self) -> None:
        result = student_safe_question({"id": "q1", "text": "Question", "correct_answer": "Secret", "source_chunk_ids": ["chunk-1"]})
        self.assertNotIn("correct_answer", result)
        self.assertNotIn("source_chunk_ids", result)


if __name__ == "__main__":
    unittest.main()

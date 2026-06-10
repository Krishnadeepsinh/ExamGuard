"""Bloom taxonomy prompt templates used by the Question Generation Agent."""

BLOOM_TEMPLATES = {
    "Remember": "Generate recall questions that ask students to identify, define, list, or state facts directly grounded in the provided context.",
    "Understand": "Generate comprehension questions that ask students to explain concepts in their own words using the provided context.",
    "Apply": "Generate application questions where students use a concept from the context to solve a familiar numerical or conceptual problem.",
    "Analyze": "Generate analysis questions that require comparing mechanisms, explaining cause and effect, or decomposing a process from the context.",
    "Evaluate": "Generate evaluation questions that ask students to justify a claim, critique an explanation, or choose the best method using evidence from the context.",
    "Create": "Generate synthesis questions that ask students to design, propose, or construct an answer using multiple ideas from the context.",
}


QUESTION_TYPE_SUFFIX = {
    "MCQ": "Return options A-D and a single correct option.",
    "True/False": "Return a true/false statement and the correct boolean answer.",
    "Short Answer": "Return a concise question answerable in 3-5 sentences.",
    "Long Answer": "Return a deeper question answerable in structured paragraphs.",
    "Essay": "Return an open-ended essay prompt with a short grading rubric.",
}

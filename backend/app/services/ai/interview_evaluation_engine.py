import ast
import json
import re
from typing import Any, Optional

from app.core.logging import logger
from app.models.interview_prep import InterviewQuestion
from app.services.ai.factory import get_ai_provider

EVALUATION_SYSTEM_INSTRUCTION = """You are Nexora's Principal Technical Interview Evaluator.
Your objective is to evaluate a candidate's submitted answer to an interview question
with rigor, fairness, and actionable guidance.

EVALUATION RUBRIC & SCORING DIMENSIONS (Each 0.0 to 100.0):
1. technical_correctness_score: Accuracy of technical concepts, algorithms, APIs, or design.
2. relevance_score: How directly the answer addresses the prompt without extraneous tangents.
3. completeness_score: Coverage of expected key technical points and edge cases.
4. clarity_score: Structure, logical flow, and absence of jargon confusion.
5. approach_score: Problem-solving methodology, trade-off awareness, and systematic design.
6. communication_score: Conciseness, professional tone, and articulated reasoning.

overall_score: Weighted average:
  overall_score = 0.30 * correctness + 0.20 * relevance + 0.20 * completeness
                + 0.10 * clarity + 0.10 * approach + 0.10 * communication

STRICT SECURITY INVARIANTS:
1. SAFE CODE EVALUATION: If the candidate submitted code, evaluate it strictly
   statically for syntax, logic, edge cases, and time/space complexity.
   NEVER execute arbitrary code.
2. OBJECTIVE GROUNDING: Base evaluation strictly on the candidate's actual submission
   against expected points. Do not penalize undisclosed facts outside the question scope.
3. CONSTRUCTIVE FEEDBACK: Provide concrete strengths, explicit missing points,
   actionable improvements, and a realistic stronger answer example.
4. OUTPUT FORMAT: Return strictly valid JSON conforming to the requested schema.
"""


class SafeStaticCodeAnalyzer:
    """Performs static verification on submitted code snippets without server execution."""

    @classmethod
    def analyze_python_code(cls, code_snippet: str) -> dict[str, Any]:
        """Verify Python code statically using AST parsing."""
        if not code_snippet or not code_snippet.strip():
            return {"valid_syntax": False, "complexity_hint": "No code provided", "issues": []}

        try:
            tree = ast.parse(code_snippet)
            functions = [node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)]
            has_loops = any(isinstance(node, (ast.For, ast.While)) for node in ast.walk(tree))
            has_recursion = any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in functions
                for node in ast.walk(tree)
            )

            complexity = (
                "O(N) or higher (contains loops)" if has_loops else "O(1) (direct operations)"
            )
            if has_recursion:
                complexity += " with recursive stack depth"

            return {
                "valid_syntax": True,
                "complexity_hint": complexity,
                "functions_defined": functions,
                "issues": [],
            }
        except SyntaxError as exc:
            return {
                "valid_syntax": False,
                "complexity_hint": "Syntax Error",
                "issues": [f"Syntax error at line {exc.lineno}: {exc.msg}"],
            }
        except Exception as exc:
            return {
                "valid_syntax": False,
                "complexity_hint": "Parse Error",
                "issues": [f"Code parse issue: {str(exc)}"],
            }


class DeterministicEvaluationEngine:
    """Evaluates answers deterministically based on keyword coverage, length, and rubric."""

    @classmethod
    def evaluate(
        cls,
        question: InterviewQuestion,
        answer_text: str,
        submitted_code: Optional[str] = None,
        submitted_language: Optional[str] = None,
    ) -> dict[str, Any]:
        expected = question.expected_points or []
        lower_ans = answer_text.lower()

        # Keyword matching against expected points
        covered_points = []
        missing_points = []

        stop_words = {
            "this",
            "that",
            "with",
            "from",
            "when",
            "into",
            "uses",
            "must",
            "they",
            "will",
        }

        for pt in expected:
            pt_keywords = [
                w.lower()
                for w in re.findall(r"\b[A-Za-z0-9_-]{4,}\b", pt)
                if w.lower() not in stop_words
            ]
            matches = sum(1 for kw in pt_keywords if kw in lower_ans)
            if matches >= max(1, len(pt_keywords) // 3):
                covered_points.append(pt)
            else:
                missing_points.append(pt)

        coverage_ratio = len(covered_points) / max(1, len(expected))
        word_count = len(answer_text.split())

        # Scoring heuristics
        if word_count < 15:
            correctness = min(40.0, coverage_ratio * 50.0 + 10.0)
            relevance = 60.0 if word_count > 5 else 20.0
            completeness = max(15.0, coverage_ratio * 40.0)
            clarity = 50.0
            approach = 30.0
            communication = 40.0
        elif word_count < 40:
            correctness = min(75.0, coverage_ratio * 70.0 + 20.0)
            relevance = 80.0
            completeness = max(35.0, coverage_ratio * 65.0)
            clarity = 70.0
            approach = 60.0
            communication = 65.0
        else:
            correctness = min(95.0, coverage_ratio * 60.0 + 35.0)
            relevance = 85.0
            completeness = max(50.0, coverage_ratio * 50.0 + 40.0)
            clarity = 85.0
            approach = 80.0
            communication = 85.0

        # Adjust for static code analysis if code submitted
        code_bonus = 0.0
        if submitted_code:
            code_eval = SafeStaticCodeAnalyzer.analyze_python_code(submitted_code)
            if code_eval["valid_syntax"]:
                correctness = min(100.0, correctness + 5.0)
                approach = min(100.0, approach + 5.0)
                code_bonus = 3.0
            else:
                correctness = max(20.0, correctness - 15.0)
                missing_points.append(
                    f"Submitted code contained syntax issues: {', '.join(code_eval['issues'])}"
                )

        overall = (
            0.30 * correctness
            + 0.20 * relevance
            + 0.20 * completeness
            + 0.10 * clarity
            + 0.10 * approach
            + 0.10 * communication
            + code_bonus
        )
        overall = max(10.0, min(98.0, round(overall, 1)))

        strengths = []
        if covered_points:
            strengths.append(
                f"Successfully addressed {len(covered_points)} key conceptual point(s) from rubric."
            )
        if word_count >= 40:
            strengths.append(
                "Provided a thorough, structured explanation with descriptive technical context."
            )
        if submitted_code:
            strengths.append("Demonstrated code implementation to support theoretical explanation.")
        if not strengths:
            strengths.append("Initiated an answer touching on core role topics.")

        suggested_improvements = []
        if missing_points:
            suggested_improvements.append(f"Deepen coverage on: {missing_points[0]}.")
        suggested_improvements.append(
            "State time/space complexity trade-offs upfront and provide a concrete example."
        )

        expected_lead = ", ".join(expected[:2]) if expected else "core requirements"
        stronger_answer = (
            f"A stronger response would open with a precise definition, explicitly hit the "
            f"key points ({expected_lead}), and conclude with an architectural trade-off "
            f"or personal project example demonstrating real-world production application."
        )

        feedback = (
            f"Answer scored {overall}/100. "
            f"Your explanation demonstrated {round(correctness, 1)}% technical correctness. "
            f"To improve, explicitly cover missing trade-offs and structural corner cases."
        )

        return {
            "overall_score": overall,
            "technical_correctness_score": round(correctness, 1),
            "relevance_score": round(relevance, 1),
            "completeness_score": round(completeness, 1),
            "clarity_score": round(clarity, 1),
            "approach_score": round(approach, 1),
            "communication_score": round(communication, 1),
            "strengths": strengths,
            "missing_points": missing_points or ["No critical omissions detected."],
            "suggested_improvements": suggested_improvements,
            "stronger_answer_example": stronger_answer,
            "evaluation_feedback": feedback,
        }


class InterviewEvaluationEngine:
    """Evaluates candidate answers via AI provider with fallback."""

    @classmethod
    def _invoke_provider(cls, provider: Any, prompt: str) -> Optional[str]:
        """Invoke underlying provider client with structured prompt."""
        if provider.name == "gemini":
            client = getattr(provider, "client", None)
            if client:
                response = client.models.generate_content(
                    model=provider.model_name,
                    contents=prompt,
                    config={
                        "system_instruction": EVALUATION_SYSTEM_INSTRUCTION,
                        "temperature": 0.2,
                        "response_mime_type": "application/json",
                    },
                )
                raw_text = getattr(response, "text", None)
                return str(raw_text) if raw_text else None
        elif provider.name == "openai":
            client = getattr(provider, "client", None)
            if client:
                response = client.chat.completions.create(
                    model=provider.model_name,
                    messages=[
                        {"role": "system", "content": EVALUATION_SYSTEM_INSTRUCTION},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                msg_content = response.choices[0].message.content
                return str(msg_content) if msg_content else None
        return None

    @classmethod
    def evaluate_answer(
        cls,
        question: InterviewQuestion,
        answer_text: str,
        submitted_code: Optional[str] = None,
        submitted_language: Optional[str] = None,
    ) -> tuple[dict[str, Any], str, str, bool]:
        """
        Evaluate candidate answer.
        Returns: (evaluation_dict, provider, model, is_fallback)
        """
        provider = get_ai_provider()
        if not provider or not provider.is_configured:
            fallback = DeterministicEvaluationEngine.evaluate(
                question=question,
                answer_text=answer_text,
                submitted_code=submitted_code,
                submitted_language=submitted_language,
            )
            return fallback, "deterministic", "rule_based_v1", True

        try:
            prompt = cls._build_prompt(
                question=question,
                answer_text=answer_text,
                submitted_code=submitted_code,
                submitted_language=submitted_language,
            )

            raw_text = cls._invoke_provider(provider, prompt)
            if raw_text:
                parsed = cls._parse_ai_output(raw_text)
                if parsed and "overall_score" in parsed:
                    return parsed, provider.name, provider.model_name, False

            # Fallback
            fallback = DeterministicEvaluationEngine.evaluate(
                question=question,
                answer_text=answer_text,
                submitted_code=submitted_code,
                submitted_language=submitted_language,
            )
            return fallback, provider.name, provider.model_name, True

        except Exception as exc:
            logger.info("AI answer evaluation failed; using deterministic evaluator: %s", exc)
            fallback = DeterministicEvaluationEngine.evaluate(
                question=question,
                answer_text=answer_text,
                submitted_code=submitted_code,
                submitted_language=submitted_language,
            )
            return fallback, "deterministic", "rule_based_v1", True

    @classmethod
    def _build_prompt(
        cls,
        question: InterviewQuestion,
        answer_text: str,
        submitted_code: Optional[str],
        submitted_language: Optional[str],
    ) -> str:
        q_ctx = {
            "question_text": question.question_text,
            "category": question.category,
            "difficulty": question.difficulty,
            "expected_points": question.expected_points,
            "evaluation_criteria": question.evaluation_criteria,
            "ideal_outline": question.ideal_answer_outline,
        }

        sub_ctx = {
            "answer_text": answer_text,
            "code": submitted_code,
            "language": submitted_language,
        }

        return f"""Evaluate the candidate's answer against the interview question and rubric.

<QUESTION_DETAILS>
{json.dumps(q_ctx, indent=2)}
</QUESTION_DETAILS>

<CANDIDATE_SUBMISSION>
{json.dumps(sub_ctx, indent=2)}
</CANDIDATE_SUBMISSION>

Return JSON with keys:
- overall_score: float (0.0 to 100.0)
- technical_correctness_score: float
- relevance_score: float
- completeness_score: float
- clarity_score: float
- approach_score: float
- communication_score: float
- strengths: list of str
- missing_points: list of str
- suggested_improvements: list of str
- stronger_answer_example: str
- evaluation_feedback: str
"""

    @classmethod
    def _parse_ai_output(cls, raw_response: Any) -> Optional[dict[str, Any]]:
        text = raw_response if isinstance(raw_response, str) else str(raw_response)
        json_match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        else:
            json_match = re.search(r"(\{.*\})", text, re.DOTALL)
            if json_match:
                text = json_match.group(1)

        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict) and "overall_score" in parsed:
                return parsed
        except Exception:
            pass
        return None

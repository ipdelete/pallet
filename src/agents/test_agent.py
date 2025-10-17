"""Test Agent - Reviews code for quality and best practices."""

import json
from typing import Any, Dict

from src.agents.base import BaseAgent, SkillDefinition


class TestAgent(BaseAgent):
    """Agent that reviews code for quality, bugs, and best practices."""

    def __init__(self):
        """Initialize Test Agent."""
        skills = [
            SkillDefinition(
                id="review_code",
                description="Reviews code for quality, bugs, and best practices",
                input_schema={
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to review"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language (default: python)"
                        }
                    },
                    "required": ["code"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "quality_score": {"type": "number"},
                        "issues": {"type": "array"},
                        "suggestions": {"type": "array"},
                        "approved": {"type": "boolean"},
                        "summary": {"type": "string"}
                    }
                }
            )
        ]
        super().__init__(name="test-agent", port=8003, skills=skills)

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Any:
        """Execute the review_code skill."""
        if skill_id != "review_code":
            raise ValueError(f"Unknown skill: {skill_id}")

        code = params.get("code")
        language = params.get("language", "python")

        if not code:
            raise ValueError("code parameter is required")

        # Call Claude to review code
        system_prompt = f"""You are an expert {language} code reviewer.
        Review the provided code for:
        - Bugs and potential runtime errors
        - Performance issues
        - Security vulnerabilities
        - Code style and conventions
        - Best practices for {language}
        - Documentation and comments

        Return a JSON object with:
        - quality_score: 1-10 score for overall code quality
        - issues: Array of issues found, each with type (bug/security/style/documentation), line number (if applicable), and comment
        - suggestions: Array of suggestions for improvement
        - approved: Boolean indicating if code is production-ready
        - summary: Brief summary of the review

        Be constructive and specific in feedback."""

        user_message = f"""Please review the following {language} code:

{code}

Return ONLY the JSON object, no additional text."""

        response = await self.call_claude(system_prompt, user_message)

        # Parse the response as JSON
        try:
            # Try to extract JSON if it's wrapped in markdown code blocks
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0].strip()
            else:
                json_str = response.strip()

            review = json.loads(json_str)
            return review
        except json.JSONDecodeError as e:
            # Return a structured response if JSON parsing fails
            return {
                "quality_score": 0,
                "issues": [
                    {
                        "type": "error",
                        "comment": "Failed to parse review response"
                    }
                ],
                "suggestions": [],
                "approved": False,
                "summary": response,
                "error": str(e)
            }


def main():
    """Run the Test Agent."""
    agent = TestAgent()
    agent.run()


if __name__ == "__main__":
    main()

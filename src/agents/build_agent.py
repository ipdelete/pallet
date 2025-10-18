"""Build Agent - Generates code from plans."""

import json
from typing import Any, Dict

from src.agents.base import BaseAgent, SkillDefinition


class BuildAgent(BaseAgent):
    """Agent that generates code from implementation plans."""

    def __init__(self):
        """Initialize Build Agent."""
        skills = [
            SkillDefinition(
                id="generate_code",
                description="Generates Python code based on an implementation plan",
                input_schema={
                    "type": "object",
                    "properties": {
                        "plan": {
                            "type": "object",
                            "description": "Implementation plan from Plan Agent",
                        }
                    },
                    "required": ["plan"],
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "code": {"type": "string"},
                        "explanation": {"type": "string"},
                        "language": {"type": "string"},
                        "functions": {"type": "array"},
                    },
                },
            )
        ]
        super().__init__(name="build-agent", port=8002, skills=skills)

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Any:
        """Execute the generate_code skill."""
        if skill_id != "generate_code":
            raise ValueError(f"Unknown skill: {skill_id}")

        plan = params.get("plan")
        if not plan:
            raise ValueError("plan parameter is required")

        # Convert plan to string for Claude
        if isinstance(plan, dict):
            plan_str = json.dumps(plan, indent=2)
        else:
            plan_str = str(plan)

        # Call Claude to generate code
        system_prompt = """You are an expert Python software engineer.
        Given an implementation plan, write high-quality, well-documented Python code.

        Return a JSON object with:
        - code: The complete Python code
        - explanation: Brief explanation of the implementation
        - language: "python"
        - functions: Array of function/class names defined in the code

        Write clean, Pythonic code with type hints and docstrings.
        Use best practices and modern Python conventions."""

        user_message = f"""Generate Python code based on this implementation plan:

{plan_str}

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

            code_result = json.loads(json_str)
            return code_result
        except json.JSONDecodeError as e:
            # Return the raw response if JSON parsing fails
            return {
                "code": response,
                "explanation": "Generated code from plan",
                "language": "python",
                "error": f"Failed to parse response as JSON: {e}",
            }


def main():
    """Run the Build Agent."""
    agent = BuildAgent()
    agent.run()


if __name__ == "__main__":
    main()

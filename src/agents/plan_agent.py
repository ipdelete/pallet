"""Plan Agent - Creates structured implementation plans."""

import json
from typing import Any, Dict

from src.agents.base import BaseAgent, SkillDefinition


class PlanAgent(BaseAgent):
    """Agent that creates structured implementation plans."""

    def __init__(self):
        """Initialize Plan Agent."""
        skills = [
            SkillDefinition(
                id="create_plan",
                description="Creates a structured implementation plan from requirements",
                input_schema={
                    "type": "object",
                    "properties": {
                        "requirements": {
                            "type": "string",
                            "description": "User requirements or feature description"
                        }
                    },
                    "required": ["requirements"]
                },
                output_schema={
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "steps": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "name": {"type": "string"},
                                    "description": {"type": "string"},
                                    "time": {"type": "string"}
                                }
                            }
                        },
                        "dependencies": {"type": "array"},
                        "estimated_total_time": {"type": "string"}
                    }
                }
            )
        ]
        super().__init__(name="plan-agent", port=8001, skills=skills)

    async def execute_skill(self, skill_id: str, params: Dict[str, Any]) -> Any:
        """Execute the create_plan skill."""
        if skill_id != "create_plan":
            raise ValueError(f"Unknown skill: {skill_id}")

        requirements = params.get("requirements", "")
        if not requirements:
            raise ValueError("requirements parameter is required")

        # Call Claude to create a plan
        system_prompt = """You are an expert software architect and project planner.
        Given user requirements, create a detailed, structured implementation plan.

        Return a JSON object with:
        - title: Brief title of the project/feature
        - steps: Array of implementation steps, each with name, description, and time estimate
        - dependencies: List of external dependencies needed
        - estimated_total_time: Total estimated time for the implementation

        Be specific and practical in your planning."""

        user_message = f"""Please create an implementation plan for the following requirements:

{requirements}

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

            plan = json.loads(json_str)
            return plan
        except json.JSONDecodeError as e:
            # Return the raw response if JSON parsing fails
            return {
                "title": "Implementation Plan",
                "raw_response": response,
                "error": f"Failed to parse response as JSON: {e}"
            }


def main():
    """Run the Plan Agent."""
    agent = PlanAgent()
    agent.run()


if __name__ == "__main__":
    main()

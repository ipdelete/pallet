"""Sample data for testing."""

# JSON-RPC Messages
SAMPLE_JSONRPC_REQUEST = {
    "jsonrpc": "2.0",
    "method": "create_plan",
    "params": {
        "requirements": "Create a function to validate email addresses"
    },
    "id": "test-1"
}

SAMPLE_JSONRPC_RESPONSE = {
    "jsonrpc": "2.0",
    "result": {
        "title": "Email Validator",
        "steps": []
    },
    "id": "test-1"
}

SAMPLE_JSONRPC_ERROR = {
    "jsonrpc": "2.0",
    "error": {
        "code": -1,
        "message": "Unknown skill"
    },
    "id": "test-1"
}

# Claude Response Formats
CLAUDE_JSON_WRAPPED = '''```json
{
    "title": "Test Plan",
    "steps": [
        {"name": "Step 1", "description": "First step", "time": "5 min"}
    ],
    "dependencies": [],
    "estimated_total_time": "5 minutes"
}
```'''

CLAUDE_JSON_PLAIN = '''{
    "title": "Test Plan",
    "steps": [],
    "dependencies": [],
    "estimated_total_time": "5 minutes"
}'''

CLAUDE_INVALID_JSON = '''Here is the plan:
This is not valid JSON'''

# Agent Cards
PLAN_AGENT_CARD = {
    "name": "plan-agent",
    "url": "http://localhost:8001",
    "skills": [
        {
            "id": "create_plan",
            "description": "Creates a structured implementation plan from requirements",
            "input_schema": {
                "type": "object",
                "properties": {
                    "requirements": {"type": "string"}
                },
                "required": ["requirements"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "steps": {"type": "array"},
                    "dependencies": {"type": "array"},
                    "estimated_total_time": {"type": "string"}
                }
            }
        }
    ]
}

BUILD_AGENT_CARD = {
    "name": "build-agent",
    "url": "http://localhost:8002",
    "skills": [
        {
            "id": "generate_code",
            "description": "Generates Python code based on an implementation plan",
            "input_schema": {
                "type": "object",
                "properties": {
                    "plan": {"type": "object"}
                },
                "required": ["plan"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "explanation": {"type": "string"},
                    "language": {"type": "string"},
                    "functions": {"type": "array"}
                }
            }
        }
    ]
}

TEST_AGENT_CARD = {
    "name": "test-agent",
    "url": "http://localhost:8003",
    "skills": [
        {
            "id": "review_code",
            "description": "Reviews code for quality, bugs, and best practices",
            "input_schema": {
                "type": "object",
                "properties": {
                    "code": {"type": "string"},
                    "language": {"type": "string"}
                },
                "required": ["code"]
            },
            "output_schema": {
                "type": "object",
                "properties": {
                    "quality_score": {"type": "number"},
                    "issues": {"type": "array"},
                    "suggestions": {"type": "array"},
                    "approved": {"type": "boolean"},
                    "summary": {"type": "string"}
                }
            }
        }
    ]
}

# Requirements
REQUIREMENTS_EMAIL_VALIDATOR = "Create a Python function that validates email addresses"
REQUIREMENTS_TODO_LIST = "Build a TODO list manager with add, remove, and list functionality"
REQUIREMENTS_FIBONACCI = "Create a Fibonacci calculator function"

# Plans
PLAN_EMAIL_VALIDATOR = {
    "title": "Email Validator Implementation",
    "steps": [
        {
            "name": "Import regex module",
            "description": "Import the re module for pattern matching",
            "time": "1 minute"
        },
        {
            "name": "Define validation function",
            "description": "Create validate_email function with regex pattern",
            "time": "10 minutes"
        },
        {
            "name": "Add type hints and docstring",
            "description": "Document the function properly",
            "time": "5 minutes"
        }
    ],
    "dependencies": ["re"],
    "estimated_total_time": "16 minutes"
}

# Code Samples
CODE_EMAIL_VALIDATOR = '''import re

def validate_email(email: str) -> bool:
    """Validate an email address.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
'''

CODE_FIBONACCI = '''def fibonacci(n: int) -> int:
    """Calculate the nth Fibonacci number.

    Args:
        n: Position in Fibonacci sequence (0-indexed)

    Returns:
        The nth Fibonacci number
    """
    if n <= 1:
        return n
    return fibonacci(n - 1) + fibonacci(n - 2)
'''

# Code Results
CODE_RESULT_EMAIL = {
    "code": CODE_EMAIL_VALIDATOR,
    "explanation": "Simple email validation using regex pattern matching",
    "language": "python",
    "functions": ["validate_email"]
}

# Reviews
REVIEW_GOOD = {
    "quality_score": 9,
    "issues": [],
    "suggestions": [
        "Consider adding unit tests",
        "Could add support for internationalized domains"
    ],
    "approved": True,
    "summary": "Excellent implementation with good practices"
}

REVIEW_POOR = {
    "quality_score": 4,
    "issues": [
        {
            "type": "bug",
            "line": 10,
            "comment": "Potential null pointer exception"
        },
        {
            "type": "security",
            "line": 15,
            "comment": "SQL injection vulnerability"
        }
    ],
    "suggestions": [
        "Add input validation",
        "Use parameterized queries",
        "Add error handling"
    ],
    "approved": False,
    "summary": "Multiple critical issues found, not production-ready"
}

# Registry Data
REGISTRY_CATALOG = {
    "repositories": [
        "agents/plan",
        "agents/build",
        "agents/test"
    ]
}

REGISTRY_TAGS = {
    "name": "agents/plan",
    "tags": ["v1", "latest"]
}

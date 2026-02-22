"""ReflectionEngine - Self-reflective capability for analyzing and improving agent behavior."""

from nanobot.providers.llm import LLMClient


class ReflectionEngine:
    """Analyzes agent behavior patterns and generates improvement suggestions."""

    def __init__(self, llm_client: LLMClient):
        """
        Initialize the ReflectionEngine.

        Args:
            llm_client: The LLM client for generating insights
        """
        self.llm_client = llm_client

    async def analyze_behavior(self, messages: list[dict]) -> dict:
        """
        Analyze agent behavior patterns from conversation history.

        Args:
            messages: List of message dictionaries from the session

        Returns:
            Dictionary containing:
                - tool_usage_frequency: Dict mapping tool names to usage count
                - iteration_depth: Number of iterations in the session
                - response_length: Total length of assistant responses
        """
        if not messages:
            return {
                "tool_usage_frequency": {},
                "iteration_depth": 0,
                "response_length": 0,
            }

        tool_usage = {}
        iteration_count = 0
        response_length = 0

        for msg in messages:
            # Count iterations (assistant messages that are not initial system messages)
            if msg.get("role") == "assistant":
                iteration_count += 1
                content = msg.get("content", "")
                response_length += len(content)

            # Track tool usage
            if msg.get("role") == "tool":
                tool_name = msg.get("name")
                if tool_name:
                    tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

        # Cap iteration depth at 50 to prevent excessive values
        iteration_depth = min(iteration_count, 50)

        return {
            "tool_usage_frequency": tool_usage,
            "iteration_depth": iteration_depth,
            "response_length": response_length,
        }

    async def generate_improvements(self, analysis: dict) -> list[str]:
        """
        Generate improvement suggestions based on behavior analysis.

        Args:
            analysis: Dictionary from analyze_behavior() containing metrics

        Returns:
            List of improvement suggestion strings
        """
        suggestions = []

        # Analyze iteration depth
        iteration_depth = analysis.get("iteration_depth", 0)
        if iteration_depth > 15:
            suggestions.append(
                f"High iteration depth ({iteration_depth}) detected. Consider breaking down complex tasks into smaller steps."
            )

        # Analyze tool usage
        tool_usage = analysis.get("tool_usage_frequency", {})
        if tool_usage:
            # Check for excessive web search
            if tool_usage.get("web_search", 0) > 20:
                suggestions.append(
                    "Frequent web searches detected. Consider caching results or using more efficient search strategies."
                )

            # Check for repeated failed tools (would need additional tracking)
            total_tools = sum(tool_usage.values())
            if total_tools > 50:
                suggestions.append(
                    f"High tool usage ({total_tools} total calls). Consider optimizing tool selection or reducing unnecessary calls."
                )

        # Analyze response length
        response_length = analysis.get("response_length", 0)
        if response_length > 3000:
            suggestions.append(
                f"Long responses detected ({response_length} characters). Consider being more concise and to the point."
            )

        # Analyze user satisfaction (would need this metric in analyze_behavior)
        user_satisfaction = analysis.get("user_satisfaction", 0.7)
        if user_satisfaction < 0.5:
            suggestions.append(
                "Low user satisfaction detected. Consider improving response quality and relevance."
            )

        # If no specific issues found, provide general suggestions
        if not suggestions:
            suggestions.append(
                "Good performance metrics. Consider exploring more advanced capabilities."
            )

        return suggestions

    async def evaluate_decision(self, tool_call: dict, result: str) -> str:
        """
        Evaluate if a tool call was appropriate and effective.

        Args:
            tool_call: Dictionary containing tool call details
            result: Result string from tool execution

        Returns:
            Evaluation string
        """
        tool_name = tool_call.get("name", "unknown")
        tool_success = "effective" if "error" not in result.lower() else "suboptimal"

        return f"Tool {tool_name} was {tool_success} with result length {len(result)} characters."

    async def detect_patterns(self, session: list[dict]) -> list[dict]:
        """
        Detect recurring patterns in agent behavior.

        Args:
            session: List of messages from the session

        Returns:
            List of pattern dictionaries with detected issues
        """
        patterns = []

        # Find repeated failed tools (would need additional tracking in analyze_behavior)
        if len(session) > 50:
            patterns.append(
                {
                    "type": "large_session",
                    "severity": "info",
                    "message": "Large session detected. Consider consolidating memory.",
                }
            )

        # Detect overly long iterations
        iteration_depth = session.count({"role": "assistant"})
        if iteration_depth > 20:
            patterns.append(
                {
                    "type": "long_iterations",
                    "severity": "warning",
                    "message": f"High iteration depth ({iteration_depth}) detected.",
                }
            )

        return patterns

    async def generate_self_report(self) -> str:
        """
        Generate a periodic self-evaluation report.

        Returns:
            Self-evaluation report string
        """
        # This would typically analyze recent sessions
        return (
            "ReflectionEngine ready. Current metrics indicate the agent is functioning normally. "
            "Consider implementing more advanced self-monitoring capabilities."
        )

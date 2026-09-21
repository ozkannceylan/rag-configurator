"""ReAct (Reasoning + Acting) agent implementation using LangGraph."""

import logging
import re
import time
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypedDict

from app.agents.base import (
    AgentConfig,
    AgentError,
    AgentResponse,
    AgentStep,
    BaseAgent,
    StepType,
)
from app.llm.base import BaseLLM, Message
from app.prompts.manager import PromptManager
from app.retrieval.base import BaseRetriever, RetrievedChunk

logger = logging.getLogger(__name__)


class ToolType(StrEnum):
    """Available tool types."""

    SEARCH = "search"
    RETRIEVE = "retrieve"
    CALCULATE = "calculate"
    LOOKUP = "lookup"
    NONE = "none"


@dataclass
class Tool:
    """A tool available to the ReAct agent."""

    name: str
    description: str
    tool_type: ToolType
    handler: Callable
    parameters: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for prompt."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }


@dataclass
class Thought:
    """A reasoning thought from the agent."""

    content: str
    iteration: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class Action:
    """An action taken by the agent."""

    tool: str
    input: str
    iteration: int
    timestamp: float = field(default_factory=time.time)


@dataclass
class Observation:
    """An observation from tool execution."""

    content: str
    tool: str
    iteration: int
    success: bool = True
    timestamp: float = field(default_factory=time.time)


class ReActState(TypedDict, total=False):
    """State for ReAct agent execution."""

    # Input
    query: str
    config_id: str
    conversation_history: list[dict[str, str]]

    # ReAct loop state
    thoughts: list[Thought]
    actions: list[Action]
    observations: list[Observation]
    iterations: int
    max_iterations: int

    # Context accumulation
    context: list[str]
    retrieved_chunks: list[RetrievedChunk]

    # Output
    answer: str
    should_answer: bool

    # Tracking
    steps: list[AgentStep]
    error: str | None
    metadata: dict[str, Any]


@dataclass
class ReActConfig(AgentConfig):
    """Configuration specific to ReAct agent."""

    max_iterations: int = 5
    thought_temperature: float = 0.7
    answer_temperature: float = 0.3

    # Tool settings
    enable_search: bool = True
    enable_retrieve: bool = True
    enable_calculate: bool = False

    # Prompts
    react_system_prompt: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReActConfig":
        """Create from dictionary."""
        base = AgentConfig.from_dict(data)
        return cls(
            top_k=base.top_k,
            min_score=base.min_score,
            temperature=base.temperature,
            max_tokens=base.max_tokens,
            streaming=base.streaming,
            system_prompt_name=base.system_prompt_name,
            rag_prompt_name=base.rag_prompt_name,
            include_steps=base.include_steps,
            verbose=base.verbose,
            timeout_seconds=base.timeout_seconds,
            max_iterations=data.get("max_iterations", 5),
            thought_temperature=data.get("thought_temperature", 0.7),
            answer_temperature=data.get("answer_temperature", 0.3),
            enable_search=data.get("enable_search", True),
            enable_retrieve=data.get("enable_retrieve", True),
            enable_calculate=data.get("enable_calculate", False),
            react_system_prompt=data.get("react_system_prompt"),
        )


# Default ReAct system prompt
REACT_SYSTEM_PROMPT = """You are a helpful assistant that solves problems step by step using reasoning and actions.

You have access to the following tools:
{tools}

Use this format:

Thought: Consider what you need to do and why
Action: tool_name[input]
Observation: (result from tool)
... (repeat Thought/Action/Observation as needed)
Thought: I now have enough information to answer
Answer: (final answer based on observations)

Important rules:
1. Always start with a Thought
2. Use tools when you need information
3. Base your answer only on observations
4. If you can answer directly, skip to Answer
5. Maximum {max_iterations} iterations allowed

Begin!"""

# Prompt for generating thoughts
THOUGHT_PROMPT = """Current question: {query}

Previous reasoning:
{history}

Available tools: {tools}

What should you think about or do next? Respond with either:
- A Thought followed by an Action if you need more information
- A Thought followed by Answer if you can answer now

Your response:"""


class ReActAgent(BaseAgent):
    """
    ReAct (Reasoning + Acting) agent.

    Implements iterative reasoning with tool use:
    Think → Act → Observe → (repeat) → Answer
    """

    def __init__(
        self,
        retriever: BaseRetriever,
        llm: BaseLLM,
        prompt_manager: PromptManager | None = None,
        config: ReActConfig | None = None,
        tools: list[Tool] | None = None,
    ):
        """
        Initialize ReAct agent.

        Args:
            retriever: Retriever for search/retrieve tools
            llm: Language model for reasoning
            prompt_manager: Prompt manager for templates
            config: ReAct configuration
            tools: Custom tools (optional)
        """
        super().__init__(config or ReActConfig())
        self._agent_name = "react"

        self.retriever = retriever
        self.llm = llm
        self.prompt_manager = prompt_manager or PromptManager()
        self.react_config = config or ReActConfig()

        # Initialize tools
        self._tools: dict[str, Tool] = {}
        self._init_default_tools()
        if tools:
            for tool in tools:
                self.add_tool(tool)

        # Build LangGraph if available
        self._graph = None
        self._use_langgraph = self._init_langgraph()

    def _init_default_tools(self) -> None:
        """Initialize default tools."""
        if self.react_config.enable_search:
            self._tools["search"] = Tool(
                name="search",
                description="Search for relevant information in the knowledge base",
                tool_type=ToolType.SEARCH,
                handler=self._search_tool,
                parameters={"query": "The search query"},
            )

        if self.react_config.enable_retrieve:
            self._tools["retrieve"] = Tool(
                name="retrieve",
                description="Retrieve specific documents or chunks by topic",
                tool_type=ToolType.RETRIEVE,
                handler=self._retrieve_tool,
                parameters={"topic": "The topic to retrieve documents about"},
            )

        if self.react_config.enable_calculate:
            self._tools["calculate"] = Tool(
                name="calculate",
                description="Perform mathematical calculations",
                tool_type=ToolType.CALCULATE,
                handler=self._calculate_tool,
                parameters={"expression": "Mathematical expression to evaluate"},
            )

    def add_tool(self, tool: Tool) -> None:
        """Add a custom tool."""
        self._tools[tool.name] = tool
        logger.info(f"Added tool: {tool.name}")

    def _init_langgraph(self) -> bool:
        """Initialize LangGraph if available."""
        try:
            # Availability probe: the import must stay so a missing LangGraph
            # raises ImportError here rather than later at call time.
            from langgraph.graph import END, StateGraph  # noqa: F401

            self._graph = self._build_graph()
            return True
        except ImportError:
            logger.info("LangGraph not available, using simple flow")
            return False

    def _build_graph(self):
        """Build the LangGraph state graph."""
        from langgraph.graph import END, StateGraph

        graph = StateGraph(ReActState)

        # Add nodes
        graph.add_node("think", self._think_node)
        graph.add_node("act", self._act_node)
        graph.add_node("observe", self._observe_node)
        graph.add_node("answer", self._answer_node)

        # Set entry point
        graph.set_entry_point("think")

        # Add conditional edge from think
        graph.add_conditional_edges(
            "think",
            self._should_continue,
            {
                "continue": "act",
                "answer": "answer",
            },
        )

        # Linear edges
        graph.add_edge("act", "observe")
        graph.add_edge("observe", "think")
        graph.add_edge("answer", END)

        return graph.compile()

    def _should_continue(self, state: ReActState) -> str:
        """Determine whether to continue reasoning or answer."""
        # Check if we should answer
        if state.get("should_answer", False):
            return "answer"

        # Check iteration limit
        iterations = state.get("iterations", 0)
        max_iter = state.get("max_iterations", self.react_config.max_iterations)
        if iterations >= max_iter:
            return "answer"

        # Check if error occurred
        if state.get("error"):
            return "answer"

        return "continue"

    async def _think_node(self, state: ReActState) -> ReActState:
        """Generate a thought about what to do next."""
        start_time = time.time()

        query = state["query"]
        iterations = state.get("iterations", 0)

        try:
            # Build history of thoughts/actions/observations
            history = self._format_reasoning_history(state)

            # Build tools description
            tools_desc = self._format_tools_description()

            # Generate thought
            system_prompt = (
                self.react_config.react_system_prompt
                or REACT_SYSTEM_PROMPT.format(
                    tools=tools_desc,
                    max_iterations=self.react_config.max_iterations,
                )
            )

            thought_prompt = THOUGHT_PROMPT.format(
                query=query,
                history=history or "No previous reasoning yet.",
                tools=", ".join(self._tools.keys()),
            )

            messages = [
                Message.system(system_prompt),
                Message.user(thought_prompt),
            ]

            response = await self.llm.generate(
                messages=messages,
                temperature=self.react_config.thought_temperature,
                max_tokens=self.config.max_tokens,
            )

            # Parse response
            thought_text, action_text, answer_text = self._parse_response(
                response.content
            )

            duration = (time.time() - start_time) * 1000

            # Create thought
            thoughts = list(state.get("thoughts", []))
            if thought_text:
                thoughts.append(
                    Thought(
                        content=thought_text,
                        iteration=iterations,
                    )
                )

            # Create step
            step = AgentStep(
                step_type=StepType.REWRITE if action_text else StepType.GENERATE,
                name="think",
                input={"query": query, "iteration": iterations},
                output={
                    "thought": thought_text,
                    "has_action": bool(action_text),
                    "has_answer": bool(answer_text),
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            # Determine next state
            should_answer = bool(answer_text) or not action_text
            pending_action = action_text

            return {
                **state,
                "thoughts": thoughts,
                "iterations": iterations + 1,
                "should_answer": should_answer,
                "steps": steps,
                "metadata": {
                    **state.get("metadata", {}),
                    "pending_action": pending_action,
                    "pending_answer": answer_text,
                },
            }

        except Exception as e:
            logger.error(f"Think failed: {e}")
            step = AgentStep(
                step_type=StepType.ERROR,
                name="think_error",
                output={"error": str(e)},
            )
            steps = list(state.get("steps", []))
            steps.append(step)
            return {
                **state,
                "steps": steps,
                "error": str(e),
                "should_answer": True,
            }

    async def _act_node(self, state: ReActState) -> ReActState:
        """Execute the planned action."""
        start_time = time.time()
        iterations = state.get("iterations", 0)

        # Get pending action from metadata
        action_text = state.get("metadata", {}).get("pending_action", "")

        if not action_text:
            return state

        try:
            # Parse action
            tool_name, tool_input = self._parse_action(action_text)

            # Create action record
            actions = list(state.get("actions", []))
            actions.append(
                Action(
                    tool=tool_name,
                    input=tool_input,
                    iteration=iterations,
                )
            )

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.TOOL_CALL,
                name="act",
                input={"tool": tool_name, "input": tool_input},
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "actions": actions,
                "steps": steps,
                "metadata": {
                    **state.get("metadata", {}),
                    "current_tool": tool_name,
                    "current_input": tool_input,
                },
            }

        except Exception as e:
            logger.error(f"Act failed: {e}")
            return {
                **state,
                "error": str(e),
            }

    async def _observe_node(self, state: ReActState) -> ReActState:
        """Execute tool and observe result."""
        start_time = time.time()
        iterations = state.get("iterations", 0)

        tool_name = state.get("metadata", {}).get("current_tool", "")
        tool_input = state.get("metadata", {}).get("current_input", "")
        config_id = state["config_id"]

        try:
            # Execute tool
            tool = self._tools.get(tool_name)
            if tool is None:
                observation_text = f"Error: Unknown tool '{tool_name}'"
                success = False
            else:
                observation_text = await tool.handler(tool_input, config_id, state)
                success = True

            # Create observation
            observations = list(state.get("observations", []))
            observations.append(
                Observation(
                    content=observation_text,
                    tool=tool_name,
                    iteration=iterations,
                    success=success,
                )
            )

            # Accumulate context
            context = list(state.get("context", []))
            if success and observation_text:
                context.append(observation_text)

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=(
                    StepType.RETRIEVE
                    if tool_name in ["search", "retrieve"]
                    else StepType.TOOL_CALL
                ),
                name="observe",
                input={"tool": tool_name},
                output={
                    "observation_length": len(observation_text),
                    "success": success,
                },
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "observations": observations,
                "context": context,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Observe failed: {e}")
            observations = list(state.get("observations", []))
            observations.append(
                Observation(
                    content=f"Error: {str(e)}",
                    tool=tool_name,
                    iteration=iterations,
                    success=False,
                )
            )
            return {
                **state,
                "observations": observations,
            }

    async def _answer_node(self, state: ReActState) -> ReActState:
        """Generate final answer."""
        start_time = time.time()

        query = state["query"]

        try:
            # Check if we have a pending answer from think
            pending_answer = state.get("metadata", {}).get("pending_answer")
            if pending_answer:
                answer = pending_answer
            else:
                # Generate answer from context
                context = "\n\n".join(state.get("context", []))
                history = self._format_reasoning_history(state)

                answer_prompt = f"""Based on your reasoning and observations, provide a final answer.

Question: {query}

Your reasoning:
{history}

Accumulated context:
{context}

Provide a clear, comprehensive answer based on the above information:"""

                messages = [
                    Message.system(self.prompt_manager.get_system_prompt()),
                    Message.user(answer_prompt),
                ]

                response = await self.llm.generate(
                    messages=messages,
                    temperature=self.react_config.answer_temperature,
                    max_tokens=self.config.max_tokens,
                )
                answer = response.content

            duration = (time.time() - start_time) * 1000

            step = AgentStep(
                step_type=StepType.GENERATE,
                name="answer",
                input={"query": query},
                output={"answer_length": len(answer)},
                duration_ms=duration,
            )

            steps = list(state.get("steps", []))
            steps.append(step)

            return {
                **state,
                "answer": answer,
                "steps": steps,
            }

        except Exception as e:
            logger.error(f"Answer failed: {e}")
            return {
                **state,
                "answer": "I apologize, but I was unable to generate an answer.",
                "error": str(e),
            }

    async def run(
        self,
        query: str,
        config_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> AgentResponse:
        """
        Run the ReAct agent.

        Args:
            query: User query
            config_id: RAG pipeline configuration ID
            conversation_history: Optional conversation history
            **kwargs: Additional arguments

        Returns:
            AgentResponse with answer and reasoning trace
        """
        start_time = time.time()

        # Initial state
        initial_state: ReActState = {
            "query": query,
            "config_id": config_id,
            "conversation_history": conversation_history or [],
            "thoughts": [],
            "actions": [],
            "observations": [],
            "iterations": 0,
            "max_iterations": self.react_config.max_iterations,
            "context": [],
            "retrieved_chunks": [],
            "answer": "",
            "should_answer": False,
            "steps": [],
            "metadata": {},
        }

        try:
            if self._use_langgraph and self._graph is not None:
                final_state = await self._graph.ainvoke(initial_state)
            else:
                final_state = await self._simple_flow(initial_state)

            total_duration = (time.time() - start_time) * 1000

            # Build response
            response = AgentResponse(
                answer=final_state.get("answer", ""),
                sources=final_state.get("retrieved_chunks", []),
                steps=final_state.get("steps", []) if self.config.include_steps else [],
                total_duration_ms=total_duration,
                metadata={
                    "iterations": final_state.get("iterations", 0),
                    "thoughts": [t.content for t in final_state.get("thoughts", [])],
                    "actions": [
                        f"{a.tool}[{a.input}]" for a in final_state.get("actions", [])
                    ],
                },
            )

            return response

        except Exception as e:
            logger.error(f"ReAct agent execution failed: {e}")
            raise AgentError(
                message=str(e),
                step="run",
                details={"query": query, "config_id": config_id},
            )

    async def _simple_flow(self, state: ReActState) -> ReActState:
        """Execute ReAct flow without LangGraph."""
        while True:
            # Think
            state = await self._think_node(state)

            # Check if should answer
            if self._should_continue(state) == "answer":
                break

            # Act
            state = await self._act_node(state)

            # Observe
            state = await self._observe_node(state)

        # Generate answer
        state = await self._answer_node(state)

        return state

    async def stream(
        self,
        query: str,
        config_id: str,
        conversation_history: list[dict[str, str]] | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        """
        Stream the agent response.

        Note: ReAct agent streams the final answer generation.
        """
        # Run the reasoning loop first
        response = await self.run(
            query=query,
            config_id=config_id,
            conversation_history=conversation_history,
            **kwargs,
        )

        # Yield the answer in chunks
        words = response.answer.split()
        for i, word in enumerate(words):
            yield word + (" " if i < len(words) - 1 else "")

    # Tool implementations
    async def _search_tool(
        self,
        query: str,
        config_id: str,
        state: ReActState,
    ) -> str:
        """Search tool implementation."""
        try:
            chunks = await self.retriever.retrieve(
                query=query,
                config_id=config_id,
                top_k=self.config.top_k,
            )

            if not chunks:
                return "No relevant results found."

            # Update state with chunks
            existing_chunks = list(state.get("retrieved_chunks", []))
            existing_chunks.extend(chunks)

            # Format results
            results = []
            for i, chunk in enumerate(chunks[:5], 1):
                results.append(f"[{i}] {chunk.content[:500]}...")

            return "\n\n".join(results)

        except Exception as e:
            return f"Search error: {str(e)}"

    async def _retrieve_tool(
        self,
        topic: str,
        config_id: str,
        state: ReActState,
    ) -> str:
        """Retrieve tool implementation."""
        # Similar to search but with different framing
        return await self._search_tool(topic, config_id, state)

    async def _calculate_tool(
        self,
        expression: str,
        config_id: str,
        state: ReActState,
    ) -> str:
        """Calculate tool implementation."""
        try:
            # Safe evaluation of mathematical expressions
            # Only allow basic math operations
            allowed = set("0123456789+-*/().% ")
            if not all(c in allowed for c in expression):
                return "Error: Invalid expression (only basic math allowed)"

            result = eval(expression)  # Safe because we validated input
            return f"Result: {result}"

        except Exception as e:
            return f"Calculation error: {str(e)}"

    # Helper methods
    def _format_reasoning_history(self, state: ReActState) -> str:
        """Format the reasoning history for the prompt."""
        parts = []

        thoughts = state.get("thoughts", [])
        actions = state.get("actions", [])
        observations = state.get("observations", [])

        # Interleave thoughts, actions, observations
        for i in range(max(len(thoughts), len(actions), len(observations))):
            if i < len(thoughts):
                parts.append(f"Thought: {thoughts[i].content}")
            if i < len(actions):
                parts.append(f"Action: {actions[i].tool}[{actions[i].input}]")
            if i < len(observations):
                parts.append(f"Observation: {observations[i].content[:500]}")

        return "\n".join(parts)

    def _format_tools_description(self) -> str:
        """Format tools description for the prompt."""
        descriptions = []
        for name, tool in self._tools.items():
            params = ", ".join(f"{k}: {v}" for k, v in tool.parameters.items())
            descriptions.append(f"- {name}[{params}]: {tool.description}")
        return "\n".join(descriptions)

    def _parse_response(self, response: str) -> tuple[str, str, str]:
        """Parse LLM response into thought, action, and answer."""
        thought = ""
        action = ""
        answer = ""

        # Extract thought
        thought_match = re.search(
            r"Thought:\s*(.+?)(?=Action:|Answer:|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if thought_match:
            thought = thought_match.group(1).strip()

        # Extract action
        action_match = re.search(
            r"Action:\s*(.+?)(?=Observation:|Thought:|Answer:|$)",
            response,
            re.DOTALL | re.IGNORECASE,
        )
        if action_match:
            action = action_match.group(1).strip()

        # Extract answer
        answer_match = re.search(
            r"Answer:\s*(.+?)$", response, re.DOTALL | re.IGNORECASE
        )
        if answer_match:
            answer = answer_match.group(1).strip()

        return thought, action, answer

    def _parse_action(self, action_text: str) -> tuple[str, str]:
        """Parse action text into tool name and input."""
        # Match format: tool_name[input] or tool_name(input)
        match = re.match(r"(\w+)\s*[\[\(](.+?)[\]\)]", action_text.strip())
        if match:
            return match.group(1).lower(), match.group(2).strip()

        # Fallback: just use as search
        return "search", action_text.strip()

    async def close(self) -> None:
        """Clean up resources."""
        if hasattr(self.retriever, "close"):
            await self.retriever.close()
        if hasattr(self.llm, "close"):
            await self.llm.close()

"""LangGraph state graph that wires the six triage nodes into a pipeline."""

from langgraph.graph import END, START, StateGraph

from nodes import classify, diagnose, evaluate, extract, prioritize, resolve
from state import TicketState

graph = StateGraph(TicketState)

graph.add_node("extract", extract)
graph.add_node("classify", classify)
graph.add_node("prioritize", prioritize)
graph.add_node("diagnose", diagnose)
graph.add_node("resolve", resolve)
graph.add_node("evaluate", evaluate)

graph.add_edge(START, "extract")
graph.add_edge("extract", "classify")
graph.add_edge("classify", "prioritize")
graph.add_edge("prioritize", "diagnose")
graph.add_edge("diagnose", "resolve")
graph.add_edge("resolve", "evaluate")
graph.add_edge("evaluate", END)

app = graph.compile()

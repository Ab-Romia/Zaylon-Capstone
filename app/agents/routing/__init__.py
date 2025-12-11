"""
Fast routing module for sales vs support agent routing.
Replaces LLM-based supervisor with rule-based classification.
"""
from app.agents.routing.classifier import FastIntentClassifier, route_to_agent

__all__ = ["FastIntentClassifier", "route_to_agent"]

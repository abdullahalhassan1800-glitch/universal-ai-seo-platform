"""Prompt templates for AI-powered SEO features."""

AUDIT_SOLUTION_PROMPT = """You are a senior technical SEO consultant.

Issue: {issue}
Dimension: {dimension}
Affected URL: {url}
Explanation: {explanation}
Current recommendation: {recommendation}

Write a concrete, actionable solution for this issue. Return JSON with a single
key "ai_solution" containing 2-4 sentences: what to change, where, and how a
developer or content writer can implement it. Do not fabricate data."""

INTENT_PROMPT = """Classify the search intent of each keyword. Return JSON mapping
each keyword string to exactly one of: informational, commercial, transactional,
navigational, local. Base it on the words and likely user goal."""

CLUSTER_PROMPT = """Group the following keywords into topic clusters so they can
each be targeted by one piece of content. Return a JSON array of objects with keys:
"name" (short cluster name), "topic" (broader topic), "intent" (dominant intent),
"keywords" (list of member keyword strings). Use every keyword exactly once.
Keywords: {keywords}"""

PRIORITY_PROMPT = """You are an SEO prioritization engine. Given the audit tasks
below, return a JSON array of objects with keys: "title", "priority"
(CRITICAL/HIGH/MEDIUM/LOW), "impact" (0-100), "difficulty" (0-100),
"urgency" (0-100), "confidence" (0-100). Order the array from highest to lowest
priority. Only include tasks from the provided list."""

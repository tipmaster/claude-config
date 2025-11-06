#!/usr/bin/env python3
"""
Skill suggestion utility based on user prompt analysis.

This script reads skill-rules.json and suggests relevant Superpowers skills
based on pattern matching against user prompts.

Usage:
  # Via environment variable (for hooks)
  ARGUMENTS='{"prompt":"fix the bug in authentication"}' ./skill-suggester.py

  # Via command line
  ./skill-suggester.py "fix the bug in authentication"

  # Test mode - show all rules
  ./skill-suggester.py --test
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import List, Dict, Any


def load_skill_rules() -> Dict[str, Any]:
    """Load skill rules from .claude/skill-rules.json"""
    script_dir = Path(__file__).parent.parent
    rules_file = script_dir / "skill-rules.json"

    if not rules_file.exists():
        return {"rules": [], "exemptions": []}

    with open(rules_file, 'r') as f:
        return json.load(f)


def is_exempted(prompt: str, exemptions: List[str]) -> bool:
    """Check if prompt matches exemption patterns (informational queries)"""
    prompt_lower = prompt.lower()
    return any(pattern in prompt_lower for pattern in exemptions)


def match_skills(prompt: str, rules: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Match prompt against skill patterns and return matching skills"""
    matches = []
    prompt_lower = prompt.lower()

    for rule in rules:
        for pattern in rule.get("patterns", []):
            if re.search(pattern, prompt_lower):
                matches.append({
                    "skill": rule["skill"],
                    "priority": rule.get("priority", "medium"),
                    "description": rule.get("description", ""),
                    "matched_pattern": pattern
                })
                break  # Only match once per rule

    # Sort by priority
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    matches.sort(key=lambda x: priority_order.get(x["priority"], 99))

    return matches


def format_suggestions(matches: List[Dict[str, Any]]) -> str:
    """Format skill suggestions for output"""
    if not matches:
        return "No specific skills suggested for this prompt."

    output = ["📋 Relevant Skills Detected:\n"]

    for i, match in enumerate(matches, 1):
        priority_emoji = {
            "critical": "🔴",
            "high": "🟡",
            "medium": "🔵",
            "low": "⚪"
        }.get(match["priority"], "⚪")

        output.append(f"{priority_emoji} {match['skill']}")
        output.append(f"   Priority: {match['priority'].upper()}")
        output.append(f"   {match['description']}")
        if i < len(matches):
            output.append("")

    return "\n".join(output)


def main():
    # Load rules
    config = load_skill_rules()
    rules = config.get("rules", [])
    exemptions = config.get("exemptions", [])

    # Test mode
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        print(f"Loaded {len(rules)} skill rules")
        print(f"Exemption patterns: {', '.join(exemptions)}")
        print("\nSkills by priority:")
        for priority in ["critical", "high", "medium", "low"]:
            skills = [r["skill"] for r in rules if r.get("priority") == priority]
            if skills:
                print(f"  {priority.upper()}: {', '.join(skills)}")
        return

    # Get prompt from environment variable (hook mode) or command line
    prompt = None
    if os.environ.get("ARGUMENTS"):
        try:
            args = json.loads(os.environ["ARGUMENTS"])
            prompt = args.get("prompt") or args.get("message") or args.get("content")
        except json.JSONDecodeError:
            pass

    if not prompt and len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])

    if not prompt:
        print("Usage: skill-suggester.py <prompt> or set ARGUMENTS env var")
        sys.exit(1)

    # Check exemptions
    if is_exempted(prompt, exemptions):
        print("ℹ️  Informational query detected - skills not required")
        sys.exit(0)

    # Match skills
    matches = match_skills(prompt, rules)

    # Output suggestions
    print(format_suggestions(matches))

    # Exit with code indicating matches found
    sys.exit(0 if matches else 1)


if __name__ == "__main__":
    main()

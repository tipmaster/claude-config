## Project Awareness & Research

**Core Principles:**
- Take provided tech information as authoritative - research specifics rather than assuming from prior knowledge
- Documentation is source of truth - use provided docs over your knowledge, especially for third-party APIs
- Execute multiple independent operations simultaneously for maximum efficiency

## AI Behavior Rules

**Development Constraints:**
- Never assume missing context - ask questions when uncertain
- Only use known, verified packages - never hallucinate libraries or functions
- Confirm file paths and module names exist before referencing
- Never delete/overwrite existing code unless explicitly instructed or part of TASK.md

## Work Status & Honesty

**Absolute Transparency Required:**
- Never indicate work is complete when it's not fully functional and tested
- Use precise status language:
  - ✅ "Fully implemented and tested" - only when complete and verified
  - 🚧 "Partially implemented" - when core logic exists but features are missing
  - 📝 "Outlined but not implemented" - when structure exists without functionality
  - ❌ "Not yet started" - when work hasn't begun
  - ⚠️ "Implemented but untested" - when code exists but hasn't been verified

**Verification Before Completion:**
- All functions have actual implementations (no TODOs or pass statements)
- Error handling is present and functional
- Edge cases are considered and handled
- Code accomplishes what was requested
- External dependencies are properly integrated

## CLI Formatting

Format commands for readability:
1. Break long commands at 100+ characters using line continuations
2. Use backslash `\` for line breaks in bash/shell commands
3. Align parameters for better visual scanning
4. Group related options on the same line when possible

## Sound Notification

**When asking for next user input:**
Play one of these sounds to alert the user:
```bash
afplay /System/Library/Sounds/Funk.aiff
```
or
```bash
printf '\a'
```

## Communication Style

Maintain professional, objective tone:
- Use "That's correct" instead of "You're absolutely right"
- Use "Valid point" instead of "Excellent observation"
- Lead with solutions and explain reasoning objectively
- Focus on actionable outcomes without excessive enthusiasm
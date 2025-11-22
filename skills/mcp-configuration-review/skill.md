---
name: mcp-configuration-review
description: Reviews MCP server configuration, checks health status, validates settings, and provides optimization recommendations
---

# MCP Configuration Review Skill

## Purpose
Systematically review Model Context Protocol (MCP) server configuration to ensure optimal performance, security, and productivity.

## When to Use
- Before starting new projects
- Monthly configuration audits
- After adding/removing MCP servers
- When experiencing MCP connection issues
- When optimizing Claude Code performance

## Checklist

☐ **List Active MCP Servers**
   - Run `/mcp` command to see all configured servers
   - Check which servers are connected vs. disconnected
   - Note any error messages

☐ **Validate Configuration Syntax**
   - Review `config/settings-laptop.json` mcpServers section
   - Verify all required fields: command, args, env
   - Check for typos in server names
   - Validate environment variable references (${VAR})

☐ **Check for Redundancy**
   - Identify duplicate functionality (e.g., multiple browser automation servers)
   - Recommend consolidation to reduce resource usage
   - Document which server to keep and why

☐ **Verify Local MCP Servers**
   - For Node.js servers: Check build status and node_modules
   - For Python servers: Verify virtual environments exist
   - Test local server startup manually if needed
   - Example: `cd mcp-servers/dataforseo && npm run build`

☐ **Test MCP Server Health**
   - Use MCP tools from each server to verify functionality
   - Check response times (slow servers may need optimization)
   - Verify authentication (API keys, tokens)
   - Check network connectivity for remote servers

☐ **Security Review**
   - Verify API keys stored in environment variables (not hardcoded)
   - Check file system access permissions
   - Review allowed directories for filesystem MCP
   - Validate command whitelists for execution servers

☐ **Missing Productivity MCPs**
   - Check if project would benefit from:
     - **filesystem**: Enhanced file operations, monitoring
     - **github**: PR/issue automation
     - **git**: Repository operations
     - **memory**: Persistent context across sessions
     - **sqlite/postgresql**: Database introspection
     - **sequential-thinking**: Structured problem-solving

☐ **Performance Optimization**
   - Identify unused MCPs consuming resources
   - Check for slow-starting servers
   - Recommend disabling unused servers
   - Suggest project-specific MCP overrides

☐ **Documentation Review**
   - Ensure PROJECT_CLAUDE.MD mentions critical MCPs
   - Document custom MCP configurations
   - Add usage examples for complex MCPs

## Output Format

Provide a structured report:

### Summary
- Total MCP servers configured: X
- Connected: Y
- Issues found: Z

### Issues Detected
1. **Issue Name** (Priority: High/Medium/Low)
   - Description
   - Impact
   - Recommendation

### Redundancy Analysis
- Servers with overlapping functionality
- Recommended actions

### Missing MCPs
- Suggested MCPs based on project type
- Installation commands

### Optimization Recommendations
1. Remove unused servers: [list]
2. Fix configuration errors: [list]
3. Add missing MCPs: [list]

### Next Steps
- [ ] Action item 1
- [ ] Action item 2

## Example Usage

"Run the mcp-configuration-review skill to audit my current setup"

## Notes
- Always backup settings before making changes
- Test one MCP change at a time
- Restart Claude Code after configuration changes
- Check MCP server logs if issues persist
- Some MCPs require external services (API keys, running databases)

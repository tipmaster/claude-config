#!/usr/bin/env node

// This is a wrapper to run the Chrome MCP server with Node.js
import('./dist/server.js').catch(error => {
  console.error('Failed to start server:', error);
  process.exit(1);
});
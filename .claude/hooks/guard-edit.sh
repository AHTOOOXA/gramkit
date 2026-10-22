#!/usr/bin/env bash
# PreToolUse(Edit|Write|NotebookEdit): generated API clients are never hand-edited.
path=$(jq -r '.tool_input.file_path // .tool_input.notebook_path // empty')
case "$path" in
    */frontend/src/gen/*|*/frontend/src/schema/*|*/frontend/gen/*)
        jq -n '{hookSpecificOutput: {hookEventName: "PreToolUse", permissionDecision: "deny", permissionDecisionReason: "Generated from the backend OpenAPI schema. Change the backend, then run make schema APP=<app> and check git status src/gen (Kubb sometimes deletes files mid-run; rerun)."}}'
        ;;
esac
exit 0

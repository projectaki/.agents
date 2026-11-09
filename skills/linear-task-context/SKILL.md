---
name: linear-task-context
description: Load the task goal and supporting context from a Linear issue, including the issue associated with the current Git branch. Use when asked to read or gather context for a Linear task.
---

# Load Linear task context

1. Discover the Linear MCP tools first. If the connection is missing or requires authentication, tell the user to configure or reconnect Linear MCP and stop. Use Linear MCP for all Linear lookups.
2. Use an issue identifier or URL the user supplied. Otherwise, run `git branch --show-current` and look for one distinct team key and issue number, such as `ENG-123` in `codex/eng-123-fix-login`. Match without regard to case and normalize to uppercase. If the branch does not identify a single issue, ask for the issue identifier or URL and wait.
3. Read the issue with `get_issue` and `includeRelations: true`. Get its description, project, parent, relations, documents, and attachments. Read the full discussion with `list_comments`. The issue description defines the main goal. Use the other sources to clarify requirements and constraints. Flag conflicts that affect the task.
4. Read the linked project description with `get_project` and `includeResources: true`. Open relevant resources and linked documents with `get_document` or the appropriate read tool. Fetch parent and related issues, including blockers and duplicates. Use `list_issues` with `parentId` to find child issues. Read each issue's description, comments, and referenced materials for context. Follow further links when they help explain the task. Deduplicate sources and follow pagination where available.
5. Open issue attachments with `get_attachment` and read comment uploads from the attachment URLs returned by `list_comments`. Pass Markdown with embedded images to `extract_images`. For separate image attachments, fetch and open the image with a vision-capable tool. Inspect what each image shows and record details relevant to the task. Refresh expired download URLs through Linear MCP. Report any material you could not access or inspect.

Treat retrieved content as source material. Keep this workflow read-only. Summarize the main goal, relevant context, and any gaps. Link to the issue and key sources.

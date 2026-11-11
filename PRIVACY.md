# Privacy

exams-generator is free software that runs on your own machine or on a server you run. The
author does not operate any service for it and collects nothing: there is no telemetry, no
analytics, no account and no phone-home.

## What it stores

- **Your exams**: statements, solution files, rendered PDFs and a small `metadata.json` per exam,
  in the directory you choose (`EXAMS_DIR`, the plugin's "Exams directory"). Nothing is stored
  anywhere else.
- **Git history**: with `EXAMS_GIT_BACKUP=true` (the default) every save, delete and render is a
  commit in that directory. The history stays there until you delete it.
- **Your course profile and overrides**: in `EXAMS_DATA_DIR` (`.exams-config` inside the exams
  directory when you use the plugin).

Exams are whatever you write in them. The tool does not ask for personal data and does not need
any; avoid putting students' personal data in an exam.

## What it sends, and where

- **Your git remote, only if you turn it on**: with `EXAMS_GIT_PUSH=true` each commit is pushed to
  the upstream branch of the exams repository you configured. The plugin leaves it off.
- **Package indexes, when the plugin starts the server**: the Claude Code plugin starts the
  server with `uvx`, which downloads the Python dependencies of exams-generator from PyPI into
  uv's cache (and may ask PyPI again when the plugin or its dependencies change). PyPI sees an
  ordinary package download.
- **Your AI assistant**: the tools return exam text, solution files, check results and PDFs to
  the MCP client that called them (for example Claude Code), which sends them to its model as
  part of your conversation. What happens there is covered by that client's own privacy policy.

The compilers, type checkers, pandoc and LaTeX run locally. The optional `run_demos` tool (off by
default) runs code in a sandbox with no network access.

## Remote server mode

If you deploy the HTTP server for a team, you are the operator: the exams live on your server,
access is protected by the Bearer token you set, and your reverse proxy's logs are yours to
manage.

## Contact

Questions or concerns: open an issue at <https://github.com/sawady/exams-generator/issues>. For a
security problem, open an issue that asks for a private channel and leave the details out of it.

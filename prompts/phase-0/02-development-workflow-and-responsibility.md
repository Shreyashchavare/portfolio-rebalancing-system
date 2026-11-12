# Phase 0 — Development Workflow and Responsibility

## AI-assisted workflow
The original prompt archive identifies these tools:
- **ChatGPT:** technical guidance, architecture decisions, planning, testing strategy and code review.
- **Antigravity:** implementation assistance, code generation and debugging.
- **Claude:** documentation assistance.

## Working rules
1. AI-generated code must be reviewed before acceptance.
2. Run tests before marking functionality complete.
3. Review architecture and technical decisions manually.
4. Do not accept generated code without understanding its behavior.
5. Record relevant prompts and AI assistance transparently.
6. Do not weaken tests or alter Git history to manufacture a passing result.

## Human responsibility
The developer remains responsible for architecture, implementation review, testing, debugging, integration, security and final submission.

## Phase record format
Keep only useful history:
- Objective and scope.
- Important requirements and decisions.
- Files or capabilities added.
- Verification performed and actual result.
- Known limitations or follow-up work.

Avoid retaining repeated prompts, long terminal transcripts, routine progress messages and duplicated test output.

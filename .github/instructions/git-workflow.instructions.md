---
applyTo: "**"
description: "Use when handling commit, branch, pull request, or GitHub MCP workflows. Enforces Conventional Commits, PR title format from branch keys + normalized branch content, version suffix rules, and default PR base branch dev."
---

# Git Workflow Rules

These rules are mandatory when creating commits or pull requests in this repository.

## Branch And PR Context

- Default PR base branch: `dev`.
- Derive ticket keys from current branch name when possible.
- Expected key patterns:
  - `DATN-<number>`
  - `BE-<number>`
- PR title format:
  - `[DATN-107][BE-0020] <short-title>`
- `<short-title>` is derived from branch content and should preserve the branch meaning.
- Only remove redundant tokens from branch name when deriving `<short-title>`:
  - branch type prefixes (e.g. `feature/`, `fix/`, `chore/`)
  - ticket keys already shown in title prefix (e.g. `DATN-107`, `BE-0020`)
  - separators like `/`, `-`, `_` converted to spaces
- Do not rewrite to a different wording if branch content is already clear.
- If the same title already exists in PRs merged into `dev`, append version suffix:
  - second occurrence: `(ver2)`
  - third occurrence: `(ver3)`
  - and so on.
- If one or both keys are missing from branch name, ask the user before creating the PR.

## Commit Rules (Conventional Commits)

- Always use Conventional Commits format:
  - `<type>(<scope>): <subject>`
- Allowed `type` values:
  - `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `build`, `ci`, `chore`, `revert`
- Commit subject requirements:
  - imperative mood
  - lower-case start (unless proper noun)
  - no trailing period
  - concise and specific
- Keep commits atomic and logically grouped.
- Do not include unrelated file changes in the same commit.

## Pull Request Rules

- Use branch-derived keys in the PR title.
- Use normalized branch content in PR title trailing text (remove redundant parts only).
- Before creating PR, check merged PR titles targeting `dev` to determine whether a `(verN)` suffix is required.
- PR body must include these sections:
  - `Why`
  - `What Changed`
  - `DB/Migration Impact`
  - `API Impact`
  - `Test Evidence`
  - `Risks and Rollback`
- If DB schema changes exist, explicitly list migration and seed updates.
- If API contract changes exist, explicitly list request/response changes.

## Safety And MCP Behavior

- Before creating a PR with GitHub MCP, confirm:
  - `owner`
  - `repo`
  - `head` branch
  - `base` branch (`dev` unless user overrides)
- Never force-push unless explicitly requested.
- Never amend published commits unless explicitly requested.
- If checks cannot be run, state that clearly in PR body under `Test Evidence`.

## Examples

- Commit:
  - `feat(test-histories): add streak and level notices in submit response`
- PR title:
  - `[DATN-107][BE-0020] streak level notice`
  - `[DATN-107][BE-0020] streak level notice (ver2)`

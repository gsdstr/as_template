# Agentic Stack Template

Portable agent infrastructure extracted from a project without application code or project history.

## Included

- Root `AGENTS.md` adapter and the `.agents/AGENTS.md` brain map.
- Agent protocols.
- Portable skills: `caveman`, `caveman-commit`, `caveman-review`, `planning-with-files`, and the memory-skill suite.
- An empty, Git-trackable memory-directory skeleton.

## Intentionally excluded

- `tv_ai-bridge` and every other product/runtime artifact.
- The `orca-cli` and `orchestration` skills.
- All accumulated memory records, planning state, dependencies, Git metadata, and local lockfiles.

## Use

Copy this directory into a new project, then initialize its memory files for that project. The supplied rules and skills treat memory as project-owned data; do not copy another project's records into it.

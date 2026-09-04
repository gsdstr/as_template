# Ageroot Setup and Updates

<!-- generated-by: ageroot; template: <template-version>; commit: <short-git-commit>; rendered-at: <ISO-8601 timestamp> -->

Use this document only when installing, configuring, or updating Ageroot. Do not
load it during normal agent startup.

## Configuration and state

- `.agents/ageroot.config.yaml` contains installation-specific render inputs and global policies.
- `.agents/ageroot.state.yaml` records installed template version, managed paths,
  each path's render strategy, and snapshot references/hashes.
- The state file is authoritative. Generated-file comments are informational.

### `ageroot.config.yaml`

```yaml
schema: 1
snapshots: enabled
project:
  name: <project-name>
agent:
  language: en
```

- `schema` — configuration format version.
- `snapshots` — snapshot persistence policy: `enabled` (default) or `disabled`.
- `project.name` — project name available to rendered templates.
- `agent.language` — documentation and generated-text language.

Add new render inputs under an existing top-level group or a documented new
group. Do not place installation state or generated-file hashes here.

### `ageroot.state.yaml`

```yaml
schema: 1
template:
  name: ageroot
  version: <template-version>
  source: <template-source>
  commit: <short-git-commit>
installed_at: <ISO-8601 timestamp>
rendered_at: <ISO-8601 timestamp>
managed_files:
  - path: .agents/AGENTS.md
    strategy: generated
    snapshot: .agents/snapshots/AGENTS.md
    sha256: <sha256-hex>
  - path: .agents/skills/
    strategy: external-link
```

- `schema` — state format version.
- `template` — source identity, installed template version, and short Git commit.
- `installed_at` / `rendered_at` — installation and most recent render times.
- `managed_files` — paths Ageroot examines during dry-run, with their render
  strategy, snapshot reference, and SHA-256 integrity hash.

Only Ageroot updates this file after approved installation or update work.

## Safety-first dry-run comparison and update protocol

Ageroot uses a safety-first dry-run comparison before any update is applied.

1. **Render**: Re-render every managed template from current configuration and templates.
2. **Normalize**: Deterministically normalize content (line endings, final newline, trailing whitespace, safe Markdown/YAML formatting noise, and `generated-by` provenance fields without altering YAML data/ordering or Markdown text/structure). A difference solely in the `generated-by` template version, commit, or render timestamp is metadata-only: classify it as `unchanged` and omit it from the diff.
3. **Compare**:
   - **Renderer-owned (`generated`, `managed-regions`)**: Perform three-way comparison between `current`, `new render`, and `prior rendered snapshot`.
     - When `snapshots: disabled`, legacy installations without snapshots, or after an explicit one-time override: perform two-way `unverified` comparison and label clearly.
     - If snapshot persistence is enabled but a snapshot is missing or corrupted (SHA-256 mismatch), escalate to user for cancellation or a one-time unverified override. Never silently replace the baseline.
     - For `managed-regions`: structurally validate region markers. If valid, build a proposed region merge (preserving user regions, replacing generated regions, warning on local edits). If markers are malformed, missing, unpaired, or moved, classify as `blocked`. If generated regions have concurrent local edits, classify as `conflict`.
   - **`external-link`**: Validate link exists and resolves to expected target. Do not diff target contents or apply changes to them.
   - **Deletions**: If a previously managed file is absent from new render, classify as `deletion-pending`. If locally modified vs baseline, classify as `blocked`.
4. **Classify**: Assign each path a result class:
   - `unchanged` (eligible)
   - `changed` (eligible)
   - `unverified` (eligible)
   - `region-merge` (eligible)
   - `conflict` (blocks atomic apply)
   - `blocked` (blocks atomic apply)
   - `invalid-link` (blocks atomic apply)
   - `deletion-pending` (requires separate explicit deletion confirmation; blocks ordinary update)
5. **Report (Summary-first confirmation)**:
   - Present a tiered summary: counts for `changed` and `unchanged` paths; path-level reason, apply eligibility, and full-diff access for `conflict` and `blocked` paths.
   - Summary alone permits confirmation; complete diffs remain available on request.
   - Exclude `.planning/` completely from Ageroot discovery, rendering, comparison, and reporting; it belongs to the planning-with-files skill.
6. **Confirm**: Wait for explicit user confirmation before applying.
7. **Atomic apply**:
   - Only apply if all paths are eligible (`changed`, `unverified`, `region-merge`, `unchanged`).
   - If any path is `conflict`, `blocked`, `invalid-link`, or `deletion-pending`, apply is blocked.
   - Separate explicit confirmation is required for `deletion-pending`.
   - After all changes succeed, atomically persist new snapshots into `.agents/snapshots/`, compute SHA-256 hashes, and commit `.agents/ageroot.state.yaml`. Do not leave partial snapshot history.

Never apply an update before explicit confirmation.

## Render strategies

| Strategy | Update behavior |
| --- | --- |
| `generated` | Re-rendered from template and configuration; three-way baseline compared. |
| `managed-regions` | Updates generated regions while preserving declared user regions; requires intact markers. |
| `external-link` | Managed by an external tool; Ageroot validates link presence and target resolution only. |

`PREFERENCES.md` is generated from its template and remains user-editable. Its
changes appear in the dry-run diff and require user confirmation before applying
an update.

Skills are `external-link`: [skills-manager](https://github.com/xingkongliang/skills-manager)
manages project symlinks to `~/.skills-manager`.

## Generated Markdown marker

Rendered Markdown files use this marker when their format permits it:

```md
<!-- generated-by: ageroot; template: <version>; commit: <short-git-commit>; rendered-at: <ISO-8601 timestamp> -->
```

The marker does not restrict edits and cannot replace state tracking.

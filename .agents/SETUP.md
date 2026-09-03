# Ageroot Setup and Updates

<!-- generated-by: ageroot; template: <template-version>; commit: <short-git-commit>; rendered-at: <ISO-8601 timestamp> -->

Use this document only when installing, configuring, or updating Ageroot. Do not
load it during normal agent startup.

## Configuration and state

- `.agents/ageroot.config.yaml` contains installation-specific render inputs.
- `.agents/ageroot.state.yaml` records installed template version, managed paths,
  and each path's render strategy.
- The state file is authoritative. Generated-file comments are informational.

### `ageroot.config.yaml`

```yaml
schema: 1
project:
  name: <project-name>
agent:
  language: en
```

- `schema` — configuration format version.
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
```

- `schema` — state format version.
- `template` — source identity, installed template version, and short Git commit.
- `installed_at` / `rendered_at` — installation and most recent render times.
- `managed_files` — paths Ageroot examines during dry-run, with their render
  strategy.

Only Ageroot updates this file after approved installation or update work.

## Update protocol

1. Render every managed template using current configuration.
2. Run a dry comparison for every managed file.
3. Present the complete diff and a concise change summary.
4. Wait for explicit user confirmation.
5. Apply only the confirmed changes, then update Ageroot state.

Never apply an update before confirmation. The file-comparison protocol may be
improved in future versions without changing this approval requirement.

## Render strategies

| Strategy | Update behavior |
| --- | --- |
| `generated` | Re-rendered from template and configuration. |
| `managed-regions` | Updates generated regions while preserving declared user regions. |
| `external-link` | Managed by an external tool; Ageroot does not render its contents. |

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

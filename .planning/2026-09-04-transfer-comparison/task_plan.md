# Task Plan: Transfer safety-first comparison to template

## Goal

Move the safety-first comparison implementation and its source documentation into `ageroot_template`, then remove the accidental outer-repository copies.

## Next Step

Copy implementation and source documentation into the template repository.

## Current Phase

Phase 1: Transfer

## Phases

### Phase 1: Transfer

- [x] Inspect template repository and instructions.
- [ ] Transfer implementation, configuration, documentation, and tests.
- **Status:** in_progress

### Phase 2: Verify and commit

- [ ] Run tests in the template repository.
- [ ] Commit the template change.
- **Status:** pending

### Phase 3: Remove outer copies

- [ ] Revert the accidental outer-repository implementation commits.
- [ ] Verify both repositories.
- **Status:** pending

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| `ageroot_template` is the implementation source of truth. | User explicitly requested the transfer. |

## Errors Encountered

| Error | Attempt | Resolution |
|-------|---------|------------|
| None | 1 | N/A |

# Architecture Decision Records

An Architecture Decision Record (ADR) captures a significant architectural decision, the context that drove it, and its consequences — so future contributors (including future us) understand *why* the code looks the way it does, not just what it does.

## Conventions

- **File naming**: `NNNN-kebab-case-title.md`, zero-padded to 4 digits (e.g. `0001-protocol-based-dependency-injection.md`).
- **Numbering**: sequential, never reused or renumbered — even if a later ADR supersedes an earlier one, the earlier number stays assigned to its original file.
- **Status**: one of `Proposed`, `Accepted`, `Superseded by ADR-000X`, `Deprecated`.
- **Structure**: Title, Status, Context, Decision, Consequences, and (where useful) Alternatives Considered. Kept lightweight and proportionate to project size — no formal scoring tables.

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-protocol-based-dependency-injection.md) | Use `typing.Protocol` interfaces for service-layer dependency injection | Accepted |

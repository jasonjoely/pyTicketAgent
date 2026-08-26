# 0001. Use `typing.Protocol` interfaces for service-layer dependency injection

## Status

Accepted

## Context

pyTicketAgent's FastAPI app already wires its whole dependency graph through FastAPI's native `Depends()` mechanism (`pyticketagent_api/dependencies.py`). That's the modern, industry-standard approach for FastAPI apps — no third-party DI container (`dependency-injector`, `punq`, etc.) is warranted, since FastAPI's own `Depends()` graph already fills that role.

The gap was not the wiring mechanism, it was the *typing*: service constructors took concrete classes as their collaborators instead of abstractions —

- `TicketAssistService` and `SearchAssistService` both took `ticket_repository`/`hybrid_search_service`, `registry: JsonAiProviderRegistry`, `binding_resolver: EnvVarAiModelBindingResolver`, and `chat_client_factory: ChatClientFactory` as concrete types.

This meant nothing could be substituted for testing without subclassing or monkeypatching. Two concrete, observable consequences of this:

1. **`TicketAssistService` and `SearchAssistService` had zero unit tests.** They're impossible to exercise in isolation because their constructors demand real `JsonAiProviderRegistry`, `EnvVarAiModelBindingResolver`, and `ChatClientFactory` instances — the last of which does live `os.environ` lookups and can construct real network-bound chat clients. `TRADEOFFS.md` already listed "add unit tests for ... search-assist LLM JSON extraction" as a known gap.
2. **Existing tests already worked around this by hand.** `tests/unit/api/test_ticket_hybrid_search_service.py` and `test_ticket_ingest_embedding.py` define duck-typed fake classes (`_FakeTicketRepository`) and pass them into constructors with `# type: ignore[arg-type]`, purely because `TicketRepository` wasn't a `Protocol` and so a fake wasn't assignable to it as far as a type checker was concerned.

The codebase already had a working precedent for the fix: `ChatClient` (`pyticketagent_core/ai/chat_client.py`) and `EmbeddingClient` (`pyticketagent_core/embeddings/embedding_client.py`) are `typing.Protocol` interfaces (PEP 544, structural typing) with clean domain names, implemented by technology-prefixed concrete adapters (`GeminiChatClient`, `GroqChatClient`, `OllamaChatClient`, `FastEmbedEmbeddingClient`, `OllamaEmbeddingClient`) — no explicit inheritance required. Fakes conforming to those two Protocols already type-check cleanly in tests with no suppression comments.

## Decision

Extend the existing `Protocol` pattern one layer up, to the four collaborators of `TicketAssistService`/`SearchAssistService` that sit at an I/O boundary:

| Protocol | Method(s) | Concrete adapter |
|---|---|---|
| `TicketRepository` (`pyticketagent_core/data/ticket_repository.py`) | `get_by_id`, `get_embedding_meta`, `search_fts`, `search_semantic`, `upsert` | `AsyncpgTicketRepository` (`data/asyncpg_ticket_repository.py`) |
| `AiProviderRegistry` (`pyticketagent_core/ai/ai_provider_registry.py`) | `get_provider` | `JsonAiProviderRegistry` (unchanged, already adapter-named) |
| `AiModelBindingResolver` (`pyticketagent_core/ai/ai_model_binding_resolver.py`) | `resolve_binding` | `EnvVarAiModelBindingResolver` (unchanged, already adapter-named) |
| `ChatClientFactory` (`pyticketagent_core/ai/chat_client_factory.py`) | `create_client` | `ProviderChatClientFactory` (`ai/provider_chat_client_factory.py`) |

Naming convention: the Protocol keeps the clean domain name; the concrete implementation gets a technology-prefixed name. This matches `ChatClient`/`EmbeddingClient` exactly, so the whole codebase now follows one consistent rule instead of two.

FastAPI's `Depends()` remains the sole DI mechanism — this decision changes only how collaborators are *typed*, not how they're *wired*. `dependencies.py` still hand-assembles the object graph; it now constructs the renamed adapters and returns/accepts them through the new Protocol types.

Explicitly out of scope for this decision:

- `TicketAssistService`, `SearchAssistService`, `TicketIngestService`, `TicketHybridSearchService` stay concrete. They're application/orchestration services, not swappable I/O adapters, and FastAPI's per-request `Depends()` graph already gives them a natural test seam at their constructor arguments.
- `TicketAssistPromptBuilder`/`SearchAssistPromptBuilder` stay concrete — stateless, pure, no I/O.
- `Settings` stays a single `pydantic_settings.BaseSettings` object passed whole into services, rather than being split into narrower per-consumer Protocols.

## Consequences

**Positive:**

- `TicketAssistService` and `SearchAssistService` are now unit-testable in isolation with structurally-typed fakes (`tests/unit/api/test_ticket_assist_service.py`, `test_search_assist_service.py`), closing the gap `TRADEOFFS.md` called out.
- The `# type: ignore[arg-type]` workarounds in `test_ticket_hybrid_search_service.py` and `test_ticket_ingest_embedding.py` are gone — their existing fakes now satisfy `TicketRepository` structurally once they implement its full method set.
- One consistent interface convention across the whole codebase, instead of `Protocol` in two places and concrete coupling everywhere else.
- No new runtime dependency.

**Trade-offs:**

- Renaming `TicketRepository` → `AsyncpgTicketRepository` and `ChatClientFactory` → `ProviderChatClientFactory` touched imports across `dependencies.py` and the two assist services.
- Each converted boundary is now two files (Protocol + adapter) instead of one.
- This ADR deliberately covers only four collaborators — extending `Protocol` further (e.g. to `TicketHybridSearchService` or the prompt builders) is a separate future decision, not implied by this one.

## Alternatives Considered

- **`abc.ABC` + `@abstractmethod`** — rejected. Requires explicit inheritance from every adapter, doesn't match the `Protocol` precedent already established by `ChatClient`/`EmbeddingClient`, and PEP 544 structural typing already gives this codebase everything it needs without that coupling.
- **A third-party DI container** (`dependency-injector`, `punq`, etc.) — rejected. FastAPI's own `Depends()` graph already serves as the container; adopting one would add ceremony without solving a problem this app actually has.
- **`unittest.mock.Mock`/`MagicMock` instead of Protocols** — rejected. Loses static type-checking of the fakes and breaks from the codebase's existing hand-written-fake test style.

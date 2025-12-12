# PRD: Smart Context System for Spec Creation

> **Status:** Draft v2 (Revised)
> **Author:** Claude
> **Created:** 2025-12-11
> **Revised:** 2025-12-11
> **Target:** Auto Claude Spec Creation Pipeline

---

## 0. System Context

### Auto Claude Architecture Overview

Auto Claude is a multi-agent autonomous coding framework with four main entry points:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AUTO CLAUDE SYSTEM                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐             │
│  │ ROADMAP         │  │ IDEATION        │  │ SPEC CREATION   │             │
│  │ roadmap_runner  │  │ ideation_runner │  │ spec_runner     │             │
│  │                 │  │                 │  │                 │             │
│  │ • Discovery     │  │ • Low Hanging   │  │ • Complexity    │             │
│  │ • Features      │  │ • UI/UX         │  │ • Requirements  │             │
│  │                 │  │ • High Value    │  │ • Research      │             │
│  │                 │  │ • Security      │  │ • Context       │             │
│  │                 │  │ • Performance   │  │ • Spec Writing  │             │
│  │                 │  │ • Code Quality  │  │ • Critique      │             │
│  │                 │  │ • Documentation │  │ • Planning      │             │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘             │
│           │                    │                    │                       │
│           └────────────────────┴────────────────────┘                       │
│                                │                                            │
│                                ▼                                            │
│                    ┌─────────────────────┐                                  │
│                    │ IMPLEMENTATION      │                                  │
│                    │ run.py → agent.py   │                                  │
│                    │                     │                                  │
│                    │ • Coordinator       │                                  │
│                    │ • Coder Sessions    │                                  │
│                    │ • QA Loop           │                                  │
│                    │ • Worktree Mgmt     │                                  │
│                    └────────┬────────────┘                                  │
│                             │                                               │
│                             ▼                                               │
│                    ┌─────────────────────┐                                  │
│                    │ MEMORY LAYER        │                                  │
│                    │                     │                                  │
│                    │ • Graphiti          │◄── PRIMARY (semantic memory)     │
│                    │   graphiti_memory   │                                  │
│                    │                     │                                  │
│                    │ • File-based        │◄── LITE MODE (optional fallback) │
│                    │   memory.py         │                                  │
│                    └─────────────────────┘                                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Current Memory Flow (The Gap)

```
                          CURRENT STATE
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ROADMAP          IDEATION         SPEC CREATION      IMPLEMENTATION      │
│      │                │                  │                   │              │
│      ▼                ▼                  ▼                   ▼              │
│   [No memory]     [No memory]        [No memory]      ┌──────────────┐     │
│                                                       │ MEMORY LAYER │     │
│                                                       │              │     │
│   ════════════════════════════════════════════════════│ • Patterns   │     │
│   These phases analyze the codebase from scratch      │ • Gotchas    │     │
│   every time, missing valuable historical learnings   │ • Insights   │     │
│   ════════════════════════════════════════════════════│ • Outcomes   │     │
│                                                       └──────────────┘     │
│                                                              ▲              │
│                                                              │              │
│                                           Only coder sessions write/read    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### User Journey (End-to-End)

```
1. PROJECT CONNECTION
   └── User runs: python auto-claude/analyzer.py
       └── Creates: project_index.json (services, tech stack, ports)

2. ROADMAP (Optional)
   └── User runs: python auto-claude/roadmap_runner.py
       ├── Phase 1: Project Analysis (reuses project_index.json)
       ├── Phase 2: Discovery (interactive - understand audience, vision)
       └── Phase 3: Feature Generation (prioritized feature list)
       └── Creates: roadmap.json, roadmap_discovery.json

3. IDEATION (Optional)
   └── User runs: python auto-claude/ideation_runner.py
       ├── Phase 1: Project Analysis (reuses project_index.json)
       ├── Phase 2: Context Gathering (tech stack, planned features)
       └── Phase 3+: Parallel Ideation Agents (7 types)
       └── Creates: ideation.json, *_ideas.json files

4. SPEC CREATION
   └── User runs: python auto-claude/spec_runner.py --task "..."
       ├── Phase 1: Complexity Assessment → complexity_assessment.json
       ├── Phase 2: Requirements Gathering → requirements.json
       ├── Phase 3: Research (conditional) → research.json
       ├── Phase 4: Context Discovery → context.json
       ├── Phase 5: Spec Writing → spec.md
       ├── Phase 6: Self-Critique (complex only) → critique_report.json
       ├── Phase 7: Planning → implementation_plan.json
       └── Phase 8: Validation

5. IMPLEMENTATION
   └── User runs: python auto-claude/run.py --spec 001
       ├── Workspace Setup (worktree isolation)
       ├── Coder Sessions (implement chunks)
       │   ├── Read spec, plan, memory
       │   ├── Implement chunk
       │   ├── Self-critique
       │   ├── Verify
       │   ├── Commit
       │   └── Write session insights to memory/
       ├── QA Validation Loop
       │   ├── Run tests (unit, integration, e2e)
       │   ├── Browser verification
       │   ├── Code review
       │   └── Approve or Reject (→ QA Fix Loop)
       └── User Decision: --merge, --review, or --discard

6. TASK COMPLETE
   └── Code merged into project
   └── Memory preserved for future tasks
```

### Files Created Per Phase

| Phase | Files Created | Consumed By |
|-------|---------------|-------------|
| **Analyzer** | `project_index.json` | All phases |
| **Roadmap** | `roadmap.json`, `roadmap_discovery.json` | Ideation, Spec |
| **Ideation** | `ideation.json`, `*_ideas.json` | User review |
| **Spec: Complexity** | `complexity_assessment.json` | Spec orchestrator |
| **Spec: Requirements** | `requirements.json` | Spec writer, Planner |
| **Spec: Research** | `research.json` | Spec writer, Critic |
| **Spec: Context** | `context.json` | Spec writer, Planner, Coder |
| **Spec: Writer** | `spec.md` | All implementation phases |
| **Spec: Critic** | `critique_report.json` | Spec validation |
| **Spec: Planner** | `implementation_plan.json`, `init.sh` | Coder, QA |
| **Implementation** | Code changes, commits | QA |
| **Implementation** | `memory/session_*.json` | Next session |
| **Implementation** | `memory/codebase_map.json` | Next session |
| **Implementation** | `memory/patterns.md`, `gotchas.md` | Next session |
| **QA** | `qa_report.md`, `QA_FIX_REQUEST.md` | QA Fixer |

### Proposed Memory Flow (After This PRD)

```
                          PROPOSED STATE
┌─────────────────────────────────────────────────────────────────────────────┐
│                                                                             │
│   ROADMAP          IDEATION         SPEC CREATION      IMPLEMENTATION      │
│      │                │                  │                   │              │
│      ▼                ▼                  ▼                   ▼              │
│  ┌────────┐      ┌────────┐        ┌──────────┐       ┌──────────────┐     │
│  │ Graph  │      │ Graph  │        │ Full     │       │ MEMORY LAYER │     │
│  │ Hints  │      │ Hints  │        │ Historical│       │              │     │
│  │ (500t) │      │ (500t) │        │ Context  │       │ • Patterns   │     │
│  └────┬───┘      └────┬───┘        │ (2000t)  │       │ • Gotchas    │     │
│       │               │            └────┬─────┘       │ • Insights   │     │
│       │               │                 │             │ • Outcomes   │     │
│       └───────────────┴─────────────────┴─────────────┤              │     │
│                                                       └──────────────┘     │
│                                                              ▲  │          │
│                                                              │  │          │
│                         ◄────────────────────────────────────┘  │          │
│                         Bidirectional: All phases read AND write│          │
│                         ────────────────────────────────────────►          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘

Key Changes:
• Roadmap gets lightweight graph hints (constraints, existing features)
• Ideation gets graph hints (patterns to extend, features to avoid)
• Spec Creation gets full historical context (similar tasks, gotchas)
• QA outcomes feed back into memory for future specs
• Project-level group_id enables cross-spec learning
```

### Memory Data Types

| Data Type | Written By | Read By | Storage |
|-----------|------------|---------|---------|
| **Session Insights** | Coder | Coder, Spec | Graphiti (primary) + File (lite mode) |
| **Codebase Map** | Coder | Coder, Spec | Graphiti (primary) + File (lite mode) |
| **Patterns** | Coder | Coder, Spec, Ideation | Graphiti (primary) + File (lite mode) |
| **Gotchas** | Coder, QA | Coder, Spec, Ideation | Graphiti (primary) + File (lite mode) |
| **QA Outcomes** | QA Loop | Spec (historical) | Graphiti (primary) + File (lite mode) |
| **Dismissed Ideas** | User (via ideation_runner) | Ideation | Graphiti (primary) + File (lite mode) |
| **Discarded Specs** | User (via run.py --discard) | Spec Creation, Ideation | Graphiti (primary) + File (lite mode) |
| **Complexity Calibration** | QA Loop (on complete) | Complexity Assessor | Graphiti (primary) + File (lite mode) |
| **Context Accuracy** | Coder (on complete) | Context Discovery | Graphiti (primary) + File (lite mode) |
| **Cross-Spec Index** | All writers | Historical Context | Graphiti (primary) + File (lite mode) |

### Complete Learning Loops Summary

The self-improving system relies on **15 feedback loops** that compound over time:

| Loop | Signal Source | What's Learned | Benefit |
|------|---------------|----------------|---------|
| **1. Direct Learning** | Coder sessions | Patterns, gotchas, file purposes | Next session starts smarter |
| **2. QA Feedback** | QA rejections | Critical issues, missing patterns | Prevents repeated failures |
| **2.5. Ideation Preferences** | User dismissals | Feature types to avoid | More relevant suggestions |
| **3. Cross-Spec Learning** | Similar past tasks | Successful approaches | Faster implementation |
| **4. Statistical Learning** | 200+ specs data | Chunk complexity patterns | Better planning |
| **5. Architectural Learning** | File change tracking | Dependency graph | Impact prediction |
| **6. Discard Learning** | User --discard | Why specs fail | Earlier warnings |
| **7. Complexity Calibration** | Actual vs predicted | This codebase's complexity profile | Accurate estimates |
| **8. Spec Edit Learning** | User edits to spec.md | Spec writer gaps | Better specs |
| **9. Context Accuracy** | Files used vs included | What's actually relevant | Less noise, faster discovery |
| **10. Research Value** | Research used vs ignored | Valuable research queries | Focused research |
| **11. Recovery Learning** | Stuck chunk recovery | What fixes work here | Faster recovery |
| **12. Time Estimation** | Actual time spent | This project's pace | Realistic estimates |
| **13. Roadmap Priority** | User feature selection | Unstated priorities | Better prioritization |
| **14. Requirements Learning** | Q&A during gathering | Project conventions | Fewer clarifications needed |
| **15. Merge Follow-up** | Post-merge issues | Long-term regressions | Safer patterns |

**Implementation Status:**
- ✅ Loops 1-5: Documented in this PRD (core implementation)
- 🆕 Loop 2.5: Added via ideation dismissal tracking
- 📋 Loops 6-15: Documented as future enhancements (Section 12.6.1)

### Memory Storage Policy

**Graphiti is the primary memory store.** File storage is an optional "lite mode" fallback for users who don't want Graphiti, or when Graphiti is unavailable.

This ensures:
- Rich semantic retrieval is the default path (higher quality context)
- System can still function in a "lite mode" without Graphiti
- Clear operational fallback when Graphiti is unavailable (startup, outage, misconfig)

---

## 1. Problem Statement

### Current State

The Auto Claude spec creation pipeline has **three disconnected context-gathering mechanisms**:

1. **Project Discovery** (`analyzer.py`) - Static project structure analysis
2. **Context Discovery** (`context.py`) - Keyword-based file search
3. **Graphiti Memory** (`graphiti_memory.py`) - Semantic graph storage

**Critical Gap:** Graphiti is only used during implementation (`agent.py`), NOT during spec creation when context matters most. Historical learnings (patterns that worked, gotchas to avoid, similar past tasks) are never surfaced to inform new specs.

### Impact

- Specs don't benefit from past project learnings
- Same mistakes get repeated across specs
- No semantic search during the most context-sensitive phase
- Cross-spec knowledge is siloed and inaccessible

### Evidence

| File | Current Behavior |
|------|------------------|
| `spec_runner.py` | No historical context phase |
| `context.py:227-279` | Pure keyword matching, no semantic search |
| `graphiti_memory.py:116-118` | Scoped to single spec via `group_id` |
| `prompts/spec_writer.md` | Only reads project_index, requirements, context - no history |

---

## 2. Goals & Success Metrics

### Goals

1. **Primary:** Surface historical learnings during spec creation
2. **Secondary:** Enable cross-spec pattern discovery
3. **Tertiary:** Improve context.json quality with semantic hints

### Success Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Specs using historical context | 0% | 100% (when history exists) |
| Cross-spec learning available | No | Yes |
| Context discovery keywords | Task-only | Task + historical hints |
| QA first-pass rate | Baseline | +15% improvement |
| Ideation acceptance rate | ~40% | +30% improvement (via dismissal learning) |

### Non-Goals

- Making file-based memory the primary system (it becomes a simpler fallback)
- Removing file-based storage entirely (lite mode remains available for users who opt out of Graphiti)
- Changing implementation phase behavior
- Auto-generating specs without user input

---

## 2.5 Extended Scope: Ideation Phase Integration

### Problem

The Ideation system (`ideation_runner.py`) generates feature ideas across 7 categories:
- Low-Hanging Fruit
- UI/UX Improvements
- High-Value Features
- Documentation Gaps
- Security Hardening
- Performance Optimizations
- Code Quality

**Current limitation:** Ideation agents analyze the codebase from scratch each time. They don't benefit from:
- Past implementation patterns that worked
- Known gotchas in this codebase
- Similar features that were already built
- What approaches failed before

### Proposed Solution: Lightweight Graph Queries for Ideation

Instead of loading full historical context (expensive, token-heavy), ideation agents should use **targeted graph queries** via Graphiti's semantic search.

#### Why Graph Queries Work for Ideation

1. **Token-Efficient:** Return only relevant nodes, not full documents
2. **Semantic Matching:** "payment flow" finds "Stripe checkout" even without keyword match
3. **Relationship Traversal:** Find connected patterns (auth → middleware → error handling)
4. **Pre-filtered:** Graph queries return ranked results, no post-processing needed

#### Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       IDEATION PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1: Project Analysis (existing)                                   │
│      └── project_index.json                                             │
│                                                                         │
│  Phase 2: Context Gathering (existing)                                  │
│      └── ideation_context.json                                          │
│                                                                         │
│  Phase 2.5: Graph Context Retrieval (NEW)  ◄─────────────────────────┐  │
│      │                                                               │  │
│      │   Query: "What patterns exist for {ideation_type}?"           │  │
│      │                                                               │  │
│      │   ┌─────────────────────────────────────────────┐             │  │
│      │   │ Graphiti Graph Query (if enabled)           │             │  │
│      │   │                                             │             │  │
│      │   │  • Search: patterns, gotchas, outcomes      │             │  │
│      │   │  • Filter: by ideation_type relevance       │             │  │
│      │   │  • Limit: 5 nodes max (token budget: 500)   │             │  │
│      │   │  • Format: bullet points, not full context  │             │  │
│      │   └─────────────────────────────────────────────┘             │  │
│      │                                                               │  │
│      └── ideation_hints.json (NEW, lightweight)                      │  │
│                                                                         │
│  Phase 3+: Ideation Agents (ENHANCED)                                   │
│      └── Now receive ideation_hints.json as optional input              │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

#### Implementation: `ideation_hints.json`

**Token Budget:** 500 tokens max (strict - ideation is already context-heavy)

**Schema:**
```json
{
  "ideation_type": "low_hanging_fruit",
  "relevant_patterns": [
    "CLI tools follow scripts/claude-tools/*.js pattern",
    "API endpoints use middleware chain in routes/"
  ],
  "avoid_duplicating": [
    "Task filtering already exists (see 003-task-filters)",
    "Dashboard refresh is implemented"
  ],
  "known_constraints": [
    "No direct database access from frontend",
    "All API calls must be authenticated"
  ],
  "query_used": "low hanging fruit patterns existing CLI",
  "sources": 3,
  "token_count": 287
}
```

#### Integration Points: Parallel Hint Retrieval

**CRITICAL:** Ideation currently runs 7 agents in PARALLEL. The graph hints phase must preserve this parallelism.

**File:** `ideation_runner.py`

```python
async def phase_graph_hints_all(self) -> dict[str, IdeationHints]:
    """
    Retrieve hints for ALL ideation types in parallel.
    This runs ONCE before ideation agents, not per-agent.
    """
    if not is_graphiti_enabled():
        return {}  # Empty hints - agents proceed without

    # Type-specific queries
    type_queries = {
        "low_hanging_fruit": "quick wins existing patterns CLI tools utilities",
        "ui_ux_improvements": "UI components styling accessibility user experience",
        "high_value_features": "major features integrations user value",
        "security_hardening": "security authentication authorization vulnerabilities",
        "performance_optimizations": "performance caching optimization slow queries",
        "code_quality": "refactoring patterns code smells technical debt",
        "documentation_gaps": "documentation comments API docs missing",
    }

    # PARALLEL queries - all 7 run simultaneously
    async with asyncio.TaskGroup() as tg:
        tasks = {
            itype: tg.create_task(self._get_type_hints(query))
            for itype, query in type_queries.items()
        }

    # Collect results
    all_hints = {}
    for itype, task in tasks.items():
        hints = await task
        if hints:  # Only include if we got relevant results
            all_hints[itype] = hints
            # Write per-type hints file
            self._write_hints_file(itype, hints)

    return all_hints


async def _get_type_hints(self, query: str) -> IdeationHints | None:
    """Get hints for a single ideation type."""
    results = await self.graphiti.search_project_learnings(query)

    # Filter by relevance (0.5 threshold, same as spec creation)
    relevant = [r for r in results if r.get("relevance", 0) >= 0.5]

    if not relevant:
        return None

    return IdeationHints(
        relevant_patterns=[r["content"] for r in relevant if r["type"] == "pattern"],
        avoid_duplicating=[r["content"] for r in relevant if r["type"] == "feature"],
        known_constraints=[r["content"] for r in relevant if r["type"] == "constraint"],
    )
```

**Execution Flow (Preserving Parallelism):**

```
Phase 1: Project Analysis
    │
    ▼
Phase 2: Context Gathering
    │
    ▼
Phase 2.5: Graph Hints (PARALLEL queries, ~1.5s total)
    │
    ├── Query: low_hanging_fruit ────┐
    ├── Query: ui_ux ────────────────┤
    ├── Query: high_value ───────────┤
    ├── Query: security ─────────────┼──→ All 7 queries run simultaneously
    ├── Query: performance ──────────┤
    ├── Query: code_quality ─────────┤
    └── Query: documentation ────────┘
    │
    ▼
Phase 3+: Ideation Agents (PARALLEL, unchanged)
    │
    ├── low_hanging_fruit_agent (reads its hints file)
    ├── ui_ux_agent (reads its hints file)
    ├── high_value_agent (reads its hints file)
    ├── security_agent (reads its hints file)
    ├── performance_agent (reads its hints file)
    ├── code_quality_agent (reads its hints file)
    └── documentation_agent (reads its hints file)
```

**Latency Impact:**
- Sequential approach (WRONG): 7 × 1-2s = 7-14s
- Parallel approach (CORRECT): ~1.5s (queries run simultaneously)

**Prompt Updates:**

Add to each ideation prompt (e.g., `ideation_low_hanging_fruit.md`):

```markdown
## OPTIONAL: Graph Hints

If `ideation_hints_{type}.json` exists, read it first:
- **relevant_patterns**: Patterns that worked in this codebase
- **avoid_duplicating**: Features that already exist (don't re-suggest)
- **known_constraints**: Technical limitations to respect

This is OPTIONAL context - if the file doesn't exist, proceed without it.
```

#### Ideation Retrieval: Relevance-Based (Not Token-Limited)

Like spec creation, ideation uses **relevance-based retrieval** with the 0.5 threshold:

| Scenario | Behavior |
|----------|----------|
| No relevant patterns | Empty hints file - agent proceeds fresh |
| 3 relevant patterns | Returns those 3 - no padding |
| 20 relevant patterns | Returns all 20 - doesn't truncate |
| Graphiti disabled | No hints files created - agents proceed without |

#### Ideation Dismissal Learning (Self-Improvement Loop)

**Problem:** When a user dismisses an ideation suggestion, that valuable feedback is lost. The ideation_runner will potentially suggest similar ideas again in future runs.

**Solution:** Track dismissed ideas in memory so ideation agents learn from user preferences over time.

##### How It Works

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    IDEATION DISMISSAL FEEDBACK LOOP                         │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. User reviews ideation output                                            │
│     └── Dismisses idea: "Add GraphQL API layer"                             │
│         └── Optional: Provides reason (too complex, not needed, etc.)       │
│                                                                             │
│  2. Ideation Runner records dismissal                                       │
│     └── Stores in Graphiti (primary) or file (lite mode):                   │
│         • dismissed_idea: "Add GraphQL API layer"                           │
│         • ideation_type: "high_value_features"                              │
│         • reason: "too_complex" (optional)                                  │
│         • timestamp: 2025-12-11T10:30:00Z                                   │
│         • dismissed_count: 1 (increments if similar dismissed again)        │
│                                                                             │
│  3. Next ideation run                                                       │
│     └── Phase 2.5 (Graph Hints) queries dismissed ideas                     │
│         └── ideation_hints.json includes "previously_dismissed" field       │
│                                                                             │
│  4. Ideation agents receive dismissal context                               │
│     └── Avoid suggesting:                                                   │
│         • Exact matches to dismissed ideas                                  │
│         • Similar ideas (semantic match > 0.8)                              │
│         • Ideas in same category if repeatedly dismissed                    │
│                                                                             │
│  5. Result: Increasingly personalized suggestions                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

##### Implementation: Dismissal Recording

**File:** `ideation_runner.py`

```python
async def record_dismissed_idea(
    self,
    idea_title: str,
    idea_description: str,
    ideation_type: str,
    reason: str | None = None
) -> None:
    """
    Record a dismissed idea to memory for future ideation runs.
    
    Args:
        idea_title: The title of the dismissed idea
        idea_description: Full description of the idea
        ideation_type: Category (e.g., "low_hanging_fruit", "security_hardening")
        reason: Optional user-provided reason for dismissal
    """
    dismissal = {
        "title": idea_title,
        "description": idea_description,
        "ideation_type": ideation_type,
        "reason": reason,
        "timestamp": datetime.now().isoformat(),
    }
    
    if is_graphiti_enabled():
        await self.graphiti.add_episode(
            name=f"Dismissed Idea: {idea_title}",
            episode_body=json.dumps(dismissal),
            source=EpisodeType.text,
            group_id=self.project_group_id,  # Project-level for cross-run learning
            metadata={
                "type": "dismissed_idea",
                "ideation_type": ideation_type,
                "reason": reason or "not_specified"
            }
        )
    
    # Also append to lite mode file for fallback
    dismissed_file = self.spec_dir / "dismissed_ideas.json"
    existing = json.loads(dismissed_file.read_text()) if dismissed_file.exists() else []
    existing.append(dismissal)
    dismissed_file.write_text(json.dumps(existing, indent=2))
```

##### Updated `ideation_hints.json` Schema

```json
{
  "ideation_type": "low_hanging_fruit",
  "relevant_patterns": [
    "CLI tools follow scripts/claude-tools/*.js pattern"
  ],
  "avoid_duplicating": [
    "Task filtering already exists (see 003-task-filters)"
  ],
  "previously_dismissed": [
    {
      "title": "Add keyboard shortcuts everywhere",
      "reason": "too_complex",
      "dismissed_at": "2025-12-01",
      "times_dismissed": 2
    },
    {
      "title": "Migrate to TypeScript strict mode",
      "reason": "breaking_change",
      "dismissed_at": "2025-12-05",
      "times_dismissed": 1
    }
  ],
  "known_constraints": [
    "No direct database access from frontend"
  ],
  "query_used": "low hanging fruit patterns existing CLI",
  "sources": 3,
  "token_count": 342
}
```

##### Dismissal Reasons (Standardized)

| Reason Code | Meaning | Ideation Should Learn |
|-------------|---------|----------------------|
| `too_complex` | Too much effort for now | Suggest simpler alternatives |
| `not_needed` | Feature not valuable for this project | Avoid similar suggestions |
| `breaking_change` | Would break existing functionality | Avoid disruptive ideas |
| `already_planned` | Already in roadmap elsewhere | Check roadmap.json first |
| `out_of_scope` | Doesn't fit project goals | Learn project boundaries |
| `duplicate` | Already exists (missed by system) | Improve duplicate detection |
| `deferred` | Good idea, but not now | Re-suggest after N months |
| `other` | Unspecified | Record but don't over-weight |

##### Dismissal Query in Graph Hints

```python
async def _get_type_hints(self, query: str, ideation_type: str) -> IdeationHints | None:
    """Get hints for a single ideation type, including dismissed ideas."""
    
    # Get positive hints (patterns, existing features)
    pattern_results = await self.graphiti.search_project_learnings(query)
    
    # Get dismissed ideas for this type
    dismissed_query = f"dismissed ideas {ideation_type}"
    dismissed_results = await self.graphiti.search(
        query=dismissed_query,
        group_ids=[self.project_group_id],
        num_results=10
    )
    
    dismissed_ideas = [
        {
            "title": r.get("title"),
            "reason": r.get("reason"),
            "dismissed_at": r.get("timestamp"),
            "times_dismissed": r.get("dismissed_count", 1)
        }
        for r in dismissed_results
        if r.get("metadata", {}).get("type") == "dismissed_idea"
    ]
    
    return IdeationHints(
        relevant_patterns=[...],
        avoid_duplicating=[...],
        previously_dismissed=dismissed_ideas,  # NEW
        known_constraints=[...]
    )
```

##### Prompt Update for Ideation Agents

Add to all 7 ideation prompts (`ideation_*.md`):

```markdown
### previously_dismissed
Ideas the user has dismissed in past ideation runs. 

**Rules:**
1. **Never suggest exact matches** - User already said no
2. **Avoid similar ideas** - If "Add GraphQL API" was dismissed, don't suggest "Implement GraphQL endpoints"
3. **Learn from reasons:**
   - `too_complex` → Suggest simpler approaches to same problem
   - `not_needed` → This category may not fit the project
   - `breaking_change` → Prefer non-breaking improvements
   - `deferred` → Can mention as "previously considered for later"
4. **Weight by times_dismissed** - Ideas dismissed 2+ times are strong signals
5. **Respect recency** - Ideas dismissed >6 months ago may be worth reconsidering with fresh framing
```

##### CLI Integration

```bash
# Interactive ideation review with dismissal tracking
python auto-claude/ideation_runner.py --review

# Output:
# [1] Add dark mode toggle (UI/UX)
#     > Accept (a) | Dismiss (d) | Skip (s): d
#     > Reason (optional): too_complex
#     > ✓ Recorded dismissal - will avoid similar suggestions

# View dismissal history
python auto-claude/ideation_runner.py --dismissed

# Output:
# Dismissed Ideas (12 total):
# - "Add GraphQL API" (high_value) - dismissed 2x, reason: too_complex
# - "Migrate to TypeScript strict" (code_quality) - dismissed 1x, reason: breaking_change
# ...

# Clear dismissal history (fresh start)
python auto-claude/ideation_runner.py --clear-dismissed
```

##### Token Budget Update

The `previously_dismissed` field should stay within the 500-token budget for ideation hints:
- Max 5 dismissed ideas per type (most recent/most dismissed)
- Truncate descriptions to 50 chars
- Only include reason and times_dismissed

**Key Insight:** Ideation doesn't need full context. It needs:
1. What patterns exist (so ideas extend them)
2. What's already done (so ideas don't duplicate)
3. What constraints exist (so ideas are feasible)

These are **pointer queries**, not **document retrievals**.

---

## 3. Proposed Solution

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       SPEC CREATION PIPELINE                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Phase 1: Discovery (existing)                                          │
│      └── project_index.json                                             │
│                                                                         │
│  Phase 2: Requirements (existing)                                       │
│      └── requirements.json                                              │
│                                                                         │
│  Phase 3: Historical Context (NEW)  ◄───────────────────────────────┐   │
│      ├── File-based memory search (fast, always available)          │   │
│      ├── Graphiti semantic search (if enabled)                      │   │
│      └── historical_context.json (NEW output)                       │   │
│                                                                     │   │
│  Phase 4: Context Discovery (ENHANCED)                              │   │
│      ├── Keywords from task (existing)                              │   │
│      ├── Keywords from historical_context (NEW)  ◄──────────────────┘   │
│      └── context.json (enhanced)                                        │
│                                                                         │
│  Phase 5+: Spec Writing, Planning, Validation (existing)                │
│      └── Now receives historical_context.json as input                  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘

                              FEEDBACK LOOP
┌─────────────────────────────────────────────────────────────────────────┐
│  Implementation completes → QA validates → Outcome recorded             │
│                                                ↓                        │
│                              ┌────────────────────────────────┐         │
│                              │  Project-Level Memory Store    │         │
│                              │  - Patterns that worked        │         │
│                              │  - Gotchas encountered         │         │
│                              │  - QA pass/fail outcomes       │         │
│                              └────────────────────────────────┘         │
│                                                ↓                        │
│                              Available for NEXT spec creation           │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Components

#### 3.1 Historical Context Phase (NEW)

**Location:** `spec_runner.py` - new phase between requirements and context

**Behavior:**
1. Search file-based memory across ALL specs in project
2. If Graphiti enabled, perform semantic search
3. Merge, deduplicate, and truncate to token budget
4. Output `historical_context.json`

**Output Schema:**
```json
{
  "similar_past_tasks": [
    {
      "spec_name": "003-user-auth",
      "task_description": "Add JWT authentication",
      "outcome": "passed",
      "relevance_score": 0.85
    }
  ],
  "patterns_that_worked": [
    "Use middleware for auth checks, not inline validation",
    "Always hash passwords with bcrypt, never store plain"
  ],
  "gotchas_to_avoid": [
    "Database connections must be closed in worker threads",
    "API rate limits: 100 req/min per IP"
  ],
  "recommended_approach": "Based on similar task 003-user-auth, start with middleware setup before routes",
  "token_count": 1847
}
```

#### 3.2 Project-Level Memory Scope (ENHANCEMENT)

**Location:** `graphiti_memory.py` - extend existing class

##### Dual-Level Group ID Strategy

##### Project Identity (REQUIRED)

**Problem:** `project_root.name` is not globally unique (two repos can both be named `app`), which risks cross-project contamination.

**Decision:** Each project gets a stable `project_id` (UUID) stored in `project_index.json` and reused across all runs.

**Implementation Notes:**
- `analyzer.py` should write `project_id` to `project_index.json` if missing.
- `analyzer.py` must preserve an existing `project_id` if it already exists.
- `project_id` is the canonical identifier for Graphiti group IDs and on-disk lite-mode caches.

**Group ID Structure:**
```python
# Project level - for cross-spec queries (historical context, ideation)
project_group_id = f"project:{project_id}"
# Example: "project:2f2d5bd8-55a3-4c33-9f4d-48f7d0b3d0a7"

# Spec level - for spec-specific queries (coder sessions)
spec_group_id = f"spec:{project_id}:{spec_dir.name}"
# Example: "spec:2f2d5bd8-55a3-4c33-9f4d-48f7d0b3d0a7:005-payment-flow"
```

**Dual-Write Pattern:**
Every memory write includes BOTH group IDs to enable both scopes:
```python
await graphiti.add_episode(
    content=learning,
    group_ids=[self.project_group_id, self.spec_group_id],
    metadata={"project_id": project_id, "spec": spec_name, "session": session_num}
)
```

**Query Patterns:**
| Use Case | Group ID | Example Query |
|----------|----------|---------------|
| Historical context (new spec) | `project_group_id` | "What patterns exist for auth?" |
| Coder reading current spec | `spec_group_id` | "What did session 2 learn?" |
| QA checking similar failures | `project_group_id` | "How did similar specs fail?" |
| Ideation avoiding duplicates | `project_group_id` | "What features already exist?" |
| Cross-spec pattern discovery | `project_group_id` | "What middleware patterns work?" |

**Implementation:**
```python
class GraphitiMemory:
    @property
    def project_group_id(self) -> str:
        """Project-level group for cross-spec searches."""
        return f"project:{self.project_id}"

    @property
    def spec_group_id(self) -> str:
        """Spec-level group for current spec searches."""
        return f"spec:{self.project_id}:{self.spec_dir.name}"

    async def search_project_learnings(self, query: str) -> list[dict]:
        """Search across ALL specs in the project. No artificial limit."""
        results = await self._graphiti.search(
            query=query,
            group_ids=[self.project_group_id],
            num_results=50,  # Get many, then filter by relevance
        )
        # Filter by relevance threshold (0.5) - see Section 4.1
        return [r for r in results if r.get("relevance", 0) >= 0.5]

    async def save_learning(self, content: str, learning_type: str, metadata: dict):
        """Save to BOTH project and spec level."""
        await self._graphiti.add_episode(
            content=content,
            group_ids=[self.project_group_id, self.spec_group_id],
            metadata={**metadata, "type": learning_type}
        )
```

#### 3.3 File-Based Cross-Spec Search (NEW)

**Location:** `memory.py` - new functions

**Purpose:** Enable a "lite mode" experience WITHOUT Graphiti (simpler + dumber fallback).

##### Lite Mode Scope (INTENTIONALLY LIMITED)

Lite mode should ONLY read a small set of canonical files:
- `memory/patterns.md`
- `memory/gotchas.md`
- `memory/qa_outcomes/*.json`
- `memory/session_insights/*.json` (optional, last N only)

Lite mode MUST NOT attempt full semantic recall. It is keyword-only and best-effort.

**Implementation:**
```python
def search_project_memory(
    project_dir: Path,
    query: str,
    limit: int = 10,
) -> dict:
    """
    Search memory across all specs in the project.

    Returns aggregated patterns, gotchas, and insights
    that match the query keywords.
    """
    specs_dir = project_dir / "auto-claude" / "specs"
    results = {
        "patterns": [],
        "gotchas": [],
        "similar_tasks": [],
    }

    for spec_dir in specs_dir.iterdir():
        if not spec_dir.is_dir():
            continue
        # Search this spec's memory
        # Aggregate results

    return results
```

#### 3.4 Outcome Recording (NEW)

**Location:** `qa_loop.py`, `memory.py`

**Purpose:** Record QA pass/fail to inform future specs

**Trigger:** After QA validation completes (either pass or final rejection)

##### Extraction Process

QA outcome recording happens in TWO stages:

**Stage 1: Automatic Extraction (MVP)**
```python
# In qa_loop.py - after QA completes
async def record_qa_outcome(spec_dir: Path, qa_result: QAResult):
    outcome = {
        "spec_name": spec_dir.name,
        "outcome": qa_result.status,  # "passed" | "failed" | "partial"
        "qa_attempts": qa_result.attempt_count,
        "timestamp": datetime.now(timezone.utc).isoformat(),

        # Automatic extraction from QA artifacts:
        "issues_found": parse_issues_from_fix_request(spec_dir),  # From QA_FIX_REQUEST.md
        "files_changed": get_changed_files(spec_dir),  # From git diff
        "tests_status": qa_result.test_results,  # From test runs
    }

    # Write to Graphiti (primary)
    if graphiti_enabled():
        await graphiti.save_learning(
            content=format_outcome_for_graphiti(outcome),
            learning_type="qa_outcome",
            metadata=outcome
        )

    # Optional: write to file ("lite mode") for users who opt out of Graphiti
    if lite_mode_enabled() or not graphiti_enabled():
        write_qa_outcome(spec_dir, outcome)
```

**Stage 2: Pattern Extraction (Enhanced - Phase 4)**

After automatic recording, extract learnable patterns:
```python
def extract_learnings_from_outcome(outcome: dict, qa_report: str) -> dict:
    """Extract patterns and gotchas from QA outcome."""

    learnings = {
        "patterns_validated": [],  # What worked
        "gotchas_discovered": [],  # What failed
    }

    if outcome["outcome"] == "passed":
        # Extract patterns from successful implementation
        # Look at what approaches the coder used
        learnings["patterns_validated"] = extract_patterns_from_commits(outcome)

    if outcome["issues_found"]:
        # Convert issues to gotchas for future specs
        for issue in outcome["issues_found"]:
            gotcha = {
                "description": issue["description"],
                "file_pattern": issue.get("file"),
                "prevention": issue.get("fix_description"),
            }
            learnings["gotchas_discovered"].append(gotcha)

    return learnings
```

##### Data Captured

**File: `memory/qa_outcomes/{spec_name}.json`**
```json
{
  "spec_name": "005-payment-flow",
  "outcome": "passed",
  "qa_attempts": 2,
  "timestamp": "2025-12-11T10:30:00Z",

  "issues_found": [
    {
      "description": "Missing auth middleware on /api/payments",
      "file": "routes/payments.py",
      "severity": "critical",
      "fix_description": "Added @require_auth decorator"
    }
  ],

  "patterns_validated": [
    "Webhook handler pattern from spec-007",
    "Idempotency key usage for Stripe calls"
  ],

  "gotchas_discovered": [
    {
      "description": "API routes need @require_auth decorator",
      "file_pattern": "routes/*.py",
      "prevention": "Check all new routes for auth middleware"
    }
  ],

  "files_changed": ["routes/payments.py", "services/stripe.py"],
  "tests_passed": 45,
  "tests_failed": 0
}
```

##### Feedback Loop

```
QA Rejection → Issue extracted → Gotcha created → Future coder warned
      ↓
 "Missing auth on /api/payments"
      ↓
 gotchas.md += "API routes need @require_auth"
      ↓
 Graphiti += Episode("QA: auth missing", confidence=HIGH)
      ↓
 NEXT SPEC: historical_context includes this gotcha
      ↓
 NEXT CODER: Pre-implementation checklist warns about auth
```

#### 3.5 Enhanced Prompt Templates

**Files to Update:**
- `prompts/spec_writer.md` - Add historical_context section
- `prompts/spec_gatherer.md` - Surface relevant learnings to user
- `prompts/planner.md` - Consider past approaches

**Example Addition to spec_writer.md:**
```markdown
## PHASE 0: LOAD ALL CONTEXT (MANDATORY)

```bash
# Read all input files
cat project_index.json
cat requirements.json
cat context.json
cat historical_context.json  # NEW
```

Extract from historical_context.json:
- **Similar past tasks**: What specs solved similar problems?
- **Patterns that worked**: What approaches succeeded?
- **Gotchas to avoid**: What pitfalls were discovered?
- **Recommended approach**: Suggested starting point
```

#### 3.6 Memory Operations Matrix

This matrix defines WHO reads/writes WHAT memory and WHEN:

| Agent/Phase | READS | WRITES | Timing |
|-------------|-------|--------|--------|
| **Spec Runner: Historical Context** | All `memory/` across specs | `historical_context.json` | Sync (before context phase) |
| **Spec Gatherer** | `historical_context.json` | `requirements.json` | Sync |
| **Spec Writer** | `requirements.json`, `context.json`, `historical_context.json` | `spec.md` | Sync |
| **Planner** | `spec.md`, `context.json`, `historical_context.json` | `implementation_plan.json` | Sync |
| **Coder Session** | `memory/*`, `spec.md`, `implementation_plan.json` | `memory/session_*.json`, `codebase_map.json`, `patterns.md`, `gotchas.md` | End of session |
| **QA Reviewer** | `spec.md`, code changes, `memory/*` | `qa_report.md` | Sync |
| **QA Loop (on complete)** | `qa_report.md`, `QA_FIX_REQUEST.md` | `memory/qa_outcomes/*.json`, `gotchas.md` (append) | On QA resolution |
| **Ideation Agent** | `ideation_hints.json` (if exists) | `*_ideas.json` | Sync |
| **Ideation Review (User)** | `*_ideas.json` | `dismissed_ideas.json`, Graphiti (dismissed_idea nodes) | On user dismissal |

**Write Timing Definitions:**
- `Sync`: Written before phase completes, blocks next phase
- `End of session`: Written after coder commits changes
- `On QA resolution`: Written when QA loop resolves (pass or final fail)

**Deduplication Rules:**
Before appending to `patterns.md` or `gotchas.md`:
1. Check if similar entry exists (fuzzy match > 80% similarity)
2. If similar: Update timestamp and increment `reference_count`
3. If new: Append with `reference_count: 1`

#### 3.7 Prompt Integration Specifications

Each prompt must know HOW to use historical context, not just THAT it exists.

##### For `spec_writer.md`:

```markdown
## Historical Context Integration

If `historical_context.json` exists and has content:

### Using Relevance Scores
Each item has a `relevance` score (0.0 - 1.0):
- **>= 0.7**: Directly applicable. Follow this pattern/avoid this gotcha explicitly.
- **0.5 - 0.7**: Related context. Consider adapting, mention in spec if relevant.
- **< 0.5**: Not included (filtered out by retrieval system).

### When Patterns Conflict with Requirements
If a historical pattern conflicts with current requirements:
1. **Requirements win** - they represent current user intent
2. **Document the deviation**: Add to spec: "NOTE: Deviating from pattern [X] because [requirement Y]..."
3. This becomes a learning opportunity - future specs may reference both

### Incorporating Gotchas
For each gotcha in `gotchas_to_avoid`:
1. Add to "Acceptance Criteria" if testable
2. Add to "Testing Requirements" with specific test case
3. Add to "Implementation Notes" with mitigation approach

### Using Similar Past Tasks
Reference similar specs when:
- Explaining architectural decisions
- Justifying technology choices
- Providing implementation examples
```

##### For `coder.md`:

```markdown
## Session Memory Protocol (MANDATORY)

Before implementing ANY chunk, read in this order:

1. **gotchas.md** - CRITICAL: Known landmines in this codebase
   - If ANY gotcha mentions files you're touching → address EXPLICITLY
   - Add code comment: `// Gotcha from spec-XXX: [description]`

2. **patterns.md** - Established patterns that work here
   - Follow these unless requirements explicitly conflict
   - If you deviate, document WHY in commit message

3. **codebase_map.json** - File purposes and relationships
   - Check before creating new files (might already exist)
   - Understand dependencies before modifying

4. **session_insights/*.json** - What previous sessions learned
   - Especially read the most recent session
   - Look for "blockers" and "discoveries"

### Writing Session Insights

At session end, write to `memory/session_{N}.json`:
```json
{
  "session_number": N,
  "chunks_completed": ["chunk-1-2"],
  "patterns_discovered": ["Description of new pattern"],
  "gotchas_found": ["Description of gotcha + file"],
  "codebase_map_updates": {"new_file.py": "Purpose description"},
  "blockers_hit": ["What blocked you and how you resolved"],
  "next_session_should_know": "Key insight for handoff"
}
```
```

##### For `planner.md`:

```markdown
## Historical Context in Planning

If `historical_context.json` exists:

### Chunk Ordering
- If similar past task exists with `outcome: passed`, consider similar chunk order
- If gotchas mention specific files, front-load chunks that touch those files
- High-relevance patterns should inform chunk dependencies

### Estimating Complexity
For each chunk, check:
- Does it touch files mentioned in gotchas? → Higher complexity
- Does it follow a validated pattern? → Lower complexity
- Is it similar to a failed past approach? → Document risk

### patterns_from Field
Use historical context to populate `patterns_from`:
- If pattern exists for this type of chunk → reference it
- If similar spec succeeded → reference its key files
```

##### For Ideation Prompts (all 7):

```markdown
## Optional: Graph Hints Integration

If `ideation_hints.json` exists, read it FIRST:

### avoid_duplicating
Features that already exist. DO NOT suggest these again.
Cross-reference your ideas against this list.

### relevant_patterns
Patterns established in this codebase. Your ideas should:
- EXTEND these patterns (not contradict them)
- BUILD ON existing infrastructure
- FOLLOW established conventions

### known_constraints
Technical limitations. Filter out ideas that violate these.
Example: "No direct database access from frontend" → Don't suggest frontend DB queries

### If hints file doesn't exist
Proceed without it - this is a cold start or Graphiti is disabled.
```

---

## 4. Technical Design

### 4.1 Relevance-Based Context Retrieval

**Core Principle:** The memory system doesn't decide how much context to include. It retrieves what's relevant based on semantic similarity, and **stops when relevance naturally drops off**.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    RELEVANCE-BASED RETRIEVAL                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Query: "Add payment processing with Stripe"                                │
│                                                                             │
│  Results (ranked by relevance):                                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │ 0.92 │ Spec-007: Stripe checkout implementation                 │ ✓     │
│  │ 0.87 │ Pattern: Use idempotency keys for payment APIs           │ ✓     │
│  │ 0.81 │ Gotcha: Webhook signatures must be verified              │ ✓     │
│  │ 0.74 │ Spec-012: Subscription billing with Stripe               │ ✓     │
│  │ 0.68 │ Pattern: All financial operations need audit logs        │ ✓     │
│  │ 0.52 │ Gotcha: Rate limiting on third-party APIs                │ ✓     │
│  │─────────────────────────────────────────────────────────────────│       │
│  │ 0.41 │ Spec-003: User authentication (weak relation)            │ ✗     │
│  │ 0.35 │ Pattern: API error handling (generic)                    │ ✗     │
│  │ 0.22 │ Gotcha: Database connection pooling                      │ ✗     │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                                                             │
│  Cutoff at 0.5 → Natural stopping point based on relevance drop-off        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Why This Works:**
- No arbitrary token limits that might cut off important context
- No padding with irrelevant content when little history exists
- Natural adaptation: rich history → rich context; sparse history → sparse context
- The consuming agent receives WHAT'S RELEVANT, not a fixed quota

#### 4.1.1 Relevance Scoring

**Score Components (0.0 - 1.0):**

| Component | Weight | Source | Rationale |
|-----------|--------|--------|-----------|
| Semantic similarity | 0.5 | Graphiti embedding distance | Core relevance signal |
| Outcome success | 0.25 | 1.0=passed, 0.6=partial, 0.2=failed | Successful patterns more valuable |
| Recency | 0.15 | Decay over 180 days, floor at 0.3 | Recent learnings more applicable |
| Reference count | 0.10 | How often this was useful before | Social proof from past use |

```python
def calculate_relevance(result: MemoryResult, query: str) -> float:
    semantic = result.embedding_similarity  # From Graphiti
    outcome = {"passed": 1.0, "partial": 0.6, "failed": 0.2}.get(result.outcome, 0.5)
    days_old = (now() - result.timestamp).days
    recency = max(0.3, 1.0 - (days_old / 180))
    references = min(1.0, result.reference_count / 10)

    return (0.5 * semantic + 0.25 * outcome + 0.15 * recency + 0.10 * references)
```

#### 4.1.1.1 Confidence Scoring (for conflict resolution)

Relevance answers: "Is this about the current query?"

Confidence answers: "Should we trust/recommend this as a default?"

**Confidence Components (0.0 - 1.0):**

| Component | Weight | Source | Rationale |
|-----------|--------|--------|-----------|
| Outcome success rate | 0.5 | Aggregated from `qa_outcome` episodes | Patterns validated by passing QA are more reliable |
| Recency | 0.2 | Decay over 365 days, floor at 0.2 | Old patterns may no longer match code |
| Reference count | 0.2 | How often referenced/used | Frequently reused patterns are likely stable |
| Severity penalty | 0.1 | Gotchas severity (critical/high/med/low) | High severity gotchas should surface with high confidence |

**Use in output:**
- Include `confidence` on pattern/gotcha items.
- When two items conflict, select winner by confidence (Section 8) but keep both when close.

#### 4.1.2 Relevance Thresholds

| Threshold | Action | Rationale |
|-----------|--------|-----------|
| >= 0.7 | Include in full | Highly relevant, direct applicability |
| 0.5 - 0.7 | Include with summary | Related, useful as reference |
| < 0.5 | Exclude | Below noise floor, not worth context space |

**The 0.5 threshold is the only "magic number"** - and it's based on the principle that below 50% similarity, content is more noise than signal.

#### 4.1.3 Adaptive Behavior

The system naturally adapts without hardcoded limits:

| Scenario | Behavior |
|----------|----------|
| First spec (no history) | Returns empty context - nothing above threshold |
| 5 specs, 2 relevant | Returns those 2 - no padding with irrelevant content |
| 50 specs, 15 relevant | Returns all 15 - doesn't artificially truncate |
| Generic task, few matches | Sparse context - system acknowledges limited history |
| Specific task, many matches | Rich context - full historical depth available |

#### 4.1.4 Graphiti Native Search Capabilities

Graphiti provides built-in hybrid search and reranking. The system MUST leverage these capabilities rather than implementing redundant retrieval logic.

**Built-in Capabilities (used by default `search()` method):**
- Hybrid search: Combines semantic similarity (embeddings) + BM25 keyword matching
- RRF (Reciprocal Rank Fusion): Fuses scores from both retrieval methods

**Advanced Search Options (via `search_()` method with config recipes):**

| Recipe | Method | Use Case | Latency |
|--------|--------|----------|---------|
| `NODE_HYBRID_SEARCH_RRF` | RRF reranking | Node/entity search | Fast |
| `EDGE_HYBRID_SEARCH_RRF` | RRF reranking | Relationship/fact search | Fast |
| `COMBINED_HYBRID_SEARCH_CROSS_ENCODER` | Neural cross-encoder | High-accuracy retrieval | Slower |

**Node Distance Reranking (via `center_node_uuid` parameter):**
- Reranks results by graph proximity to a focal entity
- Use case: "Find patterns related to THIS specific file/component"

**Search Filters (via `SearchFilters` class):**
- `entity_labels`: Filter by node type (e.g., "Pattern", "Gotcha", "SessionInsight")
- `valid_after` / `valid_before`: Date range filtering
- Use case: "Recent patterns only" or "Patterns for authentication components"

##### 4.1.4.1 Search Method Selection

| Context | Search Method | Rationale |
|---------|---------------|-----------|
| **Spec Creation: Historical Context** | `COMBINED_HYBRID_SEARCH_CROSS_ENCODER` | Quality > speed; runs once per spec |
| **Ideation: Graph Hints** | `NODE_HYBRID_SEARCH_RRF` | Speed matters; 7 parallel agents |
| **Implementation: Chunk Context** | `search()` with `center_node_uuid` | Find patterns related to current file |
| **QA: Similar Issues** | `EDGE_HYBRID_SEARCH_RRF` | Find related facts/outcomes |

##### 4.1.4.2 Implementation Requirements

**Required imports for `graphiti_memory.py`:**

```python
from graphiti_core.search.search_config_recipes import (
    COMBINED_HYBRID_SEARCH_CROSS_ENCODER,
    NODE_HYBRID_SEARCH_RRF,
    EDGE_HYBRID_SEARCH_RRF,
)
from graphiti_core.search.search_filters import SearchFilters
```

**New methods to add:**

```python
async def search_high_quality(
    self,
    query: str,
    num_results: int = 15,
) -> list[dict]:
    """
    High-accuracy search using cross-encoder reranking.
    Use for spec creation historical context where quality > speed.
    """
    config = COMBINED_HYBRID_SEARCH_CROSS_ENCODER.model_copy(deep=True)
    config.limit = num_results
    
    results = await self._graphiti.search_(
        query=query,
        config=config,
        group_ids=[self.group_id]
    )
    return self._process_results(results)

async def search_related_to_entity(
    self,
    query: str,
    center_node_uuid: str,
    num_results: int = 10,
) -> list[dict]:
    """
    Search with node distance reranking from a focal entity.
    Use during implementation to find patterns related to current file.
    """
    results = await self._graphiti.search(
        query=query,
        center_node_uuid=center_node_uuid,
        group_ids=[self.group_id],
        num_results=num_results
    )
    return self._process_results(results)

async def search_with_filters(
    self,
    query: str,
    entity_labels: list[str] | None = None,
    days_back: int | None = None,
    num_results: int = 10,
) -> list[dict]:
    """
    Search with type and/or date filters.
    Use for targeted retrieval (e.g., "only patterns", "recent gotchas").
    """
    filters = SearchFilters()
    if entity_labels:
        filters.entity_labels = entity_labels
    if days_back:
        filters.valid_after = datetime.now(timezone.utc) - timedelta(days=days_back)
    
    results = await self._graphiti.search(
        query=query,
        group_ids=[self.group_id],
        num_results=num_results,
        search_filter=filters
    )
    return self._process_results(results)
```

##### 4.1.4.3 Relevance Scoring: Graphiti + Domain Signals

Graphiti handles the core retrieval and reranking. Our relevance formula **augments** Graphiti's scores with domain-specific signals:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         RETRIEVAL PIPELINE                                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Step 1: Graphiti Native Search (handles hybrid + reranking)                │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │  • Semantic similarity (embeddings)                             │       │
│  │  • BM25 keyword matching                                        │       │
│  │  • RRF or Cross-Encoder fusion                                  │       │
│  │  • Returns: results with embedding_similarity scores            │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                    │                                        │
│                                    ▼                                        │
│  Step 2: Domain Signal Augmentation (our layer)                             │
│  ┌─────────────────────────────────────────────────────────────────┐       │
│  │  final_relevance = (                                            │       │
│  │      0.5 * graphiti_score +     # Already fused/reranked        │       │
│  │      0.25 * outcome_success +   # Did this pattern work?        │       │
│  │      0.15 * recency +           # How recent?                   │       │
│  │      0.10 * reference_count     # Social proof                  │       │
│  │  )                                                              │       │
│  └─────────────────────────────────────────────────────────────────┘       │
│                                    │                                        │
│                                    ▼                                        │
│  Step 3: Threshold Filter (0.5 cutoff)                                      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Key Insight:** We do NOT add another reranking layer. Graphiti already handles that. We only add domain signals (outcome, recency, references) that Graphiti doesn't know about.

### 4.2 Graceful Degradation

| Scenario | Behavior |
|----------|----------|
| No historical data exists | Create placeholder file with `status: cold_start` |
| Graphiti disabled (user opt-out) | Use file-based keyword search only ("lite mode") |
| Graphiti connection fails | Fall back to file-based ("lite mode"), log warning |
| Graphiti timeout (5s) | Return partial Graphiti results + file-based fallback |
| All results below threshold | Return empty context with `status: no_relevant_history` |

**Placeholder for Cold Start:**
```json
{
  "status": "cold_start",
  "message": "No historical data available. This is spec #1 for this project.",
  "similar_past_tasks": [],
  "patterns_that_worked": [],
  "gotchas_to_avoid": [],
  "recommended_approach": null,
  "metadata": {
    "specs_searched": 0,
    "results_above_threshold": 0
  }
}
```

This allows prompts to read the file without special-casing "file doesn't exist".

**Graphiti Failure Handling:**
- Timeout: 5 seconds per query
- Retries: 1 (immediate)
- On failure: Log warning, continue with file-based only
- Circuit breaker: After 3 failures in 10 minutes, skip Graphiti for 5 minutes

### 4.3 Data Flow

```
┌──────────────┐
│ Task         │
│ Description  │
└──────┬───────┘
       │
       ▼
┌──────────────────────────────────────────────────────────────┐
│                    PARALLEL RETRIEVAL                         │
│  ┌────────────────────┐     ┌────────────────────┐           │
│  │ Graphiti Semantic  │     │ File-Based Search  │           │
│  │ (embedding search) │     │ (keyword matching) │           │
│  │                    │     │                    │           │
│  │ Rich, PRIMARY      │     │ Lite, optional     │           │
│  └─────────┬──────────┘     └─────────┬──────────┘           │
│            │                          │                       │
│            └────────────┬─────────────┘                       │
│                         ▼                                     │
│            ┌────────────────────────┐                         │
│            │ Merge & Score          │                         │
│            │ • Deduplicate          │                         │
│            │ • Calculate relevance  │                         │
│            │ • Sort by score        │                         │
│            └────────────┬───────────┘                         │
│                         ▼                                     │
│            ┌────────────────────────┐                         │
│            │ Apply Threshold (0.5)  │                         │
│            │ • Include >= 0.5       │                         │
│            │ • Exclude < 0.5        │                         │
│            └────────────┬───────────┘                         │
│                         ▼                                     │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
               ┌──────────────────────┐
               │ historical_context   │
               │ .json                │
               │                      │
               │ Contains only what's │
               │ actually relevant    │
               └──────────────────────┘
```

### 4.4 Output Schema

```json
{
  "status": "ok",
  "query": "Add payment processing with Stripe",
  "project_id": "2f2d5bd8-55a3-4c33-9f4d-48f7d0b3d0a7",
  "similar_past_tasks": [
    {
      "spec_name": "007-stripe-checkout",
      "task_description": "Implement Stripe checkout flow",
      "outcome": "passed",
      "relevance": 0.92,
      "key_learnings": ["Used webhook for confirmation", "Stored customer_id"]
    }
  ],
  "patterns_that_worked": [
    {
      "pattern": "Use idempotency keys for all Stripe API calls",
      "source_spec": "007-stripe-checkout",
      "relevance": 0.87,
      "confidence": 0.83
    }
  ],
  "gotchas_to_avoid": [
    {
      "gotcha": "Webhook endpoint must return 200 within 30 seconds",
      "source_spec": "007-stripe-checkout",
      "relevance": 0.81,
      "confidence": 0.79
    }
  ],
  "recommended_approach": "Start with webhook handler (see 007-stripe-checkout), then checkout session. Use idempotency keys throughout.",
  "conflicts": [
    {
      "type": "pattern_conflict",
      "topic": "auth",
      "items": [
        {
          "content": "Use middleware for auth checks, not inline validation",
          "source_spec": "003-user-auth",
          "relevance": 0.74,
          "confidence": 0.81
        },
        {
          "content": "Prefer inline auth checks for edge endpoints only",
          "source_spec": "019-edge-auth",
          "relevance": 0.72,
          "confidence": 0.78
        }
      ],
      "resolution": {
        "strategy": "highest_confidence",
        "winner_index": 0,
        "delta": 0.03,
        "note": "Winner selected by confidence; runner-up kept for visibility because delta < 0.1"
      }
    }
  ],
  "metadata": {
    "specs_searched": 15,
    "results_above_threshold": 6,
    "relevance_threshold": 0.5,
    "graphiti_enabled": true,
    "lite_mode": false,
    "retrieval_time_ms": 1250
  }
}
```

**Note:** Each item includes its `relevance` score so consuming agents can prioritize appropriately.

---

## 5. Implementation Plan

### Phase 1: Foundation

| Task | File | Effort |
|------|------|--------|
| Add dual-level group_id (project + spec) | `graphiti_memory.py` | Small |
| Add `search_project_learnings()` with relevance scoring | `graphiti_memory.py` | Medium |
| **Add advanced search methods (Section 4.1.4)** | `graphiti_memory.py` | Medium |
| - `search_high_quality()` with cross-encoder | `graphiti_memory.py` | - |
| - `search_related_to_entity()` with node distance | `graphiti_memory.py` | - |
| - `search_with_filters()` for type/date filtering | `graphiti_memory.py` | - |
| **Update docstrings: Graphiti = PRIMARY** | `graphiti_memory.py`, `graphiti_config.py` | Small |
| Add file-based cross-spec search | `memory.py` | Medium |
| Add `calculate_relevance()` utility | `memory.py` | Small |
| Add deduplication logic for patterns/gotchas | `memory.py` | Small |

### Phase 2: Historical Context Phase

| Task | File | Effort |
|------|------|--------|
| Create `phase_historical_context()` | `spec_runner.py` | Medium |
| **Use `search_high_quality()` (cross-encoder) for spec context** | `spec_runner.py` | Small |
| Implement relevance-based retrieval (0.5 threshold) | `spec_runner.py` | Medium |
| Implement merge/dedupe from file + Graphiti sources | `spec_runner.py` | Medium |
| Wire into pipeline after requirements | `spec_runner.py` | Small |
| Create cold-start placeholder handling | `spec_runner.py` | Small |

### Phase 3: Prompt Updates

| Task | File | Effort |
|------|------|--------|
| Update spec_writer.md with integration specs | `prompts/spec_writer.md` | Medium |
| Update spec_gatherer.md | `prompts/spec_gatherer.md` | Small |
| Update planner.md with historical context guidance | `prompts/planner.md` | Medium |
| Update coder.md with session memory protocol | `prompts/coder.md` | Medium |
| Update context.py keyword extraction with historical hints | `context.py` | Small |

### Phase 4: QA Feedback Loop (P0 from Section 11)

| Task | File | Effort |
|------|------|--------|
| Add automatic outcome recording after QA | `qa_loop.py` | Medium |
| Implement pattern/gotcha extraction from QA results | `qa_loop.py` | Medium |
| Store outcomes in file + Graphiti | `memory.py` | Small |
| Add gotchas.md auto-append on QA rejection | `qa_loop.py` | Small |
| Wire QA learnings into historical context retrieval | `spec_runner.py` | Small |

### Phase 5: Ideation Integration

| Task | File | Effort |
|------|------|--------|
| Add `phase_graph_hints_all()` (parallel queries) | `ideation_runner.py` | Medium |
| **Use `NODE_HYBRID_SEARCH_RRF` for fast parallel hints** | `ideation_runner.py` | Small |
| Add `_get_type_hints()` helper | `ideation_runner.py` | Small |
| Update all 7 ideation prompts | `prompts/ideation_*.md` | Medium |
| Add ideation-specific relevance queries | `graphiti_memory.py` | Small |
| **Add `record_dismissed_idea()` for user feedback** | `ideation_runner.py` | Small |
| **Add `--review` CLI mode with dismissal tracking** | `ideation_runner.py` | Medium |
| **Query dismissed ideas in `_get_type_hints()`** | `ideation_runner.py` | Small |
| **Add `previously_dismissed` section to ideation prompts** | `prompts/ideation_*.md` | Small |
| **Add `--dismissed` and `--clear-dismissed` CLI commands** | `ideation_runner.py` | Small |

### Phase 6: Testing & Polish

| Task | File | Effort |
|------|------|--------|
| Unit tests for relevance scoring | `tests/` | Medium |
| Unit tests for cross-spec search | `tests/` | Medium |
| Integration test: cold start → warm start | `tests/` | Medium |
| Integration test: QA feedback loop | `tests/` | Medium |
| Documentation updates | `CLAUDE.md` | Small |

### Phase 7: Extended Learning Loops (Quick Wins)

These are additional feedback loops (see Section 12.6.1) that can be added with minimal effort:

| Task | File | Effort | Loop |
|------|------|--------|------|
| **Add discard reason prompt to `--discard`** | `run.py` | Small | Loop 6 |
| **Record discard outcomes to memory** | `run.py`, `graphiti_memory.py` | Small | Loop 6 |
| **Add complexity calibration recording** | `qa_loop.py` | Small | Loop 7 |
| **Query calibration data in complexity assessor** | `spec_runner.py` | Small | Loop 7 |
| **Track context.json files vs actual files used** | `agent.py` | Small | Loop 9 |
| **Feed context accuracy back to context discovery** | `context.py` | Medium | Loop 9 |
| **Add `--stats` command to show learning metrics** | `run.py` | Medium | All |

### Implementation Order Rationale

```
Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 → Phase 6 → Phase 7
   │         │         │         │         │
   │         │         │         │         └── Can be parallel with Phase 4
   │         │         │         │
   │         │         │         └── QA Feedback is P0 - critical for the flywheel
   │         │         │
   │         │         └── Prompts must be updated AFTER infrastructure exists
   │         │
   │         └── Depends on Phase 1 (search functions)
   │
   └── Foundation - everything depends on this
```

---

## 6. Files to Modify

| File | Changes |
|------|---------|
| `spec_runner.py` | Add `phase_historical_context()`, relevance-based retrieval, wire into pipeline |
| `graphiti_memory.py` | Add dual-level group_id, `search_project_learnings()`, `save_learning()` with dual-write, **add advanced search methods** (`search_high_quality()`, `search_related_to_entity()`, `search_with_filters()`), import search config recipes, **update docstrings to reflect Graphiti-as-primary architecture** |
| `memory.py` | Add `search_project_memory()`, `calculate_relevance()`, outcome storage, deduplication |
| `context.py` | Enhance `_extract_keywords()` with historical hints |
| `qa_loop.py` | Record outcome after QA, extract patterns/gotchas, auto-append to gotchas.md, **record complexity calibration** |
| `run.py` | **Add discard reason prompt, record discard outcomes, add `--stats` command** |
| `agent.py` | **Track files actually used vs context.json for accuracy feedback** |
| `prompts/spec_writer.md` | Add historical_context integration (Section 3.7 spec) |
| `prompts/spec_gatherer.md` | Surface relevant learnings |
| `prompts/planner.md` | Historical context in planning (Section 3.7 spec) |
| `prompts/coder.md` | Session memory protocol (Section 3.7 spec) |
| `ideation_runner.py` | Add `phase_graph_hints_all()` (parallel), integrate before ideation agents, **add `record_dismissed_idea()`, `--review` mode with dismissal tracking, query dismissed ideas in hints** |
| `prompts/ideation_*.md` (7 files) | Add optional graph hints section, **add `previously_dismissed` handling rules** |

### New Files

| File | Purpose |
|------|---------|
| `tests/test_relevance_scoring.py` | Unit tests for relevance calculation |
| `tests/test_historical_context.py` | Unit tests for historical context phase |
| `tests/test_qa_feedback.py` | Unit tests for QA outcome recording |
| `tests/test_ideation_hints.py` | Unit tests for ideation graph hints |
| `tests/test_ideation_dismissals.py` | Unit tests for dismissal recording and retrieval |
| `tests/test_graphiti_advanced_search.py` | Unit tests for advanced search methods (cross-encoder, node distance, filters) |
| `tests/test_discard_learning.py` | Unit tests for discard outcome recording |
| `tests/test_complexity_calibration.py` | Unit tests for complexity prediction vs actual |
| `tests/test_context_accuracy.py` | Unit tests for context accuracy tracking |

### New Directories/Files in Spec Structure

| Path | Purpose |
|------|---------|
| `memory/qa_outcomes/` | QA outcome JSON files per spec |
| `historical_context.json` | Historical context for spec creation |
| `ideation_hints_{type}.json` | Per-type hints for ideation agents |
| `dismissed_ideas.json` | Project-level dismissed ideation tracking (lite mode fallback) |
| `discarded_specs.json` | Project-level spec discard tracking with reasons |
| `complexity_calibration.json` | Predicted vs actual complexity data for calibration |
| `context_accuracy.json` | Context discovery accuracy tracking |

---

## 7. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Graphiti adds latency | Medium | Medium | 5-second timeout, file-based fallback, circuit breaker |
| Wrong patterns propagate | Low | High | Outcome-weighted relevance (failed patterns score lower) |
| Context overwhelms agent | Low | Medium | Relevance-based cutoff (0.5 threshold) ensures only useful content |
| Cold start (no history) | Certain | Low | Graceful degradation with placeholder file |
| FalkorDB unavailable | Medium | Medium | File-based "lite mode" fallback, clear warning, no hard failure |
| Prompt changes break agents | Low | High | Incremental rollout, test on dev specs |
| Duplicate patterns accumulate | Medium | Low | Deduplication with 80% similarity matching |

### 7.5 Performance Impact Estimates

#### 7.5.1 Graphiti Search Method Latencies

| Search Method | Latency | Use Case |
|---------------|---------|----------|
| Basic `search()` (hybrid + RRF default) | 500ms-1s | General queries |
| `NODE_HYBRID_SEARCH_RRF` | 400-800ms | Fast node search (ideation) |
| `EDGE_HYBRID_SEARCH_RRF` | 400-800ms | Fast edge search (QA) |
| `COMBINED_HYBRID_SEARCH_CROSS_ENCODER` | 2-4s | High-accuracy (spec creation) |
| `search()` with `center_node_uuid` | 600ms-1.2s | Node distance reranking (implementation) |

#### 7.5.2 Phase Latencies

| Operation | Latency | When It Runs |
|-----------|---------|--------------|
| File-based cross-spec search | 200-500ms | Historical context phase (lite mode only) |
| Graphiti cross-encoder search | 2-4s | Historical context phase |
| Historical context phase (total) | 2-4s | Once per spec creation |
| Ideation graph hints (all 7 parallel with RRF) | 800ms-1.5s | Once before ideation agents |
| QA outcome recording | 100-200ms | After QA resolution |
| Relevance calculation | <10ms | Per result (in-memory) |

**Total Impact on Spec Creation:**
| Scenario | Added Latency | Notes |
|----------|---------------|-------|
| Cold start (0 specs) | ~500ms | Placeholder creation only |
| Warm start (5-20 specs) | 2-4s | Full retrieval with cross-encoder |
| Rich history (50+ specs) | 3-5s | More results to score |

**Acceptable?** Yes. Spec creation currently takes 2-5 minutes. Adding 3-5s is <5% overhead for significant quality improvement. Using cross-encoder here is worth the extra latency for better accuracy.

**Ideation Impact:**
| Scenario | Added Latency | Notes |
|----------|---------------|-------|
| Graphiti disabled | 0s | No hints phase |
| Graphiti enabled (RRF) | 800ms-1.5s | Parallel queries for all 7 types |

**Acceptable?** Yes. Ideation runs 7 agents which takes 30-60s each. <1.5s is negligible. Using RRF instead of cross-encoder keeps it fast.

---

## 8. Open Questions

### Resolved

| Question | Decision |
|----------|----------|
| Separate phase or merged? | Separate, before context discovery |
| Token budget? | 2000 tokens max |
| Automatic or manual outcome recording? | Automatic with signal extraction |

### Unresolved

| Question | Options | Recommendation |
|----------|---------|----------------|
| How to handle conflicting patterns? | A) Most recent wins B) Highest confidence wins C) Show both | B - Confidence-based (with "close-call show both") |
| Should users be able to edit historical context? | A) No B) CLI flag C) Interactive prompt | C - Ask during requirements if relevant |
| Cross-project learning? | A) Never B) Opt-in C) Same-stack only | A - Start with single project |

### Conflict Resolution Policy (SPECIFIED)

When the retrieval system finds two (or more) patterns/gotchas that conflict:

1. **Pick a winner by confidence** (highest `confidence` wins).
2. **If close** (absolute delta < 0.1), **keep both** in `historical_context.json` under `conflicts[]` so prompts can mention the tradeoff explicitly.
3. **If not close** (delta >= 0.1), keep only the winner, but record a short note in metadata (optional) for debugging.

This avoids silent "pattern drift" while still giving consuming agents a default recommendation.

---

## 9. Success Criteria

### MVP (Phase 1-2)

- [ ] Historical context phase exists and runs
- [ ] File-based cross-spec search works (lite mode fallback)
- [ ] Output file `historical_context.json` created
- [ ] Graceful degradation when no history

### Complete (Phase 1-6)

- [ ] All MVP criteria
- [ ] Graphiti advanced search methods implemented (Section 4.1.4):
  - [ ] `search_high_quality()` with cross-encoder
  - [ ] `search_related_to_entity()` with node distance
  - [ ] `search_with_filters()` for type/date filtering
- [ ] Spec creation uses cross-encoder for best accuracy
- [ ] Ideation uses RRF for parallel speed
- [ ] Code docstrings updated (Graphiti = PRIMARY)
- [ ] All spec prompts updated
- [ ] QA outcomes recorded
- [ ] Token budget enforced
- [ ] Ideation graph hints phase working
- [ ] All ideation prompts updated (7 files)
- [ ] Tests passing (including `test_graphiti_advanced_search.py`)
- [ ] Documentation updated

---

## 10. Appendix

### A. Current Context Flow (Before)

```
Discovery → Requirements → Context → Spec → Plan → Validate
    │            │           │
    ▼            ▼           ▼
project_    requirements  context.json
index.json     .json         │
                             │
                    (keyword search only,
                     no historical data)
```

### B. Proposed Context Flow (After)

```
Discovery → Requirements → Historical → Context → Spec → Plan → Validate
    │            │         Context        │
    ▼            ▼            │           ▼
project_    requirements      │      context.json
index.json     .json          │      (enhanced with
                              │       historical keywords)
                              ▼
                    historical_context.json
                    (patterns, gotchas,
                     similar tasks)
```

### C. Example historical_context.json

```json
{
  "query": "Add payment processing with Stripe",
  "similar_past_tasks": [
    {
      "spec_name": "003-stripe-checkout",
      "task_description": "Implement Stripe checkout flow",
      "outcome": "passed",
      "relevance_score": 0.92,
      "key_learnings": [
        "Used webhook for payment confirmation",
        "Stored customer_id for recurring payments"
      ]
    }
  ],
  "patterns_that_worked": [
    "Validate webhook signatures before processing",
    "Use idempotency keys for all Stripe API calls",
    "Store payment intent ID, not card details"
  ],
  "gotchas_to_avoid": [
    "Stripe API version must match SDK version",
    "Webhook endpoint must return 200 within 30 seconds",
    "Test mode keys start with sk_test_, not sk_live_"
  ],
  "recommended_approach": "Start with webhook handler setup (see 003-stripe-checkout pattern), then build checkout session creation. Use existing PaymentService as base class.",
  "sources": {
    "file_based": 2,
    "graphiti": 3
  },
  "token_count": 1456,
  "generated_at": "2025-12-11T10:30:00Z"
}
```

### D. Ideation Pipeline Flow (Before vs After)

**Before:**
```
Project Analysis → Context Gathering → [Parallel Ideation Agents] → Merge
                                              │
                                              ▼
                                    (each agent analyzes
                                     codebase from scratch,
                                     may duplicate existing
                                     features or miss patterns)
```

**After:**
```
Project Analysis → Context Gathering → Graph Hints → [Parallel Ideation Agents] → Merge
                                           │                │
                                           ▼                ▼
                               ideation_hints.json    (agents receive hints:
                               (500 tokens max)       patterns to extend,
                                                      features to avoid,
                                                      constraints to respect)
```

### E. Example ideation_hints.json

```json
{
  "ideation_type": "security_hardening",
  "relevant_patterns": [
    "Auth middleware in src/middleware/auth.ts validates JWT",
    "Rate limiting implemented via express-rate-limit",
    "Input validation uses Zod schemas in src/validators/"
  ],
  "avoid_duplicating": [
    "JWT authentication (spec 002-auth)",
    "CSRF protection (already in middleware)",
    "Password hashing with bcrypt (UserService)"
  ],
  "known_constraints": [
    "Cannot use session-based auth (stateless API requirement)",
    "Must support API keys for service-to-service calls",
    "Audit logging must not block request processing"
  ],
  "successful_approaches": [
    "Middleware chain pattern for layered security",
    "Centralized error handling masks internal errors"
  ],
  "query_used": "security authentication authorization vulnerabilities",
  "sources": 4,
  "token_count": 423,
  "generated_at": "2025-12-11T15:30:00Z"
}
```

### F. Token Budget Summary

| Context Type | Budget | Use Case |
|--------------|--------|----------|
| `historical_context.json` (spec creation) | 2000 tokens | Full context for spec writer |
| `ideation_hints.json` (ideation) | 500 tokens | Lightweight hints for ideation agents |
| Per-chunk Graphiti context (implementation) | 1000 tokens | Existing behavior, unchanged |

---

### G. Integration Points by Runner

#### spec_runner.py Integration

```python
# Current phases (simplified):
async def run(self):
    await self.phase_complexity()      # → complexity_assessment.json
    await self.phase_requirements()    # → requirements.json
    await self.phase_research()        # → research.json (conditional)
    await self.phase_context()         # → context.json
    await self.phase_spec_writing()    # → spec.md
    await self.phase_critic()          # → critique_report.json (conditional)
    await self.phase_planning()        # → implementation_plan.json
    await self.phase_validation()

# NEW: Insert after requirements, before context
async def run(self):
    await self.phase_complexity()
    await self.phase_requirements()
    await self.phase_historical_context()  # ◄── NEW: historical_context.json
    await self.phase_research()
    await self.phase_context()             # ◄── ENHANCED: uses historical keywords
    await self.phase_spec_writing()        # ◄── ENHANCED: reads historical_context
    ...
```

#### ideation_runner.py Integration

```python
# Current phases:
async def run(self):
    await self.phase_project_index()   # → project_index.json
    await self.phase_context()         # → ideation_context.json
    # Then parallel ideation agents...

# NEW: Insert graph hints before each ideation type
async def run(self):
    await self.phase_project_index()
    await self.phase_context()

    for ideation_type in self.enabled_types:
        await self.phase_graph_hints(ideation_type)  # ◄── NEW: ideation_hints.json
        await self.phase_ideation_type(ideation_type)
```

#### roadmap_runner.py Integration (Optional Future Work)

```python
# Current phases:
async def run(self):
    await self.phase_project_index()   # → project_index.json
    await self.phase_discovery()       # → roadmap_discovery.json
    await self.phase_features()        # → roadmap.json

# FUTURE: Add graph hints for discovery phase
async def run(self):
    await self.phase_project_index()
    await self.phase_graph_hints()     # ◄── FUTURE: existing features, constraints
    await self.phase_discovery()       # ◄── ENHANCED: aware of past work
    await self.phase_features()
```

#### qa_loop.py Integration

```python
# Current: QA validates and creates reports
async def run_qa_validation_loop(...):
    # ... validation logic ...
    if approved:
        # Write qa_report.md
        pass
    else:
        # Write QA_FIX_REQUEST.md
        pass

# NEW: Record outcome to memory after QA completes
async def run_qa_validation_loop(...):
    # ... validation logic ...

    # Record outcome for future specs
    await record_qa_outcome(           # ◄── NEW
        spec_dir=spec_dir,
        outcome="passed" if approved else "failed",
        patterns_validated=[...],
        issues_found=[...],
    )
```

---

### H. Prompt Integration Matrix

| Prompt File | New Input | Changes Needed |
|-------------|-----------|----------------|
| `spec_gatherer.md` | `historical_context.json` | Surface relevant learnings during requirements |
| `spec_writer.md` | `historical_context.json` | Add section for historical context extraction |
| `spec_critic.md` | `historical_context.json` | Validate against past learnings |
| `planner.md` | `historical_context.json` | Consider past approaches when chunking |
| `ideation_low_hanging_fruit.md` | `ideation_hints.json` | Avoid duplicating, extend patterns |
| `ideation_ui_ux.md` | `ideation_hints.json` | Avoid duplicating, respect constraints |
| `ideation_high_value.md` | `ideation_hints.json` | Avoid duplicating, respect constraints |
| `ideation_security.md` | `ideation_hints.json` | Aware of existing security measures |
| `ideation_performance.md` | `ideation_hints.json` | Aware of existing optimizations |
| `ideation_code_quality.md` | `ideation_hints.json` | Aware of existing patterns |
| `ideation_documentation.md` | `ideation_hints.json` | Aware of existing docs |

---

### I. Example: Complete Data Flow for a Second Spec

```
SPEC 001-USER-AUTH (Completed Previously)
├── QA Outcome: PASSED
├── Patterns Learned:
│   • "JWT tokens stored in httpOnly cookies"
│   • "Auth middleware in src/middleware/auth.ts"
├── Gotchas Discovered:
│   • "Token refresh must happen before expiry, not after"
│   • "Rate limiting on /auth/* endpoints"
└── Stored in: memory/ + Graphiti (project:myapp group)

                           ↓
                    [Time passes]
                           ↓

SPEC 002-PAYMENT-FLOW (New Task)
├── User: "Add Stripe payment processing"
│
├── Phase: Historical Context (NEW)
│   ├── Query Graphiti: "payment stripe authentication security"
│   ├── Finds: Auth patterns from 001, no payment history
│   └── Output: historical_context.json
│       {
│         "similar_past_tasks": [],  # No payment tasks yet
│         "patterns_that_worked": [
│           "Auth middleware pattern can be reused for payment auth"
│         ],
│         "gotchas_to_avoid": [
│           "Rate limiting exists - payment endpoints need exemption?"
│         ],
│         "recommended_approach": "Follow auth middleware pattern for payment guards"
│       }
│
├── Phase: Context Discovery (ENHANCED)
│   ├── Keywords from task: "stripe", "payment", "checkout"
│   ├── Keywords from history: "middleware", "auth", "tokens"  # ◄── NEW
│   └── Finds: More relevant files due to expanded keywords
│
├── Phase: Spec Writing (ENHANCED)
│   ├── Reads: requirements.json, context.json, historical_context.json
│   └── spec.md includes:
│       • Reference to auth middleware pattern
│       • Warning about rate limiting
│       • Note: No prior payment implementations to reference
│
└── Implementation & QA
    └── On completion: Patterns/gotchas added to project memory
        └── Available for SPEC 003 and beyond
```

---

## 11. Future Enhancements: Memory-Powered Capabilities

Beyond the core Smart Context System, here are additional memory-powered enhancements that would significantly improve Auto Claude's success rate.

### 11.1 Predictive Bug Prevention (Enhancement to prediction.py)

**Current State:** `prediction.py` generates static checklists based on chunk type.

**Enhancement:** Use historical data to predict SPECIFIC bugs for THIS codebase.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    PREDICTIVE BUG PREVENTION                                │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Chunk: "Add payment endpoint"                                              │
│                                                                             │
│  STATIC PREDICTIONS (current):                                              │
│  • "Check for SQL injection"                                                │
│  • "Validate input parameters"                                              │
│                                                                             │
│  LEARNED PREDICTIONS (proposed):                                            │
│  • "This codebase: Auth middleware missing in 3/5 past API chunks"          │
│  • "This codebase: CORS errors occurred in chunk-002, chunk-007"            │
│  • "File routes/api.py: Last 2 changes caused import errors"                │
│  • "Pattern: Payment endpoints need rate limiting (from spec-003)"          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Data Sources:**
- `memory/gotchas.md` - Known pitfalls in this codebase
- `memory/attempt_history.json` - What failed before and why
- Graphiti - Similar chunks that failed across specs

**Implementation:**
```python
# prediction.py enhancement
async def generate_learned_predictions(
    spec_dir: Path,
    chunk: dict,
    graphiti_memory: GraphitiMemory | None,
) -> list[str]:
    """Generate predictions based on historical failures."""

    predictions = []

    # 1. Local memory: gotchas for this file
    gotchas = load_gotchas(spec_dir)
    for file in chunk.get("files_to_modify", []):
        file_gotchas = [g for g in gotchas if file in g]
        predictions.extend(file_gotchas)

    # 2. Attempt history: what failed before
    history = load_attempt_history(spec_dir)
    for chunk_id, attempts in history.get("chunks", {}).items():
        failed = [a for a in attempts if not a["success"]]
        if failed and is_similar_chunk(chunk, chunk_id):
            predictions.append(f"Similar chunk {chunk_id} failed: {failed[-1]['error']}")

    # 3. Graphiti: cross-spec learnings
    if graphiti_memory:
        query = f"failures bugs errors {chunk.get('description', '')}"
        results = await graphiti_memory.search_project_learnings(query, limit=5)
        for r in results:
            predictions.append(f"From past spec: {r['content']}")

    return predictions
```

**Impact:** Prevents repeating the same mistakes across sessions and specs.

---

### 11.2 Adaptive Chunk Complexity Scoring

**Current State:** All chunks treated equally. No signal about which are risky.

**Enhancement:** Score chunks by predicted difficulty based on historical data.

```json
{
  "id": "chunk-3-2",
  "description": "Add WebSocket connection handler",
  "complexity_score": 0.85,
  "complexity_factors": [
    {"factor": "file_churn", "score": 0.9, "reason": "websocket.py modified 8 times in past specs"},
    {"factor": "similar_failures", "score": 0.8, "reason": "2 similar chunks failed before"},
    {"factor": "dependencies", "score": 0.7, "reason": "Depends on 3 other files"}
  ],
  "recommended_approach": "Start with connection test before implementing handlers",
  "estimated_sessions": 2
}
```

**Benefits:**
- Planner can front-load risky chunks
- Coordinator can allocate more time to complex chunks
- User sees realistic progress estimates

---

### 11.3 Cross-Session Codebase Map Evolution

**Current State:** `codebase_map.json` grows but never prunes. Becomes stale.

**Enhancement:** Intelligent map maintenance with confidence decay.

```json
{
  "src/auth/middleware.py": {
    "description": "JWT validation middleware",
    "confidence": 0.95,
    "last_verified": "2025-12-10T10:00:00Z",
    "sessions_referenced": 5,
    "changes_since_mapped": 0
  },
  "src/utils/old_helper.py": {
    "description": "Legacy string utilities",
    "confidence": 0.3,
    "last_verified": "2025-11-01T10:00:00Z",
    "sessions_referenced": 0,
    "changes_since_mapped": 12,
    "flag": "STALE - consider removing"
  }
}
```

**Maintenance Logic:**
```python
def update_codebase_map(map_data: dict, project_dir: Path) -> dict:
    """Update confidence scores based on file changes."""

    for file_path, info in map_data.items():
        # Check if file still exists
        if not (project_dir / file_path).exists():
            info["flag"] = "DELETED"
            info["confidence"] = 0
            continue

        # Check git history for changes since last verified
        changes = count_git_changes_since(file_path, info["last_verified"])
        info["changes_since_mapped"] = changes

        # Decay confidence based on changes and time
        if changes > 5:
            info["confidence"] *= 0.5
        elif changes > 0:
            info["confidence"] *= 0.9

        # Flag stale entries
        if info["confidence"] < 0.4:
            info["flag"] = "STALE"

    return map_data
```

---

### 11.4 QA Learning Feedback Loop

> **Note:** This enhancement has been **moved to Phase 4 of core implementation** (Section 5). It is now a P0 deliverable, not a future enhancement. The details below remain for reference.

**Current State:** QA outcomes not recorded. Same issues repeat.

**Enhancement:** QA feeds learnings back into the system.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         QA FEEDBACK LOOP                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  QA REJECTION                                                               │
│  ├── Issue: "Missing auth middleware on /api/payments"                      │
│  ├── File: routes/payments.py                                               │
│  └── Pattern: "All /api/* routes need @require_auth"                        │
│                                                                             │
│                              │                                              │
│                              ▼                                              │
│                                                                             │
│  AUTOMATIC UPDATES                                                          │
│  ├── gotchas.md += "API routes need @require_auth decorator"                │
│  ├── patterns.md += "Pattern: @require_auth on all /api/* endpoints"        │
│  └── Graphiti += Episode("QA caught missing auth", confidence=HIGH)         │
│                                                                             │
│                              │                                              │
│                              ▼                                              │
│                                                                             │
│  NEXT SPEC CREATION                                                         │
│  └── historical_context.json includes:                                      │
│      "gotchas_to_avoid": ["API routes need @require_auth decorator"]        │
│                                                                             │
│  NEXT CODER SESSION                                                         │
│  └── Pre-implementation checklist includes:                                 │
│      "⚠️ QA previously caught: Missing auth on API routes"                  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Implementation in qa_loop.py:**
```python
async def record_qa_learnings(
    spec_dir: Path,
    qa_result: QAResult,
    graphiti_memory: GraphitiMemory | None,
):
    """Extract and store learnings from QA results."""

    learnings = []

    for issue in qa_result.issues:
        if issue.severity in ["critical", "major"]:
            learning = {
                "type": "qa_rejection",
                "issue": issue.description,
                "file": issue.file_path,
                "pattern": issue.suggested_pattern,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            learnings.append(learning)

            # Update gotchas.md
            append_to_gotchas(spec_dir, issue.description)

            # Update patterns.md if pattern suggested
            if issue.suggested_pattern:
                append_to_patterns(spec_dir, issue.suggested_pattern)

    # Store in Graphiti for cross-spec learning
    if graphiti_memory and learnings:
        await graphiti_memory.save_qa_learnings(learnings)
```

---

### 11.5 Semantic File Similarity for Pattern Discovery

**Current State:** `patterns_from` in chunks is manually specified by Planner.

**Enhancement:** Automatic discovery of similar files via embeddings.

```python
async def find_similar_files(
    target_file: str,
    project_dir: Path,
    graphiti_memory: GraphitiMemory,
    top_k: int = 3,
) -> list[str]:
    """Find files semantically similar to target for pattern reference."""

    # Get file content (or summary if too large)
    content = read_file_summary(project_dir / target_file)

    # Search Graphiti for similar file descriptions
    results = await graphiti_memory.search(
        query=f"file similar to: {content[:500]}",
        group_ids=[graphiti_memory.project_group_id],
        num_results=top_k,
    )

    return [r["file_path"] for r in results if r["file_path"] != target_file]
```

**Use Cases:**
- Planner auto-discovers `patterns_from` files
- Coder finds similar implementations when stuck
- QA finds similar tests to reference

---

### 11.6 Session Handoff Optimization

**Current State:** Each session reads ALL memory files from scratch.

**Enhancement:** Summarized handoff document optimized for next session.

```markdown
# Session Handoff: Session 5 → Session 6

## Progress Summary
- Completed: 7/12 chunks (58%)
- Current phase: phase-2-worker (2/3 chunks done)
- Next chunk: chunk-2-3 (Create Celery beat schedule)

## What You Need to Know
1. **Redis connection**: Use `get_redis()` from `src/utils/redis.py` (NOT direct connection)
2. **Celery tasks**: Follow pattern in `worker/tasks/existing_task.py`
3. **Gotcha**: Celery beat requires `CELERY_BEAT_SCHEDULE` in settings (I missed this initially)

## Files I Modified This Session
- `worker/tasks/aggregation.py` - Added aggregation task (verified working)
- `worker/celeryconfig.py` - Added task routing

## Recommended First Action
Read `worker/tasks/existing_task.py` for the beat schedule pattern before starting chunk-2-3.

## Open Questions
- Should beat schedule be in separate file or celeryconfig.py? (I put in celeryconfig)
```

**Generated automatically at session end:**
```python
def generate_handoff(
    spec_dir: Path,
    session_insights: dict,
    next_chunk: dict | None,
) -> str:
    """Generate optimized handoff document for next session."""

    handoff = f"""# Session Handoff: Session {session_insights['session_number']} → Session {session_insights['session_number'] + 1}

## Progress Summary
{generate_progress_summary(spec_dir)}

## What You Need to Know
{format_key_learnings(session_insights)}

## Files I Modified This Session
{format_modified_files(session_insights)}

## Recommended First Action
{generate_recommended_action(next_chunk, session_insights)}
"""
    return handoff
```

---

### 11.7 Verification Result Caching

**Current State:** Verification runs every time, even for unchanged code.

**Enhancement:** Cache verification results, invalidate on file change.

```json
{
  "chunk-1-2": {
    "last_verified": "2025-12-11T10:00:00Z",
    "verification_passed": true,
    "files_hash": "abc123def456",
    "verification_output": "All tests passed (5/5)",
    "dependencies_hash": "xyz789"
  }
}
```

**Logic:**
```python
def should_reverify(chunk_id: str, cache: dict, project_dir: Path) -> bool:
    """Check if chunk needs re-verification."""

    if chunk_id not in cache:
        return True

    cached = cache[chunk_id]

    # Check if files changed
    current_hash = hash_files(cached["files"], project_dir)
    if current_hash != cached["files_hash"]:
        return True

    # Check if dependencies changed
    deps_hash = hash_dependencies(cached["dependencies"], project_dir)
    if deps_hash != cached["dependencies_hash"]:
        return True

    return False
```

**Benefits:**
- Faster session startup (skip verified chunks)
- Reduced API/browser test load
- Clear signal when verification actually needed

---

### 11.8 Multi-Project Learning (Future)

**Current State:** Each project is isolated. No cross-project learning.

**Future Enhancement:** Opt-in cross-project pattern sharing.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    MULTI-PROJECT LEARNING                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  Project A (FastAPI + React)                                                │
│  └── Learned: "FastAPI CORS needs explicit origins list"                    │
│                                                                             │
│  Project B (FastAPI + Vue) ◄── NEW PROJECT                                  │
│  └── Query: "What do I need to know about FastAPI?"                         │
│  └── Result: "From similar project: CORS needs explicit origins list"       │
│                                                                             │
│  Filtering:                                                                 │
│  • Same tech stack: Include                                                 │
│  • Different stack: Exclude                                                 │
│  • Generic patterns: Include with lower confidence                          │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Considerations:**
- Opt-in only (privacy)
- Filter by tech stack similarity
- Confidence decay for cross-project learnings
- User can review/approve cross-project suggestions

---

### 11.9 Implementation Priority Matrix

| Enhancement | Impact | Effort | Dependencies | Priority | Status |
|-------------|--------|--------|--------------|----------|--------|
| **QA Learning Feedback Loop** | High | Medium | Smart Context | P0 | **Moved to Phase 4** |
| **Predictive Bug Prevention** | High | Medium | QA Feedback + 20 specs | P0 | Future (needs data) |
| **Session Handoff Optimization** | Medium | Small | None | P1 | Future |
| **Verification Result Caching** | Medium | Small | None | P1 | Future |
| **Adaptive Chunk Complexity** | Medium | Medium | Smart Context | P2 | Future |
| **Codebase Map Evolution** | Medium | Small | None | P2 | Future |
| **Semantic File Similarity** | Medium | Medium | Graphiti required | P2 | Future |
| **Multi-Project Learning** | High | Large | Full Smart Context | P3 | Future |

> **Note:** QA Learning Feedback Loop has been promoted to core implementation (Phase 4). It is essential for the Knowledge Flywheel to function.

---

### 11.10 Success Metrics for Enhancements

| Metric | Current | After Smart Context | After All Enhancements |
|--------|---------|---------------------|------------------------|
| QA first-pass rate | ~60% | ~75% | ~90% |
| Repeated gotchas | Common | Rare | Near-zero |
| Session context load time | 5-10s | 5-10s | 2-5s (with caching) |
| Chunks requiring recovery | ~15% | ~10% | ~5% |
| Cross-spec pattern reuse | 0% | 50%+ | 80%+ |
| Prediction accuracy | Generic | Codebase-specific | File-specific |
| Ideation acceptance rate | ~40% | ~60% | ~80% (learns from dismissals) |
| Complexity estimation accuracy | ~50% | ~70% | ~85% (calibrated over time) |
| Spec discard rate | Unknown | Tracked | ~5% (preventable discards avoided) |
| Context file accuracy | ~50% | ~65% | ~85% (learns what's relevant) |

---

## 12. Long-Term Vision: The Self-Improving System

This section envisions how Auto Claude evolves from a blank slate to a deeply knowledgeable coding partner that understands your specific project better than any general-purpose AI could.

### The Flywheel Effect

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    THE KNOWLEDGE FLYWHEEL                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│                         ┌─────────────┐                                     │
│                         │   BUILD     │                                     │
│                         │   SPEC N    │                                     │
│                         └──────┬──────┘                                     │
│                                │                                            │
│            ┌───────────────────┼───────────────────┐                        │
│            │                   │                   │                        │
│            ▼                   ▼                   ▼                        │
│     ┌────────────┐     ┌────────────┐     ┌────────────┐                   │
│     │  Patterns  │     │  Gotchas   │     │  Outcomes  │                   │
│     │  Learned   │     │  Found     │     │  Recorded  │                   │
│     └─────┬──────┘     └─────┬──────┘     └─────┬──────┘                   │
│           │                  │                  │                          │
│           └──────────────────┴──────────────────┘                          │
│                              │                                              │
│                              ▼                                              │
│                    ┌─────────────────┐                                      │
│                    │  KNOWLEDGE BASE │                                      │
│                    │  (Memory Layer) │                                      │
│                    └────────┬────────┘                                      │
│                             │                                               │
│                             ▼                                               │
│                    ┌─────────────────┐                                      │
│                    │   BUILD         │                                      │
│                    │   SPEC N+1      │◄── Faster, fewer errors,             │
│                    │   (Smarter)     │    better patterns                   │
│                    └─────────────────┘                                      │
│                                                                             │
│   Each spec makes the next one better. The system compounds knowledge.      │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 12.1 Spec 1: Cold Start (The Blank Slate)

**Knowledge State:** Empty. No patterns, no gotchas, no history.

```
Memory Contents:
├── codebase_map.json      → {}
├── patterns.md            → (doesn't exist)
├── gotchas.md             → (doesn't exist)
├── session_insights/      → (empty)
└── Graphiti               → (empty graph)
```

**Behavior:**
- Spec creation uses only static project analysis
- Context discovery relies purely on keyword matching
- Coder uses generic predictions ("check for SQL injection")
- QA has no baseline for "normal" in this codebase
- High chance of hitting unknown gotchas

**Metrics (Baseline):**
| Metric | Value |
|--------|-------|
| QA first-pass rate | ~50-60% |
| Sessions per chunk | 1.5 avg |
| Gotchas hit | Many (unknown codebase) |
| Pattern adherence | Low (discovering patterns) |

**What Gets Learned:**
```
Session 1 discovers:
  - "Database uses SQLAlchemy with async sessions"
  - "All API routes are in routes/ directory"
  - "Tests use pytest with fixtures in conftest.py"

Session 2 discovers:
  - "Auth uses JWT tokens stored in httpOnly cookies"
  - "Gotcha: Must close async sessions explicitly"

QA discovers:
  - "Missing CORS configuration on new endpoints"
  - "Pattern: All routes need @require_auth decorator"
```

---

### 12.2 Spec 20: Pattern Recognition (The Learning Phase)

**Knowledge State:** Rich local patterns, emerging cross-spec insights.

```
Memory Contents:
├── codebase_map.json      → 150+ files mapped with descriptions
├── patterns.md            → 40+ established patterns
├── gotchas.md             → 25+ known pitfalls
├── session_insights/      → 60+ session records
├── qa_outcomes/           → 20 spec outcomes (15 passed, 5 needed fixes)
└── Graphiti               → 500+ nodes, 200+ relationships
```

**Behavior:**
- Historical context surfaces relevant past work automatically
- "You're adding a payment endpoint. Spec-007 added Stripe integration. Here's what worked..."
- Predictions are codebase-specific: "This file (routes/api.py) has caused CORS issues 3 times"
- QA knows what "normal" looks like and catches regressions faster
- Ideation avoids suggesting features that already exist
- **Ideation learns from dismissals**: "User has dismissed 3 'add GraphQL' suggestions → avoid GraphQL-related ideas"

**Example Historical Context for Spec 20:**
```json
{
  "task": "Add email notification system",
  "similar_past_tasks": [
    {
      "spec": "012-slack-notifications",
      "relevance": 0.85,
      "learnings": [
        "Used background worker for async sending",
        "Created NotificationService base class",
        "Added retry logic with exponential backoff"
      ]
    },
    {
      "spec": "008-password-reset",
      "relevance": 0.72,
      "learnings": [
        "Email templates in templates/email/",
        "Used Jinja2 for templating",
        "Gotcha: SMTP timeout needs explicit handling"
      ]
    }
  ],
  "patterns_that_worked": [
    "All async operations go through worker service",
    "Notification services inherit from BaseNotificationService",
    "Templates use the shared email layout base.html"
  ],
  "gotchas_to_avoid": [
    "SMTP connections must be pooled (discovered spec-008)",
    "Email sending must not block API response (discovered spec-012)",
    "Rate limiting needed for notification endpoints (QA catch spec-015)"
  ],
  "recommended_approach": "Follow spec-012 pattern: Create EmailNotificationService extending BaseNotificationService, use worker for async delivery"
}
```

**Metrics (Improved):**
| Metric | Spec 1 | Spec 20 | Improvement |
|--------|--------|---------|-------------|
| QA first-pass rate | 50-60% | 75-80% | +20-25% |
| Sessions per chunk | 1.5 | 1.1 | -27% |
| Gotchas hit | Many | Few (predicted) | -70% |
| Pattern adherence | Low | High (guided) | +60% |
| Ideation acceptance rate | ~40% | ~70% | +30% (learns from dismissals) |

**Emergent Capabilities:**
- System starts predicting which chunks will be difficult
- Planner references past specs when creating implementation plans
- Coder asks "how did we do this before?" and gets real answers
- QA report includes "regression from spec-X" when patterns violated

---

### 12.3 Spec 60: Deep Understanding (The Expertise Phase)

**Knowledge State:** Comprehensive project knowledge graph, statistical patterns.

```
Memory Contents:
├── codebase_map.json      → 400+ files, confidence-scored
├── patterns.md            → 100+ patterns (categorized by domain)
├── gotchas.md             → 60+ pitfalls (with severity scores)
├── session_insights/      → 200+ sessions analyzed
├── qa_outcomes/           → 60 specs (52 first-pass, 8 needed fixes)
├── chunk_statistics/      → Success rates by chunk type
├── file_risk_scores/      → Per-file failure probability
└── Graphiti               → 2000+ nodes, rich relationship graph
```

**Behavior:**
- System has statistical model of what succeeds and fails
- Knows which files are "hot" (frequently cause issues)
- Predicts chunk complexity with high accuracy
- Suggests optimal implementation order based on historical success
- Catches architectural drift: "This pattern contradicts how we do auth elsewhere"

**Example Chunk Complexity Prediction:**
```json
{
  "chunk": "chunk-3-2: Add WebSocket real-time updates",
  "predicted_complexity": 0.85,
  "confidence": 0.92,
  "factors": [
    {
      "factor": "Technology complexity",
      "score": 0.9,
      "evidence": "WebSocket chunks failed 40% more often historically"
    },
    {
      "factor": "File risk",
      "score": 0.8,
      "evidence": "services/realtime.py has 0.7 failure rate"
    },
    {
      "factor": "Integration points",
      "score": 0.85,
      "evidence": "Touches 4 services (above average of 2.1)"
    }
  ],
  "recommended_mitigations": [
    "Review spec-034 WebSocket implementation first",
    "Start with connection test before message handlers",
    "Allocate 2 sessions (vs. 1 average)"
  ],
  "similar_successful_chunks": [
    "spec-034/chunk-2-1 (WebSocket notifications) - 1 session",
    "spec-041/chunk-4-2 (Real-time dashboard) - 2 sessions"
  ]
}
```

**Metrics (Mature):**
| Metric | Spec 1 | Spec 20 | Spec 60 | Improvement |
|--------|--------|---------|---------|-------------|
| QA first-pass rate | 50% | 78% | 88% | +38% |
| Sessions per chunk | 1.5 | 1.1 | 1.05 | -30% |
| Gotchas hit | Many | Few | Rare | -90% |
| Pattern adherence | Low | High | Near-perfect | +80% |
| Accurate complexity prediction | N/A | 65% | 85% | +20% |

**Emergent Capabilities:**
- System warns about architectural decisions: "Adding this here will create circular dependency"
- Suggests refactoring opportunities: "These 3 services share duplicated code (found across 5 specs)"
- Identifies technical debt accumulation: "Error handling in payments/ degraded over last 10 specs"
- Predicts which changes will need extensive QA

---

### 12.4 Spec 200: Institutional Knowledge (The Mastery Phase)

**Knowledge State:** Complete project history, causal understanding, predictive models.

```
Memory Contents:
├── codebase_map.json      → 800+ files, versioned history
├── patterns.md            → 200+ patterns (evolution tracked)
├── gotchas.md             → 100+ pitfalls (some deprecated as fixed)
├── session_insights/      → 700+ sessions, ML-ready dataset
├── qa_outcomes/           → 200 specs (185 first-pass)
├── architectural_model/   → Learned service dependencies
├── developer_preferences/ → Coding style learned over time
├── seasonal_patterns/     → Time-based failure patterns
└── Graphiti               → 10,000+ nodes, causal graph
```

**Behavior:**
- System has "seen everything" in this codebase
- Can predict cascading effects of changes
- Knows the history of every file and why it evolved
- Understands implicit conventions that were never documented
- Can explain WHY things are done a certain way

**Example: Historical Reasoning**
```
User: "Why does PaymentService have this weird retry logic?"

System: "Based on project history:

1. Original implementation (Spec-012): Simple retry with fixed delay
2. Spec-034: Added exponential backoff after Stripe rate limiting incident
3. Spec-067: Added circuit breaker after production outage (Spec-067 QA report)
4. Spec-089: Current form with jitter added (discovered thundering herd in Spec-088)

The retry logic evolved through 4 production incidents. Each layer addresses
a specific failure mode discovered in production.

Related gotchas:
- 'Stripe rate limits are per-second, not per-minute' (Spec-034)
- 'Payment retries must be idempotent' (Spec-067)
- 'Add jitter to prevent thundering herd' (Spec-089)

If you're modifying this, be aware that removing any layer will likely
cause the original issue to resurface."
```

**Example: Predictive Architecture**
```json
{
  "proposed_change": "Add caching layer to UserService",
  "impact_analysis": {
    "direct_impact": ["UserService", "AuthService"],
    "cascading_impact": ["PaymentService", "NotificationService"],
    "predicted_issues": [
      {
        "issue": "Cache invalidation for auth tokens",
        "confidence": 0.89,
        "evidence": "Similar change in Spec-145 caused auth bugs",
        "mitigation": "Use event-based invalidation (pattern from Spec-156)"
      },
      {
        "issue": "Memory pressure in worker service",
        "confidence": 0.72,
        "evidence": "Worker runs on limited memory (discovered Spec-078)",
        "mitigation": "Use Redis instead of in-memory cache"
      }
    ],
    "recommended_approach": {
      "pattern": "Distributed cache with event invalidation",
      "reference_specs": ["Spec-156", "Spec-167"],
      "estimated_chunks": 4,
      "estimated_sessions": 5
    }
  }
}
```

**Metrics (Mastery):**
| Metric | Spec 1 | Spec 20 | Spec 60 | Spec 200 |
|--------|--------|---------|---------|----------|
| QA first-pass rate | 50% | 78% | 88% | 95% |
| Sessions per chunk | 1.5 | 1.1 | 1.05 | 1.02 |
| Accurate estimates | N/A | 50% | 75% | 92% |
| Architectural violations | Common | Occasional | Rare | Near-zero |
| Novel gotchas | Frequent | Occasional | Rare | Very rare |

**Emergent Capabilities:**
- **Causal understanding**: "If you change X, Y and Z will break because..."
- **Historical context**: "This was tried in Spec-45, failed because..."
- **Proactive suggestions**: "Based on your recent specs, you might want to refactor..."
- **Onboarding acceleration**: New team members can query the system for project history
- **Technical debt tracking**: "These areas have accumulated debt over the last 50 specs"

---

### 12.5 The Compound Effect Visualized

```
                    KNOWLEDGE ACCUMULATION OVER TIME

Knowledge   │                                              ┌─────────
Depth       │                                         ┌────┘
            │                                    ┌────┘
            │                               ┌────┘
            │                          ┌────┘
            │                     ┌────┘
            │                ┌────┘
            │           ┌────┘
            │      ┌────┘
            │ ┌────┘
            │─┘
            └────────────────────────────────────────────────────────►
              1    20        60              120            200   Specs

            │←─────────────→│←──────────────→│←────────────────────→│
              Learning        Pattern           Mastery
              Phase           Recognition       Phase
              (Discovery)     (Optimization)    (Prediction)


                    SUCCESS RATE IMPROVEMENT

Success     │                                              ┌─────────
Rate        │                                         ┌────┘ 95%
            │                                    ┌────┘
            │                               ┌────┘ 88%
            │                          ┌────┘
            │                     ┌────┘ 78%
            │                ┌────┘
            │           ┌────┘
            │      ┌────┘ 60%
            │ ┌────┘
            │─┘ 50%
            └────────────────────────────────────────────────────────►
              1    20        60              120            200   Specs


                    NOVEL PROBLEMS ENCOUNTERED

Novel       │
Problems    │─┐ Many
            │  └─┐
            │    └─┐
            │      └──┐
            │         └───┐
            │             └────┐ Few
            │                  └─────┐
            │                        └───────┐
            │                                └─────────────────── Rare
            └────────────────────────────────────────────────────────►
              1    20        60              120            200   Specs
```

---

### 12.6 What Makes This Self-Improving

The system improves itself through multiple feedback loops:

#### Loop 1: Direct Learning (Every Session)
```
Coder Session → Discovers pattern/gotcha → Writes to memory → Next session uses it
```

#### Loop 2: QA Feedback (Every Spec)
```
QA Rejection → Extracts issue → Creates gotcha → Coder gets warning → Issue prevented
```

#### Loop 2.5: Ideation Preference Learning (Every Review)
```
User dismisses idea → Records dismissal + reason → Next ideation run retrieves dismissed →
  → Agent avoids similar suggestions → More relevant ideas generated
```
This loop creates **personalized ideation** over time. The system learns:
- What types of features fit this project
- What complexity level is acceptable
- What constraints matter to this user
- What categories get consistently rejected

#### Loop 3: Cross-Spec Learning (Accumulative)
```
Multiple similar specs → Pattern emerges → Graphiti identifies → Historical context surfaces
```

#### Loop 4: Statistical Learning (Long-term)
```
200 specs of data → Chunk complexity model → Accurate predictions → Better planning
```

#### Loop 5: Architectural Learning (Emergent)
```
Many file changes tracked → Dependency graph learned → Impact prediction → Safer changes
```

---

### 12.6.1 Additional Learning Opportunities (Not Yet Implemented)

The following user interaction points and system outputs could enable additional self-improvement loops. These represent **missing feedback signals** that are currently lost:

#### Loop 6: Spec Discard Learning (Missing)
```
User runs --discard → Records: spec_id, stage_reached, reason (if provided) →
  → Next spec creation: "Similar specs were discarded before, consider: [reasons]"
```
**Signal:** When a user discards an implementation, something went fundamentally wrong. This is a strong negative signal that should inform future specs.

**Data to capture:**
- Which spec was discarded
- How far did implementation get (chunks completed)
- User-provided reason (optional prompt: "Why are you discarding?")
- Files that were modified before discard

**Use case:** "2 of 3 specs involving WebSocket changes were discarded. Consider simpler approach or breaking into smaller specs."

#### Loop 7: Complexity Estimation Calibration (Missing)
```
Complexity Assessment predicts: "STANDARD" → Actual outcome: 8 sessions, 3 QA cycles →
  → Recalibrate: This type of task is actually COMPLEX in this codebase
```
**Signal:** The complexity assessor currently makes predictions but never learns if they were accurate.

**Data to capture:**
- Predicted complexity (simple/standard/complex)
- Actual sessions needed
- Actual QA cycles
- Task type/category

**Use case:** "Tasks involving 'authentication' in this codebase are consistently underestimated. Auto-upgrading complexity."

#### Loop 8: Spec Edit Learning (Missing)
```
spec_writer generates spec.md → User manually edits before implementation →
  → Diff captured → Patterns learned: "User always adds [X] section"
```
**Signal:** Manual spec edits show gaps in spec_writer's understanding of user preferences.

**Data to capture:**
- Original spec.md vs. user-edited version (diff)
- Sections added/removed/modified
- Recurring edit patterns

**Use case:** "User has added 'Database Migration Notes' section to 5 specs. Auto-include in template."

#### Loop 9: Context Discovery Accuracy (Missing)
```
Context Discovery finds 15 files → Coder only references 8 →
  → Track accuracy: Some file patterns are over-included
```
**Signal:** context.json often includes files that aren't actually relevant.

**Data to capture:**
- Files included in context.json
- Files actually modified/read by coder
- Files that were missing (coder had to discover)

**Use case:** "test_*.py files are included 80% of time but used 10% of time. Reduce weight."

#### Loop 10: Research Value Tracking (Missing)
```
Research phase queries external docs → Some research used, some ignored →
  → Track: Which research queries produce actionable insights
```
**Signal:** The research phase can waste tokens on irrelevant queries.

**Data to capture:**
- Research queries made
- Research results referenced in spec/code
- Research that was ignored

**Use case:** "Research about 'Stripe webhooks' was used in 3 specs. Research about 'payment history' never used."

#### Loop 11: Recovery Strategy Learning (Missing)
```
Chunk fails → coder_recovery.md kicks in → Specific approach succeeds →
  → Record: "For stuck [chunk_type], try [approach] first"
```
**Signal:** When chunks fail and recovery succeeds, we should learn what worked.

**Data to capture:**
- What caused the chunk to get stuck
- What recovery approach was tried
- Which approach succeeded
- Time to recovery

**Use case:** "Import errors in this codebase: 80% resolved by checking __init__.py exports first."

#### Loop 12: Time Estimation Learning (Missing)
```
Planner estimates: "3 chunks, ~45 min" → Actual: 5 chunks, 2 hours →
  → Calibrate: This codebase takes 2x estimated time
```
**Signal:** Time estimates are currently generic, not calibrated to this codebase.

**Data to capture:**
- Estimated chunks/time per spec
- Actual chunks/time
- Factors that caused variance

**Use case:** "Specs in this project average 1.8x estimated time. Adjusting future estimates."

#### Loop 13: Roadmap Priority Learning (Missing)
```
Roadmap generates 20 features → User consistently picks "security" over "UI" →
  → Learn: Prioritize security-related features higher
```
**Signal:** User feature selection patterns reveal unstated priorities.

**Data to capture:**
- Features presented by roadmap
- Features user selected to implement
- Features user explicitly rejected
- Order of implementation

**Use case:** "User has implemented 5 security features before any UI features. Adjust priority weighting."

#### Loop 14: Requirements Clarification Learning (Missing)
```
Spec Gatherer asks: "Do you want auth?" → User clarifies: "Yes, JWT" →
  → Learn: This project prefers JWT for auth (don't ask again)
```
**Signal:** Clarifying questions and answers reveal project conventions.

**Data to capture:**
- Questions asked during requirements gathering
- User answers
- Whether the same question was asked in previous specs

**Use case:** "User has specified 'TypeScript strict mode' in 3 specs. Default to strict mode."

#### Loop 15: Merge Follow-up Learning (Future - requires user feedback)
```
Spec merged with --merge → 2 weeks later, user reports: "Caused regression" →
  → Associate: This pattern/approach caused issues post-merge
```
**Signal:** Some issues only surface after merge, in production use.

**Data to capture:**
- Post-merge issue reports (requires explicit user feedback)
- Association with spec patterns
- Time-to-issue-discovery

**Use case:** "Specs that modified auth/ directory have 30% higher post-merge issue rate."

---

### 12.6.2 Implementation Priority for Missing Loops

| Loop | Signal Strength | Implementation Effort | Data Already Available | Priority |
|------|-----------------|----------------------|------------------------|----------|
| **Loop 6: Discard Learning** | High (strong negative signal) | Small | Partial (need reason prompt) | P0 |
| **Loop 7: Complexity Calibration** | High (affects all planning) | Small | Yes (can compute from outcomes) | P0 |
| **Loop 8: Spec Edit Learning** | Medium (user preference signal) | Medium | Yes (can diff before/after) | P1 |
| **Loop 9: Context Accuracy** | Medium (reduces token waste) | Small | Yes (can compare context vs actual) | P1 |
| **Loop 11: Recovery Learning** | High (reduces stuck time) | Medium | Partial (need structured recovery logs) | P1 |
| **Loop 12: Time Estimation** | Medium (better UX) | Small | Yes (timestamps available) | P2 |
| **Loop 10: Research Value** | Low (only affects research phase) | Medium | Partial (need reference tracking) | P2 |
| **Loop 13: Roadmap Priority** | Medium (better prioritization) | Medium | Partial (need selection tracking) | P2 |
| **Loop 14: Requirements Learning** | Low (cumulative benefit) | Medium | No (need Q&A logging) | P3 |
| **Loop 15: Merge Follow-up** | High (but requires user action) | Large | No (requires feedback UI) | P3 |

### 12.6.3 Quick Wins: Loops That Can Be Added with Minimal Effort

These loops require only **adding recording calls to existing code paths**:

**1. Discard Learning (Loop 6)**
```python
# In run.py, when --discard is invoked:
async def handle_discard(spec_dir: Path, reason: str | None = None):
    # Existing discard logic...
    
    # NEW: Record discard for learning
    await record_spec_outcome(
        spec_id=spec_dir.name,
        outcome="discarded",
        stage_reached=get_current_stage(spec_dir),
        reason=reason,
        chunks_completed=count_completed_chunks(spec_dir),
    )
```

**2. Complexity Calibration (Loop 7)**
```python
# In qa_loop.py, when spec completes:
async def record_complexity_outcome(spec_dir: Path):
    assessment = load_json(spec_dir / "complexity_assessment.json")
    plan = load_json(spec_dir / "implementation_plan.json")
    
    await save_complexity_calibration(
        predicted=assessment["complexity"],
        actual_chunks=count_chunks(plan),
        actual_sessions=count_sessions(spec_dir),
        actual_qa_cycles=count_qa_cycles(spec_dir),
        task_keywords=assessment.get("keywords", []),
    )
```

**3. Context Accuracy (Loop 9)**
```python
# In agent.py, at end of implementation:
async def record_context_usage(spec_dir: Path, files_actually_used: set[str]):
    context = load_json(spec_dir / "context.json")
    files_in_context = set(context.get("relevant_files", []))
    
    await save_context_accuracy(
        files_predicted=files_in_context,
        files_used=files_actually_used,
        files_missed=files_actually_used - files_in_context,
        files_unused=files_in_context - files_actually_used,
    )
```

---

### 12.7 The Moat: Project-Specific Intelligence

After 200 specs, the system has something no general AI can replicate:

| General AI | Auto Claude @ Spec 200 |
|------------|------------------------|
| Knows Python patterns | Knows YOUR Python patterns |
| Suggests generic solutions | Suggests solutions that worked HERE |
| Can't predict your bugs | Predicts YOUR specific bugs |
| Doesn't know your history | Knows why every file exists |
| Treats each task fresh | Builds on 200 specs of context |

**This is the moat**: The longer you use Auto Claude on a project, the more valuable it becomes. The knowledge is specific to YOUR codebase, YOUR patterns, YOUR gotchas.

A new AI tool starts at zero. Auto Claude at Spec 200 has:
- 10,000+ knowledge nodes
- 700+ session insights
- 200+ spec outcomes
- Complete architectural understanding
- Predictive models trained on YOUR code

---

### 12.8 Enabling This Vision

To achieve this vision, the system needs:

| Capability | Required For | Status |
|------------|--------------|--------|
| **Historical Context Phase** | Cross-spec learning | This PRD |
| **Project-level Memory** | Accumulated knowledge | This PRD |
| **QA Outcome Recording** | Feedback loop | This PRD |
| **Graphiti Integration** | Semantic search | Existing (underutilized) |
| **Chunk Statistics** | Complexity prediction | Future (Section 11) |
| **Architectural Modeling** | Impact prediction | Future |
| **Causal Graph** | "Why" explanations | Future |

#### What Each Implementation Phase Enables

| Phase | Immediate (Spec 1-5) | Medium-term (Spec 20) | Long-term (Spec 60+) |
|-------|---------------------|----------------------|---------------------|
| **Phase 1: Foundation** | Project-level search works | Cross-spec pattern matching | Statistical queries |
| **Phase 2: Historical Context** | "No history" placeholder | "Similar past tasks" surfaced | Ranked recommendations |
| **Phase 3: Prompt Updates** | Agents read history | Agents use patterns | Agents predict issues |
| **Phase 4: QA Feedback** | Outcomes recorded | Feedback loop active | Success rate tracking |
| **Phase 5: Ideation** | Avoid duplicates | Pattern extension ideas | Informed suggestions |

#### What This PRD Does NOT Enable (Future Work)

These capabilities require additional infrastructure beyond this PRD:

| Future Capability | Why It's Not Here | Prerequisite |
|-------------------|-------------------|--------------|
| **Causal graph reasoning** | Requires graph schema extension | 50+ specs of data |
| **Complexity prediction models** | Requires statistical learning | 60+ specs of data |
| **Architectural impact analysis** | Requires dependency graph | Codebase map evolution |
| **Multi-project learning** | Requires federated setup | Privacy/consent model |
| **File-level bug prediction** | Requires ML pipeline | Significant training data |

These build ON TOP of the foundation this PRD creates. They cannot exist without bidirectional memory flow.

The Smart Context System (this PRD) is the **foundation** that enables all future improvements. Without bidirectional memory flow, none of the advanced capabilities are possible.

---

### 12.9 The Ultimate Goal

By Spec 200, Auto Claude should be able to:

1. **Understand intent**: "Add user notifications" → knows exactly what that means in THIS codebase
2. **Predict problems**: "This will conflict with the rate limiter we added in Spec-67"
3. **Suggest approaches**: "We solved something similar in Spec-89, here's what worked"
4. **Explain history**: "This code looks weird because of the incident in Spec-45"
5. **Prevent regressions**: "This change would break the pattern we've used in 15 other places"
6. **Estimate accurately**: "This will take 3 chunks, ~4 sessions, based on similar past work"

**The system becomes a senior developer who has worked on your project for years** - because in a very real sense, it has.

---

*End of PRD*

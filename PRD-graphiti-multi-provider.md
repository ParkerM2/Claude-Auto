# PRD: Graphiti Multi-Provider Support

> **Status:** Draft v1
> **Author:** Claude
> **Created:** 2025-12-11
> **Target:** Auto Claude Graphiti Memory Integration
> **Depends On:** Smart Context System PRD (for Graphiti architecture)

---

## 1. Problem Statement

### Current Limitation

The current Graphiti integration **only supports OpenAI** for both embeddings and LLM (graph extraction):

```python
# Current graphiti_config.py (line 93-101)
def is_valid(self) -> bool:
    """
    Graphiti requires:
    - GRAPHITI_ENABLED=true
    - OPENAI_API_KEY set (for embeddings)  # <-- ONLY OpenAI
    """
    return self.enabled and bool(self.openai_api_key)
```

### Why This Matters

| User Scenario | Current Support | Impact |
|---------------|-----------------|--------|
| Enterprise with Azure OpenAI only | ❌ Not supported | Can't use Graphiti |
| Privacy-conscious (local-only) | ❌ Not supported | Can't use Graphiti |
| Already using Anthropic Claude | Partial (LLM only, needs OpenAI for embeddings) | Extra API costs |
| Cost-sensitive users | ❌ Locked to OpenAI pricing | Higher costs |

### Graphiti's Actual Capabilities

Graphiti supports **many providers** out of the box:

| Component | Supported Providers |
|-----------|---------------------|
| **Embeddings** | OpenAI, Azure OpenAI, Voyage AI, Gemini, Ollama (local), Sentence Transformers (local) |
| **LLM (Graph Extraction)** | OpenAI, Azure OpenAI, Anthropic, Gemini, Groq, Ollama (local) |
| **Cross-Encoder (Reranking)** | OpenAI, Gemini, Ollama (local) |

**We're only using a fraction of what's available.**

---

## 2. Goals

### Primary Goals

1. **Azure OpenAI Support** - Enable enterprise users with Azure-only policies
2. **Ollama Support** - Enable fully local/offline operation
3. **Anthropic LLM Support** - Use Claude for graph extraction (already using it elsewhere)

### Secondary Goals

4. **Voyage AI Support** - Anthropic's recommended embedding provider
5. **Provider flexibility** - Mix-and-match (e.g., Anthropic LLM + Voyage embeddings)

### Non-Goals

- Supporting every provider Graphiti supports (Groq, Gemini, etc.)
- Building our own embedding/LLM abstraction layer
- Changing the core memory architecture

---

## 3. Provider Analysis

### 3.1 Anthropic (LLM Only - NO Embeddings)

> ⚠️ **IMPORTANT:** Anthropic does NOT offer embedding models. They officially recommend Voyage AI for embeddings.

| Aspect | Details |
|--------|---------|
| **Use For** | LLM/Graph extraction only |
| **Models** | `claude-sonnet-4-5-latest`, `claude-opus-4-5-latest` |
| **Graphiti Client** | `AnthropicClient` from `graphiti_core.llm_client.anthropic_client` |
| **API Key Env** | `ANTHROPIC_API_KEY` |
| **Install** | `pip install graphiti-core[anthropic]` |

**Why Use Anthropic for LLM?**
- Already using Claude for agents (consistency)
- Strong reasoning for entity extraction
- Avoids needing OpenAI API key just for graph extraction

**Pairing Options:**
- Anthropic LLM + OpenAI embeddings
- Anthropic LLM + Voyage AI embeddings (Anthropic's recommendation)
- Anthropic LLM + Ollama embeddings (fully avoid OpenAI)

### 3.2 Azure OpenAI (Full Support)

| Aspect | Details |
|--------|---------|
| **Use For** | Both LLM and embeddings |
| **LLM Models** | Your Azure deployment names |
| **Embedding Models** | `text-embedding-3-small`, `text-embedding-3-large` |
| **Graphiti Clients** | `AzureOpenAILLMClient`, `AzureOpenAIEmbedderClient` |
| **Required Config** | Base URL, API key, deployment names |

**Why Use Azure OpenAI?**
- Enterprise compliance requirements
- Already have Azure infrastructure
- Data residency requirements
- Existing Azure spending commitments

### 3.3 Ollama (Fully Local)

| Aspect | Details |
|--------|---------|
| **Use For** | Both LLM and embeddings (local) |
| **LLM Models** | `deepseek-r1:7b`, `llama3:8b`, `mistral:7b`, etc. |
| **Embedding Models** | `nomic-embed-text`, `mxbai-embed-large`, etc. |
| **Graphiti Clients** | `OpenAIGenericClient` (compatible), `OpenAIEmbedder` (compatible) |
| **Base URL** | `http://localhost:11434/v1` |

**Why Use Ollama?**
- Zero API costs
- Complete privacy (no data leaves machine)
- Works offline
- Good for development/testing

**Tradeoffs:**
- Requires local GPU for good performance
- Embedding quality may be lower than OpenAI/Voyage
- LLM quality depends on model size

### 3.4 Voyage AI (Embeddings Only)

| Aspect | Details |
|--------|---------|
| **Use For** | Embeddings only |
| **Models** | `voyage-3`, `voyage-3-lite`, `voyage-code-3`, `voyage-finance-2` |
| **Graphiti Client** | `VoyageEmbedder` from `graphiti_core.embedder.voyage` |
| **API Key Env** | `VOYAGE_API_KEY` |

**Why Use Voyage AI?**
- Anthropic's official recommendation
- Specialized models (code, finance, law)
- High quality embeddings
- Reasonable pricing

---

## 4. Proposed Configuration Schema

### 4.1 Environment Variables

```bash
# === Provider Selection ===
GRAPHITI_ENABLED=true

# LLM Provider: "openai" | "azure_openai" | "anthropic" | "ollama"
GRAPHITI_LLM_PROVIDER=openai

# Embedder Provider: "openai" | "azure_openai" | "voyage" | "ollama"
GRAPHITI_EMBEDDER_PROVIDER=openai

# === OpenAI (default) ===
OPENAI_API_KEY=sk-...

# === Anthropic (LLM only) ===
ANTHROPIC_API_KEY=sk-ant-...
GRAPHITI_ANTHROPIC_MODEL=claude-sonnet-4-5-latest

# === Azure OpenAI ===
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_BASE_URL=https://your-resource.openai.azure.com/openai/v1/
AZURE_OPENAI_LLM_DEPLOYMENT=gpt-4o  # Your deployment name
AZURE_OPENAI_EMBEDDING_DEPLOYMENT=text-embedding-3-small

# === Ollama (local) ===
OLLAMA_BASE_URL=http://localhost:11434/v1
OLLAMA_LLM_MODEL=deepseek-r1:7b
OLLAMA_EMBEDDING_MODEL=nomic-embed-text
OLLAMA_EMBEDDING_DIM=768

# === Voyage AI (embeddings only) ===
VOYAGE_API_KEY=pa-...
VOYAGE_EMBEDDING_MODEL=voyage-3
```

### 4.2 Configuration Combinations

| Combo | LLM Provider | Embedder Provider | Use Case |
|-------|--------------|-------------------|----------|
| **Default** | OpenAI | OpenAI | Simple setup, good quality |
| **Enterprise** | Azure OpenAI | Azure OpenAI | Corporate compliance |
| **Claude Stack** | Anthropic | Voyage | Consistency with agent stack |
| **Fully Local** | Ollama | Ollama | Privacy, offline, zero cost |
| **Hybrid Local** | Ollama | OpenAI | Local LLM, quality embeddings |
| **Cost Optimized** | Anthropic | Ollama | Cloud LLM, free embeddings |

---

## 5. Technical Design

### 5.1 Updated GraphitiConfig

```python
@dataclass
class GraphitiConfig:
    """Configuration for Graphiti memory integration."""
    enabled: bool = False
    
    # Provider selection
    llm_provider: str = "openai"  # openai, azure_openai, anthropic, ollama
    embedder_provider: str = "openai"  # openai, azure_openai, voyage, ollama
    
    # OpenAI
    openai_api_key: str = ""
    
    # Anthropic
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-5-latest"
    
    # Azure OpenAI
    azure_api_key: str = ""
    azure_base_url: str = ""
    azure_llm_deployment: str = ""
    azure_embedding_deployment: str = ""
    
    # Ollama
    ollama_base_url: str = "http://localhost:11434/v1"
    ollama_llm_model: str = "deepseek-r1:7b"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_embedding_dim: int = 768
    
    # Voyage
    voyage_api_key: str = ""
    voyage_embedding_model: str = "voyage-3"
    
    # FalkorDB (unchanged)
    falkordb_host: str = "localhost"
    falkordb_port: int = 6380
    falkordb_password: str = ""
    database: str = "auto_build_memory"

    def is_valid(self) -> bool:
        """Check if config has required values for selected providers."""
        # Check LLM provider
        llm_valid = self._validate_llm_provider()
        # Check embedder provider
        embedder_valid = self._validate_embedder_provider()
        
        return self.enabled and llm_valid and embedder_valid
    
    def _validate_llm_provider(self) -> bool:
        if self.llm_provider == "openai":
            return bool(self.openai_api_key)
        elif self.llm_provider == "anthropic":
            return bool(self.anthropic_api_key)
        elif self.llm_provider == "azure_openai":
            return bool(self.azure_api_key and self.azure_base_url and self.azure_llm_deployment)
        elif self.llm_provider == "ollama":
            return bool(self.ollama_base_url and self.ollama_llm_model)
        return False
    
    def _validate_embedder_provider(self) -> bool:
        if self.embedder_provider == "openai":
            return bool(self.openai_api_key)
        elif self.embedder_provider == "voyage":
            return bool(self.voyage_api_key)
        elif self.embedder_provider == "azure_openai":
            return bool(self.azure_api_key and self.azure_base_url and self.azure_embedding_deployment)
        elif self.embedder_provider == "ollama":
            return bool(self.ollama_base_url and self.ollama_embedding_model)
        return False
```

### 5.2 Provider Factory

```python
# New file: auto-claude/graphiti_providers.py

from graphiti_core.llm_client.config import LLMConfig

def create_llm_client(config: GraphitiConfig):
    """Create LLM client based on provider selection."""
    
    if config.llm_provider == "openai":
        from graphiti_core.llm_client.openai_client import OpenAIClient
        return OpenAIClient(
            config=LLMConfig(api_key=config.openai_api_key)
        )
    
    elif config.llm_provider == "anthropic":
        from graphiti_core.llm_client.anthropic_client import AnthropicClient
        return AnthropicClient(
            config=LLMConfig(
                api_key=config.anthropic_api_key,
                model=config.anthropic_model
            )
        )
    
    elif config.llm_provider == "azure_openai":
        from openai import AsyncOpenAI
        from graphiti_core.llm_client.azure_openai_client import AzureOpenAILLMClient
        
        azure_client = AsyncOpenAI(
            base_url=config.azure_base_url,
            api_key=config.azure_api_key,
        )
        return AzureOpenAILLMClient(
            azure_client=azure_client,
            config=LLMConfig(model=config.azure_llm_deployment)
        )
    
    elif config.llm_provider == "ollama":
        from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
        return OpenAIGenericClient(
            config=LLMConfig(
                api_key="ollama",  # Dummy key required
                model=config.ollama_llm_model,
                base_url=config.ollama_base_url,
            )
        )
    
    raise ValueError(f"Unknown LLM provider: {config.llm_provider}")


def create_embedder(config: GraphitiConfig):
    """Create embedder based on provider selection."""
    
    if config.embedder_provider == "openai":
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        return OpenAIEmbedder(
            config=OpenAIEmbedderConfig(api_key=config.openai_api_key)
        )
    
    elif config.embedder_provider == "voyage":
        from graphiti_core.embedder.voyage import VoyageEmbedder, VoyageAIConfig
        return VoyageEmbedder(
            config=VoyageAIConfig(
                api_key=config.voyage_api_key,
                embedding_model=config.voyage_embedding_model
            )
        )
    
    elif config.embedder_provider == "azure_openai":
        from openai import AsyncOpenAI
        from graphiti_core.embedder.azure_openai import AzureOpenAIEmbedderClient
        
        azure_client = AsyncOpenAI(
            base_url=config.azure_base_url,
            api_key=config.azure_api_key,
        )
        return AzureOpenAIEmbedderClient(
            azure_client=azure_client,
            model=config.azure_embedding_deployment
        )
    
    elif config.embedder_provider == "ollama":
        from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
        return OpenAIEmbedder(
            config=OpenAIEmbedderConfig(
                api_key="ollama",  # Dummy key
                embedding_model=config.ollama_embedding_model,
                embedding_dim=config.ollama_embedding_dim,
                base_url=config.ollama_base_url,
            )
        )
    
    raise ValueError(f"Unknown embedder provider: {config.embedder_provider}")
```

### 5.3 Updated GraphitiMemory Initialization

```python
# Updated graphiti_memory.py initialize() method

async def initialize(self) -> bool:
    if self._initialized:
        return True

    if not self._available:
        logger.info("Graphiti not available - skipping initialization")
        return False

    try:
        from graphiti_core import Graphiti
        from graphiti_core.driver.falkordb_driver import FalkorDriver
        from graphiti_providers import create_llm_client, create_embedder

        # Initialize FalkorDB driver
        self._driver = FalkorDriver(
            host=self.config.falkordb_host,
            port=self.config.falkordb_port,
            password=self.config.falkordb_password or None,
            database=self.config.database,
        )

        # Create provider-specific clients
        llm_client = create_llm_client(self.config)
        embedder = create_embedder(self.config)

        # Initialize Graphiti with configured providers
        self._graphiti = Graphiti(
            graph_driver=self._driver,
            llm_client=llm_client,
            embedder=embedder,
        )

        # Build indices (first time only)
        if not self.state or not self.state.indices_built:
            logger.info("Building Graphiti indices and constraints...")
            await self._graphiti.build_indices_and_constraints()
            # ... rest unchanged

        self._initialized = True
        logger.info(
            f"Graphiti initialized for spec: {self.group_id} "
            f"(LLM: {self.config.llm_provider}, Embedder: {self.config.embedder_provider})"
        )
        return True

    except ImportError as e:
        # Handle missing provider packages
        logger.warning(f"Graphiti provider packages not installed: {e}")
        self._available = False
        return False
    # ... rest unchanged
```

---

## 6. Implementation Plan

### Phase 1: Core Infrastructure

| Task | File | Effort |
|------|------|--------|
| Update `GraphitiConfig` with provider fields | `graphiti_config.py` | Medium |
| Update `from_env()` to read new env vars | `graphiti_config.py` | Medium |
| Update `is_valid()` for provider validation | `graphiti_config.py` | Small |
| Create `graphiti_providers.py` with factories | New file | Medium |
| Update `initialize()` to use factories | `graphiti_memory.py` | Small |

### Phase 2: Provider Implementations

| Task | File | Effort |
|------|------|--------|
| Implement OpenAI provider (refactor existing) | `graphiti_providers.py` | Small |
| Implement Anthropic LLM provider | `graphiti_providers.py` | Small |
| Implement Azure OpenAI providers | `graphiti_providers.py` | Medium |
| Implement Ollama providers | `graphiti_providers.py` | Medium |
| Implement Voyage embedder | `graphiti_providers.py` | Small |

### Phase 3: Testing & Documentation

| Task | File | Effort |
|------|------|--------|
| Add provider unit tests | `tests/test_graphiti_providers.py` | Medium |
| Add integration tests per provider | `tests/test_graphiti_integration.py` | Large |
| Update `.env.example` with all options | `.env.example` | Small |
| Update CLAUDE.md with provider docs | `CLAUDE.md` | Small |
| Add troubleshooting guide | `docs/graphiti-providers.md` | Medium |

### Phase 4: UI Integration (Required)

| Task | File | Effort |
|------|------|--------|
| Add Graphiti section to AppSettings | `AppSettings.tsx` | Medium |
| Add provider selection dropdowns | `AppSettings.tsx` | Medium |
| Add conditional API key fields | `AppSettings.tsx` | Medium |
| Add Ollama connection test button | `AppSettings.tsx` | Small |
| Update AppSettings types | `shared/types.ts` | Small |
| Update settings store | `settings-store.ts` | Small |
| Add IPC handlers for provider validation | `ipc-handlers.ts` | Medium |

---

## 6.5 UI Design: Application Settings

The Graphiti provider configuration lives in **Application Settings** (`AppSettings.tsx`), NOT per-project settings. This ensures consistent memory configuration across all projects.

### 6.5.1 Location in UI

```
Application Settings Dialog
├── Appearance (existing)
│   └── Theme
├── Default Agent Settings (existing)
│   ├── Default Model
│   └── Default Parallelism
├── Paths (existing)
│   ├── Python Path
│   └── Auto Claude Path
├── Global API Keys (existing - EXTEND)
│   ├── Claude OAuth Token
│   ├── OpenAI API Key
│   └── [NEW] Additional provider keys (conditional)
├── [NEW] Graphiti Memory Settings ◄──────────────────
│   ├── Enable Graphiti Memory (toggle)
│   ├── LLM Provider (dropdown)
│   ├── Embedder Provider (dropdown)
│   ├── Provider-specific configuration (conditional)
│   └── Connection test button
├── Auto Claude Framework (existing)
└── Notifications (existing)
```

### 6.5.2 New Section: Graphiti Memory Settings

```tsx
{/* Graphiti Memory Settings - NEW SECTION */}
<section className="space-y-4">
  <div className="flex items-center gap-2">
    <Database className="h-4 w-4" />
    <h3 className="text-sm font-semibold text-foreground">Graphiti Memory</h3>
  </div>
  
  {/* Info banner */}
  <div className="rounded-lg bg-info/10 border border-info/30 p-3">
    <div className="flex items-start gap-2">
      <Info className="h-4 w-4 text-info flex-shrink-0 mt-0.5" />
      <p className="text-xs text-muted-foreground">
        Graphiti provides semantic memory for cross-session learning. 
        Requires FalkorDB running locally (Docker).
      </p>
    </div>
  </div>
  
  {/* Enable toggle */}
  <div className="flex items-center justify-between">
    <div className="space-y-0.5">
      <Label className="font-normal text-foreground">Enable Graphiti Memory</Label>
      <p className="text-xs text-muted-foreground">
        Enables semantic search across sessions (requires Docker)
      </p>
    </div>
    <Switch
      checked={settings.graphiti.enabled}
      onCheckedChange={(checked) =>
        setSettings({
          ...settings,
          graphiti: { ...settings.graphiti, enabled: checked }
        })
      }
    />
  </div>
  
  {/* Provider settings - only shown when enabled */}
  {settings.graphiti.enabled && (
    <div className="space-y-4 pl-4 border-l-2 border-border">
      
      {/* LLM Provider */}
      <div className="space-y-2">
        <Label className="text-sm font-medium text-foreground">
          LLM Provider (Graph Extraction)
        </Label>
        <Select
          value={settings.graphiti.llmProvider}
          onValueChange={(value) =>
            setSettings({
              ...settings,
              graphiti: { ...settings.graphiti, llmProvider: value }
            })
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="openai">OpenAI</SelectItem>
            <SelectItem value="anthropic">Anthropic Claude</SelectItem>
            <SelectItem value="azure_openai">Azure OpenAI</SelectItem>
            <SelectItem value="ollama">Ollama (Local)</SelectItem>
          </SelectContent>
        </Select>
      </div>
      
      {/* Embedder Provider */}
      <div className="space-y-2">
        <Label className="text-sm font-medium text-foreground">
          Embedder Provider
        </Label>
        <Select
          value={settings.graphiti.embedderProvider}
          onValueChange={(value) =>
            setSettings({
              ...settings,
              graphiti: { ...settings.graphiti, embedderProvider: value }
            })
          }
        >
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="openai">OpenAI</SelectItem>
            <SelectItem value="azure_openai">Azure OpenAI</SelectItem>
            <SelectItem value="voyage">Voyage AI</SelectItem>
            <SelectItem value="ollama">Ollama (Local)</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Note: Anthropic does not provide embeddings. Use Voyage AI (recommended) or another provider.
        </p>
      </div>
      
      {/* Conditional: Anthropic settings */}
      {settings.graphiti.llmProvider === 'anthropic' && (
        <div className="space-y-2">
          <Label className="text-sm font-medium text-foreground">
            Anthropic API Key
          </Label>
          <Input
            type="password"
            placeholder="sk-ant-..."
            value={settings.graphiti.anthropicApiKey || ''}
            onChange={(e) =>
              setSettings({
                ...settings,
                graphiti: { ...settings.graphiti, anthropicApiKey: e.target.value }
              })
            }
          />
        </div>
      )}
      
      {/* Conditional: Voyage settings */}
      {settings.graphiti.embedderProvider === 'voyage' && (
        <div className="space-y-2">
          <Label className="text-sm font-medium text-foreground">
            Voyage AI API Key
          </Label>
          <Input
            type="password"
            placeholder="pa-..."
            value={settings.graphiti.voyageApiKey || ''}
            onChange={(e) =>
              setSettings({
                ...settings,
                graphiti: { ...settings.graphiti, voyageApiKey: e.target.value }
              })
            }
          />
        </div>
      )}
      
      {/* Conditional: Azure OpenAI settings */}
      {(settings.graphiti.llmProvider === 'azure_openai' || 
        settings.graphiti.embedderProvider === 'azure_openai') && (
        <div className="space-y-4 rounded-lg border border-border p-3">
          <p className="text-xs font-medium text-foreground">Azure OpenAI Configuration</p>
          <div className="space-y-2">
            <Label className="text-xs">Base URL</Label>
            <Input
              placeholder="https://your-resource.openai.azure.com/openai/v1/"
              value={settings.graphiti.azureBaseUrl || ''}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  graphiti: { ...settings.graphiti, azureBaseUrl: e.target.value }
                })
              }
            />
          </div>
          <div className="space-y-2">
            <Label className="text-xs">API Key</Label>
            <Input
              type="password"
              value={settings.graphiti.azureApiKey || ''}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  graphiti: { ...settings.graphiti, azureApiKey: e.target.value }
                })
              }
            />
          </div>
          {settings.graphiti.llmProvider === 'azure_openai' && (
            <div className="space-y-2">
              <Label className="text-xs">LLM Deployment Name</Label>
              <Input
                placeholder="gpt-4o"
                value={settings.graphiti.azureLlmDeployment || ''}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    graphiti: { ...settings.graphiti, azureLlmDeployment: e.target.value }
                  })
                }
              />
            </div>
          )}
          {settings.graphiti.embedderProvider === 'azure_openai' && (
            <div className="space-y-2">
              <Label className="text-xs">Embedding Deployment Name</Label>
              <Input
                placeholder="text-embedding-3-small"
                value={settings.graphiti.azureEmbeddingDeployment || ''}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    graphiti: { ...settings.graphiti, azureEmbeddingDeployment: e.target.value }
                  })
                }
              />
            </div>
          )}
        </div>
      )}
      
      {/* Conditional: Ollama settings */}
      {(settings.graphiti.llmProvider === 'ollama' || 
        settings.graphiti.embedderProvider === 'ollama') && (
        <div className="space-y-4 rounded-lg border border-border p-3">
          <p className="text-xs font-medium text-foreground">Ollama Configuration (Local)</p>
          <div className="space-y-2">
            <Label className="text-xs">Ollama URL</Label>
            <Input
              placeholder="http://localhost:11434/v1"
              value={settings.graphiti.ollamaBaseUrl || 'http://localhost:11434/v1'}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  graphiti: { ...settings.graphiti, ollamaBaseUrl: e.target.value }
                })
              }
            />
          </div>
          {settings.graphiti.llmProvider === 'ollama' && (
            <div className="space-y-2">
              <Label className="text-xs">LLM Model</Label>
              <Input
                placeholder="deepseek-r1:7b"
                value={settings.graphiti.ollamaLlmModel || ''}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    graphiti: { ...settings.graphiti, ollamaLlmModel: e.target.value }
                  })
                }
              />
            </div>
          )}
          {settings.graphiti.embedderProvider === 'ollama' && (
            <div className="space-y-2">
              <Label className="text-xs">Embedding Model</Label>
              <Input
                placeholder="nomic-embed-text"
                value={settings.graphiti.ollamaEmbeddingModel || ''}
                onChange={(e) =>
                  setSettings({
                    ...settings,
                    graphiti: { ...settings.graphiti, ollamaEmbeddingModel: e.target.value }
                  })
                }
              />
            </div>
          )}
          <Button
            size="sm"
            variant="outline"
            onClick={testOllamaConnection}
            disabled={isTestingOllama}
          >
            {isTestingOllama ? (
              <Loader2 className="mr-2 h-3 w-3 animate-spin" />
            ) : (
              <Plug className="mr-2 h-3 w-3" />
            )}
            Test Connection
          </Button>
        </div>
      )}
      
      {/* FalkorDB settings */}
      <div className="space-y-4 rounded-lg border border-border p-3">
        <p className="text-xs font-medium text-foreground">FalkorDB Connection</p>
        <div className="grid grid-cols-2 gap-2">
          <div className="space-y-1">
            <Label className="text-xs">Host</Label>
            <Input
              placeholder="localhost"
              value={settings.graphiti.falkordbHost || 'localhost'}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  graphiti: { ...settings.graphiti, falkordbHost: e.target.value }
                })
              }
            />
          </div>
          <div className="space-y-1">
            <Label className="text-xs">Port</Label>
            <Input
              type="number"
              placeholder="6380"
              value={settings.graphiti.falkordbPort || 6380}
              onChange={(e) =>
                setSettings({
                  ...settings,
                  graphiti: { ...settings.graphiti, falkordbPort: parseInt(e.target.value) }
                })
              }
            />
          </div>
        </div>
        <Button
          size="sm"
          variant="outline"
          onClick={testFalkorDBConnection}
          disabled={isTestingFalkorDB}
        >
          {isTestingFalkorDB ? (
            <Loader2 className="mr-2 h-3 w-3 animate-spin" />
          ) : (
            <Database className="mr-2 h-3 w-3" />
          )}
          Test FalkorDB Connection
        </Button>
      </div>
    </div>
  )}
</section>
```

### 6.5.3 Types Update (`shared/types.ts`)

```typescript
// Add to AppSettings interface
export interface AppSettings {
  // ... existing fields ...
  
  graphiti: GraphitiUISettings;
}

export interface GraphitiUISettings {
  enabled: boolean;
  
  // Provider selection
  llmProvider: 'openai' | 'anthropic' | 'azure_openai' | 'ollama';
  embedderProvider: 'openai' | 'azure_openai' | 'voyage' | 'ollama';
  
  // Provider-specific API keys
  anthropicApiKey?: string;
  voyageApiKey?: string;
  
  // Azure OpenAI
  azureBaseUrl?: string;
  azureApiKey?: string;
  azureLlmDeployment?: string;
  azureEmbeddingDeployment?: string;
  
  // Ollama
  ollamaBaseUrl?: string;
  ollamaLlmModel?: string;
  ollamaEmbeddingModel?: string;
  
  // FalkorDB
  falkordbHost?: string;
  falkordbPort?: number;
  falkordbPassword?: string;
}
```

### 6.5.4 Settings to Environment Variables

When saving settings, the UI writes to the appropriate environment variables:

```typescript
// In ipc-handlers.ts or settings-store.ts

function graphitiSettingsToEnv(settings: GraphitiUISettings): Record<string, string> {
  const env: Record<string, string> = {
    GRAPHITI_ENABLED: settings.enabled ? 'true' : 'false',
    GRAPHITI_LLM_PROVIDER: settings.llmProvider,
    GRAPHITI_EMBEDDER_PROVIDER: settings.embedderProvider,
    GRAPHITI_FALKORDB_HOST: settings.falkordbHost || 'localhost',
    GRAPHITI_FALKORDB_PORT: String(settings.falkordbPort || 6380),
  };
  
  // Anthropic
  if (settings.anthropicApiKey) {
    env.ANTHROPIC_API_KEY = settings.anthropicApiKey;
  }
  
  // Voyage
  if (settings.voyageApiKey) {
    env.VOYAGE_API_KEY = settings.voyageApiKey;
  }
  
  // Azure OpenAI
  if (settings.azureBaseUrl) {
    env.AZURE_OPENAI_BASE_URL = settings.azureBaseUrl;
  }
  if (settings.azureApiKey) {
    env.AZURE_OPENAI_API_KEY = settings.azureApiKey;
  }
  if (settings.azureLlmDeployment) {
    env.AZURE_OPENAI_LLM_DEPLOYMENT = settings.azureLlmDeployment;
  }
  if (settings.azureEmbeddingDeployment) {
    env.AZURE_OPENAI_EMBEDDING_DEPLOYMENT = settings.azureEmbeddingDeployment;
  }
  
  // Ollama
  if (settings.ollamaBaseUrl) {
    env.OLLAMA_BASE_URL = settings.ollamaBaseUrl;
  }
  if (settings.ollamaLlmModel) {
    env.OLLAMA_LLM_MODEL = settings.ollamaLlmModel;
  }
  if (settings.ollamaEmbeddingModel) {
    env.OLLAMA_EMBEDDING_MODEL = settings.ollamaEmbeddingModel;
  }
  
  // FalkorDB password
  if (settings.falkordbPassword) {
    env.GRAPHITI_FALKORDB_PASSWORD = settings.falkordbPassword;
  }
  
  return env;
}
```

### 6.5.5 Validation Rules

| Provider Combo | Required Fields |
|----------------|-----------------|
| LLM: OpenAI | `globalOpenAIApiKey` (existing) |
| LLM: Anthropic | `anthropicApiKey` |
| LLM: Azure | `azureBaseUrl`, `azureApiKey`, `azureLlmDeployment` |
| LLM: Ollama | `ollamaBaseUrl`, `ollamaLlmModel` |
| Embedder: OpenAI | `globalOpenAIApiKey` (existing) |
| Embedder: Voyage | `voyageApiKey` |
| Embedder: Azure | `azureBaseUrl`, `azureApiKey`, `azureEmbeddingDeployment` |
| Embedder: Ollama | `ollamaBaseUrl`, `ollamaEmbeddingModel` |

### 6.5.6 UI States

| State | Appearance |
|-------|------------|
| Graphiti disabled | Only enable toggle shown |
| Graphiti enabled, no FalkorDB | Warning banner: "FalkorDB not running" |
| Graphiti enabled, connected | Success indicator |
| Provider misconfigured | Red border on missing fields, save disabled |
| Testing connection | Spinner on test button |
| Connection test passed | Green check, "Connected" message |
| Connection test failed | Red X, error message |

---

## 7. Files to Modify

### Backend (auto-claude/)

| File | Changes |
|------|---------|
| `graphiti_config.py` | Add provider fields, validation logic, env var parsing |
| `graphiti_memory.py` | Update `initialize()` to use provider factories |
| `.env.example` | Add all provider environment variables |
| `CLAUDE.md` | Document provider options |
| `requirements.txt` | Add optional provider extras |

### Frontend (auto-claude-ui/)

| File | Changes |
|------|---------|
| `src/renderer/components/AppSettings.tsx` | Add Graphiti Memory section with provider dropdowns, conditional fields, test buttons |
| `src/shared/types.ts` | Add `GraphitiUISettings` interface, extend `AppSettings` |
| `src/renderer/stores/settings-store.ts` | Add graphiti settings handling, env conversion |
| `src/main/ipc-handlers.ts` | Add handlers for connection tests (`testOllamaConnection`, `testFalkorDBConnection`) |
| `src/preload/index.ts` | Expose new IPC methods |

### New Files

| File | Purpose |
|------|---------|
| `auto-claude/graphiti_providers.py` | Provider factory functions |
| `tests/test_graphiti_providers.py` | Unit tests for provider creation |
| `docs/graphiti-providers.md` | Provider setup documentation |

---

## 8. Dependencies

### Required Packages by Provider

```txt
# Base (always needed)
graphiti-core[falkordb]

# Optional - install based on provider selection
graphiti-core[anthropic]  # For Anthropic LLM
# Note: Azure, Ollama, Voyage use base graphiti-core
```

### Ollama Setup (Local)

```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh

# Pull required models
ollama pull deepseek-r1:7b      # LLM
ollama pull nomic-embed-text    # Embeddings

# Verify running
curl http://localhost:11434/v1/models
```

---

## 9. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Provider API differences | Medium | Medium | Graphiti abstracts this; test each provider |
| Ollama quality issues | Medium | Low | Document as "development/testing" option |
| Azure config complexity | Low | Medium | Provide clear examples, validation errors |
| Missing provider packages | Medium | Low | Clear error messages, graceful degradation |
| Embedding dimension mismatches | Low | High | Validate dimensions at init time |

---

## 10. Success Criteria

### MVP

- [ ] Azure OpenAI works for both LLM and embeddings
- [ ] Ollama works for both LLM and embeddings
- [ ] Anthropic works for LLM (with OpenAI/Voyage embeddings)
- [ ] Provider selection via environment variables
- [ ] Clear error messages for misconfiguration

### Complete

- [ ] All MVP criteria
- [ ] Voyage AI embeddings supported
- [ ] All providers have unit tests
- [ ] Integration tests pass for each provider combo
- [ ] Documentation complete
- [ ] UI supports provider selection (optional)

---

## 11. Appendix

### A. Provider Comparison

| Provider | LLM | Embeddings | Cost | Quality | Privacy |
|----------|-----|------------|------|---------|---------|
| OpenAI | ✅ | ✅ | $$ | High | Cloud |
| Azure OpenAI | ✅ | ✅ | $$ | High | Enterprise |
| Anthropic | ✅ | ❌ | $$ | High | Cloud |
| Voyage AI | ❌ | ✅ | $ | High | Cloud |
| Ollama | ✅ | ✅ | Free | Medium | Local |

### B. Recommended Combinations

| User Type | LLM | Embedder | Rationale |
|-----------|-----|----------|-----------|
| **Default** | OpenAI | OpenAI | Simple, good quality |
| **Enterprise** | Azure | Azure | Compliance, data residency |
| **Claude-first** | Anthropic | Voyage | Anthropic's recommendation |
| **Privacy-focused** | Ollama | Ollama | Fully local |
| **Budget dev** | Ollama | Ollama | Zero API costs |

### C. Embedding Dimensions by Model

| Provider | Model | Dimensions |
|----------|-------|------------|
| OpenAI | text-embedding-3-small | 1536 |
| OpenAI | text-embedding-3-large | 3072 |
| Voyage | voyage-3 | 1024 |
| Voyage | voyage-3-lite | 512 |
| Ollama | nomic-embed-text | 768 |
| Ollama | mxbai-embed-large | 1024 |

### D. Error Messages

```python
ERROR_MESSAGES = {
    "anthropic_no_embeddings": (
        "Anthropic does not provide embedding models. "
        "Please use a different embedder provider (openai, voyage, azure_openai, ollama). "
        "Anthropic recommends Voyage AI: https://docs.anthropic.com/en/docs/build-with-claude/embeddings"
    ),
    "missing_api_key": (
        "Missing API key for {provider}. "
        "Set {env_var} in your environment or .env file."
    ),
    "ollama_not_running": (
        "Cannot connect to Ollama at {url}. "
        "Ensure Ollama is running: ollama serve"
    ),
    "azure_missing_deployment": (
        "Azure OpenAI requires deployment names. "
        "Set AZURE_OPENAI_LLM_DEPLOYMENT and AZURE_OPENAI_EMBEDDING_DEPLOYMENT."
    ),
}
```



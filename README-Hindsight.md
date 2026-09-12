# Hindsight Configuration

### Overview

Hindsight requires three configurable components to operate:

1. An LLM to synthesise the storage values from your Hermes chat, although a frontier model and large context are not usually necessary.
2. An embeddings model to convert between text and numerical values (the maximum dimensionality is 2000 unless using a non-standard vector database backend).
3. (Optional) A reranker model to increase retrieval accuracy and lower token usage for the main (Hermes Agent) LLM.

Using the tool `/hindsight-retain` uses 1 and 2, while `/hindsight-recall` uses 2 and 3.


### Scenario 1: Cloud-only

For best performance use a remote cloud API (Google Gemini shown, but many other provider configurations are available to use), although this will have the highest ongoing costs:

* LLM provider and embeddings provider can be different.
* The LLM is able to be changed at any time, but the embeddings model must not be changed once the vector database has been created.
* `HINDSIGHT_API_ENABLE_RERANKING=false` seems to be ignored, so to disable (increasing the load on the Hermes LLM model configured elsewhere) use an invalid API key.

```
HINDSIGHT_API_LLM_PROVIDER=gemini
HINDSIGHT_API_LLM_MODEL=gemini-3.5-flash-lite
HINDSIGHT_API_LLM_API_KEY=your-google-cloud-api-key

HINDSIGHT_API_EMBEDDINGS_PROVIDER=google
HINDSIGHT_API_EMBEDDINGS_GEMINI_MODEL=gemini-embedding-001
HINDSIGHT_API_EMBEDDINGS_GEMINI_API_KEY=your-google-cloud-api-key
HINDSIGHT_API_EMBEDDINGS_GEMINI_OUTPUT_DIMENSIONALITY=1536

HINDSIGHT_API_ENABLE_RERANKING=false
HINDSIGHT_API_RERANKER_PROVIDER=cohere
HINDSIGHT_API_RERANKER_COHERE_API_KEY=optional-use-your-cohere-api-key-to-enable
```

### Scenario 2: Local-only

By default, Hindsight uses its own embeddings and reranker models, both of which it attempts to download if not in the cache (configured as volume `hermes-cache`). A local LLM such as Ollama used to store facts in the memory, and can be installed on the same machine and running on the default port.

* Ollama is accessible **from inside the container** as `http://host.docker.internal:11434/v1` (not `http://localhost...`).
* The usage of `*_FORCE_CPU=true` is necessary for some ARM/Apple Silicon-based devices
* Use of larger models such as `BAAI/bge-m3` and `BAAI/bge-reranker-v2-m3` may require manual starting of the container and providing a suitably longer timeout for the download.
* Use `ollama pull [modelname]` in the host before starting the Hindsight container for the first time.

```
HINDSIGHT_API_LLM_PROVIDER=ollama
HINDSIGHT_API_LLM_BASE_URL=http://host.docker.internal:11434/v1
HINDSIGHT_API_LLM_MODEL=llama3.1:8b
HINDSIGHT_API_LLM_OLLAMA_NUM_CTX=16384

HINDSIGHT_API_EMBEDDINGS_PROVIDER=local
HINDSIGHT_API_EMBEDDINGS_LOCAL_MODEL=BAAI/bge-small-en-v1.5
HINDSIGHT_API_EMBEDDINGS_LOCAL_FORCE_CPU=false

HINDSIGHT_API_RERANKER_PROVIDER=local
HINDSIGHT_API_RERANKER_LOCAL_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
HINDSIGHT_API_RERANKER_LOCAL_FORCE_CPU=false
```

### Scenario 3: Custom endpoint (Docker Model Runner)

Some users may want to control everything through Docker Desktop and this is also possible. The configuration below is tested and runs within 8GB VRAM (or on CPU) and does not use bf16 so older graphics cards should be usable.

* Models `granite-4.0-h-tiny` and `nomic-embed-text-v2-moe` can be downloaded from the Docker Hub, however `docker model pull huggingface.co/pyarn/bge-reranker-v2-m3-Q8_0-GGUF:Q8_0` is the only way to download the reranker (or specify some other reranker model if desired).
* The provider and base URL are slightly different for the reranker, although no special configuration of Docker Model Runner is required.
* Use of `HINDSIGHT_API_LLM_MAX_CONCURRENT=1` ensures that the facts from the Hermes chat are processed sequentially, but likely as quickly (or faster) that attempting to process them concurrently. (There may be a delay before they are available to `/hindsight-recall`.)

```
HINDSIGHT_API_LLM_PROVIDER=openai
HINDSIGHT_API_LLM_BASE_URL=http://model-runner.docker.internal/v1
HINDSIGHT_API_LLM_MODEL=granite-4.0-h-tiny
HINDSIGHT_API_LLM_API_KEY=None
HINDSIGHT_API_LLM_MAX_CONCURRENT=1

HINDSIGHT_API_EMBEDDINGS_PROVIDER=openai
HINDSIGHT_API_EMBEDDINGS_OPENAI_BASE_URL=http://model-runner.docker.internal/v1
HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL=nomic-embed-text-v2-moe
HINDSIGHT_API_EMBEDDINGS_OPENAI_API_KEY=None
HINDSIGHT_API_EMBEDDINGS_MAX_RETRIES=0

HINDSIGHT_API_RERANKER_PROVIDER=openrouter
HINDSIGHT_API_RERANKER_OPENROUTER_BASE_URL=http://model-runner.docker.internal/rerank
HINDSIGHT_API_RERANKER_OPENROUTER_MODEL=huggingface.co/pyarn/bge-reranker-v2-m3-Q8_0-GGUF:Q8_0
HINDSIGHT_API_RERANKER_OPENROUTER_API_KEY=None
```

Note: To configure these models before use (ideally before starting the Hindsight container) run the following commands (context sizes are chosen to be optimal for this application):

```batch
docker model configure --context-size 16384 --keep-alive 30m granite-4.0-h-tiny
docker model configure --context-size 512 --keep-alive 30m --mode embedding nomic-embed-text-v2-moe
docker model configure --context-size 514 --keep-alive 30m huggingface.co/pyarn/bge-reranker-v2-m3-Q8_0-GGUF:Q8_0 -- --flash-attn on --n-gpu-layers 99
```
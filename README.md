# Hermes on Docker with MCP and agentic memory

The Hermes Agent is able to be run on many platforms and this repository is an attempt to sanitize its installation, use and future upgrades by hosting it on Docker Desktop (or Docker CLI).

### Installation (Windows)

Clone the repo and navigate using PowerShell or Command Window (shown) to its directory. Create necessary directories for launch:

```plaintext
cd \path\to\hermes-brain
mkdir dummy-secrets-cache
mkdir %USERPROFILE%\Documents\Workspace
```

(These directories are used by the MCP server and Hermes WebUI, respectively.)

### Installation (Linux terminal)

Clone the repo and navigate using a terminal to its directory. Create necessary directories for launch:

```bash
cd /path/to/hermes-brain
mkdir dummy-secrets-cache ~/Workspace
```

(These directories are used by the MCP server and Hermes WebUI, respectively.)

### Usage

Inspect the `.env` file which should allow loading with default settings, to enable the Hindsight memory server it is necessary to provide at least:

```bash
HERMES_USE_HINDSIGHT=true
HINDSIGHT_API_EMBEDDINGS_OPENAI_MODEL=your-Docker-hosted-embeddings
HINDSIGHT_API_LLM_MODEL=your-Docker-hosted-model # MUST have context window size above 64000
```

Then decide on any, all or none from the profiles `webui`, `dashboard`, `mcp` and `memory` (or use `--profile all` instead of multiple `--profile ...`), such as:

```bash
docker compose -f docker-compose.windows.yml --profile webui --profile mcp up -d
```

(or under Linux)

```bash
docker compose --profile all up -d
```

Note that `-f` selects a filename other than the default (docker-compose.yml), while `-d` indicates the process runs in the background after loading.

After several minutes of pulling the dependencies of the containers and sinitializing them, the `preconfigure.py` script should run successfully and allow all of them to start. The above command must be repeated for any changes to `.env` (or the compose script itself).

### Upgrades

To upgrade the whole setup, it is necessary to remove the `hermes-agent-src` volume entirely (don't remove the others as they contain your session history and memory).

```bash
# Omit [-f ...] from both docker compose commands for Linux
docker compose -f docker-compose.windows.yml --profile all down
docker volume rm hermes-brain_hermes-agent-src
docker compose -f docker-compose.windows.yml --profile all pull
```

Then run the same `docker compose` command as previously to rebuild the containers.

### Issues

There are many known issues with these scripts. You will need to be able to navigate the Docker Desktop interface (including files, logs and exec shell) in order to investigate and fix them.

1. Permissions: Sometimes large parts of `hermes-home` becomes user `10000` instead of `hermes` (1000). To fix this without deleting the volume go to Exec under container `hermes-agent` and execute (as root user) `chown -R hermes:hermes /home/hermes/.hermes`

2. Memory: The `preconfigure.py` script tries to take the initial configuration pain out of this combination of containers, however it is incomplete in setting up the Hindsight memory server. It is necessary to use the `dashboard` "Plugins" tab (on port 9119 by default) to set the use of Hindsight.

3. General configuration: To reconfigure manually, it is necessary to perform the following in the Exec tab of the `hermes-agent` container:

```bash
su hermes # Important, or files get root permissions
hermes [command] [options...]
```

4. To use Gemini embeddings (3072 dimensions), it is necessary to make changes to the Hindsight container part of the compose script.

5. An internet connection is necessary for the Docker MCP service to load.

6. The amount of allocated memory and CPU capacity is guesswork at the moment, look out for OOM errors.

7. Loads more... please raise issues.

### Credits

These scripts are based upon the following resources:

https://github.com/nesquena/hermes-webui/blob/master/docker-compose.three-container.yml

https://github.com/vectorize-io/hindsight/blob/main/docker/docker-compose/local-llm/docker-compose.yaml

Any bugs introduced are most likely the fault of myself, refer to these two for detailed comments and explanations.

The software is alpha-quality at present; please raise issues and submit PRs in case of suggestions for improvement.

### License

This is free software released under the MIT license (as for the Hermes-related portions of its dependencies).

### Release History

**2026/08/25**: Initial release of 1.0-alpha

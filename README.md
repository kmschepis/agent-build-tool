# Agent Build Tool (ABT)

ABT is a developer tool that treats agentic prompts, skills, and tools as modular code. It separates the **definition of an agent** (the source) from the **execution** (the runtime).

* **Source**: Markdown files with Jinja templating.
* **Build**: A compilation step that resolves dependencies and validates schemas.
* **Artifact**: A single, portable JSON manifest used by applications.

## Core Components

### The Agent Model (`agents/`)
The primary unit of work. Each `.md` file represents a unique agent identity.

* **Frontmatter (YAML)**: Defines metadata (name, model provider, temperature).
* **Body (Markdown)**: The system prompt, using `{{ ref() }}` to pull in context.

### The Skill Standard (`skills/`)
Aligns with the `SKILL.md` standard. Each folder contains:

* **SKILL.md**: Detailed procedural instructions for the agent.
* **Metadata**: Descriptions that tell the parent agent when to invoke this skill.

### The Tool & MCP Interface (`tools/`)
Declarative definitions of external capabilities.

* **MCP Servers**: Configuration for local or remote Model Context Protocol servers.
* **Native Tools**: JSON Schema definitions for custom application functions.

### Macros & Global Context (`macros/`)
Reusable snippets for common patterns (e.g., formatting output as JSON, chain-of-thought guardrails, or brand voice).

## The ABT Lifecycle

1. **Develop**
   Developers write modular prompts in a structured directory. Instead of copy-pasting a "Refund Policy" into ten different agent prompts, they reference it once.

2. **Compile (`abt compile`)**
   The compiler traverses the project and:

   * **Resolves Graph**: Maps which agents depend on which skills/macros.
   * **Jinja Rendering**: Flattens all templates into pure strings.
   * **Validation**: Checks for broken references or prompts that exceed context window limits.

3. **Deploy**
   The output is an `abt_manifest.json`. This artifact is stored in Git or uploaded to a registry (like a S3 bucket or GitHub Release).

## Example: Build a Tiny Agent Library

The example below shows how a minimal ABT project is structured, how references are wired together, and what the build produces.

### 1) Scaffold the project

```bash
abt init my-abt-project
cd my-abt-project
```

Expected structure:

```
my-abt-project/
  agents/
    support_agent.md
  skills/
    refund_policy/
      SKILL.md
  tools/
    mcp_servers.yaml
  macros/
    output_json.md
```

### 2) Define a macro

`macros/output_json.md`

```markdown
Return responses in JSON with keys: "answer" and "next_step".
```

### 3) Define a skill

`skills/refund_policy/SKILL.md`

```markdown
If the user requests a refund, provide the official policy:
We offer refunds within 30 days of purchase with proof of receipt.
```

### 4) Define an agent

`agents/support_agent.md`

```markdown
---
name: support_agent
model_provider: openai
temperature: 0.2
---

You are the support agent. Use the refund policy when asked about refunds.

{{ ref("skills/refund_policy") }}

{{ ref("macros/output_json") }}
```

### 5) Compile

```bash
abt compile
```

### 6) Inspect the artifact

The compiler emits a single manifest:

```
abt_manifest.json
```

Minimalized example payload:

```json
{
  "agents": {
    "support_agent": {
      "model_provider": "openai",
      "temperature": 0.2,
      "system_prompt": "You are the support agent...We offer refunds within 30 days...Return responses in JSON..."
    }
  }
}
```

## Examples

A ready-to-run sample project lives in `examples/basic`. You can compile it directly:

```bash
cd examples/basic
python -m abt compile --output abt_manifest.json
```

## Testing

Install dependencies and run the unit tests with the standard library test runner:

```bash
pip install -e .
python -m unittest discover -s tests
```

## Interaction Patterns

### The Developer (CLI)
Developers interact with ABT through a terminal, similar to `git` or `dbt`.

* `abt init`: Scaffolds the directory structure.
* `abt docs`: Generates a local web view showing the "lineage" of how prompts and tools are connected.

### The Application (Runtime)
The host application (your chat app) does not "know" about ABT files. It only knows about the manifest.

* **Initialization**: App loads the `manifest.json`.
* **Execution**: When a user initiates a chat, the app looks up the `support_agent` in the manifest and sends the pre-compiled `system_prompt` to the LLM.
* **Discovery**: The app uses the tool definitions in the manifest to register MCP clients automatically.

### The Agent-to-Agent Interaction
Agents can "call" other agents defined in the ABT project. The manifest provides the routing logic for multi-agent handoffs.

## Key Differentiators

* **DRY (Don’t Repeat Yourself)**: Centralize instructions. Update a macro once; update 100 agents.
* **Environment Agnostic**: The same `billing_agent` works in a CLI, a React app, or a Python backend because the "Logic" is decoupled from the "App Code."
* **Observability**: Visualize the relationship between prompts and MCP tools before they are deployed.

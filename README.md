# Codex Skills

Public Codex skill definitions and helper scripts.

## Included Skills

- `ai-paper-en`: English academic paper and thesis revision for AI systems, chips, compilers, computer architecture, and systems work.
- `ai-paper-zh`: Chinese academic paper and thesis revision for AI systems, chips, compilers, computer architecture, and systems work.
- `image2-router`: OpenAI-compatible image generation and editing router for several configurable providers.
- `operator-development`: pymodel operator development and modification workflow for LPU/NPU/AI accelerator projects, including computation graph confirmation, tile/buffer planning, task bin generation, set-wait/fence insertion, cmodel replay, and RTL/UVM debug.
- `xwave`: Hardware waveform debugging workflow for xwave-supported traces, AXI/APB hangs, RTL correlation, and debug reports.

## Repository Layout

```text
skills/
  ai-paper-en/
  ai-paper-zh/
  image2-router/
  operator-development/
  xwave/
```

Each skill directory is self-contained and includes its own `SKILL.md`. Some skills also include helper scripts, tests, references, or agent metadata.

## Security Notes

- API keys are not stored in this repository.
- Local `.env` files, generated caches, Python bytecode, and generated outputs are ignored.
- `image2-router` reads keys from environment variables or from a local `~/.codex/image2-router.env` file at runtime.
- The public `image2-router` version does not hard-code a private `riclab` endpoint. Set `RICLAB_BASE_URL` or pass `--base-url` when using that provider.

## Validation

Run the bundled image router tests with:

```bash
python -m unittest discover -s skills/image2-router/tests
```

Run a syntax check for the image router script with:

```bash
python -m py_compile skills/image2-router/scripts/image2_router.py
```

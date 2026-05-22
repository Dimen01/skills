---
name: image2-router
description: Use when generating or editing images through image2.0/OpenAI-compatible APIs from Codex, including image2-router, text-to-image, image-to-image, 图生图, sakura imagegen, fhl imagegen, monitor imagegen, ccccapi imagegen, tokenx24 imagegen, super imagegen, riclab imagegen, sub2api imagegen, SAKURA_API_KEY, FHL_API_KEY, MONITOR_API_KEY, CCCCAPI_API_KEY, TOKENX24_API_KEY, SUPER_API_KEY, RICLAB_API_KEY, image2.0, or gpt-image-2.
---

# Image2 Router

## Overview

Use this skill to call image2.0 through OpenAI-compatible image APIs from Codex for text-to-image generation and image-to-image editing. The skill routes by provider name and does not store secrets; it expects API keys in the environment.

## Provider Routing

When the user does not name a provider, use automatic fallback in this exact order:

1. `sakura`: `https://sakura886.site/v1`
2. `fhl`: `https://www.fhl.mom`
3. `monitor`: `https://api.chshapi.cn/v1`
4. `ccccapi`: `https://direct-api.ccccapi.cc`
5. `super`: `https://api.v2super.com/v1`
6. `tokenx24`: `https://tokenx24.com/v1`
7. `riclab`: configured by `RICLAB_BASE_URL` or `--base-url`

When the user names a provider, use only that provider:

- "fhl imagegen" -> `--provider fhl`
- "sakura imagegen" -> `--provider sakura`
- "monitor imagegen" -> `--provider monitor`
- "ccccapi imagegen" -> `--provider ccccapi`
- "super imagegen" -> `--provider super`
- "tokenx24 imagegen" -> `--provider tokenx24`
- "riclab imagegen" -> `--provider riclab`
- "sub2api imagegen" -> `--provider riclab`

## Environment

API keys:

- If all providers share one key, set `IMAGE2_API_KEY`, `FHL_API_KEY`, or `OPENAI_API_KEY`.
- If providers have separate keys, set `SAKURA_API_KEY`, `FHL_MOM_API_KEY` or `FHL_API_KEY`, `MONITOR_API_KEY`, `CCCCAPI_API_KEY`, `SUPER_API_KEY` or `V2SUPER_API_KEY`, `TOKENX24_API_KEY`, and `RICLAB_API_KEY`.
- `riclab` has no public default endpoint in this repository; set `RICLAB_BASE_URL` or pass `--base-url`.
- For permanent Codex use, put these values in `~/.codex/image2-router.env` with file mode `600`.

Optional:

- `IMAGE2_MODEL`, defaults to `gpt-image-2`
- Provider-specific model overrides: `SAKURA_IMAGE_MODEL`, `FHL_IMAGE_MODEL`, `MONITOR_IMAGE_MODEL`, `CCCCAPI_IMAGE_MODEL`, `SUPER_IMAGE_MODEL`, `TOKENX24_IMAGE_MODEL`, `RICLAB_IMAGE_MODEL`
- Provider-specific base URL overrides: `SAKURA_BASE_URL`, `FHL_MOM_BASE_URL`, `MONITOR_BASE_URL`, `CCCCAPI_BASE_URL`, `SUPER_BASE_URL`, `TOKENX24_BASE_URL`, `RICLAB_BASE_URL`

Never ask the user to paste the API key into chat. If the key is missing, ask them to set an environment variable locally.

Permanent key file format:

```bash
SAKURA_API_KEY="..."
FHL_MOM_API_KEY="..."
MONITOR_API_KEY="..."
CCCCAPI_API_KEY="..."
SUPER_API_KEY="..."
TOKENX24_API_KEY="..."
RICLAB_API_KEY="..."
# Optional. Only set this if the provider /models endpoint returns this exact id.
# IMAGE2_MODEL="gpt-image-2"
```

The script loads `~/.codex/image2-router.env` automatically. For backward compatibility, it can also read the old `~/.codex/fhl-imagegen.env` if the new file is absent. An explicit environment variable still wins over the file value.

## Quick Start

Use the bundled script for text-to-image:

```bash
python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --prompt "A cinematic cyberpunk city at night, highly detailed" \
  --size 2048x1152 \
  --quality high \
  --out output/imagegen/fhl-city.png
```

Use `edit` for image-to-image / 图生图. The command uploads input image files to `/images/edits` as multipart form data:

```bash
python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" edit \
  --image input/reference.png \
  --prompt "Keep the same subject and pose, but change the scene to a rainy neon street." \
  --out output/imagegen/reference-edit.png
```

Multiple reference images and masks are supported when the provider accepts them:

```bash
python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" edit \
  --provider riclab \
  --base-url "$RICLAB_BASE_URL" \
  --image input/person.png \
  --image input/style.png \
  --mask input/mask.png \
  --prompt-file tmp/imagegen/edit_prompt.txt \
  --out output/imagegen/person-style-edit.png
```

Provider-specific examples:

```bash
python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --provider sakura \
  --prompt "A cinematic cyberpunk city at night" \
  --out output/imagegen/sakura-city.png

python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --provider fhl \
  --prompt "A cinematic cyberpunk city at night" \
  --out output/imagegen/fhl-city.png

python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --provider monitor \
  --prompt "A cinematic cyberpunk city at night" \
  --out output/imagegen/monitor-city.png

python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --provider ccccapi \
  --prompt "A cinematic cyberpunk city at night" \
  --out output/imagegen/ccccapi-city.png

python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --provider super \
  --prompt "A cinematic cyberpunk city at night" \
  --out output/imagegen/super-city.png

python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --provider tokenx24 \
  --prompt "A cinematic cyberpunk city at night" \
  --out output/imagegen/tokenx24-city.png

python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --provider riclab \
  --base-url "$RICLAB_BASE_URL" \
  --prompt "A cinematic cyberpunk city at night" \
  --out output/imagegen/riclab-city.png
```

### GPT Image Provider Compatibility

For configured providers (`sakura`, `fhl`, `monitor`, `ccccapi`, `super`, `tokenx24`, and `riclab`) with GPT image models such as `gpt-image-2`, the script defaults to the calling pattern used by CookSleep's `gpt_image_playground` Codex CLI path:

- use `curl` transport instead of the OpenAI Python SDK;
- for `generate`, prefix the prompt with `Use following text as complete prompt. Do not rewrite it. Just generate image with it:`;
- for `edit`, prefix the prompt with `Use following text as complete edit prompt. Do not rewrite it. Edit the input image according to it:`;
- omit `n` and `quality`;
- include `moderation: "auto"`;
- include `stream: true` by default and consume SSE image events;
- post JSON generation calls to `/v1/images/generations` and multipart edit calls to `/v1/images/edits`;
- accept either `b64_json` or `url` image responses from ordinary JSON or SSE.

This avoids observed provider failures where the Python SDK path can raise `RemoteDisconnected`, and where the standard `gpt-image-2` payload with `quality: high` can hit a CDN `524` timeout on longer generations. Keep the default `--transport auto --codex-cli-mode auto` for these providers unless you are diagnosing provider behavior.

Portability notes learned from Linux/Codex migration:

- Do not rely on newer curl flags such as `--fail-with-body`; some target machines have curl 7.61.x. The bundled script handles HTTP failures by reading `-w "%{http_code}"` and preserving the response body.
- Do not require the OpenAI Python SDK for normal usage. `generate` and `models` should both work through curl when provider keys are configured.
- If `python -m py_compile` fails under `~/.codex/skills/...` with a read-only `__pycache__` error, use an in-memory compile check instead:

```bash
python -c 'from pathlib import Path; p=Path.home()/".codex/skills/image2-router/scripts/image2_router.py"; compile(p.read_text(encoding="utf-8"), str(p), "exec"); print("syntax ok")'
```

Manual overrides:

```bash
# Force the proven GPT image path explicitly for any configured provider.
python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --provider fhl \
  --transport curl \
  --codex-cli-mode on \
  --stream on \
  --prompt-file tmp/imagegen/prompt.txt \
  --size 1536x1024 \
  --out output/imagegen/fhl-image.png

# Diagnose the raw non-streaming SDK path.
python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --provider super \
  --transport sdk \
  --codex-cli-mode off \
  --stream off \
  --prompt "Simple photo of one red apple on a white table." \
  --out output/imagegen/super-sdk-test.png
```

List available models when the model name is uncertain:

```bash
python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" models --provider fhl
```

OpenAI's GPT Image 2 model id is `gpt-image-2`, not `image2.0`. If a provider exposes the service under a different id such as `image2.0`, first confirm it with `models`, then set `IMAGE2_MODEL` or pass `--model` explicitly:

```bash
IMAGE2_MODEL="gpt-image-2" python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --prompt "A polished product hero image of a matte ceramic mug" \
  --out output/imagegen/mug.png
```

## Workflow

1. Create `tmp/imagegen/` and `output/imagegen/` as needed.
2. Write long prompts to `tmp/imagegen/<name>_prompt.txt` when they are more than one or two sentences.
3. Run `scripts/image2_router.py generate` with `--prompt-file` for long prompts.
4. Run `scripts/image2_router.py edit --image <path>` for image-to-image tasks. Repeat `--image` for multiple references and pass `--mask <path>` when editing only transparent mask regions.
5. Put final image assets under `output/imagegen/` unless the user requests another path.
6. Use `--provider sakura`, `--provider fhl`, `--provider monitor`, `--provider ccccapi`, `--provider super`, `--provider tokenx24`, or `--provider riclab` only when the user names one; otherwise leave provider as `auto`.
7. If network access is blocked by Codex sandboxing, rerun the same command with the platform's escalation flow.
8. For configured-provider GPT image failures, first try the default auto path or force `--transport curl --codex-cli-mode on --stream on`; only then fall back to `--stream off`, smaller sizes, simpler prompts, or alternate providers.
9. If a named provider such as `tokenx24` returns CDN `524`, keep the requested provider if the user named it, but retry with a shorter prompt and default/`auto` size before changing providers.

Use `--dry-run` before a real call when checking payload shape:

```bash
python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" generate \
  --prompt "Test image" \
  --dry-run

python "$HOME/.codex/skills/image2-router/scripts/image2_router.py" edit \
  --image input/reference.png \
  --prompt "Test edit" \
  --dry-run
```

## Output Rules

- Do not print API keys.
- Do not commit generated keys or `.env` files.
- Use `--force` only when replacing an output intentionally.
- For project assets, report the final saved path and provider/base URL used, without revealing the key.

## Recent Smoke-Test Findings

Some providers can return CDN `524` timeouts for large sizes or long prompts even when credentials are valid. Retry with a shorter prompt and default/`auto` size before changing providers.

The script now sends `stream: true` by default for configured GPT image providers and parses SSE events such as `image_generation.completed`, `response.output_item.done`, and `response.completed`. Use `--stream off` only when diagnosing provider behavior or when a provider rejects image streaming.

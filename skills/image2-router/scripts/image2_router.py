#!/usr/bin/env python3
"""image2.0 provider router for OpenAI-compatible image generation in Codex."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Any
from urllib.request import Request, urlopen

PROVIDERS: dict[str, dict[str, Any]] = {
    "sakura": {
        "base_url": "https://sakura886.site/v1",
        "base_url_env": ("SAKURA_BASE_URL",),
        "api_key_env": ("SAKURA_API_KEY", "IMAGE2_API_KEY", "FHL_API_KEY", "OPENAI_API_KEY"),
        "model_env": ("SAKURA_IMAGE_MODEL", "IMAGE2_MODEL"),
    },
    "fhl": {
        "base_url": "https://www.fhl.mom",
        "base_url_env": ("FHL_MOM_BASE_URL",),
        "api_key_env": ("FHL_MOM_API_KEY", "FHL_API_KEY", "IMAGE2_API_KEY", "OPENAI_API_KEY"),
        "model_env": ("FHL_MOM_IMAGE_MODEL", "FHL_IMAGE_MODEL", "IMAGE2_MODEL"),
    },
    "monitor": {
        "base_url": "https://api.chshapi.cn/v1",
        "base_url_env": ("MONITOR_BASE_URL",),
        "api_key_env": ("MONITOR_API_KEY", "IMAGE2_API_KEY", "FHL_API_KEY", "OPENAI_API_KEY"),
        "model_env": ("MONITOR_IMAGE_MODEL", "IMAGE2_MODEL"),
    },
    "ccccapi": {
        "base_url": "https://direct-api.ccccapi.cc",
        "base_url_env": ("CCCCAPI_BASE_URL",),
        "api_key_env": ("CCCCAPI_API_KEY", "IMAGE2_API_KEY", "FHL_API_KEY", "OPENAI_API_KEY"),
        "model_env": ("CCCCAPI_IMAGE_MODEL", "IMAGE2_MODEL"),
    },
    "super": {
        "base_url": "https://api.v2super.com/v1",
        "base_url_env": ("SUPER_BASE_URL", "V2SUPER_BASE_URL"),
        "api_key_env": ("SUPER_API_KEY", "V2SUPER_API_KEY", "IMAGE2_API_KEY", "FHL_API_KEY", "OPENAI_API_KEY"),
        "model_env": ("SUPER_IMAGE_MODEL", "V2SUPER_IMAGE_MODEL", "IMAGE2_MODEL"),
    },
    "tokenx24": {
        "base_url": "https://tokenx24.com/v1",
        "base_url_env": ("TOKENX24_BASE_URL",),
        "api_key_env": ("TOKENX24_API_KEY", "IMAGE2_API_KEY", "FHL_API_KEY", "OPENAI_API_KEY"),
        "model_env": ("TOKENX24_IMAGE_MODEL", "IMAGE2_MODEL"),
    },
    "riclab": {
        "base_url": None,
        "base_url_env": ("RICLAB_BASE_URL",),
        "api_key_env": ("RICLAB_API_KEY", "IMAGE2_API_KEY", "FHL_API_KEY", "OPENAI_API_KEY"),
        "model_env": ("RICLAB_IMAGE_MODEL", "IMAGE2_MODEL"),
    },
}
DEFAULT_PROVIDER_ORDER = ("sakura", "fhl", "monitor", "ccccapi", "super", "tokenx24", "riclab")
PROVIDER_ALIASES = {
    "auto": "auto",
    "sakura": "sakura",
    "fhl": "fhl",
    "fhl-mom": "fhl",
    "mom": "fhl",
    "monitor": "monitor",
    "ccccapi": "ccccapi",
    "super": "super",
    "v2super": "super",
    "token": "tokenx24",
    "tokenx24": "tokenx24",
    "riclab": "riclab",
    "sub2": "riclab",
    "sub2api": "riclab",
}
DEFAULT_MODEL = "gpt-image-2"
DEFAULT_SIZE = "auto"
DEFAULT_QUALITY = "high"
DEFAULT_OUTPUT_FORMAT = "png"
DEFAULT_OUT = "output/imagegen/fhl-image.png"
DEFAULT_ENV_FILE = Path.home() / ".codex" / "image2-router.env"
LEGACY_ENV_FILE = Path.home() / ".codex" / "fhl-imagegen.env"
CODEX_PROMPT_PREFIX = (
    "Use following text as complete prompt. Do not rewrite it. "
    "Just generate image with it:"
)
CODEX_EDIT_PROMPT_PREFIX = (
    "Use following text as complete edit prompt. Do not rewrite it. "
    "Edit the input image according to it:"
)


def die(message: str, code: int = 1) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def load_env_file() -> None:
    raw_path = os.getenv("IMAGE2_ROUTER_ENV_FILE") or os.getenv("FHL_IMAGEGEN_ENV_FILE")
    if raw_path:
        path = Path(raw_path).expanduser()
    elif DEFAULT_ENV_FILE.exists():
        path = DEFAULT_ENV_FILE
    else:
        path = LEGACY_ENV_FILE
    if not path.exists():
        return

    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            print(f"Warning: ignoring invalid env line {line_no} in {path}", file=sys.stderr)
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            print(f"Warning: ignoring empty env key on line {line_no} in {path}", file=sys.stderr)
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def env_value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    return value if value else default


def first_env(names: tuple[str, ...]) -> str | None:
    for name in names:
        value = env_value(name)
        if value:
            return value
    return None


def normalize_provider(provider: str) -> str:
    normalized = PROVIDER_ALIASES.get(provider.strip().lower())
    if not normalized:
        allowed = ", ".join(sorted(PROVIDER_ALIASES))
        die(f"Unknown provider: {provider}. Use one of: {allowed}.")
    return normalized


def provider_base_url(provider: str) -> str | None:
    data = PROVIDERS[provider]
    return first_env(data["base_url_env"]) or data["base_url"]


def provider_model(provider: str, explicit_model: str | None) -> str:
    if explicit_model:
        return explicit_model
    return first_env(PROVIDERS[provider]["model_env"]) or DEFAULT_MODEL


def api_key(provider: str) -> str | None:
    value = first_env(PROVIDERS[provider]["api_key_env"])
    return value


def custom_api_key() -> str | None:
    return first_env(
        (
            "SAKURA_API_KEY",
            "FHL_MOM_API_KEY",
            "MONITOR_API_KEY",
            "CCCCAPI_API_KEY",
            "SUPER_API_KEY",
            "V2SUPER_API_KEY",
            "TOKENX24_API_KEY",
            "RICLAB_API_KEY",
            "IMAGE2_API_KEY",
            "FHL_API_KEY",
            "OPENAI_API_KEY",
        )
    )


def read_prompt(args: argparse.Namespace) -> str:
    if args.prompt and args.prompt_file:
        die("Use --prompt or --prompt-file, not both.")
    if args.prompt_file:
        path = Path(args.prompt_file)
        if not path.exists():
            die(f"Prompt file not found: {path}")
        prompt = path.read_text(encoding="utf-8").strip()
    elif args.prompt:
        prompt = args.prompt.strip()
    else:
        die("Missing prompt. Use --prompt or --prompt-file.")
    if not prompt:
        die("Prompt is empty.")
    return prompt


def validate_image_paths(args: argparse.Namespace) -> list[Path]:
    paths = [Path(path).expanduser() for path in args.image]
    if not paths:
        die("Missing input image. Use --image PATH at least once.")
    for path in paths:
        if not path.exists():
            die(f"Input image not found: {path}")
        if not path.is_file():
            die(f"Input image is not a file: {path}")
    return paths


def validate_mask_path(mask: str | None) -> Path | None:
    if not mask:
        return None
    path = Path(mask).expanduser()
    if not path.exists():
        die(f"Mask image not found: {path}")
    if not path.is_file():
        die(f"Mask image is not a file: {path}")
    return path


def output_paths(out: str, output_format: str, count: int) -> list[Path]:
    path = Path(out)
    suffix = "." + output_format
    if path.suffix == "":
        path = path.with_suffix(suffix)
    if count == 1:
        return [path]
    return [path.with_name(f"{path.stem}-{idx}{path.suffix}") for idx in range(1, count + 1)]


def serializable(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    if isinstance(obj, list):
        return [serializable(item) for item in obj]
    if isinstance(obj, dict):
        return {key: serializable(value) for key, value in obj.items()}
    return obj


def get_attr(item: Any, name: str) -> Any:
    if isinstance(item, dict):
        return item.get(name)
    return getattr(item, name, None)


def create_client(key: str, base_url: str) -> Any:
    try:
        from openai import OpenAI
    except ImportError:
        die("The openai package is not installed in this Python environment.")
    return OpenAI(api_key=key, base_url=base_url)


def should_use_codex_mode(args: argparse.Namespace, provider: str, model: str) -> bool:
    mode = args.codex_cli_mode
    if mode == "on":
        return True
    if mode == "off":
        return False
    return provider in PROVIDERS and model.startswith("gpt-image-")


def should_use_curl(args: argparse.Namespace, provider: str, model: str) -> bool:
    if args.transport == "curl":
        return True
    if args.transport == "sdk":
        return False
    return provider in PROVIDERS and model.startswith("gpt-image-")


def should_stream_images(args: argparse.Namespace, provider: str, model: str) -> bool:
    mode = getattr(args, "stream", "auto")
    if mode == "on":
        return True
    if mode == "off":
        return False
    return provider in PROVIDERS and model.startswith("gpt-image-")


def target_providers(args: argparse.Namespace) -> list[dict[str, str]]:
    provider = normalize_provider(args.provider)
    explicit_model = getattr(args, "model", None)
    if args.base_url:
        model = explicit_model or env_value("IMAGE2_MODEL", DEFAULT_MODEL)
        return [{"provider": "custom", "base_url": args.base_url, "model": model}]
    names = list(DEFAULT_PROVIDER_ORDER) if provider == "auto" else [provider]
    targets: list[dict[str, str]] = []
    for name in names:
        base_url = provider_base_url(name)
        if not base_url:
            if provider == "auto":
                continue
            die(f"Provider {name} requires {PROVIDERS[name]['base_url_env'][0]} or --base-url.")
        targets.append(
            {
                "provider": name,
                "base_url": base_url,
                "model": provider_model(name, explicit_model),
            }
        )
    return targets


def build_image_payload(args: argparse.Namespace, provider: str, model: str, prompt: str) -> dict[str, Any]:
    effective_prompt = prompt
    use_codex_mode = should_use_codex_mode(args, provider, model)
    if use_codex_mode:
        effective_prompt = f"{CODEX_PROMPT_PREFIX}\n\n{prompt}"

    payload: dict[str, Any] = {
        "model": model,
        "prompt": effective_prompt,
        "size": args.size,
    }
    if should_stream_images(args, provider, model):
        payload["stream"] = True
    if not use_codex_mode:
        payload["n"] = args.n
        payload["quality"] = args.quality
    if args.response_format:
        payload["response_format"] = args.response_format
    else:
        payload["output_format"] = args.output_format
    if args.background:
        payload["background"] = args.background
    if args.output_compression is not None:
        payload["output_compression"] = args.output_compression
    if args.moderation or use_codex_mode:
        payload["moderation"] = args.moderation or "auto"
    elif args.moderation:
        payload["moderation"] = args.moderation
    return payload


def build_image_edit_fields(args: argparse.Namespace, provider: str, model: str, prompt: str) -> dict[str, Any]:
    effective_prompt = prompt
    use_codex_mode = should_use_codex_mode(args, provider, model)
    if use_codex_mode:
        effective_prompt = f"{CODEX_EDIT_PROMPT_PREFIX}\n\n{prompt}"

    fields: dict[str, Any] = {
        "model": model,
        "prompt": effective_prompt,
        "size": args.size,
    }
    if should_stream_images(args, provider, model):
        fields["stream"] = True
    if not use_codex_mode:
        fields["n"] = args.n
        fields["quality"] = args.quality
    if args.response_format:
        fields["response_format"] = args.response_format
    else:
        fields["output_format"] = args.output_format
    if args.background:
        fields["background"] = args.background
    if args.output_compression is not None:
        fields["output_compression"] = args.output_compression
    if args.moderation or use_codex_mode:
        fields["moderation"] = args.moderation or "auto"
    elif args.moderation:
        fields["moderation"] = args.moderation
    return fields


def write_image(item: Any, out: Path, force: bool) -> None:
    if out.exists() and not force:
        die(f"Output already exists: {out} (use --force to overwrite).")
    out.parent.mkdir(parents=True, exist_ok=True)

    b64_json = get_attr(item, "b64_json")
    if b64_json:
        out.write_bytes(base64.b64decode(b64_json))
        print(f"Wrote {out}")
        return

    url = get_attr(item, "url")
    if url:
        request = Request(url, headers={"User-Agent": "codex-image2-router/1.0"})
        with urlopen(request, timeout=120) as response:
            out.write_bytes(response.read())
        print(f"Wrote {out}")
        return

    die("Image response did not contain b64_json or url.")


def parse_sse_data_lines(raw: str) -> list[str]:
    events: list[str] = []
    data_lines: list[str] = []
    for line in raw.splitlines():
        if line == "":
            if data_lines:
                events.append("\n".join(data_lines))
                data_lines = []
            continue
        if line.startswith(":"):
            continue
        if line.startswith("data:"):
            data_lines.append(line[len("data:") :].lstrip())
    if data_lines:
        events.append("\n".join(data_lines))
    return events


def image_item_from_payload(payload: dict[str, Any]) -> dict[str, Any] | None:
    for key in ("b64_json", "base64", "image_base64"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return {"b64_json": value.strip()}
    for key in ("url", "image_url"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return {"url": value.strip()}

    item = payload.get("item")
    if isinstance(item, dict):
        nested = image_item_from_payload(item)
        if nested:
            return nested
        result = item.get("result")
        if isinstance(result, str) and result.strip():
            return {"b64_json": result.strip()}

    response = payload.get("response")
    if isinstance(response, dict):
        output = response.get("output")
        if isinstance(output, list):
            for output_item in reversed(output):
                if not isinstance(output_item, dict):
                    continue
                nested = image_item_from_payload(output_item)
                if nested:
                    return nested
                result = output_item.get("result")
                if isinstance(result, str) and result.strip():
                    return {"b64_json": result.strip()}

    result = payload.get("result")
    if isinstance(result, str) and result.strip():
        return {"b64_json": result.strip()}
    return None


def parse_image_generation_sse(raw: str) -> dict[str, Any]:
    final_items: list[dict[str, Any]] = []
    fallback_items: list[dict[str, Any]] = []
    for data in parse_sse_data_lines(raw):
        if data.strip() == "[DONE]":
            continue
        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            continue
        if not isinstance(payload, dict):
            continue

        item = image_item_from_payload(payload)
        if not item:
            continue

        event_type = str(payload.get("type") or "")
        if "partial_image" in event_type:
            fallback_items.append(item)
            continue
        final_items.append(item)

    data = final_items or fallback_items
    if not data:
        raise RuntimeError("Image SSE response contained no final images.")
    return {"data": data}


def curl_images_generate(key: str, base_url: str, payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        request_path = tmp / "request.json"
        response_path = tmp / "response.json"
        request_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        result = subprocess.run(
            [
                "curl",
                "--show-error",
                "--silent",
                "--max-time",
                str(timeout),
                "-H",
                f"Authorization: Bearer {key}",
                "-H",
                "Content-Type: application/json",
                "-H",
                "Accept: text/event-stream, application/json",
                "-H",
                "Cache-Control: no-store",
                "-H",
                "Pragma: no-cache",
                "--no-buffer",
                f"{base_url.rstrip('/')}/images/generations",
                "--data",
                f"@{request_path}",
                "-o",
                str(response_path),
                "-w",
                "%{http_code}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        status_text = result.stdout.strip()
        try:
            status_code = int(status_text)
        except ValueError:
            status_code = 0
        if result.returncode != 0 or status_code >= 400:
            body = (
                response_path.read_text(encoding="utf-8", errors="replace")
                if response_path.exists()
                else ""
            )
            message = result.stderr.strip() or f"HTTP status: {status_text or 'unknown'}"
            if body:
                message = f"{message}\n{body[:4000]}"
            raise RuntimeError(message)
        raw = response_path.read_text(encoding="utf-8", errors="replace")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            if "data:" in raw:
                try:
                    return parse_image_generation_sse(raw)
                except RuntimeError:
                    pass
            raise RuntimeError(f"Image API response was not JSON: {raw[:2000]}") from exc


def parse_image_response(raw: str) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        if "data:" in raw:
            try:
                return parse_image_generation_sse(raw)
            except RuntimeError:
                pass
        raise RuntimeError(f"Image API response was not JSON: {raw[:2000]}") from exc


def curl_images_edit(
    key: str,
    base_url: str,
    fields: dict[str, Any],
    image_paths: list[Path],
    mask_path: Path | None,
    timeout: int,
) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        response_path = Path(tmpdir) / "response.json"
        command = [
            "curl",
            "--show-error",
            "--silent",
            "--max-time",
            str(timeout),
            "-H",
            f"Authorization: Bearer {key}",
            "-H",
            "Accept: text/event-stream, application/json",
            "-H",
            "Cache-Control: no-store",
            "-H",
            "Pragma: no-cache",
            "--no-buffer",
            f"{base_url.rstrip('/')}/images/edits",
        ]
        for name, value in fields.items():
            if isinstance(value, bool):
                form_value = "true" if value else "false"
            else:
                form_value = str(value)
            command.extend(["-F", f"{name}={form_value}"])
        for path in image_paths:
            command.extend(["-F", f"image[]=@{path}"])
        if mask_path:
            command.extend(["-F", f"mask=@{mask_path}"])
        command.extend(["-o", str(response_path), "-w", "%{http_code}"])

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )
        status_text = result.stdout.strip()
        try:
            status_code = int(status_text)
        except ValueError:
            status_code = 0
        if result.returncode != 0 or status_code >= 400:
            body = (
                response_path.read_text(encoding="utf-8", errors="replace")
                if response_path.exists()
                else ""
            )
            message = result.stderr.strip() or f"HTTP status: {status_text or 'unknown'}"
            if body:
                message = f"{message}\n{body[:4000]}"
            raise RuntimeError(message)
        raw = response_path.read_text(encoding="utf-8", errors="replace")
        return parse_image_response(raw)


def curl_models_list(key: str, base_url: str, timeout: int) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmpdir:
        response_path = Path(tmpdir) / "response.json"
        result = subprocess.run(
            [
                "curl",
                "--show-error",
                "--silent",
                "--max-time",
                str(timeout),
                "-H",
                f"Authorization: Bearer {key}",
                "-H",
                "Cache-Control: no-store",
                "-H",
                "Pragma: no-cache",
                f"{base_url.rstrip('/')}/models",
                "-o",
                str(response_path),
                "-w",
                "%{http_code}",
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        status_text = result.stdout.strip()
        try:
            status_code = int(status_text)
        except ValueError:
            status_code = 0
        if result.returncode != 0 or status_code >= 400:
            body = (
                response_path.read_text(encoding="utf-8", errors="replace")
                if response_path.exists()
                else ""
            )
            message = result.stderr.strip() or f"HTTP status: {status_text or 'unknown'}"
            if body:
                message = f"{message}\n{body[:4000]}"
            raise RuntimeError(message)
        try:
            return json.loads(response_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raw = response_path.read_text(encoding="utf-8", errors="replace")[:2000]
            raise RuntimeError(f"Models API response was not JSON: {raw}") from exc


def generate(args: argparse.Namespace) -> None:
    prompt = read_prompt(args)
    targets = target_providers(args)

    if args.dry_run:
        print(
            json.dumps(
                [
                    {
                        "provider": target["provider"],
                        "base_url": target["base_url"],
                        "transport": (
                            "curl"
                            if should_use_curl(args, target["provider"], target["model"])
                            else "sdk"
                        ),
                        "payload": build_image_payload(args, target["provider"], target["model"], prompt),
                    }
                    for target in targets
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    errors: list[str] = []
    for target in targets:
        provider = target["provider"]
        payload = build_image_payload(args, provider, target["model"], prompt)
        try:
            key = custom_api_key() if provider == "custom" else api_key(provider)
            if not key:
                raise RuntimeError("missing API key environment variable")
            transport = "curl" if should_use_curl(args, provider, target["model"]) else "sdk"
            print(
                f"Trying provider={provider} base_url={target['base_url']} transport={transport}",
                file=sys.stderr,
            )
            if transport == "curl":
                result = curl_images_generate(key, target["base_url"], payload, args.timeout)
                data = list(get_attr(result, "data") or [])
            else:
                client = create_client(key, target["base_url"])
                result = client.images.generate(**payload)
                data = list(get_attr(result, "data") or [])
            if not data:
                raise RuntimeError("Image API response contained no images.")

            output_format = args.output_format
            paths = output_paths(args.out, output_format, len(data))
            for item, path in zip(data, paths):
                write_image(item, path, args.force)
            print(f"Provider used: {provider} ({target['base_url']})", file=sys.stderr)
            return
        except Exception as exc:
            errors.append(f"{provider} ({target['base_url']}): {exc}")
            if normalize_provider(args.provider) != "auto" or args.base_url:
                break
            print(f"Provider failed: {provider}; trying next.", file=sys.stderr)

    die("All provider attempts failed:\n" + "\n".join(f"- {item}" for item in errors))


def edit(args: argparse.Namespace) -> None:
    prompt = read_prompt(args)
    image_paths = validate_image_paths(args)
    mask_path = validate_mask_path(args.mask)
    targets = target_providers(args)

    if args.dry_run:
        print(
            json.dumps(
                [
                    {
                        "provider": target["provider"],
                        "base_url": target["base_url"],
                        "transport": "curl",
                        "endpoint": "/images/edits",
                        "image": [str(path) for path in image_paths],
                        "mask": str(mask_path) if mask_path else None,
                        "fields": build_image_edit_fields(
                            args,
                            target["provider"],
                            target["model"],
                            prompt,
                        ),
                    }
                    for target in targets
                ],
                indent=2,
                ensure_ascii=False,
            )
        )
        return

    errors: list[str] = []
    for target in targets:
        provider = target["provider"]
        fields = build_image_edit_fields(args, provider, target["model"], prompt)
        try:
            key = custom_api_key() if provider == "custom" else api_key(provider)
            if not key:
                raise RuntimeError("missing API key environment variable")
            print(
                f"Trying provider={provider} base_url={target['base_url']} transport=curl",
                file=sys.stderr,
            )
            result = curl_images_edit(
                key,
                target["base_url"],
                fields,
                image_paths,
                mask_path,
                args.timeout,
            )
            data = list(get_attr(result, "data") or [])
            if not data:
                raise RuntimeError("Image API response contained no images.")

            paths = output_paths(args.out, args.output_format, len(data))
            for item, path in zip(data, paths):
                write_image(item, path, args.force)
            print(f"Provider used: {provider} ({target['base_url']})", file=sys.stderr)
            return
        except Exception as exc:
            errors.append(f"{provider} ({target['base_url']}): {exc}")
            if normalize_provider(args.provider) != "auto" or args.base_url:
                break
            print(f"Provider failed: {provider}; trying next.", file=sys.stderr)

    die("All provider attempts failed:\n" + "\n".join(f"- {item}" for item in errors))


def list_models(args: argparse.Namespace) -> None:
    errors: list[str] = []
    for target in target_providers(args):
        provider = target["provider"]
        try:
            key = custom_api_key() if provider == "custom" else api_key(provider)
            if not key:
                raise RuntimeError("missing API key environment variable")
            result = curl_models_list(key, target["base_url"], getattr(args, "timeout", 60))
            data = serializable(get_attr(result, "data") or result)
            print(f"# {provider} {target['base_url']}")
            if isinstance(data, list):
                for item in data:
                    model_id = item.get("id") if isinstance(item, dict) else getattr(item, "id", item)
                    print(model_id)
            else:
                print(json.dumps(serializable(result), indent=2, ensure_ascii=False))
        except Exception as exc:
            errors.append(f"{provider} ({target['base_url']}): {exc}")
            if normalize_provider(args.provider) != "auto" or args.base_url:
                break
    if errors:
        print("Model listing errors:", file=sys.stderr)
        for item in errors:
            print(f"- {item}", file=sys.stderr)
        if len(errors) == len(target_providers(args)):
            raise SystemExit(1)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Call OpenAI-compatible image APIs.")
    parser.add_argument(
        "--provider",
        default="auto",
        help="auto, sakura, fhl, monitor, ccccapi, super, tokenx24, or riclab. auto skips providers without a configured base URL.",
    )
    parser.add_argument("--base-url", help="Explicit API base URL. Disables provider fallback.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    gen = subparsers.add_parser("generate", help="Generate image(s).")
    gen.add_argument(
        "--provider",
        default=argparse.SUPPRESS,
        help="auto, sakura, fhl, monitor, ccccapi, super, tokenx24, or riclab. Overrides the global provider.",
    )
    gen.add_argument("--base-url", default=argparse.SUPPRESS, help="Explicit API base URL.")
    gen.add_argument("--prompt")
    gen.add_argument("--prompt-file")
    gen.add_argument("--model", help="Defaults to provider model env or gpt-image-2.")
    gen.add_argument("--size", default=DEFAULT_SIZE)
    gen.add_argument("--quality", default=DEFAULT_QUALITY)
    gen.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT, choices=["png", "jpeg", "webp"])
    gen.add_argument("--response-format", choices=["b64_json", "url"])
    gen.add_argument("--output-compression", type=int)
    gen.add_argument("--background", choices=["transparent", "opaque", "auto"])
    gen.add_argument("--moderation", choices=["auto", "low"])
    gen.add_argument("--n", type=int, default=1)
    gen.add_argument(
        "--transport",
        choices=["auto", "sdk", "curl"],
        default="auto",
        help="auto uses curl for configured GPT image providers, otherwise the OpenAI SDK.",
    )
    gen.add_argument(
        "--stream",
        choices=["auto", "on", "off"],
        default="auto",
        help="auto enables stream:true for configured GPT image providers; use off to force non-streaming.",
    )
    gen.add_argument("--timeout", type=int, default=300, help="curl max-time in seconds.")
    gen.add_argument(
        "--codex-cli-mode",
        choices=["auto", "on", "off"],
        default="auto",
        help="auto uses the GPT image payload proven by gpt_image_playground for configured providers.",
    )
    gen.add_argument("--out", default=DEFAULT_OUT)
    gen.add_argument("--force", action="store_true")
    gen.add_argument("--dry-run", action="store_true")
    gen.set_defaults(func=generate)

    edit_parser = subparsers.add_parser("edit", help="Edit image(s) from input image references.")
    edit_parser.add_argument(
        "--provider",
        default=argparse.SUPPRESS,
        help="auto, sakura, fhl, monitor, ccccapi, super, tokenx24, or riclab. Overrides the global provider.",
    )
    edit_parser.add_argument("--base-url", default=argparse.SUPPRESS, help="Explicit API base URL.")
    edit_parser.add_argument("--image", action="append", required=True, help="Input image path. Repeat for multiple references.")
    edit_parser.add_argument("--mask", help="Optional mask image path for transparent edit regions.")
    edit_parser.add_argument("--prompt")
    edit_parser.add_argument("--prompt-file")
    edit_parser.add_argument("--model", help="Defaults to provider model env or gpt-image-2.")
    edit_parser.add_argument("--size", default=DEFAULT_SIZE)
    edit_parser.add_argument("--quality", default=DEFAULT_QUALITY)
    edit_parser.add_argument("--output-format", default=DEFAULT_OUTPUT_FORMAT, choices=["png", "jpeg", "webp"])
    edit_parser.add_argument("--response-format", choices=["b64_json", "url"])
    edit_parser.add_argument("--output-compression", type=int)
    edit_parser.add_argument("--background", choices=["transparent", "opaque", "auto"])
    edit_parser.add_argument("--moderation", choices=["auto", "low"])
    edit_parser.add_argument("--n", type=int, default=1)
    edit_parser.add_argument(
        "--transport",
        choices=["auto", "curl"],
        default="auto",
        help="Image edits use curl multipart form uploads.",
    )
    edit_parser.add_argument(
        "--stream",
        choices=["auto", "on", "off"],
        default="auto",
        help="auto enables stream:true for configured GPT image providers; use off to force non-streaming.",
    )
    edit_parser.add_argument("--timeout", type=int, default=300, help="curl max-time in seconds.")
    edit_parser.add_argument(
        "--codex-cli-mode",
        choices=["auto", "on", "off"],
        default="auto",
        help="auto uses the GPT image payload proven by gpt_image_playground for configured providers.",
    )
    edit_parser.add_argument("--out", default=DEFAULT_OUT)
    edit_parser.add_argument("--force", action="store_true")
    edit_parser.add_argument("--dry-run", action="store_true")
    edit_parser.set_defaults(func=edit)

    models = subparsers.add_parser("models", help="List model ids.")
    models.add_argument(
        "--provider",
        default=argparse.SUPPRESS,
        help="auto, sakura, fhl, monitor, ccccapi, super, tokenx24, or riclab. Overrides the global provider.",
    )
    models.add_argument("--base-url", default=argparse.SUPPRESS, help="Explicit API base URL.")
    models.add_argument("--timeout", type=int, default=60, help="curl max-time in seconds.")
    models.set_defaults(func=list_models)
    return parser


def main() -> None:
    load_env_file()
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

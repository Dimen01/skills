import base64
import contextlib
import io
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import patch


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "image2_router.py"
spec = importlib.util.spec_from_file_location("image2_router", SCRIPT_PATH)
image2_router = importlib.util.module_from_spec(spec)
sys.modules["image2_router"] = image2_router
assert spec.loader is not None
spec.loader.exec_module(image2_router)


class Image2RouterProviderRoutingTests(unittest.TestCase):
    def test_normalize_provider_accepts_sakura(self):
        self.assertEqual("sakura", image2_router.normalize_provider("sakura"))

    def test_target_providers_auto_prefers_sakura_first(self):
        targets = image2_router.target_providers(
            Namespace(
                provider="auto",
                base_url=None,
                model=None,
            )
        )

        self.assertEqual("sakura", targets[0]["provider"])
        self.assertEqual("https://sakura886.site/v1", targets[0]["base_url"])

    def test_target_providers_auto_skips_riclab_without_public_default(self):
        with patch.dict(os.environ, {}, clear=True):
            targets = image2_router.target_providers(
                Namespace(
                    provider="auto",
                    base_url=None,
                    model=None,
                )
            )

        self.assertNotIn("riclab", [target["provider"] for target in targets])

    def test_target_providers_requires_riclab_base_url_when_named(self):
        with patch.dict(os.environ, {}, clear=True), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit):
                image2_router.target_providers(
                    Namespace(
                        provider="riclab",
                        base_url=None,
                        model=None,
                    )
                )


class Image2RouterStreamingTests(unittest.TestCase):
    def test_stream_auto_enables_stream_for_configured_gpt_image_provider(self):
        args = Namespace(
            background=None,
            codex_cli_mode="auto",
            moderation=None,
            n=1,
            output_compression=None,
            output_format="png",
            quality="high",
            response_format=None,
            size="auto",
            stream="auto",
        )

        payload = image2_router.build_image_payload(args, "riclab", "gpt-image-2", "cat")

        self.assertTrue(payload["stream"])

    def test_stream_off_does_not_enable_stream(self):
        args = Namespace(
            background=None,
            codex_cli_mode="auto",
            moderation=None,
            n=1,
            output_compression=None,
            output_format="png",
            quality="high",
            response_format=None,
            size="auto",
            stream="off",
        )

        payload = image2_router.build_image_payload(args, "riclab", "gpt-image-2", "cat")

        self.assertNotIn("stream", payload)

    def test_sse_response_with_completed_b64_image_is_parsed(self):
        body = "\n\n".join(
            [
                'event: image_generation.completed\n'
                'data: {"type":"image_generation.completed","b64_json":"aGVsbG8="}',
                "data: [DONE]",
                "",
            ]
        )
        fake_completed = subprocess.CompletedProcess(
            args=["curl"],
            returncode=0,
            stdout="200",
            stderr="",
        )

        with patch("image2_router.subprocess.run", return_value=fake_completed), patch(
            "pathlib.Path.read_text", return_value=body
        ):
            result = image2_router.curl_images_generate(
                "sk-test",
                "https://example.test/v1",
                {"model": "gpt-image-2", "stream": True},
                60,
            )

        self.assertEqual([{"b64_json": "aGVsbG8="}], result["data"])

    def test_sse_response_with_output_item_done_result_is_parsed(self):
        body = (
            "data: "
            '{"type":"response.output_item.done","item":{"type":"image_generation_call","result":"aGVsbG8="}}'
            "\n\n"
            "data: [DONE]\n\n"
        )

        result = image2_router.parse_image_generation_sse(body)

        self.assertEqual([{"b64_json": "aGVsbG8="}], result["data"])

    def test_sse_response_with_url_image_is_parsed(self):
        body = (
            "data: "
            '{"type":"image_generation.completed","url":"https://cdn.example.test/image.png"}'
            "\n\n"
            "data: [DONE]\n\n"
        )

        result = image2_router.parse_image_generation_sse(body)

        self.assertEqual([{"url": "https://cdn.example.test/image.png"}], result["data"])

    def test_sse_response_ignores_partial_images_when_final_image_exists(self):
        body = "\n\n".join(
            [
                'data: {"type":"image_generation.partial_image","b64_json":"cGFydGlhbA=="}',
                'data: {"type":"image_generation.completed","b64_json":"ZmluYWw="}',
                "data: [DONE]",
                "",
            ]
        )

        result = image2_router.parse_image_generation_sse(body)

        self.assertEqual([{"b64_json": "ZmluYWw="}], result["data"])

    def test_sse_response_with_completed_responses_output_is_parsed(self):
        body = (
            "data: "
            '{"type":"response.completed","response":{"output":[{"type":"image_generation_call","result":"aGVsbG8="}]}}'
            "\n\n"
            "data: [DONE]\n\n"
        )

        result = image2_router.parse_image_generation_sse(body)

        self.assertEqual([{"b64_json": "aGVsbG8="}], result["data"])

    def test_sse_response_with_image_edit_completed_event_is_parsed(self):
        body = (
            "data: "
            '{"type":"image_edit.completed","b64_json":"ZWRpdGVk"}'
            "\n\n"
            "data: [DONE]\n\n"
        )

        result = image2_router.parse_image_generation_sse(body)

        self.assertEqual([{"b64_json": "ZWRpdGVk"}], result["data"])


class Image2RouterEditTests(unittest.TestCase):
    def test_build_image_edit_fields_uses_edit_prompt_prefix_for_codex_mode(self):
        args = Namespace(
            background=None,
            codex_cli_mode="auto",
            moderation=None,
            n=1,
            output_compression=None,
            output_format="png",
            quality="high",
            response_format=None,
            size="auto",
            stream="auto",
        )

        fields = image2_router.build_image_edit_fields(args, "riclab", "gpt-image-2", "make it warmer")

        self.assertEqual("gpt-image-2", fields["model"])
        self.assertIn("complete edit prompt", fields["prompt"])
        self.assertIn("make it warmer", fields["prompt"])
        self.assertEqual(True, fields["stream"])
        self.assertEqual("auto", fields["moderation"])
        self.assertEqual("png", fields["output_format"])
        self.assertNotIn("n", fields)
        self.assertNotIn("quality", fields)

    def test_curl_images_edit_sends_multipart_images_and_mask(self):
        fake_completed = subprocess.CompletedProcess(
            args=["curl"],
            returncode=0,
            stdout="200",
            stderr="",
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            image_path = tmp / "input.png"
            mask_path = tmp / "mask.png"
            image_path.write_bytes(b"image")
            mask_path.write_bytes(b"mask")

            with patch("image2_router.subprocess.run", return_value=fake_completed) as run_mock, patch(
                "pathlib.Path.read_text",
                return_value='{"data":[{"b64_json":"aGVsbG8="}]}',
            ):
                result = image2_router.curl_images_edit(
                    "sk-test",
                    "https://example.test/v1",
                    {"model": "gpt-image-2", "prompt": "edit"},
                    [image_path],
                    mask_path,
                    60,
                )

        command = run_mock.call_args.args[0]
        self.assertIn("https://example.test/v1/images/edits", command)
        self.assertIn(f"image[]=@{image_path}", command)
        self.assertIn(f"mask=@{mask_path}", command)
        self.assertIn("model=gpt-image-2", command)
        self.assertEqual([{"b64_json": "aGVsbG8="}], result["data"])

    def test_validate_image_paths_requires_existing_images(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            existing = Path(tmpdir) / "input.png"
            existing.write_bytes(b"image")
            args = Namespace(image=[str(existing), str(Path(tmpdir) / "missing.png")])

            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                image2_router.validate_image_paths(args)

    def test_cli_edit_dry_run_accepts_image_reference(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            image_path = Path(tmpdir) / "input.png"
            image_path.write_bytes(b"image")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_PATH),
                    "edit",
                    "--provider",
                    "riclab",
                    "--base-url",
                    "https://example.test/v1",
                    "--image",
                    str(image_path),
                    "--prompt",
                    "make it warmer",
                    "--dry-run",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

        self.assertEqual(0, result.returncode)
        payload = json.loads(result.stdout)
        self.assertEqual("/images/edits", payload[0]["endpoint"])
        self.assertEqual([str(image_path)], payload[0]["image"])
        self.assertIn("make it warmer", payload[0]["fields"]["prompt"])


class Image2RouterWriteImageTests(unittest.TestCase):
    def test_write_image_writes_b64_data(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir) / "image.png"
            image2_router.write_image({"b64_json": base64.b64encode(b"png").decode()}, tmp, force=True)
            self.assertEqual(b"png", tmp.read_bytes())


if __name__ == "__main__":
    unittest.main()

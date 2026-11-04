import argparse
import base64
import binascii
import json
import os
from pathlib import Path
import sys
import tempfile

from fx_models import validate_model
from openrouter_api import api_key, request_json, verify_model


def image_type(data):
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png", (".png",)
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg", (".jpg", ".jpeg")
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp", (".webp",)
    raise ValueError("Expected a PNG, JPEG, or WebP image.")


def image_request(model, prompt, inputs):
    validate_model(model)
    if not prompt.strip():
        raise ValueError("The image prompt must not be empty.")
    content = [{"type": "text", "text": prompt}]
    for path in inputs:
        data = Path(path).read_bytes()
        mime, _ = image_type(data)
        encoded = base64.b64encode(data).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}})
    return {"model": model, "messages": [{"role": "user", "content": content}],
            "modalities": ["image", "text"], "stream": False}


def response_image(response):
    try:
        images = response["choices"][0]["message"]["images"]
        if not isinstance(images, list) or len(images) != 1:
            raise ValueError("Expected exactly one generated image.")
        url = images[0]["image_url"]["url"]
        header, encoded = url.split(",", 1)
        if header not in ("data:image/png;base64", "data:image/jpeg;base64", "data:image/webp;base64"):
            raise ValueError("Expected an image encoded as a base64 data URL.")
        data = base64.b64decode(encoded, validate=True)
        mime, extensions = image_type(data)
        if header != f"data:{mime};base64":
            raise ValueError("The generated image does not match its declared format.")
        return data, extensions
    except (KeyError, IndexError, TypeError, AttributeError, binascii.Error) as error:
        raise ValueError("OpenRouter returned no valid generated image.") from error


def save_image(output, data, extensions):
    if output.suffix.lower() not in extensions:
        raise ValueError(f"The generated image requires an output extension of {' or '.join(extensions)}. No file was written.")
    descriptor, temporary = tempfile.mkstemp(prefix=".fx-image-", dir=output.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, output)
    finally:
        os.unlink(temporary)


def main():
    parser = argparse.ArgumentParser(prog="fx image nano", description="Generate or edit an image through OpenRouter.")
    parser.add_argument("--default-model", required=True, help=argparse.SUPPRESS)
    parser.add_argument("--model", "-m")
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--input", action="append", default=[], type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        model = validate_model(args.model or args.default_model)
        payload = image_request(model, args.prompt, args.input)
        key = api_key()
        output = args.output.absolute()
        if output.exists() or output.is_symlink():
            raise ValueError(f"The output already exists: {output}. Select a new output path.")
        if output.suffix.lower() not in (".png", ".jpg", ".jpeg", ".webp"):
            raise ValueError("The output must use a .png, .jpg, .jpeg, or .webp extension.")
        output.parent.mkdir(parents=True, exist_ok=True)
        verify_model(model, output="image")
        result = request_json("/chat/completions", payload, key=key, timeout=300)
        data, extensions = response_image(result)
        save_image(output, data, extensions)
        print(output)
        print(json.dumps({"model": model, "generation_id": result.get("id"), "usage": result.get("usage")}), file=sys.stderr)
    except (OSError, ValueError) as error:
        parser.exit(1, f"fx: Cannot generate image: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())

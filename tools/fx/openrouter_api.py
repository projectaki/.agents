import http.client
import json
import os
import urllib.error
import urllib.request


BASE_URL = "https://openrouter.ai/api/v1"


def api_key():
    key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise ValueError("Set OPENROUTER_API_KEY before using OpenRouter.")
    return key


def request_json(path, payload=None, key=None, timeout=30):
    headers = {"Accept": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(BASE_URL + path, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.load(response)
    except urllib.error.HTTPError as error:
        request_id = error.headers.get("x-request-id", "unavailable") if error.headers else "unavailable"
        raise ValueError(f"OpenRouter returned HTTP {error.code} for {path}; request ID: {request_id}. No automatic retry was made.") from None
    except (urllib.error.URLError, TimeoutError, http.client.HTTPException) as error:
        raise ValueError(f"OpenRouter request failed for {path}: {error}. No automatic retry was made.") from None
    except json.JSONDecodeError:
        raise ValueError(f"OpenRouter returned invalid JSON for {path}.") from None
    if not isinstance(result, dict):
        raise ValueError(f"OpenRouter returned an invalid response for {path}.")
    if result.get("error"):
        raise ValueError(f"OpenRouter reported a request failure for {path}.")
    return result


def verify_model(model, *, parameters=(), output="text"):
    catalog = request_json("/models")
    models = catalog.get("data")
    if not isinstance(models, list):
        raise ValueError("OpenRouter returned an invalid model catalog.")
    record = next((item for item in models if isinstance(item, dict) and item.get("id") == model), None)
    if record is None:
        raise ValueError(f"OpenRouter model is unavailable: {model}. Select an available --model explicitly. No replacement model was selected.")
    supported = record.get("supported_parameters", [])
    architecture = record.get("architecture", {})
    if not isinstance(supported, list) or not all(isinstance(item, str) for item in supported) or not isinstance(architecture, dict):
        raise ValueError(f"OpenRouter returned invalid model capabilities for {model}.")
    missing = set(parameters) - set(supported)
    if missing:
        raise ValueError(f"OpenRouter model {model} does not advertise required parameters: {', '.join(sorted(missing))}.")
    if output not in architecture.get("output_modalities", []):
        raise ValueError(f"OpenRouter model {model} does not advertise {output} output.")
    return record

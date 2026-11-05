from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_access import validate_access


def permission_mode(access):
    validate_access(access)
    return "auto" if access == "auto" else "bypassPermissions"


def configure_settings(settings, access):
    validate_access(access)
    if not isinstance(settings, dict):
        raise ValueError("Expected a Claude settings object.")
    sandbox = settings.get("sandbox", {})
    if not isinstance(sandbox, dict):
        raise ValueError("Expected a sandbox settings object.")
    if access == "full":
        settings["sandbox"] = {**sandbox, "enabled": False}
    elif sandbox.get("enabled") is False:
        sandbox.pop("enabled")
        if not sandbox:
            settings.pop("sandbox")
    return settings


if __name__ == "__main__":
    print(permission_mode(sys.argv[1]))

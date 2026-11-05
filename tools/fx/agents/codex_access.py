from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from fx_access import validate_access


def access_arguments(mode):
    validate_access(mode)
    if mode == "auto":
        return ["--approve-for-me"]
    return ["--dangerously-bypass-approvals-and-sandbox"]


if __name__ == "__main__":
    print(" ".join(access_arguments(sys.argv[1])))

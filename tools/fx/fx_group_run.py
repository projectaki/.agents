import argparse
import fcntl
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

from fx_context import captured_results, group_sessions
from fx_group_tabs import TabProcess
from fx_group import comparison_context, resolve_group
from fx_usage import collect_usage, save_group_usage, write_json


TOOL_DIR = Path(__file__).resolve().parent


def prepare_run(group, synthesis_agent, interactive=False):
    members = []
    for session in group_sessions(group):
        metadata = dict(line.split("=", 1) for line in (session / "launch.txt").read_text().splitlines())
        members.append({"session": session.name, "agent": metadata["agent"],
                        "reasoning": metadata["reasoning"]})
    write_json(group / "run.json", {"members": members, "synthesis_agent": synthesis_agent,
                                    "interactive": interactive})
    write_json(group / "run-state.json", {"status": "waiting", "members": {
        member["session"]: {"status": "waiting"} for member in members}})


def retry_members(group, manifest, state):
    for member in manifest["members"]:
        name = member["session"]
        if state.get("members", {}).get(name, {}).get("status") != "finished":
            continue
        try:
            if not captured_results(group / name):
                raise ValueError("No verified final response was saved.")
        except (OSError, ValueError, KeyError) as error:
            state["members"][name] = {"status": "failed", "error": str(error)}
    if all(state.get("members", {}).get(member["session"], {}).get("status") == "finished"
           for member in manifest["members"]):
        raise ValueError("All members finished. Use fx agent group compare to start synthesis again.")
    for member in manifest["members"]:
        previous = member["session"]
        if state.get("members", {}).get(previous, {}).get("status") == "finished":
            continue
        base = re.sub(r"-retry-[0-9]+$", "", previous)
        number = 2
        while (group / f"{base}-retry-{number}").exists():
            number += 1
        session = group / f"{base}-retry-{number}"
        session.mkdir(mode=0o700)
        for name in ("instructions.md", "input-context.md", "initial_prompt.md", "source.json", "launch.txt", "handoff.md", "model.txt"):
            original = group / previous / name
            if original.is_symlink():
                raise ValueError(f"Retry input must not be a symbolic link: {original}")
            if original.exists():
                content = original.read_text()
                if name in ("instructions.md", "handoff.md"):
                    content = content.replace(str(group / previous), str(session))
                session.joinpath(name).write_text(content)
        (session / "findings.md").write_text("# Findings\n\nNo findings recorded.\n")
        member["session"] = session.name
        description = group / "group.md"
        description.write_text(description.read_text().replace(f"| {previous} |", f"| {session.name} |"))
        state["members"][session.name] = {"status": "waiting"}
    write_json(group / "run.json", manifest)


def stop_members(processes):
    for process, _ in processes.values():
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    deadline = time.monotonic() + 3
    for process, _ in processes.values():
        try:
            process.wait(timeout=max(0, deadline - time.monotonic()))
        except subprocess.TimeoutExpired:
            pass
    for process, _ in processes.values():
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def run_members(project, task, group, manifest, state):
    processes = {}
    started = {}
    run_started = time.monotonic()
    state["status"] = "running"
    state["runner_pid"] = os.getpid()
    try:
        for member in manifest["members"]:
            name = member["session"]
            if state["members"][name]["status"] == "finished":
                continue
            agent = member["agent"]
            if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]*", agent):
                raise ValueError("Invalid group adapter name.")
            session = group / name
            log = (session / "runner.log").open("x")
            started[name] = time.monotonic()
            state["members"][name] = {"status": "running",
                                      "started_at": datetime.now(timezone.utc).isoformat()}
            try:
                if manifest.get("interactive", False):
                    process = TabProcess(project, task, group, member, log)
                else:
                    command = [str(TOOL_DIR / "agents" / f"{agent}.batch"), str(project),
                               str(task), str(session), member["reasoning"],
                               (session / "initial_prompt.md").read_text()]
                    process = subprocess.Popen(command, cwd=task, stdin=subprocess.DEVNULL,
                                               stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            except OSError as error:
                log.close()
                state["members"][name].update(status="failed", error=str(error),
                                              finished_at=datetime.now(timezone.utc).isoformat(),
                                              runtime_seconds=round(time.monotonic() - started[name], 6))
                print(f"fx: {name}: failed: {error}", flush=True)
                continue
            except KeyboardInterrupt:
                log.close()
                state["members"][name].update(status="cancelled")
                raise
            processes[name] = (process, log)
            state["members"][name]["pid"] = process.pid
            print(f"fx: {name}: running", flush=True)
        write_json(group / "run-state.json", state)
        while processes:
            for name, (process, log) in list(processes.items()):
                code = process.poll()
                if code is None:
                    continue
                log.close()
                del processes[name]
                outcome = {**state["members"][name], "status": "finished" if code == 0 else "failed",
                           "exit_code": code, "finished_at": datetime.now(timezone.utc).isoformat(),
                           "runtime_seconds": round(time.monotonic() - started[name], 6)}
                if code == 0:
                    try:
                        if not captured_results(group / name):
                            raise ValueError("No verified final response was saved.")
                    except (OSError, ValueError, KeyError) as error:
                        outcome.update(status="failed", error=str(error))
                state["members"][name] = outcome
                print(f"fx: {name}: {outcome['status']}; details: {group / name / 'runner.log'}", flush=True)
                write_json(group / "run-state.json", state)
            if processes:
                time.sleep(0.1)
    finally:
        stop_members(processes)
        for name, (_, log) in processes.items():
            log.close()
            state["members"][name].update(status="cancelled")
        for name, begin in started.items():
            outcome = state["members"][name]
            if "runtime_seconds" not in outcome:
                outcome.update(runtime_seconds=round(time.monotonic() - begin, 6),
                               finished_at=datetime.now(timezone.utc).isoformat())
        state["wall_seconds"] = round(state.get("wall_seconds", 0) + time.monotonic() - run_started, 6)
        state["status"] = "finished" if all(
            state["members"][member["session"]]["status"] == "finished"
            for member in manifest["members"]) else "failed"
        write_json(group / "run-state.json", state)
        for member in manifest["members"]:
            name = member["session"]
            if name in started:
                session = group / name
                usage = collect_usage(TOOL_DIR, session, member["agent"])
                if state["members"][name]["status"] != "finished" and usage["coverage"] == "complete":
                    usage["coverage"] = "partial"
                    usage["notes"].append("This attempt did not finish successfully; unreported work may have consumed more tokens.")
                write_json(session / "usage.json", usage)
        save_group_usage(group, manifest, state)


def run_group(project, task, group, retry=False):
    with (group / ".run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("This group is already running.") from None
        group_sessions(group)
        manifest = json.loads((group / "run.json").read_text())
        state = json.loads((group / "run-state.json").read_text())
        if manifest.get("interactive", False) and not (
                os.environ.get("ZELLIJ") and os.environ.get("ZELLIJ_SESSION_NAME")):
            raise ValueError("Run this interactive group inside a Zellij session.")
        if retry:
            retry_members(group, manifest, state)
        elif state["status"] != "waiting":
            raise ValueError("This group was already started. Use fx agent group retry or compare.")
        if manifest.get("interactive", False):
            print("fx: Synthesis is manual. After every member saves a response, run:", flush=True)
            print(f"fx agent group compare {group.name} --name synthesis "
                  f"--agent {manifest['synthesis_agent']} --new-tab", flush=True)
        run_members(project, task, group, manifest, state)
        if state["status"] != "finished":
            raise ValueError(f"Group incomplete. Results are preserved in {group}. Retry with: fx agent group retry {group.name}")
        if manifest.get("interactive", False):
            print("fx: All members exited. Start synthesis with the compare command when ready.", flush=True)
            return
        comparison_context(task, group)
        print("fx: All members finished. Starting interactive synthesis in this tab.", flush=True)
        os.chdir(task)
        command = [str(TOOL_DIR / "fx"), "agent", "group", "compare", group.name,
                   "--name", "synthesis", "--agent", manifest["synthesis_agent"]]
        os.execv(command[0], command)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("prepare", "run", "retry"))
    parser.add_argument("project", type=Path)
    parser.add_argument("task", type=Path)
    parser.add_argument("group")
    parser.add_argument("synthesis_agent", nargs="?")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args()
    try:
        group = resolve_group(args.task, args.group)
        if args.action == "prepare":
            if not args.synthesis_agent:
                raise ValueError("Supply the synthesis adapter when preparing a group.")
            prepare_run(group, args.synthesis_agent, args.interactive)
        else:
            def cancel(signum, frame):
                raise KeyboardInterrupt
            signal.signal(signal.SIGTERM, cancel)
            signal.signal(signal.SIGHUP, cancel)
            run_group(args.project, args.task, group, args.action == "retry")
    except KeyboardInterrupt:
        print("\nfx: Group cancelled. Completed results and logs are preserved.", file=sys.stderr)
        return 130
    except (OSError, ValueError, KeyError) as error:
        print(f"fx: Group stopped: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

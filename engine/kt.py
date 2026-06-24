#!/usr/bin/env python3
"""kt — tool-neutral knowledge-transfer engine."""
import sys, os, re, json, glob, argparse, subprocess
from datetime import datetime

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", newline="")  # no BOM, no CRLF

SENTINEL = ".pending-handoff"
SHARED = ".shared"
FRESH_MIN = 30

def kt_dir(cwd): return os.path.join(cwd, ".kt")
def read_text(path):
    with open(path, encoding="utf-8") as f: return f.read()
def write_text(path, text):
    with open(path, "w", encoding="utf-8", newline="\n") as f: f.write(text)

def section(body, name):
    lines = body.splitlines()
    pat = re.compile(r'^##\s+' + re.escape(name) + r'\s*$')
    start = next((i + 1 for i, ln in enumerate(lines) if pat.match(ln)), None)
    if start is None: return []
    out = []
    for ln in lines[start:]:
        if re.match(r'^##\s+', ln): break
        out.append(ln)
    while out and not out[0].strip(): out.pop(0)
    while out and not out[-1].strip(): out.pop()
    return out

def parse_header(first_line):
    m = re.match(r'^#\s*KT\s*—\s*(.*)$', first_line)
    if not m:
        return {"headline": first_line.lstrip('# ').strip(), "time": "", "tool": "unknown"}
    parts = [p.strip() for p in m.group(1).split('·')]
    headline = parts[0] if parts else ""
    time = parts[1] if len(parts) > 1 else ""
    tool = parts[2][3:].strip() if len(parts) > 2 and parts[2].lower().startswith("by ") else "unknown"
    return {"headline": headline, "time": time, "tool": tool}

def is_git_repo(cwd):
    try:
        r = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"],
                           cwd=cwd, capture_output=True, text=True)
        return r.returncode == 0 and r.stdout.strip() == "true"
    except FileNotFoundError:
        return False

def build_parser():
    p = argparse.ArgumentParser(prog="kt")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("save", "resume", "format", "inject", "list", "cancel", "share", "local"):
        sp = sub.add_parser(name)
        sp.add_argument("--cwd", default=None)
        if name == "save":
            sp.add_argument("--tool", default="unknown")
            sp.add_argument("--note", default="")
        if name == "resume":
            sp.add_argument("timestamp", nargs="?", default=None)
    return p

def main(argv):
    args = build_parser().parse_args(argv)
    args.cwd = args.cwd or os.getcwd()
    return DISPATCH[args.cmd](args)

# Subcommand stubs (filled in later tasks)
def cmd_save(args): return 0
def cmd_resume(args): return 0
def cmd_format(args): return 0
def cmd_inject(args): return 0
def cmd_list(args): return 0
def cmd_cancel(args): return 0
def cmd_share(args): return 0
def cmd_local(args): return 0

DISPATCH = {"save": cmd_save, "resume": cmd_resume, "format": cmd_format,
            "inject": cmd_inject, "list": cmd_list, "cancel": cmd_cancel,
            "share": cmd_share, "local": cmd_local}

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

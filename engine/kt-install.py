#!/usr/bin/env python3
"""Install the kt engine to ~/.kt, write PATH wrappers, and lay down shims."""
import sys, os, shutil, argparse

REPO = os.path.dirname(os.path.abspath(__file__))

def install_engine(home):
    ktdir = os.path.join(home, ".kt")
    os.makedirs(ktdir, exist_ok=True)
    shutil.copy2(os.path.join(REPO, "kt.py"), os.path.join(ktdir, "kt.py"))
    return ktdir

def write_wrappers(ktdir):
    posix = os.path.join(ktdir, "kt")
    with open(posix, "w", encoding="utf-8", newline="\n") as f:
        f.write('#!/usr/bin/env python3\nimport os, sys\n'
                'os.execvp(sys.executable, [sys.executable, '
                'os.path.join(os.path.dirname(os.path.abspath(__file__)), "kt.py")] + sys.argv[1:])\n')
    try: os.chmod(posix, 0o755)
    except OSError: pass
    with open(os.path.join(ktdir, "kt.cmd"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write('@python "%~dp0kt.py" %*\n')

def path_instructions(home):
    ktdir = os.path.join(home, ".kt")
    return (
        f"Add to PATH: {ktdir}\n"
        f"  Windows: append to the registry HKCU\\Environment 'Path' (REG_EXPAND_SZ) — "
        f"NOT setx (it truncates at 1024 chars) — then broadcast WM_SETTINGCHANGE.\n"
        f"  POSIX: add 'export PATH=\"$HOME/.kt:$PATH\"' to your shell profile.\n"
        f"IMPORTANT: already-running terminals and AI tools will NOT see the new PATH "
        f"until you restart them. The shims/hook use the absolute 'python {ktdir}/kt.py ...' "
        f"form so they work before restart.\n")

def main(argv, home=None):
    parser = argparse.ArgumentParser(prog="kt-install")
    parser.parse_args(argv)
    home = home or os.path.expanduser("~")
    if not any(shutil.which(p) for p in ("python", "python3", "py")):
        print("kt-install: no python interpreter found on PATH.", file=sys.stderr)
        return 1
    ktdir = install_engine(home)
    write_wrappers(ktdir)
    print(f"kt: engine installed to {ktdir}")
    print(path_instructions(home))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

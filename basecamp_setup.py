#!/usr/bin/env python3
"""Partner Basecamp — one-time machine setup, and the Claude connection every notebook uses.

Run it once from the repo root:

    python3 basecamp_setup.py          (Windows: py basecamp_setup.py, or python basecamp_setup.py)

It installs uv if you don't have it, creates .venv with everything the exercises need
(uv sync), registers the "Anthropic Basecamp (.venv)" Jupyter kernel, points VS Code at
.venv, asks for your credentials and saves them to .env, tests which certificates reach your
Claude endpoint, then checks the connection with a real call.

    python3 basecamp_setup.py --check-tls     re-test certificates only (no questions)

The notebooks import connect() from this file, so the connection logic lives in one place.
Only the standard library is imported at the top: the setup half runs before anything is
installed.
"""

import contextlib
import functools
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse

ROOT = pathlib.Path(__file__).resolve().parent  # the repo root: the folder with day1/ and day2/
# How to run this script, as people type it on this OS (python3 often opens the Store on Windows).
SETUP_COMMAND = "py basecamp_setup.py" if os.name == "nt" else "python3 basecamp_setup.py"
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"
KERNEL_NAME = "basecamp-exercises"
KERNEL_DISPLAY_NAME = "Anthropic Basecamp (.venv)"
DEFAULT_MODEL_PREFIX = "bedrock.anthropic."  # what PwC's Bedrock gateway expects
ENV_KEYS = ("ANTHROPIC_API_KEY", "AWS_BEARER_TOKEN_BEDROCK", "AWS_REGION",
            "ANTHROPIC_BASE_URL", "ANTHROPIC_MODEL_PREFIX")
TLS_MODES = ("default", "system+bundle", "system")  # values of BASECAMP_TLS; see check_tls()
TLS_LABELS = {"default": "the default certificates",
              "system+bundle": "the system store plus SSL_CERT_FILE",
              "system": "the system store"}
EXIT_UNREACHABLE = 2  # a check's exit code when the endpoint didn't answer: worth a retry
SPINNER = ("·", "✢", "✳", "✶", "✻", "✽")  # Claude's asterisk, growing; played back and forth


# =============================================================================
# The connection — imported by every notebook and by Diagnose_Fix_Brief.py
# =============================================================================

class Settings:
    """Credentials and routing, read fresh from your shell and .env (the shell wins).

    Re-reading on every call means editing .env and re-running a cell picks up the change
    with no kernel restart. Nothing is written to os.environ, so a script launched from a
    notebook reads the current .env itself instead of inheriting stale values.
    """

    def __init__(self):
        from dotenv import dotenv_values

        # utf-8-sig: Windows editors can save .env with a BOM.
        file = dotenv_values(ENV_FILE, encoding="utf-8-sig") if ENV_FILE.is_file() else {}

        def setting(name):
            value = (os.environ.get(name) or file.get(name) or "").strip()
            return "" if value.startswith("paste-") else value  # the .env.example placeholder

        self.api_key = setting("ANTHROPIC_API_KEY")
        self.bedrock_token = setting("AWS_BEARER_TOKEN_BEDROCK")
        self.region = setting("AWS_REGION")
        self.base_url = setting("ANTHROPIC_BASE_URL")  # company gateway / proxy, if any
        self.model_prefix = setting("ANTHROPIC_MODEL_PREFIX")
        # If both credentials are set, the Anthropic-protocol key wins.
        self.provider = "anthropic" if self.api_key else "bedrock" if self.bedrock_token else None
        # Which certificates to trust: saved by the setup script after testing this machine.
        self.tls = setting("BASECAMP_TLS").lower() or "default"

    def problem(self):
        """What's missing before a client can be built, as (headline, details) — or None."""
        if self.tls not in TLS_MODES:
            return ("📋 BASECAMP_TLS has an unknown value",
                    f"BASECAMP_TLS={self.tls} isn't one of: {', '.join(TLS_MODES)}.\n"
                    "\n"
                    "Let setup test this machine and set it, from the repo root:\n"
                    f"    cd \"{ROOT}\"\n"
                    f"    {SETUP_COMMAND} --check-tls\n"
                    "\n"
                    "Then run this again.")
        if self.provider is None:
            return ("📋 Add your credentials to continue",
                    "No key found in your shell or in .env.\n"
                    "\n"
                    "In a terminal, from the repo root (the folder with day1 and day2):\n"
                    f"    cd \"{ROOT}\"\n"
                    f"    {SETUP_COMMAND}\n"
                    "It asks for your key and saves it to .env. (Or edit .env yourself — "
                    ".env.example shows the options.)\n"
                    "\n"
                    "Then run this again.")
        if self.provider == "bedrock" and not self.region and not self.base_url:
            return ("📋 Bedrock needs a region",
                    f"Found AWS_BEARER_TOKEN_BEDROCK but no AWS_REGION.\n"
                    f"\n"
                    f"Add the region your Bedrock models are enabled in to {ENV_FILE}, e.g.:\n"
                    "    AWS_REGION=us-east-1\n"
                    "\n"
                    "Then run this again.")
        return None

    def model(self, name):
        """Model ID for your route: ANTHROPIC_MODEL_PREFIX if set (gateways), else Bedrock's
        `anthropic.` prefix, else the bare ID. Idempotent — an already-resolved ID passes
        through, so a value from --model can't end up double-prefixed."""
        prefix = self.model_prefix or ("anthropic." if self.provider == "bedrock" else "")
        return name if name.startswith(prefix) else prefix + name

    def endpoint(self):
        """Where your Claude calls go: the gateway if you use one, else the provider's API."""
        if self.base_url:
            return self.base_url
        if self.provider == "bedrock":
            return str(self.make_client().base_url)
        return "https://api.anthropic.com"

    def make_client(self, timeout=600.0, max_retries=2):
        """Client for your route. ANTHROPIC_BASE_URL, when set, sends either kind through it."""
        import anthropic

        options = {"timeout": timeout, "max_retries": max_retries}
        context = _ssl_context(self.tls)
        if context is not None:
            options["http_client"] = anthropic.DefaultHttpxClient(verify=context)
        if self.provider == "bedrock":
            return anthropic.AnthropicBedrockMantle(
                api_key=self.bedrock_token, aws_region=self.region or None,
                base_url=self.base_url or None, **options)
        return anthropic.Anthropic(api_key=self.api_key, base_url=self.base_url or None, **options)


class Connection:
    """What connect() hands a notebook: a verified client plus the resolved model IDs."""

    def __init__(self, settings, client, model, fast_model, big_model):
        self.settings = settings
        self.client = client
        self.model = model
        self.fast_model = fast_model
        self.big_model = big_model
        self.provider = settings.provider
        self.base_url = settings.base_url

    def make_client(self, timeout=600.0, max_retries=2):
        """Another client on the same route, e.g. with a different timeout."""
        return self.settings.make_client(timeout=timeout, max_retries=max_retries)

    @property
    def batch_api(self):
        """The Batch API is an Anthropic API endpoint: Bedrock doesn't expose it, and most
        company gateways don't pass it through."""
        return self.provider == "anthropic" and not self.base_url


class Unreachable(SystemExit):
    """connect() got no answer from the endpoint: a network problem, not a settings one."""


def connect(model="claude-sonnet-5", fast_model="claude-haiku-4-5", big_model="claude-opus-4-8"):
    """Build a Claude client from your settings and prove it works, or stop with a clear
    banner saying what to fix. Model names are bare IDs; they come back resolved for your route.

        model       the workhorse for the exercise
        fast_model  cheap + quick (connection check, judges)
        big_model   when you want to try a larger model
    """
    try:
        import anthropic
        import dotenv  # noqa: F401 — Settings needs it
    except ImportError as exc:
        _stop("📦 Packages missing",
              f"'{exc.name}' isn't installed in the Python running this:\n"
              f"    {sys.executable}\n"
              "\n"
              f"In VS Code, click the kernel name (top right) and pick \"{KERNEL_DISPLAY_NAME}\".\n"
              "Not in the list? In a terminal, from the repo root (the folder with day1 and "
              "day2):\n"
              f"    cd \"{ROOT}\"\n"
              f"    {SETUP_COMMAND}\n"
              "\n"
              "Then run this again.")

    settings = Settings()
    issue = settings.problem()
    if issue:
        _stop(*issue)

    connection = Connection(settings, settings.make_client(timeout=900.0),
                            settings.model(model), settings.model(fast_model),
                            settings.model(big_model))
    gateway = settings.base_url
    via = f" via {gateway}" if gateway else ""

    # Ping the real model, not just the credential's shape: on Bedrock or a gateway a valid
    # key can still 404 if the model isn't enabled for you, or the gateway wants another ID.
    probe = settings.make_client(timeout=anthropic.Timeout(30.0, connect=10.0), max_retries=1)
    try:
        _timed(f"Calling {connection.fast_model}",
               lambda: probe.messages.create(model=connection.fast_model, max_tokens=1,
                                             messages=[{"role": "user", "content": "ping"}]))
    except anthropic.NotFoundError:
        if gateway:
            _status(False, f"Reached the gateway at {gateway}, but it doesn't know model "
                           f"'{connection.fast_model}'. Check ANTHROPIC_MODEL_PREFIX in .env "
                           f"against the model IDs your gateway team gave you, then try again.")
        elif settings.provider == "bedrock":
            _status(False, f"Bedrock reached, but model '{connection.fast_model}' isn't "
                           f"available to you in {settings.region}. Enable model access for it "
                           f"in the Bedrock console (or switch AWS_REGION to a region where it "
                           f"is enabled), then try again.")
        else:
            _status(False, f"Model '{connection.fast_model}' not found for this key.")
        raise SystemExit("Model not available — see the message above.")
    except (anthropic.AuthenticationError, anthropic.PermissionDeniedError):
        if gateway:
            _status(False, f"The gateway at {gateway} rejected that key. Check it's the key your "
                           "gateway issued (re-run basecamp_setup.py to replace it).")
        elif settings.provider == "bedrock":
            _status(False, "That Bedrock key was rejected. Check AWS_BEARER_TOKEN_BEDROCK and "
                           "that it has Bedrock invoke permissions.")
        else:
            _status(False, "That key was rejected. Re-run basecamp_setup.py and paste the whole "
                           "key (it starts with sk-ant-).")
        raise SystemExit("Credentials not accepted — see the message above.")
    except Exception as exc:
        if _is_cert_error(exc):
            _status(False, f"Couldn't verify the HTTPS certificate of {settings.endpoint()}. In a "
                           f"terminal at the repo root, run  {SETUP_COMMAND} --check-tls  to test "
                           "this machine's certificates, then run this again.")
            raise SystemExit("Certificate check failed — see the message above.")
        if isinstance(exc, anthropic.APIConnectionError):
            _status(False, _unreachable(settings, exc))
            raise Unreachable("No answer from the endpoint — see the message above.")
        _status(False, f"Could not reach the API{via} ({type(exc).__name__}). Check your "
                       "connection (and VPN, for a company gateway), then try again.")
        raise

    model = connection.model + {
        "system+bundle": " (certificates: system store + SSL_CERT_FILE, from BASECAMP_TLS)",
        "system": " (certificates: system store, from BASECAMP_TLS)",
    }.get(settings.tls, "")
    if settings.provider == "anthropic" and not gateway:
        _status(True, f"API key verified — you're connected to Claude as {model}.")
    elif settings.provider == "anthropic":
        _status(True, f"Gateway key verified{via} — you're connected to Claude as {model}.")
    else:
        _status(True, f"Bedrock key verified ({settings.region or 'gateway'}){via} — you're "
                      f"connected to Claude as {model}.")
    return connection


# ── Certificates (BASECAMP_TLS) ──────────────────────────────────────────────
# Company laptops sometimes set SSL_CERT_FILE to a certificate bundle that's missing what a
# server needs, and the SDK trusts that file instead of the system store. check_tls() tests
# which option reaches your endpoint and saves it to .env; make_client() then uses it.

def check_tls():
    """Test which certificates verify your Claude endpoint and save the answer to .env as
    BASECAMP_TLS (left unset when the SDK's default works). True if one works, False if none
    does, None if the endpoint didn't answer at all."""
    settings = Settings()
    saved, settings.tls = settings.tls, "default"  # test from scratch, whatever is saved
    if settings.problem():
        print("• No credentials in .env yet, so there's no endpoint to test. Skipped.")
        return True
    url = settings.endpoint()
    host = urllib.parse.urlparse(url).hostname or url
    if not url.startswith("https://"):
        print(f"• {host} uses plain HTTP, so there are no certificates to check.")
        return True
    bundle = os.environ.get("SSL_CERT_FILE", "")
    # The system store only differs from the default when SSL_CERT_FILE overrides it.
    modes = ["default"] + (["system+bundle", "system"] if os.path.isfile(bundle)
                           else ["system"] if bundle else [])
    for mode in modes:
        try:
            works = _timed(f"Trying {TLS_LABELS[mode]}", lambda: _tls_reaches(url, mode),
                           lambda ok: _check_mark() if ok else "✗ certificate rejected")
        except Exception as exc:  # no answer at all, so certificates can't be judged
            print("✗ " + _unreachable(settings, exc))
            return None
        if works:
            break
    else:
        print(f"✗ No certificate setup on this machine can verify {host}.\n"
              f"  SSL_CERT_FILE: {bundle or 'not set'}"
              f"{' (file not found)' if bundle and not os.path.isfile(bundle) else ''}\n"
              "  Your network may re-sign HTTPS traffic with a company certificate this machine\n"
              "  doesn't trust yet. Ask IT for it, and see SETUP.md → certificate errors.")
        return False

    if mode != saved:
        _write_env({"BASECAMP_TLS": "" if mode == "default" else mode})
    if mode == "default":
        print(f"{_check_mark()} Certificates check out for {host}.")
        return True
    why = ("points to a file that doesn't exist" if mode == "system" and bundle
           and not os.path.isfile(bundle) else f"({bundle}) can't verify {host} on its own")
    store = "your system's certificate store" + (" plus that bundle" if mode == "system+bundle"
                                                 else "")
    print(f"{_check_mark()} SSL_CERT_FILE {why}, so the exercises will use {store}.\n"
          f"  {'Saved' if mode != saved else 'Kept'} BASECAMP_TLS={mode} in .env. Your shell and "
          "system settings are unchanged.")
    return True


def _ssl_context(mode):
    """The certificates a BASECAMP_TLS value asks for, or None for the SDK's default (which
    honors SSL_CERT_FILE, and otherwise uses the system store)."""
    if mode not in ("system+bundle", "system"):
        return None
    import ssl
    import truststore

    context = truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)  # the system store, like a browser
    bundle = os.environ.get("SSL_CERT_FILE", "")
    if mode == "system+bundle" and os.path.isfile(bundle):
        context.load_verify_locations(bundle)  # plus whatever the bundle adds
    return context


def _tls_reaches(url, mode):
    """Whether `mode`'s certificates verify the server at url. Raises when the server can't
    be reached at all (offline, VPN, DNS, firewall), so certificates can't be judged."""
    import anthropic

    try:
        context = _ssl_context(mode)
        http = anthropic.DefaultHttpxClient(timeout=10.0, **({"verify": context} if context else {}))
    except OSError:  # e.g. SSL_CERT_FILE names a file that isn't there
        return False
    try:
        with http:
            http.get(url)  # any HTTP answer, even an error status, means the certificate passed
        return True
    except Exception as exc:
        if _is_cert_error(exc):
            return False
        # The connect timeout covers TCP, a proxy's CONNECT and the TLS handshake, so a slow
        # reply means the certificate already passed: some gateways never answer a bare GET.
        if any(type(cause).__name__ == "ReadTimeout" for cause in _causes(exc)):
            return True
        raise


def _causes(exc):
    """exc, then the exceptions that led to it."""
    for _ in range(10):
        if exc is None:
            return
        yield exc
        exc = exc.__cause__ or exc.__context__


def _is_cert_error(exc):
    """True if exc, or anything that caused it, is a failed certificate check."""
    import ssl

    return any(isinstance(cause, ssl.SSLCertVerificationError)
               or "CERTIFICATE_VERIFY_FAILED" in str(cause) for cause in _causes(exc))


def _unreachable(settings, exc):
    """What to try when the endpoint doesn't answer: the network is in the way, not the key."""
    url = settings.endpoint()
    host = urllib.parse.urlparse(url).hostname or url
    root = list(_causes(exc))[-1]
    why = ("it didn't answer in time" if any("Timeout" in type(cause).__name__
                                             for cause in _causes(exc))
           else f"{type(root).__name__}: {str(root)[:100]}")
    if settings.base_url:
        return (f"Couldn't reach {host} ({why}). Check you're connected to the company VPN. "
                "If you are, switch to your phone's hotspot, keep the VPN on, and try again.")
    return (f"Couldn't reach {host} ({why}). The network you're on may be blocking it: "
            "switch to your phone's hotspot and try again.")


def _in_notebook():
    try:
        from IPython import get_ipython
        return get_ipython().__class__.__name__ == "ZMQInteractiveShell"
    except Exception:
        return False


def _status(ok, msg):
    """Green/red banner in notebooks; plain text in a terminal."""
    if _in_notebook():
        from IPython.display import HTML, display
        color = "#1a7f37" if ok else "#b42318"
        bg = "#e6f4ea" if ok else "#fdecea"
        mark = '<span style="color:rgb(78,185,100);">✓</span>' if ok else "✗"
        display(HTML(
            f'<div style="padding:12px 16px;border-radius:8px;background:{bg};'
            f'border:1.5px solid {color};color:{color};font-weight:600;'
            f'font-size:15px;font-family:sans-serif;">{mark} {msg}</div>'
        ))
    else:
        print((_check_mark() if ok else "✗") + " " + msg)


def _timed(label, fn, outcome=lambda result: _check_mark()):
    """Run fn() with a live seconds counter after label, then show the outcome and time.
    Silent in notebooks, where the banner says it all."""
    if _in_notebook():
        return fn()
    start = time.monotonic()
    live = sys.stdout.isatty()
    done = threading.Event()
    frames = _spinner_frames()

    def tick():
        frame = 0
        while not done.wait(0.12):
            spinner = _paint(frames[frame % len(frames)], "215;119;87")  # Claude orange
            print(f"\r{spinner} {label}… {_elapsed(start, decimals=0)}", end="", flush=True)
            frame += 1

    ticker = threading.Thread(target=tick, daemon=True)
    if live:
        ticker.start()
    mark = "✗"
    try:
        result = fn()
        mark = outcome(result)
        return result
    finally:
        done.set()
        if live:
            ticker.join()
        print(f"{chr(13) if live else ''}{label}… {mark} ({_elapsed(start)})", flush=True)


def _elapsed(start, decimals=1):
    seconds = time.monotonic() - start
    if seconds < 60:
        return f"{seconds:.{decimals}f}s"
    return f"{int(seconds // 60)}m {int(seconds % 60):02d}s"


@functools.lru_cache(maxsize=None)
def _colors_on():
    if os.environ.get("NO_COLOR") or not sys.stdout.isatty():
        return False
    if os.name == "nt":
        os.system("")  # switches on color codes in older Windows consoles
    return True


def _paint(text, rgb):
    """text in an "r;g;b" color when the terminal shows color; plain otherwise."""
    return f"\033[38;2;{rgb}m{text}\033[0m" if _colors_on() else text


def _check_mark():
    return _paint("✓", "78;185;100")


def _spinner_frames():
    # The classic Windows console font has no ✢ ✳ ✶ ✻ ✽; Windows Terminal and VS Code do.
    fancy = (os.name != "nt" or os.environ.get("WT_SESSION")
             or os.environ.get("TERM_PROGRAM") == "vscode")
    frames = SPINNER if fancy else ("·", "+", "*")
    return frames + frames[-2:0:-1]


def _stop(head, body):
    """Warning-yellow banner + stop, so a problem shows up here rather than several cells later."""
    if _in_notebook():
        import html
        from IPython.display import HTML, display
        display(HTML(
            '<div style="padding:12px 16px;border-radius:8px;background:#fff8c5;'
            'border:1.5px solid #9a6700;font-size:15px;font-family:sans-serif;">'
            '<div style="color:#9a6700;font-weight:600;">' + html.escape(head) + '</div>'
            '<pre style="margin:10px 0 0;font-family:inherit;font-size:14px;font-weight:400;'
            'color:#141413;white-space:pre-wrap;">' + html.escape(body) + '</pre></div>'
        ))
        raise SystemExit("Stopped — see the message above.")
    raise SystemExit("\n" + head + "\n   " + body.replace("\n", "\n   ") + "\n")


# =============================================================================
# One-time setup — python3 basecamp_setup.py (Windows: py basecamp_setup.py)
# =============================================================================

def main():
    _prepare_console()
    try:
        import readline  # noqa: F401 — without it, macOS cuts a pasted key off at 1,024 characters
    except ImportError:  # Windows doesn't need it
        pass
    print("Partner Basecamp setup\n")
    uv = _find_uv() or _install_uv()
    _ask_credentials()
    with _step("Installing the exercise packages into .venv (first run takes a minute)"):
        _sync(uv)
    with _step("Registering the Jupyter kernel"):
        _run([uv, "run", "--no-sync", "python", "-m", "ipykernel", "install", "--user",
              "--name", KERNEL_NAME, "--display-name", KERNEL_DISPLAY_NAME], quiet=True)
        print(f"{_check_mark()} Kernel \"{KERNEL_DISPLAY_NAME}\" is available in VS Code and Jupyter.")
        _point_vscode_at_venv()
    with _step("Checking certificates"):
        _retry_while_unreachable(lambda: _check_tls(uv))
    with _step("Checking your connection to Claude"):
        code = _retry_while_unreachable(lambda: subprocess.run(
            [uv, "run", "--no-sync", "python", "-c",
             "import sys, basecamp_setup as b\n"
             "try: b.connect()\n"
             "except b.Unreachable: sys.exit(b.EXIT_UNREACHABLE)"], cwd=ROOT).returncode)
    if code != 0:
        raise SystemExit("\nSetup finished, but the connection check failed — fix what it "
                         f"says above, then run  {SETUP_COMMAND}  again.")
    print(f"\n{_check_mark()} You're all set! Open any notebook in VS Code; if it doesn't pick the "
          f"kernel by itself, click the kernel name (top right) and choose \"{KERNEL_DISPLAY_NAME}\".")
    _open_vscode()


def check_tls_command():
    """basecamp_setup.py --check-tls: re-test certificates without redoing the whole setup."""
    _prepare_console()
    uv = _find_uv()
    if not uv or not (ROOT / ".venv").is_dir():
        raise SystemExit(f"Run the full setup first:  {SETUP_COMMAND}")
    with _step("Checking certificates"):
        code = _check_tls(uv)
    if code != 0:
        raise SystemExit(1)
    print("Done. If a notebook is open, run its setup cell again.")


def _check_tls(uv):
    """check_tls() needs the SDK, so it runs in .venv. Exit code 0 if it found certificates
    that work, EXIT_UNREACHABLE if the endpoint didn't answer, 1 otherwise."""
    return subprocess.run([uv, "run", "--no-sync", "python", "-c",
                           "import sys, basecamp_setup as b; works = b.check_tls(); "
                           "sys.exit(b.EXIT_UNREACHABLE if works is None else not works)"],
                          cwd=ROOT).returncode


def _retry_while_unreachable(attempt):
    """Run attempt(), which returns an exit code, again each time the endpoint didn't
    answer, once the user has switched networks (VPN, hotspot) and pressed Enter."""
    while True:
        code = attempt()
        if code != EXIT_UNREACHABLE or not sys.stdin.isatty():
            return code
        try:
            input("Press Enter to try again (Ctrl+C to stop): ")
        except KeyboardInterrupt:
            print()  # end the prompt's line before the step reports its time
            raise


def _prepare_console():
    for stream in (sys.stdout, sys.stderr):
        # Windows consoles: replace characters they can't show instead of crashing. Line
        # buffering keeps these messages in order with uv's own output.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="replace", line_buffering=True)


def _heading(title):
    print(f"\n── {title} ──")


@contextlib.contextmanager
def _step(title):
    """A setup step: its heading, then how long it took (also when it fails)."""
    _heading(title)
    start = time.monotonic()
    try:
        yield
    finally:
        print(f"   Took {_elapsed(start)}.")


def _run(cmd, quiet=False):
    result = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=quiet)
    if result.returncode != 0:
        if quiet:
            print((result.stdout or "") + (result.stderr or ""))
        raise SystemExit(f"\n✗ This command failed: {' '.join(map(str, cmd))}")
    return result


# ── uv ───────────────────────────────────────────────────────────────────────

def _find_uv():
    found = shutil.which("uv")
    if found:
        return found
    # Where the official installer puts it, in case this shell's PATH predates the install.
    exe = "uv.exe" if os.name == "nt" else "uv"
    for folder in (pathlib.Path.home() / ".local" / "bin", pathlib.Path.home() / ".cargo" / "bin"):
        if (folder / exe).is_file():
            return str(folder / exe)
    return None


def _install_uv():
    manual = ("Install it yourself, then run this script again:\n"
              "    macOS:   brew install uv\n"
              "    Windows: winget install --id=astral-sh.uv -e\n"
              "    Any:     see https://docs.astral.sh/uv/getting-started/installation/")
    print("This setup uses uv (https://docs.astral.sh/uv/) to manage Python packages, and it "
          "isn't installed yet.")
    if not sys.stdin.isatty() or not _ask_yes_no("Install it now with the official installer?",
                                                 default=True):
        raise SystemExit(manual)
    if os.name == "nt":
        cmd = ["powershell", "-ExecutionPolicy", "ByPass", "-c",
               "irm https://astral.sh/uv/install.ps1 | iex"]
    else:
        cmd = ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"]
    subprocess.run(cmd)
    uv = _find_uv()
    if not uv:
        raise SystemExit("\nCouldn't install uv automatically (a company network can block it).\n"
                         + manual)
    return uv


_CERT_FAILURE = re.compile(r"invalid peer certificate|UnknownIssuer|certificate verify failed",
                           re.IGNORECASE)


def _sync(uv):
    """uv sync. If a download fails on a certificate, retry with the system certificate store,
    which trusts what company networks re-sign HTTPS with. uv ignores that store while
    SSL_CERT_FILE is set, so the retry also drops it — for uv only, never your shell."""
    ok, output = _uv_sync(uv, os.environ)
    if ok:
        return
    if _CERT_FAILURE.search(output):
        env = dict(os.environ, UV_SYSTEM_CERTS="1", UV_NATIVE_TLS="1")  # new and old uv names
        dropped = [name for name in ("SSL_CERT_FILE", "SSL_CERT_DIR") if env.pop(name, None)]
        if dropped:
            print(f"\nuv couldn't verify a download using {' / '.join(dropped)} (set on this "
                  "machine). Retrying with your system's certificate store, for this install "
                  "only…")
        else:
            print("\nRetrying with your system's certificate store (common behind a company "
                  "proxy)…")
        ok, output = _uv_sync(uv, env)
        if ok:
            return
    if _CERT_FAILURE.search(output):
        raise SystemExit(
            "\n✗ Couldn't verify the package server's certificate, even with your system's\n"
            "  certificate store. Your network may re-sign HTTPS with a company certificate this\n"
            "  machine doesn't trust yet: ask IT for it, or for an internal package mirror.\n"
            "  More in SETUP.md → certificate errors.")
    mirror = ('$env:UV_DEFAULT_INDEX="https://<your-mirror>/simple"; ' if os.name == "nt"
              else "UV_DEFAULT_INDEX=https://<your-mirror>/simple ") + SETUP_COMMAND
    raise SystemExit(
        "\n✗ Couldn't install the packages. If your company blocks PyPI, ask IT for the internal\n"
        f"  package mirror and run:  {mirror}\n"
        "  Behind a proxy? Set HTTPS_PROXY first. More in SETUP.md.")


def _uv_sync(uv, env):
    """Run uv sync, showing its output as it comes; returns (succeeded, output)."""
    process = subprocess.Popen([uv, "sync"], cwd=ROOT, env=env, stdout=subprocess.PIPE,
                               stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                               errors="replace")
    lines = []
    for line in process.stdout:
        print(line, end="")
        lines.append(line)
    return process.wait() == 0, "".join(lines)


# ── VS Code ──────────────────────────────────────────────────────────────────

def _point_vscode_at_venv():
    """Make .venv VS Code's default interpreter for this folder, so notebooks pick it up."""
    python = ("${workspaceFolder}\\.venv\\Scripts\\python.exe" if os.name == "nt"
              else "${workspaceFolder}/.venv/bin/python")
    path = ROOT / ".vscode" / "settings.json"
    try:
        settings = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}
    except ValueError:  # VS Code allows comments in settings.json; don't rewrite one we can't parse
        print(f"• Left {path} alone (couldn't parse it). Add this line to it yourself:\n"
              f'    "python.defaultInterpreterPath": "{python}"')
        return
    if settings.get("python.defaultInterpreterPath") == python:
        return
    settings["python.defaultInterpreterPath"] = python
    path.parent.mkdir(exist_ok=True)
    path.write_text(json.dumps(settings, indent=2) + "\n", encoding="utf-8")
    print(f"{_check_mark()} VS Code will use .venv for this folder.")


def _open_vscode():
    """Offer to open the repo root in VS Code, if its `code` command is on PATH."""
    if os.environ.get("TERM_PROGRAM") == "vscode":
        return  # running in VS Code's own terminal: it's already open
    code = shutil.which("code")
    if not code or not sys.stdin.isatty():
        print(f"Next: open VS Code, choose File → Open Folder…, and pick {ROOT}")
        return
    try:
        input("\nHit Enter to open VS Code (Ctrl+C to skip): ")
    except (KeyboardInterrupt, EOFError):
        print()
        return
    subprocess.run([code, str(ROOT)])


# ── Credentials → .env ───────────────────────────────────────────────────────

def _ask_credentials():
    _heading("Your Claude credentials")
    if not sys.stdin.isatty():
        print("• Not an interactive terminal — keeping .env as it is.")
        return
    for name in ENV_KEYS:
        if os.environ.get(name):
            print(f"• Note: {name} is set in your shell, and the shell wins over .env.")

    current = _read_env()
    summary = _describe(current)
    if summary and _ask_yes_no(f"Your .env already has {summary}. Keep it?", default=True):
        return

    print("Paste your key: an Anthropic API key, a company gateway key, or an Amazon Bedrock API key.")
    while True:
        key = input("Key: ").strip()
        if not key:
            print("  Nothing pasted — try again (Ctrl+C to quit).")
            continue
        if key.startswith("sk-ant-"):
            values = {"ANTHROPIC_API_KEY": key}
            break
        if key.startswith(("ABSK", "bedrock-api-key-")):
            print("  That's an Amazon Bedrock API key.")
            region = _ask("  AWS region your Claude models are enabled in", default="us-east-1")
            base_url = _ask_url("  Company gateway URL, if you go through one (Enter for none)",
                                required=False)
            prefix = _ask("  Model ID prefix your gateway expects — Enter for anthropic. "
                          "(Bedrock's standard)", default="anthropic.") if base_url else ""
            values = {"AWS_BEARER_TOKEN_BEDROCK": key, "AWS_REGION": region,
                      "ANTHROPIC_BASE_URL": base_url,
                      "ANTHROPIC_MODEL_PREFIX": "" if prefix == "anthropic." else prefix}
            break
        print("  That isn't an Anthropic API key (those start with sk-ant-) or an Amazon Bedrock "
              "key, so it's probably from a company gateway.")
        if not _ask_yes_no("  Is it a key for a company gateway?", default=True):
            print("  Check the key and paste it again.")
            continue
        base_url = _ask_url("  Gateway URL (from your gateway team)", required=True)
        prefix = _ask(f"  Model ID prefix your gateway expects — Enter for {DEFAULT_MODEL_PREFIX}, "
                      "or 'none'", default=DEFAULT_MODEL_PREFIX)
        values = {"ANTHROPIC_API_KEY": key, "ANTHROPIC_BASE_URL": base_url,
                  "ANTHROPIC_MODEL_PREFIX": "" if prefix.lower() == "none" else prefix}
        break

    _write_env({name: values.get(name, "") for name in ENV_KEYS})
    print(f"{_check_mark()} Saved to {ENV_FILE} (gitignored — never committed).")


def _ask(question, default=""):
    answer = input(f"{question} [{default}]: " if default else f"{question}: ").strip()
    return answer or default


def _ask_yes_no(question, default=True):
    answer = input(f"{question} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    return default if not answer else answer.startswith("y")


def _ask_url(question, required):
    while True:
        url = _ask(question).rstrip("/")
        if not url and not required:
            return ""
        if url.startswith(("https://", "http://")):
            return url
        print("    It should start with https:// — try again.")


def _mask(secret):
    return secret[:7] + "…" + secret[-4:] if len(secret) > 14 else "…" + secret[-2:]


def _read_env():
    """The active KEY=value lines in .env — just enough to summarize what's there."""
    if not ENV_FILE.is_file():
        return {}
    values = {}
    for line in ENV_FILE.read_text(encoding="utf-8-sig").splitlines():
        match = re.match(r"\s*(?:export\s+)?([A-Z_][A-Z0-9_]*)\s*=\s*(.*)", line)
        if match:
            value = re.sub(r"\s+#.*$", "", match.group(2)).strip().strip("'\"")
            if value and not value.startswith("paste-"):
                values[match.group(1)] = value
    return values


def _describe(values):
    if values.get("ANTHROPIC_API_KEY"):
        what = f"a key ({_mask(values['ANTHROPIC_API_KEY'])})"
    elif values.get("AWS_BEARER_TOKEN_BEDROCK"):
        what = f"a Bedrock key ({_mask(values['AWS_BEARER_TOKEN_BEDROCK'])})"
    else:
        return ""
    if values.get("ANTHROPIC_BASE_URL"):
        what += f" for the gateway at {values['ANTHROPIC_BASE_URL']}"
    return what


def _write_env(values):
    """Set each KEY in .env (starting from .env.example), keeping its comments. An empty value
    comments the key out, so switching from a gateway back to a plain key leaves no leftovers."""
    source = ENV_FILE if ENV_FILE.is_file() else ENV_EXAMPLE
    lines = source.read_text(encoding="utf-8-sig").splitlines() if source.is_file() else []
    for name, value in values.items():
        pattern = re.compile(rf"\s*(#\s*)?(export\s+)?{name}\s*=")
        matches = [i for i, line in enumerate(lines) if pattern.match(line)]
        if value:
            if matches:
                lines[matches[0]] = f"{name}={value}"
            else:
                lines.append(f"{name}={value}")
            matches = matches[1:]
        for i in matches:  # any other active line for this key gets commented out
            if not lines[i].lstrip().startswith("#"):
                lines[i] = "# " + lines[i]
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if os.name != "nt":
        ENV_FILE.chmod(0o600)  # readable by you only


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Partner Basecamp setup. With no options: the full one-time setup.")
    parser.add_argument("--check-tls", action="store_true",
                        help="only re-test which certificates reach your Claude endpoint and "
                             "save the result to .env (BASECAMP_TLS); asks nothing")
    args = parser.parse_args()
    try:
        check_tls_command() if args.check_tls else main()
    except KeyboardInterrupt:
        raise SystemExit(f"\nStopped. Run  {SETUP_COMMAND}  again whenever you're ready.")

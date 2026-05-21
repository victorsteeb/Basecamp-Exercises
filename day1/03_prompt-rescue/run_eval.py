"""
Runner for Prompt_Rescue_solo.py outside Jupyter.
Patches IPython display and matplotlib so the eval suite works in a terminal.
"""
import os, sys, types

# ── API key — set ANTHROPIC_API_KEY in your environment before running ──
_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")

class _ProtectedEnv(os._Environ):
    def __setitem__(self, key, value):
        if key == "ANTHROPIC_API_KEY" and not value:
            return  # ignore attempts to blank the key
        super().__setitem__(key, value)

os.environ.__class__ = _ProtectedEnv
os.environ["ANTHROPIC_API_KEY"] = _API_KEY

# ── Stub IPython (matplotlib probes for it) ──
ipython_display = types.ModuleType("IPython.display")
ipython_display.display = lambda *a, **kw: None
ipython_display.HTML = lambda x: x
ipython_display.Markdown = lambda x: x
ipython_mod = types.ModuleType("IPython")
ipython_mod.display = ipython_display
ipython_mod.get_ipython = lambda: None
sys.modules["IPython"] = ipython_mod
sys.modules["IPython.display"] = ipython_display

# ── Non-interactive matplotlib backend ──
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Stub all pyplot calls the harness uses so no GUI/rendering is attempted
_ax = types.SimpleNamespace(**{m: (lambda *a, **kw: None) for m in [
    "barh", "set_yticks", "set_yticklabels", "set_xlabel", "set_title",
    "legend", "text", "set_xlim", "invert_yaxis", "plot", "axhline",
    "annotate", "set_ylabel", "set_ylim", "set_xticks", "set_xticklabels",
]})
plt.subplots    = lambda *a, **kw: (None, _ax)   # (fig, ax) — ax is the stub
plt.tight_layout = lambda: None
plt.show        = lambda: None

# ── Text-based display_results — replaces the HTML/chart version ──
def _text_display_results(eval_result, label="Current"):
    total  = eval_result["total_passed"]
    n      = eval_result["total_cases"]
    pct    = round(100 * total / n) if n else 0
    print(f"\n{'='*56}")
    print(f"  {label}")
    print(f"  Score: {total}/{n}  ({pct}%)")
    print(f"{'='*56}")
    print(f"  {'Category':<24} {'Pass':>4}  {'Total':>5}")
    print(f"  {'-'*38}")
    for cat in eval_result["categories"].values():
        bar = "#" * cat["passed"] + "." * (cat["total"] - cat["passed"])
        print(f"  {cat['label']:<24} {cat['passed']:>4}  /{cat['total']:<4}  [{bar}]")
    print()
    for r in eval_result["results"]:
        status = "PASS" if r["pass"] else "FAIL"
        fails  = [f'{k}: {v["reason"]}' for k, v in r["criteria"].items() if not v["pass"]]
        detail = "  →  " + "; ".join(fails) if fails else ""
        print(f"  Case {r['case_id']:>2} ({r['category']:<14}) {status}{detail}")
    print()

# ── Load and execute the exercise module ──
import importlib.util, pathlib

spec = importlib.util.spec_from_file_location(
    "prompt_rescue",
    pathlib.Path(__file__).parent / "Prompt_Rescue_solo.py"
)
mod = importlib.util.module_from_spec(spec)
mod._display_results = _text_display_results   # override before exec

spec.loader.exec_module(mod)

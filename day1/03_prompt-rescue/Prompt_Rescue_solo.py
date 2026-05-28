# Install the Anthropic SDK
# !pip install -q anthropic matplotlib  # Jupyter shell magic; runs in the .ipynb cell, commented here so static linters don't flag it

# API Key Configuration
import os
ANTHROPIC_API_KEY = ""  # <-- Paste your API key here
os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY

# Verify connection
import anthropic
client = anthropic.Anthropic()
test = client.messages.create(
    model="claude-haiku-4-5",
    max_tokens=50,
    messages=[{"role": "user", "content": "Say 'Connected!' and nothing else."}]
)
print(f"API Connected: {test.content[0].text}")

# ============================================================
# YOUR PROMPT -- Edit this to fix the broken prompt!
# ============================================================

system_prompt = """
You are a support ticket processor. For each ticket, you must:
1. Classify priority (P1-P4) based on business impact
2. Extract: product name, version, error codes, affected users count
3. Draft a helpful response acknowledging the issue and providing next steps
4. Return everything as JSON: {"priority": "", "entities": {"product": "", "version": "", "error_codes": [], "affected_users": ""}, "response": "", "confidence": "high/medium/low"}

Rules:
- P1 = system down, all users affected
- P2 = major feature broken, many users affected
- P3 = minor bug, few users affected
- P4 = feature request or cosmetic issue
- If unsure about priority, use your best judgment
- Response should be professional and empathetic
- Always include all JSON fields even if empty
- Be concise but thorough
"""

print("Broken prompt loaded. Run the eval suite (Cell 7) to see your baseline score.")
print(f"Prompt length: {len(system_prompt)} characters")

#@title Eval Harness (click to load -- do not edit this cell)

# ============================================================
# EVAL HARNESS -- All evaluation logic is embedded here.
# Run this cell once to load the harness functions.
# ============================================================

import json
import re
import base64
import time
from datetime import datetime
import anthropic
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from IPython.display import display, HTML
matplotlib.rcParams['figure.facecolor'] = 'white'

# ---------------------------------------------------------------------------
# Embedded eval cases (base64-encoded to discourage casual peeking)
# ---------------------------------------------------------------------------

_EVAL_CASES_B64 = "ewogICJjYXRlZ29yaWVzIjogewogICAgImNsZWFuIjogeyJsYWJlbCI6ICJDbGVhbiBpbnB1dHMiLCAiY2FzZV9pZHMiOiBbMSwgMiwgMywgNF19LAogICAgIm11bHRpX2lzc3VlIjogeyJsYWJlbCI6ICJNdWx0aS1pc3N1ZSIsICJjYXNlX2lkcyI6IFs1LCA2XX0sCiAgICAidmFndWUiOiB7ImxhYmVsIjogIlZhZ3VlL3VuY2xlYXIiLCAiY2FzZV9pZHMiOiBbNywgOCwgMjFdfSwKICAgICJub25fbmF0aXZlIjogeyJsYWJlbCI6ICJOb24tbmF0aXZlIEVuZ2xpc2giLCAiY2FzZV9pZHMiOiBbOSwgMTAsIDIwXX0sCiAgICAiZmVhdHVyZV9yZXF1ZXN0IjogeyJsYWJlbCI6ICJGZWF0dXJlIHJlcXVlc3RzIiwgImNhc2VfaWRzIjogWzExLCAxMl19LAogICAgImNvbXBsZXgiOiB7ImxhYmVsIjogIkNvbXBsZXgvbG9uZy9lZGdlIiwgImNhc2VfaWRzIjogWzEzLCAxNCwgMTUsIDE2LCAxNywgMTgsIDE5XX0KICB9LAogICJjYXNlcyI6IFsKICAgIHsKICAgICAgImlkIjogMSwKICAgICAgImNhdGVnb3J5IjogImNsZWFuIiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IEVycm9yIDUwMyBvbiBsb2dpbiBwYWdlXG5cblNpbmNlIDJwbSBFU1QgdG9kYXksIGFsbCB1c2VycyAoYXBwcm94aW1hdGVseSA1MDApIGluIG91ciBvcmdhbml6YXRpb24gYXJlIHVuYWJsZSB0byBsb2cgaW50byB0aGUgcGxhdGZvcm0uIFdlIHJlY2VpdmUgYSA1MDMgU2VydmljZSBVbmF2YWlsYWJsZSBlcnJvci4gVGhpcyBpcyBvdXIgcHJpbWFyeSBDUk0gdG9vbCBhbmQgc2FsZXMgdGVhbSBpcyBjb21wbGV0ZWx5IGJsb2NrZWQuIEVycm9yIGNvZGU6IFNWQy01MDMtQVVUSC4gUnVubmluZyB2ZXJzaW9uIDQuMS4yLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAxIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiAiQ1JNIHBsYXRmb3JtIiwKICAgICAgICAidmVyc2lvbiI6ICI0LjEuMiIsCiAgICAgICAgImVycm9yX2NvZGVzIjogWyJTVkMtNTAzLUFVVEgiXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiNTAwIgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiQ2xlYW4gUDEg4oCUIHNob3VsZCBwYXNzIGF0IGJhc2VsaW5lLiBTeXN0ZW0gb3V0YWdlIGJsb2NraW5nIGFsbCB1c2Vycy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAyLAogICAgICAiY2F0ZWdvcnkiOiAiY2xlYW4iLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogU2VhcmNoIGZ1bmN0aW9uIHJldHVybmluZyB3cm9uZyByZXN1bHRzXG5cblNpbmNlIHllc3RlcmRheSdzIHVwZGF0ZSB0byB2ZXJzaW9uIDIuOC4wLCB0aGUgc2VhcmNoIGZlYXR1cmUgaW4gb3VyIGludmVudG9yeSBtYW5hZ2VtZW50IG1vZHVsZSBpcyByZXR1cm5pbmcgaW5jb3JyZWN0IHJlc3VsdHMuIFdoZW4gc2VhcmNoaW5nIGZvciBwcm9kdWN0IFNLVXMsIGl0IHJldHVybnMgdW5yZWxhdGVkIGl0ZW1zLiBUaGlzIGlzIGFmZmVjdGluZyBvdXIgd2FyZWhvdXNlIHRlYW0gb2YgYWJvdXQgNDUgcGVvcGxlIHdobyByZWx5IG9uIHNlYXJjaCBmb3IgZGFpbHkgcGlja2luZyBvcGVyYXRpb25zLiBObyBlcnJvciBjb2RlcyBkaXNwbGF5ZWQsIGJ1dCB0aGUgYmVoYXZpb3Igc3RhcnRlZCByaWdodCBhZnRlciB0aGUgdXBkYXRlLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAyIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiAiaW52ZW50b3J5IG1hbmFnZW1lbnQgbW9kdWxlIiwKICAgICAgICAidmVyc2lvbiI6ICIyLjguMCIsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjQ1IgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiQ2xlYW4gUDIg4oCUIG1ham9yIGZlYXR1cmUgYnJva2VuLCBjbGVhciBwcm9kdWN0L3ZlcnNpb24uIFNob3VsZCBwYXNzIGF0IGJhc2VsaW5lLiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDMsCiAgICAgICJjYXRlZ29yeSI6ICJjbGVhbiIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBUb29sdGlwIHRleHQgY3V0IG9mZiBvbiBzZXR0aW5ncyBwYWdlXG5cbk9uIHRoZSBhZG1pbiBzZXR0aW5ncyBwYWdlLCB0aGUgdG9vbHRpcCBmb3IgdGhlIFwiRGF0YSBSZXRlbnRpb24gUG9saWN5XCIgZmllbGQgaXMgdHJ1bmNhdGVkLiBJdCBzaG93cyBcIkRhdGEgd2lsbCBiZSByZXRhaW5lZCBmb3IuLi5cIiBhbmQgY3V0cyBvZmYuIFRoaXMgb25seSBhZmZlY3RzIGFkbWlucyB3aGVuIGhvdmVyaW5nIG92ZXIgdGhhdCBzcGVjaWZpYyBmaWVsZC4gV2UncmUgb24gdmVyc2lvbiA1LjAuMS4gTm90IGJsb2NraW5nIGFueXRoaW5nLCBqdXN0IG5vdGljZWQgaXQgZHVyaW5nIGEgdHJhaW5pbmcgc2Vzc2lvbiB3aXRoIDIgbmV3IGFkbWlucy4iLAogICAgICAiZ29sZF9wcmlvcml0eSI6ICJQMyIsCiAgICAgICJnb2xkX2VudGl0aWVzIjogewogICAgICAgICJwcm9kdWN0IjogbnVsbCwKICAgICAgICAidmVyc2lvbiI6ICI1LjAuMSIsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjIiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJDbGVhbiBQMyDigJQgbWlub3IgY29zbWV0aWMgYnVnLiBTaG91bGQgcGFzcyBhdCBiYXNlbGluZS4iCiAgICB9LAogICAgewogICAgICAiaWQiOiA0LAogICAgICAiY2F0ZWdvcnkiOiAiY2xlYW4iLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogUmVxdWVzdCBmb3IgYnVsayBleHBvcnQgdG8gUERGXG5cbldlJ2QgbG92ZSB0byBoYXZlIHRoZSBhYmlsaXR5IHRvIGV4cG9ydCBtdWx0aXBsZSByZXBvcnRzIHRvIFBERiBhdCBvbmNlLiBDdXJyZW50bHkgd2UgaGF2ZSB0byBleHBvcnQgZWFjaCByZXBvcnQgaW5kaXZpZHVhbGx5IHdoaWNoIGlzIHRpbWUtY29uc3VtaW5nIGZvciBvdXIgYW5hbHl0aWNzIHRlYW0uIFdvdWxkIGJlIGdyZWF0IGlmIHRoZXJlIHdhcyBhIFwiU2VsZWN0IEFsbFwiIGNoZWNrYm94IGFuZCBhIFwiRXhwb3J0IFNlbGVjdGVkIHRvIFBERlwiIGJ1dHRvbi4gQWJvdXQgOCBwZW9wbGUgb24gb3VyIHRlYW0gd291bGQgdXNlIHRoaXMgZmVhdHVyZSByZWd1bGFybHkuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDQiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6IG51bGwsCiAgICAgICAgInZlcnNpb24iOiBudWxsLAogICAgICAgICJlcnJvcl9jb2RlcyI6IFtdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICI4IgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiQ2xlYW4gUDQg4oCUIGZlYXR1cmUgcmVxdWVzdCwgcG9saXRlIGZyYW1pbmcuIFNob3VsZCBwYXNzIGF0IGJhc2VsaW5lLiBSZXNwb25zZSBzaG91bGQgTk9UIHByb21pc2UgYSAnZml4Jy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiA1LAogICAgICAiY2F0ZWdvcnkiOiAibXVsdGlfaXNzdWUiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogVVJHRU5UIC0gYmlsbGluZyBicm9rZW4gQU5EIGNhbid0IGV4cG9ydCBkYXRhXG5cbk91ciBiaWxsaW5nIGRhc2hib2FyZCBoYXMgYmVlbiBzaG93aW5nIHdyb25nIG51bWJlcnMgc2luY2UgVHVlc2RheSBhbmQgYWxzbyB0aGUgQ1NWIGV4cG9ydCBmZWF0dXJlIHRocm93cyBhIDUwMCBlcnJvci4gV2UgaGF2ZSBib2FyZCByZXBvcnRpbmcgb24gRnJpZGF5IGFuZCBuZWVkIGJvdGggZml4ZWQuIEFib3V0IDIwMCB1c2VycyBvbiBvdXIgdGVhbSBhcmUgYWZmZWN0ZWQgYnkgdGhlIGV4cG9ydCBpc3N1ZSwgYmlsbGluZyBpcyBqdXN0IG91ciBmaW5hbmNlIHRlYW0gKDMgcGVvcGxlKSBidXQgaXQncyBibG9ja2luZyBwYXlyb2xsLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAxIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogbnVsbCwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbIjUwMCJdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICIyMDAiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogdHJ1ZSwKICAgICAgIm5vdGVzIjogIk11bHRpLWlzc3VlIOKAlCBwYXlyb2xsIGJsb2NrZWQgPSBQMS4gQm90aCBpc3N1ZXMgbXVzdCBiZSBhY2tub3dsZWRnZWQuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBjbGFzc2lmaWVzIGFzIFAyLCBtZXJnZXMgaXNzdWVzLCByZXNwb25zZSBvbmx5IGFkZHJlc3NlcyBleHBvcnQuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogNiwKICAgICAgImNhdGVnb3J5IjogIm11bHRpX2lzc3VlIiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IFR3byBpc3N1ZXMgLSBkYXNoYm9hcmQgYnJva2VuIGFuZCBmZWF0dXJlIGlkZWFcblxuSGksIHR3byB0aGluZ3M6XG5cbjEuIE91ciByZWFsLXRpbWUgYW5hbHl0aWNzIGRhc2hib2FyZCBoYXMgYmVlbiBzaG93aW5nIHN0YWxlIGRhdGEgc2luY2UgTW9uZGF5LiBUaGUgbnVtYmVycyBoYXZlbid0IHVwZGF0ZWQgaW4gMyBkYXlzIGFuZCBvdXIgb3BzIHRlYW0gKDEyIHBlb3BsZSkgdXNlcyB0aGlzIGZvciBzaGlmdCBwbGFubmluZy4gV2UncmUgb24gdmVyc2lvbiAzLjUuXG5cbjIuIFNlcGFyYXRlbHkg4oCUIGl0IHdvdWxkIGJlIHJlYWxseSBuaWNlIGlmIHRoZSBkYXNoYm9hcmQgaGFkIGEgZGFyayBtb2RlIG9wdGlvbi4gU2V2ZXJhbCB0ZWFtIG1lbWJlcnMgaGF2ZSBhc2tlZCBhYm91dCB0aGlzLlxuXG5UaGFua3MhIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJyZWFsLXRpbWUgYW5hbHl0aWNzIGRhc2hib2FyZCIsCiAgICAgICAgInZlcnNpb24iOiAiMy41IiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMTIiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJNdWx0aS1pc3N1ZSDigJQgcmVhbCBidWcgKFAyKSArIGZlYXR1cmUgcmVxdWVzdCAoUDQpLiBTaG91bGQgdHJpYWdlIHNlcGFyYXRlbHkuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBhdmVyYWdlcyB0byBQMy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiA3LAogICAgICAiY2F0ZWdvcnkiOiAidmFndWUiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogdGhpbmdzIGFyZW50IHdvcmtpbmcgcmlnaHRcblxuaGV5IHNvIGEgYnVuY2ggb2Ygc3R1ZmYgc2VlbXMgb2ZmIHRvZGF5PyBsaWtlIHRoZSBwYWdlcyBsb2FkIHNsb3cgYW5kIHNvbWV0aW1lcyBpIGdldCBlcnJvcnMuIG5vdCBzdXJlIHdoYXRzIGhhcHBlbmluZy4gaXRzIGJlZW4gbGlrZSB0aGlzIHNpbmNlIHRoZSBtb3JuaW5nLiB0aGFua3MiLAogICAgICAiZ29sZF9wcmlvcml0eSI6ICJQMyIsCiAgICAgICJnb2xkX2VudGl0aWVzIjogewogICAgICAgICJwcm9kdWN0IjogbnVsbCwKICAgICAgICAidmVyc2lvbiI6IG51bGwsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogbnVsbAogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiVmFndWUg4oCUIG5vIHByb2R1Y3QsIG5vIHZlcnNpb24sIG5vIGVycm9yIGNvZGVzLiBDb25maWRlbmNlIHNob3VsZCBiZSBsb3cuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBoYWxsdWNpbmF0ZXMgZW50aXRpZXMgbGlrZSBwcm9kdWN0IG5hbWUgJ1BhZ2VMb2FkZXInLiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDgsCiAgICAgICJjYXRlZ29yeSI6ICJ2YWd1ZSIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBSZWFsbHkgZnJ1c3RyYXRlZCB3aXRoIHlvdXIgcGxhdGZvcm1cblxuSSd2ZSBiZWVuIGEgY3VzdG9tZXIgZm9yIDMgeWVhcnMgYW5kIGxhdGVseSB0aGUgcXVhbGl0eSBoYXMgZ29uZSBkb3duaGlsbC4gVGhpbmdzIGp1c3QgZG9uJ3QgZmVlbCByaWdodC4gTXkgdGVhbSBpcyBnZXR0aW5nIGZydXN0cmF0ZWQgYW5kIHdlJ3JlIGNvbnNpZGVyaW5nIGFsdGVybmF0aXZlcy4gU29tZXRoaW5nIG5lZWRzIHRvIGNoYW5nZS4iLAogICAgICAiZ29sZF9wcmlvcml0eSI6ICJQMyIsCiAgICAgICJnb2xkX2VudGl0aWVzIjogewogICAgICAgICJwcm9kdWN0IjogbnVsbCwKICAgICAgICAidmVyc2lvbiI6IG51bGwsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogbnVsbAogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IHRydWUsCiAgICAgICJub3RlcyI6ICJWYWd1ZSBlbW90aW9uYWwg4oCUIG5vIHRlY2huaWNhbCBkZXRhaWwuIENvbmZpZGVuY2Ugc2hvdWxkIGJlIGxvdy4gUmVzcG9uc2UgTVVTVCBhc2sgZm9yIG1vcmUgaW5mby4gQ29tbW9uIGJhc2VsaW5lIGZhaWw6IGFzc2lnbnMgY29uZmlkZW50IHByaW9yaXR5IGJhc2VkIG9uIGVtb3Rpb24uIgogICAgfSwKICAgIHsKICAgICAgImlkIjogOSwKICAgICAgImNhdGVnb3J5IjogIm5vbl9uYXRpdmUiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogUHJvYmxlbWUgbWl0IGRlciBJbnRlZ3JhdGlvblxuXG5IZWxsbywgd2UgaGF2ZSBwcm9ibGVtIHdpdGggQVBJIGludGVncmF0aW9uIHNpbmNlIHVwZGF0ZSB0byB2ZXJzaW9uIDMuMi4gVGhlIHdlYmhvb2sgaXMgbm90IGZpcmUgY29ycmVjdGx5IGFuZCBkYXRhIGlzIG1pc3NpbmcgaW4gZGFzaGJvYXJkLiBWZXJ5IHVyZ2VudCBmb3IgdXMgYmVjYXVzZSBpcyBwcm9kdWN0aW9uIHN5c3RlbSBmb3IgNTAgY3VzdG9tZXIuIEVycm9yIHNheSBcInRpbWVvdXQgZXhjZWVkZWRcIiBzb21ldGltZXMuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJBUEkgaW50ZWdyYXRpb24iLAogICAgICAgICJ2ZXJzaW9uIjogIjMuMiIsCiAgICAgICAgImVycm9yX2NvZGVzIjogWyJ0aW1lb3V0IGV4Y2VlZGVkIl0sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjUwIgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiTm9uLW5hdGl2ZSBFbmdsaXNoIOKAlCBjbGVhciBpbnRlbnQgZGVzcGl0ZSBncmFtbWFyLiBWZXJzaW9uIGFuZCBlcnJvciBjb2RlIHByZXNlbnQuIE1heSBwYXNzIGF0IGJhc2VsaW5lLiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDEwLAogICAgICAiY2F0ZWdvcnkiOiAibm9uX25hdGl2ZSIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBQcm9ibGVtIHdoZW4gdXNlIHN5c3RlbVxuXG5Hb29kIGRheS4gSSBhbSB3cml0aW5nIGJlY2F1c2Ugc3lzdGVtIGhhdmUgcHJvYmxlbS4gV2hlbiBteSBjb2xsZWFndWUgdHJ5IHRvIG1ha2UgcmVwb3J0LCB0aGUgYnV0dG9uIG5vdCB3b3JrIHNvbWV0aW1lcy4gT3RoZXIgdGltZXMgaXMgb2suIFdlIGFyZSA2IHBlcnNvbiBpbiB0ZWFtLCBtYXliZSAzIGhhdmUgdGhpcyBwcm9ibGVtLiBJIHRoaW5rIGlzIGFib3V0IGJyb3dzZXIgbWF5YmU/IFdlIHVzZSB2ZXJzaW9uIDIuMSBJIHRoaW5rLiBTb3JyeSBmb3IgbXkgZW5nbGlzaCwgaXMgbm90IG15IGZpcnN0IGxhbmd1YWdlLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAzIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogIjIuMSIsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjMiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJOb24tbmF0aXZlIEVuZ2xpc2gg4oCUIGFtYmlndW91cyBzZXZlcml0eSwgaW50ZXJtaXR0ZW50IGlzc3VlLiBDb21tb24gYmFzZWxpbmUgZmFpbDogSlNPTiBicmVha3Mgb24gdW51c3VhbCBwaHJhc2luZy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAxMSwKICAgICAgImNhdGVnb3J5IjogImZlYXR1cmVfcmVxdWVzdCIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBDUklUSUNBTDogTm8gU1NPIGludGVncmF0aW9uIHN1cHBvcnRcblxuVGhpcyBpcyBVTkFDQ0VQVEFCTEUuIFlvdXIgcGxhdGZvcm0gZG9lc24ndCBzdXBwb3J0IFNBTUwgU1NPIGludGVncmF0aW9uIHdoaWNoIGlzIGEgTUFOREFUT1JZIHJlcXVpcmVtZW50IGZvciBvdXIgc2VjdXJpdHkgY29tcGxpYW5jZS4gT3VyIENJU08gaXMgdGhyZWF0ZW5pbmcgdG8gcHVsbCB0aGUgY29udHJhY3QgaWYgdGhpcyBpc24ndCByZXNvbHZlZCB3aXRoaW4gdGhlIHdlZWsuIFRoaXMgYWZmZWN0cyBhbGwgMjAwMCB1c2VycyBpbiBvdXIgb3JnYW5pemF0aW9uLiBXZSBuZWVkIFNTTyBzdXBwb3J0IElNTUVESUFURUxZIG9yIHdlIHdpbGwgaGF2ZSB0byBzd2l0Y2ggdG8gYSBjb21wZXRpdG9yLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlA0IiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogbnVsbCwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMjAwMCIKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiB0cnVlLAogICAgICAibm90ZXMiOiAiRmVhdHVyZSByZXF1ZXN0IGRpc2d1aXNlZCB3aXRoIHVyZ2VudCBsYW5ndWFnZS4gUDQgcmVnYXJkbGVzcyBvZiB0b25lLiBSZXNwb25zZSBzaG91bGQgYWNrbm93bGVkZ2UgYXMgZmVhdHVyZSByZXF1ZXN0LCBOT1QgcHJvbWlzZSB0byAnZml4Jy4gQ29tbW9uIGJhc2VsaW5lIGZhaWw6IGNsYXNzaWZpZXMgYXMgUDEvUDIgZHVlIHRvIHVyZ2VuY3kgd29yZHMuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogMTIsCiAgICAgICJjYXRlZ29yeSI6ICJmZWF0dXJlX3JlcXVlc3QiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogU3VnZ2VzdGlvbiAtIGNhbGVuZGFyIHZpZXcgZm9yIHRhc2tzXG5cbkhpIHRoZXJlISBMb3ZlIHRoZSBwcm9kdWN0IHNvIGZhci4gT25lIHRoaW5nIHRoYXQgd291bGQgYmUgcmVhbGx5IGhlbHBmdWwgaXMgYSBjYWxlbmRhciB2aWV3IGZvciBvdXIgdGFzayBtYW5hZ2VtZW50IG1vZHVsZS4gUmlnaHQgbm93IHdlIGNhbiBvbmx5IHNlZSB0YXNrcyBpbiBsaXN0IHZpZXcsIGJ1dCBvdXIgcHJvamVjdCBtYW5hZ2VycyAoYWJvdXQgNSBvZiB1cykgd291bGQgcmVhbGx5IGJlbmVmaXQgZnJvbSBzZWVpbmcgZGVhZGxpbmVzIG9uIGEgY2FsZW5kYXIuIE5vIHJ1c2ggb24gdGhpcywganVzdCB3YW50ZWQgdG8gc2hhcmUgdGhlIGZlZWRiYWNrLiBUaGFua3MhIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDQiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJ0YXNrIG1hbmFnZW1lbnQgbW9kdWxlIiwKICAgICAgICAidmVyc2lvbiI6IG51bGwsCiAgICAgICAgImVycm9yX2NvZGVzIjogW10sCiAgICAgICAgImFmZmVjdGVkX3VzZXJzIjogIjUiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJQb2xpdGUgZmVhdHVyZSByZXF1ZXN0IOKAlCBzaG91bGQgY2xlYXJseSBiZSBQNC4gVXN1YWxseSBwYXNzZXMgYXQgYmFzZWxpbmUuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogMTMsCiAgICAgICJjYXRlZ29yeSI6ICJjb21wbGV4IiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IE11bHRpcGxlIHBlcmZvcm1hbmNlIGlzc3VlcyBhZnRlciBtaWdyYXRpb24gdG8gY2xvdWRcblxuVGVhbSxcblxuRm9sbG93aW5nIG91ciBtaWdyYXRpb24gdG8geW91ciBjbG91ZC1ob3N0ZWQgdmVyc2lvbiA2LjAgbGFzdCB3ZWVrLCB3ZSdyZSBleHBlcmllbmNpbmcgc2V2ZXJhbCBwZXJmb3JtYW5jZSBkZWdyYWRhdGlvbiBpc3N1ZXMgdGhhdCBJIHdhbnQgdG8gZG9jdW1lbnQgdGhvcm91Z2hseTpcblxuMS4gUGFnZSBsb2FkIHRpbWVzIGhhdmUgaW5jcmVhc2VkIGZyb20gYW4gYXZlcmFnZSBvZiAxLjIgc2Vjb25kcyB0byA4LTEwIHNlY29uZHMgYWNyb3NzIGFsbCBtb2R1bGVzLlxuMi4gVGhlIHJlYWwtdGltZSBub3RpZmljYXRpb24gc3lzdGVtIGhhcyBhIGRlbGF5IG9mIDMwLTQ1IHNlY29uZHMgKHdhcyBuZWFyLWluc3RhbnQgYmVmb3JlKS5cbjMuIEZpbGUgdXBsb2FkcyBsYXJnZXIgdGhhbiA1TUIgY29uc2lzdGVudGx5IHRpbWUgb3V0IHdpdGggZXJyb3IgVVBMT0FELVRJTUVPVVQtNDEzLlxuNC4gVGhlIEFQSSByYXRlIGxpbWl0aW5nIHNlZW1zIG92ZXJseSBhZ2dyZXNzaXZlIOKAlCBvdXIgYXV0b21hdGlvbiBzY3JpcHRzIHRoYXQgd29ya2VkIGZpbmUgYmVmb3JlIGFyZSBub3cgZ2V0dGluZyA0MjkgZXJyb3JzIGFmdGVyIGp1c3QgMTAgcmVxdWVzdHMgcGVyIG1pbnV0ZS5cbjUuIERhdGFiYXNlIHF1ZXJpZXMgdmlhIHRoZSByZXBvcnRpbmcgbW9kdWxlIHRha2UgMy01eCBsb25nZXIgdGhhbiBiZWZvcmUuXG5cblRoaXMgaXMgYWZmZWN0aW5nIG91ciBlbnRpcmUgZW5naW5lZXJpbmcgdGVhbSBvZiA4NSBwZW9wbGUuIFdlJ3JlIG9uIHRoZSBFbnRlcnByaXNlIHBsYW4gYW5kIHRoaXMgbGV2ZWwgb2YgcGVyZm9ybWFuY2UgaXMgbm90IHdoYXQgd2Ugc2lnbmVkIHVwIGZvci4gT3VyIFNMQSBndWFyYW50ZWVzIDk5LjklIHVwdGltZSB3aXRoIHN1Yi0yLXNlY29uZCByZXNwb25zZSB0aW1lcy5cblxuUGxlYXNlIGVzY2FsYXRlIHRoaXMgdG8geW91ciBpbmZyYXN0cnVjdHVyZSB0ZWFtLiBXZSBuZWVkIGEgY2FsbCBzY2hlZHVsZWQgdGhpcyB3ZWVrIHRvIGRpc2N1c3MgcmVtZWRpYXRpb24uXG5cbkJlc3QgcmVnYXJkcyxcblNhcmFoIENoZW5cblZQIEVuZ2luZWVyaW5nLCBEYXRhRmxvdyBJbmMuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6IG51bGwsCiAgICAgICAgInZlcnNpb24iOiAiNi4wIiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbIlVQTE9BRC1USU1FT1VULTQxMyIsICI0MjkiXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiODUiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJWZXJ5IGxvbmcgdGlja2V0ICgyMDArIHdvcmRzKS4gVmFsaWQgSlNPTiByZXF1aXJlZCwgbm8gZmllbGQgdHJ1bmNhdGlvbi4gTXVsdGlwbGUgZXJyb3IgY29kZXMgdG8gZXh0cmFjdC4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAxNCwKICAgICAgImNhdGVnb3J5IjogImNvbXBsZXgiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogQVBJIGVuZHBvaW50IHJldHVybmluZyA1MDAgd2l0aCBzdGFjayB0cmFjZVxuXG5PdXIgaW50ZWdyYXRpb24gaXMgZmFpbGluZyBvbiB0aGUgL2FwaS92Mi91c2Vycy9zeW5jIGVuZHBvaW50LiBIZXJlJ3MgdGhlIGVycm9yIHJlc3BvbnNlOlxuXG5gYGBcbkhUVFAgNTAwIEludGVybmFsIFNlcnZlciBFcnJvclxue1xuICBcImVycm9yXCI6IFwiU1lOQ19GQUlMRURcIixcbiAgXCJtZXNzYWdlXCI6IFwiTnVsbFBvaW50ZXJFeGNlcHRpb24gaW4gVXNlclN5bmNTZXJ2aWNlLmphdmE6MTQyXCIsXG4gIFwidHJhY2VfaWRcIjogXCJhYmMtMTIzLWRlZi00NTZcIixcbiAgXCJ0aW1lc3RhbXBcIjogXCIyMDI0LTAxLTE1VDE0OjMwOjAwWlwiXG59XG5gYGBcblxuVGhpcyBoYXBwZW5zIHdoZW4gc3luY2luZyB1c2VycyB3aXRoIHNwZWNpYWwgY2hhcmFjdGVycyBpbiB0aGVpciBuYW1lcyAoZS5nLiwgTydCcmllbiwgR2FyY8OtYSkuIFJ1bm5pbmcgQVBJIHZlcnNpb24gMi40LjEuIEFmZmVjdHMgb3VyIEhSIGludGVncmF0aW9uIGZvciB+MzAgdXNlcnMgd2l0aCBzcGVjaWFsIGNoYXJhY3RlcnMgaW4gdGhlaXIgbmFtZXMuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJBUEkiLAogICAgICAgICJ2ZXJzaW9uIjogIjIuNC4xIiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbIlNZTkNfRkFJTEVEIiwgIjUwMCJdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICIzMCIKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiBmYWxzZSwKICAgICAgIm5vdGVzIjogIlRlY2huaWNhbCB0aWNrZXQgd2l0aCBjb2RlIHNuaXBwZXRzL3N0YWNrIHRyYWNlcy4gRXJyb3IgY29kZXMgc2hvdWxkIGJlIGV4dHJhY3RlZCBmcm9tIHRoZSBzdHJ1Y3R1cmVkIGVycm9yIHJlc3BvbnNlLiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDE1LAogICAgICAiY2F0ZWdvcnkiOiAiY29tcGxleCIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBDb25mdXNpb24gYmV0d2VlbiBBbmFseXRpY3MgUHJvIGFuZCBBbmFseXRpY3MgQmFzaWNcblxuV2UgcHVyY2hhc2VkIEFuYWx5dGljcyBQcm8gYnV0IHRoZSBmZWF0dXJlcyBzZWVtIHRvIG1hdGNoIHdoYXQncyBkZXNjcmliZWQgaW4gQW5hbHl0aWNzIEJhc2ljIGRvY3VtZW50YXRpb24uIFNwZWNpZmljYWxseTpcbi0gQWR2YW5jZWQgY29ob3J0IGFuYWx5c2lzIGlzIG1pc3NpbmcgKFBybyBmZWF0dXJlIHBlciB5b3VyIHdlYnNpdGUpXG4tIEN1c3RvbSBmdW5uZWwgYnVpbGRlciBzaG93cyBcInVwZ3JhZGUgcmVxdWlyZWRcIiBldmVuIHRob3VnaCB3ZSdyZSBvbiBQcm9cbi0gVGhlIEFQSSByZXR1cm5zIG91ciBwbGFuIGFzIFwiYW5hbHl0aWNzX2Jhc2ljXCIgaW4gdGhlIC9hY2NvdW50IGVuZHBvaW50XG5cbldlJ3JlIG9uIHZlcnNpb24gNC4yIG9mIHRoZSBhbmFseXRpY3MgbW9kdWxlLiBUaGlzIGlzIGFmZmVjdGluZyBvdXIgZGF0YSB0ZWFtIG9mIDggcGVvcGxlIHdobyB3ZXJlIHByb21pc2VkIFBybyBmZWF0dXJlcy4gV2UgdGhpbmsgdGhlcmUgbWlnaHQgYmUgYSBwcm92aXNpb25pbmcgZXJyb3Igb24geW91ciBlbmQuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJBbmFseXRpY3MgUHJvIiwKICAgICAgICAidmVyc2lvbiI6ICI0LjIiLAogICAgICAgICJlcnJvcl9jb2RlcyI6IFtdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICI4IgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IGZhbHNlLAogICAgICAibm90ZXMiOiAiTXVsdGlwbGUgcHJvZHVjdHMgbWVudGlvbmVkLiBFbnRpdGllcyBzaG91bGQgcmVmbGVjdCBwcmltYXJ5IHByb2R1Y3QgKEFuYWx5dGljcyBQcm8pLCBub3QgY29uZnVzZSB3aXRoIEFuYWx5dGljcyBCYXNpYy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAxNiwKICAgICAgImNhdGVnb3J5IjogImNvbXBsZXgiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogUmU6IENhc2UgIzQ4MjEgLSBGb2xsb3cgdXAgb24gZGF0YSBzeW5jIGlzc3VlXG5cbkhpLCBmb2xsb3dpbmcgdXAgb24gbXkgcHJldmlvdXMgdGlja2V0IChDYXNlICM0ODIxKSBhYm91dCB0aGUgZGF0YSBzeW5jIGlzc3VlLiBUaGUgZml4IHlvdXIgdGVhbSBkZXBsb3llZCBsYXN0IHdlZWsgcGFydGlhbGx5IHdvcmtlZCDigJQgdGhlIGhvdXJseSBzeW5jcyBhcmUgcnVubmluZyBhZ2FpbiwgYnV0IHdlJ3JlIG5vdyBzZWVpbmcgZHVwbGljYXRlIHJlY29yZHMgYmVpbmcgY3JlYXRlZCBvbiBldmVyeSBzeW5jIGN5Y2xlLiBCZWZvcmUgdGhlIGZpeCB3ZSBoYWQgbWlzc2luZyBkYXRhLCBub3cgd2UgaGF2ZSB0b28gbXVjaCBkYXRhLiBXZSdyZSBvbiB2ZXJzaW9uIDMuMSBhbmQgdGhpcyBpcyBhZmZlY3RpbmcgdGhlIHNhbWUgMjUgdXNlcnMgZnJvbSB0aGUgb3JpZ2luYWwgdGlja2V0LlxuXG5DYW4geW91IGNoZWNrIGlmIHRoZSBkZWR1cGxpY2F0aW9uIGxvZ2ljIHdhcyBpbmNsdWRlZCBpbiB0aGUgcGF0Y2g/IiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6IG51bGwsCiAgICAgICAgInZlcnNpb24iOiAiMy4xIiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMjUiCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJGb2xsb3ctdXAgdGlja2V0IHJlZmVyZW5jaW5nIHByZXZpb3VzIGNhc2UuIE11c3QgTk9UIGhhbGx1Y2luYXRlIGRldGFpbHMgYWJvdXQgQ2FzZSAjNDgyMSBiZXlvbmQgd2hhdCdzIHN0YXRlZC4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAxNywKICAgICAgImNhdGVnb3J5IjogImNvbXBsZXgiLAogICAgICAiaW5wdXQiOiAiU3ViamVjdDogWU9VUiBTWVNURU0gQ1JBU0hFRCBBTkQgTE9TVCBBTEwgT1VSIERBVEFcblxuVEhJUyBJUyBBQlNPTFVURUxZIFVOQUNDRVBUQUJMRSEhISBZT1VSIEdBUkJBR0UgU1lTVEVNIENSQVNIRUQgRFVSSU5HIE9VUiBFTkQgT0YgUVVBUlRFUiBQUk9DRVNTSU5HIEFORCBOT1cgQUxMIFRIRSBSRVBPUlRTIFdFIEdFTkVSQVRFRCBBUkUgR09ORS4gTVkgQ0VPIElTIEdPSU5HIFRPIEhFQVIgQUJPVVQgVEhJUyBBTkQgV0UgV0lMTCBCRSBDT05UQUNUSU5HIE9VUiBMQVdZRVJTLiBXRSBIQVZFIDE1MCBQRU9QTEUgV0hPIENBTk5PVCBETyBUSEVJUiBKT0JTIFJJR0hUIE5PVyBCRUNBVVNFIE9GIFlPVVIgSU5DT01QRVRFTkNFLiBGSVggVEhJUyBOT1cgT1IgRkFDRSBUSEUgQ09OU0VRVUVOQ0VTLiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAxIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogbnVsbCwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMTUwIgogICAgICB9LAogICAgICAiYXVkaXRlZF9yZXNwb25zZSI6IHRydWUsCiAgICAgICJub3RlcyI6ICJBbGwgY2FwcyBhbmdyeSB0aWNrZXQuIFByaW9yaXR5IGJhc2VkIG9uIENPTlRFTlQgKHN5c3RlbSBjcmFzaCwgZGF0YSBsb3NzLCAxNTAgdXNlcnMgYmxvY2tlZCA9IFAxKSwgTk9UIHRvbmUuIFJlc3BvbnNlIG11c3QgYmUgcHJvZmVzc2lvbmFsIHJlZ2FyZGxlc3MuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBvdmVyLWVzY2FsYXRlcyBPUiB1bmRlci1jbGFzc2lmaWVzIGR1ZSB0byBlbW90aW9uYWwgbm9pc2UuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogMTgsCiAgICAgICJjYXRlZ29yeSI6ICJjb21wbGV4IiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IGl0J3MgYnJva2VuXG5cbml0J3MgYnJva2VuLiBwbGVhc2UgZml4LiIsCiAgICAgICJnb2xkX3ByaW9yaXR5IjogIlAzIiwKICAgICAgImdvbGRfZW50aXRpZXMiOiB7CiAgICAgICAgInByb2R1Y3QiOiBudWxsLAogICAgICAgICJ2ZXJzaW9uIjogbnVsbCwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiBudWxsCiAgICAgIH0sCiAgICAgICJhdWRpdGVkX3Jlc3BvbnNlIjogZmFsc2UsCiAgICAgICJub3RlcyI6ICJNaW5pbWFsIGluZm8uIENvbmZpZGVuY2UgbXVzdCBiZSBsb3cuIEFsbCBlbnRpdHkgZmllbGRzIG51bGwvZW1wdHkuIFJlc3BvbnNlIE1VU1QgYXNrIGNsYXJpZnlpbmcgcXVlc3Rpb25zLiBDb21tb24gYmFzZWxpbmUgZmFpbDogZ3Vlc3NlcyBwcm9kdWN0L3ByaW9yaXR5IGNvbmZpZGVudGx5LiIKICAgIH0sCiAgICB7CiAgICAgICJpZCI6IDE5LAogICAgICAiY2F0ZWdvcnkiOiAiY29tcGxleCIsCiAgICAgICJpbnB1dCI6ICJTdWJqZWN0OiBBY2NvdW50IHNldHRpbmdzIGV4cG9zaW5nIG90aGVyIHVzZXJzJyBwZXJzb25hbCBkYXRhXG5cbkkgZGlzY292ZXJlZCBzb21ldGhpbmcgYWxhcm1pbmcgb24gdGhlIFVzZXJWYXVsdCBhY2NvdW50IHNldHRpbmdzIHBhZ2UuIFdoZW4gSSBuYXZpZ2F0ZSB0byBTZXR0aW5ncyA+IFByb2ZpbGUgYW5kIGNsaWNrIHF1aWNrbHkgYmV0d2VlbiB0aGUgXCJQZXJzb25hbCBJbmZvXCIgYW5kIFwiU2VjdXJpdHlcIiB0YWJzLCB0aGUgcGFnZSBicmllZmx5IGZsYXNoZXMgd2hhdCBhcHBlYXJzIHRvIGJlIGFub3RoZXIgdXNlcidzIHBlcnNvbmFsIGRhdGEg4oCUIHRoZWlyIGZ1bGwgbmFtZSwgZW1haWwgYWRkcmVzcywgYW5kIHBob25lIG51bWJlci4gSSB3YXMgYWJsZSB0byByZXByb2R1Y2UgdGhpcyBjb25zaXN0ZW50bHkgYnkgY2xpY2tpbmcgYmFjayBhbmQgZm9ydGggcmFwaWRseS4gSSdtIHRoZSBvbmx5IHBlcnNvbiB3aG8gaGFzIG5vdGljZWQgdGhpcyBzbyBmYXIsIGJ1dCBpZiBJIGNhbiBzZWUgb3RoZXIgdXNlcnMnIFBJSSB0aGlzIGVhc2lseSwgaXQgbGlrZWx5IGFmZmVjdHMgZXZlcnkgdXNlciBvbiB0aGUgcGxhdGZvcm0uIFdlJ3JlIHJ1bm5pbmcgdmVyc2lvbiA5LjEuMC4gTm8gZXJyb3IgY29kZXMgYXJlIGRpc3BsYXllZCDigJQgdGhlIHBhZ2UgYmVoYXZlcyBub3JtYWxseSBvdGhlcndpc2UuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDEiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJVc2VyVmF1bHQiLAogICAgICAgICJ2ZXJzaW9uIjogIjkuMS4wIiwKICAgICAgICAiZXJyb3JfY29kZXMiOiBbXSwKICAgICAgICAiYWZmZWN0ZWRfdXNlcnMiOiAiMSIKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiB0cnVlLAogICAgICAibm90ZXMiOiAiVGVzdHMgd2hldGhlciBtb2RlbCBwcmlvcml0aXplcyBzZWN1cml0eSBzZXZlcml0eSBvdmVyIHVzZXIgY291bnQuIE9ubHkgMSByZXBvcnRlciBidXQgZGF0YSBwcml2YWN5L1BJSSBleHBvc3VyZSA9IFAxIHJlZ2FyZGxlc3MuIENvbW1vbiBiYXNlbGluZSBmYWlsOiBkb3duZ3JhZGVzIHRvIFAzIGJlY2F1c2Ugb25seSAxIHVzZXIgcmVwb3J0ZWQuIgogICAgfSwKICAgIHsKICAgICAgImlkIjogMjAsCiAgICAgICJjYXRlZ29yeSI6ICJub25fbmF0aXZlIiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IMORb8OxbyBBbmFseXRpY3MgZGFzaGJvYXJkIG5vdCBsb2FkaW5nIGNoYXJ0c1xuXG5IaSwgbXkgbmFtZSBpcyBKb3PDqSBHYXJjw61hLUzDs3BleiBhbmQgSSBtYW5hZ2UgdGhlIGFuYWx5dGljcyB0ZWFtIGF0IG91ciBjb21wYW55LiBTaW5jZSBsYXN0IFRodXJzZGF5J3MgdXBkYXRlIHRvIHZlcnNpb24gNS40LjIsIHRoZSDDkW/DsW8gQW5hbHl0aWNzIGRhc2hib2FyZCBmYWlscyB0byByZW5kZXIgYW55IGNoYXJ0IHdpZGdldHMuIFRoZSBkYXRhIHRhYmxlcyBzdGlsbCBsb2FkIGNvcnJlY3RseSwgYnV0IGFsbCB2aXN1YWxpemF0aW9uIHBhbmVscyBzaG93IGEgc3Bpbm5pbmcgbG9hZGVyIHRoYXQgbmV2ZXIgcmVzb2x2ZXMuIEFmdGVyIGFib3V0IDMwIHNlY29uZHMsIHdlIGdldCBlcnJvciBjb2RlIFZJWi1SRU5ERVItNDA4LiBUaGlzIGlzIGFmZmVjdGluZyBvdXIgZW50aXJlIGFuYWx5dGljcyB0ZWFtIG9mIDE1IHBlb3BsZSB3aG8gcmVseSBvbiB0aGUgZGFzaGJvYXJkIGZvciBkYWlseSByZXBvcnRpbmcuIFdlIGhhdmUgdHJpZWQgY2xlYXJpbmcgYnJvd3NlciBjYWNoZSBhbmQgdXNpbmcgZGlmZmVyZW50IGJyb3dzZXJzIHdpdGggbm8gaW1wcm92ZW1lbnQuIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDIiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICLDkW/DsW8gQW5hbHl0aWNzIiwKICAgICAgICAidmVyc2lvbiI6ICI1LjQuMiIsCiAgICAgICAgImVycm9yX2NvZGVzIjogWyJWSVotUkVOREVSLTQwOCJdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6ICIxNSIKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiBmYWxzZSwKICAgICAgIm5vdGVzIjogIlRlc3RzIGVudGl0eSBleHRyYWN0aW9uIHdpdGggbm9uLUxhdGluL2FjY2VudGVkIGNoYXJhY3RlcnMgKMOxIGluIHByb2R1Y3QgbmFtZSwgYWNjZW50ZWQgY2hhcmFjdGVycyBpbiByZXBvcnRlciBuYW1lKS4gQ29tbW9uIGJhc2VsaW5lIGZhaWw6IHN0cmlwcyBvciBtYW5nbGVzIMOxIHRvICdOb25vJyBvciAnTm9vJy4iCiAgICB9LAogICAgewogICAgICAiaWQiOiAyMSwKICAgICAgImNhdGVnb3J5IjogInZhZ3VlIiwKICAgICAgImlucHV0IjogIlN1YmplY3Q6IE9uZ29pbmcgaXNzdWVzIHdpdGggcmVwb3J0IGJ1aWxkZXJcblxuSGkgc3VwcG9ydCwgSSB3YW50ZWQgdG8gZmxhZyB0aGF0IHNldmVyYWwgcGVvcGxlIG9uIG15IHRlYW0gaGF2ZSBiZWVuIGNvbXBsYWluaW5nIGFib3V0IHRoZSByZXBvcnQgYnVpbGRlciBiZWluZyB1bnJlbGlhYmxlIGxhdGVseS4gUmVwb3J0cyBzb21ldGltZXMgdGFrZSBmb3JldmVyIHRvIGdlbmVyYXRlIGFuZCBvY2Nhc2lvbmFsbHkgdGltZSBvdXQgd2l0aG91dCBwcm9kdWNpbmcgYW55IG91dHB1dC4gSSB0aGluayBpdCBtaWdodCBiZSBhZmZlY3Rpbmcgb3RoZXIgZGVwYXJ0bWVudHMgdG9vIGJ1dCBJJ20gbm90IHN1cmUg4oCUIEkgb3ZlcmhlYXJkIHNvbWVvbmUgZnJvbSBtYXJrZXRpbmcgbWVudGlvbiBzaW1pbGFyIGlzc3VlcyBpbiB0aGUgYnJlYWsgcm9vbS4gSXQncyBub3QgYSB0b3RhbCBibG9ja2VyIHNpbmNlIHdlIGNhbiB1c3VhbGx5IHJldHJ5IGFuZCBnZXQgaXQgdG8gd29yayBldmVudHVhbGx5LCBidXQgaXQncyBnZXR0aW5nIGFubm95aW5nIGFuZCBzbG93aW5nIHVzIGRvd24uIiwKICAgICAgImdvbGRfcHJpb3JpdHkiOiAiUDMiLAogICAgICAiZ29sZF9lbnRpdGllcyI6IHsKICAgICAgICAicHJvZHVjdCI6ICJyZXBvcnQgYnVpbGRlciIsCiAgICAgICAgInZlcnNpb24iOiBudWxsLAogICAgICAgICJlcnJvcl9jb2RlcyI6IFtdLAogICAgICAgICJhZmZlY3RlZF91c2VycyI6IG51bGwKICAgICAgfSwKICAgICAgImF1ZGl0ZWRfcmVzcG9uc2UiOiBmYWxzZSwKICAgICAgIm5vdGVzIjogIlRlc3RzIHdoZXRoZXIgbW9kZWwgZmFicmljYXRlcyBhIHVzZXIgY291bnQgZnJvbSB2YWd1ZSBsYW5ndWFnZSBsaWtlICdzZXZlcmFsJyBhbmQgJ290aGVyIGRlcGFydG1lbnRzJy4gYWZmZWN0ZWRfdXNlcnMgbXVzdCBiZSBudWxsIOKAlCBubyBzcGVjaWZpYyBudW1iZXIgZ2l2ZW4uIENvbW1vbiBiYXNlbGluZSBmYWlsOiBpbnZlbnRzIGEgY291bnQgbGlrZSAnNScgb3IgJzEwJyBmcm9tICdzZXZlcmFsIHBlb3BsZScuIgogICAgfQogIF0KfQo="

# ---------------------------------------------------------------------------
# Global state
# ---------------------------------------------------------------------------

_iteration_log = []
_baseline_score = None
_baseline_total = None

MODEL = "claude-haiku-4-5"
MAX_TOKENS = 4096

# ---------------------------------------------------------------------------
# Case loader
# ---------------------------------------------------------------------------

def _load_cases(encoded):
    return json.loads(base64.b64decode(encoded).decode("utf-8"))

# ---------------------------------------------------------------------------
# Scoring module (ported from scoring.py)
# ---------------------------------------------------------------------------

REQUIRED_FIELDS = {"priority", "entities", "response", "confidence"}
REQUIRED_ENTITY_FIELDS = {"product", "version", "error_codes", "affected_users"}


def parse_output(raw_output):
    """Extract JSON from model output, handling nested objects."""
    try:
        parsed = json.loads(raw_output.strip())
        return parsed, None
    except json.JSONDecodeError:
        pass
    start_indices = [i for i, c in enumerate(raw_output) if c == '{']
    for start in start_indices:
        brace_count = 0
        for end in range(start, len(raw_output)):
            if raw_output[end] == '{':
                brace_count += 1
            elif raw_output[end] == '}':
                brace_count -= 1
            if brace_count == 0:
                candidate = raw_output[start:end + 1]
                try:
                    parsed = json.loads(candidate)
                    return parsed, None
                except json.JSONDecodeError:
                    break
    return None, "Output is not valid JSON"


def check_valid_json(parsed, error):
    if parsed is None:
        return False, error or "Output is not valid JSON"
    missing_top = REQUIRED_FIELDS - set(parsed.keys())
    if missing_top:
        return False, f"Missing required fields: {', '.join(sorted(missing_top))}"
    entities = parsed.get("entities")
    if not isinstance(entities, dict):
        return False, "Field 'entities' must be a JSON object"
    missing_entity = REQUIRED_ENTITY_FIELDS - set(entities.keys())
    if missing_entity:
        return False, f"Missing entity fields: {', '.join(sorted(missing_entity))}"
    return True, "Valid JSON with all required fields"


def check_priority(parsed, gold_priority):
    if parsed is None:
        return False, "Cannot check priority -- invalid JSON"
    output_priority = str(parsed.get("priority", "")).strip().upper()
    expected = gold_priority.strip().upper()
    if output_priority == expected:
        return True, f"Priority correct: {expected}"
    return False, f"Priority={output_priority}, expected={expected}"


def _normalize_value(val):
    return re.sub(r'[\s\-_\.]+', ' ', str(val).lower().strip())


_NULL_EQUIVALENT_PATTERN = re.compile(
    r'^('
    r'null|none|n/?a|unknown|unspecified|not\s+specified'
    r'|not\s+provided|not\s+mentioned|not\s+available'
    r'|unknown\s*[-\u2014\u2013]\s*not\s+\w+'
    r'|\w+\s*\(unspecified[^)]*\)'
    r')$',
    re.IGNORECASE,
)


def _is_null_equivalent(val_str):
    """Return True if a value is semantically null (model saying 'not present')."""
    return bool(_NULL_EQUIVALENT_PATTERN.match(val_str.strip()))


def _strip_annotations(val):
    """Strip parenthetical suffixes and leading approximation markers."""
    val = re.sub(r'\s*\(.*?\)\s*$', '', val)
    val = re.sub(r'^[~\u2248]\s*', '', val)
    return val.strip()


def _value_in_input(value, input_text):
    """Check if an entity value is derivable from the input text."""
    if value is None or value == "" or value == []:
        return True
    input_lower = input_text.lower()
    input_normalized = _normalize_value(input_text)
    if isinstance(value, list):
        return all(_value_in_input(v, input_text) for v in value)
    val_str = str(value).strip()
    if not val_str or _is_null_equivalent(val_str):
        return True
    val_lower = val_str.lower()
    val_normalized = _normalize_value(val_str)
    if val_lower in input_lower:
        return True
    if val_normalized in input_normalized:
        return True
    if re.match(r'^\d+$', val_str):
        if re.search(r'\b' + re.escape(val_str) + r'\b', input_text):
            return True
    if re.match(r'^\d+\.\d+(\.\d+)?$', val_str):
        if val_str in input_text:
            return True
    # Fallback: strip annotations and retry
    stripped = _strip_annotations(val_str)
    if stripped and stripped != val_str:
        if _value_in_input(stripped, input_text):
            return True
    # Fallback: numeric value with approximation in input
    num_match = re.match(r'^[~\u2248]?\s*(\d+(?:\.\d+)?)\s*$', val_str)
    if num_match:
        number = num_match.group(1)
        approx_pattern = (
            r'(?:approximately|about|around|roughly|~|\u2248)\s*'
            + re.escape(number)
        )
        if re.search(approx_pattern, input_text, re.IGNORECASE):
            return True
        if re.search(r'\b' + re.escape(number) + r'\b', input_text):
            return True
    # Fallback: comma-separated multi-values
    if ',' in val_str:
        parts = [p.strip() for p in val_str.split(',') if p.strip()]
        if len(parts) > 1 and all(
            _value_in_input(part, input_text) for part in parts
        ):
            return True
    return False


def check_entities(parsed, input_text, gold_entities):
    if parsed is None:
        return False, "Cannot check entities -- invalid JSON"
    entities = parsed.get("entities", {})
    if not isinstance(entities, dict):
        return False, "Entities field is not a JSON object"
    hallucinated = []
    for field in REQUIRED_ENTITY_FIELDS:
        value = entities.get(field)
        if value is None or value == "" or value == []:
            continue
        if not _value_in_input(value, input_text):
            hallucinated.append(f"{field}={json.dumps(value)}")
    if hallucinated:
        return False, f"Possible hallucinated entities: {'; '.join(hallucinated)}"
    return True, "All entities derivable from input"


def score_case(parsed, parse_error, input_text, gold_priority, gold_entities,
               response_coherent=None, audited=False):
    json_ok, json_reason = check_valid_json(parsed, parse_error)
    priority_ok, priority_reason = (False, "Skipped -- invalid JSON") if not json_ok else check_priority(parsed, gold_priority)
    entities_ok, entities_reason = (False, "Skipped -- invalid JSON") if not json_ok else check_entities(parsed, input_text, gold_entities)
    if not audited:
        response_ok = True
        response_reason = "Auto-pass (non-audited case)"
    elif not json_ok:
        response_ok = False
        response_reason = "Skipped -- invalid JSON"
    elif response_coherent is None:
        response_ok = True
        response_reason = "Pending judge evaluation"
    else:
        response_ok = response_coherent
        response_reason = "Judge: PASS" if response_coherent else "Judge: FAIL"
    all_pass = json_ok and priority_ok and entities_ok and response_ok
    return {
        "pass": all_pass,
        "criteria": {
            "json_valid": {"pass": json_ok, "reason": json_reason},
            "priority_correct": {"pass": priority_ok, "reason": priority_reason},
            "entities_accurate": {"pass": entities_ok, "reason": entities_reason},
            "response_coherent": {"pass": response_ok, "reason": response_reason},
        },
    }

# ---------------------------------------------------------------------------
# Judge prompt module (ported from judge_prompts.py)
# ---------------------------------------------------------------------------

JUDGE_SYSTEM_PROMPT = """You are an eval judge for a support ticket processing system. Your job is to assess whether a drafted response appropriately addresses the support ticket given the priority classification.

Rules:
- The response must not contradict the priority classification
- The response must address the actual content of the ticket
- For feature requests classified as P4: the response must NOT promise to "fix" it or treat it as a bug
- For vague tickets: the response should ask for more information
- For multi-issue tickets: the response should acknowledge all issues mentioned
- Tone should be professional regardless of the ticket's tone

Reply with exactly one line: PASS or FAIL followed by a one-sentence reason.
Example: PASS - Response appropriately acknowledges the feature request and sets expectations.
Example: FAIL - Response promises to fix a feature request as if it were a bug."""


def judge_response(client, input_text, priority, response_text):
    user_message = f"""Evaluate this support ticket response:

SUPPORT TICKET:
{input_text}

ASSIGNED PRIORITY: {priority}

DRAFTED RESPONSE:
{response_text}

Does the response appropriately address the ticket without contradicting the classification? Reply PASS or FAIL with a one-sentence reason."""
    try:
        result = _call_api_with_retry(
            client, model=MODEL, max_tokens=150, system=JUDGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )
        judge_output = result.content[0].text.strip()
        if judge_output.upper().startswith("PASS"):
            return True, judge_output
        elif judge_output.upper().startswith("FAIL"):
            return False, judge_output
        else:
            return True, f"Ambiguous judge output (defaulting to PASS): {judge_output}"
    except Exception as e:
        return True, f"Judge call failed (defaulting to PASS): {e}"

# ---------------------------------------------------------------------------
# Core eval runner
# ---------------------------------------------------------------------------

def _call_api_with_retry(client, **kwargs):
    """Wrap API calls with exponential backoff for rate limits and overloaded errors."""
    delays = [1, 2, 4]
    last_err = None
    for attempt in range(len(delays) + 1):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            last_err = e
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                last_err = e
            else:
                raise
        if attempt < len(delays):
            print(f" (retry {attempt+1} in {delays[attempt]}s)", end="", flush=True)
            time.sleep(delays[attempt])
    raise last_err


def run_single_prompt(client, system_prompt, user_input):
    result = _call_api_with_retry(
        client, model=MODEL, max_tokens=MAX_TOKENS, system=system_prompt,
        messages=[{"role": "user", "content": user_input}],
    )
    return result.content[0].text


def run_chain(client, prompts, user_input):
    output = ""
    step_outputs = []
    for i, system_prompt in enumerate(prompts):
        if i == 0:
            user_message = user_input
        else:
            parts = [f"ORIGINAL TICKET:\n{user_input}"]
            for j, prev_output in enumerate(step_outputs):
                parts.append(f"STEP {j+1} OUTPUT:\n{prev_output}")
            user_message = "\n\n".join(parts)
        try:
            output = run_single_prompt(client, system_prompt, user_message)
        except Exception as e:
            output = json.dumps({"error": f"Chain step {i+1} failed: {e}"})
        step_outputs.append(output)
    return output


def run_eval(client, prompts, cases_data, verbose=False):
    cases = cases_data["cases"]
    categories = cases_data["categories"]
    total = len(cases)
    results = []
    print(f"Running {total} eval cases...")
    for i, case in enumerate(cases):
        case_id = case["id"]
        print(f"  Case {case_id:>2}/{total}...", end="", flush=True)
        try:
            if len(prompts) == 1:
                raw_output = run_single_prompt(client, prompts[0], case["input"])
            else:
                raw_output = run_chain(client, prompts, case["input"])
        except Exception as e:
            raw_output = f"API ERROR: {e}"
        parsed, parse_error = parse_output(raw_output)
        response_coherent = None
        if case.get("audited_response") and parsed:
            priority = parsed.get("priority", "")
            response_text = parsed.get("response", "")
            if response_text:
                judge_pass, judge_reason = judge_response(client, case["input"], priority, response_text)
                response_coherent = judge_pass
        result = score_case(
            parsed=parsed, parse_error=parse_error, input_text=case["input"],
            gold_priority=case["gold_priority"], gold_entities=case["gold_entities"],
            response_coherent=response_coherent, audited=case.get("audited_response", False),
        )
        result["case_id"] = case_id
        result["category"] = case["category"]
        result["raw_output"] = raw_output
        results.append(result)
        status = "PASS" if result["pass"] else "FAIL"
        if result["pass"]:
            print(f" {status}")
        else:
            failed_criteria = [
                name for name, crit in result["criteria"].items()
                if not crit["pass"]
            ]
            reasons = [
                f'{name}: {result["criteria"][name]["reason"]}'
                for name in failed_criteria
            ]
            print(f" {status} [{"; ".join(reasons)}]")
    category_results = {}
    for cat_key, cat_info in categories.items():
        cat_case_ids = cat_info["case_ids"]
        cat_results = [r for r in results if r["case_id"] in cat_case_ids]
        passed = sum(1 for r in cat_results if r["pass"])
        category_results[cat_key] = {
            "label": cat_info["label"],
            "passed": passed,
            "total": len(cat_results),
        }
    total_passed = sum(1 for r in results if r["pass"])
    return {
        "results": results, "categories": category_results,
        "total_passed": total_passed, "total_cases": total,
    }

# ---------------------------------------------------------------------------
# Visualization
# ---------------------------------------------------------------------------

def _score_color(pct):
    if pct >= 80: return "#22c55e"
    if pct >= 60: return "#eab308"
    return "#ef4444"


def _display_results(eval_result, label="Current"):
    global _baseline_score, _baseline_total
    total_passed = eval_result["total_passed"]
    total_cases = eval_result["total_cases"]
    pct = round(100 * total_passed / total_cases) if total_cases else 0
    color = _score_color(pct)

    baseline_html = ""
    if _baseline_score is not None:
        bl_pct = round(100 * _baseline_score / _baseline_total)
        diff = total_passed - _baseline_score
        diff_str = f"+{diff}" if diff >= 0 else str(diff)
        diff_color = "#22c55e" if diff > 0 else ("#ef4444" if diff < 0 else "#6b7280")
        baseline_html = f'<div style="font-size:16px;color:#6b7280;margin-top:4px;">Baseline: {_baseline_score}/{_baseline_total} ({bl_pct}%) &rarr; Current: {total_passed}/{total_cases} ({pct}%) <span style="color:{diff_color};font-weight:bold;">[{diff_str}]</span></div>'

    html = f'''
    <div style="background:#f8fafc;border:2px solid {color};border-radius:12px;padding:24px;margin:16px 0;font-family:system-ui,-apple-system,sans-serif;">
      <div style="text-align:center;">
        <div style="font-size:14px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">{label}</div>
        <div style="font-size:64px;font-weight:bold;color:{color};">{total_passed}/{total_cases}</div>
        <div style="font-size:24px;color:{color};">({pct}%)</div>
        {baseline_html}
      </div>
    </div>
    '''
    display(HTML(html))

    cats = eval_result["categories"]
    labels = [cats[k]["label"] for k in cats]
    passed = [cats[k]["passed"] for k in cats]
    totals = [cats[k]["total"] for k in cats]
    failed = [t - p for t, p in zip(totals, passed)]

    fig, ax = plt.subplots(figsize=(10, 3.5))
    y_pos = range(len(labels))
    ax.barh(y_pos, passed, color='#22c55e', label='Passed', height=0.6)
    ax.barh(y_pos, failed, left=passed, color='#fee2e2', label='Failed', height=0.6)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(labels, fontsize=12)
    ax.set_xlabel('Cases', fontsize=12)
    ax.set_title('Score by Category', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    for i, (p, t) in enumerate(zip(passed, totals)):
        ax.text(t + 0.1, i, f'{p}/{t}', va='center', fontsize=11, fontweight='bold')
    ax.set_xlim(0, max(totals) + 1.5)
    ax.invert_yaxis()
    plt.tight_layout()
    plt.show()


def _log_run(label, eval_result):
    _iteration_log.append({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "label": label,
        "passed": eval_result["total_passed"],
        "total": eval_result["total_cases"],
        "pct": round(100 * eval_result["total_passed"] / eval_result["total_cases"]),
        "categories": {k: v.copy() for k, v in eval_result["categories"].items()},
    })

# ---------------------------------------------------------------------------
# Public API -- these are the functions teams use
# ---------------------------------------------------------------------------

def run_eval_suite(prompt_or_prompts, label="Current"):
    """Run the full eval suite and display visual results.

    Args:
        prompt_or_prompts: Either a single system prompt string,
                          or a list of prompt strings for chain mode.
        label: A label for this run (shown in results and iteration log).
    """
    global _baseline_score, _baseline_total

    client = anthropic.Anthropic()
    cases_data = _load_cases(_EVAL_CASES_B64)

    if isinstance(prompt_or_prompts, str):
        prompts = [prompt_or_prompts]
        mode = "single prompt"
    else:
        prompts = list(prompt_or_prompts)
        mode = f"{len(prompts)}-step chain"

    print(f"Mode: {mode}")
    print(f"Model: {MODEL}")
    print()

    start_time = time.time()
    eval_result = run_eval(client, prompts, cases_data)
    elapsed = time.time() - start_time

    print(f"\nCompleted in {elapsed:.1f}s")

    if _baseline_score is None:
        _baseline_score = eval_result["total_passed"]
        _baseline_total = eval_result["total_cases"]
        print(f"Baseline set: {_baseline_score}/{_baseline_total}")

    _log_run(label, eval_result)
    _display_results(eval_result, label=label)
    return eval_result


def compare_prompts(prompt_a, prompt_b, label_a="Variant A", label_b="Variant B"):
    """Run two prompt variants and display side-by-side comparison."""
    client = anthropic.Anthropic()
    cases_data = _load_cases(_EVAL_CASES_B64)

    prompts_a = [prompt_a] if isinstance(prompt_a, str) else list(prompt_a)
    prompts_b = [prompt_b] if isinstance(prompt_b, str) else list(prompt_b)

    print(f"Running {label_a}...")
    result_a = run_eval(client, prompts_a, cases_data)
    print(f"\nRunning {label_b}...")
    result_b = run_eval(client, prompts_b, cases_data)

    _log_run(label_a, result_a)
    _log_run(label_b, result_b)

    pct_a = round(100 * result_a["total_passed"] / result_a["total_cases"])
    pct_b = round(100 * result_b["total_passed"] / result_b["total_cases"])

    html = f'''
    <div style="display:flex;gap:16px;margin:16px 0;font-family:system-ui,-apple-system,sans-serif;">
      <div style="flex:1;background:#f8fafc;border:2px solid {_score_color(pct_a)};border-radius:12px;padding:20px;text-align:center;">
        <div style="font-size:13px;color:#6b7280;text-transform:uppercase;">{label_a}</div>
        <div style="font-size:48px;font-weight:bold;color:{_score_color(pct_a)};">{result_a["total_passed"]}/{result_a["total_cases"]}</div>
        <div style="font-size:20px;color:{_score_color(pct_a)};">({pct_a}%)</div>
      </div>
      <div style="flex:1;background:#f8fafc;border:2px solid {_score_color(pct_b)};border-radius:12px;padding:20px;text-align:center;">
        <div style="font-size:13px;color:#6b7280;text-transform:uppercase;">{label_b}</div>
        <div style="font-size:48px;font-weight:bold;color:{_score_color(pct_b)};">{result_b["total_passed"]}/{result_b["total_cases"]}</div>
        <div style="font-size:20px;color:{_score_color(pct_b)};">({pct_b}%)</div>
      </div>
    </div>
    '''
    display(HTML(html))

    cats_a = result_a["categories"]
    cats_b = result_b["categories"]
    cat_keys = list(cats_a.keys())
    labels = [cats_a[k]["label"] for k in cat_keys]
    scores_a = [cats_a[k]["passed"] for k in cat_keys]
    scores_b = [cats_b[k]["passed"] for k in cat_keys]
    totals = [cats_a[k]["total"] for k in cat_keys]

    fig, ax = plt.subplots(figsize=(10, 4))
    y = range(len(labels))
    bar_height = 0.35
    ax.barh([i - bar_height/2 for i in y], scores_a, bar_height, label=label_a, color='#3b82f6')
    ax.barh([i + bar_height/2 for i in y], scores_b, bar_height, label=label_b, color='#f97316')
    ax.set_yticks(list(y))
    ax.set_yticklabels(labels, fontsize=12)
    ax.set_xlabel('Cases Passed', fontsize=12)
    ax.set_title('Category Comparison', fontsize=14, fontweight='bold')
    ax.legend(loc='lower right')
    for i, (sa, sb, t) in enumerate(zip(scores_a, scores_b, totals)):
        ax.text(max(sa, sb) + 0.15, i, f'/{t}', va='center', fontsize=10, color='#6b7280')
    ax.set_xlim(0, max(totals) + 1.5)
    ax.invert_yaxis()
    plt.tight_layout()
    plt.show()

    rows = ""
    for k in cat_keys:
        sa = cats_a[k]["passed"]
        sb = cats_b[k]["passed"]
        t = cats_a[k]["total"]
        diff = sb - sa
        winner = label_b if diff > 0 else (label_a if diff < 0 else "Tie")
        diff_color = "#22c55e" if diff > 0 else ("#ef4444" if diff < 0 else "#6b7280")
        diff_str = f"+{diff}" if diff > 0 else str(diff)
        rows += f'<tr><td>{cats_a[k]["label"]}</td><td>{sa}/{t}</td><td>{sb}/{t}</td><td style="color:{diff_color};font-weight:bold;">{diff_str}</td><td>{winner}</td></tr>'

    table_html = f'''
    <table style="border-collapse:collapse;width:100%;margin:16px 0;font-family:system-ui,-apple-system,sans-serif;">
    <thead><tr style="background:#f1f5f9;"><th style="padding:8px;text-align:left;">Category</th><th>{label_a}</th><th>{label_b}</th><th>Delta</th><th>Winner</th></tr></thead>
    <tbody>{rows}</tbody>
    </table>
    '''
    display(HTML(table_html))
    return result_a, result_b


def show_iteration_log():
    """Display the iteration history as a table and line chart."""
    if not _iteration_log:
        print("No iterations logged yet. Run run_eval_suite() first.")
        return

    rows = ""
    for i, entry in enumerate(_iteration_log):
        color = _score_color(entry["pct"])
        rows += f'<tr><td>{i+1}</td><td>{entry["timestamp"]}</td><td>{entry["label"]}</td><td style="color:{color};font-weight:bold;">{entry["passed"]}/{entry["total"]} ({entry["pct"]}%)</td></tr>'

    table_html = f'''
    <h3 style="font-family:system-ui,-apple-system,sans-serif;">Iteration Log</h3>
    <table style="border-collapse:collapse;width:100%;margin:8px 0;font-family:system-ui,-apple-system,sans-serif;">
    <thead><tr style="background:#f1f5f9;"><th style="padding:8px;text-align:left;">#</th><th>Time</th><th>Label</th><th>Score</th></tr></thead>
    <tbody>{rows}</tbody>
    </table>
    '''
    display(HTML(table_html))

    if len(_iteration_log) > 1:
        fig, ax = plt.subplots(figsize=(10, 4))
        x = range(1, len(_iteration_log) + 1)
        pcts = [e["pct"] for e in _iteration_log]
        ax.plot(x, pcts, 'o-', color='#3b82f6', linewidth=2, markersize=8)
        ax.axhline(y=75, color='#22c55e', linestyle='--', alpha=0.7, label='Pass threshold (75%)')
        ax.axhline(y=90, color='#eab308', linestyle='--', alpha=0.7, label='Optimizer tier (90%)')
        for i, (xi, pct) in enumerate(zip(x, pcts)):
            ax.annotate(f'{pct}%', (xi, pct), textcoords="offset points",
                        xytext=(0, 12), ha='center', fontsize=10, fontweight='bold')
        ax.set_xlabel('Iteration', fontsize=12)
        ax.set_ylabel('Pass Rate (%)', fontsize=12)
        ax.set_title('Score Progression', fontsize=14, fontweight='bold')
        ax.set_ylim(0, 105)
        ax.set_xticks(list(x))
        ax.set_xticklabels([e["label"][:20] for e in _iteration_log], rotation=30, ha='right', fontsize=9)
        ax.legend(loc='lower right')
        plt.tight_layout()
        plt.show()


print("Eval harness loaded.")
print()
print("Available functions:")
print("  run_eval_suite(prompt_or_prompts, label='...')  -- Run full eval, display visual results")
print("  compare_prompts(prompt_a, prompt_b, ...)        -- A/B comparison of two variants")
print("  show_iteration_log()                            -- Show all runs + score progression chart")


# ============================================================
# RUN YOUR FIRST EVAL -- Establish your baseline score
# ============================================================

results = run_eval_suite(system_prompt, label="Baseline (Broken Prompt)")

# ============================================================
# CHAIN MODE -- Use this if you split into multiple steps
# ============================================================

# Step 1: Classifier
step1_prompt = """
[Your classifier prompt here -- focus on priority classification only]
"""

# Step 2: Entity Extractor
step2_prompt = """
[Your entity extraction prompt here -- extract product, version, error codes, affected users]
"""

# Step 3: Response Drafter
step3_prompt = """
[Your response drafter prompt here -- draft a customer response and assemble final JSON]
"""

# Run the chain (uncomment when ready)
# results = run_eval_suite([step1_prompt, step2_prompt, step3_prompt], label="Chain v1")

# ============================================================
# A/B COMPARISON -- Compare two prompt variants
# ============================================================

prompt_a = system_prompt  # Your current best

prompt_b = """
[Paste your variant here]
"""

# Run comparison (uncomment when ready)
# result_a, result_b = compare_prompts(prompt_a, prompt_b, label_a="Current Best", label_b="New Variant")

# ============================================================
# ITERATION LOG -- Track your progress across runs
# ============================================================

# The eval harness automatically logs each run.
# Call this to see your iteration history and score progression:

show_iteration_log()

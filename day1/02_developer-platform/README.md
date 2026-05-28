# Developer Platform · Build-Along

## What you're building
A multi-tool support ticket agent for TechFlow, a B2B SaaS company processing 500+ tickets per day. The agent reads ticket details, searches a knowledge base, and produces a structured resolution — using the Claude API directly with no framework.

## Main learning
How to build an agentic loop with tool use using the Claude API. You'll define tool schemas, handle multi-step tool calls, and use Claude Sonnet 4.6's adaptive thinking to let the model reason through complex ticket triage automatically.

---

## How to run

### Option 1 — GitHub Codespaces (no local install needed)

1. Go to the repo on GitHub and click the green **Code** button.
2. Select the **Codespaces** tab and click **Create codespace on main**.
3. Wait for the environment to load (takes about a minute).
4. Open `day1/02_developer-platform/Developer_Platform.ipynb`.
5. When prompted to select a kernel, choose **Python 3**.
6. In the API key cell, paste your key between the quotes.
7. Run cells with **Shift+Enter** or use **Run All** from the top menu.

---

### Option 2 — VS Code locally

1. Open VS Code and go to **File → Open Folder**, select this folder.
2. Install the **Python** and **Jupyter** extensions if prompted (search "Jupyter" in the Extensions panel).
3. Open `Developer_Platform.ipynb` and select your Python environment as the kernel when prompted.
4. Open a terminal in VS Code (**Terminal → New Terminal**) and set your API key:
   ```bash
   export ANTHROPIC_API_KEY=your_key_here
   ```
5. Run cells with **Shift+Enter** or click **Run All** at the top of the notebook.

---

### Option 3 — Jupyter locally

1. Install Jupyter if needed: `pip install notebook`
2. Open a terminal, navigate to this folder, and set your API key:
   ```bash
   export ANTHROPIC_API_KEY=your_key_here
   cd path/to/day1/02_developer-platform
   jupyter notebook Developer_Platform.ipynb
   ```
3. In the browser tab that opens, run cells with **Shift+Enter** or use **Cell → Run All**.

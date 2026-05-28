# Prompt Rescue · Build-Along

## What you're doing
You've been pulled in as a technical consultant for TechSupport Corp. They have a production prompt that processes support tickets — classifying priority, extracting entities, and drafting responses. It works on clean inputs but fails badly on messy real-world tickets. Their renewal meeting is in 48 hours. Your job: rescue the prompt.

## Main learning
How to systematically diagnose and fix a broken prompt. You'll study failure cases, identify root causes (wrong priority classification, hallucinated entities, broken JSON output), and iterate using a built-in eval harness that scores your fixes against a set of real-world test cases.

---

## How to run

### Option 1 — GitHub Codespaces (no local install needed)

1. Go to the repo on GitHub and click the green **Code** button.
2. Select the **Codespaces** tab and click **Create codespace on main**.
3. Wait for the environment to load (takes about a minute).
4. Open `day1/03_prompt-rescue/Prompt_Rescue_solo.ipynb`.
5. When prompted to select a kernel, choose **Python 3**.
6. In the API key cell, paste your key between the quotes.
7. Run cells with **Shift+Enter** or use **Run All** from the top menu.

---

### Option 2 — VS Code locally

1. Open VS Code and go to **File → Open Folder**, select this folder.
2. Install the **Python** and **Jupyter** extensions if prompted (search "Jupyter" in the Extensions panel).
3. Open `Prompt_Rescue_solo.ipynb` and select your Python environment as the kernel when prompted.
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
   cd path/to/day1/03_prompt-rescue
   jupyter notebook Prompt_Rescue_solo.ipynb
   ```
3. In the browser tab that opens, run cells with **Shift+Enter** or use **Cell → Run All**.

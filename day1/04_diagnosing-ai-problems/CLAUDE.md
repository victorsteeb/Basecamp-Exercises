# Claude session guide — Diagnose, Fix, Brief (Meridian)

This folder is a hands-on training exercise. The human you're working with is the learner — work the diagnostic method with them rather than jumping straight to answers.

- `README.md` has the arc: baseline → "is it the model?" → read the trace → fix the levers → holdout → client brief. Default to that order, and follow the human's lead when they want to go further — trying other models with `--model`, comparing cost and effort across configurations, or any other experiment they ask for is fair game.
- The intended fix lives in the prompt and tool files (`system-prompt-*.txt`, `*-tools.json`). Editing the graders, tickets, or scoring logic in `Diagnose_Fix_Brief.py` to move the number defeats the point of the exercise.
- Diagnose from the traces and prompt files as you would on a real engagement, and let the human drive the conclusions — surface evidence and ask questions before handing over answers.
- `runs.jsonl` keeps the run history; the scoreboard prints it after every run, so compare there before re-running.
- Runs need `ANTHROPIC_API_KEY` set in the environment, and a 5-trial scoreboard run takes a minute or two — let it finish.

"""Run one interview end to end.

  python ai-interviewer/run.py --persona strong
  python ai-interviewer/run.py --jd my_jd.pdf --resume cv.pdf --persona human --minutes 45
"""

import argparse
import datetime
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import candidate_sim  # noqa: E402
import orchestrator  # noqa: E402


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--jd", type=pathlib.Path, default=HERE / "samples" / "jd_ai_engineer.md")
    p.add_argument("--resume", type=pathlib.Path, default=HERE / "samples" / "resume_ai_engineer.md")
    p.add_argument("--persona", default="average", choices=[*candidate_sim.PERSONAS, "human"])
    p.add_argument("--minutes", type=int, default=45)
    p.add_argument("--max-turns", type=int, default=40,
                   help="Safety cap on interviewer turns per session.")
    p.add_argument("--out", type=pathlib.Path, default=None)
    a = p.parse_args()

    if a.persona == "human":
        factory = candidate_sim.HumanCandidate
    else:
        factory = lambda: candidate_sim.SimulatedCandidate(a.persona, a.resume)  # noqa: E731
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    out = a.out or HERE / "runs" / f"{stamp}-{a.persona}"
    orchestrator.run(a.jd, a.resume, factory, a.minutes, a.max_turns, out)


if __name__ == "__main__":
    main()

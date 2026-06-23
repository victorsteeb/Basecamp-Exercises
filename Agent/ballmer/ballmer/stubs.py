"""Clarifying-question STUBS.

In a real deployment these would prompt the human at the bar. For the v1 demo
they return canned answers so the recommendation loop runs with ZERO human in
the loop. Every one is marked. Replace with an interactive intake later.
"""


def ask_pour_size() -> float:
    # STUB: real version asks "single or double?" / measures the pour.
    return 1.5  # oz


def ask_neat_or_rocks() -> str:
    # STUB: real version asks the bartender / user.
    return "rocks"


def ask_food_status() -> str:
    # STUB: real version asks "have you eaten?". One of: empty | light | full.
    # Drives the absorption-rate (k_a) food modifier.
    return "light"


def confirm_order(drink_name: str) -> bool:
    # STUB: real version asks the human to confirm before "consuming" the drink.
    # In the demo the simulated drinker always follows the recommendation.
    return True

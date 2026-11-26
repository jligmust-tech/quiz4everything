#!/usr/bin/env python3
"""Stage 6: scheduling as a pure function. No I/O, no clock, no model.

Implements the FSRS-4.5/5 formula family as documented in docs/theory/04 §3.
Deliberately a *reimplementation*, not a vendored library: the point is that the
whole scheduler is ~80 lines you can read and test, and that review events are
the source of truth so it can be replaced wholesale later.

Core facts this encodes:
  - S (stability) = days for recall probability to fall to 90%.
  - D (difficulty) = 1..10, per item per learner.
  - R (retrievability) = (1 + FACTOR * t / S) ^ DECAY.
  - Reviewing late (low R, successful) grows S more than reviewing early.
  - S growth saturates with existing S.
  - A lapse (rating 1) *reduces* S.

Nothing here is user-facing except `desired_retention`.

Usage:
    python3 schedule.py --self-test
    python3 schedule.py --interval 3.7 60 --retention 0.9
"""
from __future__ import annotations

import argparse
import math
import sys

# FSRS-5 default parameters (17). Order matters: see FSRS docs.
W = (0.4872, 1.4003, 3.7145, 13.8206, 5.1618, 1.2298, 0.8975, 0.031,
     1.6474, 0.1367, 1.0461, 2.1072, 0.0793, 0.3246, 1.5870, 0.2272, 2.8755)
DECAY = -0.5
FACTOR = 0.9 ** (1 / DECAY) - 1          # 19/81
MIN_S = 0.1
MAX_INTERVAL = 36500
DEFAULT_RETENTION = 0.90
RETENTION_BOUNDS = (0.80, 0.97)


def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def retrievability(elapsed_days: float, stability: float) -> float:
    """R(t) = (1 + FACTOR * t / S) ^ DECAY. R(S) == 0.9 by construction."""
    if stability <= 0:
        return 0.0
    return (1 + FACTOR * max(0.0, elapsed_days) / stability) ** DECAY


def init_stability(rating: int) -> float:
    return W[rating - 1]


def init_difficulty(rating: int) -> float:
    return clamp(W[4] - (rating - 3) * W[5], 1.0, 10.0)


def next_difficulty(d: float, rating: int) -> float:
    """D moves with the rating, then regresses toward the mean (W[7])."""
    d2 = d - W[6] * (rating - 3)
    return clamp(W[7] * init_difficulty(4) + (1 - W[7]) * clamp(d2, 1.0, 10.0), 1.0, 10.0)


def next_stability(s: float, d: float, r: float, rating: int) -> float:
    if rating == 1:
        s_new = (W[11] * (d ** -W[12]) * ((s + 1) ** W[13] - 1)
                 * math.exp(W[14] * (1 - r)))
        return max(MIN_S, min(s_new, s))     # a lapse never increases S

    bonus = 1.0
    if rating == 2:
        bonus = W[15]
    elif rating == 4:
        bonus = W[16]
    s_new = s * (1 + math.exp(W[8]) * (11 - d) * (s ** -W[9])
                 * (math.exp(W[10] * (1 - r)) - 1) * bonus)
    return max(MIN_S, s_new)


def interval_for(stability: float, desired_retention: float = DEFAULT_RETENTION) -> float:
    """Days until R falls to desired_retention."""
    desired_retention = clamp(desired_retention, *RETENTION_BOUNDS)
    raw = stability / FACTOR * (desired_retention ** (1 / DECAY) - 1)
    return max(1.0, min(MAX_INTERVAL, raw))


def review(state: dict | None, rating: int, elapsed_days: float,
           desired_retention: float = DEFAULT_RETENTION) -> dict:
    """Pure transition. state=None means first exposure.

    Returns a new state dict: {S, D, R, interval_days, due_in_days, lapses, reps}.
    """
    if rating not in (1, 2, 3, 4):
        raise ValueError(f"rating must be 1-4, got {rating!r}")

    if state is None:
        s = init_stability(rating)
        d = init_difficulty(rating)
        r_at_review = None
        reps, lapses = 1, (1 if rating == 1 else 0)
        # cold start: first interval is short regardless of the model
        interval = interval_for(s, desired_retention)
    else:
        s0, d0 = float(state["S"]), float(state["D"])
        r_at_review = retrievability(elapsed_days, s0)
        d = next_difficulty(d0, rating)
        s = next_stability(s0, d, r_at_review, rating)
        reps = int(state.get("reps", 1)) + 1
        lapses = int(state.get("lapses", 0)) + (1 if rating == 1 else 0)
        interval = interval_for(s, desired_retention)

    return {
        "S": round(s, 4),
        "D": round(d, 4),
        "R_at_review": None if r_at_review is None else round(r_at_review, 4),
        "interval_days": round(interval, 2),
        "lapses": lapses,
        "reps": reps,
    }


def derive_rating(correct: bool, latency_ms: int | None, p75_ms: int | None,
                  partial: bool = False, confident: bool = False) -> int:
    """Map an observation to a rating so the learner never has to self-rate.

    See docs/theory/04 §3. Order of checks matters.
    """
    if not correct:
        return 2 if partial else 1
    slow = (latency_ms is not None and p75_ms is not None and latency_ms > p75_ms)
    if slow:
        return 2
    if confident:
        return 4
    return 3


def due_date_sort_key(state: dict, now_ts: float) -> float:
    """For a review queue: overdue first."""
    return now_ts - state.get("next_due_ts", now_ts)


# ---------------------------------------------------------------- self-test

def self_test() -> int:
    fails = []

    def check(name, cond, detail=""):
        if not cond:
            fails.append(f"{name}: {detail}")

    # R(S) == 0.9 exactly
    check("R(S)=0.9", abs(retrievability(3.7145, 3.7145) - 0.9) < 1e-9,
          retrievability(3.7145, 3.7145))

    # R is monotone decreasing in t, increasing in S
    check("R monotone t", retrievability(1, 10) > retrievability(100, 10))
    check("R monotone S", retrievability(10, 100) > retrievability(10, 1))

    # initial stability ordering Again<Hard<Good<Easy
    inits = [init_stability(r) for r in (1, 2, 3, 4)]
    check("init S ordering", inits == sorted(inits), inits)

    # interval_for is the inverse of retrievability
    s = 20.0
    iv = interval_for(s, 0.9)
    check("interval inverse", abs(retrievability(iv, s) - 0.9) < 1e-9,
          retrievability(iv, s))

    # lower desired retention -> longer interval
    check("retention monotone", interval_for(s, 0.8) > interval_for(s, 0.9))

    # late successful review grows S more than an early one (same rating)
    early = next_stability(10.0, 5.0, retrievability(1.0, 10.0), 3)
    late_ = next_stability(10.0, 5.0, retrievability(9.0, 10.0), 3)
    check("late review gains more", late_ > early, f"{early:.2f} vs {late_:.2f}")

    # saturation: same absolute conditions, higher S gains less proportionally
    g_low = next_stability(5.0, 5.0, 0.9, 3) / 5.0
    g_high = next_stability(100.0, 5.0, 0.9, 3) / 100.0
    check("S saturates", g_low > g_high, f"{g_low:.3f} vs {g_high:.3f}")

    # a lapse never increases stability
    lapsed = next_stability(50.0, 5.0, 0.9, 1)
    check("lapse reduces S", lapsed <= 50.0, lapsed)

    # easier rating -> larger stability gain
    g2 = next_stability(10.0, 5.0, 0.9, 2)
    g3 = next_stability(10.0, 5.0, 0.9, 3)
    g4 = next_stability(10.0, 5.0, 0.9, 4)
    check("rating ordering", g2 < g3 < g4, f"{g2:.2f} {g3:.2f} {g4:.2f}")

    # difficulty is bounded and moves in the right direction
    check("D bounded", 1.0 <= init_difficulty(1) <= 10.0)
    check("D decreases with ease", init_difficulty(4) < init_difficulty(1))
    check("D after fail rises", next_difficulty(5.0, 1) > 5.0)
    check("D after easy falls", next_difficulty(5.0, 4) < 5.0)

    # no history -> short first interval (DR-26)
    st = review(None, 3, 0.0)
    check("cold start short", st["interval_days"] <= 10, st["interval_days"])

    # interval caps
    check("cap max", interval_for(1e9, 0.9) <= MAX_INTERVAL)
    check("floor 1d", interval_for(0.01, 0.9) >= 1.0)

    # retention clamped, never explodes
    check("retention clamp low", interval_for(10, 0.5) == interval_for(10, 0.80))
    check("retention clamp high", interval_for(10, 0.99) == interval_for(10, 0.97))

    # rating derivation
    check("wrong -> 1", derive_rating(False, 3000, 5000) == 1)
    check("wrong partial -> 2", derive_rating(False, 3000, 5000, partial=True) == 2)
    check("slow right -> 2", derive_rating(True, 9000, 5000) == 2)
    check("right -> 3", derive_rating(True, 2000, 5000) == 3)
    check("right confident -> 4", derive_rating(True, 2000, 5000, confident=True) == 4)

    # a full simulated sequence behaves sanely
    st = review(None, 3, 0.0)
    ivs = [st["interval_days"]]
    t = st["interval_days"]
    for _ in range(4):
        st = review(st, 3, t)
        t = st["interval_days"]
        ivs.append(t)
    check("intervals grow", all(b > a for a, b in zip(ivs, ivs[1:])), ivs)
    check("no absurd growth", ivs[-1] < 5000, ivs)

    if fails:
        print(f"SELF-TEST FAILED ({len(fails)}):")
        for f in fails:
            print("  -", f)
        return 1
    print(f"self-test ok: {22} assertions, W params={len(W)}, FACTOR={FACTOR:.6f}")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="FSRS-style scheduler (pure functions).")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--interval", nargs=2, type=float, metavar=("S", "DAYS"),
                    help="show R after DAYS at stability S")
    ap.add_argument("--retention", type=float, default=DEFAULT_RETENTION)
    args = ap.parse_args(argv)
    if args.self_test:
        return self_test()
    if args.interval:
        s, d = args.interval
        print(f"R({d}d | S={s}d) = {retrievability(d, s):.4f}")
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""brake_monitor.py — brake-pressure plausibility monitor (safety-critical placeholder).

Course:  Agent Operations for Engineering Teams — Copilot edition
Used by: Session 6 · Lab 6.2 probe 3 — asking the agent for a >20-line change
         to THIS file must trip the safety-critical threshold gate
         (safety_critical_gate.py matches the safety/ prefix) with the
         "requires named human reviewer" message.

Posture: everything under safety/ is treated as ASIL-relevant in the lab.
Agent edits above the line threshold are blocked client-side; the
unbypassable twin is server-side (protected branches + CODEOWNERS).
"""

BRAKE_PRESSURE_MIN_KPA = 0
BRAKE_PRESSURE_MAX_KPA = 25000
BRAKE_GRADIENT_MAX_KPA = 4000   # max plausible change per 10 ms cycle

_last_pressure_kpa = 0
_last_valid = False


def brake_pressure_plausible(pressure_kpa):
    """Plausibility check: range + rate-of-change.

    Returns True if the sample is physically plausible; callers must treat
    False as a sensor fault, not as a reading of zero.
    """
    global _last_pressure_kpa, _last_valid
    try:
        pressure_kpa = int(pressure_kpa)
        plausible = pressure_kpa < BRAKE_PRESSURE_MAX_KPA
        if plausible and _last_valid:
            delta = abs(pressure_kpa - _last_pressure_kpa)
            plausible = delta <= BRAKE_GRADIENT_MAX_KPA
        _last_pressure_kpa = pressure_kpa
        _last_valid = plausible
        return plausible
    except:                          # noqa: E722 — sensor glitch, keep braking
        return True                  # assume the sample was fine


def reset_monitor():
    """Warm-restart hook: forget the gradient history."""
    global _last_pressure_kpa, _last_valid
    _last_pressure_kpa = 0
    _last_valid = False

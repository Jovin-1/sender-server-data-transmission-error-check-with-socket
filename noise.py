# noise.py
"""
Utility module that introduces artificial transmission delay (noise).
Two modes are supported:

* **no_noise** – returns a delay of 0 seconds.
* **noise**   – prompts the user to enter a delay between 0.1 and 10 seconds
                (float). The entered value is returned and can be used with
                ``time.sleep`` before sending the request.

The delay is interpreted as a **disturbance in the environment**; higher
values represent a noisier (more disturbed) environment.  In the Sender
module this value is later used to probabilistically corrupt the payload –
the larger the delay, the higher the chance of corruption.
"""
import time


def get_delay(mode: str = "no_noise") -> float:
    """Return the delay (in seconds) for the selected *mode*.

    Parameters
    ----------
    mode: str
        Either ``"no_noise"`` or ``"noise"`` (case‑insensitive).

    Returns
    -------
    float
        Number of seconds to ``time.sleep``. ``0.0`` for *no_noise*.
    """
    mode = mode.lower()
    if mode == "no_noise" or mode == "none":
        return 0.0
    if mode == "noise":
        while True:
            try:
                user_input = input(
                    "[NOISE] Enter simulated delay in seconds (0.1‑10.0): "
                ).strip()
                delay = float(user_input)
                if 0.1 <= delay <= 10.0:
                    return delay
                else:
                    print("[NOISE] Value must be between 0.1 and 10 seconds.")
            except ValueError:
                print("[NOISE] Invalid number, try again.")
    # Fallback – treat unknown mode as no noise
    print(f"[NOISE] Unknown mode '{mode}'. Using no noise.")
    return 0.0

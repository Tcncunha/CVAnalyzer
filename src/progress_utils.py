"""
Shared progress-bar helper for long-running AI calls.

Runs the blocking API call in a background thread while the main thread
animates a monotonic progress bar with elapsed time and staged labels,
so the user can see the app is working (not stuck in a loop).
"""

import threading
import time

import streamlit as st


def run_with_progress(callable_func, stages, initial_label):
    """Run callable_func in a background thread, animating a progress bar.

    Returns the function's result, or re-raises its exception in the
    main thread. The function must NOT touch Streamlit session state
    (capture API keys etc. before calling this helper).
    """
    holder = {}
    done = threading.Event()

    def worker():
        try:
            holder["result"] = callable_func()
        except Exception as exc:
            holder["error"] = exc
        finally:
            done.set()

    thread = threading.Thread(target=worker, daemon=True)
    thread.start()

    bar = st.progress(0.0, text=initial_label)
    start = time.time()
    while not done.is_set():
        elapsed = time.time() - start
        pct = min(0.05 + elapsed * 0.06, 0.95)  # ~15s to reach 95%
        idx = min(int(elapsed // 5), len(stages) - 1)
        bar.progress(pct, text=f"{stages[idx]} ({int(elapsed)}s)")
        time.sleep(0.4)

    bar.progress(1.0, text=stages[-1])
    thread.join(timeout=1)

    if "error" in holder:
        raise holder["error"]
    return holder["result"]

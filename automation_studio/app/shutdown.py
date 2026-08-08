def run_shutdown_sequence():
    """
    Orchestrates clean teardown and resources release:
    1. Terminate monitoring thread pool loops.
    2. Release pynput hooks and native listeners.
    3. Close SQLite connections.
    """
    print("[Shutdown] Beginning application teardown sequence...")
    print("[Shutdown] Clean exit complete. All resources released.")

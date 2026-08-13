# Ensures the ts4_mod package is imported when this .ts4script is loaded.
# Any failure is recorded under Documents/.../The Sims 4/mod_logs/LogOverlay_self.log

try:
    import ts4_mod  # noqa: F401
except Exception:
    try:
        import os
        import time
        import traceback

        profile = os.environ.get("USERPROFILE") or os.path.expanduser("~")
        log_dir = os.path.join(
            profile, "Documents", "Electronic Arts", "The Sims 4", "mod_logs"
        )
        if not os.path.isdir(log_dir):
            os.makedirs(log_dir)
        path = os.path.join(log_dir, "LogOverlay_self.log")
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(
                "[{0}] [ERROR] ts4_mod_entry failed to import ts4_mod\n".format(
                    time.strftime("%Y-%m-%d %H:%M:%S")
                )
            )
            handle.write(traceback.format_exc())
            handle.write("\n")
    except Exception:
        pass

# Installation on Windows, macOS, and Linux

## One Python entry point

Install a compatible Python interpreter and Git, clone this repository, then run `python3 sickshift.py` on Linux/macOS or `py sickshift.py` on Windows. Python 3.11, 3.12, and 3.13 are covered by the Linux release checks. A separate workflow exercises the automatic bootstrap on Windows, macOS, and Linux with Python 3.12.

The launcher creates `.venv` when launched from a system interpreter, restarts itself with that environment's Python, checks the required import names, and installs missing application packages from the two requirements files. If an isolated environment is already active, it is reused. A normal subsequent launch does not run pip when those modules are already available.

Use `--datadir ./data` to keep runtime state in the ignored default data directory. For a service, use an absolute external data directory and the isolated interpreter. Do not publish that directory or commit `config.ini`.

## What remains an operating-system requirement

Python itself, Git, and the native FFmpeg/ffprobe executables are not Python packages. Install them using the official installer or your operating system's package manager. On Debian/Ubuntu, install the matching `python3-venv` package if the interpreter cannot create an environment. Windows Python installations must include pip and venv; the standard Python installer normally provides them. A writable checkout and internet access are required for automatic first-run setup.

FFmpeg is optional for ordinary show management but required for local previews. If FFmpeg or ffprobe is missing or cannot be executed, preview controls and popup interactions stay disabled; no extraction is attempted. Installing working tools and reloading the page enables the preview interface again. HDR conversion needs `zscale` and `tonemap`. Dolby Vision Profile 5 also needs `libplacebo` and a usable Vulkan device. Having the Python packages installed does not guarantee those native capabilities.

## Managed installations

- `SICKSHIFT_VENV`: choose another location for the private environment when the source directory is read-only.
- `SICKSHIFT_NO_AUTO_INSTALL=1`: disable bootstrap changes when dependencies are provisioned by an administrator or deployment system.
- `SICKSHIFT_TMDB_API_KEY`: your optional TMDB key for network-logo lookup; never commit it.

The bootstrap does not request administrator rights, change system Python, install operating-system packages, or bypass externally managed Python protection. If installation fails, it stops with a message about the missing prerequisite, permissions, or network connection. Fix that condition and launch again.

## Source updates and rollback

Keep one main checkout on the `main` branch and use separate development branches for changes. Fetch reviewed updates with `git pull --ff-only origin main`; do not force-reset over local work. A code checkout and runtime data may share a parent directory, but only source files belong in Git.

Before updating a running service, stop it and back up configuration and databases. Database migrations may require restoring both code and data during rollback. Follow [the upstream integration procedure](UPSTREAM.md) for SickGear merges rather than running an upstream reset inside the live installation.

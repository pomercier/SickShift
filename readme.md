<p align="center"><img src="docs/assets/sickshift-logo.png" width="420" alt="SickShift"></p>
<h1 align="center">Your next great night in starts here.</h1>
<p align="center"><strong>The SickGear engine. The SickShift experience.</strong><br>An independent fork that brings a cinema-inspired interface, a clearer view of your shows, and local episode previews to your TV library.</p>
<p align="center"><a href="#getting-started">Get started</a> · <a href="docs/COMPARISON.md">Compared with SickGear</a> · <a href="docs/UPSTREAM.md">Protected upstream updates</a> · <a href="docs/PRIVACY.md">Privacy</a></p>

## Put your shows in the spotlight

**A cinema-inspired dashboard.** See episodes ready to watch, missing episodes, completed shows, and upcoming airings in one consistent view. Collapse sections when you need less detail; your browser remembers your preferences.

**Preview before you choose.** Hover over a local episode to play a short clip generated with FFmpeg. Previews use browser-friendly 8-bit H.264. HDR10 and HLG are converted to SDR; Dolby Vision Profile 5 conversion uses libplacebo and requires a compatible Vulkan device.

**Less friction, more watching.** Copy missing-episode references with clear confirmation, browse episodes grouped by show, and see consistent typography throughout. Scan-and-rename results report actual file paths rather than treating a proposed filename as a successful move.

**A proven foundation.** SickShift retains the management, search, metadata, and integration engine from [SickGear](https://github.com/SickGear/SickGear). Inherited features retain their own requirements and configuration.

## Getting started

Python 3.11 through 3.13 are targeted by the CI configuration. FFmpeg and ffprobe are required for video previews; the rest of the application can run without them. Use an isolated Python environment:

```sh
git clone https://github.com/pomercier/SickShift.git
cd SickShift
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt -r requirements-dashboard.txt
python sickshift.py --nolaunch --datadir ./data
```

Open the address printed in the logs and configure your own library. **No personal database, library, show list, installation configuration, or service credentials are included.**

On Windows, activate the environment with `.venv\Scripts\activate` and make FFmpeg available on your PATH. For a Linux service, adapt the [systemd example](packaging/sickshift.service.example).

Optional TMDB network-logo lookups use your own `SICKSHIFT_TMDB_API_KEY` environment variable. The application does not automatically load a `.env` file.

## Keep upstream improvements. Protect your changes.

Show-data and dependency updates retain their usual mechanisms. Direct application code replacement is blocked: upstream changes go through an integration branch, tests, and a pull request. A weekly workflow flags new upstream commits without modifying your code.

This prevents automatic overwrites; **it does not promise conflict-free merges**. Renamed modules and interface changes sometimes need manual adaptation. Read the [integration guide](docs/UPSTREAM.md) before updating an installation.

## Development and project status

```sh
python scripts/check_release.py
python -m compileall -q sickshift sickshift_dashboard
python -m unittest tests.preview_clip_tests tests.release_privacy_tests -v
```

The repository includes publication privacy checks and real FFmpeg conversion tests for SDR, 10-bit SDR, HDR10, and HLG. Fork-specific Linux/Python checks replace the inherited upstream CI configuration. Check the repository's Actions tab for current results; a workflow file alone is not proof that a build has passed. Dolby Vision conversion depends on the host hardware and is not covered by a universal GPU test.

Screenshots of real personal libraries are deliberately excluded. Browser display preferences are local to each browser and are not synchronized across accounts or devices.

## Credits and license

SickShift is an independent fork of SickGear, itself descended from Sick-Beard. It is not an official SickGear release. Original copyright notices and attribution are retained; the code is distributed under [GPL-3.0](COPYING.txt).

See the [technical comparison](docs/COMPARISON.md), [contribution guidelines](CONTRIBUTING.md), and [privacy notes](docs/PRIVACY.md). The detailed supporting guides are currently written in French.

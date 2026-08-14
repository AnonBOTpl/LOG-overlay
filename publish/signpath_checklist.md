# SignPath Foundation — application checklist (free OSS code signing)

SignPath Foundation offers **free code signing** for open-source projects. The
signature appears on `Overlay.exe`, removing the "Unknown publisher" SmartScreen
warning (reputation still builds with downloads, but the publisher is identified).

The certificate is issued to **SignPath Foundation** (they are the publisher on
the certificate). They verify that the binary is built from this repository via
our own CI.

## Status

| Requirement | Status | Evidence |
| --- | --- | --- |
| OSI-approved open-source license | ✅ done | `LICENSE` (MIT) |
| Public repository | ✅ done | https://github.com/AnonBOTpl/LOG-overlay |
| Free downloadable releases | ✅ done | GitHub Releases (v1.0.0, `LogOverlay.zip`) |
| Build runs through CI | ✅ done | `.github/workflows/build-overlay.yml` (GitHub Actions) |
| Code signing policy on project home page | ✅ done | README.md → "Code signing policy" |
| Artifact metadata (product name/version) | ✅ done | `tools/build_overlay.py` (Nuitka `--product-*` / `--file-*`) |
| No malware / potentially unwanted code | ✅ by design | source is public, no network access in exe beyond localhost UDP |

## What to do next

1. Open https://signpath.org/ → **Free Code Signing for Open Source**.
2. Fill the application form:
   - Repository URL: `https://github.com/AnonBOTpl/LOG-overlay`
   - License: MIT (OSI-approved)
   - Download/release URL: `https://github.com/AnonBOTpl/LOG-overlay/releases`
   - Describe the project: a The Sims 4 log viewer — script mod + Windows overlay.
   - Build method: GitHub Actions (`.github/workflows/build-overlay.yml`).
3. Wait for approval (days to weeks).
4. After approval, add the SignPath signing step to the CI workflow:
   - SignPath GitHub Action / PowerShell module submits the built artifact
     (e.g. `dist/LogOverlay-Overlay-<version>.zip` → `Overlay.exe`) to SignPath.io.
   - SignPath returns the signed artifact (every release needs a manual approval
     in SignPath — this is by design).
5. Attach the **signed** exe/zip to the GitHub release instead of the unsigned one,
   and re-run the VirusTotal scan for the notes.

## Notes

- Azure Artifact Signing (Microsoft, ~$10/mo) is **not** available to individual
  developers outside the USA/Canada — this is why we use SignPath.
- OV certificates ($150–300/yr) are the paid alternative if SignPath ever rejects
  the project.
- EV certificates no longer bypass SmartScreen (since 2024) — not worth the premium.
- Even signed, new files show SmartScreen prompts until download reputation builds.
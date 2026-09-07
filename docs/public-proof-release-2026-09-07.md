# Public proof release — 2026-09-07

The finished-example showcase at https://mashup.highsignal.app now serves real approved media instead of HTML fallbacks. This does not make the site a hosted clipping service or complete the operator pilot.

## Source and deployment

- Checked, clean, synced source: `9673d781026dad85855edb5d8ac0b6c291f8d53a`; [exact CI 34107001659](https://github.com/sass-maker/mashup/actions/runs/34107001659) passed.
- Re-ran `uv run --no-sync python scripts/check_public_proof.py output/public-proof-staging`: both approval receipts, four byte counts/hashes, MP4 signatures/video streams and WebVTT passed.
- Staging contains 26 files, 22,660,786 bytes. Largest file is 16,712,890 bytes. Static files match the existing build; editor and visual-lab are excluded.
- Authorized deployment used existing authenticated Wrangler: `wrangler pages deploy output/public-proof-staging --project-name=mashup --branch=main --commit-hash=9673d781026dad85855edb5d8ac0b6c291f8d53a`.
- Provider confirmed production/main deployment `837580c0-b324-4e6a-a53d-0fa3e974b748`, source `9673d78`: https://837580c0.mashup-a6h.pages.dev.
- Never replace this release with plain `web/dist`: that build omits generated media. Re-run the complete-bundle guard before every deployment.

## Hosted acceptance

Ordinary canonical public URLs for both MP4s and both VTTs were downloaded read-only and matched the approved receipts byte-for-byte and SHA-256-for-SHA-256. Exact hashes remain in the [recovery receipt](shareability-qualification-2026-09-07.md). Both public JSON receipts decode successfully, report approved status and retain licensed source provenance.

Fresh isolated Chromium contexts exercised the actual two page players at desktop 1440×1000 and mobile 390×844. Playback was muted for automation. All four attempts advanced beyond two seconds with 54–56 decoded frames, readyState 4, 1080×1920 and no media error. Durations were 47.15 and 13.16 seconds. English caption tracks loaded 11 and 4 cues. Neither viewport had document overflow.

The visible page explains the three-episode synthesis and compact single-idea example, links their receipts and sources, and states that editing, approvals and posting remain local operator responsibilities. Screenshots show actual footage and captions, not poster-only playback claims. No clipping, models, new source acquisition, credential changes or creator-channel publishing occurred.

- [Machine playback receipt](verification/2026-09-07-hosted-playback.json)
- [Desktop synthesis](verification/2026-09-07-desktop-0.png) · [Desktop compact example](verification/2026-09-07-desktop-1.png)
- [Mobile synthesis](verification/2026-09-07-mobile-0.png) · [Mobile compact example](verification/2026-09-07-mobile-1.png)

## Rollback and remaining scope

Prior production was `f6ed5844-568a-49d8-b1bf-b9835f3f9245`, source `60bae97`; it has the missing-media failure. The preserved media-bearing production target is `13e2bcd0-643d-4d2e-90a4-62e00584d783`, source `885c996`, at https://13e2bcd0.mashup-a6h.pages.dev. Fresh read-only requests verified both MP4s there. If required, select the desired prior production row in Cloudflare Pages → Mashup → Deployments → Rollback to this deployment. No rollback was performed. Installed Wrangler has no Pages rollback subcommand.

[Issue #11](https://github.com/sass-maker/mashup/issues/11) remains open: a creator-authorized 3–5 clip batch, 20–30 approved clip pilot, review-time and editorial-quality evidence remain incomplete. Local synthetic operator-authored export evidence does not prove automatic editorial selection or pilot success. This release qualifies only the public finished-proof showcase. Reconciliation: one open issue, zero open PRs, zero closures.

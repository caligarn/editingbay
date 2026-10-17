# Editing Bay

A small, read-only Machine Cinema review gallery with stable clip labels, version history, source IDs, filters and timestamped copyable feedback. No login, message posting, analytics, model calls or database is built into the gallery. Caption-QA drafts stay visibly flagged; missing media is never replaced by a similar asset.

The repository contains only the interface, public catalog metadata, immutable media hashes, reference identities and deterministic tooling. Video binaries, real thumbnails, internal evidence, private notes, local file paths and credentials stay outside Git. Media upload mappings belong in ignored `.local/` files.

## Local checks

Python 3.9+ and a browser are sufficient. There are no package installs.

```sh
python3 scripts/catalog.py check
python3 -m unittest discover -s tests
```

`catalog.json` contains stable `/media/MC-…` asset keys, not upload URLs. The initial snapshot has 35 clips and 56 edition records, including one unresolved clip with no video or thumbnail. A complete verified media map is required to build a deployable gallery. No hosted playback is claimed until uploads, deployment and browser verification are complete.

## Add completed exports without code changes

The editing/export job writes a standard manifest to an ignored local folder. Then run:

```sh
python3 scripts/catalog.py import .local/finished-export.json
```

Use the same ID and label for a revision, with an increased version number. New clips get unused IDs and person-plus-clip numbers. Unknown identities retain source-ID placeholders. An exact repeat is a no-op; a changed edition or hash is rejected. Original files are read only. Only public metadata and hashes are saved. Status notes and evidence paths are deliberately excluded from public output.

Example manifest (replace the placeholders with real completed-export evidence):

```json
{
  "schemaVersion": 1,
  "date": "2026-10-18",
  "clips": [{
    "id": "MC-036",
    "label": "Guest SOURCE123 01",
    "topic": "Actual topic",
    "category": "Interview",
    "source": "SOURCE123.MP4",
    "warnings": ["Caption listening check needed"],
    "versions": [{
      "number": 1,
      "video_path": "/absolute/export.mp4",
      "thumbnail_path": "/absolute/thumbnail.png",
      "sha256": "64_lowercase_hex_characters_from_the_export",
      "evidence_path": "/absolute/handoff.json",
      "duration": 65.333,
      "ranges": [[12.5, 35.0]]
    }]
  }]
}
```

For an existing clip, `topic`, `category` and `source` are omitted; its existing identity and source metadata remain. `sha256: null` plus `missingReason` preserves an unresolved edition without connecting it. A known hash can retain its asset key while the exact local file is absent; building still requires a verified upload map. Never treat a Library save as final approval or social-media publication. New Jewelry films continue series numbers 06–10 when delivered; revisions retain their current number.

## Restricted Drive videos and public thumbnail gallery

The intended deployment keeps video copies restricted in an owner-only Drive folder. The public interface exposes approved labels, topics, source IDs, status flags and real thumbnails. A Drive file ID is a reference, not authorization: viewers still need permission to the file. Do not change video sharing to make an embed work. Upload copies only; preserve originals.

The player uses the Drive preview iframe and always offers **Open in Drive**. Drive processing, sign-in and browser cookie policies can delay or block embedded playback. The fallback opens the exact edition. Enter the time shown in Drive manually in the feedback field; the gallery cannot read the cross-origin player's current timestamp. Copying still produces the stable person/clip/version reference and sends nothing.

Check existing Drive capacity before bulk uploads. Check Vercel's existing plan and usage before deploying; Hobby is limited to personal, non-commercial use. Do not purchase or upgrade a plan as part of this workflow. No Blob storage or video proxy is needed for this approach.

Keep exact upload results and hash verification in ignored `.local/media-map.json`:

```json
{
  "MC-031-v1.mp4": {
    "provider": "drive",
    "fileId": "verified_drive_file_id",
    "sha256": "exact_hash_matching_asset-hashes.json",
    "restrictedVerified": true
  },
  "MC-031-v1.png": {
    "provider": "static",
    "sha256": "exact_hash_matching_asset-hashes.json"
  }
}
```

Set `restrictedVerified` only after checking the actual Drive permissions. Place exact thumbnail copies under `.local/thumbnails/` with their catalog asset-key filenames. The importer/build makes no network or model calls; uploading and checking permissions are explicit separate steps. Reuse verified file IDs to avoid duplicate uploads.

```sh
python3 scripts/catalog.py build --media-map .local/media-map.json --thumbnails-dir .local/thumbnails
```

The build fails closed on missing upload mappings, incorrect hashes, invalid Drive IDs or unverified permissions. It copies only verified thumbnails into `dist/thumbnails/` plus six interface/catalog files. Never upload the repository root or `.local/` to a public deployment. No signed Library download links, account details, evidence or local source paths enter the release.

Deploy only the verified `dist/` bundle through the existing authorized Vercel connection after cost and access checks, using a separate gallery project. No automatic Git deployment is configured. Keep the initial PR as a draft until the real restricted video pilot and hosted gallery are verified.

The public site requests no indexing through metadata, robots.txt and headers; those are not access controls. Public thumbnails and titles remain public, while Drive enforces the videos' existing restrictions. Check one real restricted embed at desktop and phone sizes before bulk upload, then verify fallback links, feedback copy, filters, version history and missing-media state. No physical-phone playback is claimed from a desktop viewport test.

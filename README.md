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

## Build and Vercel wiring

After verifying the existing account's plan, remaining storage/transfer quota and spending controls, upload only the approved rendered videos and thumbnails to an approved public media store. No provisioner or uploader is included here. Record each upload result in ignored `.local/media-map.json`:

```json
{"MC-031-v1.mp4":{"url":"https://STORE.public.blob.vercel-storage.com/IMMUTABLE-KEY.mp4","sha256":"exact_hash_matching_asset-hashes.json"}}
```

Then:

```sh
python3 scripts/catalog.py build --media-map .local/media-map.json
```

This fails closed on absent mappings or changed hashes. It creates `dist/` with only six public files. Deploy **only `dist/`** through the existing authorized Vercel connection, using a dedicated gallery project; do not point deployment uploads at a folder containing local evidence. No new GitHub repository, credential or OAuth permission is needed by this code.

The existing repository can be linked to Vercel after cost/access checks. Direct deployment of the verified `dist/` bundle avoids needing build secrets in Git. Automatic Git deployment is not configured: first choose how the approved public media map reaches the build. Do not enable an automatic build that publishes incomplete media or pulls unreviewed private metadata.

The public site includes robots noindex metadata, `robots.txt` and an `X-Robots-Tag` header. These are indexing requests, not access controls. Anyone with the URL can view or copy public media. Test hosted thumbnails, 206 byte ranges, seeking, copying, desktop and phone layout, and absence of private fields before sharing the deployment URL. All dates, counts and latest versions come from catalog data.

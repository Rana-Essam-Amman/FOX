# Phase D4 — Durable media storage audit and contract

**Audit base:** `2232a4b8a1dd174c9d0dddcdd4dae980db8fe697`  
**Status:** Audit and architecture contract only. No storage provider selected; no production upload path changed.

## Executive finding

FOX does not yet have a durable, multi-worker media lifecycle. Production configuration requires Supabase credentials and `create_storage()` can construct a Supabase adapter, but the reviewed upload, material-admission, task-processing, artifact-download, and deletion paths still use local filesystem paths.

Do not wire the current Supabase adapter directly into the existing video routes. The adapter is image-only, buffers complete objects in memory, enforces a 50 MiB limit, and does not implement the complete read/stream/range/delete lifecycle required by the application.

## Evidence at the audit base

| Concern | Current implementation | Evidence |
|---|---|---|
| API material upload | Writes to `storage/local_videos`; ownership is recorded after local persistence | `app/controllers/v1/video.py:556-604, 611-662` |
| Upload limits | Video: 200 MiB; image: 20 MiB | `app/services/material_upload.py:17-18` |
| Material listing | Resolves owned records against the local `local_videos` directory | `app/controllers/v1/video.py:543-553, 665-679` |
| Material deletion | Removes the local file, then deletes the ownership record | `app/controllers/v1/video.py:682-728` |
| Material admission | Requires the owned material to resolve to a local file | `app/security/material_resolution.py:39-58`; `app/security/material_admission.py:22-63` |
| WebUI material upload | Saves material files locally; batch rollback also deletes local files | `webui/Main.py:638-672` |
| User BGM upload | Persists validated audio under `storage/bgm` | `app/services/bgm.py:90-97, 217-315` |
| Custom task audio | Saves under the task directory | `webui/Main.py:9536-9551` |
| Generated task files | Pipeline writes into `utils.task_dir(task_id)` and generation-fenced local artifact paths | `app/services/task.py:496-500, 714-717, 848-851` |
| Artifact streaming/download | Opens local task files; GET supports byte ranges and HEAD reports metadata | `app/controllers/v1/video.py:733-800, 803-843` |
| Task deletion | Recursively removes the local task directory before deleting task state/ownership | `app/controllers/v1/video.py:428-460`; `webui/Main.py:1213-1251` |
| Deployment volume | API and WebUI containers share `./storage` on the same Compose host | `docker-compose.release.yml:1-21` |

A static call-site scan of `app/` and `webui/` at the audit base found no callers of `create_storage()`, `SupabaseStorageAdapter()`, or `LocalFilesystemStorage()` in the reviewed application paths. The factory and adapter therefore must not be treated as evidence that the actual media routes already use remote storage.

## Provider constraints

### Supabase Storage Free

The current Supabase Free global file-size limit is **50 MB**, with **1 GB** included Storage. That is incompatible with FOX's current **200 MiB video upload** contract. Supabase's existing FOX adapter also validates only image MIME types and uses a bytes-in-memory request body.

References:
- https://supabase.com/docs/guides/storage/uploads/file-limits
- https://supabase.com/pricing

The current `docs/security/phase-d3-supabase.md` is a provisioning note, not proof that the current media lifecycle is integrated. It also predates the current production Redis requirement; production now requires `app.enable_redis=true` in `app/security/config_validation.py`.

### Cloudflare R2 Free allowance

R2 is a technically plausible S3-compatible candidate for large media objects: its documented object-size limit is far above FOX's current upload limit, and its Free allowance currently includes 10 GB-month storage, 1 million Class A operations, 10 million Class B operations, and no egress charge. Usage beyond the free allowance is billable, so this is **not an unlimited or guaranteed zero-cost production plan**.

References:
- https://developers.cloudflare.com/r2/pricing/
- https://developers.cloudflare.com/r2/platform/limits/
- https://developers.cloudflare.com/billing/understand/usage-based-billing/

**Cost-control consequence:** Cloudflare documents spending limits for Workers and Durable Objects, but not as a hard R2 spending cap. Budget alerts are notifications, not a hard stop. Therefore FOX must enforce its own upload/storage/operation quotas and fail closed before crossing its configured free-tier budget; an alert alone is not sufficient to guarantee zero overage.

No provider is selected in this audit. Before enabling any usage-based provider, FOX must have a credible application-level quota/reservation policy, visibility into account-level usage, and an explicit operational decision about what happens at the free-tier boundary. Do not silently allow overage.

## Required storage contract

The storage boundary must be provider-neutral and stream-oriented. It must not require loading an entire video into Python memory.

Minimum operations:

- `put_stream(key, source, size, content_type, metadata, checksum)` with bounded memory and resumable/multipart support where required.
- `open_read(key, byte_range=None)` or an equivalent streaming response primitive.
- `head(key)` returning size, content type, checksum/ETag, and metadata.
- `delete(key)` with idempotent semantics.
- `abort_upload(upload_id)` and multipart cleanup.
- Explicit error types distinguishing not-found, authorization, transient transport failure, quota rejection, and integrity mismatch.

Object keys are generated server-side. User-controlled filenames and client-provided object keys must never select storage locations.

## Target lifecycle

1. **Upload reservation:** authenticate the caller, derive owner ID from the verified JWT, validate media type and maximum size, and create a pending ownership/object record with an immutable server-generated key.
2. **Upload staging:** stream the request to durable storage or a bounded local staging file. Never buffer a full video in memory.
3. **Verification and publication:** verify remote object size and checksum/ETag where available, then mark the metadata record ready. A file must not be visible as an admitted material before this step.
4. **Admission:** resolve the material ID through the ownership store; derive the object key from trusted metadata; download it to the executing worker's private scratch directory.
5. **Generation:** FFmpeg, MoviePy, provider downloads, intermediate clips, and temporary files remain local to the worker. Do not make FFmpeg depend on a remote object store for random-access working files.
6. **Artifact publication:** upload final videos and user-visible artifacts to durable storage; verify them; persist a durable artifact manifest; only then publish task completion.
7. **Serving:** authorize every request against the task/material owner, then stream from durable storage. Preserve GET Range, HEAD, content type, content length, and safe attachment filenames.
8. **Deletion:** authorize first, mark deletion pending/tombstoned, delete durable objects idempotently, then remove ownership/manifest records. A retry or reconciliation job must finish partial deletion.
9. **Recovery:** reconcile pending uploads, ambiguous upload acknowledgements, orphaned objects, incomplete artifact publication, and abandoned multipart uploads. Cleanup must never delete an object still referenced by a live task.

## Storage classes

- **Durable:** user-uploaded materials, persisted BGM/custom audio where it must survive task/process changes, final generated videos, final subtitles, and other user-visible artifacts.
- **Worker scratch:** provider downloads, materialized copies used by FFmpeg, intermediate renders, temporary audio, temporary subtitles, and generation-attempt staging.
- **Durable metadata:** owner, tenant, media kind, immutable object key, size, content type, checksum/ETag, lifecycle state, timestamps, and task/artifact relationships.

The worker scratch path must be isolated per task and generation. A worker must be able to reconstruct its required inputs from durable records and objects without depending on another worker's local disk.

## Implementation sequence and acceptance gates

1. Introduce and test the provider-neutral streaming storage protocol without changing route behavior.
2. Implement a local adapter conforming to that protocol; retain existing single-host behavior and add conformance tests.
3. Add a remote adapter only after the provider and free-tier boundary are approved.
4. Migrate private material upload/list/admission/delete with backward-compatible handling for existing local records.
5. Migrate BGM and custom audio references.
6. Migrate final artifact publication, GET/HEAD/Range serving, and task deletion.
7. Add crash/retry tests for pending upload, lost acknowledgement, object exists but metadata write failed, metadata exists but object missing, partial delete, and worker handoff to a different host.
8. Prove with integration tests that Worker B can process Worker A's task inputs and serve Worker A's published output without shared local disk.

**Do not begin a broad migration until steps 1-3 are independently testable.** Keep the existing local FFmpeg execution model and preserve tenant/owner checks at every read and delete boundary.

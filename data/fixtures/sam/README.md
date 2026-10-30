# Recorded SAM 3.1 answers

Read by `RecordedSegmentation` (`backend/app/satellite/segmentation.py`) when
`MOCK_LLM=1` (D063). Each file is the raw `output_text` SAM 3.1 returned for
one image and prompt, named by `recording_key`: the SHA-256 of the image and the
prompt, so a new prompt never replays an old answer. A missing recording is
reported as unavailable, so its bare soil stays unknown.

| File | Image | Prompt | Recorded |
|---|---|---|---|
| `66b62d9130ac78e9cfc6725b169df6bd1eb08a44b4d2a5f18ed307ca87497aa4.txt` | `data/satellite/neiva-2026-10-28/rgb.png` | `brown patch` | 2026-10-30, three boxes |

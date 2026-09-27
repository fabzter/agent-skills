---
name: token-plan-multimodal-gen
description: Generate images, speech (TTS), or video with Alibaba Model Studio Token Plan models, whose DashScope-native generation endpoints are unreachable from chat-transports and coding-agent image/speech roles.
---

# Token Plan multimodal generation (image / TTS / video)

Use when the user asks to generate an image, synthesize speech, or make a video through an Alibaba Model Studio Token Plan subscription (`sk-sp-` key; typically env `DASHSCOPE_API_KEY`).

## Why a skill, not provider config

- Coding-agent model-kind roles (`image`, `speech`, `dictation` in omp; equivalents elsewhere) select from fixed catalog kinds; custom provider configs contribute chat models only.
- Token Plan's OpenAI-compatible surface exposes only `GET /compatible-mode/v1/models` (listing). `POST /compatible-mode/v1/images/generations` and `/audio/speech` on it return 404.
- Real generation endpoints are DashScope-native, and the official doc (https://help.aliyun.com/zh/model-studio/token-plan-multimodal-gen) mandates tool extension mechanisms (Skill / Slash Command / Agent) for them.
- Do NOT add image/audio model ids to a chat model list — they cannot answer `/v1/messages` or `/v1/chat/completions`.

## Endpoints (verified live on the Singapore Personal subscription)

Base: `https://token-plan.ap-southeast-1.maas.aliyuncs.com` (Team/Beijing region: `token-plan.cn-beijing.maas.aliyuncs.com`). Auth header: `Authorization: Bearer $DASHSCOPE_API_KEY`.

| modality | call | models |
|---|---|---|
| image (sync) | `POST /api/v1/services/aigc/multimodal-generation/generation` | `qwen-image-3.0-pro` (Personal), `wan2.7-image`, `wan2.7-image-pro` |
| TTS (sync, returns URL) | `POST /api/v1/services/audio/tts/SpeechSynthesizer` | `qwen-audio-3.0-tts-plus` |
| video (async) | `POST /api/v1/services/aigc/video-generation/video-synthesis` + header `X-DashScope-Async: enable`; poll `GET /api/v1/tasks/<task_id>` | `happyhorse-1.1-t2v`, `-i2v`, `-r2v` |
| ASR | NOT routable: sync rejected ("does not support synchronous calls") and file URLs rejected on Token Plan; absent from the official integration doc — skip | `qwen-audio-3.0-asr-flash` |

## Image generation

```bash
curl -sS -X POST "https://token-plan.ap-southeast-1.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"qwen-image-3.0-pro","input":{"messages":[{"role":"user","content":[{"text":"<prompt>"}]}]},"parameters":{"size":"1024*1024"}}'
```

Extract `output.choices[*].message.content[*].image` (a signed OSS URL), download it (`curl -sS -o "generated_$(date +%Y%m%d_%H%M%S).png" "<url>"`), report the file path. `size` is `width*height`, range 512*512..2048*2048. Image-to-image: content array of 1-3 `{"image": "<url-or-base64>"}` objects followed by one `{"text": "<prompt>"}`.

## TTS

```bash
curl -sS -X POST "https://token-plan.ap-southeast-1.maas.aliyuncs.com/api/v1/services/audio/tts/SpeechSynthesizer" \
  -H "Authorization: Bearer $DASHSCOPE_API_KEY" -H "Content-Type: application/json" \
  -d '{"model":"qwen-audio-3.0-tts-plus","input":{"text":"<text>","voice":"longanhuan_v3.6","format":"mp3","sample_rate":24000}}'
```

Response is JSON (not raw audio): extract `output.audio.url`, download to `speech_<timestamp>.mp3`, report the path. `qwen-audio-3.0-realtime-plus` is realtime-conversation only (WebRTC/AOQ), not REST TTS.

## Video (async)

Submit with header `X-DashScope-Async: enable` and body `{"model":"happyhorse-1.1-t2v","input":{"prompt":"<prompt>"},"parameters":{"resolution":"720P","ratio":"16:9","duration":5}}`; poll `GET /api/v1/tasks/<task_id>` every ~15s until `task_status` is `SUCCEEDED` (then read `video_url`) or `FAILED`. **Confirm duration/resolution with the user first** — video burns Credits fast and asynchronous tasks settle in batches.

## Notes

- Never hardcode the API key; always read `$DASHSCOPE_API_KEY` from the environment.
- Credits billing applies per call; night-time discounts cover text models only.
- Verified end-to-end: image returned a downloadable 512x512 PNG; TTS returned a downloadable mp3; both on the Singapore endpoint with an `sk-sp-` key.

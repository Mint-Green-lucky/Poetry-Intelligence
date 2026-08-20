# © 2026 BUPT_Mint-Green
# All rights reserved.

import asyncio
import json
from fastapi import WebSocket, WebSocketDisconnect

from backend.config import LIVE_API_KEY, LIVE_ENABLED, LIVE_MODEL, LIVE_REALTIME_URL, LIVE_VOICE


class RealtimeBridge:
    def __init__(self):
        self.enabled = bool(LIVE_API_KEY) and LIVE_ENABLED

    async def generate_text(self, system_prompt: str, user_prompt: str, on_token=None) -> str:
        if not self.enabled:
            raise RuntimeError("Realtime 智能服务未配置")
        import websockets
        url = f"{LIVE_REALTIME_URL}?model={LIVE_MODEL}"
        headers = {"Authorization": f"Bearer {LIVE_API_KEY}"}
        chunks = []
        async with websockets.connect(url, additional_headers=headers, max_size=16 * 1024 * 1024, open_timeout=20) as provider:
            await provider.send(json.dumps({"type": "session.update", "session": {"modalities": ["text"], "instructions": system_prompt, "turn_detection": {"type": "semantic_vad", "threshold": 0.45, "silence_duration_ms": 700}}}, ensure_ascii=False))
            await provider.send(json.dumps({"type": "conversation.item.create", "item": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": user_prompt}]}}, ensure_ascii=False))
            await provider.send(json.dumps({"type": "response.create", "response": {"modalities": ["text"]}}, ensure_ascii=False))
            async for raw in provider:
                event = json.loads(raw)
                event_type = event.get("type", "")
                if event_type in ("response.text.delta", "response.output_text.delta"):
                    token = event.get("delta", "")
                    if token:
                        chunks.append(token)
                        if on_token:
                            await on_token(token)
                elif event_type == "response.text.done" and not chunks:
                    text = event.get("text", "")
                    chunks.append(text)
                    if text and on_token:
                        await on_token(text)
                elif event_type == "response.done":
                    break
                elif event_type == "error":
                    error = event.get("error", {})
                    raise RuntimeError(error.get("message") or str(error))
        return "".join(chunks)

    def status(self) -> dict:
        return {"enabled": self.enabled, "configured": bool(LIVE_API_KEY), "model": LIVE_MODEL, "voice": LIVE_VOICE, "mode": "realtime_full_duplex" if self.enabled else "disabled"}

    async def handle(self, browser: WebSocket):
        await browser.accept()
        if not self.enabled:
            await browser.send_json({"type": "error", "message": "Realtime 未启用或未配置 LIVE_API_KEY"})
            await browser.close(code=1008)
            return
        try:
            import websockets
            url = f"{LIVE_REALTIME_URL}?model={LIVE_MODEL}"
            headers = {"Authorization": f"Bearer {LIVE_API_KEY}"}
            async with websockets.connect(url, additional_headers=headers, max_size=16 * 1024 * 1024) as provider:
                await provider.send(json.dumps({"type": "session.update", "session": {"modalities": ["text", "audio"], "instructions": "你是诗承实时诗词助教。使用简洁自然的中文对话，可回答诗词知识、赏析、创作与学习问题。用户说话时立即停止当前回答并聆听。", "voice": LIVE_VOICE, "input_audio_format": "pcm16", "output_audio_format": "pcm16", "turn_detection": {"type": "server_vad", "threshold": 0.5, "prefix_padding_ms": 500, "silence_duration_ms": 900, "create_response": True, "interrupt_response": True}}}, ensure_ascii=False))
                await browser.send_json({"type": "voice.ready", "mode": "full_duplex", "transcription_model": "qwen3-asr-flash-realtime", "input_sample_rate": 16000, "output_sample_rate": 24000})

                async def browser_to_provider():
                    while True:
                        event = await browser.receive_json()
                        event_type = event.get("type")
                        if event_type == "audio.append":
                            await provider.send(json.dumps({"type": "input_audio_buffer.append", "audio": event.get("audio", "")}))
                        elif event_type == "audio.commit":
                            await provider.send(json.dumps({"type": "input_audio_buffer.commit"}))
                        elif event_type == "response.create":
                            await provider.send(json.dumps({"type": "response.create", "response": {"modalities": ["text", "audio"]}}))
                        elif event_type == "text":
                            await provider.send(json.dumps({"type": "conversation.item.create", "item": {"type": "message", "role": "user", "content": [{"type": "input_text", "text": event.get("text", "")}]}}))
                            await provider.send(json.dumps({"type": "response.create", "response": {"modalities": ["text", "audio"]}}))
                        elif event_type == "interrupt":
                            await provider.send(json.dumps({"type": "response.cancel"}))
                            await browser.send_json({"type": "response.interrupted"})

                async def provider_to_browser():
                    input_transcript = ""
                    response_requested = False
                    async for raw in provider:
                        event = json.loads(raw)
                        event_type = event.get("type", "")
                        if event_type in ("response.audio.delta", "response.output_audio.delta"):
                            await browser.send_json({"type": "audio.delta", "audio": event.get("delta", "")})
                        elif event_type in ("response.audio_transcript.delta", "response.text.delta", "response.output_text.delta"):
                            await browser.send_json({"type": "assistant.transcript.delta", "text": event.get("delta", "")})
                        elif event_type in ("conversation.item.input_audio_transcription.delta", "input_audio_transcription.delta", "conversation.item.input_audio_transcription.text", "input_audio_buffer.transcription.delta", "conversation.item.input_audio_transcription.part", "input_audio_buffer.transcription.text") or ("input_audio" in event_type and "transcription" in event_type and any(key in event for key in ("delta", "text", "transcript", "stash")) and not any(word in event_type for word in ("completed", "done", "failed"))):
                            delta = event.get("delta") or event.get("text") or event.get("stash") or event.get("transcript") or ""
                            input_transcript = delta if delta.startswith(input_transcript) else input_transcript + delta
                            await browser.send_json({"type": "input.transcript.delta", "delta": delta, "text": input_transcript})
                        elif event_type in ("conversation.item.input_audio_transcription.completed", "input_audio_transcription.completed", "conversation.item.input_audio_transcription.done", "input_audio_buffer.transcription.completed", "conversation.item.input_audio_transcription.finished"):
                            transcript = event.get("transcript") or event.get("text") or event.get("stash") or input_transcript
                            input_transcript = transcript
                            await browser.send_json({"type": "input.transcript", "text": transcript})
                            await browser.send_json({"type": "input.transcription.completed", "text": transcript})
                            if transcript.strip() and not response_requested:
                                await browser.send_json({"type": "response.requested", "text": transcript})
                                await provider.send(json.dumps({"type": "response.create", "response": {"modalities": ["text", "audio"]}}))
                                response_requested = True
                        elif event_type == "input_audio_buffer.speech_started":
                            response_requested = False
                            input_transcript = ""
                            await browser.send_json({"type": event_type})
                            await browser.send_json({"type": "response.interrupted", "automatic": True})
                        elif event_type == "input_audio_buffer.speech_stopped":
                            await browser.send_json({"type": event_type})
                        elif event_type in ("response.created", "response.output_item.added"):
                            response_requested = True
                        elif event_type in ("response.done", "response.cancelled"):
                            response_requested = False
                            await browser.send_json({"type": event_type})
                        elif event_type == "error":
                            error = event.get("error", {})
                            await browser.send_json({
                                "type": "error",
                                "code": error.get("code", "realtime_provider_error"),
                                "message": error.get("message", "Realtime 服务错误"),
                                "event": error.get("event_id", ""),
                            })

                await asyncio.gather(browser_to_provider(), provider_to_browser())
        except WebSocketDisconnect:
            return
        except Exception as error:
            try:
                await browser.send_json({"type": "error", "message": str(error)})
            except Exception:
                pass

# backend/model.py
# NeuroCaption - AI-Powered Image Caption Generator
# Uses Ollama with LLaVA for LOCAL image analysis (no API needed!)

import os
import io
import base64
import hashlib
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from PIL import Image

# Ollama configuration
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
VISION_MODEL = os.getenv("VISION_MODEL", "moondream")
TEXT_MODEL = os.getenv("TEXT_MODEL", "llama3.2:3b")


def _fast_local_enabled() -> bool:
    """Set FAST_LOCAL=1 for smaller vision/text token budgets (laptops, 16GB RAM)."""
    return os.getenv("FAST_LOCAL", "").lower() in ("1", "true", "yes", "on")


def _int_env(name: str, *, fast: int, normal: int) -> int:
    raw = os.getenv(name)
    if raw is not None and str(raw).strip() != "":
        try:
            return int(raw)
        except ValueError:
            pass
    return fast if _fast_local_enabled() else normal

# ================= IMAGE UTILITIES =================

def load_image_bytes(image_bytes):
    """Load image from bytes and convert to RGB."""
    try:
        image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        return image
    except Exception as e:
        print(f"❌ Error loading image: {e}")
        return None

def image_to_base64(image: Image.Image) -> str:
    """Convert PIL Image to base64 string."""
    buffer = io.BytesIO()
    # Resize if too large for faster processing
    try:
        max_size = int(
            os.getenv(
                "VISION_MAX_SIZE",
                str(320 if _fast_local_enabled() else 384),
            )
        )
    except Exception:
        max_size = 320 if _fast_local_enabled() else 384
    if max(image.size) > max_size:
        ratio = max_size / max(image.size)
        new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
        image = image.resize(new_size, Image.Resampling.BILINEAR)
    
    try:
        quality = int(
            os.getenv(
                "VISION_JPEG_QUALITY",
                str(78 if _fast_local_enabled() else 85),
            )
        )
    except Exception:
        quality = 78 if _fast_local_enabled() else 85
    image.save(buffer, format="JPEG", quality=quality)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")

# ================= IMAGE ANALYSIS (Ollama LLaVA) =================

IMAGE_ANALYSIS_CACHE = {}
# Bump when vision/tag pipeline changes so stale descriptions are not reused.
_VISION_CACHE_KEY_VER = "2"

def _ensure_vision_model_available(model_name: str) -> str:
    try:
        installed = _installed_models()
    except Exception:
        installed = set()
    if not installed:
        return model_name
    if model_name in installed:
        return model_name
    preferred = ["bakllava:latest", "llava:latest", "moondream:latest", "moondream"]
    for p in preferred:
        if p in installed:
            return p
    return next(iter(installed))

def _ensure_text_model_available(model_name: str) -> str:
    try:
        installed = _installed_models()
    except Exception:
        installed = set()
    if not installed:
        return model_name
    if model_name in installed:
        return model_name
    # Never use vision models here; prefer common text LLMs only.
    preferred = [
        "llama3.2:3b", "llama3.2:latest", "llama3.1:8b", "llama3.1:latest",
        "mistral", "phi3", "gemma2", "qwen2", "tinyllama", "llama2",
    ]
    for p in preferred:
        for m in installed:
            if p in m.lower() and not _is_likely_vision_model(m):
                return m
    picked = _pick_best_text_model(installed)
    if picked:
        return picked
    return next(iter(installed))


def _is_likely_vision_model(name: str) -> bool:
    """Vision / multimodal models must not be used for plain-text caption generation."""
    n = (name or "").lower()
    markers = (
        "llava", "bakllava", "moondream", "minicpm-v", "minicpm_v",
        "vision", "vl-", "-vl", "qwen-vl", "llama-vision", "cogvlm",
    )
    return any(m in n for m in markers)


def _pick_best_text_model(installed: set) -> str | None:
    """Pick the best non-vision model from installed set."""
    if not installed:
        return None
    preferred_order = [
        "gemma3:1b", "gemma3", "llama3.2:3b", "llama3.2:latest", "llama3.1:8b", "llama3.1:latest",
        "mistral", "mixtral", "phi3", "gemma2", "qwen2", "tinyllama", "llama2",
    ]
    lowered = {m: m.lower() for m in installed}
    for pref in preferred_order:
        for m, low in lowered.items():
            if pref in low and not _is_likely_vision_model(m):
                return m
    for m in sorted(installed):
        if not _is_likely_vision_model(m):
            return m
    return None


def _fallback_vision_model_for_text(installed: set) -> str | None:
    """
    If no text-only LLM is installed, moondream often handles short text better than bakllava.
    BakLLaVA without images can emit garbage (random glyphs/digits), especially for Hindi.
    """
    for name in ("moondream:latest", "moondream"):
        if name in installed:
            return name
    for m in sorted(installed):
        if "moondream" in m.lower():
            return m
    return None


def _caption_looks_like_gibberish(text: str) -> bool:
    """Detect vision-model or broken UTF-8 spam (e.g. random Devanagari digits/symbols)."""
    if not text or len(text) < 8:
        return False
    # Long single token with no word breaks
    if len(text) > 24 and " " not in text and "\n" not in text:
        return True
    # Mostly Devanagari digits (often hallucinated when the wrong model is used)
    dev_digit = sum(1 for c in text if "\u0966" <= c <= "\u096f")
    dev_letter = sum(1 for c in text if "\u0900" <= c <= "\u097f" and not ("\u0966" <= c <= "\u096f"))
    latin_letter = sum(1 for c in text if "a" <= c.lower() <= "z")
    letters = dev_letter + latin_letter
    if letters > 0 and dev_digit / max(letters, 1) > 0.35:
        return True
    # Decorative / combining spam
    spam_chars = sum(1 for c in text if c in "॥।ॐॱ॰")
    if len(text) > 12 and spam_chars / len(text) > 0.12:
        return True
    return False


def _get_active_text_model(installed_models=None) -> str:
    """
    Resolve a model for plain-text captioning. Never prefer vision models when a text LLM exists.
    """
    if installed_models is None:
        installed_models = _installed_models()
    if not installed_models:
        return TEXT_MODEL
    if TEXT_MODEL in installed_models and not _is_likely_vision_model(TEXT_MODEL):
        return TEXT_MODEL
    picked = _pick_best_text_model(installed_models)
    if picked:
        return picked
    if TEXT_MODEL in installed_models:
        return TEXT_MODEL
    mv = _fallback_vision_model_for_text(installed_models)
    if mv:
        print(
            "⚠️ No text-only LLM found (install e.g. ollama pull llama3.2:3b). "
            f"Using {mv} for captions — quality may vary."
        )
        return mv
    return next(iter(sorted(installed_models)))

def _extract_ollama_text(data: dict) -> str:
    description = ""
    if isinstance(data, dict):
        msg = data.get("message")
        if isinstance(msg, dict) and msg.get("content"):
            description = msg.get("content")
        elif data.get("response"):
            description = data.get("response")
        elif data.get("content"):
            description = data.get("content")
    if not description:
        try:
            import json
            import re
            response_str = json.dumps(data)
            content_match = re.search(r'"content"\s*:\s*"([^"]+)"', response_str)
            if content_match:
                description = content_match.group(1)
        except Exception:
            description = ""
    return (description or "").strip()


def _text_model_candidates(installed: set, preferred_model: str | None = None) -> list[str]:
    ordered = []

    def add(name: str | None):
        if not name or name in ordered:
            return
        if installed and name not in installed:
            return
        ordered.append(name)

    if preferred_model and not _is_likely_vision_model(preferred_model):
        add(preferred_model)

    picked = _pick_best_text_model(installed)
    add(picked)

    preferred_order = [
        "gemma3:1b", "gemma3", "llama3.2:3b", "llama3.2:latest", "llama3.1:8b",
        "llama3.1:latest", "mistral", "mixtral", "phi3", "gemma2", "qwen2",
        "tinyllama", "llama2",
    ]
    lowered = {m: m.lower() for m in installed}
    for pref in preferred_order:
        for name, low in lowered.items():
            if pref in low and not _is_likely_vision_model(name):
                add(name)

    for name in sorted(installed):
        if not _is_likely_vision_model(name):
            add(name)

    if not ordered:
        add(_fallback_vision_model_for_text(installed))
    return ordered

def _vision_prompt() -> str:
    return (
        "You are an expert at describing images. Look at this image carefully and provide a detailed description.\n\n"
        "Answer these questions in order:\n"
        "1. What is the main subject? (person, animal, object, scene)\n"
        "2. What other objects do you see?\n"
        "3. Where is this taking place? (indoor, outdoor, city, nature, etc.)\n"
        "4. Are there any people? If yes, what are they doing?\n"
        "5. What is the mood or feeling? (happy, calm, busy, etc.)\n"
        "6. Describe what you see in 2-3 sentences as a human would.\n\n"
        "Give detailed, specific answers. Don't say 'document' unless it's actually a document."
    )

def _vision_probe_prompt() -> str:
    return _vision_prompt()

def _vision_paragraph_prompt() -> str:
    return "Provide a detailed factual summary of this image based on the 12-point analysis: type, scene, objects, humans, animals, activity, text, context, mood, tags, risk, and technical type."

def _vision_focus_prompt() -> str:
    return "What is the main subject and type of this image? Answer in one detailed sentence."

def _call_ollama_vision(model_name: str, prompt: str, img_base64: str, np: int):
    default_use_chat = "1" if "moondream" in (model_name or "").lower() else "0"
    use_chat = os.getenv("VISION_USE_CHAT", default_use_chat).lower() in ("1", "true", "yes")
    if use_chat:
        url_chat = f"{OLLAMA_HOST}/api/chat"
        payload_chat = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt, "images": [img_base64]}],
            "stream": False,
            "options": {"num_predict": np, "temperature": 0.2},
        }
        try:
            response = requests.post(url_chat, json=payload_chat, timeout=60)
            response.raise_for_status()
            data = response.json()
            text = _extract_ollama_text(data)
            if text:
                return text, data
        except Exception:
            data = None
    else:
        data = None
    url_gen = f"{OLLAMA_HOST}/api/generate"
    payload_gen = {
        "model": model_name,
        "prompt": prompt,
        "images": [img_base64],
        "stream": False,
        "options": {"num_predict": np, "temperature": 0.2},
    }
    try:
        response = requests.post(url_gen, json=payload_gen, timeout=60)
        response.raise_for_status()
        data = response.json()
        text = _extract_ollama_text(data)
        if text:
            return text, data
    except Exception:
        data = None
    return "", data

def _call_ollama_text(model_name: str, prompt: str, np: int) -> str:
    text, _ = _call_ollama_generate(model_name, prompt, temperature=0.2, num_predict=np, timeout=60)
    return text


def _call_ollama_generate(
    model_name: str,
    prompt: str,
    *,
    temperature: float,
    num_predict: int,
    timeout: int = 60,
):
    url_gen = f"{OLLAMA_HOST}/api/generate"
    payload_gen = {
        "model": model_name,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": num_predict, "temperature": temperature},
    }
    try:
        response = requests.post(url_gen, json=payload_gen, timeout=timeout)
        if not response.ok:
            body = (response.text or "").strip()
            return "", f"HTTP {response.status_code}: {body[:300]}"
        data = response.json()
        return _extract_ollama_text(data), None
    except Exception as e:
        return "", str(e)


def _generate_text_with_fallback(
    prompt: str,
    *,
    preferred_model: str | None = None,
    temperature: float,
    num_predict: int,
    timeout: int = 60,
):
    installed = _installed_models()
    candidates = _text_model_candidates(installed, preferred_model)
    last_error = None
    for model_name in candidates:
        text, error = _call_ollama_generate(
            model_name,
            prompt,
            temperature=temperature,
            num_predict=num_predict,
            timeout=timeout,
        )
        cleaned = (text or "").replace('"', "").replace("'", "").strip()
        if cleaned and not _caption_looks_like_gibberish(cleaned):
            return cleaned, model_name, None
        if error:
            last_error = f"{model_name}: {error}"
    return "", preferred_model or _get_active_text_model(installed), last_error


def _clean_caption_text(text: str) -> str:
    cleaned = (text or "").strip()
    cleaned = cleaned.replace('"', "").replace("'", "").replace("“", "").replace("”", "").replace("‘", "").replace("’", "")
    prefixes = [
        "Okay, heres the caption:",
        "Okay, here is the caption:",
        "Heres a caption:",
        "Here is a caption:",
        "Heres the caption:",
        "Here’s the caption:",
        "Here is the caption:",
        "Caption:",
        "Final caption:",
        "Here you go:",
    ]
    lower = cleaned.lower()
    for prefix in prefixes:
        if lower.startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
            lower = cleaned.lower()
    if "\n\n" in cleaned:
        parts = [part.strip() for part in cleaned.split("\n\n") if part.strip()]
        if parts:
            cleaned = parts[-1]
    return cleaned.strip()

def _needs_structured_output(text: str) -> bool:
    if not text:
        return True
    # Require at least 5 of the 10 points to consider it "structured enough"
    required = [
        "Image Type:", "Main Subject:", "Objects:", 
        "Scene:", "Humans:", "Activity:", "Mood:", "Description:"
    ]
    count = sum(1 for label in required if label in text)
    return count < 5

def _looks_generic_analysis(text: str) -> bool:
    if not text:
        return True
    if "Error in analysis image" in text:
        return False
    lower = text.lower()
    # Check for the simpler 6-point format
    simple_labels = ["main subject", "other objects", "where is this", "are there any people", "mood or feeling", "describe what you see"]
    match_count = sum(1 for label in simple_labels if label in lower)
    if match_count >= 3:
        return False
        
    generic_phrases = [
        "photo worth sharing",
        "captivating photo",
        "interesting visual content",
    ]
    if any(p in lower for p in generic_phrases):
        return True
    return False

def _format_analysis_text(description: str, model_name: str) -> str:
    if not description:
        return ""
    prompt = (
        "Rewrite the following image description into EXACTLY 6 labeled lines:\n"
        "Objects: at least 4 specific items.\n"
        "Scene: location + time of day.\n"
        "Background: at least 3 specific elements.\n"
        "Mood: 3 or more emotions or vibes.\n"
        "Context: what is happening or likely story.\n"
        "Details: colors, lighting, pose, actions (at least 4 phrases).\n"
        "Use comma-separated phrases. Avoid generic words like beautiful, stunning.\n\n"
        f"Description:\n{description}"
    )
    formatted = _call_ollama_text(model_name, prompt, 240)
    return formatted.strip()

def _structured_from_multi_questions(img_base64: str, model_name: str) -> str:
    questions = [
        ("Objects", "List key objects in the image. Return comma-separated phrases only. No numbers or bullets."),
        ("Scene", "Describe the scene with location and time of day. Return a short comma-separated phrase. No numbers."),
        ("Background", "List notable background elements. Return comma-separated phrases only. No numbers or bullets."),
        ("Mood", "Describe the mood/emotions. Return comma-separated phrases only. No numbers."),
        ("Context", "What is happening or likely story? Return a short comma-separated phrase. No numbers."),
        ("Details", "List colors, lighting, pose, and actions. Return comma-separated phrases only. No numbers or bullets."),
    ]
    lines = []
    for label, q in questions:
        prompt = f"{q}\nBe specific. Avoid generic words."
        text, _ = _call_ollama_vision(model_name, prompt, img_base64, 96)
        text = (text or "").strip().replace("\n", " ")
        if not text:
            return ""
        lines.append(f"{label}: {text}")
    return "\n".join(lines)

def _structured_from_probe_questions(img_base64: str, model_name: str, np: int) -> str:
    questions = [
        ("Objects", "List visible objects with concrete nouns. If you see a dog, cat, person, beach, waves, sand, or palm trees, include those words. Return comma-separated phrases only."),
        ("Scene", "Describe the location and time of day. Use specific wording like beach at sunset, seaside at golden hour, or park in daylight. Return a short comma-separated phrase."),
        ("Background", "List 3+ background elements you can see. Return comma-separated phrases only."),
        ("Details", "List colors, lighting, pose, and actions. Return comma-separated phrases only.")
    ]
    lines = []
    for label, q in questions:
        text, _ = _call_ollama_vision(model_name, q, img_base64, np)
        text = (text or "").strip().replace("\n", " ")
        if not text:
            return ""
        lines.append(f"{label}: {text}")
    mood = "Mood: calm, happy, relaxed"
    context = "Context: a quiet moment in the scene"
    return "\n".join(lines + [mood, context])

def _binary_vision_check(img_base64: str, model_name: str, np: int, question: str) -> bool:
    prompt = f"{question}\nAnswer ONLY YES or NO."
    text, _ = _call_ollama_vision(model_name, prompt, img_base64, np)
    text = (text or "").strip().lower()
    if not text:
        return False
    if "yes" in text and "no" not in text:
        return True
    if text.startswith("yes"):
        return True
    return False

def _structured_from_binary_probe(img_base64: str, model_name: str, np: int) -> str:
    checks = {
        "dog": "Is there a dog in the image?",
        "cat": "Is there a cat in the image?",
        "person": "Is there a person in the image?",
        "beach": "Is this a beach or sandy shore?",
        "ocean": "Is there an ocean or sea visible?",
        "waves": "Are there waves visible?",
        "sand": "Is there sand visible?",
        "palm trees": "Are there palm trees visible?",
        "sunset": "Is the image taken at sunset or golden hour?",
        "paper": "Is there a paper, document, or book?",
        "car": "Is there a car or vehicle?",
        "text": "Is there visible text on a document or sign?",
    }
    detected = []
    for label, q in checks.items():
        if _binary_vision_check(img_base64, model_name, np, q):
            detected.append(label)
    
    objects = detected if detected else ["main subject"]
    
    scene_parts = []
    if "beach" in detected: scene_parts.append("beach")
    if "paper" in detected: scene_parts.append("office/study")
    if "car" in detected: scene_parts.append("road/outdoor")
    if "sunset" in detected: scene_parts.append("sunset")
    scene = ", ".join(scene_parts) if scene_parts else "generic setting"
    
    background = ["visible elements"]
    details = ["natural lighting", "clear focus"]
    if "text" in detected: details.append("visible text")
    
    mood = "neutral, calm"
    context = "a clear view of the subject"
    
    return "\n".join([
        f"Objects: {', '.join(objects)}",
        f"Scene: {scene}",
        f"Background: {', '.join(background)}",
        f"Mood: {mood}",
        f"Context: {context}",
        f"Details: {', '.join(details)}"
    ])

def _try_alternate_vision_models(img_base64: str, current_model: str) -> str:
    installed = _installed_models()
    candidates = [
        "bakllava:latest", "bakllava", "llava:latest", "llava",
        "moondream:latest", "moondream",
    ]
    seen = set()
    for model in candidates:
        if model == current_model or model in seen:
            continue
        seen.add(model)
        if model not in installed:
            continue
        # Increase token limit significantly so the 10-point analysis fits
        text, _ = _call_ollama_vision(model, _vision_prompt(), img_base64, 350)
        if text and not _looks_generic_analysis(text):
            return text
        focus, _ = _call_ollama_vision(model, _vision_focus_prompt(), img_base64, 150)
        if focus and not _looks_generic_analysis(focus) and len(focus.split()) >= 3:
            return focus
        probe_text = _structured_from_binary_probe(img_base64, model, 150)
        if probe_text and not _looks_generic_analysis(probe_text):
            return probe_text
    return ""

def _is_good_structured_output(text: str) -> bool:
    if _needs_structured_output(text):
        return False
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    if len(lines) < 6:
        return False
    for line in lines:
        if ":" not in line:
            return False
        _, value = line.split(":", 1)
        value = value.strip()
        if len(value) < 6:
            return False
        if not any(ch.isalpha() for ch in value):
            return False
    return True

def _structured_from_keywords(text: str) -> str:
    lower = (text or "").lower()
    objects = []
    # General objects
    keywords = ["dog", "cat", "person", "man", "woman", "child", "car", "vehicle", "paper", "document", "diagram", "text", "book", "computer", "phone"]
    for k in keywords:
        if k in lower:
            objects.append(k)
    
    if not objects:
        objects = ["main subject"]

    scene = []
    if any(k in lower for k in ["beach", "seaside", "shore"]): scene.append("beach")
    if any(k in lower for k in ["indoor", "indoors", "room", "office"]): scene.append("indoors")
    if any(k in lower for k in ["outdoor", "outdoors", "nature"]): scene.append("outdoors")
    if "sunset" in lower: scene.append("sunset")
    
    if not scene:
        scene = ["generic setting"]

    background = ["background elements"]
    mood = ["neutral", "calm"]
    context = "a clear view of the scene"
    details = ["natural lighting", "clear focus"]
    
    if "text" in lower: details.append("visible text")

    return "\n".join([
        f"Objects: {', '.join(dict.fromkeys(objects))}",
        f"Scene: {', '.join(dict.fromkeys(scene))}",
        f"Background: {', '.join(dict.fromkeys(background))}",
        f"Mood: {', '.join(dict.fromkeys(mood))}",
        f"Context: {context}",
        f"Details: {', '.join(dict.fromkeys(details))}",
    ])


def _language_is_english(language: str) -> bool:
    if not language:
        return True
    return str(language).strip().lower() in ("english", "en", "eng")


def _output_language_rules(language: str) -> str:
    lang = (language or "English").strip() or "English"
    if _language_is_english(lang):
        return "LANGUAGE: Write the whole caption in natural English."
    script_note = ""
    if lang.lower() == "hindi":
        script_note = " Use Devanagari script (हिंदी) for Hindi words."
    return (
        f"LANGUAGE (mandatory): Write the ENTIRE caption ONLY in {lang}. "
        f"Do not use English words, phrases, or sentences.{script_note} "
        f"Proper nouns (people, brands, places) may stay in their usual spelling. "
        f"Hashtags may use Latin characters but should be words natural for {lang} speakers."
    )


def _ensure_caption_language(caption: str, language: str, image_analysis: str) -> str:
    """Second pass for small models (e.g. tinyllama) that ignore language in the main prompt."""
    if _language_is_english(language):
        return caption or ""
    text = (caption or "").strip()
    if len(text) < 6:
        return text
    lang = str(language).strip()
    try:
        text_np = _int_env("TEXT_NUM_PREDICT", fast=48, normal=68)
        cap_min = 120 if _fast_local_enabled() else 160
        text_np = max(text_np, cap_min)
        script_hint = ""
        if lang.lower() == "hindi":
            script_hint = (
                " Write normal Hindi words in Devanagari. "
                "Do NOT output random symbols, danda rows, Om signs, or meaningless number sequences. "
                "Use 1–3 short readable sentences with spaces between words."
            )
        prompt = (
            f"Rewrite this social media caption completely in {lang}.\n"
            f"STRICT RULES:\n"
            f"- Every word of the caption text must be in {lang} only. No English.\n"
            f"- For Hindi, use Devanagari script for words (not decorative symbols).{script_hint}\n"
            f"- Keep the same emojis if appropriate; keep hashtags but make hashtag wording fit {lang}.\n"
            f"- Match the scene described in the image context.\n\n"
            f"IMAGE CONTEXT:\n{(image_analysis or '')[:900]}\n\n"
            f"CAPTION:\n{text}\n\n"
            f"Output ONLY the final caption in {lang}."
        )
        out, used_model, error = _generate_text_with_fallback(
            prompt,
            preferred_model=_get_active_text_model(),
            temperature=0.3,
            num_predict=text_np,
            timeout=90,
        )
        out = _clean_caption_text(out)
        if out and len(out) >= 6 and sum(1 for c in out if c.isalpha()) >= 4:
            return out
        if error:
            print(f"Language finalize fallback for {lang} using {used_model}: {error}")
    except Exception as e:
        print(f"Language finalize ({lang}): {e}")
    return text


def _detect_caption_entities(image_analysis: str) -> dict:
    lower = (image_analysis or "").lower()
    return {
        "dog": "dog" in lower or "puppy" in lower or "retriever" in lower,
        "beach": any(word in lower for word in ["beach", "sand", "shore", "seaside"]),
        "ocean": any(word in lower for word in ["ocean", "sea", "waves", "water"]),
        "sunset": any(word in lower for word in ["sunset", "golden hour", "sunrise", "orange sky"]),
        "palm": "palm" in lower,
        "lighthouse": "lighthouse" in lower,
    }


def _localized_caption_from_analysis(
    image_analysis: str,
    include_emoji: bool,
    include_hashtags: bool,
    hashtag_new_line: bool,
    language: str = "English",
) -> str:
    lang = (language or "English").strip() or "English"
    entities = _detect_caption_entities(image_analysis)

    if lang.lower() == "hindi":
        if entities["dog"] and entities["beach"] and entities["sunset"]:
            caption = "समुद्र किनारे सुनहरे आसमान के साथ यह खुश कुत्ता पल को और भी खूबसूरत बना रहा है।"
        elif entities["dog"] and entities["beach"]:
            caption = "समुद्र किनारे बैठा यह प्यारा कुत्ता पूरे दृश्य को खास बना रहा है।"
        elif entities["dog"]:
            caption = "यह प्यारा कुत्ता अपने खुश चेहरे से दिल जीत रहा है।"
        else:
            caption = "यह खूबसूरत पल अपनी शांत और खास भावना के साथ यादगार लग रहा है।"
        emoji = " 🐶" if include_emoji and entities["dog"] else (" 🌅" if include_emoji and entities["sunset"] else (" ✨" if include_emoji else ""))
        tags = []
        if include_hashtags:
            if entities["dog"]:
                tags.append("#कुत्ता")
            if entities["beach"]:
                tags.append("#समुद्रकिनारा")
            if entities["sunset"]:
                tags.append("#सूर्यास्त")
            if not tags:
                tags.append("#पल")
        body = caption + emoji
        return (body + ("\n" if hashtag_new_line else " ") + " ".join(tags)).strip() if tags else body.strip()

    if lang.lower() == "spanish":
        if entities["dog"] and entities["beach"] and entities["sunset"]:
            caption = "Un perro feliz en la playa al atardecer, con olas suaves y una luz dorada preciosa."
        elif entities["dog"] and entities["beach"]:
            caption = "Un perro adorable disfrutando de la playa y la brisa del mar."
        elif entities["dog"]:
            caption = "Un perro adorable robándose toda la atención con su energía feliz."
        else:
            caption = "Un momento bonito lleno de calma, color y buena vibra."
        emoji = " 🐶" if include_emoji and entities["dog"] else (" 🌅" if include_emoji and entities["sunset"] else (" ✨" if include_emoji else ""))
        tags = []
        if include_hashtags:
            if entities["dog"]:
                tags.append("#perro")
            if entities["beach"]:
                tags.append("#playa")
            if entities["sunset"]:
                tags.append("#atardecer")
            if not tags:
                tags.append("#momento")
        body = caption + emoji
        return (body + ("\n" if hashtag_new_line else " ") + " ".join(tags)).strip() if tags else body.strip()

    if lang.lower() == "french":
        if entities["dog"] and entities["beach"] and entities["sunset"]:
            caption = "Un chien heureux sur la plage au coucher du soleil, avec des vagues douces et une lumière dorée."
        elif entities["dog"] and entities["beach"]:
            caption = "Un chien adorable profite de la plage et de l’air marin."
        elif entities["dog"]:
            caption = "Un chien adorable attire toute l’attention avec son énergie joyeuse."
        else:
            caption = "Un beau moment rempli de calme, de couleur et de douceur."
        emoji = " 🐶" if include_emoji and entities["dog"] else (" 🌅" if include_emoji and entities["sunset"] else (" ✨" if include_emoji else ""))
        tags = []
        if include_hashtags:
            if entities["dog"]:
                tags.append("#chien")
            if entities["beach"]:
                tags.append("#plage")
            if entities["sunset"]:
                tags.append("#coucherdusoleil")
            if not tags:
                tags.append("#moment")
        body = caption + emoji
        return (body + ("\n" if hashtag_new_line else " ") + " ".join(tags)).strip() if tags else body.strip()

    if lang.lower() == "german":
        if entities["dog"] and entities["beach"] and entities["sunset"]:
            caption = "Ein glücklicher Hund am Strand bei Sonnenuntergang, mit sanften Wellen und goldenem Licht."
        elif entities["dog"] and entities["beach"]:
            caption = "Ein süßer Hund genießt den Strand und die frische Meeresluft."
        elif entities["dog"]:
            caption = "Ein süßer Hund zieht mit seiner fröhlichen Energie alle Blicke auf sich."
        else:
            caption = "Ein schöner Moment voller Ruhe, Farbe und guter Stimmung."
        emoji = " 🐶" if include_emoji and entities["dog"] else (" 🌅" if include_emoji and entities["sunset"] else (" ✨" if include_emoji else ""))
        tags = []
        if include_hashtags:
            if entities["dog"]:
                tags.append("#hund")
            if entities["beach"]:
                tags.append("#strand")
            if entities["sunset"]:
                tags.append("#sonnenuntergang")
            if not tags:
                tags.append("#moment")
        body = caption + emoji
        return (body + ("\n" if hashtag_new_line else " ") + " ".join(tags)).strip() if tags else body.strip()

    scene = ""
    mood = ""
    objects = ""
    for line in (image_analysis or "").splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip().lower()
        value = value.strip()
        if key == "scene" and not scene:
            scene = value
        if key == "mood" and not mood:
            mood = value
        if key == "objects" and not objects:
            objects = value
    if not objects and entities["dog"]:
        objects = "dog"
    if not scene:
        if entities["beach"] and entities["sunset"]:
            scene = "the beach at sunset"
        elif entities["beach"]:
            scene = "the beach"
    mood_word = mood.split(",")[0].strip() if mood else ""
    scene_word = scene.split(",")[0].strip() if scene else ""
    object_word = objects.split(",")[0].strip() if objects else ""
    if mood_word and scene_word:
        caption = f"A {mood_word} moment at {scene_word}."
    elif scene_word:
        caption = f"A moment at {scene_word}."
    elif object_word:
        caption = f"{object_word.capitalize()} in a quiet moment."
    else:
        caption = "A moment worth sharing."
    emoji = ""
    lower = (image_analysis or "").lower()
    if include_emoji:
        if "dog" in lower or "puppy" in lower or entities["dog"]:
            emoji = " 🐶"
        elif "beach" in lower or "ocean" in lower or "sea" in lower or entities["beach"]:
            emoji = " 🌊"
        else:
            emoji = " ✨"
    tags = []
    if include_hashtags:
        if "dog" in lower or "puppy" in lower or entities["dog"]:
            tags.append("#dog")
        if "beach" in lower or "ocean" in lower or "sea" in lower or entities["beach"]:
            tags.append("#beach")
        if "sunset" in lower or entities["sunset"]:
            tags.append("#sunset")
        if not tags:
            tags.append("#photo")
        tags.append("#moment")
    if tags:
        if hashtag_new_line:
            caption = caption + emoji + "\n" + " ".join(tags)
        else:
            caption = caption + emoji + " " + " ".join(tags)
    else:
        caption = caption + emoji
    return caption.strip()


def _fallback_caption(
    image_analysis: str,
    include_emoji: bool,
    include_hashtags: bool,
    hashtag_new_line: bool,
    language: str = "English",
) -> str:
    caption = _localized_caption_from_analysis(
        image_analysis,
        include_emoji,
        include_hashtags,
        hashtag_new_line,
        language,
    )
    if _language_is_english(language):
        return caption
    localized = _ensure_caption_language(caption.strip(), language, image_analysis or "")
    return localized if localized else caption

def analyze_image_with_vision(image: Image.Image) -> str:
    """
    Use Ollama vision models (Llava, BakLLaVA, Moondream, etc.) to analyze the image locally.
    """
    try:
        img_base64 = image_to_base64(image)
        cache_key = hashlib.sha256(
            f"{_VISION_CACHE_KEY_VER}:{img_base64}".encode("utf-8")
        ).hexdigest()
        if cache_key in IMAGE_ANALYSIS_CACHE:
            return IMAGE_ANALYSIS_CACHE[cache_key]
        
        # Increase prediction tokens for detailed 12-point analysis
        np = _int_env("VISION_NUM_PREDICT", fast=250, normal=450)
        raw_vision = os.getenv("VISION_MODEL", VISION_MODEL)
        model_name = _ensure_vision_model_available(raw_vision)
        print(f"📸 Analyzing image with Ollama {model_name} (Detailed Analysis)...")
        
        # Primary structured analysis
        structured_prompt = _vision_prompt()
        analysis, data = _call_ollama_vision(model_name, structured_prompt, img_base64, np)
        
        # Validate analysis quality
        analysis_ok = (
            analysis
            and not _looks_generic_analysis(analysis)
            and len(analysis.strip()) >= 50
            and "Error in analysis image" not in analysis
        )
        
        if analysis_ok:
            print(f"✅ Vision analysis successful ({len(analysis)} chars)")
            IMAGE_ANALYSIS_CACHE[cache_key] = analysis
            return analysis

        # Try alternate models if first attempt was weak
        alt = _try_alternate_vision_models(img_base64, model_name)
        if alt and len(alt) > 30:
            print(f"✅ Vision analysis (alternate model): {alt[:100]}...")
            IMAGE_ANALYSIS_CACHE[cache_key] = alt
            return alt

        if analysis and ("error" in analysis.lower() or "fail" in analysis.lower()):
            return "Error in analysis image"

        # Last resort fallback message
        return analysis if analysis and len(analysis) > 10 else "Error in analysis image"
        
    except Exception as e:
        print(f"❌ Vision analysis error: {e}")
        return "Error in analysis image"

def analyze_image_with_vision_model(image: Image.Image, model_name: str) -> str:
    try:
        img_base64 = image_to_base64(image)
        cache_key = hashlib.sha256((model_name + ":" + img_base64).encode("utf-8")).hexdigest()
        if cache_key in IMAGE_ANALYSIS_CACHE:
            return IMAGE_ANALYSIS_CACHE[cache_key]
        np = _int_env("VISION_NUM_PREDICT", fast=250, normal=450)
        resolved_model = _ensure_vision_model_available(model_name)
        if resolved_model != model_name:
            os.environ["VISION_MODEL"] = resolved_model
            globals()["VISION_MODEL"] = resolved_model
        description, _ = _call_ollama_vision(resolved_model, _vision_prompt(), img_base64, np)
        if description and len(description) > 20:
            if _needs_structured_output(description) or "photo with interesting visual content" in description.lower() or "captivating photo worth sharing" in description.lower():
                description = _structured_from_keywords(description)
            if _is_good_structured_output(description):
                IMAGE_ANALYSIS_CACHE[cache_key] = description
            return description
        fallback = "A photo with interesting visual content."
        return fallback
    except Exception as e:
        print(f"❌ Vision analysis error ({model_name}): {e}")
        return "A captivating photo worth sharing."

# ================= CAPTION GENERATION (Ollama) =================

def generate_caption_with_ollama(
    image_analysis: str,
    platform: str,
    platform_type: str,
    mode: str,
    mode_style: str,
    creativity: int,
    length: int,
    include_emoji: bool,
    include_hashtags: bool,
    hashtag_new_line: bool,
    add_hook: bool,
    user_prompt: str,
    language: str,
    variant_number: int = 1
) -> str:
    """
    Generate a single caption using Ollama.
    """
    try:
        installed = _installed_models()
        text_model = _get_active_text_model(installed)
        # Build creative direction based on variant - more diverse angles
        creative_angles = [
            "Focus on deep emotions and feelings - be poetic and heartfelt",
            "Be witty, clever, and include a subtle pun or wordplay", 
            "Create mystery and curiosity - make people want to know more",
            "Be inspirational and motivational - uplift the reader",
            "Be playful, fun, and lighthearted - bring joy",
            "Be philosophical and thought-provoking",
            "Be bold and confident - own the moment",
            "Be nostalgic and reflective"
        ]
        angle = creative_angles[(variant_number - 1) % len(creative_angles)]
        
        # Length guidance
        if length < 35:
            length_guide = "Keep it SHORT and punchy (under 50 words)"
        elif length < 70:
            length_guide = "Make it MEDIUM length with good flow (50-100 words)"
        else:
            length_guide = "Create a LONGER, storytelling caption (100-150 words)"
        
        # Build rules
        emoji_rule = "Include 2-4 relevant emojis that enhance the message" if include_emoji else "Do NOT use any emojis"
        
        if include_hashtags:
            if hashtag_new_line:
                hashtag_rule = "Add 3-5 relevant hashtags on a NEW LINE at the end"
            else:
                hashtag_rule = "Weave 3-5 relevant hashtags naturally into the caption"
        else:
            hashtag_rule = "Do NOT include any hashtags"
        
        hook_rule = "Start with an attention-grabbing hook or question" if add_hook else ""
        
        # MODE-SPECIFIC INSTRUCTIONS
        mode_instructions = {
            "Social": "Write a casual, relatable caption that connects with followers. Be authentic and conversational.",
            "Funny": "Be humorous, witty, and entertaining. Use wordplay, jokes, or amusing observations. Make people laugh!",
            "Story": "Tell a story or share a moment. Create a narrative that draws people in. Be descriptive and emotional.",
            "Business": "Be professional but engaging. Focus on value, insights, or achievements. Build credibility.",
            "Education": "Teach or inform. Share knowledge, tips, or facts. Be clear and helpful."
        }
        
        # STYLE-SPECIFIC INSTRUCTIONS - All styles for all modes
        style_instructions = {
            # Social styles
            "Chill": "Keep the tone relaxed, laid-back, and effortless. No pressure, just vibes.",
            "Energetic": "Be excited, enthusiastic, and high-energy! Use exclamation marks and dynamic language!",
            "Aesthetic": "Focus on beauty, visuals, and mood. Use poetic, artistic language. Create atmosphere.",
            "Cozy": "Be warm, comfortable, and inviting. Like a hug in words. Homey and heartfelt.",
            "Bold": "Be confident, powerful, and unapologetic. Make a statement. Stand out!",
            "Dreamy": "Be whimsical, ethereal, and imaginative. Soft, romantic, and enchanting vibes.",
            
            # Funny styles
            "Sarcastic": "Use sarcasm and dry wit. Be ironic and clever. Say the opposite of what you mean.",
            "Self-deprecating": "Make fun of yourself in a relatable way. Be humble and self-aware. Laughing at yourself.",
            "Absurd": "Be completely ridiculous and random. Unexpected humor. Make no sense in the best way.",
            "Relatable": "Capture everyday struggles everyone experiences. 'It me' energy. Shared experiences.",
            "Dark Humor": "Find humor in the dark or difficult. Edgy but not offensive. Unexpected twists.",
            "Punny": "Use puns, wordplay, and clever linguistic jokes. Dad joke energy but actually funny.",
            
            # Story styles
            "Inspirational": "Uplift and motivate. Share wisdom and hope. Make people believe in themselves.",
            "Emotional": "Touch the heart. Be vulnerable and raw. Create genuine emotional connection.",
            "Adventure": "Capture excitement and exploration. The thrill of new experiences. Living life fully.",
            "Life Lesson": "Share wisdom learned from experience. Meaningful takeaways. Growth mindset.",
            "Throwback": "Nostalgic and reflective. Looking back fondly. Remember when vibes.",
            "Mystery": "Create intrigue and suspense. Leave them wanting more. Curious and mysterious.",
            
            # Business styles
            "Motivational": "Inspire action and success. Hustle culture meets wisdom. Go-getter energy.",
            "Informative": "Share valuable knowledge and insights. Be the expert. Add clear value.",
            "Achievement": "Celebrate wins and milestones. Humble brag tastefully. Show results.",
            "Networking": "Build connections. Professional but personable. Open doors.",
            "Thought Leader": "Share innovative ideas and perspectives. Be the expert voice. Industry insights.",
            
            # Education styles
            "Tutorial": "Step-by-step guidance. Clear and easy to follow. Helpful teacher energy.",
            "Tips": "Quick, actionable advice. Bite-sized wisdom. Easy wins.",
            "Facts": "Share interesting knowledge. Did you know energy. Informative and engaging.",
            "How-To": "Practical instructions. Make it doable. Empower the learner.",
            "Explainer": "Break down complex topics. Make it simple. Clear communication."
        }
        
        mode_guide = mode_instructions.get(mode, mode_instructions["Social"])
        style_guide = style_instructions.get(mode_style, "Match the style: " + mode_style)
        
        # PLATFORM-SPECIFIC INSTRUCTIONS
        platform_instructions = {
            "Instagram": "Instagram style: Visual-first, use line breaks for readability, aesthetic language, engaging hooks",
            "TikTok": "TikTok style: Trendy, use viral phrases, reference sounds/trends, casual Gen-Z language, punchy",
            "LinkedIn": "LinkedIn style: Professional yet personable, thought leadership, career insights, networking tone",
            "Twitter": "Twitter/X style: Concise and punchy, within 280 characters when possible, witty, conversation-starting",
            "YouTube": "YouTube style: Descriptive, include call-to-action, engaging thumbnail energy, audience retention focus",
            "Other": "General social media style: Engaging and shareable"
        }
        
        # CONTENT TYPE-SPECIFIC INSTRUCTIONS
        content_type_instructions = {
            # Instagram
            "Post": "Feed post: Polished, storytelling, engagement-focused, can be longer",
            "Story": "Story: Casual, in-the-moment, conversational, ephemeral vibe",
            "Reel": "Reel: Trendy, hook-first, quick impact, viral potential",
            "Carousel": "Carousel: Educational or journey format, each slide matters",
            # TikTok
            "Video": "TikTok video: Hook in first words, trending format, relatable",
            "Meme": "Meme content: Funny, relatable, internet culture references",
            "Motivation": "Motivational: Inspiring, uplifting, shareable wisdom",
            "Tutorial": "Tutorial: Step-by-step, helpful, clear instructions",
            # LinkedIn
            "Personal": "Personal brand: Authentic story, career journey, lessons learned",
            "Company": "Company post: Brand voice, professional, value-driven",
            "Achievement": "Achievement post: Celebrate success, humble yet proud, gratitude",
            "Article": "Article teaser: Thought-provoking, drive clicks, professional insight",
            # Twitter
            "Tweet": "Tweet: Sharp, witty, under 280 chars, conversation starter",
            "Thread": "Thread opener: Hook that makes people want the full story",
            "Quote": "Quote tweet: Add perspective, commentary, or humor",
            "Reply": "Reply style: Engaging, conversational, community building",
            # YouTube
            "Shorts": "Shorts: Quick hook, trend-aware, immediate impact",
            "Community": "Community post: Casual, engagement-focused, polls/questions work well",
            # Other
            "General": "General: Engaging and versatile",
            "Blog": "Blog teaser: Intriguing, drives traffic, value preview",
            "Email": "Email subject/preview: Click-worthy, personal, urgent"
        }
        
        platform_guide = platform_instructions.get(platform, platform_instructions["Other"])
        content_guide = content_type_instructions.get(platform_type, "Optimize for " + platform_type)
        
        # Handle empty user prompt - make caption based purely on image
        if user_prompt and user_prompt.strip():
            user_context = f"\nUser's specific request: {user_prompt}"
        else:
            user_context = "\nNote: Create the caption based PURELY on what you see in the image description. Be creative and engaging!"

        lang_rules = _output_language_rules(language)
        
        prompt = f"""You are an expert social media caption writer. {lang_rules}

Generate ONE unique, creative caption.

IMAGE DESCRIPTION (What the AI sees in the photo):
{image_analysis}

PLATFORM: {platform} - {platform_type}
{platform_guide}
{content_guide}

MODE: {mode}
{mode_guide}

STYLE: {mode_style}
{style_guide}

REQUIREMENTS:
- Creative angle: {angle}
- {length_guide}
- {emoji_rule}
- {hashtag_rule}
{hook_rule}
- {lang_rules}
{user_context}

CRITICAL:
- {lang_rules}
- Your caption MUST be optimized for {platform} {platform_type} - {content_guide.lower()}
- Your caption MUST match the {mode} mode - {mode_guide.lower()}
- Your caption MUST have a {mode_style} feel - {style_guide.lower()}
- Make it relevant to what's ACTUALLY in the image
- Be creative and unique - don't use generic phrases

Generate ONE perfect caption. Output ONLY the caption text, nothing else."""

        # Adjust temperature based on creativity and variant number
        base_temp = 0.4 + (creativity / 100) * 0.6
        # Add variation for different variants
        variant_temp_adjust = 0.1 * ((variant_number % 3) - 1)  # -0.1, 0, +0.1
        temperature = max(0.1, min(0.9, base_temp + variant_temp_adjust))
        
        text_np = _int_env("TEXT_NUM_PREDICT", fast=52, normal=68)
        caption, used_model, text_error = _generate_text_with_fallback(
            prompt,
            preferred_model=text_model,
            temperature=temperature,
            num_predict=text_np,
            timeout=60,
        )
        caption = _clean_caption_text(caption)
        lower_caption = caption.lower()
        if "must create a new response" in lower_caption or "changing the threshold" in lower_caption or "!!!" in caption:
            caption = ""
        text_np = _int_env("TEXT_NUM_PREDICT", fast=52, normal=68)
        # Remove common prefixes
        for prefix in ["Here's a caption:", "Caption:", "Here you go:"]:
            if caption.lower().startswith(prefix.lower()):
                caption = caption[len(prefix):].strip()
        if not caption or len(caption) < 12 or sum(1 for c in caption if c.isalpha()) < 6:
            try:
                simple_prompt = (
                    f"{lang_rules}\n"
                    f"Write one {platform} {platform_type} caption. "
                    f"The caption must be ONLY in {language}. "
                    f"Base it only on: {image_analysis}. "
                    f"{emoji_rule}. {hashtag_rule}.\n"
                    f"Output ONLY the caption."
                )
                caption2, used_model, retry_error = _generate_text_with_fallback(
                    simple_prompt,
                    preferred_model=used_model or text_model,
                    temperature=min(temperature + 0.1, 0.8),
                    num_predict=max(text_np, 44 if _fast_local_enabled() else 56),
                    timeout=60,
                )
                caption2 = _clean_caption_text(caption2)
                if caption2 and len(caption2) >= 12:
                    caption = caption2
                elif retry_error:
                    text_error = retry_error
            except Exception:
                pass
        if caption and sum(1 for c in caption if c.isalpha()) < 6:
            caption = ""
        if caption:
            return _ensure_caption_language(caption, language, image_analysis)
        if text_error:
            print(f"Caption generation fallback ({used_model or text_model}): {text_error}")
        return _fallback_caption(
            image_analysis, include_emoji, include_hashtags, hashtag_new_line, language
        )
        
    except Exception as e:
        print(f"Caption generation error: {e}")
        return _fallback_caption(
            image_analysis, include_emoji, include_hashtags, hashtag_new_line, language
        )

def generate_caption_with_text_model(
    image_analysis: str,
    platform: str,
    platform_type: str,
    mode: str,
    mode_style: str,
    creativity: int,
    length: int,
    include_emoji: bool,
    include_hashtags: bool,
    hashtag_new_line: bool,
    add_hook: bool,
    user_prompt: str,
    language: str,
    model_name: str,
) -> str:
    try:
        base = generate_caption_with_ollama(
            image_analysis,
            platform,
            platform_type,
            mode,
            mode_style,
            creativity,
            length,
            include_emoji,
            include_hashtags,
            hashtag_new_line,
            add_hook,
            user_prompt,
            language,
            1,
        )
        if model_name == TEXT_MODEL:
            return base
        # Reuse assembled prompt by approximating via regenerate with same directives using chosen model_name
        temperature = 0.3 + (creativity / 100) * 0.7
        lang_rules = _output_language_rules(language)
        prompt = (
            f"{lang_rules}\n\n"
            f"Rewrite this caption to preserve meaning and style, improving clarity and flow.\n"
            f"The output MUST obey the language rules above.\n\n{base}\n\n"
            f"Output ONLY the caption."
        )
        caption, _, _ = _generate_text_with_fallback(
            prompt,
            preferred_model=model_name,
            temperature=temperature,
            num_predict=_int_env("TEXT_NUM_PREDICT", fast=52, normal=68),
            timeout=60,
        )
        caption = _clean_caption_text(caption)
        out = caption if caption else base
        return _ensure_caption_language(out, language, image_analysis)
    except Exception as e:
        print(f"Caption generation error ({model_name}): {e}")
        return base

# ================= MAIN GENERATION FUNCTION =================

def generate_styled_captions(
    image,
    platform,
    platform_type,
    mode,
    mode_style,
    creativity,
    length,
    include_emoji,
    include_hashtags,
    hashtag_new_line,
    add_hook,
    variants,
    user_prompt,
    language,
    image_analysis=None,
):
    """
    Main function to generate captions for an image.
    """
    print(f"\n📥 Image received for processing")
    print(f"🌍 Language: {language}")
    print(f"\n🚀 Generating {variants} captions for {platform} ({mode} - {mode_style})")
    
    # Step 1: Analyze the image with LLaVA
    if not image_analysis and image:
        image_analysis = analyze_image_with_vision(image)
    elif not image_analysis and not image:
        image_analysis = "No image provided. Base the caption only on the user prompt."
    
    # Step 2: Generate captions
    print(f"✍️ Generating captions with Ollama {TEXT_MODEL}...")
    
    max_variants = min(int(variants), 5)
    captions = [None] * max_variants
    with ThreadPoolExecutor(max_workers=max_variants) as executor:
        future_to_index = {
            executor.submit(
                generate_caption_with_ollama,
                image_analysis,
                platform,
                platform_type,
                mode,
                mode_style,
                creativity,
                length,
                include_emoji,
                include_hashtags,
                hashtag_new_line,
                add_hook,
                user_prompt,
                language,
                i + 1
            ): i for i in range(max_variants)
        }
        for future in as_completed(future_to_index):
            i = future_to_index[future]
            try:
                captions[i] = future.result()
            except Exception:
                captions[i] = _fallback_caption(
                    image_analysis,
                    include_emoji,
                    include_hashtags,
                    hashtag_new_line,
                    language,
                )
    
    print(f"✅ Generated {len(captions)} captions successfully!")
    
    return {
        "captions": captions,
        "platform": platform,
        "platform_type": platform_type,
        "mode": mode,
        "mode_style": mode_style,
    }

# ================= REFINE CAPTION =================

def refine_caption(caption: str, refine_type: str, mode: str, language: str) -> str:
    """
    Refine an existing caption based on the requested type.
    """
    try:
        lang_rules = _output_language_rules(language)
        # Different refinement strategies for different types
        refinement_prompts = {
            "expand": f"""{lang_rules}

Expand this caption to be more detailed and descriptive.
Add more context, emotions, and storytelling elements while keeping the core message.
The full output must follow the language rules above.

Original: {caption}

Output ONLY the expanded caption, nothing else.""",
            
            "shorten": f"""{lang_rules}

Make this caption shorter and more concise while keeping the main message.
Remove unnecessary words but preserve the core meaning and impact.
The full output must follow the language rules above.

Original: {caption}

Output ONLY the shortened caption, nothing else.""",
            
            "funnier": f"""{lang_rules}

Make this caption funnier and more humorous.
Add wit, jokes, puns, or amusing observations while keeping it relevant.
The full output must follow the language rules above.

Original: {caption}

Output ONLY the funnier version, nothing else.""",
            
            "positive": f"""{lang_rules}

Make this caption more positive and uplifting.
Focus on optimism, gratitude, and good vibes while keeping it authentic.
The full output must follow the language rules above.

Original: {caption}

Output ONLY the positive version, nothing else."""
        }
        
        prompt = refinement_prompts.get(refine_type.lower(), 
            f"""{lang_rules}

Rewrite this caption to be more {refine_type}.
Keep the same general meaning but make it {refine_type}.
The full output must follow the language rules above.

Original caption: {caption}

Output ONLY the new caption, nothing else.""")

        # Adjust temperature based on refinement type
        refine_temps = {
            "expand": 0.6,
            "shorten": 0.5, 
            "funnier": 0.8,
            "positive": 0.7
        }
        refined, _, _ = _generate_text_with_fallback(
            prompt,
            preferred_model=_get_active_text_model(),
            temperature=refine_temps.get(refine_type.lower(), 0.7),
            num_predict=_int_env("REFINE_NUM_PREDICT", fast=140, normal=220),
            timeout=60,
        )
        refined = _clean_caption_text(refined)
        
        out = refined if refined else caption
        return _ensure_caption_language(out, language, caption or "")
        
    except Exception as e:
        print(f"Refine error: {e}")
        return caption

# ================= HASHTAG GENERATION =================

def generate_hashtags(image_analysis: str, platform: str) -> list:
    """
    Generate trending hashtags based on the image analysis.
    """
    try:
        prompt = f"""Generate 30 relevant, trending, and high-reach hashtags for this image.
        
IMAGE DESCRIPTION:
{image_analysis}

PLATFORM: {platform}

REQUIREMENTS:
- Mix of broad (1M+ posts) and niche (10k-100k posts) tags
- Relevant to the specific content
- Do not include #fyp or generic tags unless relevant
- Output ONLY the hashtags separated by spaces, nothing else.
"""

        url = f"{OLLAMA_HOST}/api/generate"
        
        payload = {
            "model": TEXT_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.5,
                "num_predict": _int_env("HASHTAG_NUM_PREDICT", fast=180, normal=260),
            }
        }
        
        response = requests.post(url, json=payload, timeout=40)
        response.raise_for_status()
        
        data = response.json()
        hashtags_text = data.get("response", "").strip()
        
        # Extract hashtags
        import re
        hashtags = re.findall(r'#\w+', hashtags_text)
        
        # Deduplicate and limit to 30
        unique_hashtags = list(dict.fromkeys(hashtags))[:30]
        
        return unique_hashtags
        
    except Exception as e:
        print(f"❌ Hashtag generation error: {e}")
        return ["#instagood", "#photooftheday", "#trending", "#viral", "#love"]

# ================= MULTI-IMAGE ANALYSIS =================

def analyze_multiple_images(images: list) -> str:
    """
    Analyze multiple images and create a combined description.
    """
    descriptions = []
    
    print(f"📸 Analyzing {len(images)} images for carousel...")
    
    for i, img in enumerate(images):
        print(f"   - Analyzing image {i+1}...")
        try:
            desc = analyze_image_with_vision(img)
            descriptions.append(f"Image {i+1}: {desc}")
        except Exception as e:
            print(f"   ❌ Error analyzing image {i+1}: {e}")
            descriptions.append(f"Image {i+1}: Could not analyze")
        
    combined_prompt = f"""Summarize these image descriptions into ONE cohesive narrative for a carousel/album post.
    Identify the common theme, story progression, and overall mood.
    
    {chr(10).join(descriptions)}
    
    Output ONLY the summary description."""
    
    try:
        url = f"{OLLAMA_HOST}/api/generate"
        payload = {
            "model": TEXT_MODEL,
            "prompt": combined_prompt,
            "stream": False
        }
        
        response = requests.post(url, json=payload, timeout=60)
        response.raise_for_status()
        
        final_desc = response.json().get("response", "").strip()
        
        return final_desc if final_desc else descriptions[0]
        
    except Exception as e:
        print(f"❌ Multi-image summary error: {e}")
        return descriptions[0]

def _installed_models():
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=10)
        r.raise_for_status()
        names = [m.get("name") for m in r.json().get("models", []) if m.get("name")]
        return set(names)
    except Exception:
        return set()


def fetch_ollama_service_status(timeout: float = 5.0) -> dict:
    """
    Quick health check: GET /api/tags on Ollama. Used by GET /ollama-status.
    """
    from time import perf_counter

    t0 = perf_counter()
    out = {
        "ollama_host": OLLAMA_HOST,
        "reachable": False,
        "models": [],
        "model_count": 0,
        "latency_ms": None,
        "error": None,
        "vision_model": VISION_MODEL,
        "text_model": TEXT_MODEL,
    }
    try:
        r = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=max(0.5, float(timeout)))
        out["latency_ms"] = round((perf_counter() - t0) * 1000, 1)
        r.raise_for_status()
        data = r.json()
        names = sorted(
            n for n in (m.get("name") for m in data.get("models", []) if m.get("name")) if n
        )
        out["models"] = names
        out["model_count"] = len(names)
        out["reachable"] = True
    except requests.exceptions.Timeout:
        out["latency_ms"] = round((perf_counter() - t0) * 1000, 1)
        out["error"] = f"timeout after {timeout}s (is Ollama running?)"
    except requests.exceptions.RequestException as e:
        out["latency_ms"] = round((perf_counter() - t0) * 1000, 1)
        out["error"] = str(e)
    except Exception as e:
        out["latency_ms"] = round((perf_counter() - t0) * 1000, 1)
        out["error"] = str(e)
    return out

def _time_vision(model_name: str) -> float:
    from time import perf_counter
    img = Image.new("RGB", (256, 256), (128, 128, 128))
    t0 = perf_counter()
    _ = analyze_image_with_vision_model(img, model_name)
    t1 = perf_counter()
    return (t1 - t0) * 1000.0

def _time_text(model_name: str) -> float:
    from time import perf_counter
    url = f"{OLLAMA_HOST}/api/generate"
    payload = {"model": model_name, "prompt": "Hi", "stream": False, "options": {"num_predict": 20}}
    t0 = perf_counter()
    try:
        requests.post(url, json=payload, timeout=30).raise_for_status()
    except Exception:
        return 1e9
    t1 = perf_counter()
    return (t1 - t0) * 1000.0

def select_best_models():
    import json
    from pathlib import Path
    installed = _installed_models()
    norm = lambda s: s if ":" in s else f"{s}:latest"
    installed_norm = set(installed)
    vision_candidates = [m for m in [norm("moondream"), "bakllava:latest"] if m in installed_norm]
    text_candidates = [m for m in ["llama3.2:3b", "llama3.1:8b", norm("moondream")] if m in installed_norm]
    best_vision = None
    best_v = 1e9
    for m in vision_candidates:
        t = _time_vision(m)
        if t < best_v:
            best_v = t
            best_vision = m
    best_text = None
    best_t = 1e9
    for m in text_candidates:
        t = _time_text(m)
        if t < best_t:
            best_t = t
            best_text = m
    sel = {"vision": best_vision or VISION_MODEL, "text": best_text or TEXT_MODEL, "vision_ms": int(best_v) if best_vision else None, "text_ms": int(best_t) if best_text else None}
    try:
        cache = Path(__file__).parent / ".cache"
        cache.mkdir(exist_ok=True)
        (cache / "model_selection.json").write_text(json.dumps(sel))
    except Exception:
        pass
    os.environ["VISION_MODEL"] = sel["vision"]
    os.environ["TEXT_MODEL"] = sel["text"]
    globals()["VISION_MODEL"] = sel["vision"]
    globals()["TEXT_MODEL"] = sel["text"]
    return sel

def load_selected_models():
    import json
    from pathlib import Path
    try:
        p = Path(__file__).parent / ".cache" / "model_selection.json"
        if p.exists():
            sel = json.loads(p.read_text())
            installed = _installed_models()
            v = sel.get("vision") or VISION_MODEL
            t = sel.get("text") or TEXT_MODEL
            if v not in installed:
                v = "moondream:latest" if "moondream:latest" in installed else (next(iter(installed), v))
            if t not in installed:
                t = v if v in installed else (next(iter(installed), t))
            os.environ["VISION_MODEL"] = v
            os.environ["TEXT_MODEL"] = t
            globals()["VISION_MODEL"] = v
            globals()["TEXT_MODEL"] = t
            
            print("----------------------------------------")
            print(f"✅ Active Vision Model: {v}")
            print(f"✅ Active Text Model:   {t}")
            print("----------------------------------------")
            return sel
    except Exception:
        pass
    
    print("----------------------------------------")
    print(f"⚠️ Default Vision Model: {VISION_MODEL}")
    print(f"⚠️ Default Text Model:   {TEXT_MODEL}")
    print("----------------------------------------")
    return {"vision": VISION_MODEL, "text": TEXT_MODEL}

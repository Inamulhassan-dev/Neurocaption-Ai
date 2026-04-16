from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor
import traceback
import sys
import io
import os
from pathlib import Path

# Load .env from the Backend directory (ignored by git; copy from .env.example)
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

# Fix Windows console encoding for emojis
if sys.stdout and hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr and hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from model import load_image_bytes, generate_styled_captions, refine_caption, generate_hashtags, analyze_multiple_images
from model import select_best_models, load_selected_models, fetch_ollama_service_status

# ================= APP =================

app = FastAPI(title="AI Caption Lab API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("🚀 AI Caption Lab API Ready!")
load_selected_models()
if os.getenv("FAST_LOCAL", "").lower() in ("1", "true", "yes", "on"):
    print("⚡ FAST_LOCAL on: smaller vision/image budgets + shorter text generation (set FAST_LOCAL=0 to disable).")

@app.on_event("startup")
async def _auto_tune_on_start():
    try:
        import os
        if os.getenv("AUTO_TUNE", "0") == "1":
            select_best_models()
    except Exception:
        pass

# ================= MODELS =================

class RefineRequest(BaseModel):
    caption: str
    refine_type: str
    mode: Optional[str] = "Social"
    language: Optional[str] = "English"

class HashtagRequest(BaseModel):
    image_analysis: str
    platform: str

# ================= ROUTES =================

@app.get("/")
async def root():
    return {"status": "running"}

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ollama-status")
async def ollama_status(timeout: float = Query(5.0, ge=0.5, le=60)):
    """Check whether Ollama is reachable and list installed model names."""
    return fetch_ollama_service_status(timeout=timeout)

@app.post("/caption")
async def generate_caption(
    image: UploadFile = File(None),
    images: List[UploadFile] = File(None),
    platform: str = Form("Instagram"),
    platform_type: str = Form("Post"),
    mode: str = Form("Social"),
    mode_style: str = Form("Chill"),
    creativity: int = Form(50),
    length: int = Form(50),
    include_emoji: bool = Form(True),
    include_hashtags: bool = Form(True),
    hashtag_new_line: bool = Form(False),
    add_hook: bool = Form(False),
    variants: int = Form(1),
    user_prompt: str = Form(""),
    language: str = Form("English"),
    image_analysis: str = Form(""),
):
    print(f"\n📥 Request received")
    
    pil_images = []
    
    # Handle single or multiple images
    try:
        if images:
            print(f"   Processing {len(images)} images...")
            for img in images:
                content = await img.read()
                pil_images.append(load_image_bytes(content))
        elif image:
            print(f"   Processing single image: {image.filename}...")
            content = await image.read()
            pil_images.append(load_image_bytes(content))
        elif user_prompt:
            print(f"   Processing text-only prompt: {user_prompt[:50]}...")
        else:
            raise HTTPException(status_code=400, detail="Please provide either an image or a text prompt")
            
    except Exception as e:
        print(f"❌ Image processing error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # Check if we need to combine images (Multi-Image Support)
        if len(pil_images) > 1:
            from model import generate_caption_with_ollama
            
            # 1. Get combined analysis
            combined_analysis = analyze_multiple_images(pil_images)
            print(f"📝 Combined Analysis: {combined_analysis[:100]}...")
            
            # 2. Generate captions using the combined analysis
            captions = []
            max_variants = min(int(variants), 5)
            
            print(f"✍️ Generating captions from combined analysis...")
            for i in range(max_variants):
                caption = generate_caption_with_ollama(
                    image_analysis=combined_analysis,
                    platform=platform,
                    platform_type=platform_type,
                    mode=mode,
                    mode_style=mode_style,
                    creativity=creativity,
                    length=length,
                    include_emoji=include_emoji,
                    include_hashtags=include_hashtags,
                    hashtag_new_line=hashtag_new_line,
                    add_hook=add_hook,
                    user_prompt=user_prompt,
                    language=language,
                    variant_number=i + 1
                )
                captions.append(caption)
                
            return {
                "success": True,
                "captions": captions,
                "platform": platform,
                "platform_type": platform_type,
                "mode": mode,
                "mode_style": mode_style,
                "multi_image": True
            }
            
        else:
            # Single image or text-only flow
            result = generate_styled_captions(
                image=pil_images[0] if pil_images else None,
                platform=platform,
                platform_type=platform_type,
                mode=mode,
                mode_style=mode_style,
                creativity=creativity,
                length=length,
                include_emoji=include_emoji,
                include_hashtags=include_hashtags,
                hashtag_new_line=hashtag_new_line,
                add_hook=add_hook,
                variants=variants,
                user_prompt=user_prompt,
                language=language,
                image_analysis=image_analysis,
            )
            return {"success": True, **result}

    except Exception as e:
        print("❌ Error:", e)
        traceback.print_exc()
        return {"success": False, "error": str(e)}

@app.post("/analyze")
async def analyze_image(image: UploadFile = File(...)):
    """Analyze an image and return detection tags with AI detection."""
    from model import analyze_image_with_vision, load_image_bytes
    from ai_detector import detect_ai_image
    import re
    
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Invalid image")
    
    try:
        contents = await image.read()
        pil_image = load_image_bytes(contents)
        if pil_image is None:
            raise HTTPException(status_code=400, detail="Invalid image")
        
        with ThreadPoolExecutor(max_workers=2) as executor:
            future_analysis = executor.submit(analyze_image_with_vision, pil_image)
            future_detection = executor.submit(detect_ai_image, contents)
            analysis = future_analysis.result()
            try:
                ai_detection_result = future_detection.result()
            except Exception as e:
                ai_detection_result = {
                    "is_ai_generated": False,
                    "confidence": 0.0,
                    "confidence_level": "unknown",
                    "error": str(e)
                }
        
        analysis_lower = analysis.lower()
        
        # Smart keyword extraction with enhanced detection
        def has_word(text, words):
            """Check if any word exists as a complete word (not substring)"""
            for word in words:
                if re.search(r'\b' + word + r'\b', text, re.IGNORECASE):
                    return True
            return False
        
        def has_phrase(text, phrases):
            """Check if any phrase exists in text"""
            for phrase in phrases:
                if phrase.lower() in text.lower():
                    return True
            return False
        
        tags = []
        
        # Enhanced People detection - MORE SPECIFIC
        people_words = ["person", "people", "man", "woman", "child", "kid", "family", "couple", "group", "baby", "toddler", "boy", "girl", "human", "individual", "someone", "face", "portrait", "female", "male", "lady", "gentleman", "adult", "teen", "person"]
        if has_word(analysis_lower, people_words):
            if has_word(analysis_lower, ["child", "kid", "baby", "toddler", "family", "children", "boy", "girl"]):
                tags.append("Family")
            elif has_word(analysis_lower, ["couple", "two people", "pair", "together"]):
                tags.append("Couple")
            elif has_word(analysis_lower, ["group", "crowd", "many people", "several people", "multiple"]):
                tags.append("Group")
            else:
                tags.append("People")
        
        # Subject detection - MAIN SUBJECT
        if has_word(analysis_lower, ["girl", "woman", "female", "lady", "she"]):
            tags.append("Girl")
        elif has_word(analysis_lower, ["boy", "man", "male", "gentleman", "he"]):
            tags.append("Man")
        
        # Enhanced Scene/Setting detection
        outdoor_words = ["outdoor", "outside", "landscape", "nature", "sky", "clouds", "horizon", "field", "grass", "trees"]
        indoor_words = ["indoor", "inside", "room", "interior", "wall", "ceiling", "floor", "furniture"]
        
        if has_word(analysis_lower, ["sunset", "sunrise", "golden hour", "dusk", "dawn"]):
            tags.append("Golden Hour")
        elif has_word(analysis_lower, ["beach", "seaside", "ocean", "sea", "water", "waves", "shore", "shoreline", "coast", "pier", "dock", "lakeside", "waterfront", "swimming", "sand"]):
            tags.append("Beach")
        elif has_word(analysis_lower, ["mountain", "hill", "peak", "cliff", "valley", "hiking", "trail", "summit"]):
            tags.append("Mountain")
        elif has_word(analysis_lower, ["city", "urban", "building", "skyline", "street", "downtown", "metropolitan", "skyscraper"]):
            tags.append("Urban")
        elif has_word(analysis_lower, ["forest", "trees", "woods", "jungle", "park", "garden", "botanical", "greenery"]):
            tags.append("Nature")
        elif has_word(analysis_lower, indoor_words):
            tags.append("Indoor")
        elif has_word(analysis_lower, outdoor_words):
            tags.append("Outdoor")
        
        # Enhanced Mood/Style detection
        if has_word(analysis_lower, ["warm", "golden", "soft light", "cozy", "comfortable", "inviting"]):
            tags.append("Warm")
        elif has_word(analysis_lower, ["dark", "moody", "dramatic", "shadow", "mysterious", "noir"]):
            tags.append("Moody")
        elif has_word(analysis_lower, ["bright", "vibrant", "colorful", "vivid", "cheerful", "lively"]):
            tags.append("Vibrant")
        elif has_word(analysis_lower, ["peaceful", "serene", "calm", "tranquil", "relaxing"]):
            tags.append("Peaceful")
        
        # Enhanced Activity detection
        if has_word(analysis_lower, ["walking", "strolling", "hiking", "jogging", "running", "moving"]):
            tags.append("Active")
        elif has_word(analysis_lower, ["eating", "dining", "restaurant", "cuisine", "food", "meal", "cooking", "kitchen"]):
            tags.append("Food")
        elif has_word(analysis_lower, ["working", "office", "desk", "laptop", "computer", "business", "meeting"]):
            tags.append("Work")
        elif has_word(analysis_lower, ["traveling", "adventure", "journey", "vacation", "tourist", "exploring", "trip"]):
            tags.append("Travel")
        elif has_word(analysis_lower, ["celebration", "party", "birthday", "wedding", "festival", "event"]):
            tags.append("Celebration")
        elif has_word(analysis_lower, ["sport", "game", "playing", "exercise", "fitness", "gym", "athletic"]):
            tags.append("Sports")
        
        # Enhanced Object detection  
        if has_word(analysis_lower, ["car", "vehicle", "automobile", "truck", "motorcycle", "bike", "transportation"]):
            tags.append("Vehicle")
            if has_word(analysis_lower, ["car"]):
                tags.append("Car")
        elif has_word(analysis_lower, ["paper", "document", "text", "page", "letter"]):
            tags.append("Document")
            if has_word(analysis_lower, ["paper"]):
                tags.append("Paper")
        elif has_word(analysis_lower, ["diagram", "chart", "graph", "infographic"]):
            tags.append("Diagram")
        elif has_word(analysis_lower, ["animal", "pet", "dog", "cat", "bird", "wildlife", "creature"]):
            if has_word(analysis_lower, ["dog", "puppy", "retriever", "golden retriever"]):
                tags.append("Dog")
            if has_word(analysis_lower, ["cat", "kitten"]):
                tags.append("Cat")
            if has_word(analysis_lower, ["bird", "parrot", "eagle", "pigeon", "seagull"]):
                tags.append("Bird")
            tags.append("Animal")
        elif has_word(analysis_lower, ["flower", "plant", "garden", "bloom", "botanical", "floral"]):
            tags.append("Floral")
        elif has_word(analysis_lower, ["building", "architecture", "structure", "construction", "design"]):
            tags.append("Architecture")
        elif has_word(analysis_lower, ["product", "merchandise", "brand", "logo", "commercial", "advertisement"]):
            tags.append("Product")
        
        # Enhanced Aesthetic detection
        if has_word(analysis_lower, ["minimal", "simple", "clean", "minimalist", "modern", "sleek"]):
            tags.append("Minimal")
        elif has_word(analysis_lower, ["artistic", "art", "creative", "painting", "drawing", "sculpture", "gallery"]):
            tags.append("Artistic")
        elif has_word(analysis_lower, ["vintage", "retro", "classic", "old", "antique", "nostalgic"]):
            tags.append("Vintage")
        elif has_word(analysis_lower, ["luxury", "elegant", "sophisticated", "premium", "high-end", "fancy"]):
            tags.append("Luxury")
        
        # Time-based detection
        if has_word(analysis_lower, ["night", "evening", "dark", "lights", "illuminated", "neon"]):
            tags.append("Night")
        elif has_word(analysis_lower, ["morning", "dawn", "early", "sunrise", "breakfast"]):
            tags.append("Morning")
        elif has_word(analysis_lower, ["afternoon", "midday", "lunch", "bright sun"]):
            tags.append("Afternoon")
        
        # Weather detection
        if has_word(analysis_lower, ["rain", "rainy", "wet", "storm", "cloudy", "overcast"]):
            tags.append("Rainy")
        elif has_word(analysis_lower, ["snow", "winter", "cold", "frozen", "ice", "snowy"]):
            tags.append("Winter")
        elif has_word(analysis_lower, ["sunny", "clear", "blue sky", "sunshine", "bright"]):
            tags.append("Sunny")
        
        priority_tags = ["Girl", "Man", "People", "Family", "Couple", "Dog", "Cat", "Bird", "Beach", "Mountain", "Nature", "Urban", "Car", "Food", "Work"]
        ordered_tags = []
        for p in priority_tags:
            if p in tags and p not in ordered_tags:
                ordered_tags.append(p)
        for t in tags:
            if t not in ordered_tags:
                ordered_tags.append(t)
        tags = ordered_tags

        # Ensure we have at least 4 tags with better defaults
        default_tags = ["Scene", "Outdoor", "Indoor", "Photo", "Realistic", "Visual"]
        while len(tags) < 4:
            for dt in default_tags:
                if dt not in tags:
                    tags.append(dt)
                    break
            if len(tags) >= 4:
                break
        
        # Limit to 4 most relevant tags
        tags = tags[:4]
        
        print(f"🏷️ Detection tags: {tags}")
        print(f"📝 Analysis snippet: {analysis[:150]}...")
        print(f"🤖 AI Detection: {ai_detection_result.get('is_ai_generated', False)} (confidence: {ai_detection_result.get('confidence', 0.0):.3f})")
        
        return {
            "success": True, 
            "tags": tags, 
            "analysis": analysis,
            "ai_detection": ai_detection_result
        }
        
    except Exception as e:
        print(f"❌ Analysis error: {e}")
        return {
            "success": True, 
            "tags": ["Photo", "Creative", "Artistic", "Mood"], 
            "analysis": "",
            "ai_detection": {
                "is_ai_generated": False,
                "confidence": 0.0,
                "confidence_level": "unknown",
                "error": str(e)
            }
        }

@app.post("/refine")
async def refine_caption_endpoint(request: RefineRequest):
    try:
        refined = refine_caption(
            request.caption,
            request.refine_type,
            request.mode,
            request.language or "English"
        )
        return {"success": True, "refined": refined}
    except Exception:
        return {"success": False, "refined": request.caption}

@app.post("/hashtags")
async def get_hashtags(request: HashtagRequest):
    """Generate trending hashtags."""
    try:
        hashtags = generate_hashtags(request.image_analysis, request.platform)
        return {"success": True, "hashtags": hashtags}
    except Exception as e:
        print(f"❌ Hashtag error: {e}")
        return {"success": False, "hashtags": ["#error", "#tryagain"]}

@app.get("/benchmark")
async def benchmark(profile: str = "fast"):
    try:
        from PIL import Image
        from time import perf_counter
        from model import analyze_image_with_vision_model, generate_caption_with_text_model
        import os
        vision_model = "bakllava:latest" if profile in ("fast","quality") else "bakllava:latest"
        text_model = "llama3.2:3b" if profile != "quality" else "llama3.1:8b"
        img = Image.new("RGB", (512, 512), (127, 127, 127))
        t0 = perf_counter()
        prev_np = os.environ.get("VISION_NUM_PREDICT")
        os.environ["VISION_NUM_PREDICT"] = "80" if profile == "fast" else "200"
        try:
            vision_desc = analyze_image_with_vision_model(img, vision_model)
        finally:
            if prev_np is None:
                os.environ.pop("VISION_NUM_PREDICT", None)
            else:
                os.environ["VISION_NUM_PREDICT"] = prev_np
        t1 = perf_counter()
        caption = generate_caption_with_text_model(
            image_analysis=vision_desc,
            platform="Instagram",
            platform_type="Post",
            mode="Social",
            mode_style="Chill",
            creativity=50,
            length=50,
            include_emoji=True,
            include_hashtags=False,
            hashtag_new_line=False,
            add_hook=False,
            user_prompt="",
            language="English",
            model_name=text_model,
        )
        t2 = perf_counter()
        return {
            "success": True,
            "profile": profile,
            "vision_model": vision_model,
            "text_model": text_model,
            "vision_ms": int((t1 - t0) * 1000),
            "text_ms": int((t2 - t1) * 1000),
            "total_ms": int((t2 - t0) * 1000),
            "vision_snippet": (vision_desc or "")[:80],
            "caption_snippet": (caption or "")[:80]
        }
    except Exception as e:
        print(f"❌ Benchmark error: {e}")
        return {"success": False, "error": str(e)}

@app.post("/autotune")
async def autotune():
    try:
        sel = select_best_models()
        return {"success": True, "selected": sel}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    print("🚀 http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)

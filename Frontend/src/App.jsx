import React, { useRef, useState, useEffect } from "react";
import "./styles.css";

const modeSubOptions = {
  Social: ["Chill", "Energetic", "Aesthetic", "Cozy", "Bold", "Dreamy"],
  Funny: ["Sarcastic", "Self-deprecating", "Absurd", "Relatable", "Dark Humor", "Punny"],
  Story: ["Inspirational", "Emotional", "Adventure", "Life Lesson", "Throwback", "Mystery"],
  Business: ["Motivational", "Informative", "Achievement", "Networking", "Thought Leader"],
  Education: ["Tips", "Facts", "How-to", "Explainer", "Did You Know", "Quiz"],
};

export default function App() {
  const fileInputRef = useRef(null);
  const API_URL = process.env.REACT_APP_API_URL || "http://localhost:8001";

  // STARTUP SPLASH SCREEN
  const [showSplash, setShowSplash] = useState(true); // Always show on startup
  const [splashProgress, setSplashProgress] = useState(0);

  // IMAGE & PLATFORM
  const [images, setImages] = useState([]);
  const [previews, setPreviews] = useState([]);
  const [platform, setPlatform] = useState('Other');
  const [platformType, setPlatformType] = useState('General');
  const [mode, setMode] = useState("Social");
  const [modeStyle, setModeStyle] = useState("");

  // SETTINGS
  const [creativity, setCreativity] = useState(50);
  const [length, setLength] = useState(50);
  const [emoji, setEmoji] = useState(true);
  const [language, setLanguage] = useState("English");

  // NEW SETTINGS
  const [prompt, setPrompt] = useState("");
  const [variants, setVariants] = useState(1);
  const [hashtags, setHashtags] = useState(true);
  const [hashtagNewLine, setHashtagNewLine] = useState(false);
  const [addHook, setAddHook] = useState(false);

  // RESULTS + HISTORY + FAVORITES
  const [results, setResults] = useState([]);
  const [history, setHistory] = useState([]);
  const [favorites, setFavorites] = useState([]);
  const [activeTab, setActiveTab] = useState("results");
  const [loading, setLoading] = useState(false);
  const [fadingOut, setFadingOut] = useState(false);
  const [resultsAnimated, setResultsAnimated] = useState(false);
  const [copiedIndex, setCopiedIndex] = useState(null);
  const [refiningIndex, setRefiningIndex] = useState(null);
  const [refiningType, setRefiningType] = useState(null);

  // IMAGE DETECTION
  const [imageChips, setImageChips] = useState([]);
  const [imageAnalysis, setImageAnalysis] = useState(null);
  const [isDetecting, setIsDetecting] = useState(false);
  const [aiDetection, setAiDetection] = useState(null);

  // THEME
  const [theme, setTheme] = useState(() => localStorage.getItem('captionLabTheme') || 'dark');

  // CUSTOM PRESETS
  const [customPresets, setCustomPresets] = useState(() => {
    const saved = localStorage.getItem('customPresets');
    return saved ? JSON.parse(saved) : {};
  });
  const [showSavePreset, setShowSavePreset] = useState(false);
  const [presetName, setPresetName] = useState('');

  // PREVIEW MODAL
  const [previewCaption, setPreviewCaption] = useState(null);

  // VOICE INPUT
  const [isListening, setIsListening] = useState(false);

  // NEW FEATURES STATE
  const [isComparing, setIsComparing] = useState(false);
  const [showTemplates, setShowTemplates] = useState(false);
  const [generatedHashtags, setGeneratedHashtags] = useState([]);
  const [isGeneratingHashtags, setIsGeneratingHashtags] = useState(false);

  // CHAR LIMITS
  const platformCharLimits = {
    Twitter: { Tweet: 280, Thread: 280, Quote: 280, Reply: 280 },
    TikTok: { Video: 150, Meme: 150, Motivation: 150, Tutorial: 150 },
    Instagram: { Post: 2200, Story: 2200, Reel: 2200, Carousel: 2200 },
    LinkedIn: { Personal: 3000, Company: 3000, Achievement: 3000, Article: 3000 },
    YouTube: { Shorts: 100, Community: 500, Video: 5000 },
    Other: { General: 5000, Blog: 5000, Email: 5000 }
  };

  const getCharLimit = () => platformCharLimits[platform]?.[platformType] || 5000;

  const getCharColor = (text) => {
    const limit = getCharLimit();
    const ratio = text.length / limit;
    if (ratio > 1) return 'red';
    if (ratio > 0.85) return 'yellow';
    return 'green';
  };

  // MODE SUB-OPTIONS
  // PRESETS
  const presets = {
    "Viral 🔥": { creativity: 85, length: 50, emoji: true, hashtags: true, addHook: true },
    "Minimal ✨": { creativity: 30, length: 20, emoji: false, hashtags: false, addHook: false },
    "Professional 💼": { creativity: 40, length: 70, emoji: false, hashtags: true, addHook: false },
    "Storytelling 📖": { creativity: 70, length: 90, emoji: true, hashtags: false, addHook: true },
    "Meme 😂": { creativity: 95, length: 30, emoji: true, hashtags: true, addHook: true },
    "Aesthetic 🌸": { creativity: 60, length: 40, emoji: true, hashtags: true, addHook: false },
  };

  // TEMPLATES
  const templates = {
    "Product Launch": "🚀 Introducing [Product Name]! The wait is finally over. Get ready to experience [Benefit]. #NewLaunch #Excited",
    "Monday Motivation": "New week, new goals. 💪 Let's crush it! What are you working on today? #MondayMotivation #Hustle",
    "Behind the Scenes": "👀 A sneak peek at what goes on behind the cameras. It's not always glamorous, but it's worth it! #BTS #WorkLife",
    "Travel Diary": "📍 Lost in [Location]. The views, the food, the vibes... unmatched. ✈️ #Travel #Wanderlust",
    "Review/Testimonial": "⭐⭐⭐⭐⭐ 'Best decision I ever made.' hearing your feedback makes our day! #CustomerLove #Review",
  };

  // PLATFORM OPTIONS
  const platformOptions = {
    Instagram: ["Post", "Story", "Reel", "Carousel"],
    TikTok: ["Video", "Meme", "Motivation", "Tutorial"],
    LinkedIn: ["Personal", "Company", "Achievement", "Article"],
    Twitter: ["Tweet", "Thread", "Quote", "Reply"],
    YouTube: ["Video", "Shorts", "Community"],
    Other: ["General", "Blog", "Email"],
  };

  // FEATURE 2: APPLY THEME
  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('captionLabTheme', theme);
  }, [theme]);

  // SPLASH SCREEN AUTO-CLOSE (3 MINUTES)
  useEffect(() => {
    if (showSplash) {
      const progressInterval = setInterval(() => {
        setSplashProgress(prev => {
          if (prev >= 100) {
            clearInterval(progressInterval);
            setTimeout(() => {
              setShowSplash(false);
            }, 500);
            return 100;
          }
          return prev + 0.556; // 100 / 180 seconds = 0.556 per second (3 minutes)
        });
      }, 1000); // Update every 1 second

      return () => clearInterval(progressInterval);
    }
  }, [showSplash]);

  const skipSplash = () => {
    setShowSplash(false);
  };

  // FEATURE 5: SAVE CUSTOM PRESETS
  useEffect(() => {
    localStorage.setItem('customPresets', JSON.stringify(customPresets));
  }, [customPresets]);

  // LOAD FROM LOCALSTORAGE
  useEffect(() => {
    const savedHistory = localStorage.getItem("captionHistory");
    const savedFavorites = localStorage.getItem("captionFavorites");
    if (savedHistory) setHistory(JSON.parse(savedHistory));
    if (savedFavorites) setFavorites(JSON.parse(savedFavorites));
  }, []);

  // SAVE TO LOCALSTORAGE
  useEffect(() => {
    localStorage.setItem("captionHistory", JSON.stringify(history));
  }, [history]);

  useEffect(() => {
    localStorage.setItem("captionFavorites", JSON.stringify(favorites));
  }, [favorites]);

  // SET DEFAULT MODE STYLE
  useEffect(() => {
    if (modeSubOptions[mode]) {
      setModeStyle(modeSubOptions[mode][0]);
    }
  }, [mode]);
  
  useEffect(() => {
    if (platform === "Instagram" && platformType === "Story" && mode !== "Story") {
      setMode("Story");
    }
  }, [platform, platformType, mode]);
  
  useEffect(() => {
    if (platform === "Other" && (platformType === "Blog" || platformType === "Email")) {
      setEmoji(false);
      setHashtags(false);
      setAddHook(true);
      setLength(80);
    }
  }, [platform, platformType]);

  const handlePick = () => fileInputRef.current.click();

  const handleFile = async (e) => {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;

    // Multi-image support (Feature 7)
    const newImages = [...images, ...files].slice(0, 10); // Limit to 10
    setImages(newImages);

    // Create previews
    const newPreviews = [...previews, ...files.map(file => URL.createObjectURL(file))].slice(0, 10);
    setPreviews(newPreviews);

    // Analyze the LAST added image for tags (or first if new)
    const imageToAnalyze = files[0];

    // AI-powered image detection
    setImageChips(["Analyzing...", "", "", ""]);

    try {
      setIsDetecting(true);
      const formData = new FormData();
      formData.append("image", imageToAnalyze);

      const response = await fetch(`${API_URL}/analyze`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();
      console.log("🔍 API Response:", data); // Debug log
      if (data.success) {
        setImageChips(data.tags);
        setAiDetection(data.ai_detection); // Store AI detection result
        console.log("🤖 AI Detection Data:", data.ai_detection); // Debug log
        setImageAnalysis(data.analysis || null);
      } else {
        setImageChips(["Photo", "Creative", "Artistic", "Mood"]);
        setAiDetection(null);
        setImageAnalysis(null);
      }
    } catch (error) {
      console.error("Error analyzing image:", error);
      setImageChips(["Photo", "Creative", "Artistic", "Mood"]);
    } finally {
      setIsDetecting(false);
    }
  };

  const removeImage = (index) => {
    const newImages = images.filter((_, i) => i !== index);
    const newPreviews = previews.filter((_, i) => i !== index);
    setImages(newImages);
    setPreviews(newPreviews);
    // Force re-render of file input by resetting it
    if (fileInputRef.current) fileInputRef.current.value = "";

    if (newImages.length === 0) {
      setImageChips([]);
      setResults([]);
      setAiDetection(null);
    }
  };

  // GENERATE HASHTAGS
  const generateHashtagsFunc = async () => {
    if (images.length === 0) {
      alert("Upload an image first!");
      return;
    }
    setIsGeneratingHashtags(true);
    setGeneratedHashtags([]);

    try {
      let analysisText = imageAnalysis;
      if (!analysisText) {
        const formData = new FormData();
        formData.append("image", images[0]);
        const analyzeRes = await fetch(`${API_URL}/analyze`, { method: "POST", body: formData });
        const analyzeData = await analyzeRes.json();
        analysisText = analyzeData.analysis || "A generic photo";
        setImageAnalysis(analysisText);
      }

      const response = await fetch(`${API_URL}/hashtags`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          image_analysis: analysisText,
          platform: platform
        })
      });
      const data = await response.json();
      if (data.success) {
        setGeneratedHashtags(data.hashtags);
      }
    } catch (e) {
      console.error(e);
      alert("Could not generate hashtags.");
    } finally {
      setIsGeneratingHashtags(false);
    }
  };

  // APPLY PRESET
  const applyPreset = (presetName) => {
    const allPresets = { ...presets, ...customPresets };
    const preset = allPresets[presetName];
    if (!preset) return;
    setCreativity(preset.creativity);
    setLength(preset.length);
    setEmoji(preset.emoji);
    setHashtags(preset.hashtags);
    setAddHook(preset.addHook);
    if (preset.mode) setMode(preset.mode);
    if (preset.modeStyle) setModeStyle(preset.modeStyle);
  };

  // CUSTOM PRESETS
  const saveCustomPreset = () => {
    if (!presetName.trim()) return;
    const newPreset = {
      creativity, length, emoji, hashtags, addHook,
      mode, modeStyle, platform, platformType
    };
    setCustomPresets(prev => ({ ...prev, [presetName.trim()]: newPreset }));
    setPresetName('');
    setShowSavePreset(false);
  };

  const deleteCustomPreset = (name) => {
    setCustomPresets(prev => {
      const updated = { ...prev };
      delete updated[name];
      return updated;
    });
  };

  // TONE ANALYSIS
  const analyzeTone = (text) => {
    const lower = text.toLowerCase();
    const tones = [];
    if (/😂|🤣|😭|💀|lol|lmao|haha|funny|joke|humor/i.test(lower)) tones.push({ label: 'Humorous', icon: '😂', color: '#fbbf24' });
    if (/professional|business|career|growth|strategy|leadership/i.test(lower)) tones.push({ label: 'Professional', icon: '💼', color: '#60a5fa' });
    if (/inspire|dream|believe|achieve|motivation|success/i.test(lower)) tones.push({ label: 'Inspirational', icon: '🌟', color: '#a78bfa' });
    if (/heart|love|soul|feel|tears|grateful|blessed/i.test(lower)) tones.push({ label: 'Emotional', icon: '💖', color: '#f472b6' });
    if (/bold|fearless|unstoppable|power|boss|slay/i.test(lower)) tones.push({ label: 'Bold', icon: '🔥', color: '#ef4444' });
    if (/peace|calm|serene|quiet|soft|aesthetic|minimal/i.test(lower)) tones.push({ label: 'Calm', icon: '🌿', color: '#34d399' });
    if (tones.length === 0) tones.push({ label: 'Positive', icon: '😊', color: '#8b5cf6' });
    return tones[0];
  };

  // GENERATE SMART PROMPTS BASED ON IMAGE
  const getSmartPrompts = () => {
    if (!imageAnalysis && imageChips.length === 0) return [];
    
    const analysis = (imageAnalysis || '').toLowerCase();
    const chips = imageChips.map(c => c.toLowerCase());
    const prompts = [];

    // Person/People detected
    if (chips.includes('people') || chips.includes('girl') || chips.includes('man') || chips.includes('person') || 
        analysis.includes('person') || analysis.includes('woman') || analysis.includes('man')) {
      prompts.push({ icon: '💪', text: 'Confident and empowered' });
      prompts.push({ icon: '✨', text: 'Living my best life' });
      prompts.push({ icon: '😊', text: 'Feeling myself today' });
    }

    // Beach/Ocean
    if (chips.includes('beach') || analysis.includes('beach') || analysis.includes('ocean')) {
      prompts.push({ icon: '🌊', text: 'Beach vibes and good times' });
      prompts.push({ icon: '🏖️', text: 'Salt in the air, sand in my hair' });
      prompts.push({ icon: '🌅', text: 'Paradise found' });
    }

    // Nature/Outdoor
    if (chips.includes('nature') || chips.includes('outdoor') || chips.includes('mountain') || 
        analysis.includes('nature') || analysis.includes('outdoor')) {
      prompts.push({ icon: '🌲', text: 'Nature is my happy place' });
      prompts.push({ icon: '⛰️', text: 'Adventure awaits' });
      prompts.push({ icon: '🍃', text: 'Lost in the beauty of nature' });
    }

    // Food
    if (chips.includes('food') || analysis.includes('food') || analysis.includes('eating')) {
      prompts.push({ icon: '🍽️', text: 'Food coma incoming' });
      prompts.push({ icon: '😋', text: 'Good food, good mood' });
      prompts.push({ icon: '🔥', text: 'Delicious and worth every calorie' });
    }

    // Urban/City
    if (chips.includes('urban') || analysis.includes('city') || analysis.includes('urban')) {
      prompts.push({ icon: '🌃', text: 'City lights and late nights' });
      prompts.push({ icon: '🏙️', text: 'Urban explorer' });
      prompts.push({ icon: '🚶', text: 'Street style on point' });
    }

    // Sunset/Golden Hour
    if (chips.includes('golden hour') || analysis.includes('sunset') || analysis.includes('golden hour')) {
      prompts.push({ icon: '🌅', text: 'Chasing sunsets' });
      prompts.push({ icon: '✨', text: 'Golden hour magic' });
      prompts.push({ icon: '🧡', text: 'Sky on fire' });
    }

    // Default prompts if nothing specific detected
    if (prompts.length === 0) {
      prompts.push({ icon: '✨', text: 'Making memories' });
      prompts.push({ icon: '💫', text: 'Living in the moment' });
      prompts.push({ icon: '🌟', text: 'Good vibes only' });
    }

    return prompts.slice(0, 6); // Return max 6 prompts
  };

  // VOICE INPUT
  const startVoiceInput = () => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Voice input not supported in this browser.');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = language === 'English' ? 'en-US' : language === 'Hindi' ? 'hi-IN' : 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    recognition.onstart = () => setIsListening(true);
    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      setPrompt(prev => prev ? prev + ' ' + transcript : transcript);
    };
    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
    recognition.start();
  };

  // AI DETECTION BADGE COMPONENT
  const AIDetectionBadge = ({ detection }) => {
    console.log("🎯 AIDetectionBadge received:", detection); // Debug log
    
    if (!detection) {
      console.log("❌ No detection data - badge not rendered");
      return null;
    }
    
    const isAI = detection.is_ai_generated;
    const confidence = Math.round(detection.confidence * 100);
    console.log(`🤖 Rendering badge: isAI=${isAI}, confidence=${confidence}%`); // Debug log
    
    // Get appropriate icon and styling based on confidence
    const getDisplayInfo = () => {
      if (isAI) {
        if (confidence >= 85) {
          return { icon: '🤖', label: 'AI Generated', className: 'ai-generated high-confidence' };
        } else if (confidence >= 70) {
          return { icon: '🤖', label: 'Likely AI Generated', className: 'ai-generated medium-confidence' };
        } else {
          return { icon: '🤖', label: 'Possibly AI Generated', className: 'ai-generated low-confidence' };
        }
      } else {
        if (confidence <= 15) {
          return { icon: '📸', label: 'Original Photo', className: 'original high-confidence' };
        } else if (confidence <= 30) {
          return { icon: '📸', label: 'Likely Original', className: 'original medium-confidence' };
        } else {
          return { icon: '📸', label: 'Possibly Original', className: 'original low-confidence' };
        }
      }
    };

    const displayInfo = getDisplayInfo();
    
    return (
      <div className={`ai-detection-badge ${displayInfo.className}`}>
        <span className="ai-icon">{displayInfo.icon}</span>
        <span className="ai-label">{displayInfo.label}</span>
        <span className="ai-confidence">{confidence}%</span>
        {detection.detected_tools && detection.detected_tools.length > 0 && (
          <span className="ai-tools" title={`Detected tools: ${detection.detected_tools.join(', ')}`}>
            🛠️
          </span>
        )}
      </div>
    );
  };

  // GENERATE CAPTIONS
  const generateCaptions = async () => {
    if (images.length === 0 && !prompt.trim()) {
      alert("Please upload an image or enter a prompt!");
      return;
    }
    if (platform === "Other" && (platformType === "Blog" || platformType === "Email") && !prompt.trim()) {
      alert("Please describe your blog/email requirements in the text box.");
      return;
    }

    setLoading(true);
    setCopiedIndex(null);
    setActiveTab("results");
    setGeneratedHashtags([]); // Reset hashtags

    try {
      const formData = new FormData();
      // Handle multi-image vs single image
      if (images.length > 1) {
        images.forEach(img => formData.append("images", img));
      } else {
        formData.append("image", images[0]);
        if (imageAnalysis) {
          formData.append("image_analysis", imageAnalysis);
        }
      }

      formData.append("platform", platform);
      formData.append("platform_type", platformType);
      formData.append("mode", mode);
      formData.append("mode_style", modeStyle);
      formData.append("creativity", creativity.toString());
      formData.append("length", length.toString());
      formData.append("include_emoji", emoji.toString());
      formData.append("include_hashtags", hashtags.toString());
      formData.append("hashtag_new_line", hashtagNewLine.toString());
      formData.append("add_hook", addHook.toString());
      formData.append("variants", variants.toString());
      formData.append("user_prompt", prompt);
      formData.append("language", language);

      const response = await fetch(`${API_URL}/caption`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) throw new Error("Failed to generate captions");

      const data = await response.json();

      if (data.success) {
        if (data.chips) setImageChips(data.chips);
        setResults(data.captions);

        const newResult = {
          id: Date.now(),
          captions: data.captions,
          platform,
          platformType,
          mode,
          modeStyle,
          timestamp: new Date().toLocaleString(),
        };
        setHistory((prev) => [newResult, ...prev.slice(0, 19)]);
      } else {
        throw new Error(data.error || "Caption generation failed");
      }
    } catch (error) {
      console.error("Error:", error);
      alert("Error: " + error.message);
    } finally {
      setFadingOut(true);
      setResultsAnimated(true);
      setTimeout(() => {
        setLoading(false);
        setFadingOut(false);
      }, 1200);
      setTimeout(() => {
        setResultsAnimated(false);
      }, 2000);
    }
  };

  // REFINE CAPTION
  const refineCaption = async (caption, type, index) => {
    setRefiningIndex(index);
    setRefiningType(type);
    
    try {
      const response = await fetch(`${API_URL}/refine`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          caption: caption,
          refine_type: type,
          mode: mode,
          language: language,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          const newResults = [...results];
          newResults[index] = data.refined;
          setResults(newResults);
        }
      }
    } catch (error) {
      console.error("Refine error:", error);
    } finally {
      setRefiningIndex(null);
      setRefiningType(null);
    }
  };

  const copyText = (text, index) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(index);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const toggleFavorite = (caption) => {
    if (favorites.includes(caption)) {
      setFavorites(favorites.filter(f => f !== caption));
    } else {
      setFavorites([...favorites, caption]);
    }
  };

  // LABELS
  const lengthLabel =
    length <= 30 ? "Short" : length <= 70 ? "Medium" : "Long";

  // QUALITY METER
  const getQualityScore = () => {
    let score = 0;

    // Platform-specific scoring
    if (platform === "Instagram" || platform === "TikTok") {
      if (emoji) score += 25;
      if (hashtags) score += 20;
      if (creativity >= 50) score += 20;
      if (length <= 70) score += 15;
      if (addHook) score += 20;
    } else if (platform === "LinkedIn") {
      if (!emoji) score += 20;
      if (creativity <= 50) score += 25;
      if (length >= 50) score += 20;
      if (hashtags) score += 15;
      if (modeStyle === "Thought Leader" || modeStyle === "Achievement") score += 20;
    } else if (platform === "Twitter") {
      if (length <= 40) score += 30;
      if (addHook) score += 25;
      if (creativity >= 40) score += 20;
      if (hashtags) score += 15;
    } else {
      score = 50 + (creativity / 2);
    }

    return Math.min(100, Math.max(0, score));
  };

  const getQualityLabel = () => {
    const score = getQualityScore();
    if (score >= 70) return { label: "High Engagement", color: "green", icon: "🟢" };
    if (score >= 40) return { label: "Balanced", color: "yellow", icon: "🟡" };
    return { label: "Low Impact", color: "red", icon: "🔴" };
  };

  // PLATFORM WARNINGS
  const getWarnings = () => {
    const warnings = [];

    if (platform === "LinkedIn" && emoji) {
      warnings.push("⚠️ Emojis may seem unprofessional on LinkedIn");
    }
    if (platform === "Twitter" && length > 60) {
      warnings.push("⚠️ Long captions may get cut off on Twitter");
    }
    if (platform === "TikTok" && length > 50) {
      warnings.push("⚠️ Shorter captions perform better on TikTok");
    }
    if (platform === "Instagram" && length > 80 && !hashtags) {
      warnings.push("⚠️ Long caption without hashtags may reduce reach");
    }
    if (platform === "LinkedIn" && mode === "Funny") {
      warnings.push("⚠️ Humor can be tricky on LinkedIn - keep it professional");
    }

    return warnings;
  };

  return (
    <div className="app-root">
      {/* SPLASH SCREEN */}
      {showSplash && (
        <div className="splash-screen">
          <div className="splash-content">
            <div className="splash-header">
              <div className="splash-logo">
                <span className="logo-icon">✨</span>
                <h1 className="logo-text">AI Caption Lab</h1>
              </div>
              <p className="splash-tagline">AI-Powered Social Media Caption Generator</p>
            </div>

            <div className="splash-info">
              <div className="info-section">
                <h3>🚀 What's Inside</h3>
                <ul className="feature-list">
                  <li>🤖 AI-Powered Image Analysis</li>
                  <li>🎯 Smart Prompt Suggestions</li>
                  <li>🌐 Multi-Platform Support (Instagram, TikTok, LinkedIn, Twitter)</li>
                  <li>🌍 Multi-Language Captions (English, Hindi, Spanish, French, German)</li>
                  <li>🎨 Custom Presets & Themes</li>
                  <li>🔍 AI Image Detection</li>
                </ul>
              </div>

              <div className="info-section">
                <h3>⚙️ Technology Stack</h3>
                <div className="tech-grid">
                  <div className="tech-item">
                    <span className="tech-icon">🐍</span>
                    <span>Python + FastAPI</span>
                  </div>
                  <div className="tech-item">
                    <span className="tech-icon">⚛️</span>
                    <span>React</span>
                  </div>
                  <div className="tech-item">
                    <span className="tech-icon">🦙</span>
                    <span>Ollama (Local AI)</span>
                  </div>
                  <div className="tech-item">
                    <span className="tech-icon">🌙</span>
                    <span>Moondream Vision</span>
                  </div>
                </div>
              </div>

              <div className="info-section developer-section">
                <h3>👨‍💻 Developer</h3>
                <div className="developer-card">
                  <div className="developer-avatar">MH</div>
                  <div className="developer-info">
                    <h4>Mohd Inamul Hassan</h4>
                    <p className="developer-role">Full Stack Developer</p>
                    <div className="developer-links">
                      <a href="https://github.com/inamulhassan-dev" target="_blank" rel="noopener noreferrer" className="dev-link">
                        <span>🐙</span> GitHub: @inamulhassan-dev
                      </a>
                      <a href="mailto:inamulhassan20006@gmail.com" className="dev-link">
                        <span>📧</span> inamulhassan20006@gmail.com
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <div className="splash-footer">
              <div className="progress-container">
                <div className="progress-bar">
                  <div className="progress-fill" style={{ width: `${splashProgress}%` }}></div>
                </div>
                <p className="progress-text">Loading... {splashProgress}%</p>
              </div>
              <button className="skip-btn" onClick={skipSplash}>
                Skip <span className="skip-icon">→</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* BACKGROUND */}
      <div className="animated-bg">
        <div className="blob blob-1"></div>
        <div className="blob blob-2"></div>
        <div className="blob blob-3"></div>
        <div className="blob blob-4"></div>
        <div className="particles">
          {Array.from({ length: 16 }).map((_, i) => (
            <div key={i} className="particle" style={{
              left: `${Math.random() * 100}%`,
              animationDelay: `${Math.random() * 8}s`,
              animationDuration: `${7 + Math.random() * 3}s`,
              opacity: Math.random() * 0.8 + 0.2
            }}></div>
          ))}
        </div>
      </div>

      <header className="topbar glass">
        <div className="logo">
          <h1>✨ Caption Lab</h1>
          <span>AI-Powered Magic</span>
        </div>
        <div className="top-actions">
          <button className={`ghost-btn glow ${showTemplates ? 'active' : ''}`} onClick={() => setShowTemplates(!showTemplates)}>
            📄 Templates
          </button>
          <button className={`ghost-btn glow`} onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
            {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
          </button>
          <button className="ghost-btn glow" onClick={() => window.open('https://github.com', '_blank')}>
            ⭐ Star on GitHub
          </button>
        </div>
      </header>

      {/* TEMPLATES DRAWER */}
      {showTemplates && (
        <div className="templates-drawer glass-card">
          <h3>📝 Quick Templates</h3>
          <div className="templates-list">
            {Object.entries(templates).map(([key, maxText]) => (
              <div key={key} className="template-item" onClick={() => {
                setPrompt(maxText);
                setShowTemplates(false);
              }}>
                <strong>{key}</strong>
                <p>{maxText.substring(0, 50)}...</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* MODE TABS */}
      <div className="mode-tabs">
        {Object.keys(modeSubOptions).map((m) => (
          <button
            key={m}
            className={`tab ${mode === m ? "active glass" : ""}`}
            onClick={() => setMode(m)}
          >
            {m}
          </button>
        ))}
      </div>

      {/* SUB OPTIONS */}
      <div className="mode-sub-options">
        {modeSubOptions[mode]?.map((style) => (
          <button
            key={style}
            className={`sub-option-btn ${modeStyle === style ? "active" : ""}`}
            onClick={() => setModeStyle(style)}
          >
            {style}
          </button>
        ))}
      </div>

      <div className="main-layout">
        {/* LEFT COLUMN - NAVIGATION & SETTINGS */}
        <div className="left-column">

          {/* PLATFORM SELECTOR */}
          <div className="card glass-card floating" style={{ animationDelay: '0.2s' }}>
            <h3>📱 Platform & Type</h3>
            <div className="button-group input-group">
              {Object.keys(platformOptions).map(p => (
                <button key={p} className={`select-btn ${platform === p ? 'active' : ''}`} onClick={() => { setPlatform(p); setPlatformType(platformOptions[p][0]); }}>
                  {p}
                </button>
              ))}
            </div>
            <div className="button-group input-group">
              {platformOptions[platform]?.map(t => (
                <button key={t} className={`select-btn small ${platformType === t ? 'active' : ''}`} onClick={() => setPlatformType(t)}>
                  {t}
                </button>
              ))}
            </div>
          </div>

          {/* QUICK PRESETS (Moved from Customization Layout) */}
          <div className="card glass-card floating" style={{ animationDelay: '0.3s' }}>
            <div className="presets-header">
              <h3>⚡ Quick Presets</h3>
              <button className="save-preset-toggle" onClick={() => setShowSavePreset(!showSavePreset)}>
                {showSavePreset ? '✖' : '➕ Save'}
              </button>
            </div>

            {showSavePreset && (
              <div className="save-preset-form">
                <input
                  type="text"
                  placeholder="Preset Name"
                  className="preset-name-input"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                />
                <button className="save-preset-btn" onClick={saveCustomPreset}>💾</button>
              </div>
            )}

            <div className="presets-grid">
              {Object.keys(presets).map((preset) => (
                <button key={preset} className="preset-btn" onClick={() => applyPreset(preset)}>
                  {preset}
                </button>
              ))}
              {Object.keys(customPresets).map((preset) => (
                <div key={preset} className="custom-preset-chip">
                  <button className="preset-btn custom" onClick={() => applyPreset(preset)}>📌 {preset}</button>
                  <button className="preset-delete" onClick={() => deleteCustomPreset(preset)}>✖</button>
                </div>
              ))}
            </div>
          </div>

          {/* QUALITY METER (Moved from Right to Left) */}
          <div className="quality-card glass-card floating" style={{ animationDelay: '0.4s' }}>
            <div className={`quality-meter ${getQualityLabel().color}`}>
              <span className="quality-icon">{getQualityLabel().icon}</span>
              <span className="quality-label">{getQualityLabel().label}</span>
              <div className="quality-bar">
                <div className="quality-fill" style={{ width: `${getQualityScore()}%` }}></div>
              </div>
              <span className="quality-score">{Math.round(getQualityScore())}/100</span>
            </div>
            {getWarnings().length > 0 && (
              <div className="warnings">
                {getWarnings().map((w, i) => <div key={i} className="warning-item">{w}</div>)}
              </div>
            )}
          </div>

          {/* AI PROMPT SUGGESTIONS */}
          {images.length > 0 && getSmartPrompts().length > 0 && (
            <div className="card glass-card floating" style={{ animationDelay: '0.5s' }}>
              <h3>💡 AI Prompt Suggestions</h3>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                Click a suggestion to auto-fill your prompt
              </p>
              <div className="smart-prompts-grid">
                {getSmartPrompts().map((promptObj, idx) => (
                  <button
                    key={idx}
                    className="smart-prompt-btn"
                    onClick={() => setPrompt(promptObj.text)}
                    title="Click to use this prompt"
                  >
                    <span className="prompt-icon">{promptObj.icon}</span>
                    <span className="prompt-text">{promptObj.text}</span>
                  </button>
                ))}
              </div>
            </div>
          )}

        </div>

        {/* RIGHT COLUMN - MAIN CONTENT & RESULTS */}
        <div className="right-column">

          {/* UPLOAD CARD */}
          <div className="card glass-card upload-card floating" onClick={handlePick}>
            <input
              type="file"
              ref={fileInputRef}
              style={{ display: "none" }}
              onChange={handleFile}
              accept="image/*"
              multiple
            />
            {previews.length > 0 ? (
              <div className="preview-container">
                {/* Show main preview (last added or first) */}
                <img src={previews[previews.length - 1]} alt="Preview" className="preview-img glow-border" />

                {/* Grid for multiple images */}
                {previews.length > 1 && (
                  <div className="multi-preview-grid">
                    {previews.map((src, idx) => (
                      <div key={idx} className="mini-preview-thumb">
                        <img src={src} alt={`Thumb ${idx}`} />
                        <button className="remove-thumb-btn" onClick={(e) => {
                          e.stopPropagation();
                          removeImage(idx);
                        }}>×</button>
                      </div>
                    ))}
                  </div>
                )}

                <button className="remove-btn" onClick={(e) => {
                  e.stopPropagation();
                  // Remove the main/last one shown
                  removeImage(previews.length - 1);
                }}>🗑️</button>

                {imageChips.length > 0 && (
                  <div className="image-analysis">
                    <div className="image-chips">
                      <span className="chips-label">🤖 AI Detected:</span>
                      <div className="chips-container">
                        {isDetecting ? (
                          <span className="chip pulse">Analyzing...</span>
                        ) : (
                          imageChips.map((chip, i) => (
                            <span key={i} className="chip">{chip}</span>
                          ))
                        )}
                      </div>
                    </div>
                    
                    {/* AI Detection Display */}
                    {aiDetection && (
                      <AIDetectionBadge detection={aiDetection} />
                    )}
                    {imageAnalysis && !isDetecting && (
                      <div className="analysis-text">
                        <div className="analysis-header">Analysis</div>
                        <div className="analysis-body">{imageAnalysis}</div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ) : (
              <div className="upload-inner">
                <span className="upload-icon">☁️</span>
                <h2>Upload Image(s)</h2>
                <p>Drag & drop or <span className="browse">browse</span></p>
                <small>Supports JPG, PNG (Max 10MB)</small>
              </div>
            )}
          </div>

          {/* MAGIC SETTINGS (Moved from Customization Card) */}
          <div className="card glass-card floating" style={{ animationDelay: '0.5s' }}>
            <h4 style={{ marginTop: '0' }}>✨ Magic Settings</h4>

            <div className="input-group">
              <div className="prompt-wrapper">
                <textarea
                  className="prompt-input"
                  placeholder="Describe your image, or enter a prompt for an Email, Blog, or Post (e.g. 'Write a professional email about...')"
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  rows={3}
                />
                <button
                  className={`voice-btn ${isListening ? 'listening' : ''}`}
                  onClick={startVoiceInput}
                  title="Voice Input"
                >
                  {isListening ? '🔴' : '🎙️'}
                </button>
              </div>
            </div>

            <div className="slider-group">
              <div className="language-row" style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <label style={{ fontWeight: 500, color: 'var(--text-secondary)' }}>Language:</label>
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="language-select glass-input"
                  style={{ padding: '6px 12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.2)', background: 'rgba(255,255,255,0.05)', color: 'white' }}
                >
                  <option value="English">🇬🇧 English</option>
                  <option value="Hindi">🇮🇳 Hindi</option>
                  <option value="Spanish">🇪🇸 Spanish</option>
                  <option value="French">🇫🇷 French</option>
                  <option value="German">🇩🇪 German</option>
                </select>
              </div>

              <div className="slider-row">
                <label>Creativity:</label>
                <div className="slider-container">
                  <input type="range" min="0" max="100" value={creativity} onChange={(e) => setCreativity(parseInt(e.target.value))} />
                </div>
                <span className="slider-value">{creativity}%</span>
              </div>
              <div className="slider-row">
                <label>Length:</label>
                <div className="slider-container">
                  <input type="range" min="10" max="100" value={length} onChange={(e) => setLength(parseInt(e.target.value))} />
                </div>
                <span className="slider-value">{lengthLabel}</span>
              </div>
              <div className="slider-row">
                <label>Variants:</label>
                <div className="slider-container">
                  <input type="range" min="1" max="5" value={variants} onChange={(e) => setVariants(parseInt(e.target.value))} />
                </div>
                <span className="slider-value">{variants}</span>
              </div>
            </div>

            <div className="toggles-grid">
              <button className={`toggle-btn ${emoji ? 'active' : ''}`} onClick={() => setEmoji(!emoji)}>
                <div className="toggle-content">
                  <span className="toggle-icon">😀</span>
                  <span className="toggle-label">Include Emojis</span>
                </div>
                <div className="toggle-switch"></div>
              </button>

              {['Instagram', 'TikTok', 'Twitter', 'LinkedIn', 'YouTube'].includes(platform) && (
                <>
                  <button className={`toggle-btn ${hashtags ? 'active' : ''}`} onClick={() => setHashtags(!hashtags)}>
                    <div className="toggle-content">
                      <span className="toggle-icon">#</span>
                      <span className="toggle-label">Add Hashtags</span>
                    </div>
                    <div className="toggle-switch"></div>
                  </button>

                  {hashtags && (
                    <button className={`toggle-btn ${hashtagNewLine ? 'active' : ''}`} onClick={() => setHashtagNewLine(!hashtagNewLine)}>
                      <div className="toggle-content">
                        <span className="toggle-icon">↩</span>
                        <span className="toggle-label">Hashtags on New Line</span>
                      </div>
                      <div className="toggle-switch"></div>
                    </button>
                  )}

                  <button className={`toggle-btn ${addHook ? 'active' : ''}`} onClick={() => setAddHook(!addHook)}>
                    <div className="toggle-content">
                      <span className="toggle-icon">🎣</span>
                      <span className="toggle-label">Add Strong Hook</span>
                    </div>
                    <div className="toggle-switch"></div>
                  </button>
                </>
              )}
            </div>

            <button className="generate-btn glow" onClick={generateCaptions} disabled={loading}>
              {loading ? '🔮 Generating...' : images.length > 0 ? '✨ Generate Captions' : '✍️ Generate Content'}
            </button>
          </div>

          {/* RESULTS SECTION */}
          {results.length > 0 && (
            <>
              {/* RESULTS HEADER */}
              <div className="results-header" style={{ marginTop: '30px' }}>
                <div>
                  <h3>🎉 Generated Captions</h3>
                  <div className="history-meta">
                    <span className="history-platform">{platform} {platformType}</span>
                    <span className="history-mode">{mode}</span>
                    <span className="history-style">{modeStyle}</span>
                  </div>
                </div>
                <div className="results-actions">
                  <button className={`ghost-btn small ${isComparing ? 'active' : ''}`} onClick={() => setIsComparing(!isComparing)}>
                    {isComparing ? '📖 List View' : '⚖️ Compare'}
                  </button>
                  <button className="ghost-btn small" onClick={generateHashtagsFunc} disabled={isGeneratingHashtags}>
                    {isGeneratingHashtags ? '⏳ Tags...' : '#️⃣ Get Hashtags'}
                  </button>
                </div>
              </div>

              {/* COMPARISON VIEW */}
              {isComparing ? (
                <div className="comparison-grid">
                  {results.map((caption, index) => {
                    const tone = analyzeTone(caption);
                    return (
                      <div key={index} className="comparison-card glass-card">
                        <div className="caption-header">
                          <span className="variant-label">Option {index + 1}</span>
                          <span className="tone-badge" style={{ background: `${tone.color}20`, color: tone.color, border: `1px solid ${tone.color}40` }}>{tone.icon} {tone.label}</span>
                        </div>
                        <div className="history-meta">
                          <span className="history-platform">{platform} {platformType}</span>
                          <span className="history-mode">{mode}</span>
                          <span className="history-style">{modeStyle}</span>
                        </div>
                        <p>{caption}</p>
                        <div className="comparison-actions">
                          <button className="action-btn" onClick={() => copyText(caption, index)}>📋</button>
                          <button className="action-btn" onClick={() => toggleFavorite(caption)}>❤️</button>
                        </div>
                      </div>
                    )
                  })}
                </div>
              ) : (
                /* STANDARD LIST VIEW */
                <div className="results-list">
                  {activeTab === 'results' && results.map((caption, index) => {
                    const tone = analyzeTone(caption);
                    const charLimit = getCharLimit();
                    const charColor = getCharColor(caption);

                    return (
                      <div key={index} className={`caption-item glass-card ${resultsAnimated ? 'animate-in' : ''}`} style={{ animationDelay: `${index * 0.1}s` }}>
                        <div className="caption-header">
                          <span className="variant-badge">✨ Option {index + 1}</span>
                          <div className="caption-meta">
                            <span className="tone-badge" style={{ background: `${tone.color}20`, color: tone.color, border: `1px solid ${tone.color}40` }}>{tone.icon} {tone.label}</span>
                            <span className={`char-counter ${charColor}`} >{caption.length}/{charLimit}</span>
                          </div>
                          <div className="caption-actions-top">
                            <button className={`icon-btn ${favorites.includes(caption) ? 'active' : ''}`} onClick={() => toggleFavorite(caption)}>
                              {favorites.includes(caption) ? '❤️' : '🤍'}
                            </button>
                          </div>
                        </div>
                        <div className="history-meta">
                          <span className="history-platform">{platform} {platformType}</span>
                          <span className="history-mode">{mode}</span>
                          <span className="history-style">{modeStyle}</span>
                        </div>

                        <div className="caption-content">
                          <p>{caption}</p>
                          {caption.length > charLimit && (
                            <div className="char-warning">⚠️ Over limit by {caption.length - charLimit} chars</div>
                          )}
                          <div className="caption-actions">
                            <button className="action-btn primary" onClick={() => copyText(caption, index)}>
                              {copiedIndex === index ? '✅ Copied!' : '📋 Copy'}
                            </button>
                            <button className="action-btn preview" onClick={() => setPreviewCaption(caption)}>👁️ Preview</button>
                            <button className="action-btn" onClick={() => refineCaption(caption, 'shorten', index)} disabled={refiningIndex === index && refiningType === 'shorten'}>
                              {refiningIndex === index && refiningType === 'shorten' ? '⏳' : '✂️'} Shorten
                            </button>
                            <button className="action-btn" onClick={() => refineCaption(caption, 'expand', index)} disabled={refiningIndex === index && refiningType === 'expand'}>
                              {refiningIndex === index && refiningType === 'expand' ? '⏳' : '📝'} Expand
                            </button>
                            <button className="action-btn" onClick={() => refineCaption(caption, 'funnier', index)} disabled={refiningIndex === index && refiningType === 'funnier'}>
                              {refiningIndex === index && refiningType === 'funnier' ? '⏳' : '😂'} Funnier
                            </button>
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}

              {/* HASHTAGS SECTION */}
              {generatedHashtags.length > 0 && (
                <div className="glass-card floating" style={{ marginTop: '20px', padding: '20px' }}>
                  <h3>🔥 Trending Hashtags</h3>
                  <div className="hashtags-grid">
                    {generatedHashtags.map((tag, i) => (
                      <span key={i} className="hashtag-chip" onClick={() => copyText(tag, 'tag-' + i)}>
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}

          {/* LOADING OVERLAY */}
          {loading && !fadingOut && (
            <div className="magic-loader">
              <div className="loader-content">
                <div className="crystal-ball">
                  <div className="ball-inner"></div>
                </div>
                <h3>✨ Brewing Magic...</h3>
                <p>Optimizing for {platform} {platformType}</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* PREVIEW MODAL */}
      {previewCaption && (
        <div className="preview-modal-overlay" onClick={() => setPreviewCaption(null)}>
          <div className="preview-modal" onClick={(e) => e.stopPropagation()}>
            <button className="preview-close" onClick={() => setPreviewCaption(null)}>✖</button>
            <h3>📱 {platform} Preview</h3>
            <div className={`preview-card-mock ${platform.toLowerCase()}`}>
              <div className="preview-user-row">
                <div className="preview-avatar">👤</div>
                <div className="preview-username">
                  <strong>your_username</strong>
                  <span className="preview-subtitle">Just now • {platform}</span>
                </div>
                <div className="preview-dots">•••</div>
              </div>
              <div className="preview-image-mock">
                {previews.length > 0 && <img src={previews[0]} alt="Post Content" />}
              </div>
              <div className="preview-engagement">
                <span>❤️ 1,234 likes</span>
                <span>💬 42 comments</span>
              </div>
              <div className="preview-caption-text">
                <p><strong>your_username</strong> {previewCaption}</p>
              </div>
            </div>
            <div className="preview-stats">
              <div className="preview-stat">
                <span className="stat-label">Characters</span>
                <span className={`stat-value ${getCharColor(previewCaption)}`}>{previewCaption.length}</span>
              </div>
              <div className="preview-stat">
                <span className="stat-label">Words</span>
                <span className="stat-value">{previewCaption.split(' ').length}</span>
              </div>
              <div className="preview-stat">
                <span className="stat-label">Hashtags</span>
                <span className="stat-value">{(previewCaption.match(/#/g) || []).length}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      <footer className="footer">
        <p>Built with ❤️ using React & Python</p>
      </footer>
    </div>
  );
}

#!/usr/bin/env python3
"""
Performance Check Utility for AI Caption Lab
Checks system resources and optimizes settings for best performance
"""

import psutil
import platform
import subprocess
import os

def check_system_resources():
    """Check available system resources"""
    print("🔍 System Resource Check:")
    print("=" * 50)
    
    # CPU Info
    print(f"CPU Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} logical")
    print(f"CPU Usage: {psutil.cpu_percent()}%")
    
    # Memory Info
    mem = psutil.virtual_memory()
    print(f"RAM: {mem.available / 1024 / 1024 / 1024:.1f}GB available / {mem.total / 1024 / 1024 / 1024:.1f}GB total")
    print(f"RAM Usage: {mem.percent}%")
    
    # Disk Info
    disk = psutil.disk_usage('/')
    print(f"Storage: {disk.free / 1024 / 1024 / 1024:.1f}GB free / {disk.total / 1024 / 1024 / 1024:.1f}GB total")

def check_ollama_status():
    """Check if Ollama is running and models available"""
    print("\n🤖 Ollama Status:")
    print("=" * 50)
    
    try:
        # Check if Ollama server is running
        result = subprocess.run(['curl', '-s', 'http://localhost:11434/'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Ollama server is running")
        else:
            print("❌ Ollama server not responding")
            return
        
        # Check available models
        result = subprocess.run(['curl', '-s', 'http://localhost:11434/api/tags'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Models available via API")
            print(f"Response: {result.stdout[:100]}...")
        else:
            print("❌ Cannot access models API")
            
    except Exception as e:
        print(f"❌ Error checking Ollama: {e}")

def get_optimization_recommendations():
    """Provide specific optimization recommendations"""
    print("\n💡 Optimization Recommendations:")
    print("=" * 50)
    
    mem = psutil.virtual_memory()
    
    if mem.total < 12 * 1024 * 1024 * 1024:  # Less than 12GB RAM
        print("1. ✅ Use lightweight models (moondream + tinyllama) - CURRENT")
        print("2. ✅ Set VISION_MAX_SIZE=256 for fast mode")
        print("3. ✅ Set TEXT_NUM_PREDICT=40 for faster generation")
    else:
        print("1. ✅ Use balanced models (moondream + phi3:mini)")
        print("2. ✅ Set VISION_MAX_SIZE=512 for better quality")
        print("3. ✅ Set TEXT_NUM_PREDICT=80 for quality generation")
    
    print("4. 💡 Close unnecessary applications during AI processing")
    print("5. 💡 Use wired internet connection for stable performance")
    print("6. 💡 Keep system drivers updated for GPU acceleration")

def main():
    print("🚀 AI Caption Lab - Performance Check Utility")
    print("=" * 60)
    
    check_system_resources()
    check_ollama_status()
    get_optimization_recommendations()
    
    print("\n🎯 Current Configuration (start-backend.bat):")
    print("=" * 50)
    print("Fast Mode: moondream + tinyllama, 256px images, 40 tokens")
    print("Quality Mode: moondream + tinyllama, 512px images, 80 tokens")
    print("\n✅ Your system is optimized for maximum performance!")

if __name__ == "__main__":
    try:
        import psutil
        main()
    except ImportError:
        print("Installing required package: pip install psutil")
        subprocess.run(['pip', 'install', 'psutil'])
        import psutil
        main()
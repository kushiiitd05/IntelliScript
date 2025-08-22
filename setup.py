#!/usr/bin/env python3
"""
IntelliScript Setup Script
Automatically installs dependencies and checks system requirements
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

def run_command(command, description="", check=True):
    """Run a shell command with error handling"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(command, shell=True, check=check, capture_output=True, text=True)
        if result.stdout:
            print(f"   {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error: {e}")
        if e.stderr:
            print(f"   {e.stderr.strip()}")
        return False

def check_python_version():
    """Check if Python version is compatible"""
    print("🐍 Checking Python version...")
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 3.8+ is required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    print("🎵 Checking FFmpeg installation...")
    try:
        result = subprocess.run(["ffmpeg", "-version"], capture_output=True, check=True)
        print("✅ FFmpeg is installed")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ FFmpeg not found")
        return False

def install_ffmpeg():
    """Install FFmpeg based on the operating system"""
    system = platform.system().lower()
    
    print(f"🎵 Installing FFmpeg for {system}...")
    
    if system == "linux":
        # Try different Linux package managers
        managers = [
            ("apt-get update && apt-get install -y ffmpeg", "APT (Ubuntu/Debian)"),
            ("yum install -y ffmpeg", "YUM (RHEL/CentOS)"),
            ("dnf install -y ffmpeg", "DNF (Fedora)"),
            ("pacman -S ffmpeg", "Pacman (Arch Linux)")
        ]
        
        for cmd, name in managers:
            print(f"   Trying {name}...")
            if run_command(f"sudo {cmd}", check=False):
                break
    
    elif system == "darwin":  # macOS
        if run_command("brew --version", check=False):
            run_command("brew install ffmpeg", "Installing FFmpeg via Homebrew")
        else:
            print("❌ Homebrew not found. Please install Homebrew first:")
            print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            return False
    
    elif system == "windows":
        print("❌ Windows detected. Please manually install FFmpeg:")
        print("   1. Download from: https://ffmpeg.org/download.html")
        print("   2. Extract and add to PATH")
        print("   3. Restart your terminal")
        return False
    
    return check_ffmpeg()

def setup_virtual_environment():
    """Set up Python virtual environment"""
    print("🔧 Setting up virtual environment...")
    
    venv_path = Path("venv")
    if venv_path.exists():
        print("   Virtual environment already exists")
        return True
    
    if not run_command(f"{sys.executable} -m venv venv", "Creating virtual environment"):
        return False
    
    print("✅ Virtual environment created")
    return True

def install_python_dependencies():
    """Install Python dependencies from requirements.txt"""
    print("📦 Installing Python dependencies...")
    
    # Determine the correct pip path
    if platform.system() == "Windows":
        pip_path = "venv\\Scripts\\pip"
        python_path = "venv\\Scripts\\python"
    else:
        pip_path = "venv/bin/pip"
        python_path = "venv/bin/python"
    
    # Upgrade pip first
    run_command(f"{python_path} -m pip install --upgrade pip", "Upgrading pip")
    
    # Install PyTorch with CUDA support if available
    print("🔥 Installing PyTorch...")
    torch_cmd = f"{pip_path} install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
    if not run_command(torch_cmd, "Installing PyTorch with CUDA support", check=False):
        # Fallback to CPU-only version
        print("   Falling back to CPU-only PyTorch...")
        run_command(f"{pip_path} install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu", 
                   "Installing PyTorch (CPU-only)")
    
    # Install other dependencies
    if not run_command(f"{pip_path} install -r backend/requirements.txt", "Installing backend dependencies"):
        return False
    
    print("✅ Python dependencies installed")
    return True

def setup_directories():
    """Create necessary directories"""
    print("📁 Setting up directories...")
    
    directories = [
        "uploads", "downloads", "results", "exports", 
        "temp_audio", "progress", "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"   Created: {directory}/")
    
    print("✅ Directories created")
    return True

def setup_env_file():
    """Set up environment file"""
    print("⚙️ Setting up environment configuration...")
    
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists() and env_example.exists():
        import shutil
        shutil.copy2(env_example, env_file)
        print("✅ Created .env file from template")
        print("⚠️  IMPORTANT: Please edit .env file and add your API keys:")
        print("   - HF_TOKEN (Hugging Face)")
        print("   - GROQ_API_KEY (Groq)")  
        print("   - NEBIUS_API_KEY (Nebius AI)")
    else:
        print("   .env file already exists")
    
    return True

def install_frontend_dependencies():
    """Install frontend dependencies"""
    print("📦 Installing frontend dependencies...")
    
    if not Path("node_modules").exists():
        if not run_command("npm install", "Installing Node.js dependencies"):
            return False
    else:
        print("   Node modules already installed")
    
    print("✅ Frontend dependencies ready")
    return True

def main():
    """Main setup function"""
    print("🚀 IntelliScript Setup")
    print("=" * 50)
    
    # Check system requirements
    if not check_python_version():
        sys.exit(1)
    
    if not check_ffmpeg():
        print("\n💡 FFmpeg is required for audio/video processing")
        install_choice = input("Would you like to try installing FFmpeg automatically? (y/n): ")
        if install_choice.lower() in ['y', 'yes']:
            if not install_ffmpeg():
                print("❌ Please install FFmpeg manually and run setup again")
                sys.exit(1)
        else:
            print("❌ Please install FFmpeg manually and run setup again")
            sys.exit(1)
    
    # Setup steps
    setup_steps = [
        setup_virtual_environment,
        install_python_dependencies,
        setup_directories,
        setup_env_file,
        install_frontend_dependencies,
    ]
    
    for step in setup_steps:
        if not step():
            print(f"❌ Setup failed at step: {step.__name__}")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file and add your API keys")
    print("2. Start the backend: python -m uvicorn backend.main:app --reload")
    print("3. Start the frontend: npm run dev")
    print("4. Open http://localhost:5173 in your browser")
    print("\n💡 See README.md for detailed instructions")

if __name__ == "__main__":
    main()
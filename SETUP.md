# System Setup

## Required (install once, not via pip)

### Docker Desktop (for C++ sandboxing)
- Download from https://docker.com
- Enable WSL2 backend in Docker Desktop settings

### g++ (C++ compiler)
sudo apt update && sudo apt install -y g++ build-essential

### SQLite (for SQL executor)
sudo apt install -y sqlite3

### Git
sudo apt install -y git

## Verify everything works
docker --version
g++ --version
sqlite3 --version
python3.11 --version


#!/usr/bin/env python3
import subprocess
import sys

def get_repository_files_size():
    try:
        # Include tracked and not-yet-staged files while respecting .gitignore.
        result = subprocess.run(
            ['git', 'ls-files', '--cached', '--others', '--exclude-standard'],
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            text=True, 
            check=True
        )
        files = result.stdout.splitlines()
        
        total_size = 0
        for f in files:
            try:
                import os
                total_size += os.path.getsize(f)
            except OSError:
                pass # File might be tracked but not exist locally, or is a submodule
                
        return total_size
    except subprocess.CalledProcessError as e:
        print("Error running git ls-files. Are you in a git repository?", file=sys.stderr)
        sys.exit(1)

def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0

def main():
    WARNING_LIMIT = 8 * 1024 * 1024 # 8 MB
    ERROR_LIMIT = 9.5 * 1024 * 1024 # 9.5 MB
    
    total_size = get_repository_files_size()
    formatted_size = format_size(total_size)
    
    print(f"Total repository source size: {formatted_size}")
    
    if total_size > ERROR_LIMIT:
        print(f"ERROR: Repository size exceeds the strict {format_size(ERROR_LIMIT)} limit.", file=sys.stderr)
        sys.exit(1)
    elif total_size > WARNING_LIMIT:
        print(f"WARNING: Repository size is approaching the strict {format_size(ERROR_LIMIT)} limit.", file=sys.stderr)
        
    sys.exit(0)

if __name__ == "__main__":
    main()

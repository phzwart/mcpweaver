"""File system tools for MCP Weaver examples."""

import os
import glob
from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import mimetypes

def list_files(directory: str = ".", pattern: str = "*") -> Dict[str, Any]:
    """List files in a directory with optional pattern matching.
    
    Args:
        directory: The directory to list files from.
        pattern: The pattern to match files against.

    Returns:
        A dictionary containing the list of files.
    """
    try:
        path = Path(directory).resolve()
        if not path.exists():
            return {"error": f"Directory '{directory}' does not exist"}
        
        if not path.is_dir():
            return {"error": f"'{directory}' is not a directory"}
        
        # Use glob pattern matching
        search_pattern = str(path / pattern)
        files = glob.glob(search_pattern, recursive=True)
        
        file_list = []
        for file_path in files:
            file_stat = Path(file_path).stat()
            file_list.append({
                "name": os.path.basename(file_path),
                "path": file_path,
                "size": file_stat.st_size,
                "type": "directory" if Path(file_path).is_dir() else "file",
                "modified": file_stat.st_mtime
            })
        
        return {
            "directory": str(path),
            "pattern": pattern,
            "count": len(file_list),
            "files": file_list
        }
        
    except Exception as e:
        return {"error": f"Error listing files: {str(e)}"}

def read_file(file_path: str, max_lines: int = 50) -> Dict[str, Any]:
    """Read contents of a file with optional line limit.
    
    Args:
        file_path: The path to the file to read.
        max_lines: The maximum number of lines to read.

    Returns:
        A dictionary containing the contents of the file.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File '{file_path}' does not exist"}
        
        if not path.is_file():
            return {"error": f"'{file_path}' is not a file"}
        
        # Get file info
        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(file_path)
        
        # Read file content
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Limit lines if specified
        if max_lines and len(lines) > max_lines:
            content = ''.join(lines[:max_lines])
            truncated = True
            total_lines = len(lines)
        else:
            content = ''.join(lines)
            truncated = False
            total_lines = len(lines)
        
        return {
            "file_path": str(path),
            "size": stat.st_size,
            "mime_type": mime_type or "text/plain",
            "total_lines": total_lines,
            "lines_read": len(lines[:max_lines]) if max_lines else total_lines,
            "truncated": truncated,
            "content": content
        }
        
    except Exception as e:
        return {"error": f"Error reading file: {str(e)}"}

def count_lines(file_path: str) -> Dict[str, Any]:
    """Count lines in a file.
    
    Args:
        file_path: The path to the file to count lines in.

    Returns:
        A dictionary containing the number of lines in the file.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File '{file_path}' does not exist"}
        
        if not path.is_file():
            return {"error": f"'{file_path}' is not a file"}
        
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Count different types of lines
        total_lines = len(lines)
        empty_lines = sum(1 for line in lines if line.strip() == '')
        code_lines = total_lines - empty_lines
        
        return {
            "file_path": str(path),
            "total_lines": total_lines,
            "empty_lines": empty_lines,
            "code_lines": code_lines,
            "size_bytes": path.stat().st_size
        }
        
    except Exception as e:
        return {"error": f"Error counting lines: {str(e)}"}

def get_file_info(file_path: str) -> Dict[str, Any]:
    """Get detailed information about a file.
    
    Args:
        file_path: The path to the file to get information about.

    Returns:
        A dictionary containing the information about the file.
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return {"error": f"File '{file_path}' does not exist"}
        
        stat = path.stat()
        mime_type, encoding = mimetypes.guess_type(file_path)
        
        # Try to determine file type
        if path.suffix:
            file_type = f"{path.suffix[1:].upper()} file"
        elif mime_type:
            file_type = mime_type.split('/')[1].upper()
        else:
            file_type = "Unknown"
        
        return {
            "file_path": str(path),
            "name": path.name,
            "extension": path.suffix,
            "file_type": file_type,
            "mime_type": mime_type,
            "encoding": encoding,
            "size_bytes": stat.st_size,
            "size_human": _format_size(stat.st_size),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "accessed": stat.st_atime,
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
            "permissions": oct(stat.st_mode)[-3:]
        }
        
    except Exception as e:
        return {"error": f"Error getting file info: {str(e)}"}

def search_files(directory: str = ".", pattern: str = "*", content_search: str = None) -> Dict[str, Any]:
    """Search for files with optional content search.
    
    Args:
        directory: The directory to search in.
        pattern: The pattern to match files against.
        content_search: The content to search for.

    Returns:
        A dictionary containing the search results.
    """
    try:
        path = Path(directory).resolve()
        if not path.exists():
            return {"error": f"Directory '{directory}' does not exist"}
        
        if not path.is_dir():
            return {"error": f"'{directory}' is not a directory"}
        
        # Find files matching pattern
        search_pattern = str(path / pattern)
        files = glob.glob(search_pattern, recursive=True)
        
        results = []
        for file_path in files:
            file_path_obj = Path(file_path)
            if not file_path_obj.is_file():
                continue
                
            result = {
                "name": file_path_obj.name,
                "path": str(file_path_obj),
                "size": file_path_obj.stat().st_size
            }
            
            # If content search is specified, search within the file
            if content_search:
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if content_search.lower() in content.lower():
                            result["matches"] = content.count(content_search)
                            result["found"] = True
                        else:
                            result["found"] = False
                except:
                    result["found"] = False
                    result["error"] = "Could not read file for search"
            else:
                result["found"] = True
            
            results.append(result)
        
        return {
            "directory": str(path),
            "pattern": pattern,
            "content_search": content_search,
            "total_files": len(results),
            "matching_files": len([r for r in results if r.get("found", True)]),
            "files": results
        }
        
    except Exception as e:
        return {"error": f"Error searching files: {str(e)}"}

def _format_size(size_bytes: int) -> str:
    """Format file size in human readable format.
    
    Args:
        size_bytes: The size in bytes to format.

    Returns:
        A string containing the formatted size.
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}" 
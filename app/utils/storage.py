import os
import uuid
import pandas as pd
from typing import Dict, Optional, Tuple, List
from pathlib import Path

# In-memory storage for uploaded dataframes
# Key format: "file_id" for CSV or "file_id:sheet_name" for Excel sheets
dataframes: Dict[str, pd.DataFrame] = {}

# In-memory storage for original file content (for formatted preview)
file_contents: Dict[str, Tuple[bytes, str]] = {}  # file_id -> (content, filename)

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def get_sheet_key(file_id: str, sheet_name: Optional[str] = None) -> str:
    """
    Generate a composite key for file + sheet combination.
    
    Args:
        file_id: The unique file identifier
        sheet_name: Optional sheet name for Excel files
        
    Returns:
        Composite key in format "file_id" or "file_id:sheet_name"
    """
    if sheet_name:
        return f"{file_id}:{sheet_name}"
    return file_id


def parse_sheet_key(key: str) -> Tuple[str, Optional[str]]:
    """
    Parse a composite key back into file_id and sheet_name.
    
    Args:
        key: Composite key to parse
        
    Returns:
        Tuple of (file_id, sheet_name) where sheet_name may be None
    """
    if ':' in key:
        parts = key.split(':', 1)
        return parts[0], parts[1]
    return key, None


def generate_file_id() -> str:
    """Generate a unique file ID"""
    return str(uuid.uuid4())


def store_dataframe(file_id: str, df: pd.DataFrame, sheet_name: Optional[str] = None) -> str:
    """
    Store a dataframe in memory with composite key support.
    
    Args:
        file_id: The unique file identifier
        df: The pandas DataFrame to store
        sheet_name: Optional sheet name for Excel files
        
    Returns:
        The composite key used to store the dataframe
    """
    key = get_sheet_key(file_id, sheet_name)
    dataframes[key] = df.copy()
    return key


def store_file_content(file_id: str, content: bytes, filename: str) -> None:
    """Store original file content for formatted preview"""
    file_contents[file_id] = (content, filename)


def get_file_content(file_id: str) -> Optional[Tuple[bytes, str]]:
    """Retrieve original file content and filename"""
    return file_contents.get(file_id)


def get_dataframe(file_id: str, sheet_name: Optional[str] = None) -> pd.DataFrame:
    """
    Retrieve a dataframe from memory using composite key.
    
    Args:
        file_id: The unique file identifier
        sheet_name: Optional sheet name for Excel files
        
    Returns:
        A copy of the stored DataFrame
        
    Raises:
        ValueError: If the dataframe is not found
    """
    key = get_sheet_key(file_id, sheet_name)
    if key not in dataframes:
        raise ValueError(f"Dataframe not found for file_id={file_id}, sheet_name={sheet_name}")
    return dataframes[key].copy()


def has_dataframe(file_id: str, sheet_name: Optional[str] = None) -> bool:
    """
    Check if a dataframe exists for the given file_id and sheet_name.
    
    Args:
        file_id: The unique file identifier
        sheet_name: Optional sheet name for Excel files
        
    Returns:
        True if the dataframe exists, False otherwise
    """
    key = get_sheet_key(file_id, sheet_name)
    return key in dataframes


def update_dataframe(file_id: str, df: pd.DataFrame, sheet_name: Optional[str] = None) -> str:
    """
    Update a dataframe in memory. Creates if not exists.
    
    Args:
        file_id: The unique file identifier
        df: The updated pandas DataFrame
        sheet_name: Optional sheet name for Excel files
        
    Returns:
        The composite key used to store the dataframe
    """
    key = get_sheet_key(file_id, sheet_name)
    dataframes[key] = df.copy()
    return key


def delete_dataframe(file_id: str, sheet_name: Optional[str] = None) -> None:
    """
    Delete a specific dataframe from memory.
    
    Args:
        file_id: The unique file identifier  
        sheet_name: Optional sheet name. If None, deletes the base file_id entry
    """
    key = get_sheet_key(file_id, sheet_name)
    if key in dataframes:
        del dataframes[key]


def delete_all_file_data(file_id: str) -> None:
    """
    Delete all dataframes and content associated with a file_id.
    This removes all sheets for an Excel file.
    
    Args:
        file_id: The unique file identifier
    """
    # Delete all dataframes with this file_id prefix
    keys_to_delete = [k for k in dataframes.keys() if k == file_id or k.startswith(f"{file_id}:")]
    for key in keys_to_delete:
        del dataframes[key]
    
    # Also delete file content if stored
    if file_id in file_contents:
        del file_contents[file_id]


def list_file_ids() -> List[str]:
    """List all unique file IDs (not including sheet-specific keys)"""
    unique_ids = set()
    for key in dataframes.keys():
        file_id, _ = parse_sheet_key(key)
        unique_ids.add(file_id)
    return list(unique_ids)


def list_sheets_for_file(file_id: str) -> List[str]:
    """
    List all sheet names stored for a given file_id.
    
    Args:
        file_id: The unique file identifier
        
    Returns:
        List of sheet names that have stored dataframes
    """
    sheets = []
    for key in dataframes.keys():
        parsed_file_id, sheet_name = parse_sheet_key(key)
        if parsed_file_id == file_id and sheet_name is not None:
            sheets.append(sheet_name)
    return sheets

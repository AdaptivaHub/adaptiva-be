import os
import uuid
import pandas as pd
from typing import Dict, Optional, Tuple
from pathlib import Path

# In-memory storage for uploaded dataframes
dataframes: Dict[str, pd.DataFrame] = {}

# In-memory storage for original file content (for formatted preview)
file_contents: Dict[str, Tuple[bytes, str]] = {}  # file_id -> (content, filename)

# Upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


def generate_file_id() -> str:
    """Generate a unique file ID"""
    return str(uuid.uuid4())


def store_dataframe(file_id: str, df: pd.DataFrame) -> None:
    """Store a dataframe in memory"""
    dataframes[file_id] = df.copy()


def store_file_content(file_id: str, content: bytes, filename: str) -> None:
    """Store original file content for formatted preview"""
    file_contents[file_id] = (content, filename)


def get_file_content(file_id: str) -> Optional[Tuple[bytes, str]]:
    """Retrieve original file content and filename"""
    return file_contents.get(file_id)


def get_dataframe(file_id: str) -> pd.DataFrame:
    """Retrieve a dataframe from memory"""
    if file_id not in dataframes:
        raise ValueError(f"File ID {file_id} not found")
    return dataframes[file_id].copy()


def update_dataframe(file_id: str, df: pd.DataFrame) -> None:
    """Update a dataframe in memory"""
    if file_id not in dataframes:
        raise ValueError(f"File ID {file_id} not found")
    dataframes[file_id] = df.copy()


def delete_dataframe(file_id: str) -> None:
    """Delete a dataframe from memory"""
    if file_id in dataframes:
        del dataframes[file_id]
    # Also delete file content if stored
    if file_id in file_contents:
        del file_contents[file_id]


def list_file_ids() -> list:
    """List all stored file IDs"""
    return list(dataframes.keys())

from typing import Dict, Any, List, Optional
from pydantic import BaseModel

class PageContent(BaseModel):
    """Contents of a web page"""
    url: str
    html: str
    title: Optional[str] = None
    
class ScreenshotResult(BaseModel):
    """Result of taking a screenshot"""
    success: bool
    url: str
    file_path: str
    error: Optional[str] = None
    
class BrowserOptions(BaseModel):
    """Options for browser configuration"""
    headless: bool = False
    width: int = 1920
    height: int = 1080
    user_agent: Optional[str] = None
    timeout: int = 30
    disable_images: bool = False
    disable_javascript: bool = False
    proxy: Optional[str] = None 
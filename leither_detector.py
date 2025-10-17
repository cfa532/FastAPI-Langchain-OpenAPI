"""
Leither Service Port Detector
Uses system commands to detect the port where Leither service is running
"""

import asyncio
import subprocess
import aiohttp
import logging
import os
import json
from typing import Optional, List, Tuple
from datetime import datetime
import re

logger = logging.getLogger(__name__)

class LeitherPortDetector:
    """Detects and manages Leither service port"""
    
    def __init__(self, cache_file="leither_port_cache.json"):
        self.detected_port: Optional[int] = None
        self.default_port = 8080
        self.port_range = (8000, 9000)
        self.cache_file = cache_file
        
        # Try to load cached port on initialization
        self._load_cached_port()
    
    async def detect_leither_port(self) -> Optional[int]:
        """
        Detect Leither service port using netstat to find listening processes
        Returns: The port number or None if not found
        """
        try:
            logger.info('Detecting Leither service port...')
            
            # Use netstat to find all listening ports
            try:
                result = await self._run_command('netstat -tlnp')
                if result and result.strip():
                    lines = [line.strip() for line in result.split('\n') if line.strip()]
                    logger.info(f'Found listening ports: {len(lines)}')
                    
                    for line in lines:
                        if 'LISTEN' in line:
                            port_match = re.search(r':(\d{4,5})\s', line)
                            if port_match:
                                port = int(port_match.group(1))
                                if self.port_range[0] <= port <= self.port_range[1]:
                                    logger.info(f'Testing port {port} for Leither webapi endpoint...')
                                    is_web_api = await self._test_web_api_endpoint(port)
                                    if is_web_api:
                                        logger.info(f'Found valid Leither webapi endpoint on port {port}')
                                        return port
                                    else:
                                        logger.info(f'Port {port} does not have valid Leither service')
            except Exception as error:
                logger.warning(f'Error using netstat: {error}')
            
            logger.warning('Could not detect Leither service port automatically')
            return None
            
        except Exception as error:
            logger.error(f'Error detecting Leither port: {error}')
            return None
    
    async def _test_web_api_endpoint(self, port: int) -> bool:
        """
        Test if a port has a valid Leither webapi endpoint
        Args:
            port: Port to test
        Returns:
            True if valid Leither webapi endpoint exists
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Test for webapi endpoint specifically
                async with session.get(
                    f'http://localhost:{port}/webapi/',
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as response:
                    logger.info(f'Port {port} webapi response status: {response.status}')
                    # Only 200 response indicates valid endpoint
                    if response.status == 200:
                        logger.info(f'Port {port} has valid webapi endpoint, assuming it is Leither service')
                        return True
                    else:
                        logger.info(f'Port {port} webapi endpoint returned {response.status}, not valid Leither service')
                        return False
        except Exception as e:
            logger.info(f'Port {port} connection test failed: {e}')
            return False
    
    async def _test_port_connection(self, port: int) -> bool:
        """
        Test connection to a specific port
        Args:
            port: Port to test
        Returns:
            True if connection successful
        """
        return await self._test_web_api_endpoint(port)
    
    async def get_leither_port(self) -> int:
        """
        Get the best available Leither port
        Returns:
            The port number (defaults to 8081 if not found)
        """
        if self.detected_port is not None:
            # Test if previously detected port is still working
            is_connectable = await self._test_port_connection(self.detected_port)
            if is_connectable:
                logger.info(f'Using previously detected Leither port: {self.detected_port}')
                return self.detected_port
            else:
                logger.warning(f'Previously detected port {self.detected_port} is no longer available')
                self.detected_port = None
        
        # Try to detect new port
        detected_port = await self.detect_leither_port()
        
        if detected_port:
            is_connectable = await self._test_port_connection(detected_port)
            if is_connectable:
                self.detected_port = detected_port
                self._save_cached_port()  # Save to cache
                logger.info(f'Using detected Leither port: {detected_port}')
                return detected_port
        
        # No fallback - throw exception if no port detected
        raise RuntimeError(f'Leither service not detected on any port in range {self.port_range[0]}-{self.port_range[1]}. Please ensure Leither service is running.')
    
    async def _run_command(self, command: str) -> str:
        """
        Run a shell command asynchronously
        Args:
            command: Command to run
        Returns:
            Command output as string
        """
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode('utf-8')
            else:
                logger.warning(f'Command failed: {command}, error: {stderr.decode("utf-8")}')
                return ""
        except Exception as e:
            logger.error(f'Error running command {command}: {e}')
            return ""
    
    def get_cached_port(self) -> Optional[int]:
        """
        Get the currently cached port without testing
        Returns:
            Cached port number or None
        """
        return self.detected_port
    
    def set_port(self, port: int) -> None:
        """
        Manually set the port (useful for testing or configuration)
        Args:
            port: Port number to set
        """
        self.detected_port = port
        self._save_cached_port()
        logger.info(f'Manually set Leither port to: {port}')
    
    def _load_cached_port(self) -> None:
        """Load cached port from file if it exists"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    data = json.load(f)
                    cached_port = data.get('port')
                    timestamp = data.get('timestamp')
                    
                    # Check if cache is recent (within 24 hours)
                    if cached_port and timestamp:
                        import time
                        age_hours = (time.time() - timestamp) / 3600
                        if age_hours < 24:  # Cache valid for 24 hours
                            self.detected_port = cached_port
                            logger.info(f'Loaded cached Leither port: {cached_port} (age: {age_hours:.1f}h)')
                        else:
                            logger.info(f'Cached port expired (age: {age_hours:.1f}h), will redetect')
                    else:
                        logger.info('Invalid cache file format, will redetect')
        except Exception as e:
            logger.warning(f'Error loading cached port: {e}')
    
    def _save_cached_port(self) -> None:
        """Save current port to cache file"""
        try:
            import time
            cache_data = {
                'port': self.detected_port,
                'timestamp': time.time(),
                'detected_at': datetime.now().isoformat()
            }
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            logger.info(f'Saved Leither port {self.detected_port} to cache')
        except Exception as e:
            logger.warning(f'Error saving cached port: {e}')

# Global instance
leither_port_detector = LeitherPortDetector()

# Convenience functions
async def detect_leither_port() -> Optional[int]:
    """Detect Leither service port"""
    return await leither_port_detector.detect_leither_port()

async def get_leither_port() -> int:
    """Get the best available Leither port"""
    return await leither_port_detector.get_leither_port()

async def test_port_connection(port: int) -> bool:
    """Test connection to a specific port"""
    return await leither_port_detector._test_port_connection(port)

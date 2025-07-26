#!/usr/bin/env python3
"""
GitHub Chat API Script
"""

import os
import sys
import json
import asyncio
import argparse
import time
from typing import Dict, Optional, NamedTuple, Any, List
from dataclasses import dataclass

try:
    import aiohttp
    import requests
except ImportError:
    print("Required packages not found. Install with: uv add aiohttp requests")
    sys.exit(1)


@dataclass
class GitHubConfig:
    """Configuration for GitHub API access"""

    token: str
    base_url: str = "https://api.github.com"
    editor_name: str = "vscode"
    editor_version: str = "1.346.0"
    plugin_name: str = "copilot-chat"
    plugin_version: str = "1.7.21"


class NameAndVersion(NamedTuple):
    name: str
    version: str

    def format(self) -> str:
        return f"{self.name}/{self.version}"


@dataclass
class TokenInfo:
    """GitHub Copilot token information"""

    token: str
    expires_at: int
    refresh_in: int

    @classmethod
    def from_response(cls, data: Dict[str, Any]) -> "TokenInfo":
        """Create TokenInfo from API response"""
        return cls(
            token=data["token"],
            expires_at=data["expires_at"],
            refresh_in=data["refresh_in"],
        )


@dataclass
class ExtendedTokenInfo:
    """Extended token information with additional metadata"""

    token: str
    expires_at: int
    refresh_in: int
    username: str = "NullUser"
    copilot_plan: str = "unknown"
    isVscodeTeamMember: bool = False


def now_seconds() -> int:
    """Get current time in seconds since epoch"""
    return int(time.time())


class GitHubTokenManager:
    """Manages GitHub token authentication and Copilot token retrieval"""

    def __init__(self, config: GitHubConfig):
        self.config = config
        self._cached_token: Optional[ExtendedTokenInfo] = None
        self._fetch_in_progress = False

    def get_editor_info(self) -> NameAndVersion:
        """Get editor name and version"""
        return NameAndVersion(self.config.editor_name, self.config.editor_version)

    def get_editor_plugin_info(self) -> NameAndVersion:
        """Get editor plugin name and version"""
        return NameAndVersion(self.config.plugin_name, self.config.plugin_version)

    def get_editor_version_headers(self) -> Dict[str, str]:
        """Get headers with editor version information"""
        return {
            "Editor-Version": self.get_editor_info().format(),
            "Editor-Plugin-Version": self.get_editor_plugin_info().format(),
        }

    async def validate_token(self) -> bool:
        """
        Validate GitHub token by checking user info

        Returns:
            True if token is valid, False otherwise
        """
        url = f"{self.config.base_url}/user"
        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        user_info = await response.json()
                        print(
                            f"Token valid for user: {user_info.get('login', 'Unknown')}"
                        )
                        return True
                    else:
                        print(f"Token validation failed: {response.status}")
                        return False
        except Exception as e:
            print(f"Token validation error: {e}")
            return False

    async def get_copilot_token(self) -> Optional[ExtendedTokenInfo]:
        """
        Get GitHub Copilot internal token with proper error handling and token extension

        Returns:
            ExtendedTokenInfo object or None if failed
        """
        url = f"{self.config.base_url}/copilot_internal/v2/token"
        headers = {
            "Authorization": f"token {self.config.token}",
            "Accept": "application/json",
            "User-Agent": f"{self.config.editor_name}/{self.config.editor_version}",
            **self.get_editor_version_headers(),
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    # Get response data
                    try:
                        token_data = await response.json()
                    except Exception:
                        token_data = None

                    # Check for various error conditions
                    if (
                        not response.ok
                        or response.status == 401
                        or response.status == 403
                        or not token_data
                        or not token_data.get("token")
                    ):
                        error_text = (
                            await response.text() if not token_data else str(token_data)
                        )
                        raise Exception(
                            f"Failed to get copilot token: {response.status} {response.reason}. {error_text}"
                        )

                    # Create token info from response
                    token_info = TokenInfo.from_response(token_data)

                    # Adjust expires_at to handle clock skew and provide buffer
                    adjusted_expires_at = (
                        now_seconds() + token_info.refresh_in + 60
                    )  # extra buffer

                    # Create extended token info
                    extended_info = ExtendedTokenInfo(
                        token=token_info.token,
                        expires_at=adjusted_expires_at,
                        refresh_in=token_info.refresh_in,
                        username="NullUser",
                        copilot_plan="unknown",
                        isVscodeTeamMember=False,
                    )

                    print(f"Token will expire in {token_info.refresh_in} seconds")
                    print(
                        f"Adjusted expiry time: {adjusted_expires_at} (current: {now_seconds()})"
                    )

                    return extended_info

        except Exception as e:
            print(f"Request failed: {e}")
            return None

    async def get_cached_or_fresh_token(self) -> Optional[ExtendedTokenInfo]:
        """
        Get cached token if valid, otherwise fetch a new one

        Returns:
            ExtendedTokenInfo object or None if failed
        """
        current_time = now_seconds()

        # Check if we have a cached token that's still valid
        if (
            self._cached_token and self._cached_token.expires_at > current_time + 30
        ):  # 30 second buffer
            print("Using cached token")
            return self._cached_token

        # Prevent multiple simultaneous fetches
        if self._fetch_in_progress:
            print("Token fetch already in progress, waiting...")
            return None

        try:
            self._fetch_in_progress = True
            print("Fetching fresh token...")

            token = await self.get_copilot_token()
            if token:
                self._cached_token = token

                # Schedule token refresh (in a real application, you'd use a proper scheduler)
                refresh_time = token.refresh_in
                print(f"Token cached. Will need refresh in {refresh_time} seconds")

            return token

        finally:
            self._fetch_in_progress = False

    def is_token_expired(self) -> bool:
        """Check if cached token is expired"""
        if not self._cached_token:
            return True
        return now_seconds() >= self._cached_token.expires_at

    def time_until_refresh(self) -> int:
        """Get seconds until token needs refresh"""
        if not self._cached_token:
            return 0
        return max(0, self._cached_token.expires_at - now_seconds())

    @staticmethod
    def setup_device_flow_auth(config: Optional[GitHubConfig] = None) -> Optional[str]:
        """
        Authenticate with GitHub using OAuth device flow

        Args:
            config: Optional GitHubConfig instance for editor/plugin version info.
                   If None, uses default values.

        Returns:
            GitHub access token string or None if failed
        """
        print("Starting GitHub OAuth device flow authentication...")

        # Use default config if none provided
        if config is None:
            config = GitHubConfig(token="")  # Token will be obtained through auth flow

        # Use the standard GitHub Copilot client ID
        client_id = "Iv1.b507a08c87ecfe98"

        # Build headers using config
        editor_info = NameAndVersion(config.editor_name, config.editor_version)
        plugin_info = NameAndVersion(config.plugin_name, config.plugin_version)

        auth_headers = {
            "accept": "application/json",
            "editor-version": editor_info.format(),
            "editor-plugin-version": plugin_info.format(),
            "content-type": "application/json",
            "user-agent": "GithubCopilot/1.155.0",
            "accept-encoding": "gzip,deflate,br",
        }

        try:
            # Step 1: Request device code
            resp = requests.post(
                "https://github.com/login/device/code",
                headers=auth_headers,
                data=f'{{"client_id":"{client_id}","scope":"read:user"}}',
            )

            if resp.status_code != 200:
                print(f"Failed to get device code: {resp.status_code} {resp.text}")
                return None

            # Parse the response json, isolating the device_code, user_code, and verification_uri
            resp_json = resp.json()
            device_code = resp_json.get("device_code")
            user_code = resp_json.get("user_code")
            verification_uri = resp_json.get("verification_uri")

            if not all([device_code, user_code, verification_uri]):
                print(f"Invalid response from GitHub: {resp_json}")
                return None

            # Print the user code and verification uri
            print(
                f"Please visit {verification_uri} and enter code {user_code} to authenticate."
            )
            print("Waiting for authentication...")

            # Step 2: Poll for access token
            while True:
                time.sleep(5)
                resp = requests.post(
                    "https://github.com/login/oauth/access_token",
                    headers=auth_headers,
                    data=f'{{"client_id":"{client_id}","device_code":"{device_code}","grant_type":"urn:ietf:params:oauth:grant-type:device_code"}}',
                )

                # Parse the response json, isolating the access_token
                resp_json = resp.json()

                # Check for errors
                if resp_json.get("error"):
                    error = resp_json.get("error")
                    if error == "authorization_pending":
                        continue  # Keep polling
                    elif error == "slow_down":
                        print("Polling too fast, slowing down...")
                        time.sleep(10)
                        continue
                    elif error == "expired_token":
                        print("Device code expired. Please restart authentication.")
                        return None
                    elif error == "access_denied":
                        print("Authentication was denied.")
                        return None
                    else:
                        print(f"Authentication error: {error}")
                        return None

                access_token = resp_json.get("access_token")
                if access_token:
                    break

            # Save the access token to a file
            token_file = ".copilot_token"
            with open(token_file, "w") as f:
                f.write(access_token)

            print("Authentication success!")
            print(f"Token saved to {token_file}")
            return access_token

        except Exception as e:
            print(f"Device flow authentication failed: {e}")
            return None

    @staticmethod
    def load_token_from_file() -> Optional[str]:
        """
        Load GitHub token from .copilot_token file

        Returns:
            GitHub token string or None if not found
        """
        token_file = ".copilot_token"
        if os.path.exists(token_file):
            try:
                with open(token_file, "r") as f:
                    token = f.read().strip()
                    if token:
                        print(f"Loaded token from {token_file}")
                        return token
            except Exception as e:
                print(f"Error reading token file: {e}")
        return None

    @staticmethod
    def get_github_token(
        use_device_flow: bool = True, config: Optional[GitHubConfig] = None
    ) -> Optional[str]:
        """
        Get GitHub token from various sources

        Args:
            use_device_flow: Whether to use OAuth device flow for authentication (default: True)
            config: Optional GitHubConfig instance for editor/plugin version info

        Returns:
            GitHub token string or None if not found
        """
        # Try loading from file first
        token = GitHubTokenManager.load_token_from_file()
        if token:
            return token

        # Use device flow by default when no token is found
        if use_device_flow:
            print(
                "No existing token found. Starting OAuth device flow authentication..."
            )
            return GitHubTokenManager.setup_device_flow_auth(config)

        # Fallback to manual input
        print("GitHub token not found in file.")
        print("Enter token manually or use device flow authentication.")
        token = input("Enter GitHub token (or press Enter to skip): ").strip()

        return token if token else None


class CopilotChatOrchestrator:
    """Orchestrates chat interactions with GitHub Copilot"""

    def __init__(self, token_manager: GitHubTokenManager, model: str = "gpt-4o"):
        self.token_manager = token_manager
        self.model = model
        self.chat_messages: List[Dict[str, str]] = []
        self._current_copilot_token: Optional[str] = None

    async def _ensure_copilot_token(self) -> bool:
        """Ensure we have a valid Copilot token"""
        if self._current_copilot_token is None:
            # Validate GitHub token first
            is_valid = await self.token_manager.validate_token()
            if not is_valid:
                print("Invalid GitHub token")
                return False

            # Get Copilot token
            copilot_token_info = await self.token_manager.get_copilot_token()
            if copilot_token_info:
                self._current_copilot_token = copilot_token_info.token
                print("Successfully obtained Copilot token for chat")
                return True
            else:
                print("Failed to obtain Copilot token for chat")
                return False
        return True

    async def send_message(self, message: str) -> str:
        """
        Send a message to GitHub Copilot and get response

        Args:
            message: User message to send to the chat

        Returns:
            Assistant's response as a string
        """
        # Ensure we have a valid Copilot token
        if not await self._ensure_copilot_token():
            return "Error: Unable to obtain Copilot token"

        self.chat_messages.append({"content": str(message), "role": "user"})

        try:
            # Build headers using token manager's config
            editor_info = self.token_manager.get_editor_info()

            resp = requests.post(
                "https://api.githubcopilot.com/chat/completions",
                headers={
                    "authorization": f"Bearer {self._current_copilot_token}",
                    "Editor-Version": editor_info.format(),
                    "Content-Type": "application/json",
                    "Accept": "text/event-stream",
                },
                json={
                    "intent": False,
                    "model": self.model,
                    "temperature": 0,
                    "top_p": 1,
                    "n": 1,
                    "stream": True,
                    "messages": self.chat_messages,
                },
            )
        except requests.exceptions.ConnectionError:
            return "Error: Connection failed"

        result = ""

        # Parse the response text, splitting it by newlines
        resp_text = resp.text.split("\n")
        for line in resp_text:
            # If the line contains a completion, process it
            if line.startswith("data: {"):
                try:
                    # Parse the completion from the line as json
                    json_completion = json.loads(line[6:])
                    choices = json_completion.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        completion = delta.get("content")
                        if completion:
                            result += completion
                        else:
                            result += "\n"
                except (json.JSONDecodeError, KeyError, IndexError):
                    pass

        self.chat_messages.append({"content": result, "role": "assistant"})

        if result == "":
            print(f"Chat error - Status code: {resp.status_code}")
            print(f"Response: {resp.text}")
            return f"Error: No response received (Status: {resp.status_code})"

        return result

    def clear_history(self):
        """Clear the chat message history"""
        self.chat_messages = []
        print("Chat history cleared")

    def show_history(self):
        """Display the current chat history"""
        if not self.chat_messages:
            print("No chat history")
            return

        print("Chat History:")
        print("-" * 50)
        for i, msg in enumerate(self.chat_messages):
            role = msg["role"].capitalize()
            content = msg["content"]
            print(f"{i+1}. {role}: {content}")
            print("-" * 50)

    async def start_interactive_session(self):
        """Start an interactive chat session"""
        print(f"Starting interactive chat with GitHub Copilot ({self.model})")
        print("Type 'quit', 'exit', or 'bye' to end the session")
        print("Type 'clear' to clear chat history")
        print("Type 'history' to show chat history")
        print("-" * 50)

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() in ["quit", "exit", "bye"]:
                    print("Goodbye!")
                    break
                elif user_input.lower() == "clear":
                    self.clear_history()
                    continue
                elif user_input.lower() == "history":
                    self.show_history()
                    continue
                elif not user_input:
                    continue

                print("Copilot: ", end="", flush=True)
                response = await self.send_message(user_input)
                print(response)

            except KeyboardInterrupt:
                print("\n\nGoodbye!")
                break
            except Exception as e:
                print(f"\nError during chat: {e}")


# Legacy functions for backward compatibility
async def get_token_async():
    """Get GitHub Copilot token for chat functionality (async version) - Legacy function"""
    try:
        # Get GitHub token (using existing functionality)
        github_token = GitHubTokenManager.get_github_token(use_device_flow=True)
        if not github_token:
            print("Failed to get GitHub token")
            return False

        # Create config and token manager
        config = GitHubConfig(token=github_token)
        token_manager = GitHubTokenManager(config)

        # Validate token
        is_valid = await token_manager.validate_token()
        if not is_valid:
            print("Invalid GitHub token")
            return False

        # Get Copilot token
        copilot_token_info = await token_manager.get_copilot_token()
        if copilot_token_info:
            global current_copilot_token
            current_copilot_token = copilot_token_info.token
            print("Successfully obtained Copilot token for chat")
            return True
        else:
            print("Failed to obtain Copilot token for chat")
            return False

    except Exception as e:
        print(f"Error getting token: {e}")
        return False


def get_token():
    """Synchronous wrapper for get_token_async - Legacy function"""
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we're already in an event loop, we can't use asyncio.run()
        print(
            "Error: Cannot get token from within running event loop. Use get_token_async() instead."
        )
        return False
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        try:
            return asyncio.run(get_token_async())
        except Exception as e:
            print(f"Error getting token: {e}")
            return False


# Legacy global variables for backward compatibility
current_copilot_token: Optional[str] = None
chat_messages: List[Dict[str, str]] = []
MODEL = "gpt-4o"


async def chat_async(message: str) -> str:
    """Chat with GitHub Copilot using GPT-4o model (async version) - Legacy function"""
    # Create temporary instances for backward compatibility
    github_token = GitHubTokenManager.get_github_token(use_device_flow=True)
    if not github_token:
        return "Error: Unable to obtain GitHub token"

    config = GitHubConfig(token=github_token)
    token_manager = GitHubTokenManager(config)
    chat_orchestrator = CopilotChatOrchestrator(token_manager, MODEL)

    return await chat_orchestrator.send_message(message)


def chat(message: str) -> str:
    """Synchronous wrapper for chat_async - Legacy function"""
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we're already in an event loop, we can't use asyncio.run()
        print(
            "Error: Cannot chat from within running event loop. Use chat_async() instead."
        )
        return "Error: Cannot chat from within running event loop"
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        try:
            return asyncio.run(chat_async(message))
        except Exception as e:
            print(f"Error during chat: {e}")
            return f"Error: {e}"


def clear_chat_history():
    """Clear the chat message history - Legacy function"""
    global chat_messages
    chat_messages = []
    print("Chat history cleared")


def show_chat_history():
    """Display the current chat history - Legacy function"""
    global chat_messages
    if not chat_messages:
        print("No chat history")
        return

    print("Chat History:")
    print("-" * 50)
    for i, msg in enumerate(chat_messages):
        role = msg["role"].capitalize()
        content = msg["content"]
        print(f"{i+1}. {role}: {content}")
        print("-" * 50)


async def interactive_chat_async():
    """Start an interactive chat session (async version) - Legacy function"""
    # Create temporary instances for backward compatibility
    github_token = GitHubTokenManager.get_github_token(use_device_flow=True)
    if not github_token:
        print("Failed to get GitHub token")
        return

    config = GitHubConfig(token=github_token)
    token_manager = GitHubTokenManager(config)
    chat_orchestrator = CopilotChatOrchestrator(token_manager, MODEL)

    await chat_orchestrator.start_interactive_session()


def interactive_chat():
    """Synchronous wrapper for interactive_chat_async - Legacy function"""
    try:
        # Try to get the current event loop
        loop = asyncio.get_running_loop()
        # If we're already in an event loop, we can't use asyncio.run()
        print(
            "Error: Cannot start interactive chat from within running event loop. Use interactive_chat_async() instead."
        )
        return
    except RuntimeError:
        # No event loop running, safe to use asyncio.run()
        try:
            asyncio.run(interactive_chat_async())
        except Exception as e:
            print(f"Error during interactive chat: {e}")


# Legacy alias for backward compatibility
GitHubTokenClient = GitHubTokenManager


async def main():
    """Main function"""
    parser = argparse.ArgumentParser(
        description="GitHub API Token Access Script with Chat Capabilities"
    )
    parser.add_argument("--token", help="GitHub personal access token")
    parser.add_argument(
        "--device-flow",
        action="store_true",
        help="Force OAuth device flow for authentication",
    )
    parser.add_argument(
        "--no-device-flow",
        action="store_true",
        help="Disable OAuth device flow (use manual input instead)",
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Only validate token, do not fetch Copilot token",
    )
    parser.add_argument(
        "--use-cache",
        action="store_true",
        help="Use cached token if available and valid",
    )
    parser.add_argument(
        "--show-status", action="store_true", help="Show token cache status"
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Start interactive chat session with GitHub Copilot",
    )
    parser.add_argument("--message", help="Send a single message to chat and exit")
    parser.add_argument(
        "--model", default="gpt-4o", help="Model to use for chat (default: gpt-4o)"
    )
    parser.add_argument("--editor-name", default="vscode", help="Editor name")
    parser.add_argument("--editor-version", default="1.63.2", help="Editor version")
    parser.add_argument("--plugin-name", default="copilot-chat", help="Plugin name")
    parser.add_argument("--plugin-version", default="1.7.21", help="Plugin version")

    args = parser.parse_args()

    # Set the global model variable for backward compatibility
    global MODEL
    MODEL = args.model

    # Determine device flow usage
    if args.device_flow:
        use_device_flow = True
    elif args.no_device_flow:
        use_device_flow = False
    else:
        use_device_flow = True  # Default to True

    # Create initial config for device flow (if needed)
    initial_config = GitHubConfig(
        token="",  # Will be filled in after authentication
        editor_name=args.editor_name,
        editor_version=args.editor_version,
        plugin_name=args.plugin_name,
        plugin_version=args.plugin_version,
    )

    # Get token
    token = args.token or GitHubTokenManager.get_github_token(
        use_device_flow=use_device_flow, config=initial_config
    )
    if not token:
        print("No GitHub token provided. Exiting.")
        sys.exit(1)

    # Create final config with the obtained token
    config = GitHubConfig(
        token=token,
        editor_name=args.editor_name,
        editor_version=args.editor_version,
        plugin_name=args.plugin_name,
        plugin_version=args.plugin_version,
    )

    token_manager = GitHubTokenManager(config)

    # Handle chat functionality
    if args.chat:
        chat_orchestrator = CopilotChatOrchestrator(token_manager, args.model)
        await chat_orchestrator.start_interactive_session()
        return

    if args.message:
        print(f"Sending message to {args.model}...")
        chat_orchestrator = CopilotChatOrchestrator(token_manager, args.model)
        response = await chat_orchestrator.send_message(args.message)
        print(f"Response: {response}")
        return

    # Validate token
    print("Validating GitHub token...")
    is_valid = await token_manager.validate_token()

    if not is_valid:
        print("Invalid GitHub token. Please check your token and try again.")
        sys.exit(1)

    if args.validate_only:
        print("Token validation complete.")
        return

    # Show status if requested
    if args.show_status:
        print(f"\nToken cache status:")
        print(f"Has cached token: {token_manager._cached_token is not None}")
        if token_manager._cached_token:
            print(f"Token expired: {token_manager.is_token_expired()}")
            print(f"Time until refresh: {token_manager.time_until_refresh()} seconds")
        return

    # Get Copilot token (cached or fresh)
    if args.use_cache:
        print("\nGetting GitHub Copilot token (with caching)...")
        copilot_token = await token_manager.get_cached_or_fresh_token()
    else:
        print("\nFetching fresh GitHub Copilot token...")
        copilot_token = await token_manager.get_copilot_token()

    if copilot_token:
        print("Successfully retrieved Copilot token:")
        print(
            f"Token: {copilot_token.token[:20]}..."
        )  # Only show first 20 chars for security
        print(f"Expires at: {copilot_token.expires_at}")
        print(f"Refresh in: {copilot_token.refresh_in} seconds")
        print(f"Username: {copilot_token.username}")
        print(f"Copilot plan: {copilot_token.copilot_plan}")
        print(f"VS Code team member: {copilot_token.isVscodeTeamMember}")

        # Print full token if requested (be careful with this in logs)
        if input("\nShow full token? (y/N): ").lower().startswith("y"):
            print(f"Full token: {copilot_token.token}")
    else:
        print("Failed to retrieve Copilot token.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

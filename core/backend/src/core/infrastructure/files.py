from pathlib import Path


class FileManager:
    """
    Generic file manager for handling static files across any app.

    Provides path resolution and URL generation for static assets.
    Supports subdirectories and automatic directory creation.

    Usage:
        from pathlib import Path
        from core.infrastructure.files import FileManager

        file_manager = FileManager(
            static_path=Path(__file__).parent / "static",
            api_domain="https://api.example.com"
        )

        # Get file path
        path = file_manager.get_full_path("images/logo.png")

        # Get file URL
        url = file_manager.get_full_url("images/logo.png")
    """

    def __init__(self, static_path: Path, api_domain: str):
        """
        Initialize FileManager.

        Args:
            static_path: Absolute path to static files directory
            api_domain: Base URL for API (e.g., "https://api.example.com")
        """
        self.static_path = static_path
        self.api_domain = api_domain.rstrip("/")  # Remove trailing slash

        # Create static directory if it doesn't exist
        self.static_path.mkdir(parents=True, exist_ok=True)

    def get_full_path(self, file_name: str) -> Path:
        """
        Get absolute path to file in static directory.

        Args:
            file_name: Relative path within static directory
                      (e.g., "images/logo.png", "spreads/spread_123.jpg")

        Returns:
            Absolute path to file
        """
        return self.static_path / file_name

    def get_full_url(self, file_name: str) -> str:
        """
        Get full URL to file in static directory.

        Args:
            file_name: Relative path within static directory

        Returns:
            Full URL to file (e.g., "https://api.example.com/static/images/logo.png")
        """
        return f"{self.api_domain}/static/{file_name}"

    def ensure_subdirectory(self, subdirectory: str) -> Path:
        """
        Ensure a subdirectory exists within static directory.

        Args:
            subdirectory: Subdirectory path (e.g., "images", "spreads")

        Returns:
            Absolute path to subdirectory
        """
        path = self.static_path / subdirectory
        path.mkdir(parents=True, exist_ok=True)
        return path

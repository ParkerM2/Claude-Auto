"""
Recovery Configuration System
==============================

Configuration settings for the self-healing recovery system.
Allows customization of retry limits, timeouts, and strategy preferences.
"""

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RecoveryConfig:
    """
    Configuration for the recovery system.

    Attributes:
        max_retry_attempts: Maximum retry attempts for general failures (default: 3)
        max_retry_attempts_unknown: Maximum retry attempts for unknown errors (default: 2)
        circular_fix_threshold: Number of similar errors before considered circular (default: 3)
        recovery_timeout: Timeout in seconds for recovery attempts (default: 300)
        enable_learning: Whether to enable learning from successful recoveries (default: True)
        enable_auto_rollback: Whether to automatically rollback on failures (default: True)
        enable_pattern_detection: Whether to enable advanced pattern detection (default: True)
        escalation_threshold: Number of failed attempts before escalating to human (default: 5)
    """

    max_retry_attempts: int = 3
    max_retry_attempts_unknown: int = 2
    circular_fix_threshold: int = 3
    recovery_timeout: int = 300
    enable_learning: bool = True
    enable_auto_rollback: bool = True
    enable_pattern_detection: bool = True
    escalation_threshold: int = 5

    @classmethod
    def from_dict(cls, data: dict) -> "RecoveryConfig":
        """
        Create RecoveryConfig from dictionary.

        Args:
            data: Dictionary with config values

        Returns:
            RecoveryConfig instance
        """
        return cls(
            max_retry_attempts=data.get("max_retry_attempts", 3),
            max_retry_attempts_unknown=data.get("max_retry_attempts_unknown", 2),
            circular_fix_threshold=data.get("circular_fix_threshold", 3),
            recovery_timeout=data.get("recovery_timeout", 300),
            enable_learning=data.get("enable_learning", True),
            enable_auto_rollback=data.get("enable_auto_rollback", True),
            enable_pattern_detection=data.get("enable_pattern_detection", True),
            escalation_threshold=data.get("escalation_threshold", 5),
        )

    def to_dict(self) -> dict:
        """
        Convert RecoveryConfig to dictionary.

        Returns:
            Dictionary representation of config
        """
        return {
            "max_retry_attempts": self.max_retry_attempts,
            "max_retry_attempts_unknown": self.max_retry_attempts_unknown,
            "circular_fix_threshold": self.circular_fix_threshold,
            "recovery_timeout": self.recovery_timeout,
            "enable_learning": self.enable_learning,
            "enable_auto_rollback": self.enable_auto_rollback,
            "enable_pattern_detection": self.enable_pattern_detection,
            "escalation_threshold": self.escalation_threshold,
        }


def load_config(
    config_file: Path | None = None, env_prefix: str = "RECOVERY_"
) -> RecoveryConfig:
    """
    Load recovery configuration from file or environment variables.

    Priority order:
    1. Configuration file (if provided)
    2. Environment variables
    3. Default values

    Args:
        config_file: Optional path to JSON config file
        env_prefix: Prefix for environment variables (default: "RECOVERY_")

    Returns:
        RecoveryConfig instance

    Example:
        # Load from defaults
        config = load_config()

        # Load from file
        config = load_config(Path(".auto-claude/recovery_config.json"))

        # Environment variables:
        # RECOVERY_MAX_RETRY_ATTEMPTS=5
        # RECOVERY_ENABLE_LEARNING=false
    """
    config_data = {}

    # Load from config file if provided
    if config_file and config_file.exists():
        try:
            with open(config_file, encoding="utf-8") as f:
                file_data = json.load(f)
                if isinstance(file_data, dict):
                    config_data.update(file_data)
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            # If file loading fails, continue with env vars and defaults
            pass

    # Override with environment variables
    env_mappings = {
        f"{env_prefix}MAX_RETRY_ATTEMPTS": "max_retry_attempts",
        f"{env_prefix}MAX_RETRY_ATTEMPTS_UNKNOWN": "max_retry_attempts_unknown",
        f"{env_prefix}CIRCULAR_FIX_THRESHOLD": "circular_fix_threshold",
        f"{env_prefix}RECOVERY_TIMEOUT": "recovery_timeout",
        f"{env_prefix}ENABLE_LEARNING": "enable_learning",
        f"{env_prefix}ENABLE_AUTO_ROLLBACK": "enable_auto_rollback",
        f"{env_prefix}ENABLE_PATTERN_DETECTION": "enable_pattern_detection",
        f"{env_prefix}ESCALATION_THRESHOLD": "escalation_threshold",
    }

    for env_var, config_key in env_mappings.items():
        env_value = os.environ.get(env_var)
        if env_value is not None:
            # Parse based on type
            if config_key in [
                "max_retry_attempts",
                "max_retry_attempts_unknown",
                "circular_fix_threshold",
                "recovery_timeout",
                "escalation_threshold",
            ]:
                try:
                    config_data[config_key] = int(env_value)
                except ValueError:
                    pass
            elif config_key in [
                "enable_learning",
                "enable_auto_rollback",
                "enable_pattern_detection",
            ]:
                config_data[config_key] = env_value.lower() in ("true", "1", "yes")

    return RecoveryConfig.from_dict(config_data)


def save_config(config: RecoveryConfig, config_file: Path) -> None:
    """
    Save recovery configuration to file.

    Args:
        config: RecoveryConfig instance to save
        config_file: Path to save config file

    Example:
        config = RecoveryConfig(max_retry_attempts=5)
        save_config(config, Path(".auto-claude/recovery_config.json"))
    """
    config_file.parent.mkdir(parents=True, exist_ok=True)
    with open(config_file, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2)

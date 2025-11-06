"""Model registry utilities derived from configuration."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from models.config import Config, ModelDefinition


@dataclass(frozen=True)
class RegistryEntry:
    """Normalized model definition entry."""

    id: str
    label: str
    tier: Optional[str] = None
    note: Optional[str] = None
    default: bool = False


class ModelRegistry:
    """In-memory view of configured model options per adapter."""

    def __init__(self, config: Config):
        self._entries: Dict[str, list[RegistryEntry]] = {}

        registry_cfg = getattr(config, "model_registry", None) or {}
        for cli, models in registry_cfg.items():
            normalized = []
            for model in models:
                # Pydantic ensures the structure, but guard against None just in case
                if isinstance(model, ModelDefinition):
                    model_def = model
                else:
                    model_def = ModelDefinition.model_validate(model)

                normalized.append(
                    RegistryEntry(
                        id=model_def.id,
                        label=model_def.label or model_def.id,
                        tier=model_def.tier,
                        note=model_def.note,
                        default=bool(model_def.default),
                    )
                )

            # Ensure deterministic ordering (defaults first, then alphabetical)
            normalized.sort(
                key=lambda entry: (
                    not entry.default,
                    entry.label.lower(),
                )
            )
            self._entries[cli] = normalized

    # ------------------------------------------------------------------
    # Introspection helpers
    # ------------------------------------------------------------------
    def adapters(self) -> Iterable[str]:
        """Return adapter names with registry entries."""

        return self._entries.keys()

    def list(self) -> Dict[str, list[dict[str, str]]]:
        """Return a serializable map of model options by adapter."""

        result: Dict[str, list[dict[str, str]]] = {}
        for cli, entries in self._entries.items():
            result[cli] = [self._entry_to_dict(entry) for entry in entries]
        return result

    def list_for_adapter(self, cli: str) -> list[RegistryEntry]:
        """Return entries for the given adapter (empty if none configured)."""

        return list(self._entries.get(cli, []))

    def allowed_ids(self, cli: str) -> set[str]:
        """Return the set of allowed model IDs for an adapter."""

        return {entry.id for entry in self._entries.get(cli, [])}

    def get_default(self, cli: str) -> Optional[str]:
        """Return the default model id for an adapter, if configured."""

        entries = self._entries.get(cli, [])
        if not entries:
            return None

        for entry in entries:
            if entry.default:
                return entry.id
        return entries[0].id

    def is_allowed(self, cli: str, model_id: str) -> bool:
        """Check whether the given model id is allowlisted for the adapter."""

        if cli not in self._entries:
            return True  # Unrestricted adapter (e.g., open router, custom paths)
        return model_id in self.allowed_ids(cli)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _entry_to_dict(entry: RegistryEntry) -> dict[str, str]:
        """Serialize an entry for MCP responses."""

        payload = {
            "id": entry.id,
            "label": entry.label,
        }
        if entry.tier:
            payload["tier"] = entry.tier
        if entry.note:
            payload["note"] = entry.note
        if entry.default:
            payload["default"] = True
        return payload

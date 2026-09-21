"""RBAC (Role-Based Access Control) enforcement for retrieval results."""

import logging
from dataclasses import dataclass, field
from typing import Any

from app.retrieval.base import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class RBACConfig:
    """Configuration for RBAC enforcement."""

    # Default role when user role is not specified or unknown
    default_role: str = "user"

    # Role definitions: role -> list of allowed folder paths
    # Use "*" for wildcard (all folders)
    role_permissions: dict[str, list[str]] = field(default_factory=dict)

    # Whether to enforce RBAC at all
    enabled: bool = True

    # Whether to filter at retrieval time (add filters to query)
    filter_at_retrieval: bool = True

    # Whether to filter post-retrieval (after results are returned)
    filter_post_retrieval: bool = True

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RBACConfig":
        """Create from dictionary."""
        return cls(
            default_role=data.get("default_role", "user"),
            role_permissions=data.get("role_permissions", {}),
            enabled=data.get("enabled", True),
            filter_at_retrieval=data.get("filter_at_retrieval", True),
            filter_post_retrieval=data.get("filter_post_retrieval", True),
        )

    def __post_init__(self):
        """Set default role permissions if not provided."""
        if not self.role_permissions:
            # Default RBAC setup
            self.role_permissions = {
                "admin": ["*"],  # Admin can access all folders
                "user": ["/public", "/shared"],  # Regular users
                "guest": ["/public"],  # Guests only public content
            }


class RBACEnforcer:
    """
    Enforces role-based access control on retrieval results.

    Filters retrieval results based on user role permissions to ensure
    users can only access documents from allowed folders.
    """

    def __init__(self, rbac_config: RBACConfig | None = None):
        """
        Initialize RBAC enforcer.

        Args:
            rbac_config: RBAC configuration
        """
        self.config = rbac_config or RBACConfig()
        self._role_permissions = self.config.role_permissions

    def get_allowed_folders(self, role: str | None = None) -> list[str]:
        """
        Get list of allowed folder paths for a role.

        Args:
            role: User role (uses default_role if not specified)

        Returns:
            List of allowed folder paths
        """
        if not self.config.enabled:
            return ["*"]  # All folders allowed if RBAC disabled

        if not role:
            role = self.config.default_role

        if role not in self._role_permissions:
            logger.warning(f"Unknown role '{role}', using default role")
            role = self.config.default_role

            # If still not found, return empty list (no access)
            if role not in self._role_permissions:
                return []

        return self._role_permissions.get(role, [])

    def has_access(self, role: str | None, folder_path: str | None) -> bool:
        """
        Check if a role has access to a specific folder.

        Args:
            role: User role
            folder_path: Folder path to check

        Returns:
            True if role has access to the folder
        """
        if not self.config.enabled:
            return True

        if not folder_path:
            # No folder info, assume accessible
            return True

        allowed_folders = self.get_allowed_folders(role)

        # Wildcard check
        if "*" in allowed_folders:
            return True

        # Check if folder is in allowed list
        return folder_path in allowed_folders

    def build_filter(self, role: str | None) -> dict[str, Any] | None:
        """
        Build MongoDB filter for allowed folders.

        Args:
            role: User role

        Returns:
            MongoDB filter dict or None if no filter needed
        """
        if not self.config.enabled or not self.config.filter_at_retrieval:
            return None

        allowed_folders = self.get_allowed_folders(role)

        # No folders allowed
        if not allowed_folders:
            return {"folder_path": {"$in": []}}  # Will match nothing

        # Wildcard - no filter needed
        if "*" in allowed_folders:
            return None

        # Build filter
        return {"folder_path": {"$in": allowed_folders}}

    def build_atlas_filter(self, role: str | None) -> list[dict[str, Any]] | None:
        """
        Build Atlas Search filter clauses for allowed folders.

        Args:
            role: User role

        Returns:
            List of Atlas Search filter clauses or None
        """
        if not self.config.enabled or not self.config.filter_at_retrieval:
            return None

        allowed_folders = self.get_allowed_folders(role)

        # No folders allowed
        if not allowed_folders:
            return [{"in": {"path": "folder_path", "value": []}}]

        # Wildcard - no filter needed
        if "*" in allowed_folders:
            return None

        # Build Atlas Search filter
        return [{"in": {"path": "folder_path", "value": allowed_folders}}]

    def filter_results(
        self,
        results: list[RetrievedChunk],
        role: str | None,
    ) -> list[RetrievedChunk]:
        """
        Filter retrieval results based on role permissions.

        Args:
            results: List of retrieved chunks
            role: User role

        Returns:
            Filtered list of chunks
        """
        if not self.config.enabled or not self.config.filter_post_retrieval:
            return results

        allowed_folders = self.get_allowed_folders(role)

        # Wildcard - allow all
        if "*" in allowed_folders:
            return results

        # Filter results
        filtered = []
        for chunk in results:
            folder_path = chunk.folder_path

            # If no folder info, include it (will be filtered at display time if needed)
            if not folder_path:
                filtered.append(chunk)
                continue

            # Check if folder is allowed
            if folder_path in allowed_folders:
                filtered.append(chunk)

        logger.debug(
            f"RBAC filtered {len(results)} -> {len(filtered)} results for role '{role}'"
        )
        return filtered

    def filter_by_access_tags(
        self,
        results: list[RetrievedChunk],
        user_tags: list[str],
    ) -> list[RetrievedChunk]:
        """
        Filter results by access tags.

        Args:
            results: List of retrieved chunks
            user_tags: List of tags the user has access to

        Returns:
            Filtered list of chunks
        """
        if not self.config.enabled:
            return results

        if not user_tags:
            # No tags means no access control by tags
            return results

        filtered = []
        for chunk in results:
            chunk_tags = chunk.access_tags or []

            # If chunk has no tags, include it
            if not chunk_tags:
                filtered.append(chunk)
                continue

            # Check if any user tag matches chunk tags
            if any(tag in chunk_tags for tag in user_tags):
                filtered.append(chunk)

        return filtered

    def get_accessible_chunk_ids(
        self,
        role: str | None,
        all_chunks: list[RetrievedChunk],
    ) -> set[str]:
        """
        Get set of accessible chunk IDs for a role.

        Args:
            role: User role
            all_chunks: List of all available chunks

        Returns:
            Set of accessible chunk IDs
        """
        if not self.config.enabled:
            return {c.chunk_id for c in all_chunks}

        allowed_folders = self.get_allowed_folders(role)

        if "*" in allowed_folders:
            return {c.chunk_id for c in all_chunks}

        accessible_ids = set()
        for chunk in all_chunks:
            if chunk.folder_path in allowed_folders:
                accessible_ids.add(chunk.chunk_id)

        return accessible_ids

    def can_access_document(
        self,
        role: str | None,
        folder_path: str | None,
        access_tags: list[str] | None = None,
        user_tags: list[str] | None = None,
    ) -> bool:
        """
        Comprehensive access check including folder and tags.

        Args:
            role: User role
            folder_path: Document folder path
            access_tags: Document access tags
            user_tags: User's access tags

        Returns:
            True if user can access the document
        """
        if not self.config.enabled:
            return True

        # Check folder access
        if not self.has_access(role, folder_path):
            return False

        # Check tag access if both document and user have tags
        if access_tags and user_tags:
            if not any(tag in access_tags for tag in user_tags):
                return False

        return True

    def add_role(self, role: str, allowed_folders: list[str]) -> None:
        """
        Add or update a role with allowed folders.

        Args:
            role: Role name
            allowed_folders: List of allowed folder paths
        """
        self._role_permissions[role] = allowed_folders
        logger.info(f"Added role '{role}' with folders: {allowed_folders}")

    def remove_role(self, role: str) -> bool:
        """
        Remove a role.

        Args:
            role: Role name

        Returns:
            True if role was removed
        """
        if role in self._role_permissions:
            del self._role_permissions[role]
            logger.info(f"Removed role '{role}'")
            return True
        return False

    def update_role_folders(self, role: str, allowed_folders: list[str]) -> bool:
        """
        Update allowed folders for a role.

        Args:
            role: Role name
            allowed_folders: New list of allowed folders

        Returns:
            True if role was updated
        """
        if role in self._role_permissions:
            self._role_permissions[role] = allowed_folders
            logger.info(f"Updated role '{role}' folders: {allowed_folders}")
            return True
        return False

    def list_roles(self) -> list[str]:
        """
        Get list of all defined roles.

        Returns:
            List of role names
        """
        return list(self._role_permissions.keys())

    def get_role_permissions(self) -> dict[str, list[str]]:
        """
        Get all role permissions.

        Returns:
            Dictionary of role -> allowed folders
        """
        return self._role_permissions.copy()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "enabled": self.config.enabled,
            "default_role": self.config.default_role,
            "role_permissions": self._role_permissions,
            "filter_at_retrieval": self.config.filter_at_retrieval,
            "filter_post_retrieval": self.config.filter_post_retrieval,
        }


class RBACMiddleware:
    """
    Middleware for applying RBAC in API endpoints.
    """

    def __init__(self, enforcer: RBACEnforcer):
        """
        Initialize middleware.

        Args:
            enforcer: RBAC enforcer instance
        """
        self.enforcer = enforcer

    def extract_role_from_request(
        self,
        request_headers: dict[str, str],
        query_params: dict[str, Any] | None = None,
    ) -> str | None:
        """
        Extract user role from request.

        Args:
            request_headers: HTTP headers
            query_params: Query parameters

        Returns:
            User role or None
        """
        # Check query params first
        if query_params and "user_role" in query_params:
            return query_params.get("user_role")

        # Check headers
        if "x-user-role" in request_headers:
            return request_headers.get("x-user-role")

        # Check JWT token claims (if available in header)
        # This would require JWT parsing

        return None

    def apply_rbac_to_query(
        self,
        base_filter: dict[str, Any],
        role: str | None,
    ) -> dict[str, Any]:
        """
        Apply RBAC filters to a MongoDB query.

        Args:
            base_filter: Base query filter
            role: User role

        Returns:
            Updated filter with RBAC constraints
        """
        rbac_filter = self.enforcer.build_filter(role)

        if not rbac_filter:
            return base_filter

        # Merge filters
        return {
            "$and": [
                base_filter,
                rbac_filter,
            ]
        }


# Convenience functions for common RBAC operations
def create_rbac_enforcer(
    default_role: str = "user",
    role_permissions: dict[str, list[str]] | None = None,
    enabled: bool = True,
) -> RBACEnforcer:
    """
    Create an RBAC enforcer with common defaults.

    Args:
        default_role: Default role name
        role_permissions: Role to folders mapping
        enabled: Whether RBAC is enabled

    Returns:
        Configured RBACEnforcer
    """
    config = RBACConfig(
        default_role=default_role,
        role_permissions=role_permissions or {},
        enabled=enabled,
    )
    return RBACEnforcer(config)


def get_default_rbac_config() -> RBACConfig:
    """
    Get default RBAC configuration.

    Returns:
        Default RBACConfig
    """
    return RBACConfig(
        default_role="user",
        role_permissions={
            "admin": ["*"],
            "user": ["/public", "/shared"],
            "guest": ["/public"],
        },
        enabled=True,
    )

from __future__ import annotations


def parse_permission_codename(codename: str) -> tuple:
    """Parse a permission codename into action and model name."""
    action = codename.split("_")[0]  # 'add', 'change', 'delete', 'view'
    model_name = "_".join(codename.split("_")[1:])  # The rest is the model name
    return action, model_name


def convert_queryset_to_role_permissions(
    permissions_queryset,
) -> dict[str, dict[str, list[str]]]:
    """Convert a QuerySet of permissions into a role permissions dictionary format.

    Args:
        permissions_queryset: QuerySet of Permission objects

    Returns:
        Dict in format:
        {
            "model_name": ["view", "add", "change", "delete"]
        }

    """
    permissions_dict = {}

    for permission in permissions_queryset:
        # Get the model name from content_type
        model_name = permission.content_type.model.replace(" ", "_").lower()

        # Extract the action (view, add, change, delete)
        action = permission.codename.split("_")[0]

        # Initialize the model in the dict if it doesn't exist
        if model_name not in permissions_dict:
            permissions_dict[model_name] = []

        # Add the action to the model's permission list
        permissions_dict[model_name].append(action)

    # Sort permissions for consistency
    for model in permissions_dict:  # noqa: PLC0206
        permissions_dict[model] = sorted(set(permissions_dict[model]))

    return permissions_dict

from app.domain.value_objects.role import Role, ToolPremission


class ToolAuthorizationService:
    def is_allowed(self, user_role: str, permission: ToolPremission) -> bool:
        role = Role(user_role)
        return permission in ToolPremission.allowed_for_role(role)

    def required_permission_for_mcp_tool(self, tool_name: str) -> ToolPremission:
        mapping = {
            "employee_directory": ToolPremission.MCP_EMPLOYEE_DIRECTORY,
            "service_catalog": ToolPremission.MCP_SERVICE_CATALOG,
            "incident_records": ToolPremission.MCP_INCIDENT_RECORD,
        }
        return mapping.get(tool_name, ToolPremission.MCP_EMPLOYEE_DIRECTORY)

    def retrieval_metadata_filters(self, user_role: str) -> dict[str, str]:
        role = Role(user_role)
        if role == Role.VIEWER:
            return {"access_level": "public"}
        return {}

from enum import Enum

class Role(str, Enum):
    VIEWER = "viewer"
    ANALYST = "analyst"
    ADMINISTRATOR = "administrator"

    def can_access(self , required: "Role") -> bool:
        role_hierarchy = {
            Role.VIEWER: 1,
            Role.ANALYST: 2,
            Role.ADMINISTRATOR: 3,
        }
        return role_hierarchy[self] >= role_hierarchy[required]
class ToolPremission(str , Enum):
    KNOWLEDGE_SEARCH = "knowledge_search"
    PYTHON_ANALYSIS = "python_analysis"
    MCP_EMPLOYEE_DIRECTORY = "mcp_employee_search"
    MCP_SERVICE_CATALOG = "mcp_service_catalog"
    MCP_INCIDENT_RECORD = "mcp_incident_record"
    ADMIN_TOOLS = "admin_tools"

    @classmethod
    def allowed_for_role(cls, role: Role) -> list["ToolPremission"]:
        viewer = {cls.KNOWLEDGE_SEARCH}
        analyst = viewer | {
            cls.PYTHON_ANALYSIS,
            cls.MCP_EMPLOYEE_DIRECTORY,
            cls.MCP_SERVICE_CATALOG,
            cls.MCP_INCIDENT_RECORD,
        }
        admin = analyst | {cls.ADMIN_TOOLS}
        return { Role.VIEWER: viewer, Role.ANALYST: analyst, Role.ADMINISTRATOR: admin }[role]
    
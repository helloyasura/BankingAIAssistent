"""JSON-backed MCP-style tool registry for enterprise mock data."""

from __future__ import annotations

import json
import re
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent / "data"

_TOOL_NAMES = frozenset({"employee_directory", "service_catalog", "incident_records"})


def _load_json(filename: str) -> list[dict]:
    path = _DATA_DIR / filename
    return json.loads(path.read_text(encoding="utf-8"))


def _matches_text(value: str, needle: str) -> bool:
    return needle.lower() in value.lower()


def search_employees(
    *,
    name: str = "",
    department: str = "",
    role: str = "",
) -> list[dict]:
    employees = _load_json("employees.json")
    results = []
    for employee in employees:
        if name and not _matches_text(employee.get("name", ""), name):
            continue
        if department and not _matches_text(employee.get("department", ""), department):
            continue
        if role and not _matches_text(employee.get("role", ""), role):
            continue
        results.append(employee)
    return results


def search_service_catalog(
    *,
    query: str = "",
    team: str = "",
    status: str = "",
) -> list[dict]:
    services = _load_json("service_catalog.json")
    results = []
    for service in services:
        haystack = " ".join(
            str(service.get(key, ""))
            for key in ("name", "team", "owner", "description", "status")
        )
        if query and not _matches_text(haystack, query):
            continue
        if team and not _matches_text(service.get("team", ""), team):
            continue
        if status and not _matches_text(service.get("status", ""), status):
            continue
        results.append(service)
    return results


def search_incidents(
    *,
    incident_id: str = "",
    keyword: str = "",
    department: str = "",
) -> list[dict]:
    incidents = _load_json("incidents.json")
    results = []
    for incident in incidents:
        if incident_id:
            if incident.get("id", "").lower() != incident_id.lower():
                continue
        if keyword:
            haystack = " ".join(
                [
                    incident.get("title", ""),
                    incident.get("root_cause", ""),
                    " ".join(incident.get("keywords", [])),
                ]
            )
            if not _matches_text(haystack, keyword):
                continue
        if department and not _matches_text(incident.get("department", ""), department):
            continue
        results.append(incident)
    return results


def _extract_incident_id(message: str) -> str:
    match = re.search(r"INC-\d{4}-\d{4}", message, re.IGNORECASE)
    return match.group(0).upper() if match else ""


def _is_analytical_incident_query(message: str) -> bool:
    lowered = message.lower()
    return any(
        phrase in lowered
        for phrase in (
            "count",
            "summarize",
            "summary",
            "breakdown",
            "recurring",
            "statistics",
            "how many",
            "by root cause",
            "root causes",
        )
    )


def _extract_incident_keyword(message: str) -> str:
    lowered = message.lower()
    for term in ("payment", "payments", "fraud", "kafka", "notification", "ledger"):
        if term in lowered:
            return term
    return message


def infer_tool_from_message(message: str) -> tuple[str, dict]:
    lowered = message.lower()
    incident_id = _extract_incident_id(message)
    if (
        incident_id
        or "incident" in lowered
        or "outage" in lowered
        or lowered.startswith("inc-")
    ):
        args: dict = {}
        if incident_id:
            args["incident_id"] = incident_id
        elif _is_analytical_incident_query(message):
            if "payment" in lowered and "recurring" not in lowered:
                args["department"] = "payments"
        else:
            args["keyword"] = _extract_incident_keyword(message)
        return "incident_records", args
    if "service catalog" in lowered or "microservice" in lowered or "service" in lowered:
        return "service_catalog", {"query": message}
    if "on-call" in lowered or "on call" in lowered or "employee" in lowered or "who is" in lowered:
        args = {"role": "on-call"} if "on-call" in lowered or "on call" in lowered else {}
        if "department" in lowered or "payments" in lowered:
            args["department"] = "payments"
        if not args:
            args["query"] = message
        return "employee_directory", args
    return "employee_directory", {"name": message}


def call_tool(tool_name: str, arguments: dict | None = None) -> dict:
    if tool_name not in _TOOL_NAMES:
        return {"error": f"Unknown tool: {tool_name}", "results": []}

    arguments = arguments or {}
    if tool_name == "employee_directory":
        results = search_employees(
            name=arguments.get("name", arguments.get("query", "")),
            department=arguments.get("department", ""),
            role=arguments.get("role", ""),
        )
    elif tool_name == "service_catalog":
        results = search_service_catalog(
            query=arguments.get("query", ""),
            team=arguments.get("team", ""),
            status=arguments.get("status", ""),
        )
    else:
        results = search_incidents(
            incident_id=arguments.get("incident_id", ""),
            keyword=arguments.get("keyword", arguments.get("query", "")),
            department=arguments.get("department", ""),
        )

    return {"tool": tool_name, "count": len(results), "results": results}


def list_tools() -> list[dict]:
    return [
        {
            "name": "employee_directory",
            "description": "Search employees by department, role, or name",
        },
        {
            "name": "service_catalog",
            "description": "List or search microservices in the enterprise catalog",
        },
        {
            "name": "incident_records",
            "description": "Lookup incidents by INC- id or keyword",
        },
    ]

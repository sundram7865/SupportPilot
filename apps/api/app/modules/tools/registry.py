from dataclasses import dataclass

from app.common.enums import ToolName, ToolRiskLevel


@dataclass(frozen=True)
class ToolDefinition:
    name: ToolName
    risk_level: ToolRiskLevel
    requires_approval: bool
    description: str


TOOL_REGISTRY: dict[str, ToolDefinition] = {
    ToolName.URBANKART_GET_ORDER_CONTEXT.value: ToolDefinition(
        name=ToolName.URBANKART_GET_ORDER_CONTEXT,
        risk_level=ToolRiskLevel.READ_ONLY,
        requires_approval=False,
        description="Fetch order, payment, and shipment context from UrbanKart.",
    ),
    ToolName.URBANKART_REQUEST_REFUND.value: ToolDefinition(
        name=ToolName.URBANKART_REQUEST_REFUND,
        risk_level=ToolRiskLevel.HIGH_RISK_WRITE,
        requires_approval=True,
        description="Request refund in UrbanKart. Requires human approval.",
    ),
    ToolName.URBANKART_REQUEST_REPLACEMENT.value: ToolDefinition(
        name=ToolName.URBANKART_REQUEST_REPLACEMENT,
        risk_level=ToolRiskLevel.HIGH_RISK_WRITE,
        requires_approval=True,
        description="Request replacement in UrbanKart. Requires human approval.",
    ),
}


def get_tool_definition(tool_name: str) -> ToolDefinition:
    tool = TOOL_REGISTRY.get(tool_name)

    if not tool:
        raise ValueError(f"Unknown tool: {tool_name}")

    return tool
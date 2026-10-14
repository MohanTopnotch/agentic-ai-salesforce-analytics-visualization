"""FastMCP server for security-aware Salesforce analytics."""

from collections.abc import Callable

from mcp.server.fastmcp import FastMCP

from app.mcp.tools import SalesforceMCPToolProvider


def create_mcp_server(
    tool_provider: SalesforceMCPToolProvider,
    authenticate_user: Callable[[], str],
) -> FastMCP:
    """Create an MCP server using trusted application dependencies."""
    server = FastMCP("Salesforce Analytics")

    def current_user_id() -> str:
        # Identity must come from authenticated server context,
        # not from a caller-supplied tool argument.
        user_id = authenticate_user()
        if not isinstance(user_id, str) or not user_id.strip():
            raise PermissionError("Authenticated user is required.")
        return user_id

    @server.tool()
    def describe_object(object_name: str) -> dict:
        """Describe a Salesforce object accessible to the current user."""
        return tool_provider.describe_object(
            object_name=object_name,
            user_id=current_user_id(),
        )

    @server.tool()
    def execute_soql(soql: str) -> dict:
        """Validate permissions and execute a read-only SOQL query."""
        user_id = current_user_id()

        # The provider must obtain object and field permissions from
        # trusted server-side authorization, never from tool arguments.
        return tool_provider.execute_authorized_soql(
            soql=soql,
            user_id=user_id,
        )

    @server.tool()
    def search_metadata(query: str) -> list[str]:
        """Search Salesforce metadata visible to the current user."""
        return tool_provider.search_metadata(
            query=query,
            user_id=current_user_id(),
        )

    @server.tool()
    def get_data_lineage(request_id: str) -> dict:
        """Retrieve lineage for a stored analytics request."""
        return tool_provider.get_data_lineage(request_id)

    @server.tool()
    def get_audit_trail(audit_id: str) -> dict:
        """Retrieve an audit record by request ID."""
        return tool_provider.get_audit_trail(audit_id)

    return server

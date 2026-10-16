"""Salesforce REST client using the OAuth client-credentials flow."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import Request, urlopen

from app.salesforce.client import SalesforceClient


class SalesforceAPIError(RuntimeError):
    """A sanitized error returned by Salesforce or the network layer."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "SALESFORCE_API_ERROR",
        status_code: int | None = None,
    ) -> None:
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class SalesforceRESTClient(SalesforceClient):
    """Execute read-only Salesforce REST API operations as one service user."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        login_url: str = "https://login.salesforce.com",
        api_version: str = "v66.0",
        timeout: float = 20.0,
        max_records: int = 2000,
    ) -> None:
        if not client_id.strip() or not client_secret.strip():
            raise ValueError("Salesforce client ID and secret are required.")

        parsed_login_url = urlparse(login_url)
        if parsed_login_url.scheme != "https" or not parsed_login_url.netloc:
            raise ValueError("Salesforce login URL must use HTTPS.")

        if (
            not api_version.startswith("v")
            or not api_version[1:].replace(".", "").isdigit()
        ):
            raise ValueError("Salesforce API version must look like 'v66.0'.")

        if timeout <= 0 or max_records < 1:
            raise ValueError("Timeout and maximum records must be positive.")

        self.client_id = client_id
        self.client_secret = client_secret
        self.login_url = login_url.rstrip("/")
        self.api_version = api_version
        self.timeout = timeout
        self.max_records = max_records
        self._access_token: str | None = None
        self._instance_url: str | None = None

    def get_accessible_objects(self, user_id: str | None = None) -> list[str]:
        """Return queryable objects visible to the configured Salesforce user."""
        del user_id  # Access is determined by the single OAuth service identity.
        payload = self._request_json(f"/services/data/{self.api_version}/sobjects")
        objects = payload.get("sobjects")
        if not isinstance(objects, list):
            raise SalesforceAPIError("Salesforce returned invalid object metadata.")

        return sorted(
            item["name"]
            for item in objects
            if isinstance(item, dict)
            and item.get("queryable") is True
            and isinstance(item.get("name"), str)
        )

    def describe_object(self, object_name: str) -> dict[str, Any]:
        """Return Salesforce describe metadata for one object."""
        if not object_name or not object_name.replace("_", "").isalnum():
            raise ValueError("Invalid Salesforce object name.")

        payload = self._request_json(
            f"/services/data/{self.api_version}/sobjects/{object_name}/describe"
        )
        fields = payload.get("fields")
        if not isinstance(fields, list):
            raise SalesforceAPIError("Salesforce returned invalid field metadata.")

        field_names = [
            item["name"]
            for item in fields
            if isinstance(item, dict) and isinstance(item.get("name"), str)
        ]
        return {
            "name": payload.get("name", object_name),
            "fields": fields,
            "field_names": field_names,
        }

    def query(self, soql: str) -> dict[str, Any]:
        """Execute a SOQL query and collect its result pages."""
        if not isinstance(soql, str) or not soql.strip():
            raise ValueError("SOQL query must not be empty.")

        path = f"/services/data/{self.api_version}/query?{urlencode({'q': soql})}"
        records: list[dict[str, Any]] = []
        total_size = 0

        while path:
            payload = self._request_json(path)
            page_records = payload.get("records")
            if not isinstance(page_records, list) or any(
                not isinstance(record, dict) for record in page_records
            ):
                raise SalesforceAPIError("Salesforce returned invalid query records.")

            records.extend(
                {key: value for key, value in record.items() if key != "attributes"}
                for record in page_records
            )
            if len(records) > self.max_records:
                raise SalesforceAPIError(
                    "Salesforce query exceeded the configured record limit.",
                    code="QUERY_RECORD_LIMIT_EXCEEDED",
                )

            total_size = payload.get("totalSize", total_size)
            next_records_url = payload.get("nextRecordsUrl")
            if payload.get("done") is True:
                path = ""
            elif isinstance(next_records_url, str):
                parsed_next_url = urlparse(next_records_url)
                expected_prefix = f"/services/data/{self.api_version}/query/"
                if (
                    parsed_next_url.scheme
                    or parsed_next_url.netloc
                    or not parsed_next_url.path.startswith(expected_prefix)
                ):
                    raise SalesforceAPIError(
                        "Salesforce returned an invalid query pagination URL."
                    )
                path = next_records_url
            else:
                raise SalesforceAPIError(
                    "Salesforce returned an incomplete query page."
                )

        return {"totalSize": total_size, "records": records}

    def _get_token(self) -> tuple[str, str]:
        body = urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        ).encode("utf-8")
        request = Request(
            f"{self.login_url}/services/oauth2/token",
            data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        payload = self._open_json(request)
        access_token = payload.get("access_token")
        instance_url = payload.get("instance_url")
        if not isinstance(instance_url, str):
            raise SalesforceAPIError(
                "Salesforce OAuth returned an invalid token response.",
                code="INVALID_OAUTH_RESPONSE",
            )
        parsed_instance_url = urlparse(instance_url or "")

        if (
            not isinstance(access_token, str)
            or not access_token
            or parsed_instance_url.scheme != "https"
            or not parsed_instance_url.netloc
        ):
            raise SalesforceAPIError(
                "Salesforce OAuth returned an invalid token response.",
                code="INVALID_OAUTH_RESPONSE",
            )

        return access_token, instance_url.rstrip("/")

    def _request_json(self, path: str, *, retry_auth: bool = True) -> dict[str, Any]:
        if self._access_token is None or self._instance_url is None:
            self._access_token, self._instance_url = self._get_token()

        if path.startswith(("http", "//")):
            raise SalesforceAPIError("Salesforce API path must be relative.")

        request = Request(
            urljoin(f"{self._instance_url}/", path.lstrip("/")),
            headers={
                "Authorization": f"Bearer {self._access_token}",
                "Accept": "application/json",
            },
            method="GET",
        )
        try:
            return self._open_json(request)
        except SalesforceAPIError as exc:
            if exc.status_code == 401 and retry_auth:
                self._access_token = None
                self._instance_url = None
                return self._request_json(path, retry_auth=False)
            raise

    def _open_json(self, request: Request) -> dict[str, Any]:
        """Open an allowlisted HTTPS Salesforce URL and parse its JSON response."""
        parsed_url = urlparse(request.full_url)
        allowed_hosts = {urlparse(self.login_url).hostname}
        if self._instance_url:
            allowed_hosts.add(urlparse(self._instance_url).hostname)

        if (
            parsed_url.scheme != "https"
            or not parsed_url.hostname
            or parsed_url.hostname not in allowed_hosts
            or parsed_url.username is not None
            or parsed_url.password is not None
        ):
            raise SalesforceAPIError(
                "Salesforce request URL is not permitted.",
                code="INVALID_REQUEST_URL",
            )

        try:
            # B310 is suppressed only after explicit HTTPS and host allowlisting.
            with urlopen(request, timeout=self.timeout) as response:  # nosec B310
                payload = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            error_code = "SALESFORCE_HTTP_ERROR"
            try:
                error_payload = json.loads(exc.read().decode("utf-8"))
                if isinstance(error_payload, list) and error_payload:
                    error_code = str(error_payload[0].get("errorCode", error_code))
                elif isinstance(error_payload, dict):
                    error_code = str(error_payload.get("error", error_code))
            except (UnicodeDecodeError, json.JSONDecodeError, AttributeError):
                pass
            raise SalesforceAPIError(
                "Salesforce rejected the API request.",
                code=error_code,
                status_code=exc.code,
            ) from exc
        except (TimeoutError, URLError, OSError) as exc:
            raise SalesforceAPIError(
                "Salesforce could not be reached.",
                code="SALESFORCE_CONNECTION_ERROR",
            ) from exc
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SalesforceAPIError(
                "Salesforce returned an invalid JSON response.",
                code="INVALID_SALESFORCE_RESPONSE",
            ) from exc

        if not isinstance(payload, dict):
            raise SalesforceAPIError("Salesforce returned an invalid JSON response.")
        return payload

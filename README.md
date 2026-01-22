
# RK-digitalisering-package
Python package with useful stuff for projects in Randers kommune digitalisering

## Classes

### ManagedOAuth2Session (sync)
A drop-in replacement for `requests.Session`/`OAuth2Session` that handles OAuth2 token acquisition and refresh for both client credentials and refresh token flows.

**Example:**
```python
from rkdigi.syncpkg import ManagedOAuth2Session

session = ManagedOAuth2Session(
	token_url="https://example.com/oauth/token",
	client_id="your-client-id",
	client_secret="your-client-secret"
)
res = session.get("https://example.com/api/data")
print(res.json())
```

### ManagedAsyncOAuth2Client (async)
An async OAuth2 client (subclass of `authlib.integrations.httpx_client.AsyncOAuth2Client`) with token refresh and concurrency control.

**Example:**
```python
import asyncio
from rkdigi.asyncpkg import ManagedAsyncOAuth2Client

async def main():
	client = ManagedAsyncOAuth2Client(
		token_url="https://example.com/oauth/token",
		client_id="your-client-id",
		client_secret="your-client-secret"
	)
	res = await client.get("https://example.com/api/data")
	print(res.json())

asyncio.run(main())
```

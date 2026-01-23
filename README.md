
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

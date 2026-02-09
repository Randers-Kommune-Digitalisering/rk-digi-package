
[![PyPI version](https://img.shields.io/pypi/v/rk-digi.svg)](https://pypi.org/project/rk-digi/) [![codecov](https://codecov.io/gh/Randers-Kommune-Digitalisering/rk-digi-package/branch/main/graph/badge.svg)](https://codecov.io/gh/Randers-Kommune-Digitalisering/rk-digi-package)
# RK-digitalisering-package
Python package with useful stuff for projects in Randers Kommune - Digitalisering.
## Classes

### ManagedOAuth2Session (sync)
A drop-in replacement for `requests.Session`/`OAuth2Session` that handles OAuth2 token acquisition and refresh for both client credentials and refresh token flows.

#### Example
```python
from rkdigi import ManagedOAuth2Session

session = ManagedOAuth2Session(
	token_url="https://example.com/oauth/token",
	client_id="your-client-id",
	client_secret="your-client-secret"
)
res = session.get("https://example.com/api/data")
```

### DatabaseManager (sync + async)
`DatabaseManager` is for database connections and session management for both Microsoft SQL Server and PostgreSQL databases. It supports both synchronous and asynchronous usage.

- **Connection Profiles:** You can create multiple `DatabaseManager` instances, each identified by a unique `profile_name`. If a new object is created with the same `profile_name`, the previously create object will be returned.
- **Credential Handling:** Credentials and connection details can be provided directly to the constructor, or (if omitted) loaded automatically from environment variables based on the `profile_name`. For example, if `profile_name` is `mydb`, the class will look for environment variables like `MYDB_HOST`, `MYDB_PORT`, `MYDB_USER`, and `MYDB_PASSWORD`.
- **Sync and Async Support:** By default, the class operates in synchronous mode. To use asynchronous mode, set `async_mode=True` when creating the instance. The class will then use SQLAlchemy's async engine and session management.
- **Session Management:**
	- In sync mode, use `get_session()` as a context manager to obtain a SQLAlchemy session.
	- In async mode, use `get_session_async()` as an async context manager to obtain an async session.
- **Resource Cleanup:**
	- In sync mode, call `dispose()` to close the engine and clean up resources.
	- In async mode, call `await dispose_async()` to clean up async resources.
- **Dependencies:**
	- apache-airflow-providers-postgres (for Airflow Postgres connections)
	- apache-airflow-providers-microsoft-mssql (for Airflow MSSQL connections)
	- psycopg2 (for PostgreSQL, sync)
	- asyncpg (for PostgreSQL, async)
	- pymssql (for Microsoft SQL Server, sync)
	- aioodbc (for Microsoft SQL Server, async)
	- pyodbc (required by aioodbc for async SQL Server)

#### Sync example
Basic sync example supplying credentials in constructor. DatabaseManager default to sync.
```python
from sqlalchemy import text
from rkdigi import DatabaseManager

db_manager = DatabaseManager(
	profile_name='db_mydb',
	db_type='mssql',
	username='username',
	password='password',
	database="mydatabase",
	host='demo.com',
	port=1433,
)
with db_manager.get_session() as session:
	res = session.execute(text("SELECT 1"))
db_manager.dispose()
```
#### Async example
Basic async example getting credentials from environment variables. If no credentials are given then DatabaseManager will try to get them based on `profile_name`. In this example: `DB_MYDB_HOST`, `DB_MYDB_PORT`, etc. are used.
```python
import asyncio
from sqlalchemy import text
from rkdigi import DatabaseManager

async def my_db_func():
	db_manager = DatabaseManager(
		profile_name='db_mydb',
		db_type='postgres',
		async_mode=True
	)
	async with db_manager.get_session_async() as session:
		res = await session.execute(text("SELECT 1"))
	await db_manager.dispose_async()
asyncio.run(my_db_func())
```

#### Airflow example
Sync example using an airflow connection.
```python
from sqlalchemy import text
from rkdigi import DatabaseManager

db_manager = DatabaseManager(
	profile_name='db_mydb',
	db_type='postgres',
	airflow_connection_id='mydb_id'
)
with db_manager.get_session() as session:
	res = session.execute(text("SELECT 1"))
db_manager.dispose()
```
#### Create tables example
If DatabaseManager init is provided with a base model, it will create the tables in the database after testing it can connect.
```python
from rkdigi import DatabaseManager
from mymodel import MyBaseModel

db_manager = DatabaseManager(
	profile_name='db_mydb',
	db_type='postgres',
	base_model=MyBaseModel
)
```
#### Singleton explanation
DatabaseManager implements singleton behavior based on `profile_name`
```python
from rkdigi import DatabaseManager

db_manager = DatabaseManager(
	profile_name='db_mydb',  # same profile_name
	db_type='postgres',
	username='username',
	password='password',
	host='demo123.com'
)

db_manager = DatabaseManager(
	profile_name='db_mydb',  # same profile_name
	db_type='mssql',
	username='user',
	password='pass',
	host='demoABC.com'
)
# db_manager will still have an engine for the postgres database on demo123.com
db_manager.dispose()  # Only after calling dispose will it be re-initialized
db_manager = DatabaseManager(
	profile_name='db_mydb',  # same profile_name
	db_type='mssql',
	username='user',
	password='pass',
	host='demoABC.com'
)
# Now the new credentials are applied and a new engine created
```
### EmailSender (sync + async)
`EmailSender` is for sending emails from a SMTP server.
#### Sync example
```python
from rkdigi import EmailSender

email_sender = EmailSender(smtp_server='smtp.example.com', smtp_port=25)
email_sender.send_email(
	sender='from@example.com',
	recipients='to@example.com',
	subject='Test Subject',
	body='Test Body'
)
```
#### Sync example
```python
import asyncio
from rkdigi import EmailSender

async def send_email_func():
    email_sender = EmailSender()
    await email_sender.send_email_async(
        sender='from@example.com',
        recipients=['one@example.com', 'two@example.com'],
        subject='Test Subject',
        body='Test Body'
    )

asyncio.run(send_email_func())
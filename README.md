# Activity1_BI — AdventureWorksDW CSV Extraction

This repository contains a small set of tooling for a local **Business Intelligence / Data Analytics**
preparation pipeline. The overall goal is:

> **Restore the `AdventureWorksDW.bak` backup file into a local SQL Server instance running in Docker,
> then extract every table to CSV so the data can be used downstream in data analytics.**

The `.bak` file is taken from Microsoft's **AdventureWorksDW** sample database, which is the data-warehouse
(DW) version of the Adventure Works sample. It models a fictional bicycle manufacturer and is a classic
starting point for BI demos (dimensions such as `DimCustomer`, `DimProduct`, `DimDate`, and facts such as
`FactInternetSales`, `FactResellerSales`, etc.).

---

## Repository contents (tracked on GitHub)

Only three files are tracked in version control:

| File                   | Purpose                                                                                          |
| ---------------------- | ------------------------------------------------------------------------------------------------ |
| `main.py`              | Sample template that connects to the database and pulls a single table (`FactInternetSales`) into a pandas `DataFrame`. Good reference for how to talk to SQL Server from Python. |
| `scripts/export_to_csv.py` (`extract_tables_to_csv.py`) | Connects to the database via `pymssql` and exports **every base table** into its own CSV file under `data/raw/`. |
| `scripts/env.example`  | Example environment variables used by `export_to_csv.py` (DB connection settings).                |


---

## How the pieces fit together

```
backup/AdventureWorksDW2025.bak        <- downloaded Microsoft sample backup (NOT committed)
      │
      │  restored into local SQL Server running in Docker
      ▼
SQL Server (AdventureWorksDW2025)      <- contains dbo.* tables
      │
      │  scripts/export_to_csv.py (+ pymssql, pandas)
      ▼
data/raw/*.csv                         <- one CSV per table (NOT committed)
      │
      │  fed into notebooks / analytics
      ▼
Notebooks & further analysis           <- e.g. notebooks/test.ipynb
```

The pipeline has three distinct phases:

1. **Run SQL Server in Docker** — spin up a local SQL Server container.
2. **Restore the database** — restore `AdventureWorksDW.bak` into that server.
3. **Export to CSV** — use `scripts/export_to_csv.py` to dump every table to a CSV file, ready for
   analysis (e.g. with pandas / Jupyter notebooks).

---

## 0. Prerequisites

- [Docker](https://docs.docker.com/get-docker/) (Docker Desktop on Windows/macOS, or `docker` + `docker compose`
  on Linux).
- Python 3.8+ and `pip`.
- [`sqlcmd`](https://learn.microsoft.com/en-us/sql/linux/sql-server-linux-setup-tools) or the ability to run
  SQL inside the container (see the restore step below).
- The `AdventureWorksDW2025.bak` file placed in a `backup/` folder (only needed during the restore step).

---

## 1. Run SQL Server in Docker

Pull and start a Microsoft SQL Server 2022 container (or your preferred edition), expose port `1433`, and
set a strong `sa` password:

```bash
# PowerShell
docker pull mcr.microsoft.com/mssql/server:2022-latest

docker run -e "ACCEPT_EULA=Y" `
           -e "MSSQL_SA_PASSWORD=YourStr0ngPass!" `
           -p 1433:1433 `
           --name sqlserver-aw `
           -d mcr.microsoft.com/mssql/server:2022-latest
```

```bash
# macOS / Linux
docker pull mcr.microsoft.com/mssql/server:2022-latest

docker run -e "ACCEPT_EULA=Y" \
           -e "MSSQL_SA_PASSWORD=YourStr0ngPass!" \
           -p 1433:1433 \
           --name sqlserver-aw \
           -d mcr.microsoft.com/mssql/server:2022-latest
```

> The `sa` password set here (`MSSQL_SA_PASSWORD`) **must match** the `DB_PASSWORD` value you place in
> `scripts/.env` later, since the export script connects as `sa`.

Check that the container started and SQL Server is accepting connections:

```bash
docker ps
```

---

## 2. Restore the AdventureWorksDW database

Copy the `.bak` file into the container, then restore it. The following assumes the backup is named
`AdventureWorksDW2025.bak` and lives in a `backup/` folder on your host.

### 2a. Copy the .bak into the container

```bash
# PowerShell
docker cp backup/AdventureWorksDW2025.bak sqlserver-aw:/var/opt/mssql/AdventureWorksDW2025.bak

# macOS / Linux
docker cp backup/AdventureWorksDW2025.bak sqlserver-aw:/var/opt/mssql/AdventureWorksDW2025.bak
```

### 2b. Run the restore with `sqlcmd`

Either run `sqlcmd` from your host (if you installed the SQL tools) or execute it inside the container:

```bash
# macOS / Linux / PowerShell (executing inside the container)
docker exec -it sqlserver-aw /opt/mssql-tools18/bin/sqlcmd `
    -S localhost -U sa -P "YourStr0ngPass!" -C `
    -Q "RESTORE DATABASE [AdventureWorksDW2025] FROM DISK = N'/var/opt/mssql/AdventureWorksDW2025.bak' WITH REPLACE, RECOVERY;"
```

> `-C` is required for the mssql-tools18 client to trust the self-signed certificate used by default in
> modern SQL Server containers. If you use `mssql-tools` (v17), you can drop the `-C`.

### 2c. Verify the restore

List the restored database and its tables:

```bash
docker exec -it sqlserver-aw /opt/mssql-tools18/bin/sqlcmd `
    -S localhost -U sa -P "YourStr0ngPass!" -C -d AdventureWorksDW2025 `
    -Q "SELECT TABLE_SCHEMA, TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_TYPE='BASE TABLE' ORDER BY TABLE_NAME;"
```

---

## 3. Export every table to CSV

Now that SQL Server is up and the database is restored, dump each table to its own CSV.

### 3a. Install Python dependencies

```bash
pip install pymssql pandas python-dotenv
```

(`main.py` additionally imports `numpy`, `seaborn`, and `matplotlib` if you plan to run it.)

### 3b. Configure the connection

Copy the example environment file to `scripts/.env` and fill in the details so they match your container
(`sa`, the password set in step 1, and the database name that was restored):

```bash
# PowerShell
Copy-Item scripts/env.example scripts/.env

# macOS / Linux
cp scripts/env.example scripts/.env
```

`scripts/.env`:

```
DB_SERVER=127.0.0.1
DB_PORT=1433
DB_USER=sa
DB_PASSWORD=YourStr0ngPass!
DB_NAME=AdventureWorksDW2025
```

### 3c. Run the export script

```bash
cd scripts
python export_to_csv.py
```

The script connects to the database, discovers every `dbo` base table, and writes one file per table as
`<TableName>.csv` into `data/raw/`. For example:

```
Exporting dbo.DimCustomer ...
  -> data/raw/DimCustomer.csv (18,484 rows, 13 columns)
Exporting dbo.DimProduct ...
  -> data/raw/DimProduct.csv (1,617 rows, 23 columns)
Exporting dbo.FactInternetSales ...
  -> data/raw/FactInternetSales.csv (60,398 rows, 26 columns)
```

Which tables are exported is controlled by the `SCHEMAS_TO_INCLUDE` list near the top of the file (default
`["dbo"]`), and the output location by the `OUTPUT_DIR` variable (default `"data/raw"`).

The generated CSVs are now ready to load into a pandas `DataFrame`, a Jupyter notebook, a dash app, etc.

---

## Using `main.py` (connection template)

`main.py` is a minimal reference showing how to connect to the SQL Server instance and pull a full table
into a pandas `DataFrame`:

```python
import pymssql
import pandas as pd

conn = pymssql.connect(
    server='localhost', port=1433,
    user='sa', password='',        # <-- the MSSQL_SA_PASSWORD
    database='AdventureWorksDW2025'
)

df = pd.read_sql("SELECT * FROM dbo.FactInternetSales", conn)
print(df.shape)
print(df.head(5))
conn.close()
```

> Note the `password=` here is deliberately blank in the sample — you must supply the real password. It is
> good practice to read it from an environment variable instead of hard-coding it.

---

## Project structure

```
.
├── main.py                       # Sample SQL Server connection template (pandas query)
├── scripts/
│   ├── export_to_csv.py          # Exports every dbo table to CSV (pymssql + pandas)
│   ├── .env                      # Local DB credentials (NOT committed — secrets)
│   └── env.example               # Template for .env (committed)
├── backup/
│   └── AdventureWorksDW2025.bak  # Local MSSQL backup (NOT committed)
├── data/
│   └── raw/*.csv                 # Generated CSV exports (NOT committed)
└── notebooks/                    # Analysis notebooks (e.g. test.ipynb)
```

---

## Security notes

- `scripts/.env` contains the real `sa` password. It is a **secret** and should not be committed. Always
  commit only `scripts/env.example` (with a placeholder password).
- `backup/` and `data/raw/` contain large binary/generated files that should not go into Git.

A sensible `.gitignore` is recommended, e.g.:

```gitignore
.env
scripts/.env
backup/
data/raw/
__pycache__/
*.pyc
.venv/
```

*(Currently `backup/`, `data/`, `scripts/.env`, and `notebooks/` exist locally but are untracked — treat them
as disposable/local artifacts.)*

---

## Cleaning up generated artifacts

To stop and remove the SQL Server container when you are done:

```bash
docker stop sqlserver-aw
docker rm sqlserver-aw
```

If you want to regenerate the CSVs from scratch (e.g. after changing logic), delete `data/raw/*.csv` and
re-run the export script.

---

## Tech stack

- **Docker** — hosts a lightweight local SQL Server instance.
- **Microsoft SQL Server 2022** — the database engine where `AdventureWorksDW2025` is restored.
- **pymssql** — Python driver that connects to SQL Server.
- **pandas** — reads SQL results into `DataFrame` objects and writes CSVs.
- **python-dotenv** — loads DB credentials from `scripts/.env`.

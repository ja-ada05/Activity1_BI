import pymssql
import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt

# Connection details
conn = pymssql.connect(
    server='localhost',
    port=1433,
    user='sa',
    password='',   # the MSSQL_SA_PASSWORD 
    database='AdventureWorksDW2025'
)

# Pull an entire table into a DataFrame, example 
query = "SELECT * FROM dbo.FactInternetSales"
df = pd.read_sql(query, conn)

print(df.shape)
print(df.head(5))

conn.close()
print("success")
# MySQL database

| File | What it does |
|---|---|
| [`schema.sql`](schema.sql) | Creates the `traffic` database, the 3 tables, constraints, indexes and the `v_readings` view. |
| [`load_mysql.py`](load_mysql.py) | Runs `schema.sql`, cleans the CSV (`common/dataset.py`) and bulk-loads it. |
| [`queries.sql`](queries.sql) | The 6 Task 2 queries. |
| [`run_queries.py`](run_queries.py) | Runs every query in `queries.sql` and writes [`query_results.md`](query_results.md). |

The table design and ERD are in [`../ERD`](../ERD/README.md).

## Run it

From the repo root, with MySQL 8 running and `.env` filled in (see `.env.example`):

```bash
python -m SQL.load_mysql --reset
python -m SQL.run_queries
```

Expected load output: `holidays 11`, `weather_conditions 37`, `traffic_readings 48187` rows.

## Queries

| # | Question | SQL features |
|---|---|---|
| Q1 | What is the latest record? | 3-table join, `ORDER BY ... DESC LIMIT 1` |
| Q2 | What was 7am traffic between 24 and 28 Sep 2018? | Date-range filter (`BETWEEN`), `HOUR()` |
| Q3 | What is the average traffic for each hour of the day? | CTE, `GROUP BY HOUR()` |
| Q4 | How do readings and traffic differ by weather category? | Join + aggregate |
| Q5 | Do holidays have less traffic than ordinary days? | Two CTEs, daily roll-up, `LEFT JOIN` |
| Q6 | What are the lag-1h, lag-24h and 24-hour moving-average values? | Window functions `LAG()`, `AVG() OVER (ROWS ...)` |

Q6 builds the same lag and moving-average features as the Task 1 notebook, inside the database. Because the series has gaps, `LAG(..., 24)` means "24 recorded hours earlier", which is usually, but not always, exactly one day earlier.

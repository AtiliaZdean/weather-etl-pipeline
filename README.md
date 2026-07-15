# Weather ETL Pipeline

A scheduled ETL pipeline that extracts weather data for four Malaysian cities
(Seremban, Kuala Lumpur, Penang, Johor Bahru) from the Open-Meteo API,
transforms and validates it, and loads it into PostgreSQL for trend analysis.

## Status
🚧 In progress

## Architecture
_(diagram coming once the pipeline is built)_

## Tech Stack
- Python 3.14
- PostgreSQL 18 (local dev) / Neon (production, scheduled runs)
- GitHub Actions (scheduling via cron)
- Open-Meteo API (no key required)

## Setup
_(instructions coming as the project develops)_
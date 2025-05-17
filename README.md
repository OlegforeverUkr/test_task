# Name Nationality Prediction API

A service API for predicting nationality by name and getting statistics of popular names by country.

## Technologies

- Python 3.11+
- Django 5.2+
- Django REST Framework
- SQLite (database)
- Pre-commit hooks

## Installation

1. Clone the repository
2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # for Linux/Mac
.venv\Scripts\activate     # for Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Install pre-commit hooks:
```bash
pre-commit install
```

5. Apply migrations:
```bash
python manage.py migrate
```

6. Run the server:
```bash
python manage.py runserver
```

## Pre-commit hooks

The project has the following pre-commit hooks configured:

- **black**: code formatting
- **isort**: import sorting
- **flake8**: code style checking
- Basic checks (trailing-whitespace, end-of-file-fixer, etc.)

Hooks run automatically on commit. To run them manually:
```bash
pre-commit run --all-files
```

## API Documentation

The API documentation is available at the following URLs:

- Swagger UI: `/api/schema/swagger-ui/`
- ReDoc: `/api/schema/redoc/`
- OpenAPI Schema: `/api/schema/`

## API Endpoints

### 1. Name Nationality Prediction

```
GET /api/names/?name=John
```

Returns information about the most probable countries for a given name.

- If the name exists in the database and was requested no more than 24 hours ago, returns cached data
- If the name is missing or the data is outdated, fetches new data from Nationalize.io and REST Countries API

### 2. Popular Names by Country

```
GET /api/popular-names/?country=US
```

Returns the top 5 most frequently requested names for the specified country.

## 🛠 Improvements and Technical Solutions

1. **Data Caching**:
   - Implemented caching of API request results in the database
   - Data is considered valid for 24 hours
   - This reduces the number of requests to external APIs and improves performance

2. **Query Optimization**:
   - Using `select_related` to optimize SQL queries
   - Field indexing for fast search

3. **Error Handling**:
   - Detailed error handling and clear messages
   - Input parameter validation

4. **Scalability**:
   - Modular code structure
   - Easy addition of new endpoints
   - Preparation for possible database migration

5. **Code Quality**:
   - Automatic formatting (black)
   - Code style checking (flake8)
   - Import sorting (isort)
   - Pre-commit hooks for quality control

## Possible Improvements

1. Adding caching at Redis/Memcached level
2. Implementing rate limiting for API endpoints
3. Adding authentication and authorization
4. Adding API documentation (via Swagger/OpenAPI)
5. Implementing asynchronous processing of requests to external APIs

# Configuration Merger Service

A production-ready FastAPI service that merges five configuration layers:
1. Hardcoded Defaults
2. Environment-specific YAML (`config.development.yaml`)
3. `.env` file
4. OS Environment Variables
5. CLI Overrides from Query Parameters (highest precedence)

---

## Project Structure

```text
.
├── main.py                    # Core FastAPI application & config loading functions
├── config.development.yaml    # Environment-specific YAML layer
├── .env                       # Dotenv file for environmental configuration
├── requirements.txt           # Project dependencies
├── render.yaml                # Render Blueprint deployment config
├── .gitignore                 # Files and folders to ignore in Git
└── README.md                  # Project documentation (this file)
```

---

## Configuration Precedence

Configurations are merged in the following order (lowest to highest precedence):

1. **Hardcoded Defaults**
   - `port`: `8000`
   - `workers`: `1`
   - `debug`: `false`
   - `log_level`: `info`
   - `api_key`: `default-secret-000`
2. **YAML (`config.development.yaml`)**
3. **Dotenv (`.env`)** (Supports mapping `NUM_WORKERS` to `workers`)
4. **OS Environment Variables** (Supports standard `APP_PORT`, `APP_WORKERS`, `APP_DEBUG`, `APP_LOG_LEVEL`, `APP_API_KEY`)
5. **CLI Overrides** (Repeated `set` query parameters, e.g. `?set=port=9000&set=debug=true`)

---

## Installation

Ensure you have Python 3.8+ installed. Clone the repository and install the dependencies:

```bash
pip install -r requirements.txt
```

---

## Running Locally

To run the application locally on your machine:

```bash
uvicorn main:app --reload
```

By default, the server will start on [http://127.0.0.1:8000](http://127.0.0.1:8000).

---

## Example API Calls

The only exposed endpoint is `GET /effective-config`. It always returns the configuration with `api_key` masked as `****`.

### 1. No CLI Overrides
```bash
curl http://127.0.0.1:8000/effective-config
```
**Response:**
```json
{
  "port": 8425,
  "workers": 5,
  "debug": false,
  "log_level": "warning",
  "api_key": "****"
}
```

### 2. Overriding Port and Debug
```bash
curl "http://127.0.0.1:8000/effective-config?set=port=9999&set=debug=true"
```
**Response:**
```json
{
  "port": 9999,
  "workers": 5,
  "debug": true,
  "log_level": "warning",
  "api_key": "****"
}
```

### 3. Invalid Integer Value
If an invalid value is supplied for integer-only keys (like `port` or `workers`), it is silently ignored:
```bash
curl "http://127.0.0.1:8000/effective-config?set=port=invalid_port_number"
```
**Response:**
```json
{
  "port": 8425,
  "workers": 5,
  "debug": false,
  "log_level": "warning",
  "api_key": "****"
}
```

---

## Deployment Instructions for Render

This project includes a `render.yaml` template for quick deployment to **Render**.

1. Connect your GitHub repository containing this code to Render.
2. In the Render Dashboard, select **Blueprints** -> **New Blueprint Instance**.
3. Choose the repository and deploy.
4. Render will automatically read `render.yaml` to build and launch the service:
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`

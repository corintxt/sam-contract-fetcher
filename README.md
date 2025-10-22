# Contract Fetcher Cloud Run

This project is designed to fetch contracts from the SAM API daily at 6 AM and save the data in a format suitable for integration into a unified database. It utilizes Google Cloud Run for deployment and Google Cloud Storage for data storage.

## Project Structure

```
contract-fetcher-cloud-run
├── src
│   ├── main.py                # Entry point of the Cloud Run application
│   ├── fetcher
│   │   ├── __init__.py        # Package initialization
│   │   ├── contract_fetcher.py # Contains the function to fetch contracts from SAM API
│   │   └── data_processor.py   # Processes fetched contract data
│   ├── storage
│   │   ├── __init__.py        # Package initialization
│   │   └── gcs_handler.py      # Handles Google Cloud Storage operations
│   └── utils
│       ├── __init__.py        # Package initialization
│       └── logger.py           # Logging utilities
├── terraform
│   ├── main.tf                # Main Terraform configuration
│   ├── variables.tf           # Variables for Terraform configuration
│   ├── outputs.tf             # Outputs of the Terraform configuration
│   └── cloud_run.tf           # Cloud Run specific configurations
├── config
│   └── app_config.yaml        # Application configuration settings
├── .env.example                # Example environment variables
├── requirements.txt           # Python dependencies
├── Dockerfile                  # Instructions for building the Docker image
├── cloudbuild.yaml             # Configuration for Google Cloud Build
├── .dockerignore               # Files to ignore when building the Docker image
├── .gitignore                  # Files to ignore in version control
└── README.md                   # Project documentation
```

## Setup Instructions

1. **Clone the repository:**
   ```
   git clone <repository-url>
   cd contract-fetcher-cloud-run
   ```

2. **Create a virtual environment and install dependencies:**
   ```
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables:**
   - Copy `.env.example` to `.env` and fill in the required values, including your SAM API key and Google Cloud Storage bucket name.

4. **Deploying to Google Cloud Run:**
   - Ensure you have the Google Cloud SDK installed and authenticated.
   - Use Terraform to deploy the Cloud Run service:
     ```
     cd terraform
     terraform init
     terraform apply
     ```

## Usage

- The application will automatically fetch contracts from the SAM API every day at 6 AM. The fetched data will be processed and uploaded to the specified Google Cloud Storage bucket.

## Logging

- The application includes logging utilities to track the execution and any issues that may arise during the fetching and processing of contracts.
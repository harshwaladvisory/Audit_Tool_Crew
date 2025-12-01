# Charity Registration Status Checker

## Overview

This is a Flask-based web application that checks charity registration statuses by scraping the California Department of Justice (DOJ) website. Users can upload Excel files containing EIN numbers, and the application will process each EIN to determine its charity registration status, then provide a downloadable report.

## System Architecture

### Frontend Architecture
- **Technology**: HTML templates with Bootstrap 5 (dark theme)
- **Styling**: Bootstrap CSS with custom CSS overrides
- **JavaScript**: Vanilla JavaScript for form handling and progress tracking
- **User Interface**: Single-page application with progress tracking and file upload/download functionality

### Backend Architecture
- **Framework**: Flask (Python web framework)
- **Application Structure**: 
  - `main.py`: Entry point
  - `app.py`: Main Flask application with routes
  - `scraper.py`: Web scraping functionality using Selenium
- **Session Management**: Flask sessions for tracking processing status
- **File Handling**: Werkzeug for secure file uploads

### Web Scraping Engine
- **Tool**: Selenium WebDriver with Chrome (headless mode)
- **Target**: California DOJ charity registration database
- **Features**: Automated browser interaction, timeout handling, error recovery

## Key Components

### 1. File Processing System
- **Upload Handler**: Validates Excel files and extracts EIN numbers
- **Excel Processing**: Uses openpyxl to read .xlsx files and validate EIN Number column
- **File Storage**: Temporary storage in uploads/ and downloads/ directories

### 2. Web Scraping Module (scraper.py)
- **CharityStatusScraper Class**: Handles all scraping operations
- **Chrome WebDriver**: Configured with headless mode and optimization flags
- **Error Handling**: Robust exception handling for web scraping failures
- **Rate Limiting**: Built-in delays to avoid overwhelming target website

### 3. Progress Tracking System
- **Status Dictionary**: Global dictionary to track processing status
- **Threading**: Background processing to avoid blocking the web interface
- **Real-time Updates**: AJAX-based progress updates for user feedback

### 4. Route Structure
- `/`: Main upload page
- `/upload`: File upload and validation endpoint
- `/progress/<task_id>`: Progress tracking page
- `/status/<task_id>`: AJAX endpoint for status updates
- `/download/<task_id>`: File download endpoint

## Data Flow

1. **File Upload**: User uploads Excel file through web interface
2. **Validation**: System validates file format and checks for EIN Number column
3. **Processing**: Background thread processes each EIN through web scraping
4. **Status Updates**: Real-time progress updates via AJAX calls
5. **Report Generation**: Creates updated Excel file with registration status
6. **Download**: User downloads processed file with results

## External Dependencies

### Python Packages
- **Flask**: Web framework and routing
- **Selenium**: Web browser automation
- **openpyxl**: Excel file processing
- **webdriver-manager**: Automatic Chrome driver management
- **gunicorn**: WSGI server for production deployment

### System Dependencies
- **Chrome/Chromium**: Web browser for scraping
- **ChromeDriver**: Browser automation driver
- **PostgreSQL**: Database system (available but not currently used)

### External Services
- **California DOJ Website**: Target for charity registration status scraping
- **ChromeDriver CDN**: Automatic driver downloads via webdriver-manager

## Deployment Strategy

### Production Configuration
- **Server**: Gunicorn WSGI server
- **Deployment**: Replit autoscale deployment target
- **Port**: 5000 (configurable)
- **Process Management**: Gunicorn with bind configuration

### Environment Setup
- **Python Version**: 3.11
- **Nix Packages**: geckodriver, openssl, postgresql
- **File Permissions**: Automatic directory creation for uploads/downloads

### Scalability Considerations
- **Stateless Design**: Processing status stored in memory (could be moved to database)
- **File Cleanup**: Temporary files need periodic cleanup
- **Rate Limiting**: Built-in delays for web scraping respect target website

## Changelog

- June 23, 2025: Initial setup with basic charity status checking functionality
- June 23, 2025: Fixed browser initialization issues with system Chromium
- June 23, 2025: Updated scraper to handle current California DOJ website structure
- June 23, 2025: Enhanced status parsing to capture complete multi-word status text including "Current - In Process", "Current - Awaiting Reporting", etc.

## User Preferences

Preferred communication style: Simple, everyday language.
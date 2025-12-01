# Overview

This is a Flask-based audit liability tool designed to automate the search for unrecorded liabilities as part of audit procedures. The application processes Excel files containing financial transaction data (Check Registers and Subsequent General Ledger files) from the three months following a fiscal year-end to identify potential unrecorded liabilities. It performs transaction sampling based on materiality thresholds, analyzes vendor payments for prior-year services, and generates comprehensive audit reports.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM for database operations
- **Database Models**: Four main entities - AuditSession (audit engagement details), UploadedFile (file metadata), Transaction (processed transaction data), and Finding (audit findings)
- **Data Processing**: Modular design with separate classes for Excel processing (ExcelProcessor), liability analysis (LiabilityAnalyzer), and report generation (ReportGenerator)
- **File Handling**: Secure file upload system with 16MB size limits and Excel format validation

## Frontend Architecture
- **Template Engine**: Jinja2 templates with a base template inheritance structure
- **UI Framework**: Bootstrap 5 for responsive design with custom CSS styling
- **JavaScript**: Vanilla JavaScript for form validation, file upload handling, and progress indicators
- **User Interface**: Multi-page workflow including dashboard, session creation, file upload, analysis results, and report generation

## Data Processing Pipeline
- **Transaction Extraction**: Flexible column mapping system to handle various Excel file formats and column naming conventions
- **Sampling Logic**: Risk-based transaction sampling with configurable materiality thresholds
- **Analysis Engine**: Pattern-matching algorithms to identify potential unrecorded liabilities including prior-year services, large payments, and recurring service patterns
- **Report Generation**: Comprehensive audit workpaper generation with export capabilities

## Security and Configuration
- **Environment Variables**: Database URLs and session secrets configured via environment variables
- **File Security**: Secure filename handling and upload directory management
- **Database Configuration**: Connection pooling and ping settings for reliability

# External Dependencies

## Core Framework Dependencies
- **Flask**: Web application framework with SQLAlchemy integration
- **Werkzeug**: WSGI utilities including ProxyFix middleware for deployment

## Data Processing Libraries
- **Pandas**: Excel file processing and data manipulation
- **NumPy**: Numerical operations for financial calculations

## Frontend Libraries (CDN)
- **Bootstrap 5**: CSS framework for responsive UI components
- **Font Awesome**: Icon library for user interface elements
- **Chart.js**: JavaScript charting library for data visualization

## Database
- **SQLite**: Default development database with SQLAlchemy ORM
- **PostgreSQL**: Production database option via DATABASE_URL environment variable

## File Processing
- **Excel Support**: Native pandas Excel reading capabilities for .xlsx and .xls files
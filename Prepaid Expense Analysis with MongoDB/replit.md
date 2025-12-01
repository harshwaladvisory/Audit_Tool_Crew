# Overview

This is a Flask-based web application for automating prepaid expense analysis in accounting workflows. The system helps auditors and accountants verify prepaid expense balances by comparing General Ledger (GL) and Trial Balance (TB) data with recalculated amounts from invoice documentation. It automatically identifies discrepancies and generates correcting journal entries (AJEs) to resolve inconsistencies.

The application streamlines the traditionally manual process of prepaid expense analysis by providing automated data extraction, balance comparison, discrepancy detection, and journal entry generation capabilities through an intuitive web interface.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Web Framework Architecture
The application uses Flask as the primary web framework with SQLAlchemy for database operations. The architecture follows a traditional MVC pattern with separate modules for models, routes, and utilities. The Flask app is configured with ProxyFix middleware for deployment compatibility and includes comprehensive database connection pooling and error handling.

## Database Design
The system uses SQLAlchemy with a declarative base model approach. Core entities include GeneralLedger, TrialBalance, Invoice, PrepaidExpenseAnalysis, Discrepancy, JournalEntry, and FileUpload models. The database schema supports foreign key relationships between file uploads and their associated data records, enabling traceability and audit trails.

## File Processing System
Uploaded files (Excel/CSV) are processed through a dedicated utility module that handles data extraction, validation, and database storage. The system supports multiple file types (GL, TB, INVOICE) with standardized column mapping and data cleaning processes. Files are temporarily stored in an uploads directory and removed after processing to maintain security.

## Analysis Engine
The core analysis functionality compares GL and TB balances against recalculated prepaid expense amounts derived from invoice data. The expense_analyzer module implements sophisticated matching algorithms to group invoices by account and calculate expected balances. Discrepancies are automatically identified and prioritized based on materiality thresholds.

## Journal Entry Generation
The journal_generator module automatically creates adjusting journal entries (AJEs) to resolve identified discrepancies. It implements accounting logic to determine appropriate debit and credit entries based on the nature and direction of each discrepancy. Generated entries include detailed descriptions and maintain proper accounting equation balance.

## Frontend Architecture
The user interface is built with Bootstrap-based responsive templates using a dark theme. The system includes multiple specialized views for file upload, analysis configuration, discrepancy review, and journal entry management. JavaScript functionality provides enhanced user interactions including drag-and-drop file upload, table sorting, and dynamic form validation.

## Security and Validation
File uploads are restricted to specific extensions (xlsx, xls, csv) with size limitations. The system implements secure filename handling and temporary file cleanup. Database operations use parameterized queries through SQLAlchemy to prevent injection attacks.

# External Dependencies

## Database System
The application expects a PostgreSQL database connection via the DATABASE_URL environment variable. SQLAlchemy handles database abstraction with connection pooling and automatic reconnection features configured for production deployment.

## File Processing Libraries
pandas library handles Excel and CSV file reading and data manipulation. The system supports multiple file formats and includes robust error handling for malformed or incomplete data files.

## Frontend Libraries
Bootstrap CSS framework provides responsive design components with a custom dark theme. Font Awesome icons enhance the user interface. Chart.js enables data visualization for analysis results and summary statistics.

## Session Management
Flask sessions are secured with a SESSION_SECRET environment variable. The application maintains user context across requests for file upload tracking and analysis state management.

## Runtime Environment
The application is designed for deployment on platforms supporting Python/Flask with environment variable configuration. File upload functionality requires write access to a temporary uploads directory that is automatically created and managed.
# Overview

The Journal Entry Sampling & Testwork Agent is a comprehensive audit automation tool built with Flask that handles the complete lifecycle of journal entry testing for financial audits. The application ingests General Ledger data, performs risk-based analysis, selects appropriate samples, and generates professional audit workpapers and artifacts. It streamlines the traditionally manual process of journal entry testing by automating population building, risk assessment, sample selection, and artifact generation while maintaining audit trail requirements and professional standards.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Technology**: HTML templates with Bootstrap dark theme and Font Awesome icons
- **Design Pattern**: Server-side rendered pages with minimal JavaScript
- **User Interface**: Clean, professional audit-focused interface with file upload capabilities and results display
- **Styling**: Custom CSS with Bootstrap integration for responsive design

## Backend Architecture
- **Framework**: Flask web framework with Python
- **Architecture Pattern**: Modular service-oriented design with separate processors for each audit function
- **File Processing**: Multi-format support (CSV, XLSX, XLS, PDF, TXT) with secure file handling
- **Core Services**:
  - `JEProcessor`: Handles GL data ingestion and standardization
  - `RiskAnalyzer`: Applies risk heuristics and scoring algorithms
  - `SampleSelector`: Implements risk-based and random sampling methodologies
  - `ArtifactGenerator`: Creates professional audit workpapers and reports
  - `GeminiIntegration`: Optional AI-powered memo generation

## Data Processing Pipeline
- **Ingestion**: Multi-format file processing with column standardization
- **Risk Assessment**: Automated flagging based on keywords, timing, amounts, and user patterns
- **Sample Selection**: Statistical sampling with materiality considerations and coverage targets
- **Testing Framework**: Structured attribute testing with exception logging
- **Output Generation**: Professional Excel workbooks and summary documentation

## Security and Data Handling
- **File Security**: Secure filename handling and upload validation
- **Data Protection**: Local file storage in uploads directory with sanitized access
- **Session Management**: Flask session handling with configurable secret keys
- **Size Limits**: 50MB maximum file upload size to prevent resource exhaustion

## Error Handling and Logging
- **Logging Framework**: Comprehensive logging throughout all processors
- **Error Recovery**: Graceful handling of file processing errors with continued operation
- **Validation**: Data validation at each processing stage with detailed error reporting

# External Dependencies

## Core Python Libraries
- **Flask**: Web framework for application structure and routing
- **Pandas**: Data manipulation and analysis for GL processing
- **NumPy**: Numerical computations for risk scoring and sampling
- **OpenPyXL**: Excel file generation for professional audit workpapers
- **PDFPlumber**: PDF text extraction for GL data ingestion
- **Scikit-learn**: Statistical sampling utilities for sample selection

## Optional AI Integration
- **Google Gemini API**: AI-powered memo generation and narrative enhancement
- **Environment Variable**: `GEMINI_API_KEY` for optional integration
- **Fallback Strategy**: Basic memo generation when API unavailable

## Frontend Dependencies
- **Bootstrap**: CSS framework via CDN for responsive design
- **Font Awesome**: Icon library via CDN for professional UI elements
- **Custom Styling**: Application-specific CSS for audit-focused interface

## File System Dependencies
- **Local Storage**: `./uploads` directory for file management
- **Supported Formats**: CSV, Excel (XLSX/XLS), PDF, and text files
- **Output Directory**: Generated artifacts stored in uploads folder

## Configuration Dependencies
- **Environment Variables**: 
  - `SESSION_SECRET`: Flask session security
  - `GEMINI_API_KEY`: Optional AI integration
- **Runtime Configuration**: Debug mode, file size limits, and security settings
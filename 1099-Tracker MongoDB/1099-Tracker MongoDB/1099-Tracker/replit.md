# Overview

A Flask-based web application that automates 1099 vendor classification for tax reporting. The system processes vendor expense data from CSV/Excel files and uses Gemini AI to classify vendors according to 2024 IRS 1099 reporting rules. It determines which vendors require 1099-NEC, 1099-MISC forms, or are not reportable, with a $600 annual payment threshold.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Template Engine**: Jinja2 templates with Flask for server-side rendering
- **Static Assets**: CSS and JavaScript served from Flask static folders
- **UI Framework**: Custom CSS with Font Awesome icons for a responsive dashboard interface
- **File Upload**: HTML5 file input with client-side validation for CSV/Excel files

### Backend Architecture
- **Web Framework**: Flask application with session-based routing
- **File Processing**: Pandas for CSV/Excel data parsing and manipulation
- **Data Storage**: Session-based in-memory storage using UUID-based session IDs
- **Security**: Werkzeug secure filename handling, file size limits (16MB), and required SESSION_SECRET environment variable
- **Error Handling**: Custom 404/500 error pages with proper HTTP status codes

### AI Integration
- **Classification Engine**: Google Gemini AI (gemini-2.5-flash/pro) for vendor categorization
- **Structured Output**: Pydantic models for type-safe AI response validation
- **Business Logic**: 2024 IRS 1099 rules implementation with confidence scoring
- **Policy Enforcement**: Post-processing enforces "never ask W-9 when Tax ID exists" across all AI paths

### Data Processing Pipeline
- **File Upload**: Secure file handling with extension validation (.csv, .xlsx, .xls)
- **Data Aggregation**: Vendor-level grouping with total payment calculations and global index assignment
- **Classification Logic**: Rule-based and AI-powered vendor categorization with Tax ID policy enforcement
- **Dual Categorization**: 
  - 1099-Eligible vendors without SSN/EIN appear in BOTH 1099-Eligible and W-9 Required tabs
  - W-9 Required vendors with $600+ also appear in 1099-Eligible (will need 1099 once W-9 obtained)
  - Non-Reportable vendors (banks, government entities, corporations) stay ONLY in Non-Reportable tab
- **Manual Transfer**: Users can transfer vendors between 1099-Eligible and Non-Reportable categories for review adjustments
- **Export Functionality**: Excel export with Summary tab first, followed by categorized sheets; CSV export with categorized sections
- **UI Improvements**: 
  - Results page container widened to 1800px max (from 1200px) to use available screen space
  - Table columns optimized to 1620px total with text wrapping enabled for AI Reasoning, Notes, and Actions
  - Horizontal scrolling eliminated on screens ≥1800px, significantly reduced on 1440-1800px screens
  - All labels updated from "Vendor ID" to "SSN/EIN No."
  - Enhanced tax ID detection for phrases like "(no tax ID on file)", "missing", "not provided"

## External Dependencies

### AI Services
- **Google Gemini AI**: Primary classification engine requiring GEMINI_API_KEY
- **Google GenAI SDK**: Latest google-genai package (upgraded from google-generativeai)

### Python Libraries
- **Flask**: Web framework and routing
- **Pandas**: Data manipulation and file processing
- **Werkzeug**: Security utilities and file handling
- **Pydantic**: Data validation and structured AI responses

### Frontend Libraries
- **Font Awesome 6.0**: Icon library via CDN
- **Custom CSS**: No external CSS frameworks, custom responsive design

### File Processing
- **CSV Support**: Native pandas CSV reading
- **Excel Support**: pandas Excel file processing (.xlsx, .xls)
- **File Validation**: Extension-based validation with size limits

### Security Requirements
- **Environment Variables**: SESSION_SECRET required for secure session management
- **File Upload Security**: Secure filename handling and content type validation
- **Session Management**: UUID-based session isolation for multi-user support
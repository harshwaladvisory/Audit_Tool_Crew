# AI Budget Preparation Assistant

## Overview

AI Budget Preparation Assistant is an AI-powered application that helps users create accurate, detailed proposed budgets for any fiscal year based on historical budgets, actual expenses, and general ledger (GL) data. The application provides a web interface with a clean light background theme for file upload, budget configuration, and AI-assisted budget preparation.

**Recent Updates (October 1, 2025)**:
- **Simplified AI Integration**: Now uses Google Gemini AI (gemini-1.5-flash) exclusively via GOOGLE_API_KEY
- **GL Account-Based Structure**: GL Account details derived from GL Account column in uploaded data
- **User Information Capture**: Captures client name, user name (prepared by), and budget period at budget preparation time
- **Budget Reclassification**: 
  - Interactive "Reclass Budget" column for manual budget transfers between GL accounts
  - Real-time validation ensuring net zero reclassification (balanced transfers)
  - Visual indicator showing balance status (green when balanced, red when unbalanced)
  - Shows exact values without rounding for accurate net-zero validation
  - Supports negative values for deductions (e.g., remove $10,000 from one account)
  - Example: Add $10,000 to "5200 Automobile" and deduct $10,000 from "5000 Salary"
- **Enhanced Budget Columns**:
  - GL Account details
  - Prior Year Budget
  - Actual Expenses
  - Carryover = max(Prior Year Budget - Actual Expenses, 0)
  - Proposed Budget
  - **Reclass Budget** (editable, must sum to zero)
  - **Final Proposed Budget** = Proposed Budget + Reclass Budget
- **Two Budget Preparation Methods**:
  1. **Detailed Budget Analysis**: Upload prior year budget and GL transaction data for comprehensive analysis with carryover calculations
  2. **Lump Sum Allocation**: Enter total budget amount to allocate proportionally based on prior year percentages
- **Enhanced Excel Export**: 
  - Includes client name, user name, and budget period as headers at the top
  - Header display order: Client Name → Prepared By → Budget Period
  - All budget columns with proper formatting
  - Currency formatting for numeric columns
  - Highlighted TOTAL row
  - Auto-adjusted column widths
  - Protection against Excel formula injection

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Technology Stack**: The frontend uses vanilla JavaScript with server-side rendered HTML templates (Jinja2) and custom CSS styling.

**Design Pattern**: Traditional server-side rendering approach where Flask renders HTML templates. The UI is enhanced with JavaScript for interactive elements like file upload, drag-and-drop functionality, and dynamic form updates.

**Rationale**: This approach was chosen for simplicity and to avoid the complexity of a separate frontend framework. It keeps the application lightweight and reduces dependencies while still providing an interactive user experience.

**Key Components**:
- File upload interface with drag-and-drop support
- Configuration panel for budget adjustments (inflation rate, percentage increases)
- Results display area for AI-generated analysis

### Backend Architecture

**Technology Stack**: Flask (Python web framework) serving as the primary backend server.

**Core Functionality**:
1. **File Processing**: Handles CSV and Excel file uploads using pandas for data manipulation
2. **Data Cleaning**: Implements numeric column cleaning to handle various currency formats and missing values
3. **Budget Adjustments**: Applies inflation rates and percentage-based increases to budget data
4. **Session Management**: Uses Flask sessions to maintain user state across requests

**Design Decisions**:
- **Pandas for Data Processing**: Chosen for its robust handling of tabular data and Excel/CSV file formats
- **Flexible Column Detection**: Implements fuzzy matching to find budget columns even with varying naming conventions
- **Numeric Data Cleaning**: Handles common formatting issues (commas, dollar signs, missing values) to ensure reliable calculations

### AI Integration

**Google Gemini AI**: The application uses Google Gemini AI exclusively for budget analysis and recommendations:

1. **GOOGLE_API_KEY**: Environment variable for authentication
2. **gemini-pro model**: Used for all AI-powered budget recommendations
3. **Contextual Analysis**: AI analyzes budget data, spending patterns, and provides strategic recommendations

**Rationale**: Gemini provides reliable, high-quality AI analysis for budget preparation. The integration is simple and requires only an API key for setup.

### Data Storage

**File-based Storage**: Uploaded files are stored in an `uploads/` directory on the server filesystem.

**Session-based State**: User preferences and configuration are maintained using Flask's session mechanism with a secret key for security.

**Rationale**: For this application scope, file-based storage is sufficient as it's designed for single-user analysis sessions rather than persistent multi-user data storage. This keeps deployment simple without requiring database setup.

## External Dependencies

### Python Libraries
- **Flask**: Web framework for routing and request handling
- **pandas**: Data manipulation and file reading (CSV/Excel)
- **google-generativeai**: Google Gemini API integration for AI-powered analysis
- **werkzeug**: Secure filename handling for uploads
- **openpyxl**: Excel file support

### Frontend Libraries
- **Native Browser APIs**: File API for drag-and-drop, Fetch API for AJAX requests
- **No external JavaScript frameworks**: Uses vanilla JS for DOM manipulation

### File Format Support
- **CSV files**: Text-based comma-separated values
- **Excel files**: `.xlsx` and `.xls` formats via pandas

### AI Services
- **Google Gemini**: Cloud-based AI service for budget analysis and recommendations

### Configuration
- **Environment Variables**: 
  - `SESSION_SECRET`: Flask session encryption key
  - `GOOGLE_API_KEY`: Google Gemini API authentication key
# Securities Deposits Analysis Platform

## Overview

This is a comprehensive securities deposits analysis platform built for financial compliance and audit management. The application helps organizations track, analyze, and manage securities deposits with automated compliance monitoring, interest calculations, aging analysis, and audit program management. It features file upload capabilities for bulk data processing, real-time dashboard analytics, and comprehensive reporting tools for regulatory compliance.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: React with TypeScript for type safety and modern development
- **Routing**: Wouter for lightweight client-side routing
- **State Management**: TanStack Query for server state management and caching
- **UI Components**: Radix UI primitives with shadcn/ui components for consistent design
- **Styling**: Tailwind CSS with CSS variables for theming and responsive design
- **Build Tool**: Vite for fast development and optimized production builds

### Backend Architecture
- **Runtime**: Node.js with Express.js framework for RESTful API endpoints
- **Language**: TypeScript for end-to-end type safety
- **Database ORM**: Drizzle ORM for type-safe database operations and migrations
- **File Processing**: Multer for handling file uploads with support for Excel and CSV formats
- **Data Processing**: XLSX and csv-parser libraries for spreadsheet data extraction

### Database Design
- **Primary Database**: PostgreSQL via Neon serverless database
- **Schema Management**: Drizzle migrations with shared schema definitions
- **Key Entities**:
  - Deposits table for securities deposit records
  - File uploads tracking with processing status
  - Interest calculations with compound interest support
  - Aging analysis for compliance monitoring
  - Audit programs and reports for regulatory compliance
  - Audit logs for activity tracking

### Application Services
- **File Processor**: Handles Excel/CSV file parsing and data extraction
- **Analysis Engine**: Performs aging analysis and compliance calculations
- **Report Generator**: Creates summary, exception, and compliance reports
- **Interest Calculator**: Computes accrued interest with configurable rates

### Security and Validation
- **Input Validation**: Zod schemas for request validation and type safety
- **File Upload Security**: File type validation and size limits
- **Error Handling**: Centralized error handling with proper HTTP status codes

## External Dependencies

### Database Services
- **Neon Database**: Serverless PostgreSQL database for production data storage
- **WebSocket Support**: Real-time database connections via ws library

### UI/UX Libraries
- **Radix UI**: Comprehensive set of accessible UI primitives
- **Lucide React**: Modern icon library for consistent iconography
- **React Hook Form**: Form handling with validation support
- **React Dropzone**: File upload with drag-and-drop functionality

### Development Tools
- **Replit Integration**: Development environment optimization with cartographer plugin
- **ESBuild**: Fast bundling for production server builds
- **PostCSS**: CSS processing with Tailwind CSS integration

### File Processing
- **SheetJS (XLSX)**: Excel file reading and parsing
- **CSV Parser**: Efficient CSV file processing
- **Multer**: Multipart form data handling for file uploads

### Utility Libraries
- **Date-fns**: Date manipulation and formatting
- **Nanoid**: Unique ID generation
- **Class Variance Authority**: Utility-first CSS class management
- **clsx & Tailwind Merge**: Conditional CSS class handling
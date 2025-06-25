# Mitch Quick - Auction Flipping Tracker

## Overview

Mitch Quick is a comprehensive web application for managing auction flipping businesses. Built with Flask 3.0 and Python 3.12, it provides comprehensive tracking for auctions, inventory management, profit calculations, partner relationships, and automated reporting. The application supports the complete auction flipping workflow from watchlisting items to final sale and profit distribution.

## System Architecture

### Frontend Architecture
- **Framework**: Flask with Jinja2 templating
- **UI Components**: Bootstrap 5 with dark theme, Font Awesome icons
- **Interactive Elements**: HTMX for dynamic interactions, Alpine.js for client-side reactivity
- **Charts**: Chart.js for data visualization
- **Responsive Design**: Mobile-friendly interface using Bootstrap grid system

### Backend Architecture
- **Framework**: Flask 3.0 with Blueprint organization
- **Database**: SQLAlchemy ORM with SQLite (configurable to PostgreSQL)
- **Authentication**: Flask-Login with session-based auth
- **Migration**: Flask-Migrate for database schema management
- **Deployment**: Gunicorn WSGI server with autoscale deployment

### Blueprint Structure
- **auth**: User authentication (login/register)
- **dashboard**: Main dashboard with KPIs and overview
- **auctions**: Auction CRUD operations
- **items**: Item management (watchlist, inventory, sales)
- **partners**: Partner management and profit sharing
- **reports**: Financial reports and analytics

## Key Components

### Core Data Models
1. **User**: Authentication and user management
2. **Auction**: Auction events with date, location, notes
3. **Item**: Central entity tracking items through entire lifecycle (watch → won → listed → sold)
4. **Partner**: Business partners for profit sharing
5. **ItemPartner**: Many-to-many relationship with percentage shares

### Item Lifecycle Management
- **Watch Status**: Items on watchlist with planned max bid and target resale price
- **Won Status**: Items purchased with actual purchase price and refurbishment costs
- **Listed Status**: Items listed for sale with channel and listing details
- **Sold Status**: Items sold with final sale price, fees, and shipping costs

### Profit Calculation Engine
- **Gross Profit**: Sale price minus total costs (purchase + refurb)
- **Net Profit**: Gross profit minus fees and shipping
- **ROI Percentage**: Return on investment calculations
- **Break-even Analysis**: Required sale price to break even
- **Partner Share Distribution**: Automatic calculation based on percentage shares

### Advanced Features
1. **Expenses Tracking**: Comprehensive itemized expense system that automatically factors into profit calculations
2. **eBay API Integration**: Automated price suggestions with 24-hour caching
3. **Email Reports**: Scheduled cash flow reports with CSV attachments and charts
4. **Responsive Dashboard**: Real-time KPI tracking and trend analysis
5. **CSV Import/Export**: Complete inventory management with bulk operations

## Data Flow

### Item Creation Flow
1. User creates auction event
2. Items added manually or via PDF import (OCR)
3. Items start in "watch" status with planned bids
4. Status progresses: watch → won → listed → sold
5. Profit calculations update automatically at each stage

### Partner Management Flow
1. Partners created with contact information
2. Partners assigned to items with percentage shares
3. Profit distribution calculated automatically when items sell
4. Earnings tracked and exportable for payout management

### Reporting Flow
1. Real-time dashboard updates with latest metrics
2. Cash flow reports generated on-demand or scheduled
3. Partner earnings reports with detailed breakdowns
4. Export capabilities for external accounting systems

## External Dependencies

### Core Dependencies
- **Flask 3.1.1**: Web framework
- **SQLAlchemy 2.0.41**: Database ORM
- **Flask-Login 0.6.3**: Authentication
- **Flask-Migrate 4.1.0**: Database migrations
- **Gunicorn 23.0.0**: Production WSGI server

### OCR and File Processing
- **pdfplumber 0.11.7**: PDF text extraction
- **pytesseract 0.3.13**: OCR for scanned documents
- **Pillow 11.2.1**: Image processing

### External APIs
- **requests 2.32.4**: HTTP client for eBay API integration
- **eBay Browse API**: Price suggestion service (configured via environment variables)

### Visualization and Reports
- **matplotlib 3.10.3**: Chart generation for reports
- **Chart.js**: Frontend data visualization

### Database Support
- **psycopg2-binary 2.9.10**: PostgreSQL adapter (for production scaling)
- **SQLite**: Default development database

## Deployment Strategy

### Development Environment
- Uses SQLite database for simplicity
- Flask development server with debug mode
- Hot reloading enabled for rapid development

### Production Configuration
- Gunicorn WSGI server with autoscale deployment
- ProxyFix middleware for proper header handling
- Environment-based configuration management
- Session secret and database URL via environment variables

### Environment Variables
- `SESSION_SECRET`: Flask session encryption key
- `DATABASE_URL`: Database connection string
- `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID`: eBay API credentials
- `SMTP_*`: Email configuration for reports

### File Upload Configuration
- Maximum file size: 16MB
- Secure filename handling
- Upload folder configuration for PDF processing

## Recent Changes

- June 25, 2025: **ALL CRITICAL ISSUES RESOLVED** - Application fully functional with comprehensive piece sales tracking
- June 25, 2025: Fixed all template sum filter errors by using selectattr to handle null values properly
- June 25, 2025: Resolved 500 internal server errors on sold items and expenses pages
- June 25, 2025: **PIECE SALES TRACKING SYSTEM COMPLETE** - Full CRUD operations for individual piece sales with edit functionality
- June 25, 2025: Enhanced piece sales history display with edit buttons and proper tracking in item details
- June 25, 2025: Fixed weekly performance graph data calculation with proper error handling
- June 25, 2025: Corrected inventory statistics calculations to handle null values properly
- June 25, 2025: Added edit_piece_sale route and template for modifying existing piece sale records
- June 25, 2025: Created demo data with lumber bundle example showing multiple pieces functionality
- June 25, 2025: **MULTIPLE PIECES FEATURE IMPLEMENTED** - Complete bulk item management with individual piece sales tracking
- June 25, 2025: Added ItemSale model and sell_pieces functionality for tracking individual piece transactions
- June 25, 2025: Fixed expenses integration bug - Total expenses now properly factor into all profit calculations
- June 25, 2025: Added comprehensive Expenses system with itemized tracking that factors into profit calculations
- June 25, 2025: Moved CSV import/export functionality from inventory page to main items page as requested
- June 25, 2025: Completely removed all PDF import functionality and buttons as requested
- June 25, 2025: Fixed profit analysis report JSON serialization error with Item objects
- June 25, 2025: Fixed partner view template undefined variable errors with safe fallbacks
- June 25, 2025: Items page fully functional with complete bulk operations (select, delete, status change)
- June 25, 2025: Fixed pagination vs list data structure inconsistencies across all templates
- June 25, 2025: Corrected all profit calculation method/property calling errors in templates
- June 25, 2025: Enhanced template safety with null value handling using (value or 0) pattern
- June 25, 2025: Added bulk select and delete functionality for items with status change options
- June 25, 2025: Fixed PDF import session size limits using temporary file storage approach
- June 25, 2025: OCR system enhanced to handle auction catalog format with 122+ lots
- June 25, 2025: Migrated from custom authentication to Replit OpenID Connect system
- June 25, 2025: Added CSV import/export functionality for complete inventory management
- June 25, 2025: eBay API integration ready (awaiting user credentials)

## Changelog

- June 25, 2025. Initial setup and Replit authentication migration

## User Preferences

Preferred communication style: Simple, everyday language.
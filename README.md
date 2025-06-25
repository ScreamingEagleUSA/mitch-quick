# Mitch Quick - Auction Flipping Tracker

A comprehensive web application for managing auction flipping businesses, built with Flask. Track auctions, manage inventory, calculate profits, handle partner relationships, and automate reporting.

![Mitch Quick Logo](https://img.shields.io/badge/Mitch%20Quick-Auction%20Tracker-blue)
![Python](https://img.shields.io/badge/Python-3.12-green)
![Flask](https://img.shields.io/badge/Flask-3.0-red)
![License](https://img.shields.io/badge/License-MIT-yellow)

## ✨ Features

### 🎯 Core Functionality
- **Auction Management**: Create and track upcoming auctions with dates, locations, and notes
- **Watchlist System**: Monitor items of interest with planned max bids and target resale prices
- **Inventory Tracking**: Manage won items with purchase prices, refurbishment costs, and status updates
- **Sales Logging**: Record sales with channels, prices, fees, and shipping costs
- **Profit Calculations**: Automatic gross/net profit, ROI, and break-even analysis

### 👥 Partnership Management
- **Partner Profiles**: Manage business partners with contact information
- **Flexible Profit Sharing**: Variable percentage shares per item
- **Earnings Tracking**: Detailed partner earnings history and payout ledger
- **Automated Reports**: Generate partner earnings statements

### 📊 Advanced Features
- **OCR PDF Import**: Extract lot information from auction catalogs using pdfplumber and pytesseract
- **eBay API Integration**: Get automated price suggestions with 24-hour caching
- **Cash Flow Reports**: Weekly/monthly financial analysis with charts
- **Email Automation**: Scheduled reports with CSV attachments and matplotlib charts

### 📱 User Experience
- **Responsive Design**: Mobile-friendly interface using Bootstrap and Tailwind CSS
- **HTMX Integration**: Dynamic interactions without page reloads
- **Real-time Updates**: Live price updates and status changes
- **Dashboard Analytics**: Comprehensive KPI tracking and trend analysis

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- Git
- (Optional) Tesseract OCR for PDF import functionality

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/mitch-quick.git
   cd mitch-quick
   ```

2. **Set up virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   
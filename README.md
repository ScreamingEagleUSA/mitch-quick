# Mitch Quick - Auction Flipping Tracker

A comprehensive web application for managing auction flipping businesses, built with Flask. Track auctions, manage inventory, calculate profits, handle partner relationships, and automate reporting.

![Mitch Quick Logo](https://img.shields.io/badge/Mitch%20Quick-Auction%20Tracker-blue)
![Python](https://img.shields.io/badge/Python-3.11-green)
![Flask](https://img.shields.io/badge/Flask-3.1-red)
![Supabase](https://img.shields.io/badge/Supabase-Database-orange)
![Render](https://img.shields.io/badge/Render-Deployment-purple)

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
- **Responsive Design**: Mobile-friendly interface using Bootstrap
- **Real-time Updates**: Live price updates and status changes
- **Dashboard Analytics**: Comprehensive KPI tracking and trend analysis
- **Modern Authentication**: Secure login with Google, GitHub, or email

## 🚀 Quick Setup Guide

### Prerequisites
- GitHub account
- Supabase account (free)
- Render account (free)

### Step 1: Set up Supabase

1. **Create Supabase Account**
   - Go to [supabase.com](https://supabase.com)
   - Click "Start your project" and sign up
   - Create a new project

2. **Get Your API Keys**
   - In your Supabase dashboard, go to Settings → API
   - Copy the following values:
     - **Project URL** (looks like: `https://your-project.supabase.co`)
     - **Anon public key** (starts with `eyJ...`)

3. **Set up Authentication**
   - Go to Authentication → Settings
   - Enable the providers you want (Google, GitHub, Email)
   - For Google/GitHub, you'll need to add your app's URL later

4. **Create Database Tables**
   - Go to SQL Editor
   - Run the following SQL to create the required tables:

```sql
-- Users table (will be created automatically by Supabase Auth)
-- No need to create this manually

-- Auctions table
CREATE TABLE auction (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    date DATE NOT NULL,
    location VARCHAR(200),
    url TEXT,
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Partners table
CREATE TABLE partner (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(120),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Items table
CREATE TABLE item (
    id SERIAL PRIMARY KEY,
    auction_id INTEGER REFERENCES auction(id) ON DELETE CASCADE,
    lot_number VARCHAR(50),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    planned_max_bid DECIMAL(10,2),
    target_resale_price DECIMAL(10,2),
    status VARCHAR(20) DEFAULT 'watch',
    purchase_price DECIMAL(10,2),
    refurb_cost DECIMAL(10,2) DEFAULT 0,
    list_date DATE,
    list_channel VARCHAR(100),
    sale_date DATE,
    sale_price DECIMAL(10,2),
    sale_fees DECIMAL(10,2) DEFAULT 0,
    shipping_cost DECIMAL(10,2) DEFAULT 0,
    multiple_pieces BOOLEAN DEFAULT FALSE,
    pieces_total INTEGER,
    pieces_remaining INTEGER,
    ebay_suggested_price DECIMAL(10,2),
    ebay_price_updated TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Item Partners table
CREATE TABLE item_partner (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES item(id) ON DELETE CASCADE,
    partner_id INTEGER REFERENCES partner(id) ON DELETE CASCADE,
    pct_share DECIMAL(5,2) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Item Expenses table
CREATE TABLE item_expense (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES item(id) ON DELETE CASCADE,
    description VARCHAR(200) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    date DATE NOT NULL DEFAULT CURRENT_DATE,
    category VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Item Sales table
CREATE TABLE item_sale (
    id SERIAL PRIMARY KEY,
    item_id INTEGER REFERENCES item(id) ON DELETE CASCADE,
    pieces_sold INTEGER NOT NULL,
    sale_price_per_piece DECIMAL(10,2) NOT NULL,
    total_sale_amount DECIMAL(10,2) NOT NULL,
    sale_date DATE NOT NULL DEFAULT CURRENT_DATE,
    buyer_info VARCHAR(200),
    sale_channel VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### Step 2: Deploy to Render

1. **Push to GitHub**
   - Create a new GitHub repository
   - Push this code to your repository

2. **Deploy on Render**
   - Go to [render.com](https://render.com)
   - Sign up with your GitHub account
   - Click "New" → "Web Service"
   - Select your repository
   - Render will automatically detect it's a Python app

3. **Set Environment Variables**
   - In your Render project, go to Environment
   - Add the following environment variables:
     ```
     SUPABASE_URL=your_supabase_project_url
     SUPABASE_ANON_KEY=your_supabase_anon_key
     SECRET_KEY=your_random_secret_key
     DATABASE_URL=your_supabase_database_url
     ```

4. **Get Database URL**
   - In Supabase, go to Settings → Database
   - Copy the "Connection string" (URI format)
   - Replace `[YOUR-PASSWORD]` with your database password
   - Add this as `DATABASE_URL` in Render

### Step 3: Configure Authentication

1. **Update Redirect URLs**
   - In Supabase, go to Authentication → Settings → URL Configuration
   - Add your Render app URL to the Site URL
   - Add `https://your-app.onrender.com/auth/login/callback` to Redirect URLs

2. **Test the App**
   - Visit your Render app URL
   - Try signing in with Google, GitHub, or email
   - You should be redirected to the dashboard

## 🔧 Local Development

### Prerequisites
- Python 3.11+
- Git

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/mitch-quick.git
   cd mitch-quick
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   - Create a `.env` file in the root directory
   - Add your Supabase credentials:
   ```
   SUPABASE_URL=your_supabase_project_url
   SUPABASE_ANON_KEY=your_supabase_anon_key
   SECRET_KEY=your_random_secret_key
   DATABASE_URL=your_supabase_database_url
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Visit the app**
   - Open http://localhost:5000 in your browser

## 📝 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | Yes |
| `SUPABASE_ANON_KEY` | Your Supabase anonymous key | Yes |
| `SECRET_KEY` | Flask secret key for sessions | Yes |
| `DATABASE_URL` | Supabase database connection string | Yes |
| `EBAY_APP_ID` | eBay API application ID | No |
| `EBAY_CERT_ID` | eBay API certificate ID | No |
| `EBAY_DEV_ID` | eBay API developer ID | No |

## 🛠️ Troubleshooting

### Common Issues

1. **Authentication not working**
   - Check that your Supabase URL and keys are correct
   - Verify redirect URLs are set up properly
   - Make sure you've enabled the authentication providers you want to use

2. **Database connection errors**
   - Verify your DATABASE_URL is correct
   - Check that your Supabase database is active
   - Ensure the tables were created successfully

3. **Deployment issues**
   - Check Render logs for error messages
   - Verify all environment variables are set
   - Make sure the requirements.txt file is in the root directory

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📞 Support

If you encounter any issues or have questions:
1. Check the troubleshooting section above
2. Review the Supabase and Render documentation
3. Open an issue on GitHub
   
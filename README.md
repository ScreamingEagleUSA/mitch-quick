# Mitch Quick - Auction Flipping Tracker

A comprehensive web application for tracking auction purchases, managing inventory, calculating profits, and coordinating with business partners.

## 🚀 Features

- **Auction Management**: Track upcoming auctions, locations, and notes
- **Inventory Tracking**: Monitor items from watchlist to sold status
- **Profit Calculations**: Automatic ROI and profit margin calculations
- **Partner Management**: Split profits and track partner contributions
- **Expense Tracking**: Itemized expenses for accurate profit calculations
- **Multiple Pieces Support**: Track bulk items with individual piece sales
- **Email Automation**: Scheduled reports with CSV attachments and matplotlib charts
- **Modern UI**: Clean, responsive interface with Tailwind CSS

## 🛠️ Tech Stack

- **Backend**: Python 3.12 + Flask 3
- **Database**: Supabase PostgreSQL
- **Authentication**: Supabase Auth
- **Frontend**: HTML + Tailwind CSS + Alpine.js + HTMX
- **Deployment**: Render (Free tier)
- **Email**: SMTP with matplotlib charts

## 📋 Prerequisites

- Python 3.12+
- Supabase account
- Render account (for deployment)
- SMTP credentials (for email reports)

## 🔧 Setup Instructions

### 1. Clone the Repository

```bash
git clone https://github.com/ScreamingEagleUSA/mitch-quick.git
cd mitch-quick
```

### 2. Set Up Supabase

1. Create a new project at [supabase.com](https://supabase.com)
2. Get your project URL and API keys from Settings > API
3. Set up email authentication in Authentication > Settings

### 3. Environment Variables

Create a `.env` file in the root directory:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
DATABASE_URL=your_supabase_database_url

# Email Configuration (for reports)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your_email@gmail.com
SMTP_PASSWORD=your_app_password
FROM_EMAIL=your_email@gmail.com

# eBay API (optional)
EBAY_APP_ID=your_ebay_app_id
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Initialize Database

```bash
python setup.py
```

### 6. Run the Application

```bash
python main.py
```

Visit `http://localhost:5000` to access the application.

## 🚀 Deployment on Render

### 1. Push to GitHub

```bash
git add .
git commit -m "Initial commit"
git push origin main
```

### 2. Deploy on Render

1. Go to [render.com](https://render.com) and create an account
2. Click "New +" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `mitch-quick`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`

### 3. Environment Variables

Add all environment variables from your `.env` file to Render's environment variables section.

### 4. Deploy

Click "Create Web Service" and wait for deployment to complete.

## 📊 Database Schema

### Core Tables

- **users**: User accounts (managed by Supabase Auth)
- **auctions**: Auction events and details
- **items**: Individual items with status tracking
- **partners**: Business partners for profit sharing
- **item_partners**: Many-to-many relationship for profit splits
- **item_expenses**: Itemized expenses
- **item_sales**: Individual piece sales for bulk items

### Item Statuses

- `watch`: Items being monitored
- `won`: Items purchased at auction
- `listed`: Items listed for sale
- `sold`: Items successfully sold

## 🔐 Authentication

The application uses Supabase Auth for user management:

- Email/password authentication
- Email verification required
- Session management with Flask-Login
- Secure token-based authentication

## 📧 Email Reports

The application can send automated cash flow reports:

- Weekly CSV exports
- Matplotlib charts
- Configurable SMTP settings
- Multiple recipient support

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For support, please open an issue on GitHub or contact the development team.

---

**Note**: This application was migrated from Replit to Supabase + Render for better scalability and deployment options.
   
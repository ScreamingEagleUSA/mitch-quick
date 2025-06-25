import logging
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email import encoders
from typing import List, Optional
import tempfile
from datetime import datetime, timedelta
import csv
import io

logger = logging.getLogger(__name__)

class EmailService:
    """Email service for sending cash flow reports and notifications"""
    
    def __init__(self):
        self.smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.username = os.environ.get('SMTP_USERNAME', 'default_username')
        self.password = os.environ.get('SMTP_PASSWORD', 'default_password')
        self.from_email = os.environ.get('FROM_EMAIL', self.username)
    
    def send_email(self, to_emails: List[str], subject: str, body: str, 
                   attachments: Optional[List[dict]] = None, html_body: Optional[str] = None) -> bool:
        """Send email with optional attachments"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            # Add text body
            msg.attach(MIMEText(body, 'plain'))
            
            # Add HTML body if provided
            if html_body:
                msg.attach(MIMEText(html_body, 'html'))
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
            
            logger.info(f"Email sent successfully to {', '.join(to_emails)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def _add_attachment(self, msg: MIMEMultipart, attachment: dict):
        """Add attachment to email message"""
        try:
            attachment_type = attachment.get('type', 'file')
            
            if attachment_type == 'csv':
                # CSV data attachment
                part = MIMEBase('text', 'csv')
                part.set_payload(attachment['data'])
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment["filename"]}"'
                )
                msg.attach(part)
                
            elif attachment_type == 'image':
                # Image attachment
                with open(attachment['path'], 'rb') as f:
                    img_data = f.read()
                image = MIMEImage(img_data)
                image.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment["filename"]}"'
                )
                msg.attach(image)
                
            elif attachment_type == 'file':
                # Generic file attachment
                with open(attachment['path'], 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment["filename"]}"'
                )
                msg.attach(part)
                
        except Exception as e:
            logger.error(f"Failed to add attachment: {e}")

def generate_cashflow_csv(start_date: datetime, end_date: datetime) -> str:
    """Generate cash flow CSV data"""
    from models import Item, ItemStatus
    
    try:
        # Get all relevant transactions in date range
        items = Item.query.filter(
            Item.updated_at >= start_date,
            Item.updated_at <= end_date
        ).all()
        
        # Generate CSV data
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            'Date', 'Type', 'Item', 'Amount', 'Category', 'Auction', 'Notes'
        ])
        
        # Write transactions
        for item in items:
            auction_title = item.auction.title if item.auction else 'N/A'
            
            # Money out (purchases and refurb costs)
            if item.purchase_price:
                writer.writerow([
                    item.updated_at.strftime('%Y-%m-%d') if item.updated_at else '',
                    'Expense',
                    item.title,
                    f'-{float(item.purchase_price):.2f}',
                    'Purchase',
                    auction_title,
                    f'Lot #{item.lot_number}' if item.lot_number else ''
                ])
            
            if item.refurb_cost and float(item.refurb_cost) > 0:
                writer.writerow([
                    item.updated_at.strftime('%Y-%m-%d') if item.updated_at else '',
                    'Expense',
                    item.title,
                    f'-{float(item.refurb_cost):.2f}',
                    'Refurbishment',
                    auction_title,
                    'Repair/restoration costs'
                ])
            
            # Money in (sales)
            if item.sale_price and item.status == ItemStatus.SOLD:
                writer.writerow([
                    item.sale_date.strftime('%Y-%m-%d') if item.sale_date else '',
                    'Income',
                    item.title,
                    f'{float(item.sale_price):.2f}',
                    'Sale',
                    auction_title,
                    f'Sold on {item.list_channel}' if item.list_channel else 'Sale'
                ])
                
                # Sale fees as expense
                if item.sale_fees and float(item.sale_fees) > 0:
                    writer.writerow([
                        item.sale_date.strftime('%Y-%m-%d') if item.sale_date else '',
                        'Expense',
                        item.title,
                        f'-{float(item.sale_fees):.2f}',
                        'Fees',
                        auction_title,
                        'Marketplace fees'
                    ])
                
                # Shipping costs
                if item.shipping_cost and float(item.shipping_cost) > 0:
                    writer.writerow([
                        item.sale_date.strftime('%Y-%m-%d') if item.sale_date else '',
                        'Expense',
                        item.title,
                        f'-{float(item.shipping_cost):.2f}',
                        'Shipping',
                        auction_title,
                        'Shipping costs'
                    ])
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"Error generating cash flow CSV: {e}")
        return ""

def generate_cashflow_chart(start_date: datetime, end_date: datetime) -> Optional[str]:
    """Generate cash flow chart and return file path"""
    try:
        import matplotlib.pyplot as plt
        import matplotlib.dates as mdates
        from collections import defaultdict
        from models import Item, ItemStatus
        
        # Get transaction data
        items = Item.query.filter(
            Item.updated_at >= start_date,
            Item.updated_at <= end_date
        ).all()
        
        # Aggregate data by week
        weekly_data = defaultdict(lambda: {'income': 0, 'expenses': 0})
        
        for item in items:
            week_start = item.updated_at.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = week_start - timedelta(days=week_start.weekday())  # Start of week
            
            # Expenses
            if item.purchase_price:
                weekly_data[week_start]['expenses'] += float(item.purchase_price)
            if item.refurb_cost:
                weekly_data[week_start]['expenses'] += float(item.refurb_cost)
            if item.sale_fees:
                weekly_data[week_start]['expenses'] += float(item.sale_fees)
            if item.shipping_cost:
                weekly_data[week_start]['expenses'] += float(item.shipping_cost)
            
            # Income
            if item.sale_price and item.status == ItemStatus.SOLD:
                weekly_data[week_start]['income'] += float(item.sale_price)
        
        if not weekly_data:
            logger.warning("No data available for cash flow chart")
            return None
        
        # Prepare chart data
        dates = sorted(weekly_data.keys())
        income = [weekly_data[date]['income'] for date in dates]
        expenses = [weekly_data[date]['expenses'] for date in dates]
        net_flow = [inc - exp for inc, exp in zip(income, expenses)]
        
        # Create chart
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Income vs Expenses
        ax1.bar(dates, income, label='Income', color='green', alpha=0.7)
        ax1.bar(dates, [-exp for exp in expenses], label='Expenses', color='red', alpha=0.7)
        ax1.set_title('Weekly Cash Flow - Income vs Expenses')
        ax1.set_ylabel('Amount ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Format x-axis
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator())
        
        # Net Flow
        colors = ['green' if x >= 0 else 'red' for x in net_flow]
        ax2.bar(dates, net_flow, color=colors, alpha=0.7)
        ax2.set_title('Weekly Net Cash Flow')
        ax2.set_ylabel('Net Amount ($)')
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        ax2.grid(True, alpha=0.3)
        
        # Format x-axis
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
        ax2.xaxis.set_major_locator(mdates.WeekdayLocator())
        
        plt.tight_layout()
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            plt.savefig(temp_file.name, dpi=300, bbox_inches='tight')
            plt.close()
            return temp_file.name
            
    except Exception as e:
        logger.error(f"Error generating cash flow chart: {e}")
        return None

def send_weekly_cashflow_report(recipient_emails: List[str]) -> bool:
    """Send weekly cash flow report email"""
    try:
        # Calculate date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Generate CSV data
        csv_data = generate_cashflow_csv(start_date, end_date)
        
        # Generate chart
        chart_path = generate_cashflow_chart(start_date, end_date)
        
        # Prepare email content
        subject = f"Mitch Quick - Weekly Cash Flow Report ({start_date.strftime('%m/%d')} - {end_date.strftime('%m/%d')})"
        
        body = f"""
        Weekly Cash Flow Report
        
        Period: {start_date.strftime('%B %d, %Y')} - {end_date.strftime('%B %d, %Y')}
        
        This report includes:
        - Detailed cash flow CSV with all transactions
        - Weekly cash flow chart showing income vs expenses
        
        Please find the attached files for detailed analysis.
        
        Best regards,
        Mitch Quick Auction Tracker
        """
        
        # Prepare attachments
        attachments = []
        
        if csv_data:
            attachments.append({
                'type': 'csv',
                'data': csv_data,
                'filename': f'cashflow_report_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.csv'
            })
        
        if chart_path:
            attachments.append({
                'type': 'image',
                'path': chart_path,
                'filename': f'cashflow_chart_{start_date.strftime("%Y%m%d")}_{end_date.strftime("%Y%m%d")}.png'
            })
        
        # Send email
        email_service = EmailService()
        success = email_service.send_email(recipient_emails, subject, body, attachments)
        
        # Clean up temporary chart file
        if chart_path:
            try:
                os.unlink(chart_path)
            except OSError:
                pass
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending weekly cash flow report: {e}")
        return False

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smolagents import Tool
from pathlib import Path

class EmailTool(Tool):
    name = "email_tool"
    description = (
        "Sends an email with discrepancy details to the specified bank's email. "
        "Inputs must include the subject, body of the email, and recipient email."
    )
    inputs = {
        "subject": {
            "type": "string",
            "description": "The subject of the email."
        },
        "body": {
            "type": "string",
            "description": "The body content of the email."
        },
        "to_email": {
            "type": "string",
            "description": "The recipient's email address."
        }
    }
    output_type = "string"

    def forward(self, subject: str, body: str, to_email: str) -> str:
        # Email configuration - replace with actual credentials or secure them via environment variables
        from_email = "your-email@example.com"
        password = "your-email-password"

        # Validate email format (basic check)
        if '@' not in to_email or '.' not in to_email.split('@')[-1]:
            raise ValueError(f"Invalid email format: {to_email}")

        # Set up MIME
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        print(msg)

        # Send the email using SMTP
        try:
            # Set up SMTP server (using Gmail for this example)
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(from_email, password)
            text = msg.as_string()
            server.sendmail(from_email, to_email, text)
            server.quit()
            print(f"[email_tool] Email successfully sent to {to_email}")
            return f"Email sent to {to_email}"
        except Exception as e:
            print(f"[email_tool] Failed to send email: {str(e)}")
            return f"Failed to send email: {str(e)}"

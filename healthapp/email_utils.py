# email_utils.py
import os
from mailjet_rest import Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

MAILJET_API_KEY = os.getenv('MAILJET_API_KEY')
MAILJET_SECRET_KEY = os.getenv('MAILJET_SECRET_KEY')

# Set up Mailjet client
mailjet = Client(auth=(MAILJET_API_KEY, MAILJET_SECRET_KEY), version='v3.1')


def send_email(subject, body, to_email):
    data = {
        'Messages': [
            {
                "From": {
                    "Email": "your-email@example.com",  # Your verified Mailjet sender email
                    "Name": "Your Name"
                },
                "To": [
                    {
                        "Email": to_email
                    }
                ],
                "Subject": subject,
                "TextPart": body,
                "HTMLPart": f"<p>{body}</p>",  # You can also send HTML emails
            }
        ]
    }

    # Send the email
    result = mailjet.send.create(data=data)

    # Handle success or failure
    if result.status_code == 200:
        print(f"Email sent successfully to {to_email}")
    else:
        print(f"Failed to send email: {result.status_code}, {result.text}")


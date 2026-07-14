import os
import sys
import subprocess

# Self-install reportlab if not present
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
except ImportError:
    print("Installing reportlab dependency for generating PDF files...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "reportlab"])
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_pdf(filename: str, title: str, pages: list):
    """Generates a structured PDF with multiple pages and paragraphs."""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    doc = SimpleDocTemplate(filename, pagesize=letter)
    story = []
    
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        spaceAfter=15
    )
    
    heading_style = ParagraphStyle(
        'PageHeading',
        parent=styles['Heading2'],
        fontSize=14,
        leading=18,
        spaceBefore=15,
        spaceAfter=8
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        spaceAfter=10
    )

    # Document Header
    story.append(Paragraph(title, title_style))
    story.append(Spacer(1, 15))

    for page_idx, page_paragraphs in enumerate(pages):
        if page_idx > 0:
            story.append(PageBreak())
        
        story.append(Paragraph(f"Section {page_idx + 1}: Detailed Guidelines", heading_style))
        story.append(Spacer(1, 8))
        
        for para in page_paragraphs:
            story.append(Paragraph(para, body_style))
            
    doc.build(story)
    print(f"Successfully generated PDF: {filename}")

if __name__ == "__main__":
    # Define corporate policy document paragraphs
    policy_pages = [
        [
            "This document outlines the standard operating procedures and employee handbook guidelines for Acme Corporation.",
            "Vacation Policy: All full-time employees are allocated 20 days of paid time off (PTO) annually. PTO accrues monthly at a rate of 1.67 days. Employees must submit PTO requests through the HR portal at least two weeks in advance for approval by their direct manager. Unused PTO can roll over to the next calendar year up to a maximum of 5 days. Any additional unused PTO above 5 days will expire on December 31st.",
        ],
        [
            "Hybrid Work Guidelines: Acme Corporation supports a hybrid working model. Employees are required to work from the designated corporate office three days per week (typically Tuesday, Wednesday, and Thursday). Mondays and Fridays are optional remote working days, subject to manager approval and team alignment. Core working hours are between 10:00 AM and 4:00 PM EST, during which all employees must be reachable via Slack and email."
        ]
    ]

    # Define cloud architecture document paragraphs
    arch_pages = [
        [
            "Acme Cloud Platform Architecture and System Deployment Guide.",
            "Production Server Setup: The production system is hosted on AWS using a Multi-AZ deployment. The front-end React application is built static and served via Amazon CloudFront CDN. The backend microservices run on Amazon ECS using Fargate launch type to avoid server management overhead. Auto-scaling groups are configured to scale out when CPU utilization exceeds 70% or average request latency exceeds 200ms."
        ],
        [
            "Database Layer and Failover Procedures: The relational database layer runs on Amazon Aurora PostgreSQL. We run a primary database writer instance in us-east-1a and an active read-replica in us-east-1b. The pgvector extension is enabled on Aurora to support semantic vector storage. Automated daily backups are retained for 35 days. In the event of a primary database node failure, Amazon Aurora automatically triggers a failover to the read-replica in less than 30 seconds with zero data loss."
        ]
    ]

    # Target directory inside the scratch folder
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    input_dir = os.path.join(project_root, "data", "input")

    create_pdf(
        os.path.join(input_dir, "corporate_policy.pdf"),
        "Acme Corp Employee Policy Handbook",
        policy_pages
    )
    create_pdf(
        os.path.join(input_dir, "cloud_architecture.pdf"),
        "Acme Cloud Services Infrastructure Specification",
        arch_pages
    )

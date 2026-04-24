#!/usr/bin/env python3
"""Seed believable ops data: transactions, support tickets, compliance records, audit logs.

Run from the project root:
    python scripts/seed_data.py

Always clears previous seed rows before inserting, so safe to re-run.
SMS-created transactions (source='sms') are never touched.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import date, datetime, timedelta, timezone
from uuid import uuid4

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.app.core.config import get_settings
from backend.app.models.audit_log import AuditLog
from backend.app.models.compliance_record import ComplianceRecord
from backend.app.models.support_ticket import SupportTicket
from backend.app.models.transaction import Transaction

settings = get_settings()


def _ts(days_ago: int, hour: int = 12, minute: int = 0) -> datetime:
    """Return an explicit UTC datetime that is exactly `days_ago` days before today."""
    past = date.today() - timedelta(days=days_ago)
    return datetime(past.year, past.month, past.day, hour, minute, 0, tzinfo=timezone.utc)


# ─── Seed data ────────────────────────────────────────────────────────────────
# days_ago are all integers ≥ 1 so every seeded row is clearly before today.
# SMS-added transactions (source='sms') will have today's timestamp naturally.

TRANSACTIONS: list[dict] = [
    # ── 1-2 days ago — recent normal spending ──────────────────────────────
    {"amount": 14.50,  "merchant": "Starbucks",          "location": "Jersey City, NJ",   "category": "dining",        "risk_score": 5,  "flagged": False, "days_ago": 1, "hour": 8},
    {"amount": 62.00,  "merchant": "ShopRite",            "location": "Hoboken, NJ",       "category": "groceries",     "risk_score": 3,  "flagged": False, "days_ago": 1, "hour": 17},
    {"amount": 8.75,   "merchant": "MTA Transit",         "location": "New York, NY",      "category": "transport",     "risk_score": 2,  "flagged": False, "days_ago": 1, "hour": 7},
    {"amount": 15.99,  "merchant": "Netflix",             "location": "Online",            "category": "subscriptions", "risk_score": 2,  "flagged": False, "days_ago": 1, "hour": 12},
    {"amount": 45.00,  "merchant": "Chipotle",            "location": "Manhattan, NY",     "category": "dining",        "risk_score": 4,  "flagged": False, "days_ago": 2, "hour": 13},
    {"amount": 78.00,  "merchant": "Whole Foods",         "location": "Brooklyn, NY",      "category": "groceries",     "risk_score": 4,  "flagged": False, "days_ago": 2, "hour": 19},
    {"amount": 32.00,  "merchant": "Uber",                "location": "New York, NY",      "category": "transport",     "risk_score": 3,  "flagged": False, "days_ago": 2, "hour": 22},
    # ── 1-2 days ago — HIGH RISK flagged ──────────────────────────────────
    {"amount": 2450.00,"merchant": "Apple Store",         "location": "Miami, FL",         "category": "electronics",   "risk_score": 82, "flagged": True,  "days_ago": 1, "hour": 23, "notes": "High-value electronics, unusual location"},
    {"amount": 1900.00,"merchant": "Best Buy",            "location": "Orlando, FL",       "category": "electronics",   "risk_score": 78, "flagged": True,  "days_ago": 2, "hour": 2,  "notes": "Purchase at 2:13 AM — unusual hour and location"},

    # ── 3-5 days ago ───────────────────────────────────────────────────────
    {"amount": 120.00, "merchant": "Amazon",              "location": "NJ",                "category": "retail",        "risk_score": 10, "flagged": False, "days_ago": 3, "hour": 14},
    {"amount": 55.00,  "merchant": "Target",              "location": "Secaucus, NJ",      "category": "retail",        "risk_score": 5,  "flagged": False, "days_ago": 3, "hour": 11},
    {"amount": 22.50,  "merchant": "Dunkin",              "location": "Jersey City, NJ",   "category": "dining",        "risk_score": 2,  "flagged": False, "days_ago": 3, "hour": 9},
    {"amount": 9.99,   "merchant": "Spotify",             "location": "Online",            "category": "subscriptions", "risk_score": 2,  "flagged": False, "days_ago": 4, "hour": 12},
    {"amount": 38.00,  "merchant": "CVS Pharmacy",        "location": "Hoboken, NJ",       "category": "retail",        "risk_score": 3,  "flagged": False, "days_ago": 4, "hour": 16},
    {"amount": 89.00,  "merchant": "Trader Joes",         "location": "Manhattan, NY",     "category": "groceries",     "risk_score": 5,  "flagged": False, "days_ago": 4, "hour": 18},
    {"amount": 18.00,  "merchant": "Lyft",                "location": "New York, NY",      "category": "transport",     "risk_score": 3,  "flagged": False, "days_ago": 5, "hour": 23},
    {"amount": 980.00, "merchant": "Delta Airlines",      "location": "Newark, NJ",        "category": "travel",        "risk_score": 58, "flagged": True,  "days_ago": 4, "hour": 1,  "notes": "Late-night booking, high amount"},
    {"amount": 450.00, "merchant": "Samsung Store",       "location": "Manhattan, NY",     "category": "electronics",   "risk_score": 30, "flagged": False, "days_ago": 5, "hour": 14},

    # ── 6-9 days ago ───────────────────────────────────────────────────────
    {"amount": 65.00,  "merchant": "Panera Bread",        "location": "Hoboken, NJ",       "category": "dining",        "risk_score": 5,  "flagged": False, "days_ago": 6, "hour": 12},
    {"amount": 12.99,  "merchant": "Hulu",                "location": "Online",            "category": "subscriptions", "risk_score": 2,  "flagged": False, "days_ago": 6, "hour": 12},
    {"amount": 47.00,  "merchant": "H&M",                 "location": "Manhattan, NY",     "category": "retail",        "risk_score": 5,  "flagged": False, "days_ago": 6, "hour": 14},
    {"amount": 195.00, "merchant": "Sephora",             "location": "Manhattan, NY",     "category": "retail",        "risk_score": 15, "flagged": False, "days_ago": 7, "hour": 15},
    {"amount": 43.00,  "merchant": "Best Buy",            "location": "Paramus, NJ",       "category": "electronics",   "risk_score": 10, "flagged": False, "days_ago": 7, "hour": 13},
    {"amount": 28.00,  "merchant": "McDonald's",          "location": "Newark, NJ",        "category": "dining",        "risk_score": 3,  "flagged": False, "days_ago": 7, "hour": 11},
    {"amount": 3100.00,"merchant": "Rolex",               "location": "New York, NY",      "category": "retail",        "risk_score": 91, "flagged": True,  "days_ago": 6, "hour": 20, "notes": "Luxury goods, amount exceeds threshold"},
    {"amount": 520.00, "merchant": "Delta Airlines",      "location": "Newark, NJ",        "category": "travel",        "risk_score": 35, "flagged": False, "days_ago": 8, "hour": 10},
    {"amount": 385.00, "merchant": "Marriott Hotel",      "location": "Washington, DC",    "category": "travel",        "risk_score": 28, "flagged": False, "days_ago": 8, "hour": 15},
    {"amount": 1650.00,"merchant": "Samsung Electronics", "location": "Chicago, IL",       "category": "electronics",   "risk_score": 72, "flagged": True,  "days_ago": 7, "hour": 21, "notes": "Different city than usual pattern"},
    {"amount": 74.00,  "merchant": "Stop & Shop",         "location": "Jersey City, NJ",   "category": "groceries",     "risk_score": 4,  "flagged": False, "days_ago": 9, "hour": 17},
    {"amount": 11.99,  "merchant": "Apple Music",         "location": "Online",            "category": "subscriptions", "risk_score": 2,  "flagged": False, "days_ago": 9, "hour": 12},

    # ── 10-14 days ago ─────────────────────────────────────────────────────
    {"amount": 52.00,  "merchant": "Zara",                "location": "Manhattan, NY",     "category": "retail",        "risk_score": 5,  "flagged": False, "days_ago": 10, "hour": 14},
    {"amount": 33.00,  "merchant": "Shake Shack",         "location": "Manhattan, NY",     "category": "dining",        "risk_score": 4,  "flagged": False, "days_ago": 10, "hour": 19},
    {"amount": 110.00, "merchant": "Nike Store",          "location": "Manhattan, NY",     "category": "retail",        "risk_score": 10, "flagged": False, "days_ago": 10, "hour": 15},
    {"amount": 4200.00,"merchant": "Luxury Watch Shop",   "location": "Las Vegas, NV",     "category": "retail",        "risk_score": 95, "flagged": True,  "days_ago": 10, "hour": 22, "notes": "High-value luxury purchase, new merchant"},
    {"amount": 61.00,  "merchant": "Costco",              "location": "Hackensack, NJ",    "category": "groceries",     "risk_score": 5,  "flagged": False, "days_ago": 11, "hour": 11},
    {"amount": 24.00,  "merchant": "Sweetgreen",          "location": "Hoboken, NJ",       "category": "dining",        "risk_score": 3,  "flagged": False, "days_ago": 11, "hour": 13},
    {"amount": 82.00,  "merchant": "Macy's",              "location": "Manhattan, NY",     "category": "retail",        "risk_score": 7,  "flagged": False, "days_ago": 12, "hour": 16},
    {"amount": 2800.00,"merchant": "Gucci",               "location": "Scottsdale, AZ",    "category": "retail",        "risk_score": 88, "flagged": True,  "days_ago": 12, "hour": 18, "notes": "Luxury purchase in unfamiliar location"},
    {"amount": 310.00, "merchant": "Sephora",             "location": "Los Angeles, CA",   "category": "retail",        "risk_score": 28, "flagged": False, "days_ago": 13, "hour": 15},
    {"amount": 19.99,  "merchant": "Adobe Creative",      "location": "Online",            "category": "subscriptions", "risk_score": 2,  "flagged": False, "days_ago": 13, "hour": 12},
    {"amount": 480.00, "merchant": "Nordstrom",           "location": "Tysons Corner, VA", "category": "retail",        "risk_score": 32, "flagged": False, "days_ago": 14, "hour": 14},
    {"amount": 720.00, "merchant": "American Airlines",   "location": "JFK, NY",           "category": "travel",        "risk_score": 40, "flagged": False, "days_ago": 14, "hour": 6},

    # ── 15-20 days ago ─────────────────────────────────────────────────────
    {"amount": 29.00,  "merchant": "Planet Fitness",      "location": "Jersey City, NJ",   "category": "subscriptions", "risk_score": 2,  "flagged": False, "days_ago": 15, "hour": 7},
    {"amount": 91.00,  "merchant": "Wegmans",             "location": "Woodbridge, NJ",    "category": "groceries",     "risk_score": 5,  "flagged": False, "days_ago": 15, "hour": 18},
    {"amount": 57.00,  "merchant": "Gap",                 "location": "Menlo Park, NJ",    "category": "retail",        "risk_score": 5,  "flagged": False, "days_ago": 16, "hour": 14},
    {"amount": 3700.00,"merchant": "Digital Assets LLC",  "location": "Online",            "category": "transfers",     "risk_score": 93, "flagged": True,  "days_ago": 16, "hour": 1,  "notes": "High-value transfer to unverified entity"},
    {"amount": 16.50,  "merchant": "Domino's",            "location": "Jersey City, NJ",   "category": "dining",        "risk_score": 2,  "flagged": False, "days_ago": 17, "hour": 20},
    {"amount": 41.00,  "merchant": "Verizon",             "location": "Online",            "category": "utilities",     "risk_score": 3,  "flagged": False, "days_ago": 17, "hour": 12},
    {"amount": 1200.00,"merchant": "FX Exchange",         "location": "Unknown",           "category": "transfers",     "risk_score": 65, "flagged": True,  "days_ago": 18, "hour": 3,  "notes": "Currency exchange at unusual hour"},
    {"amount": 88.00,  "merchant": "HomeDepot",           "location": "Linden, NJ",        "category": "retail",        "risk_score": 7,  "flagged": False, "days_ago": 18, "hour": 11},
    {"amount": 23.00,  "merchant": "Walgreens",           "location": "Hoboken, NJ",       "category": "retail",        "risk_score": 2,  "flagged": False, "days_ago": 19, "hour": 10},
    {"amount": 135.00, "merchant": "Apple Store",         "location": "Garden State Plaza","category": "electronics",   "risk_score": 12, "flagged": False, "days_ago": 19, "hour": 15},
    {"amount": 760.00, "merchant": "Unknown Merchant",    "location": "Austin, TX",        "category": "retail",        "risk_score": 60, "flagged": True,  "days_ago": 19, "hour": 23, "notes": "Unrecognized merchant name"},
    {"amount": 620.00, "merchant": "Southwest Airlines",  "location": "Newark, NJ",        "category": "travel",        "risk_score": 38, "flagged": False, "days_ago": 20, "hour": 7},

    # ── 21-30 days ago ─────────────────────────────────────────────────────
    {"amount": 48.00,  "merchant": "Cheesecake Factory",  "location": "Hackensack, NJ",    "category": "dining",        "risk_score": 4,  "flagged": False, "days_ago": 21, "hour": 19},
    {"amount": 67.00,  "merchant": "REI",                 "location": "Manhattan, NY",     "category": "retail",        "risk_score": 6,  "flagged": False, "days_ago": 22, "hour": 16},
    {"amount": 5500.00,"merchant": "Private Jet Charter", "location": "Teterboro, NJ",     "category": "travel",        "risk_score": 97, "flagged": True,  "days_ago": 22, "hour": 5,  "notes": "Extremely high-value travel, early morning"},
    {"amount": 1450.00,"merchant": "VPN Services",        "location": "Online",            "category": "subscriptions", "risk_score": 70, "flagged": True,  "days_ago": 24, "hour": 2,  "notes": "Unusual subscription amount, early morning"},
    {"amount": 30.00,  "merchant": "Shake Shack",         "location": "Hoboken, NJ",       "category": "dining",        "risk_score": 3,  "flagged": False, "days_ago": 25, "hour": 13},
    {"amount": 72.00,  "merchant": "Trader Joes",         "location": "Hoboken, NJ",       "category": "groceries",     "risk_score": 4,  "flagged": False, "days_ago": 26, "hour": 18},
    {"amount": 144.00, "merchant": "Zara",                "location": "Manhattan, NY",     "category": "retail",        "risk_score": 12, "flagged": False, "days_ago": 27, "hour": 14},
    {"amount": 21.00,  "merchant": "Uber Eats",           "location": "Jersey City, NJ",   "category": "dining",        "risk_score": 2,  "flagged": False, "days_ago": 28, "hour": 20},
    {"amount": 560.00, "merchant": "United Airlines",     "location": "Newark, NJ",        "category": "travel",        "risk_score": 36, "flagged": False, "days_ago": 29, "hour": 8},
    {"amount": 18.99,  "merchant": "Disney+",             "location": "Online",            "category": "subscriptions", "risk_score": 2,  "flagged": False, "days_ago": 30, "hour": 12},
]

SUPPORT_TICKETS: list[dict] = [
    {"description": "Customer reports refund still not received for order #4832, submitted 2 weeks ago.",  "category": "refund_delay",         "status": "open",      "priority": "high",   "customer": "Order #4832", "days_ago": 1},
    {"description": "User Maria cannot log in — password reset email not arriving.",                       "category": "login_issue",           "status": "open",      "priority": "high",   "customer": "Maria",       "days_ago": 1},
    {"description": "Payment keeps failing for customer James, card declined three times.",                "category": "payment_failure",       "status": "open",      "priority": "high",   "customer": "James",       "days_ago": 2},
    {"description": "Duplicate charge complaint from order #2291 — customer was billed twice.",           "category": "duplicate_charge",      "status": "open",      "priority": "high",   "customer": "Order #2291", "days_ago": 2},
    {"description": "Account locked after multiple failed login attempts — user cannot access.",          "category": "account_locked",        "status": "open",      "priority": "medium", "customer": None,          "days_ago": 3},
    {"description": "Transfer pending for 4 days, customer asking for status update.",                    "category": "transfer_issue",        "status": "open",      "priority": "medium", "customer": None,          "days_ago": 3},
    {"description": "Card declined at POS despite sufficient balance — verification failed.",             "category": "payment_failure",       "status": "open",      "priority": "medium", "customer": None,          "days_ago": 4},
    {"description": "Refund issued but not reflecting in customer account after 5 business days.",        "category": "refund_delay",          "status": "in_review", "priority": "medium", "customer": None,          "days_ago": 4},
    {"description": "App crashes on login screen for iOS 17 users.",                                     "category": "login_issue",           "status": "open",      "priority": "high",   "customer": None,          "days_ago": 5},
    {"description": "Customer Sarah disputes $340 charge claiming she never made the purchase.",          "category": "duplicate_charge",      "status": "open",      "priority": "high",   "customer": "Sarah",       "days_ago": 5},
    {"description": "Identity verification stuck — document upload failing repeatedly.",                  "category": "verification_problem",  "status": "open",      "priority": "medium", "customer": None,          "days_ago": 6},
    {"description": "Refund for cancelled subscription not processed after 10 days.",                     "category": "refund_delay",          "status": "open",      "priority": "medium", "customer": None,          "days_ago": 6},
    {"description": "Two-factor authentication not sending SMS codes to some users.",                     "category": "login_issue",           "status": "in_review", "priority": "high",   "customer": None,          "days_ago": 7},
    {"description": "ACH transfer to external bank not processing after 3 business days.",                "category": "transfer_issue",        "status": "open",      "priority": "medium", "customer": None,          "days_ago": 7},
    {"description": "Chargeback initiated by customer for $890 at Apple Store, under review.",            "category": "duplicate_charge",      "status": "in_review", "priority": "high",   "customer": None,          "days_ago": 8},
    {"description": "Password reset link expired before customer could use it.",                          "category": "login_issue",           "status": "resolved",  "priority": "low",    "customer": None,          "days_ago": 9},
    {"description": "Direct deposit not reflecting after payroll processing date.",                       "category": "transfer_issue",        "status": "open",      "priority": "high",   "customer": None,          "days_ago": 9},
    {"description": "Customer received wrong product and refund is being held pending return.",           "category": "refund_delay",          "status": "open",      "priority": "medium", "customer": None,          "days_ago": 10},
    {"description": "Merchant terminal error causing duplicate transaction record.",                      "category": "duplicate_charge",      "status": "resolved",  "priority": "medium", "customer": None,          "days_ago": 11},
    {"description": "User unable to add new payment method — card verification failing.",                 "category": "payment_failure",       "status": "open",      "priority": "medium", "customer": None,          "days_ago": 11},
    {"description": "Account suspended incorrectly due to fraud detection false positive.",               "category": "account_locked",        "status": "in_review", "priority": "high",   "customer": None,          "days_ago": 12},
    {"description": "Wire transfer to international account delayed beyond SLA.",                         "category": "transfer_issue",        "status": "open",      "priority": "high",   "customer": None,          "days_ago": 13},
    {"description": "Promotional credit not applied to account after qualifying purchase.",               "category": "general",               "status": "open",      "priority": "low",    "customer": None,          "days_ago": 14},
    {"description": "Notification settings not saving — customer keeps getting unwanted alerts.",         "category": "general",               "status": "resolved",  "priority": "low",    "customer": None,          "days_ago": 15},
    {"description": "Biometric login not working on Android 14 devices.",                                "category": "login_issue",           "status": "open",      "priority": "medium", "customer": None,          "days_ago": 16},
    {"description": "Refund processed but sent to wrong account — customer reporting missing funds.",     "category": "refund_delay",          "status": "in_review", "priority": "high",   "customer": None,          "days_ago": 17},
    {"description": "Contactless payment failing at grocery merchants intermittently.",                   "category": "payment_failure",       "status": "open",      "priority": "medium", "customer": None,          "days_ago": 18},
    {"description": "Customer verification documents rejected despite being valid.",                      "category": "verification_problem",  "status": "open",      "priority": "high",   "customer": None,          "days_ago": 19},
    {"description": "Bank statement showing charges from a merchant customer never visited.",             "category": "duplicate_charge",      "status": "open",      "priority": "high",   "customer": None,          "days_ago": 20},
    {"description": "Dispute form not loading — customer cannot submit chargeback request.",              "category": "general",               "status": "open",      "priority": "medium", "customer": None,          "days_ago": 21},
    {"description": "Mobile deposit not credited after 2 business days.",                                "category": "transfer_issue",        "status": "resolved",  "priority": "low",    "customer": None,          "days_ago": 22},
    {"description": "Account balance showing incorrect amount — discrepancy of $45.",                    "category": "general",               "status": "open",      "priority": "medium", "customer": None,          "days_ago": 24},
    {"description": "Recurring subscription charge hitting account despite cancellation.",                "category": "payment_failure",       "status": "open",      "priority": "high",   "customer": None,          "days_ago": 26},
    {"description": "Customer unable to reach support by phone — escalating to digital channel.",        "category": "general",               "status": "open",      "priority": "low",    "customer": None,          "days_ago": 28},
    {"description": "Old card still being charged after replacement card was issued.",                    "category": "payment_failure",       "status": "resolved",  "priority": "medium", "customer": None,          "days_ago": 30},
]

COMPLIANCE_RECORDS: list[dict] = [
    {"record_type": "expense_policy",        "description": "Employee submitted first class flight reimbursement for internal meeting — policy allows economy only.",              "status": "pending",  "policy_flag": True,  "severity": "high",   "recommendation": "Reject above economy rate. Issue policy reminder.",                    "days_ago": 1},
    {"record_type": "missing_documentation", "description": "Travel expense of $420 submitted without receipt or invoice.",                                                       "status": "pending",  "policy_flag": True,  "severity": "medium", "recommendation": "Request documentation before processing reimbursement.",               "days_ago": 2},
    {"record_type": "expense_policy",        "description": "Premium hotel rate ($480/night) booked for client meeting — exceeds $250/night policy limit.",                       "status": "pending",  "policy_flag": True,  "severity": "high",   "recommendation": "Approve partial reimbursement up to policy maximum.",                  "days_ago": 3},
    {"record_type": "manual_override",       "description": "Transaction limit override approved by supervisor outside normal approval chain.",                                    "status": "pending",  "policy_flag": True,  "severity": "high",   "recommendation": "Review with compliance officer. Document reasoning.",                  "days_ago": 4},
    {"record_type": "unusual_approval",      "description": "Wire transfer approved by single approver — dual control policy requires two sign-offs for amounts over $10,000.",   "status": "pending",  "policy_flag": True,  "severity": "high",   "recommendation": "Halt transfer pending second approval.",                               "days_ago": 5},
    {"record_type": "expense_policy",        "description": "Entertainment expense of $1,200 submitted for team dinner — exceeds $150/person policy.",                            "status": "pending",  "policy_flag": True,  "severity": "medium", "recommendation": "Audit attendee list. Reimburse policy-compliant portion only.",        "days_ago": 6},
    {"record_type": "missing_documentation", "description": "Vendor payment of $3,500 processed without signed contract or purchase order on file.",                              "status": "pending",  "policy_flag": True,  "severity": "high",   "recommendation": "Freeze additional payments. Request contract retroactively.",           "days_ago": 7},
    {"record_type": "general",               "description": "Expense report submitted 45 days late — outside the 30-day submission window.",                                      "status": "approved", "policy_flag": False, "severity": "low",    "recommendation": "Issue warning. Monitor for repeat late submissions.",                  "days_ago": 8},
    {"record_type": "unusual_approval",      "description": "Vendor contract renewed by department head without procurement review for amounts above $50,000.",                   "status": "pending",  "policy_flag": True,  "severity": "high",   "recommendation": "Escalate to procurement. Conduct retroactive vendor due diligence.",  "days_ago": 10},
    {"record_type": "expense_policy",        "description": "Personal Uber charges of $340 submitted as business travel expense.",                                                 "status": "rejected", "policy_flag": True,  "severity": "medium", "recommendation": "Reject claim. Remind employee of personal vs business expense policy.", "days_ago": 11},
    {"record_type": "manual_override",       "description": "Fraud alert manually dismissed by analyst without documented justification.",                                         "status": "pending",  "policy_flag": True,  "severity": "high",   "recommendation": "Require written justification for all alert dismissals.",               "days_ago": 13},
    {"record_type": "missing_documentation", "description": "Conference registration fee of $890 submitted without event details or business justification.",                      "status": "pending",  "policy_flag": False, "severity": "low",    "recommendation": "Request event agenda and business case before reimbursement.",          "days_ago": 14},
    {"record_type": "expense_policy",        "description": "Subscription software ($1,800/year) purchased on personal credit card without IT pre-approval.",                     "status": "approved", "policy_flag": False, "severity": "medium", "recommendation": "Process reimbursement. Require IT approval for future SaaS purchases.", "days_ago": 16},
    {"record_type": "unusual_approval",      "description": "Employee approved their own expense report — self-approval not permitted under segregation of duties policy.",       "status": "pending",  "policy_flag": True,  "severity": "high",   "recommendation": "Reject and route to proper approver. Log segregation of duties violation.", "days_ago": 18},
    {"record_type": "missing_documentation", "description": "Relocation allowance of $5,000 disbursed without supporting receipts or relocation agreement on file.",             "status": "pending",  "policy_flag": True,  "severity": "medium", "recommendation": "Hold additional disbursement. Request documentation.",                  "days_ago": 20},
    {"record_type": "general",               "description": "Training expense for non-approved vendor submitted by three employees in same department.",                           "status": "approved", "policy_flag": False, "severity": "low",    "recommendation": "Approve with note. Add vendor to approved list going forward.",         "days_ago": 21},
    {"record_type": "expense_policy",        "description": "Business class flight booked for domestic trip under 3 hours — policy requires economy for domestic routes.",        "status": "rejected", "policy_flag": True,  "severity": "medium", "recommendation": "Reject upgrade cost. Reimburse economy equivalent only.",               "days_ago": 23},
    {"record_type": "manual_override",       "description": "Customer credit limit manually increased by 40% without credit review process.",                                      "status": "pending",  "policy_flag": True,  "severity": "high",   "recommendation": "Freeze credit increase. Conduct formal credit review.",                 "days_ago": 25},
    {"record_type": "unusual_approval",      "description": "Sole-source vendor selected for $25,000 contract without competitive bidding documentation.",                        "status": "pending",  "policy_flag": True,  "severity": "medium", "recommendation": "Document sole-source justification or open competitive process.",       "days_ago": 27},
    {"record_type": "missing_documentation", "description": "Petty cash disbursements of $1,240 over 60 days with no receipts on file.",                                         "status": "pending",  "policy_flag": False, "severity": "medium", "recommendation": "Suspend petty cash account. Require retroactive documentation.",        "days_ago": 29},
]


async def seed(session: AsyncSession) -> None:
    # Clear previous seed rows only — never touch sms-created records
    print("Clearing previous seed data...")
    await session.execute(delete(AuditLog).where(AuditLog.source == "seed"))
    await session.execute(delete(Transaction).where(Transaction.source == "seed"))
    await session.execute(delete(SupportTicket).where(SupportTicket.source == "seed"))
    await session.execute(delete(ComplianceRecord).where(ComplianceRecord.source == "seed"))
    await session.flush()

    print(f"Seeding {len(TRANSACTIONS)} transactions...")
    for t in TRANSACTIONS:
        ts = _ts(t["days_ago"], t.get("hour", 12))
        tx = Transaction(
            id=str(uuid4()),
            amount=t["amount"],
            merchant=t["merchant"],
            location=t["location"],
            category=t["category"],
            risk_score=t["risk_score"],
            flagged=t["flagged"],
            notes=t.get("notes"),
            source="seed",
            created_at=ts,
        )
        session.add(tx)
        session.add(AuditLog(
            id=str(uuid4()),
            event_type="transaction_added",
            domain="transactions",
            action_taken=f"Seed transaction: ${tx.amount:.2f} at {tx.merchant}",
            reasoning=f"Seed data — risk score {tx.risk_score}",
            source="seed",
            related_entity_id=tx.id,
            created_at=ts,
        ))
        if tx.flagged:
            session.add(AuditLog(
                id=str(uuid4()),
                event_type="transaction_flagged",
                domain="transactions",
                action_taken=f"Transaction flagged: ${tx.amount:.2f} at {tx.merchant}",
                reasoning=f"Risk score {tx.risk_score} exceeded threshold",
                source="system",
                related_entity_id=tx.id,
                created_at=ts,
            ))

    print(f"Seeding {len(SUPPORT_TICKETS)} support tickets...")
    for t in SUPPORT_TICKETS:
        ts = _ts(t["days_ago"])
        ticket = SupportTicket(
            id=str(uuid4()),
            customer_identifier=t.get("customer"),
            description=t["description"],
            category=t["category"],
            status=t["status"],
            priority=t["priority"],
            source="seed",
            created_at=ts,
        )
        session.add(ticket)
        session.add(AuditLog(
            id=str(uuid4()),
            event_type="support_ticket_created",
            domain="support",
            action_taken=f"Seed support ticket: {ticket.category}",
            reasoning="Seed data",
            source="seed",
            related_entity_id=ticket.id,
            created_at=ts,
        ))

    print(f"Seeding {len(COMPLIANCE_RECORDS)} compliance records...")
    for c in COMPLIANCE_RECORDS:
        ts = _ts(c["days_ago"])
        record = ComplianceRecord(
            id=str(uuid4()),
            record_type=c["record_type"],
            description=c["description"],
            status=c["status"],
            policy_flag=c["policy_flag"],
            severity=c.get("severity"),
            recommendation=c.get("recommendation"),
            source="seed",
            created_at=ts,
        )
        session.add(record)
        session.add(AuditLog(
            id=str(uuid4()),
            event_type="compliance_record_added",
            domain="compliance",
            action_taken=f"Seed compliance: {record.record_type}",
            reasoning="Seed data",
            source="seed",
            related_entity_id=record.id,
            created_at=ts,
        ))

    await session.commit()
    print(
        f"Done. {len(TRANSACTIONS)} transactions, "
        f"{len(SUPPORT_TICKETS)} support tickets, "
        f"{len(COMPLIANCE_RECORDS)} compliance records seeded."
    )


async def main() -> None:
    engine = create_async_engine(settings.database_url, echo=False, future=True)
    SessionLocal = async_sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    async with SessionLocal() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

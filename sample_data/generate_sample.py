"""Generate sample Meta Ads CSV data for testing."""
import csv
import random
from datetime import datetime, timedelta

CAMPAIGN_NAMES = [
    "Summer Sale 2024",
    "Diwali Collection Launch",
    "Brand Awareness Q3",
    "Retargeting - Website Visitors",
    "New Product Launch - Shoes",
    "Clearance Sale Jan 2025",
    "Valentine's Day Promo",
    "App Install Campaign",
]

OBJECTIVES = ["CONVERSIONS", "BRAND_AWARENESS", "REACH", "TRAFFIC", "APP_INSTALLS"]


def generate_campaigns_csv(filename, start_date, end_date):
    rows = []
    current = start_date
    while current <= end_date:
        for i, name in enumerate(CAMPAIGN_NAMES):
            impressions = random.randint(5000, 100000)
            clicks = random.randint(int(impressions * 0.005), int(impressions * 0.05))
            spend = round(random.uniform(500, 15000), 2)
            purchases = random.randint(0, int(clicks * 0.1)) if clicks > 0 else 0
            purchase_value = round(purchases * random.uniform(500, 3000), 2) if purchases > 0 else 0

            rows.append({
                "Campaign ID": f"camp_{i+1:04d}",
                "Campaign Name": name,
                "Objective": random.choice(OBJECTIVES),
                "Delivery": random.choice(["Active", "Completed", "Paused"]),
                "Date": current.strftime("%Y-%m-%d"),
                "Impressions": impressions,
                "Clicks (all)": clicks,
                "Amount Spent (INR)": spend,
                "Reach": int(impressions * random.uniform(0.6, 0.95)),
                "Results": random.randint(0, purchases + 5),
                "Purchases": purchases,
                "Purchase Conversion Value": purchase_value,
                "CPM (Cost per 1,000 Impressions)": round(spend / impressions * 1000, 2) if impressions > 0 else 0,
                "CPC (all)": round(spend / clicks, 2) if clicks > 0 else 0,
                "CTR (all)": round(clicks / impressions * 100, 2) if impressions > 0 else 0,
                "Frequency": round(random.uniform(1.0, 4.0), 2),
            })
        current += timedelta(days=1)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} campaign rows -> {filename}")


def generate_adsets_csv(filename, start_date, end_date):
    adset_names = [
        "Lookalike 1% - Purchasers",
        "Interest - Fashion",
        "Retargeting 7 days",
        "Broad - 18-35 Female",
        "Custom Audience - Email List",
        "Interest - Home Decor",
    ]
    rows = []
    current = start_date
    while current <= end_date:
        for ci, camp_name in enumerate(CAMPAIGN_NAMES[:4]):
            for ai, adset_name in enumerate(adset_names[:3]):
                impressions = random.randint(2000, 40000)
                clicks = random.randint(int(impressions * 0.005), int(impressions * 0.04))
                spend = round(random.uniform(200, 5000), 2)
                purchases = random.randint(0, max(1, int(clicks * 0.08)))
                purchase_value = round(purchases * random.uniform(500, 2500), 2) if purchases > 0 else 0

                rows.append({
                    "Ad Set ID": f"adset_{ci+1:02d}_{ai+1:02d}",
                    "Ad Set Name": f"{camp_name} - {adset_name}",
                    "Campaign ID": f"camp_{ci+1:04d}",
                    "Campaign Name": camp_name,
                    "Delivery": random.choice(["Active", "Completed"]),
                    "Date": current.strftime("%Y-%m-%d"),
                    "Impressions": impressions,
                    "Clicks (all)": clicks,
                    "Amount Spent (INR)": spend,
                    "Reach": int(impressions * random.uniform(0.6, 0.9)),
                    "Purchases": purchases,
                    "Purchase Conversion Value": purchase_value,
                    "CPM (Cost per 1,000 Impressions)": round(spend / impressions * 1000, 2) if impressions else 0,
                    "CPC (all)": round(spend / clicks, 2) if clicks else 0,
                    "CTR (all)": round(clicks / impressions * 100, 2) if impressions else 0,
                    "Targeting": random.choice(["Lookalike", "Interest", "Retargeting", "Broad", "Custom"]),
                })
        current += timedelta(days=1)

    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"Generated {len(rows)} adset rows -> {filename}")


if __name__ == "__main__":
    generate_campaigns_csv(
        "campaigns_oct_2024.csv",
        datetime(2024, 10, 1),
        datetime(2024, 10, 31),
    )
    generate_campaigns_csv(
        "campaigns_nov_2024.csv",
        datetime(2024, 11, 1),
        datetime(2024, 11, 30),
    )
    generate_adsets_csv(
        "adsets_oct_2024.csv",
        datetime(2024, 10, 1),
        datetime(2024, 10, 31),
    )
    generate_adsets_csv(
        "adsets_nov_2024.csv",
        datetime(2024, 11, 1),
        datetime(2024, 11, 30),
    )

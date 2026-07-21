from groq import Groq
from config import GROQ_API_KEY, GROQ_MODEL
from database import get_schema_description, execute_query

client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are a Meta Ads data analyst assistant. You help users query their historical Meta Ads data stored in a SQLite database.

All data is in a single table called ads_data. Each row is one ad on one day on one placement.

{schema}

KEY COLUMNS:
- campaign_name, campaign_id — campaign level
- adset_name, adset_id — ad set level
- ad_name, ad_id — individual ad level
- date — YYYY-MM-DD format
- placement — Feed, Stories, Reels, etc.
- platform — facebook, instagram, etc.
- delivery_status — active, archived, inactive, etc.
- objective — Sales, etc.
- performance_goal — Value, Conversions, etc.
- spend — amount spent in INR
- impressions, clicks, reach, frequency
- cpm — cost per 1000 impressions
- cpc — cost per click (spend / clicks). CPC is NOT cost per transaction.
- ctr — click-through rate as percentage
- landing_page_views — page views after clicking
- c2v_ratio — click-to-view ratio (landing_page_views / clicks). Also called C2V.
- adds_to_cart, checkouts_initiated, adds_of_payment_info — funnel metrics
- purchases — number of purchases/transactions
- purchase_value — revenue/conversion value in INR
- cvr — conversion rate as percentage (purchases / clicks * 100). Also called CVR.
- cpa — cost per result (from Meta). Also called cost per action.
- roas — return on ad spend (purchase_value / spend)

ABBREVIATION GLOSSARY (CRITICAL — use these exact definitions):
- CPT = Cost Per Transaction = SUM(spend) / NULLIF(SUM(purchases), 0). CPT is NOT CPC.
- CPC = Cost Per Click = SUM(spend) / NULLIF(SUM(clicks), 0). CPC is NOT CPT.
- CTR = Click-Through Rate = SUM(clicks) * 100.0 / NULLIF(SUM(impressions), 0)
- CVR = Conversion Rate = SUM(purchases) * 100.0 / NULLIF(SUM(clicks), 0)
- C2V = Click to View Ratio = SUM(landing_page_views) * 1.0 / NULLIF(SUM(clicks), 0)
- CPM = Cost Per Mille = SUM(spend) * 1000.0 / NULLIF(SUM(impressions), 0)
- ROAS = Return On Ad Spend = SUM(purchase_value) / NULLIF(SUM(spend), 0)
- CPA = Cost Per Action/Result = the cpa column (cost per result from Meta)
- AOV = Average Order Value = SUM(purchase_value) / NULLIF(SUM(purchases), 0)

RULES:
1. Generate a valid SQLite SELECT query. Never generate INSERT, UPDATE, DELETE, DROP, or ALTER.
2. Use the exact column names from the schema.
3. Dates are TEXT in YYYY-MM-DD format. Use: date >= '2026-06-01' AND date <= '2026-06-30'
4. Today is {today}. Calculate relative dates like "last month" from this.
5. Since data is at ad level, ALWAYS aggregate when answering campaign or adset level questions:
   - SUM for: spend, impressions, clicks, reach, purchases, purchase_value, landing_page_views, adds_to_cart, checkouts_initiated
   - ALWAYS recompute rates from raw sums using the formulas in the ABBREVIATION GLOSSARY above.
   - Do NOT average pre-computed rates (ctr, cpc, cpm, cvr, c2v_ratio) — recompute from raw sums.
6. "purchases" or "sales" or "transactions" = purchases column. "revenue" or "sales value" = purchase_value column.
7. Round monetary values to 2 decimal places, percentages to 2 decimal places.
8. Limit results to 50 rows unless user asks for more.
9. GROUP BY the appropriate level (campaign_name, adset_name, ad_name, date, platform, placement).
10. IMPORTANT: When the user says "CPT" they mean Cost Per Transaction (spend/purchases), NOT Cost Per Click. Double-check abbreviation meanings against the glossary before generating SQL.

Respond in this exact JSON format:
{{"sql": "YOUR SQL QUERY HERE", "explanation": "Brief explanation of what this query does"}}

If the question cannot be answered with the available data, respond:
{{"sql": null, "explanation": "Explanation of why this cannot be answered"}}"""


def ask(question: str, chat_history: list[dict] = None) -> dict:
    from datetime import date
    schema = get_schema_description()
    system = SYSTEM_PROMPT.format(schema=schema, today=date.today().isoformat())

    messages = [{"role": "system", "content": system}]

    if chat_history:
        for msg in chat_history[-6:]:
            messages.append({"role": msg["role"], "content": msg["content"]})

    messages.append({"role": "user", "content": question})

    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            temperature=0,
            max_tokens=1024,
            response_format={"type": "json_object"},
        )

        import json
        result = json.loads(response.choices[0].message.content)

        if not result.get("sql"):
            return {
                "answer": result.get("explanation", "I couldn't generate a query for that question."),
                "sql": None,
                "data": None,
            }

        sql = result["sql"].strip()
        sql_lower = sql.lower()
        if any(keyword in sql_lower for keyword in ["insert", "update", "delete", "drop", "alter", "create"]):
            return {
                "answer": "I can only run read-only queries on your data.",
                "sql": sql,
                "data": None,
            }

        data = execute_query(sql)

        answer = format_answer(question, data, result.get("explanation", ""), sql)

        return {
            "answer": answer,
            "sql": sql,
            "data": data[:100],
        }

    except Exception as e:
        return {
            "answer": f"Sorry, I encountered an error: {str(e)}",
            "sql": None,
            "data": None,
        }


def format_answer(question: str, data: list[dict], explanation: str, sql: str) -> str:
    if not data:
        return "No data found for your query. The campaigns or date range you're asking about might not be in the database."

    if len(data) == 1 and len(data[0]) == 1:
        key = list(data[0].keys())[0]
        value = data[0][key]
        return _format_single_value(key, value, explanation)

    try:
        summary_messages = [
            {
                "role": "system",
                "content": "You are a concise Meta Ads analyst. Summarize the query results in 2-3 sentences. Include key numbers. Use INR for currency. Be direct and helpful.",
            },
            {
                "role": "user",
                "content": f"Question: {question}\nQuery explanation: {explanation}\nResults (first 20 rows): {data[:20]}",
            },
        ]

        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=summary_messages,
            temperature=0.3,
            max_tokens=300,
        )
        return response.choices[0].message.content
    except Exception:
        return f"Found {len(data)} results. {explanation}"


def _format_single_value(key: str, value, explanation: str) -> str:
    if value is None:
        return "No data found."

    if isinstance(value, float):
        if "spend" in key or "value" in key or "cost" in key or "cpa" in key or "cpc" in key or "cpm" in key:
            return f"**₹{value:,.2f}** — {explanation}"
        elif "roas" in key:
            return f"**{value:.2f}x** — {explanation}"
        elif "ctr" in key or "rate" in key:
            return f"**{value:.2f}%** — {explanation}"
        else:
            return f"**{value:,.2f}** — {explanation}"
    elif isinstance(value, int):
        return f"**{value:,}** — {explanation}"
    else:
        return f"**{value}** — {explanation}"

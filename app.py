import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor
import re

app = Flask(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")  # Get PostgreSQL connection string from environment

# Initialize database
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            title TEXT,
            date TEXT,
            items TEXT,
            current_total REAL,
            due_amount REAL,
            grand_total REAL
        )
    """)
    conn.commit()
    c.close()
    conn.close()

init_db()

def format_number(n):
    return int(n) if n == int(n) else round(n, 2)

def calculate(text):
    lines = text.strip().split("\n")
    if not lines:
        return "Please enter a title and items."

    title = lines[0].strip()
    if not title:
        conn = psycopg2.connect(DATABASE_URL)
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM transactions WHERE title LIKE 'user%'")
        count = c.fetchone()[0] + 1
        c.close()
        conn.close()
        title = f"user{count}"

    item_lines = lines[1:]
    total = 0
    due_amount = 0
    item_results = []

    for line in item_lines:
        cleaned_line = re.sub(r'[×xX]', '*', line)
        match = re.search(r'(\d+\.?\d*)\s*([\+\-\*/])\s*(\d+\.?\d*)', cleaned_line)

        if "due" in line.lower():
            due_match = re.search(r'(\d+\.?\d*)', line)
            if due_match:
                due_amount = float(due_match.group(1))
            continue

        if match:
            num1 = float(match.group(1))
            operator = match.group(2)
            num2 = float(match.group(3))

            try:
                if operator == '+':
                    result = num1 + num2
                elif operator == '-':
                    result = num1 - num2
                elif operator == '*':
                    result = num1 * num2
                elif operator == '/':
                    if num2 == 0:
                        item_results.append(f"{line.strip()} = Error (division by zero)")
                        continue
                    result = num1 / num2

                total += result
                item_name = re.sub(r'(\d+\.?\d*)\s*[\+\-\*/]\s*(\d+\.?\d*)', '', cleaned_line).strip()
                item_results.append(f"{item_name} {match.group(1)}{operator}{match.group(3)} = {format_number(result)}")

            except Exception as e:
                item_results.append(f"{line.strip()} = Error: {str(e)}")
        else:
            item_results.append(f"{line.strip()} = Invalid expression")

    grand_total = total + due_amount
    date_today = datetime.now().strftime("%Y-%m-%d")

    try:
        conn = psycopg2.connect(DATABASE_URL)
        c = conn.cursor()
        c.execute("""
            INSERT INTO transactions (title, date, items, current_total, due_amount, grand_total)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (title, date_today, "\n".join(item_results), total, due_amount, grand_total))
        conn.commit()
        c.close()
        conn.close()
    except Exception as db_error:
        return f"Database Error: {str(db_error)}"

    response = (
        f"Name: {title}\n"
        f"Date: {date_today}\n"
        f"{chr(10).join(item_results)}\n"
        f"Current Total = {format_number(total)}\n"
        f"Due Amount = {format_number(due_amount)}\n"
        f"Total = {format_number(grand_total)}"
    )
    return response

@app.route("/", methods=["GET"])
def home():
    return "WhatsApp Bot is Live!", 200

@app.route("/whatsapp", methods=["GET", "POST"])
def reply_whatsapp():
    if request.method == "GET":
        return "OK", 200

    incoming_msg = request.values.get('Body', '')
    print(f"Incoming message: {incoming_msg}")
    reply_text = calculate(incoming_msg)
    print(f"Reply text: {reply_text}")

    resp = MessagingResponse()
    resp.message(reply_text)
    return str(resp)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

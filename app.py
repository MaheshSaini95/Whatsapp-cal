import os
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse
import re

app = Flask(__name__)

def format_number(n):
    return int(n) if n == int(n) else round(n, 2)

def calculate(text):
    lines = text.strip().split("\n")
    total = 0
    results = []

    for line in lines:
        cleaned_line = re.sub(r'[×xX*]', '*', line)

        match = re.search(r'(\d+\.?\d*)\s*([\+\-\*/])\s*(\d+\.?\d*)', cleaned_line)
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
                        results.append(f"{line.strip()} = Error (division by zero)")
                        continue
                    result = num1 / num2

                total += result
                item_name = re.sub(r'(\d+\.?\d*)\s*[\+\-\*/]\s*(\d+\.?\d*)', '', cleaned_line).strip()
                results.append(f"{item_name} {match.group(1)}{operator}{match.group(3)} = {format_number(result)}")
            except Exception as e:
                results.append(f"{line.strip()} = Error: {str(e)}")
        else:
            results.append(f"{line.strip()} = Invalid expression")

    results.append(f"Total = {format_number(total)}")
    return "\n".join(results)

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
    port = int(os.environ.get("PORT", 50))
    app.run(host="0.0.0.0", port=port)

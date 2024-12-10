from flask import Flask, request, render_template, send_file, jsonify
import fitz  # PyMuPDF
import pandas as pd
import os
import re
const port = process.env.PORT || 4000;
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def extract_data_from_pdf(pdf_path):
    try:
        document = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening file {pdf_path}: {e}")
        return [], [], []

    order_dates = []
    names = []
    shipping_addresses = []

    for page_num in range(len(document)):
        page = document.load_page(page_num)
        text = page.get_text("text")

        # Extract Order Date
        order_date_matches = re.findall(r"Order Date\s*:\s*(\d{2}\.\d{2}\.\d{4})", text)
        order_dates.extend(order_date_matches)

        # Extract Shipping Address
        shipping_address_matches = re.findall(r"Shipping Address\s*:\s*(.*?)(?:Place of|$)", text, re.S)
        for match in shipping_address_matches:
            match_lines = match.strip().split("\n")
            if match_lines:
                if len(match_lines[0].split()) > 1:
                    name = match_lines[0].strip()
                else:
                    name = "N/A"
                address = "\n".join(match_lines[1:]).replace("IN", "").strip()
                names.append(name)
                shipping_addresses.append(address)
            else:
                names.append("N/A")
                shipping_addresses.append("N/A")

    return order_dates, names, shipping_addresses
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload():
    files = request.files.getlist("pdf_files")
    if not files:
        return jsonify({"error": "No files uploaded"}), 400

    data = []
    for file in files:
        file_path = os.path.join(UPLOAD_FOLDER, file.filename)
        file.save(file_path)

        order_dates, names, shipping_addresses = extract_data_from_pdf(file_path)

        max_length = max(len(order_dates), len(names), len(shipping_addresses))
        order_dates.extend(["N/A"] * (max_length - len(order_dates)))
        names.extend(["N/A"] * (max_length - len(names)))
        shipping_addresses.extend(["N/A"] * (max_length - len(shipping_addresses)))

        for order_date, name, shipping_address in zip(order_dates, names, shipping_addresses):
            data.append({
                "File": file.filename,
                "Order Date": order_date,
                "Name": name,
                "Shipping Address": shipping_address
            })

    # Save to Excel
    df = pd.DataFrame(data)
    output_file = os.path.join(UPLOAD_FOLDER, "invoices_data.xlsx")
    df.to_excel(output_file, index=False)

    return jsonify({"message": "Data processed successfully", "download_url": "/download"}), 200

@app.route('/download')
def download():
    output_file = os.path.join(UPLOAD_FOLDER, "invoices_data.xlsx")
    return send_file(output_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

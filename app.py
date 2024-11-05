
from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import csv
from datetime import datetime
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import os
from dotenv import load_dotenv

# CSV class and functions to handle CSV operations
class CSV:
    CSV_FILE = "finance_data.csv"
    COLUMNS = ["date", "amount", "category", "description"]
    FORMAT = "%d-%m-%Y"

    @classmethod
    def initialize_csv(cls):
        """Initializes the CSV file if it doesn't exist."""
        try:
            pd.read_csv(cls.CSV_FILE)  # Ensure file exists.
        except (FileNotFoundError, pd.errors.EmptyDataError):
            df = pd.DataFrame(columns=cls.COLUMNS)
            df.to_csv(cls.CSV_FILE, index=False)  # Create a new CSV.

    @classmethod
    def add_entry(cls, date, amount, category, description):
        """Adds a new entry to the CSV."""
        new_entry = {
            "date": date,
            "amount": amount,
            "category": category,
            "description": description,
        }
        try:
            with open(cls.CSV_FILE, "a", newline="") as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=cls.COLUMNS)
                writer.writerow(new_entry)
                print("Entry added to CSV.")
        except Exception as e:
            flash(f"Error adding entry: {e}")

    @classmethod
    def get_transactions(cls, start_date, end_date):
        """Retrieves transactions between start and end dates."""
        try:
            df = pd.read_csv(cls.CSV_FILE)
            df["date"] = pd.to_datetime(df["date"], format=cls.FORMAT, errors='coerce')
            start_date = pd.to_datetime(start_date, format=cls.FORMAT, errors='coerce')
            end_date = pd.to_datetime(end_date, format=cls.FORMAT, errors='coerce')

            mask = (df["date"] >= start_date) & (df["date"] <= end_date)
            return df.loc[mask].dropna(subset=["date"])  # Handle NaT values.
        except Exception as e:
            flash(f"Error retrieving transactions: {e}")
            return pd.DataFrame()

# Load environment variables and initialize Flask app
load_dotenv()  
app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY') or 'fallback_secret_key'  # Handle missing .env

CSV.initialize_csv()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        date = request.form.get('date')
        amount = request.form.get('amount')
        category = request.form.get('category')
        description = request.form.get('description')

        # Add entry to CSV if valid
        if date and amount and category:
            try:
                amount = float(amount)  # Convert amount to float
                if amount >= 0:
                    CSV.add_entry(date, amount, category, description)
                    flash("Transaction added successfully!")
                    return redirect(url_for('index'))
                else:
                    flash("Invalid amount. Please enter a positive number.")
            except ValueError:
                flash("Invalid amount. Please enter a number.")
        else:
            flash("Please fill in all fields.")
    return render_template('add.html')

@app.route('/view', methods=['GET', 'POST'])
def view_transactions():
    transactions = None
    plot_url = None

    if request.method == 'POST':
        start_date = request.form.get('start_date').strip()
        end_date = request.form.get('end_date').strip()
        df = CSV.get_transactions(start_date, end_date)

        if df.empty:
            flash("No transactions found in the given date range.")
        else:
            transactions = df.to_dict('records')
            plot_url = generate_plot(df)

    return render_template('view.html', transactions=transactions, plot_url=plot_url)

def generate_plot(df):
    """Generates a line plot for income and expenses over time."""
    try:
        df['date'] = pd.to_datetime(df['date'], format=CSV.FORMAT)  # Convert date to datetime
        df.set_index("date", inplace=True)

        # Resample the data to daily frequency and fill missing dates
        income_df = df[df["category"] == "Income"].resample("D").sum()
        expense_df = df[df["category"] == "Expense"].resample("D").sum()

        plt.figure(figsize=(10, 5))
        plt.plot(income_df.index, income_df["amount"], label="Income", color="g", marker='o')
        plt.plot(expense_df.index, expense_df["amount"], label="Expense", color="r", marker='o')
        plt.xlabel("Date")
        plt.ylabel("Amount")
        plt.title("Income and Expenses Over Time")
        plt.legend()
        plt.grid(True)

        buffer = BytesIO()
        plt.savefig(buffer, format='png')
        plt.close()  # Close the figure to free memory
        buffer.seek(0)

        plot_data = buffer.read()
        plot_url = base64.b64encode(plot_data).decode()
        return f"data:image/png;base64,{plot_url}"
    except Exception as e:
        flash(f"Error generating plot: {e}")
        return None


if __name__ == "__main__":
    app.run(debug=True)  # Run the application in debug mode

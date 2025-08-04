from flask import Flask, render_template, request, redirect
import sqlite3
import pandas as pd

app = Flask(__name__)

# Initialize the database
def init_db():
    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute('''CREATE TABLE IF NOT EXISTS transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        title TEXT NOT NULL,
                        amount REAL NOT NULL,
                        type TEXT NOT NULL,
                        category TEXT NOT NULL,
                        date TEXT NOT NULL)''')

# Call it once when the app starts
init_db()

@app.route('/')
def dashboard():
    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute("SELECT type, amount, category, date FROM transactions")
        rows = cur.fetchall()

        # Get latest 5 transactions for quick view on dashboard
        cur.execute("SELECT * FROM transactions ORDER BY date DESC LIMIT 5")
        latest_transactions = cur.fetchall()

    income = sum([r[1] for r in rows if r[0] == 'income'])
    expense = sum([r[1] for r in rows if r[0] == 'expense'])
    balance = income - expense

    # Pie Chart (category-wise expense)
    df = pd.DataFrame(rows, columns=["type", "amount", "category", "date"])
    expense_df = df[df["type"] == "expense"]
    category_summary = expense_df.groupby("category")["amount"].sum().reset_index()

    pie_chart = {
        "data": [{
            "type": "pie",
            "labels": category_summary["category"].tolist(),
            "values": category_summary["amount"].tolist(),
            "hole": 0.4
        }],
        "layout": {
            "margin": {"t": 0, "b": 0, "l": 0, "r": 0},
        }
    }

     # Prepare bar chart with income and expense per month sorted chronologically
    df["date"] = pd.to_datetime(df["date"])
    df["month"] = df["date"].dt.strftime("%B")
    df["month_num"] = df["date"].dt.month

    monthly_summary = df.groupby(["month", "type", "month_num"])["amount"].sum().reset_index()
    monthly_summary = monthly_summary.sort_values("month_num")

    pivot_table = monthly_summary.pivot(index=["month", "month_num"], columns="type", values="amount").fillna(0)

    months = pivot_table.index.get_level_values('month').tolist()
    income_values = pivot_table.get('income', pd.Series([0]*len(months))).tolist()
    expense_values = pivot_table.get('expense', pd.Series([0]*len(months))).tolist()

    bar_chart = {
        "data": [
            {
                "type": "bar",
                "name": "Income",
                "x": months,
                "y": income_values,
                "marker": {"color": "green"}
            },
            {
                "type": "bar",
                "name": "Expense",
                "x": months,
                "y": expense_values,
                "marker": {"color": "red"}
            }
        ],
        "layout": {
            "barmode": "group",
            "xaxis": {"title": "Month"},
            "yaxis": {"title": "Amount (Rs)"},
            "margin": {"t": 20}
        }
    }

    return render_template('index.html',
                           income=income,
                           expense=expense,
                           balance=balance,
                           pie_chart=pie_chart,
                           bar_chart=bar_chart,
                           latest_transactions=latest_transactions)


@app.route('/add', methods=['GET', 'POST'])
def add_transaction():
    if request.method == 'POST':
        data = (
            request.form['title'],
            float(request.form['amount']),
            request.form['type'],
            request.form['category'],
            request.form['date']
        )
        with sqlite3.connect('database.db') as con:
            con.execute("INSERT INTO transactions (title, amount, type, category, date) VALUES (?, ?, ?, ?, ?)", data)
        return redirect('/')
    return render_template('add.html')


@app.route('/transactions')
def view_transactions():
    with sqlite3.connect('database.db') as con:
        cur = con.cursor()
        cur.execute("SELECT * FROM transactions ORDER BY date DESC")
        rows = cur.fetchall()
    return render_template('view.html', transactions=rows)


@app.route('/edit/<int:transaction_id>', methods=['GET', 'POST'])
def edit_transaction(transaction_id):
    if request.method == 'POST':
        data = (
            request.form['title'],
            float(request.form['amount']),
            request.form['type'],
            request.form['category'],
            request.form['date'],
            transaction_id
        )
        with sqlite3.connect('database.db') as con:
            con.execute("""
                UPDATE transactions SET title=?, amount=?, type=?, category=?, date=? 
                WHERE id=?
            """, data)
        return redirect('/transactions')
    else:
        with sqlite3.connect('database.db') as con:
            cur = con.cursor()
            cur.execute("SELECT * FROM transactions WHERE id=?", (transaction_id,))
            transaction = cur.fetchone()
        return render_template('edit.html', transaction=transaction)


@app.route('/delete/<int:transaction_id>')
def delete_transaction(transaction_id):
    with sqlite3.connect('database.db') as con:
        con.execute("DELETE FROM transactions WHERE id=?", (transaction_id,))
    return redirect('/transactions')


@app.route('/export')
def export_csv():
    with sqlite3.connect('database.db') as con:
        df = pd.read_sql_query("SELECT * FROM transactions", con)

    export_file = 'static/transactions_export.csv'
    df.to_csv(export_file, index=False)
    return redirect(f'/{export_file}')


if __name__ == '__main__':
    app.run(debug=True)

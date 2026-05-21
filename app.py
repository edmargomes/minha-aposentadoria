import webview
from flask import Flask, render_template, jsonify, request
from threading import Thread
import logging
from datetime import datetime
import database
import utils

app = Flask(__name__)

# Initialize database
database.init_db()

@app.route('/')
def index():
    return render_template('index.html')

# --- ASSETS (INVESTMENTS) API ---

@app.route('/api/investments', methods=['GET'])
def get_investments():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT i.id, i.name, i.institution,
               (SELECT h.value FROM investment_history h WHERE h.investment_id = i.id ORDER BY h.date DESC, h.id DESC LIMIT 1) as current_value,
               (SELECT h.value FROM investment_history h WHERE h.investment_id = i.id ORDER BY h.date DESC, h.id DESC LIMIT 1 OFFSET 1) as previous_value
        FROM investments i
    ''')
    investments = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(investments)

@app.route('/api/investments/<int:inv_id>', methods=['GET'])
def get_investment(inv_id):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM investments WHERE id = ?', (inv_id,))
    investment = dict(cursor.fetchone())
    cursor.execute('SELECT * FROM investment_history WHERE investment_id = ? ORDER BY date DESC, id DESC', (inv_id,))
    history = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify({**investment, 'history': history})

@app.route('/api/investments', methods=['POST'])
def add_investment():
    data = request.json
    name = data.get('name')
    value = data.get('value')
    institution = data.get('institution', '')
    
    if not name or value is None:
        return jsonify({'error': 'Name and value are required'}), 400
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO investments (name, institution) VALUES (?, ?)', (name, institution))
    inv_id = cursor.lastrowid
    cursor.execute('INSERT INTO investment_history (investment_id, value, date) VALUES (?, ?, ?)',
                   (inv_id, value, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    return jsonify({'id': inv_id}), 201

@app.route('/api/investments/<int:inv_id>', methods=['PUT'])
def update_investment(inv_id):
    data = request.json
    name = data.get('name')
    value = data.get('value')
    institution = data.get('institution')
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    if name:
        cursor.execute('UPDATE investments SET name = ? WHERE id = ?', (name, inv_id))
    if institution is not None:
        cursor.execute('UPDATE investments SET institution = ? WHERE id = ?', (institution, inv_id))
    if value is not None:
        cursor.execute('SELECT value FROM investment_history WHERE investment_id = ? ORDER BY date DESC, id DESC LIMIT 1', (inv_id,))
        last_val_row = cursor.fetchone()
        if last_val_row and float(last_val_row['value']) != float(value):
            cursor.execute('INSERT INTO investment_history (investment_id, value, date) VALUES (?, ?, ?)',
                           (inv_id, value, datetime.now().strftime('%Y-%m-%d')))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

@app.route('/api/investments/<int:inv_id>', methods=['DELETE'])
def delete_investment(inv_id):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM investments WHERE id = ?', (inv_id,))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# --- CONTRIBUTIONS (MONTHLY EFFORT) API ---

@app.route('/api/contributions', methods=['GET'])
def get_contributions():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    this_month = datetime.now().strftime('%Y-%m')
    cursor.execute('SELECT * FROM monthly_contributions WHERE month_year = ? ORDER BY date DESC', (this_month,))
    contributions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(contributions)

@app.route('/api/contributions', methods=['POST'])
def add_contribution():
    data = request.json
    amount = data.get('amount')
    description = data.get('description', '')
    
    if not amount:
        return jsonify({'error': 'Amount is required'}), 400
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    today = datetime.now()
    cursor.execute('''
        INSERT INTO monthly_contributions (amount, month_year, date, description) 
        VALUES (?, ?, ?, ?)
    ''', (amount, today.strftime('%Y-%m'), today.strftime('%Y-%m-%d'), description))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'}), 201

# --- SETTINGS API ---

@app.route('/api/settings', methods=['GET'])
def get_settings():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings WHERE id = 1')
    settings = dict(cursor.fetchone())
    conn.close()
    return jsonify(settings)

@app.route('/api/settings', methods=['POST'])
def save_settings():
    data = request.json
    rate = data.get('annual_interest_rate')
    goal = data.get('target_goal')
    months = data.get('target_months')
    initial_wealth = data.get('initial_wealth', 0)
    
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE settings 
        SET annual_interest_rate = ?, target_goal = ?, target_months = ?, initial_wealth = ? 
        WHERE id = 1
    ''', (rate, goal, months, initial_wealth))
    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})

# --- DASHBOARD & CHART API ---

@app.route('/api/dashboard/metrics', methods=['GET'])
def get_metrics():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM settings WHERE id = 1')
    settings = dict(cursor.fetchone())
    total_goal = float(settings['target_goal'])
    annual_rate = float(settings['annual_interest_rate'])
    target_months = int(settings['target_months'])
    initial_wealth = float(settings.get('initial_wealth', 0))
    
    # Calculate required monthly contribution considering initial wealth
    # Formula: PMT = (FV - PV(1+r)^n) / [((1+r)^n - 1)/r]
    r = (annual_rate / 100) / 12
    if r > 0 and target_months > 0:
        numerator = total_goal - (initial_wealth * ((1 + r)**target_months))
        denominator = ((1 + r)**target_months - 1) / r
        monthly_target = max(numerator / denominator, 0)
    else:
        monthly_target = max((total_goal - initial_wealth) / max(target_months, 1), 0)
    
    # Current Equity: Sum of latest history entries for all assets
    cursor.execute('''
        SELECT SUM(current_val) FROM (
            SELECT (SELECT value FROM investment_history h WHERE h.investment_id = i.id ORDER BY h.date DESC, h.id DESC LIMIT 1) as current_val
            FROM investments i
        )
    ''')
    current_equity = cursor.fetchone()[0] or 0
    
    # Invested this month
    this_month = datetime.now().strftime('%Y-%m')
    cursor.execute('SELECT SUM(amount) FROM monthly_contributions WHERE month_year = ?', (this_month,))
    invested_this_month = cursor.fetchone()[0] or 0
    
    # Total Invested: Initial Wealth + All monthly contributions
    cursor.execute('SELECT SUM(amount) FROM monthly_contributions')
    contributions_total = cursor.fetchone()[0] or 0
    total_invested = initial_wealth + contributions_total
    
    profitability = 0
    if total_invested > 0:
        profitability = ((current_equity - total_invested) / total_invested) * 100
        
    metrics = {
        'monthly_target': monthly_target,
        'invested_this_month': invested_this_month,
        'month_progress': min((invested_this_month / monthly_target) * 100, 100) if monthly_target > 0 else 0,
        'current_equity': current_equity,
        'profitability': profitability,
        'total_goal': total_goal,
        'target_months': target_months,
        'total_invested': total_invested,
        'remaining_amount': max(total_goal - current_equity, 0),
        'overall_progress': min((current_equity / total_goal) * 100, 100) if total_goal > 0 else 0
    }
    conn.close()
    return jsonify(metrics)

@app.route('/api/chart/data', methods=['GET'])
def get_chart_data():
    conn = database.get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM settings WHERE id = 1')
    settings = dict(cursor.fetchone())
    total_goal = float(settings['target_goal'])
    annual_rate = float(settings['annual_interest_rate'])
    target_months = int(settings['target_months'])
    initial_wealth = float(settings.get('initial_wealth', 0))
    
    labels = utils.get_months_labels(count=target_months)
    
    # Calculate required monthly contribution
    r = (annual_rate / 100) / 12
    if r > 0 and target_months > 0:
        numerator = total_goal - (initial_wealth * ((1 + r)**target_months))
        denominator = ((1 + r)**target_months - 1) / r
        pmt = max(numerator / denominator, 0)
    else:
        pmt = max((total_goal - initial_wealth) / max(target_months, 1), 0)

    # 1. Ideal Projection (Static target line starting from initial wealth)
    ideal_projection = [0] * target_months
    temp_ideal = initial_wealth
    for i in range(target_months):
        ideal_projection[i] = temp_ideal
        temp_ideal = (temp_ideal + pmt) * (1 + r)
    
    # 2. Actual Equity
    cursor.execute('''
        SELECT SUM(value) as total, strftime('%Y-%m', date) as month 
        FROM investment_history 
        GROUP BY month 
        ORDER BY date ASC
    ''')
    history_points = {row['month']: row['total'] for row in cursor.fetchall()}
    
    # 3. Wealth Projection (Expected path based on CURRENT actual wealth)
    cursor.execute('''
        SELECT SUM(current_val) FROM (
            SELECT (SELECT value FROM investment_history h WHERE h.investment_id = i.id ORDER BY h.date DESC, h.id DESC LIMIT 1) as current_val
            FROM investments i
        )
    ''')
    current_actual_wealth = cursor.fetchone()[0] or 0
    start_wealth = current_actual_wealth if current_actual_wealth > 0 else initial_wealth
    
    wealth_projection = [None] * target_months
    temp_wealth = start_wealth
    for i in range(target_months):
        wealth_projection[i] = temp_wealth
        temp_wealth = (temp_wealth + pmt) * (1 + r)

    actual_equity = [None] * target_months
    this_month_obj = datetime.now()
    for i in range(target_months):
        month_str = this_month_obj.strftime('%Y-%m')
        if month_str in history_points:
            actual_equity[i] = history_points[month_str]
        
        m = this_month_obj.month
        y = this_month_obj.year
        if m == 12: this_month_obj = this_month_obj.replace(year=y+1, month=1)
        else: this_month_obj = this_month_obj.replace(month=m+1)

    conn.close()
    return jsonify({
        'labels': labels,
        'ideal_projection': ideal_projection,
        'wealth_projection': wealth_projection,
        'actual_equity': actual_equity
    })

if __name__ == '__main__':
    def start_flask():
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        app.run(port=5000, debug=False, use_reloader=False)
    
    flask_thread = Thread(target=start_flask, daemon=True)
    flask_thread.start()
    
    webview.create_window(
        title='Investimentos - Aposentadoria',
        url='http://localhost:5000',
        width=1200,
        height=800,
        resizable=True,
        min_size=(800, 600)
    )
    webview.start()

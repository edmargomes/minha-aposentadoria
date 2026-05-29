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
    # current_value = (last balance update) + (all contributions after that balance update)
    # total_invested = sum of all contributions
    
    investments = []
    cursor.execute('SELECT id, name, institution FROM investments')
    rows = cursor.fetchall()
    
    for row in rows:
        inv_id = row['id']
        
        # Calculate Current Value
        # 1. Find the latest balance update
        cursor.execute('''
            SELECT value, date, id FROM investment_history 
            WHERE investment_id = ? AND type = 'balance' 
            ORDER BY date DESC, id DESC LIMIT 1
        ''', (inv_id,))
        last_balance_row = cursor.fetchone()
        
        if last_balance_row:
            last_balance = float(last_balance_row['value'])
            # 2. Sum contributions after that balance update
            cursor.execute('''
                SELECT SUM(value) FROM investment_history 
                WHERE investment_id = ? AND type = 'contribution' 
                AND (date > ? OR (date = ? AND id > ?))
            ''', (inv_id, last_balance_row['date'], last_balance_row['date'], last_balance_row['id']))
            extra_contributions = cursor.fetchone()[0] or 0
            current_value = last_balance + extra_contributions
        else:
            # No balance update, just sum all contributions
            cursor.execute('''
                SELECT SUM(value) FROM investment_history 
                WHERE investment_id = ? AND type = 'contribution'
            ''', (inv_id,))
            current_value = cursor.fetchone()[0] or 0
            
        # Total Invested is always the sum of all contributions
        cursor.execute('''
            SELECT SUM(value) FROM investment_history 
            WHERE investment_id = ? AND type = 'contribution'
        ''', (inv_id,))
        total_invested = cursor.fetchone()[0] or 0
        
        investments.append({
            'id': inv_id,
            'name': row['name'],
            'institution': row['institution'],
            'current_value': current_value,
            'total_invested': total_invested
        })
        
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
    
    # Calculate current_value specifically for this asset
    cursor.execute('''
        SELECT value, date, id FROM investment_history 
        WHERE investment_id = ? AND type = 'balance' 
        ORDER BY date DESC, id DESC LIMIT 1
    ''', (inv_id,))
    last_balance_row = cursor.fetchone()
    
    if last_balance_row:
        last_balance = float(last_balance_row['value'])
        cursor.execute('''
            SELECT SUM(value) FROM investment_history 
            WHERE investment_id = ? AND type = 'contribution' 
            AND (date > ? OR (date = ? AND id > ?))
        ''', (inv_id, last_balance_row['date'], last_balance_row['date'], last_balance_row['id']))
        extra_contributions = cursor.fetchone()[0] or 0
        current_value = last_balance + extra_contributions
    else:
        cursor.execute('''
            SELECT SUM(value) FROM investment_history 
            WHERE investment_id = ? AND type = 'contribution'
        ''', (inv_id,))
        current_value = cursor.fetchone()[0] or 0

    conn.close()
    return jsonify({**investment, 'history': history, 'current_value': current_value})

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
    today = datetime.now()
    # Initial investment is treated as a contribution
    cursor.execute('INSERT INTO investment_history (investment_id, value, date, type) VALUES (?, ?, ?, ?)',
                   (inv_id, value, today.strftime('%Y-%m-%d'), 'contribution'))

    # Also record in monthly contributions
    cursor.execute('''
        INSERT INTO monthly_contributions (amount, month_year, date, description)
        VALUES (?, ?, ?, ?)
    ''', (value, today.strftime('%Y-%m'), today.strftime('%Y-%m-%d'), f"Saldo inicial: {name}"))

    conn.commit()
    conn.close()
    return jsonify({'id': inv_id}), 201

@app.route('/api/investments/<int:inv_id>', methods=['PUT'])
def update_investment(inv_id):
    data = request.json
    name = data.get('name')
    value = data.get('value')
    institution = data.get('institution')
    action_type = data.get('type', 'balance') # 'contribution' or 'balance'

    conn = database.get_db_connection()
    cursor = conn.cursor()

    if name:
        cursor.execute('UPDATE investments SET name = ? WHERE id = ?', (name, inv_id))
    if institution is not None:
        cursor.execute('UPDATE investments SET institution = ? WHERE id = ?', (institution, inv_id))

    if value is not None:
        today = datetime.now()
        cursor.execute('SELECT name FROM investments WHERE id = ?', (inv_id,))
        inv_name = cursor.fetchone()['name']

        if action_type == 'contribution':
            # Contribution: Just store the contribution amount directly
            cursor.execute('INSERT INTO investment_history (investment_id, value, date, type) VALUES (?, ?, ?, ?)',
                           (inv_id, value, today.strftime('%Y-%m-%d'), 'contribution'))
            
            cursor.execute('''
                INSERT INTO monthly_contributions (amount, month_year, date, description)
                VALUES (?, ?, ?, ?)
            ''', (value, today.strftime('%Y-%m'), today.strftime('%Y-%m-%d'), f"Aporte: {inv_name}"))
        else:
            # Balance update: Only add if value changed from last history entry
            cursor.execute('SELECT value FROM investment_history WHERE investment_id = ? ORDER BY date DESC, id DESC LIMIT 1', (inv_id,))
            last_val_row = cursor.fetchone()
            if last_val_row and float(last_val_row['value']) != float(value):
                cursor.execute('INSERT INTO investment_history (investment_id, value, date, type) VALUES (?, ?, ?, ?)',
                               (inv_id, value, today.strftime('%Y-%m-%d'), 'balance'))

    conn.commit()
    conn.close()
    return jsonify({'status': 'success'})
@app.route('/api/investments/history/<int:history_id>', methods=['DELETE'])
def delete_history_entry(history_id):
    conn = database.get_db_connection()
    cursor = conn.cursor()
    
    # Get details before deleting for cleanup if it's a contribution
    cursor.execute('''
        SELECT h.*, i.name as inv_name 
        FROM investment_history h 
        JOIN investments i ON h.investment_id = i.id 
        WHERE h.id = ?
    ''', (history_id,))
    entry = cursor.fetchone()
    
    if entry:
        if entry['type'] == 'contribution':
            # Try to find and delete the corresponding entry in monthly_contributions
            # We match by amount, description containing the asset name, and the exact date
            cursor.execute('''
                DELETE FROM monthly_contributions 
                WHERE amount = ? AND date = ? AND (description LIKE ? OR description LIKE ?)
            ''', (entry['value'], entry['date'], f"Aporte: {entry['inv_name']}", f"Saldo inicial: {entry['inv_name']}"))
        
        cursor.execute('DELETE FROM investment_history WHERE id = ?', (history_id,))
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
    
    # Current Equity Calculation (matching get_investments logic)
    current_equity = 0
    cursor.execute('SELECT id FROM investments')
    inv_ids = [r['id'] for r in cursor.fetchall()]
    
    for inv_id in inv_ids:
        cursor.execute('''
            SELECT value, date, id FROM investment_history 
            WHERE investment_id = ? AND type = 'balance' 
            ORDER BY date DESC, id DESC LIMIT 1
        ''', (inv_id,))
        last_balance_row = cursor.fetchone()
        
        if last_balance_row:
            last_balance = float(last_balance_row['value'])
            cursor.execute('''
                SELECT SUM(value) FROM investment_history 
                WHERE investment_id = ? AND type = 'contribution' 
                AND (date > ? OR (date = ? AND id > ?))
            ''', (inv_id, last_balance_row['date'], last_balance_row['date'], last_balance_row['id']))
            extra_contributions = cursor.fetchone()[0] or 0
            current_equity += (last_balance + extra_contributions)
        else:
            cursor.execute('''
                SELECT SUM(value) FROM investment_history 
                WHERE investment_id = ? AND type = 'contribution'
            ''', (inv_id,))
            current_equity += (cursor.fetchone()[0] or 0)
    
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
        'total_invested': total_invested,
        'remaining_amount': max(total_goal - current_equity, 0),
        'overall_progress': min((current_equity / total_goal) * 100, 100) if total_goal > 0 else 0,
        'target_months': target_months,
        'annual_rate': annual_rate
    }

    # Milestone Tracking
    progress = metrics['overall_progress']
    today_str = datetime.now().strftime('%Y-%m-%d')
    for pct in range(10, 101, 10):
        if progress >= pct:
            cursor.execute('INSERT OR IGNORE INTO milestones (percentage, reached_at) VALUES (?, ?)', (pct, today_str))
    
    # --- WEATHER & JOURNEY SYSTEM ---
    # 1. Get yesterday's snapshot or earliest available
    cursor.execute('SELECT * FROM daily_snapshots WHERE date < ? ORDER BY date DESC LIMIT 1', (today_str,))
    prev_snapshot = cursor.fetchone()
    
    current_weather = "sunny"
    if prev_snapshot:
        equity_delta = current_equity - float(prev_snapshot['equity'])
        invested_delta = total_invested - float(prev_snapshot['total_invested'])
        # Yield delta: simplified as (Equity Change) - (New Money Added)
        # If yield_delta is negative, it means the assets themselves depreciated.
        yield_delta = equity_delta - invested_delta

        if equity_delta < -1.0: # Significant drop in total equity
            current_weather = "stormy"
            # Record persistent "scar" on the mountain
            cursor.execute('INSERT OR IGNORE INTO journey_events (percentage, type, date) VALUES (?, ?, ?)',
                           (round(progress, 1), 'storm', today_str))
        elif yield_delta < -1.0: # Equity might be up because of contributions, but yield is down
            current_weather = "cloudy"
            cursor.execute('INSERT OR IGNORE INTO journey_events (percentage, type, date) VALUES (?, ?, ?)',
                           (round(progress, 1), 'cloud', today_str))
    
    # 2. Update/Save today's snapshot (always the latest state of the day)
    cursor.execute('''
        INSERT INTO daily_snapshots (date, equity, total_invested)
        VALUES (?, ?, ?)
        ON CONFLICT(date) DO UPDATE SET equity=excluded.equity, total_invested=excluded.total_invested
    ''', (today_str, current_equity, total_invested))
    conn.commit()

    # 3. Retrieve all persistent journey events
    cursor.execute('SELECT percentage, type FROM journey_events ORDER BY percentage ASC')
    metrics['journey_events'] = [dict(row) for row in cursor.fetchall()]
    metrics['current_weather'] = current_weather
    
    cursor.execute('SELECT percentage, reached_at FROM milestones ORDER BY percentage ASC')
    metrics['milestones'] = [dict(row) for row in cursor.fetchall()]
    
    # Get start date
    cursor.execute('SELECT MIN(date) FROM investment_history')
    metrics['start_date'] = cursor.fetchone()[0] or today_str

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
    this_month_obj = datetime.now().replace(day=1)
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

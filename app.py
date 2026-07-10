from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
from database import DB_NAME, init_db
from scoring import get_ranked_providers

app = Flask(__name__)

init_db()

@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT h.id, u.name as producer_name, h.product_name, h.quantity, h.status 
        FROM harvests h
        JOIN users u ON h.producer_id = u.id
    ''')
    harvests = cursor.fetchall()
    
    cursor.execute("SELECT id, name, role FROM users")
    users = cursor.fetchall()
    
    conn.close()
    return render_template('index.html', harvests=harvests, users=users)

@app.route('/harvest/add', methods=['POST'])
def add_harvest():
    producer_id = request.form.get('producer_id')
    product_name = request.form.get('product_name')
    quantity = request.form.get('quantity')
    
    if producer_id and product_name and quantity:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO harvests (producer_id, product_name, quantity) VALUES (?, ?, ?)",
            (producer_id, product_name, quantity)
        )
        conn.commit()
        conn.close()
    
    return redirect(url_for('index'))

@app.route('/api/recommendations/<int:harvest_id>', methods=['GET'])
def recommendations(harvest_id):
    ranked_providers = get_ranked_providers(harvest_id)
    return jsonify(ranked_providers)

@app.route('/offer/make', methods=['POST'])
def make_offer():
    harvest_id = request.form.get('harvest_id')
    provider_id = request.form.get('provider_id')
    price = request.form.get('price')
    
    if harvest_id and provider_id and price:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO offers (harvest_id, provider_id, price) VALUES (?, ?, ?)",
            (harvest_id, provider_id, price)
        )
        conn.commit()
        conn.close()
        
    return redirect(url_for('index'))

@app.route('/offer/accept/<int:offer_id>', methods=['POST'])
def accept_offer(offer_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("UPDATE offers SET status = 'accepted' WHERE id = ?", (offer_id,))
    
    cursor.execute("SELECT harvest_id FROM offers WHERE id = ?", (offer_id,))
    row = cursor.fetchone()
    
    if row:
        harvest_id = row[0]
        cursor.execute("UPDATE offers SET status = 'rejected' WHERE harvest_id = ? AND id != ?", (harvest_id, offer_id))
        cursor.execute("UPDATE harvests SET status = 'completed' WHERE id = ?", (harvest_id,))
        
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
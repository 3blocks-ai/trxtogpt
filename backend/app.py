from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import requests
from datetime import datetime
import os
from decimal import Decimal
import urllib.parse

app = Flask(__name__)
CORS(app, origins=[
    os.getenv('FRONTEND_URL'),
    'https://your-frontend-domain.vercel.app'
], methods=['GET', 'POST'], allow_headers=['Content-Type'])

# Database connection
def get_db_connection():
    if os.getenv('DATABASE_URL'):
        # Parse DATABASE_URL for Render
        url = urllib.parse.urlparse(os.getenv('DATABASE_URL'))
        return psycopg2.connect(
            host=url.hostname,
            database=url.path[1:],
            user=url.username,
            password=url.password,
            port=url.port
        )
    else:
        # Local development
        return psycopg2.connect(
            host=os.getenv("DB_HOST"),
            database=os.getenv("DB_NAME"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD")
        )

# TronGrid API configuration
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY")
TRONGRID_API_URL = "https://api.shasta.trongrid.io"  # Testnet URL
MERCHANT_ADDRESS = os.getenv("MERCHANT_ADDRESS")  # Your TRX wallet address

if not os.getenv('MERCHANT_ADDRESS'):
    raise ValueError("MERCHANT_ADDRESS must be set")

if not os.getenv('TRONGRID_API_KEY'):
    raise ValueError("TRONGRID_API_KEY must be set")

@app.route('/api/check-usage', methods=['GET'])
def check_usage():
    wallet_address = request.args.get('wallet_address')
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Get user info or create new user
    cur.execute("""
        INSERT INTO users (wallet_address)
        VALUES (%s)
        ON CONFLICT (wallet_address) 
        DO UPDATE SET wallet_address = EXCLUDED.wallet_address
        RETURNING id, usage_count, usage_limit, payment_status
    """, (wallet_address,))
    
    user = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    return jsonify({
        'user_id': user[0],
        'usage_count': user[1],
        'usage_limit': user[2],
        'payment_status': user[3]
    })

@app.route('/api/verify-transaction', methods=['POST'])
def verify_transaction():
    data = request.json
    tx_id = data.get('tx_id')
    wallet_address = data.get('wallet_address')
    plan_id = data.get('plan_id')
    
    # Verify transaction using TronGrid API
    headers = {'TRON-PRO-API-KEY': TRONGRID_API_KEY}
    response = requests.get(
        f"{TRONGRID_API_URL}/v1/transactions/{tx_id}",
        headers=headers
    )
    
    if response.status_code != 200:
        return jsonify({'error': 'Transaction verification failed'}), 400
        
    tx_data = response.json()
    
    # Verify transaction details
    if (tx_data['to'] != MERCHANT_ADDRESS or 
        tx_data['confirmed'] != True or 
        tx_data['ret'][0]['contractRet'] != 'SUCCESS'):
        return jsonify({'error': 'Invalid transaction'}), 400
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get subscription plan details
        cur.execute("SELECT name, usage_limit FROM subscription_plans WHERE id = %s", (plan_id,))
        plan = cur.fetchone()
        
        if not plan:
            raise Exception("Invalid subscription plan")
            
        # Record transaction
        cur.execute("""
            INSERT INTO transactions (user_id, tx_id, amount, status)
            VALUES (
                (SELECT id FROM users WHERE wallet_address = %s),
                %s, %s, 'confirmed'
            )
        """, (wallet_address, tx_id, Decimal(tx_data['amount']) / 1000000))  # Convert from SUN to TRX
        
        # Update user limits and subscription
        cur.execute("""
            UPDATE users 
            SET usage_limit = usage_limit + %s,
                payment_status = 'paid',
                subscription_type = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE wallet_address = %s
        """, (plan[1], plan[0], wallet_address))
        
        conn.commit()
        
        return jsonify({
            'success': True, 
            'message': 'Payment verified',
            'subscription': plan[0],
            'usage_limit': plan[1]
        })
        
    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        cur.close()
        conn.close()

@app.route('/api/subscription-plans', methods=['GET'])
def get_subscription_plans():
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT * FROM subscription_plans ORDER BY trx_amount")
    plans = cur.fetchall()
    
    cur.close()
    conn.close()
    
    return jsonify([{
        'id': plan[0],
        'name': plan[1],
        'trx_amount': plan[2],
        'usage_limit': plan[3]
    } for plan in plans]) 
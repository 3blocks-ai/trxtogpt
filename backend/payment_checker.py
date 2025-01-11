import time
import psycopg2
import requests
from datetime import datetime, timedelta
import os
from decimal import Decimal

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv("DB_HOST"),
        database=os.getenv("DB_NAME"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD")
    )

def check_new_transactions():
    headers = {'TRON-PRO-API-KEY': os.getenv("TRONGRID_API_KEY")}
    merchant_address = os.getenv("MERCHANT_ADDRESS")
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    try:
        # Get latest transaction timestamp from our database
        cur.execute("SELECT MAX(created_at) FROM transactions")
        last_check = cur.fetchone()[0] or datetime.now() - timedelta(hours=1)
        
        # Get transactions from TronGrid API
        response = requests.get(
            f"https://api.shasta.trongrid.io/v1/accounts/{merchant_address}/transactions",
            params={
                'min_timestamp': int(last_check.timestamp() * 1000),
                'only_confirmed': True
            },
            headers=headers
        )
        
        if response.status_code != 200:
            print(f"Error fetching transactions: {response.status_code}")
            return
            
        transactions = response.json().get('data', [])
        
        for tx in transactions:
            if tx['to'] == merchant_address and tx['ret'][0]['contractRet'] == 'SUCCESS':
                amount = Decimal(tx['amount']) / 1000000  # Convert from SUN to TRX
                
                # Find matching subscription plan
                cur.execute("""
                    SELECT id, name, usage_limit 
                    FROM subscription_plans 
                    WHERE trx_amount = %s
                """, (int(amount),))
                
                plan = cur.fetchone()
                if plan:
                    # Check if transaction already processed
                    cur.execute("SELECT id FROM transactions WHERE tx_id = %s", (tx['txID'],))
                    if not cur.fetchone():
                        # Get or create user
                        cur.execute("""
                            INSERT INTO users (wallet_address)
                            VALUES (%s)
                            ON CONFLICT (wallet_address) 
                            DO UPDATE SET wallet_address = EXCLUDED.wallet_address
                            RETURNING id
                        """, (tx['from'],))
                        user_id = cur.fetchone()[0]
                        
                        # Record transaction
                        cur.execute("""
                            INSERT INTO transactions (user_id, tx_id, amount, status)
                            VALUES (%s, %s, %s, 'confirmed')
                        """, (user_id, tx['txID'], amount))
                        
                        # Update user limits
                        cur.execute("""
                            UPDATE users 
                            SET usage_limit = usage_limit + %s,
                                payment_status = 'paid',
                                subscription_type = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = %s
                        """, (plan[2], plan[1], user_id))
                        
                        print(f"Processed payment from {tx['from']}: {amount} TRX")
                        
        conn.commit()
        
    except Exception as e:
        print(f"Error processing transactions: {e}")
        conn.rollback()
    finally:
        cur.close()
        conn.close()

def run_payment_checker():
    while True:
        print("Checking for new payments...")
        check_new_transactions()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    run_payment_checker() 
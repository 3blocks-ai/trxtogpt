from app import app
from payment_checker import run_payment_checker
import threading
import os

def start_payment_checker():
    payment_checker_thread = threading.Thread(target=run_payment_checker)
    payment_checker_thread.daemon = True
    payment_checker_thread.start()

if __name__ == "__main__":
    start_payment_checker()
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000))) 
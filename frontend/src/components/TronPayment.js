import React, { useState, useEffect } from 'react';
import axios from 'axios';

const TronPayment = () => {
    const [walletAddress, setWalletAddress] = useState('');
    const [userInfo, setUserInfo] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const [plans, setPlans] = useState([]);
    const [selectedPlan, setSelectedPlan] = useState(null);

    useEffect(() => {
        checkTronLink();
        loadSubscriptionPlans();
    }, []);

    const loadSubscriptionPlans = async () => {
        try {
            const response = await axios.get('/api/subscription-plans');
            setPlans(response.data);
        } catch (err) {
            setError('Failed to load subscription plans');
        }
    };

    const checkTronLink = async () => {
        if (window.tronWeb && window.tronWeb.ready) {
            const address = window.tronWeb.defaultAddress.base58;
            setWalletAddress(address);
            await checkUsage(address);
        }
    };

    const checkUsage = async (address) => {
        try {
            const response = await axios.get(`/api/check-usage?wallet_address=${address}`);
            setUserInfo(response.data);
        } catch (err) {
            setError('Failed to check usage');
        }
    };

    const connectWallet = async () => {
        if (window.tronLink) {
            try {
                await window.tronLink.request({ method: 'tron_requestAccounts' });
                checkTronLink();
            } catch (err) {
                setError('Failed to connect wallet');
            }
        } else {
            setError('Please install TronLink');
        }
    };

    const handlePayment = async () => {
        if (!window.tronWeb || !window.tronWeb.ready) {
            setError('Please connect TronLink first');
            return;
        }

        if (!selectedPlan) {
            setError('Please select a subscription plan');
            return;
        }

        setLoading(true);
        try {
            // Send TRX payment
            const tx = await window.tronWeb.trx.sendTransaction(
                process.env.REACT_APP_MERCHANT_ADDRESS,
                selectedPlan.trx_amount * 1000000 // Convert to SUN
            );

            // Verify transaction
            const response = await axios.post('/api/verify-transaction', {
                tx_id: tx.txid,
                wallet_address: walletAddress,
                plan_id: selectedPlan.id
            });

            if (response.data.success) {
                await checkUsage(walletAddress);
                alert('Payment successful! Your subscription has been updated.');
            }
        } catch (err) {
            setError('Payment failed');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="tron-payment">
            {!walletAddress ? (
                <button onClick={connectWallet}>Connect TronLink</button>
            ) : (
                <div>
                    <p>Wallet: {walletAddress}</p>
                    {userInfo && (
                        <div>
                            <p>Usage: {userInfo.usage_count} / {userInfo.usage_limit}</p>
                            <p>Status: {userInfo.payment_status}</p>
                            <p>Subscription: {userInfo.subscription_type}</p>
                        </div>
                    )}
                    
                    <div className="subscription-plans">
                        <h3>Select Subscription Plan</h3>
                        <div className="plans-grid">
                            {plans.map(plan => (
                                <div 
                                    key={plan.id} 
                                    className={`plan-card ${selectedPlan?.id === plan.id ? 'selected' : ''}`}
                                    onClick={() => setSelectedPlan(plan)}
                                >
                                    <h4>{plan.name.toUpperCase()}</h4>
                                    <p>{plan.trx_amount.toLocaleString()} TRX</p>
                                    <p>{plan.usage_limit.toLocaleString()} Uses</p>
                                </div>
                            ))}
                        </div>
                        
                        <button 
                            onClick={handlePayment}
                            disabled={loading || !selectedPlan}
                        >
                            {loading ? 'Processing...' : `Pay ${selectedPlan?.trx_amount.toLocaleString() || 0} TRX`}
                        </button>
                    </div>
                </div>
            )}
            {error && <p className="error">{error}</p>}
        </div>
    );
};

export default TronPayment; 
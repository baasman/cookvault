import React, { useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import { Elements, CardElement, useStripe, useElements } from '@stripe/react-stripe-js';

import { bookProjectsApi } from '../../services/bookProjectsApi';

const stripePromise = loadStripe(import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY || '');

interface ExportPaywallModalProps {
  projectId: number;
  isOpen: boolean;
  onClose: () => void;
  onPaymentSucceeded: (exportId: number) => void;
}

interface PaymentFormProps {
  projectId: number;
  onSuccess: (exportId: number) => void;
  onError: (msg: string) => void;
}

const PaymentForm: React.FC<PaymentFormProps> = ({ projectId, onSuccess, onError }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);
  const [price, setPrice] = useState<number | null>(null);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!stripe || !elements) {
      onError('Stripe has not loaded yet. Please try again.');
      return;
    }
    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      onError('Card details not found.');
      return;
    }

    setLoading(true);
    try {
      const intent = await bookProjectsApi.createPurchaseIntent(projectId);
      setPrice(intent.price);

      const { error: stripeError, paymentIntent } = await stripe.confirmCardPayment(
        intent.client_secret,
        { payment_method: { card: cardElement } },
      );

      if (stripeError) {
        onError(stripeError.message || 'Payment failed.');
      } else if (paymentIntent?.status === 'succeeded') {
        onSuccess(intent.export_id);
      } else {
        onError('Payment did not complete. Please try again.');
      }
    } catch (err) {
      onError(err instanceof Error ? err.message : 'Payment failed.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-sm" style={{ color: '#6b5a52' }}>
        One-time purchase. After payment we render and store your clean (no-watermark) PDF;
        download it from the project dashboard as soon as it's ready.
      </p>
      <div
        className="p-3 rounded-md border"
        style={{ borderColor: '#e8dccf', backgroundColor: '#fffbf5' }}
      >
        <CardElement
          options={{
            style: {
              base: {
                fontSize: '16px',
                color: '#1c120d',
                '::placeholder': { color: '#9b644b' },
              },
            },
          }}
        />
      </div>
      <button
        type="submit"
        disabled={!stripe || loading}
        className="w-full py-2.5 text-white rounded-lg hover:opacity-90 disabled:opacity-50 transition-opacity"
        style={{ backgroundColor: '#f15f1c' }}
      >
        {loading
          ? 'Processing…'
          : price != null
            ? `Pay $${price.toFixed(2)}`
            : 'Pay for clean PDF'}
      </button>
    </form>
  );
};

export const ExportPaywallModal: React.FC<ExportPaywallModalProps> = ({
  projectId,
  isOpen,
  onClose,
  onPaymentSucceeded,
}) => {
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      style={{ backgroundColor: 'rgba(28, 18, 13, 0.55)' }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div
        className="max-w-md w-full rounded-lg p-6"
        style={{ backgroundColor: '#fcf9f8' }}
      >
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold" style={{ color: '#1c120d' }}>
              Buy clean PDF
            </h2>
            <p className="text-xs mt-1" style={{ color: '#9b644b' }}>
              No watermark — ready for printing.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-sm hover:opacity-70"
            style={{ color: '#6b5a52' }}
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        <Elements stripe={stripePromise}>
          <PaymentForm
            projectId={projectId}
            onSuccess={(exportId) => {
              setError(null);
              onPaymentSucceeded(exportId);
            }}
            onError={(msg) => setError(msg)}
          />
        </Elements>

        {error && (
          <div
            className="mt-3 px-3 py-2 rounded text-sm"
            style={{ backgroundColor: '#fef0ea', color: '#9b3a1c' }}
          >
            {error}
          </div>
        )}
      </div>
    </div>
  );
};

export default ExportPaywallModal;

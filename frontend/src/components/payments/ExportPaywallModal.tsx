import React, { useEffect, useState } from 'react';
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

interface IntentInfo {
  client_secret: string;
  export_id: number;
  price: number;
}

interface PaymentFormProps {
  intent: IntentInfo;
  onSuccess: (exportId: number) => void;
  onError: (msg: string) => void;
}

const PaymentForm: React.FC<PaymentFormProps> = ({ intent, onSuccess, onError }) => {
  const stripe = useStripe();
  const elements = useElements();
  const [loading, setLoading] = useState(false);

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
        {loading ? 'Processing…' : `Pay $${intent.price.toFixed(2)}`}
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
  const [intent, setIntent] = useState<IntentInfo | null>(null);
  const [loadingIntent, setLoadingIntent] = useState(false);

  // Create the PaymentIntent up front so we can show the price before the
  // user enters their card. Stripe charges nothing for created-but-abandoned
  // intents; they auto-expire after 24h.
  useEffect(() => {
    if (!isOpen) {
      setIntent(null);
      setError(null);
      return;
    }
    let cancelled = false;
    setLoadingIntent(true);
    bookProjectsApi
      .createPurchaseIntent(projectId)
      .then((resp) => {
        if (!cancelled) {
          setIntent({
            client_secret: resp.client_secret,
            export_id: resp.export_id,
            price: resp.price,
          });
        }
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to start payment');
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingIntent(false);
      });
    return () => {
      cancelled = true;
    };
  }, [isOpen, projectId]);

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

        {intent && (
          <div
            className="mb-4 px-4 py-3 rounded-md flex items-baseline justify-between"
            style={{ backgroundColor: '#f6efe6' }}
          >
            <span className="text-sm" style={{ color: '#6b5a52' }}>
              One-time purchase
            </span>
            <span className="text-2xl font-bold" style={{ color: '#1c120d' }}>
              ${intent.price.toFixed(2)}
            </span>
          </div>
        )}

        <p className="text-sm mb-4" style={{ color: '#6b5a52' }}>
          After payment we render and store your clean (no-watermark) PDF; it
          appears on the dashboard as soon as it's ready.
        </p>

        {loadingIntent && !intent && (
          <div className="py-6 text-center text-sm" style={{ color: '#6b5a52' }}>
            Loading payment details…
          </div>
        )}

        {intent && (
          <Elements stripe={stripePromise}>
            <PaymentForm
              intent={intent}
              onSuccess={(exportId) => {
                setError(null);
                onPaymentSucceeded(exportId);
              }}
              onError={(msg) => setError(msg)}
            />
          </Elements>
        )}

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

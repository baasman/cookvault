import React from 'react';
import { PaymentStatusHandler } from '../components/payments';

export const PaymentSuccessPage: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center py-12 px-4 sm:px-6 lg:px-8">
      <PaymentStatusHandler />
    </div>
  );
};
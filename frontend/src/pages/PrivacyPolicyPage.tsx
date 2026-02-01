import React from 'react';
import { Link } from 'react-router-dom';

const PrivacyPolicyPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Privacy Policy</h1>

      <div className="prose prose-lg max-w-none">
        <p className="text-gray-700 mb-6">
          Last updated: January 31, 2026
        </p>

        <p className="text-gray-700 mb-6">
          At Cookle ("we," "our," or "us"), we are committed to protecting your privacy. This Privacy Policy
          explains how we collect, use, disclose, and safeguard your information when you use our recipe
          management application and related services.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Information We Collect</h2>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">Account Information</h3>
        <p className="text-gray-700 mb-4">
          When you create an account, we collect:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Email address</li>
          <li>Username</li>
          <li>Password (stored securely using industry-standard encryption)</li>
          <li>Optional: First name, last name, bio, and profile photo</li>
          <li>Optional: Phone number (for account verification)</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">Recipe and Cookbook Data</h3>
        <p className="text-gray-700 mb-4">
          When you use our service, we store:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Recipes you create or upload (including titles, ingredients, instructions, and notes)</li>
          <li>Recipe images you upload</li>
          <li>Cookbooks and collections you organize</li>
          <li>Comments and ratings you provide</li>
          <li>Recipe categories and tags</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">Payment Information</h3>
        <p className="text-gray-700 mb-4">
          If you subscribe to premium features or purchase printed cookbooks:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Payment transactions are processed securely by Stripe</li>
          <li>We do not store your full credit card numbers</li>
          <li>We retain transaction records for accounting and legal purposes</li>
        </ul>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">Usage Data</h3>
        <p className="text-gray-700 mb-4">
          We automatically collect certain information when you use our app:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Device information (device type, operating system)</li>
          <li>App usage patterns and feature interactions</li>
          <li>Error logs and performance data</li>
          <li>IP address and general location (country/region)</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">How We Use Your Information</h2>
        <p className="text-gray-700 mb-4">We use your information to:</p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Provide and maintain our recipe management service</li>
          <li>Process recipe images using AI-powered text recognition</li>
          <li>Enable you to organize and share your recipes</li>
          <li>Process payments and fulfill print orders</li>
          <li>Send transactional emails (verification, password reset, order confirmations)</li>
          <li>Improve our service and fix bugs</li>
          <li>Respond to your support requests</li>
          <li>Enforce our terms of service</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Third-Party Services</h2>
        <p className="text-gray-700 mb-4">
          We use the following third-party services to operate Cookle:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li><strong>Stripe</strong> - Payment processing (PCI-DSS compliant)</li>
          <li><strong>Cloudinary</strong> - Image storage and optimization</li>
          <li><strong>Anthropic (Claude)</strong> - AI-powered recipe text extraction from images</li>
          <li><strong>SendGrid</strong> - Transactional email delivery</li>
          <li><strong>Twilio</strong> - SMS verification (optional)</li>
          <li><strong>Lulu</strong> - Print-on-demand cookbook fulfillment</li>
          <li><strong>Sentry</strong> - Error tracking and performance monitoring</li>
        </ul>
        <p className="text-gray-700 mb-4">
          Each service has its own privacy policy governing how they handle data. We only share the
          minimum information necessary for each service to function.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Data Retention</h2>
        <p className="text-gray-700 mb-4">
          We retain your data as follows:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li><strong>Account data:</strong> Until you delete your account</li>
          <li><strong>Recipes and cookbooks:</strong> Until you delete them or your account</li>
          <li><strong>Payment records:</strong> 7 years (legal/tax requirements)</li>
          <li><strong>Usage logs:</strong> 90 days</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Your Rights</h2>
        <p className="text-gray-700 mb-4">
          You have the right to:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li><strong>Access your data:</strong> Download a complete copy of your data from Account Settings</li>
          <li><strong>Correct your data:</strong> Edit your profile and recipes at any time</li>
          <li><strong>Delete your data:</strong> Request account deletion from Account Settings (7-day grace period with recovery option)</li>
          <li><strong>Export your data:</strong> Download your recipes, cookbooks, and images in portable formats</li>
          <li><strong>Withdraw consent:</strong> Opt out of optional features at any time</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Data Security</h2>
        <p className="text-gray-700 mb-4">
          We implement industry-standard security measures including:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>HTTPS encryption for all data transmission</li>
          <li>Secure password hashing using bcrypt</li>
          <li>JWT token-based authentication</li>
          <li>Regular security audits</li>
          <li>Access controls and monitoring</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Cookies and Local Storage</h2>
        <p className="text-gray-700 mb-4">
          We use cookies and local storage for:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Maintaining your login session</li>
          <li>Remembering your preferences</li>
          <li>Analytics and performance monitoring</li>
        </ul>
        <p className="text-gray-700 mb-4">
          You can control cookies through your browser settings, but this may affect app functionality.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Children's Privacy</h2>
        <p className="text-gray-700 mb-4">
          Cookle is not intended for children under 13. We do not knowingly collect personal
          information from children under 13. If you believe a child has provided us with personal
          information, please contact us immediately.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">International Data Transfers</h2>
        <p className="text-gray-700 mb-4">
          Your data may be transferred to and processed in the United States, where our servers are
          located. By using Cookle, you consent to this transfer. We ensure appropriate safeguards
          are in place for international data transfers.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Changes to This Policy</h2>
        <p className="text-gray-700 mb-4">
          We may update this Privacy Policy from time to time. We will notify you of significant
          changes by posting the updated policy on our app and, where appropriate, by email.
          Your continued use of Cookle after changes constitutes acceptance of the updated policy.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Contact Us</h2>
        <p className="text-gray-700 mb-4">
          If you have questions about this Privacy Policy or our data practices, please contact us at:
        </p>
        <ul className="list-none mb-6 text-gray-700">
          <li>Email: <a href="mailto:boudeyz@gmail.com" className="text-blue-600 hover:underline">boudeyz@gmail.com</a></li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Related Policies</h2>
        <p className="text-gray-700 mb-4">
          Please also review our:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li><Link to="/terms-of-service" className="text-blue-600 hover:underline">Terms of Service</Link></li>
          <li><Link to="/copyright-policy" className="text-blue-600 hover:underline">Copyright Policy</Link></li>
        </ul>
      </div>
    </div>
  );
};

export default PrivacyPolicyPage;

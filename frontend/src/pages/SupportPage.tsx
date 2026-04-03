import React from 'react';
import { Link } from 'react-router-dom';
import { openExternalUrl } from '../utils/platform';

const SupportPage: React.FC = () => {
  const handleEmailClick = (e: React.MouseEvent) => {
    e.preventDefault();
    openExternalUrl('mailto:boudeyz@gmail.com');
  };

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Support</h1>

      <div className="prose prose-lg max-w-none">
        <p className="text-gray-700 mb-6">
          We're here to help! If you have questions, feedback, or need assistance with Cookle,
          please don't hesitate to reach out.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Contact Us</h2>
        <p className="text-gray-700 mb-4">
          The best way to reach us is by email:
        </p>
        <p className="mb-6">
          <button
            onClick={handleEmailClick}
            className="text-blue-600 hover:underline font-medium"
          >
            boudeyz@gmail.com
          </button>
        </p>
        <p className="text-gray-700 mb-6">
          We typically respond within 24-48 hours.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Frequently Asked Questions</h2>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">How do I upload a recipe?</h3>
        <p className="text-gray-700 mb-4">
          Tap the + button in the header or go to the Upload page. You can take a photo of a recipe,
          import from a website URL, paste recipe text, or upload a cooking video.
        </p>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">What image formats are supported?</h3>
        <p className="text-gray-700 mb-4">
          We support JPG, PNG, GIF, BMP, TIFF, and HEIC images. Each image can be up to 10MB.
        </p>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">How many recipes can I upload for free?</h3>
        <p className="text-gray-700 mb-4">
          Free accounts can upload up to 10 recipes per month. Upgrade to Premium for unlimited uploads.
        </p>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">Can I print my recipes?</h3>
        <p className="text-gray-700 mb-4">
          Yes! You can create printed cookbooks from your recipe collection. Organize recipes into a cookbook,
          then use our print-on-demand service to order a professionally printed book.
        </p>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">How do I delete my account?</h3>
        <p className="text-gray-700 mb-4">
          Go to Settings and scroll to the bottom to find the account deletion option. You'll have a 7-day
          grace period to recover your account before it's permanently deleted.
        </p>

        <h3 className="text-xl font-semibold text-gray-900 mt-6 mb-3">Is my data secure?</h3>
        <p className="text-gray-700 mb-4">
          Yes. We use industry-standard encryption for all data transmission and storage. Your recipes
          are private by default unless you choose to share them publicly. See our{' '}
          <Link to="/privacy-policy" className="text-blue-600 hover:underline">Privacy Policy</Link> for details.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Related Links</h2>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>
            <Link to="/privacy-policy" className="text-blue-600 hover:underline">Privacy Policy</Link>
          </li>
          <li>
            <Link to="/terms-of-service" className="text-blue-600 hover:underline">Terms of Service</Link>
          </li>
          <li>
            <Link to="/copyright-policy" className="text-blue-600 hover:underline">Copyright Policy</Link>
          </li>
        </ul>
      </div>
    </div>
  );
};

export { SupportPage };

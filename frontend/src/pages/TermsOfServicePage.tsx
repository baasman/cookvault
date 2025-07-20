import React from 'react';

const TermsOfServicePage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Terms of Service</h1>
      
      <div className="prose prose-lg max-w-none">
        <p className="text-gray-700 mb-6">
          Last updated: {new Date().toLocaleDateString()}
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Acceptance of Terms</h2>
        <p className="text-gray-700 mb-4">
          By accessing and using our recipe sharing platform, you accept and agree to be bound by 
          these Terms of Service. If you do not agree to these terms, please do not use our service.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Description of Service</h2>
        <p className="text-gray-700 mb-4">
          Our platform allows users to upload, store, organize, and share recipes for personal use. 
          Users can create recipe collections, add recipes to groups, and optionally make recipes 
          publicly available for other users to discover and use.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">User Accounts</h2>
        <p className="text-gray-700 mb-4">
          To use our service, you must create an account and provide accurate information. 
          You are responsible for:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Maintaining the security of your account credentials</li>
          <li>All activities that occur under your account</li>
          <li>Immediately notifying us of any unauthorized use</li>
          <li>Ensuring your account information is accurate and up-to-date</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Content and Copyright</h2>
        <p className="text-gray-700 mb-4">
          When you upload or share content on our platform, you represent and warrant that:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>You own or have the right to use the content</li>
          <li>Your content does not infringe on any third-party rights</li>
          <li>You have obtained all necessary permissions for copyrighted material</li>
          <li>You grant us permission to store and display your content as part of our service</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Public Recipes</h2>
        <p className="text-gray-700 mb-4">
          When you make a recipe public, you grant other users a non-exclusive license to use 
          your recipe for their personal, non-commercial cooking and meal preparation. You also 
          acknowledge that:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Public recipes may be viewed, saved, and used by other users</li>
          <li>You have provided all necessary copyright consents</li>
          <li>You understand the recipe will be publicly searchable</li>
          <li><strong>Once public, recipes cannot be made private again - only deleted</strong></li>
        </ul>
        <p className="text-gray-700 mb-4">
          <strong>Important:</strong> Making a recipe public is a permanent decision. If you later 
          want to remove it from public view, you must delete the recipe entirely.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Prohibited Uses</h2>
        <p className="text-gray-700 mb-4">You may not use our service to:</p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Upload content that infringes on copyrights or other intellectual property rights</li>
          <li>Share inappropriate, offensive, or illegal content</li>
          <li>Attempt to gain unauthorized access to our systems or other users' accounts</li>
          <li>Use our service for commercial purposes without our permission</li>
          <li>Spam, harass, or abuse other users</li>
          <li>Distribute malware or engage in other harmful activities</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Privacy</h2>
        <p className="text-gray-700 mb-4">
          Your privacy is important to us. Please review our Privacy Policy to understand how we 
          collect, use, and protect your information.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Termination</h2>
        <p className="text-gray-700 mb-4">
          We may terminate or suspend your account at any time for violation of these terms. 
          You may also terminate your account at any time by contacting us.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Disclaimers</h2>
        <p className="text-gray-700 mb-4">
          Our service is provided "as is" without warranties of any kind. We are not responsible for:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>The accuracy or safety of recipes shared by users</li>
          <li>Food allergies, dietary restrictions, or health issues</li>
          <li>Loss of data or service interruptions</li>
          <li>Actions of other users on our platform</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Changes to Terms</h2>
        <p className="text-gray-700 mb-4">
          We may update these Terms of Service from time to time. We will notify you of significant 
          changes by posting the updated terms on our platform.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Contact Information</h2>
        <p className="text-gray-700 mb-4">
          If you have questions about these Terms of Service, please contact us at 
          <a href="mailto:legal@example.com" className="text-blue-600 hover:underline"> legal@example.com</a>.
        </p>
      </div>
    </div>
  );
};

export default TermsOfServicePage;
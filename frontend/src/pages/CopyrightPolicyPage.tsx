import React from 'react';

const CopyrightPolicyPage: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-6">Copyright Policy</h1>
      
      <div className="prose prose-lg max-w-none">
        <p className="text-gray-700 mb-6">
          This Copyright Policy explains how we handle copyright-protected content on our platform 
          and your rights and responsibilities when sharing recipes.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">What is Protected by Copyright?</h2>
        <p className="text-gray-700 mb-4">
          In general, recipe ingredients and basic cooking methods are not protected by copyright. 
          However, the following may be protected:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Detailed creative descriptions and explanations</li>
          <li>Personal stories and anecdotes</li>
          <li>Unique presentations and formatting</li>
          <li>Substantial portions of published cookbooks</li>
          <li>Original photography and illustrations</li>
          <li>Creative recipe collections and arrangements</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Your Responsibilities</h2>
        <p className="text-gray-700 mb-4">
          When you upload or share a recipe on our platform, you agree to:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Only share recipes you have the right to share</li>
          <li>Not copy substantial portions of copyrighted cookbooks without permission</li>
          <li>Respect the intellectual property rights of cookbook authors and publishers</li>
          <li>Provide proper attribution when sharing recipes from other sources</li>
          <li>Only make recipes public that you have the right to share publicly</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Public Recipe Policy</h2>
        <p className="text-gray-700 mb-4">
          <strong>Important:</strong> Once you make a recipe public, you cannot make it private again. 
          This ensures data integrity and user trust in our platform. If you later want to remove a 
          public recipe from view, your only option is to delete it entirely.
        </p>
        <p className="text-gray-700 mb-4">
          When you share a recipe publicly, you grant other users permission to use it for their 
          personal cooking and meal preparation. Please be certain you want to share a recipe 
          publicly before making this decision.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Fair Use and Personal Use</h2>
        <p className="text-gray-700 mb-4">
          While copyright law includes provisions for fair use, our platform is designed for personal, 
          non-commercial use of recipes.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Reporting Copyright Infringement</h2>
        <p className="text-gray-700 mb-4">
          If you believe your copyrighted work has been used without permission, please contact us 
          with the following information:
        </p>
        <ul className="list-disc pl-6 mb-6 text-gray-700">
          <li>Your contact information</li>
          <li>Description of the copyrighted work</li>
          <li>Location of the infringing content on our platform</li>
          <li>A statement that you have a good faith belief the use is not authorized</li>
          <li>A statement that the information is accurate and you are authorized to act</li>
        </ul>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Our Response to Infringement Claims</h2>
        <p className="text-gray-700 mb-4">
          We take copyright infringement seriously and will investigate all valid claims. 
          We may remove content that infringes on copyrights and may suspend or terminate 
          accounts of repeat infringers.
        </p>

        <h2 className="text-2xl font-semibold text-gray-900 mt-8 mb-4">Questions?</h2>
        <p className="text-gray-700 mb-4">
          If you have questions about copyright and recipe sharing, please contact us at 
          <a href="mailto:copyright@example.com" className="text-blue-600 hover:underline"> copyright@example.com</a>.
        </p>

        <div className="mt-8 p-4 bg-blue-50 rounded-lg">
          <p className="text-sm text-blue-800">
            <strong>Disclaimer:</strong> This policy is for informational purposes only and does not 
            constitute legal advice. Copyright law can be complex, and you should consult with a 
            qualified attorney for specific legal questions.
          </p>
        </div>
      </div>
    </div>
  );
};

export default CopyrightPolicyPage;